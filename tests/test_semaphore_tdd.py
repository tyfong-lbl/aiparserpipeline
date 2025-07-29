#!/usr/bin/env python3
"""
Test-Driven Development tests for semaphore implementation.
Mocks API calls and web scraping to focus on concurrency control.
"""

import asyncio
import pytest
import logging
import pandas as pd
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import time
import threading
from collections import defaultdict

# Set up test logging
logging.basicConfig(level=logging.INFO)

class ConcurrencyTracker:
    """Thread-safe tracker for concurrent operations."""
    def __init__(self):
        self.lock = threading.Lock()
        self.current_count = 0
        self.max_seen = 0
        self.history = []
        
    def acquire(self, project_name):
        with self.lock:
            self.current_count += 1
            self.max_seen = max(self.max_seen, self.current_count)
            self.history.append(('acquire', project_name, self.current_count, time.time()))
            
    def release(self, project_name):
        with self.lock:
            self.current_count -= 1
            self.history.append(('release', project_name, self.current_count, time.time()))

# Global tracker for testing
concurrency_tracker = ConcurrencyTracker()

@pytest.mark.asyncio
async def test_semaphore_limits_concurrency():
    """Test that semaphore actually limits concurrent operations."""
    from multi_project_validator import MultiProjectValidator
    from pipeline_logger import PipelineLogger
    
    # Reset tracker
    global concurrency_tracker
    concurrency_tracker = ConcurrencyTracker()
    
    # Test configuration
    max_concurrent = 5
    excel_file = "mock_medium_test.xlsx"  # 100 projects
    
    # Set up test environment
    prompt_directory = Path(__file__).resolve().parent / 'test_prompts'
    checkpoint_dir = Path(__file__).resolve().parent / 'test_checkpoints'
    pipeline_logs_dir = Path(__file__).resolve().parent / 'test_pipeline_logs'
    
    # Create directories
    for directory in [prompt_directory, checkpoint_dir, pipeline_logs_dir]:
        directory.mkdir(exist_ok=True)
    
    logger = PipelineLogger(pipeline_logs_dir)
    
    # Mock ModelValidator.consolidate_responses to simulate work and track concurrency
    async def mock_consolidate_responses(self):
        project_name = self.project_name
        concurrency_tracker.acquire(project_name)
        
        try:
            # Simulate processing time
            await asyncio.sleep(0.1)  # 100ms processing time
            
            # Return mock DataFrame
            return pd.DataFrame({
                'project': [project_name],
                'result': ['mocked_result'],
                'processed_at': [time.time()]
            })
        finally:
            concurrency_tracker.release(project_name)
    
    # Apply the mock
    with patch('page_tracker.ModelValidator.consolidate_responses', mock_consolidate_responses):
        validator = MultiProjectValidator(
            excel_path=excel_file,
            api_key="test_key",
            api_url="https://test.api.com",
            model="test_model",
            prompt_directory=prompt_directory,
            checkpoint_dir=checkpoint_dir,
            logger=logger,
            max_concurrent_projects=max_concurrent
        )
        
        print(f"Testing with {len(validator.project_names)} projects, max_concurrent={max_concurrent}")
        
        # Run the processing
        await validator.initialize()
        results = await validator.process_all_projects()
        
        # Assertions
        assert concurrency_tracker.max_seen <= max_concurrent, f"Concurrency exceeded limit: {concurrency_tracker.max_seen} > {max_concurrent}"
        assert len(results) == len(validator.project_names), f"Expected {len(validator.project_names)} results, got {len(results)}"
        
        print(f"✓ Max concurrent projects seen: {concurrency_tracker.max_seen}/{max_concurrent}")
        print(f"✓ All {len(results)} projects processed successfully")
        
        return concurrency_tracker

@pytest.mark.asyncio
async def test_large_dataset_stress_test():
    """Test semaphore with large dataset (500+ projects)."""
    from multi_project_validator import MultiProjectValidator
    from pipeline_logger import PipelineLogger
    
    # Reset tracker
    global concurrency_tracker
    concurrency_tracker = ConcurrencyTracker()
    
    # Test configuration - conservative for stress test
    max_concurrent = 20
    excel_file = "mock_large_stress_test.xlsx"  # 500 projects
    
    # Set up test environment
    prompt_directory = Path(__file__).resolve().parent / 'test_prompts'
    checkpoint_dir = Path(__file__).resolve().parent / 'test_checkpoints_large'
    pipeline_logs_dir = Path(__file__).resolve().parent / 'test_pipeline_logs_large'
    
    # Create directories
    for directory in [prompt_directory, checkpoint_dir, pipeline_logs_dir]:
        directory.mkdir(exist_ok=True)
    
    logger = PipelineLogger(pipeline_logs_dir)
    
    # Mock with faster processing for large dataset
    async def mock_consolidate_responses_fast(self):
        project_name = self.project_name
        concurrency_tracker.acquire(project_name)
        
        try:
            # Faster processing for stress test
            await asyncio.sleep(0.01)  # 10ms processing time
            
            return pd.DataFrame({
                'project': [project_name],
                'result': ['mocked_result'],
                'urls_processed': [len(self.url_df.dropna())],
                'processed_at': [time.time()]
            })
        finally:
            concurrency_tracker.release(project_name)
    
    start_time = time.time()
    
    with patch('page_tracker.ModelValidator.consolidate_responses', mock_consolidate_responses_fast):
        validator = MultiProjectValidator(
            excel_path=excel_file,
            api_key="test_key",
            api_url="https://test.api.com", 
            model="test_model",
            prompt_directory=prompt_directory,
            checkpoint_dir=checkpoint_dir,
            logger=logger,
            max_concurrent_projects=max_concurrent
        )
        
        print(f"STRESS TEST: Processing {len(validator.project_names)} projects with max_concurrent={max_concurrent}")
        
        await validator.initialize()
        results = await validator.process_all_projects()
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Assertions
        assert concurrency_tracker.max_seen <= max_concurrent, f"Concurrency exceeded: {concurrency_tracker.max_seen} > {max_concurrent}"
        assert len(results) == len(validator.project_names), f"Expected {len(validator.project_names)} results, got {len(results)}"
        
        # Performance metrics
        total_urls = results['urls_processed'].sum() if 'urls_processed' in results.columns else 0
        
        print(f"✓ STRESS TEST PASSED:")
        print(f"  - Projects processed: {len(results)}")
        print(f"  - Total URLs: {total_urls}")
        print(f"  - Max concurrent: {concurrency_tracker.max_seen}/{max_concurrent}")
        print(f"  - Processing time: {processing_time:.2f}s")
        print(f"  - Projects/second: {len(results)/processing_time:.1f}")
        
        return concurrency_tracker

@pytest.mark.asyncio 
async def test_semaphore_release_on_error():
    """Test that semaphore is properly released even when processing fails."""
    from multi_project_validator import MultiProjectValidator
    from pipeline_logger import PipelineLogger
    
    # Reset tracker
    global concurrency_tracker
    concurrency_tracker = ConcurrencyTracker()
    
    max_concurrent = 3
    excel_file = "mock_small_test.xlsx"  # 10 projects
    
    # Set up test environment
    prompt_directory = Path(__file__).resolve().parent / 'test_prompts'
    checkpoint_dir = Path(__file__).resolve().parent / 'test_checkpoints_error'
    pipeline_logs_dir = Path(__file__).resolve().parent / 'test_pipeline_logs_error'
    
    for directory in [prompt_directory, checkpoint_dir, pipeline_logs_dir]:
        directory.mkdir(exist_ok=True)
    
    logger = PipelineLogger(pipeline_logs_dir)
    
    # Mock that fails for some projects
    async def mock_consolidate_responses_with_errors(self):
        project_name = self.project_name
        concurrency_tracker.acquire(project_name)
        
        try:
            await asyncio.sleep(0.05)
            
            # Fail for projects containing "TX" in name
            if "TX" in project_name:
                raise Exception(f"Simulated failure for {project_name}")
            
            return pd.DataFrame({
                'project': [project_name],
                'result': ['success']
            })
        finally:
            concurrency_tracker.release(project_name)
    
    with patch('page_tracker.ModelValidator.consolidate_responses', mock_consolidate_responses_with_errors):
        validator = MultiProjectValidator(
            excel_path=excel_file,
            api_key="test_key",
            api_url="https://test.api.com",
            model="test_model", 
            prompt_directory=prompt_directory,
            checkpoint_dir=checkpoint_dir,
            logger=logger,
            max_concurrent_projects=max_concurrent
        )
        
        await validator.initialize()
        results = await validator.process_all_projects()
        
        # Check that semaphore was properly released (final count should be 0)
        assert concurrency_tracker.current_count == 0, f"Semaphore not properly released: {concurrency_tracker.current_count} still held"
        assert concurrency_tracker.max_seen <= max_concurrent, f"Concurrency exceeded: {concurrency_tracker.max_seen} > {max_concurrent}"
        
        print(f"✓ ERROR HANDLING TEST PASSED:")
        print(f"  - Final semaphore count: {concurrency_tracker.current_count} (should be 0)")
        print(f"  - Max concurrent seen: {concurrency_tracker.max_seen}/{max_concurrent}")
        print(f"  - Results processed: {len(results)}")

def analyze_concurrency_history(tracker):
    """Analyze the concurrency history for debugging."""
    print(f"\n=== Concurrency Analysis ===")
    print(f"Total operations: {len(tracker.history)}")
    print(f"Max concurrent: {tracker.max_seen}")
    
    # Show timeline of first few operations
    print(f"\nFirst 10 operations:")
    for i, (op, project, count, timestamp) in enumerate(tracker.history[:10]):
        print(f"  {i+1:2d}. {op:7s} {project[:20]:20s} -> {count:2d} concurrent")

if __name__ == "__main__":
    print("=== TDD Semaphore Tests ===\n")
    
    async def run_tests():
        # Test 1: Basic semaphore limiting
        print("Test 1: Semaphore Concurrency Limiting")
        tracker1 = await test_semaphore_limits_concurrency()
        analyze_concurrency_history(tracker1)
        
        print("\n" + "="*60 + "\n")
        
        # Test 2: Large dataset stress test
        print("Test 2: Large Dataset Stress Test")
        tracker2 = await test_large_dataset_stress_test()
        analyze_concurrency_history(tracker2)
        
        print("\n" + "="*60 + "\n")
        
        # Test 3: Error handling
        print("Test 3: Error Handling and Semaphore Release")
        await test_semaphore_release_on_error()
        
        print(f"\n✓ All TDD tests passed!")
        print(f"✓ Semaphore implementation is working correctly")
    
    asyncio.run(run_tests())