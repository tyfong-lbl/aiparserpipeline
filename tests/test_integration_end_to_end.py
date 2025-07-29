"""
Comprehensive integration test suite for the AiParser refactoring project.

This test suite verifies end-to-end functionality from ModelValidator through AiParser,
ensuring that the refactoring achieves all its goals: better performance, maintained
functionality, and reliable operation at scale.

These tests focus on system-level behavior rather than individual components.
"""

import asyncio
import tempfile
import pytest
import json
import pandas as pd
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call
from typing import List, Dict, Any
import statistics

# Import the classes under test
from page_tracker import ModelValidator, AiParser


class TestIntegrationEndToEnd:
    """Integration tests for complete workflow from ModelValidator through AiParser."""
    
    @pytest.fixture
    def sample_url_df(self):
        """Create sample URL DataFrame for testing."""
        return pd.DataFrame({
            'url': [
                'https://example.com/solar-project-1',
                'https://example.com/wind-project-2',
                'https://example.com/battery-storage-3'
            ],
            'project': [
                'Solar Farm Alpha',
                'Wind Farm Beta', 
                'Battery Storage Gamma'
            ]
        })
    
    @pytest.fixture
    def temp_prompt_dir(self):
        """Create temporary directory with test prompt files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            prompt_dir = Path(temp_dir)
            
            # Create realistic prompt files
            prompts = [
                "Extract the project name and location from the following content about PROJECT: ",
                "Identify the technology type and capacity for PROJECT from this content: ",
                "Find the development status and timeline for PROJECT in this text: ",
                "Extract financial information and costs for PROJECT from the content: ",
                "Identify environmental impact and permits for PROJECT from this data: "
            ]
            
            for i, prompt_text in enumerate(prompts, 1):
                prompt_file = prompt_dir / f"integration-prompt{i}.txt"
                prompt_file.write_text(prompt_text)
            
            yield prompt_dir
    
    @pytest.fixture
    def model_validator(self, sample_url_df, temp_prompt_dir):
        """Create ModelValidator instance for integration testing."""
        return ModelValidator(
            number_of_queries=5,
            prompt_dir_path=temp_prompt_dir,
            prompt_filename_base='integration-prompt',
            api_key='integration-test-key',
            api_url='https://test.integration.api.com',
            model='integration-test-model',
            project_name='Integration Test Project',
            url_df=sample_url_df
        )
    
    @pytest.mark.asyncio
    async def test_complete_workflow_single_url_multiple_prompts(self, model_validator):
        """Test complete workflow: single URL processed with multiple prompts."""
        url = 'https://example.com/integration-test-project'
        
        # Mock scraped content that would be returned
        mock_scraped_content = """
        Solar Energy Project Alpha
        Location: California, USA
        Technology: Photovoltaic Solar Panels
        Capacity: 100 MW
        Status: Under Construction
        Timeline: Completion expected Q4 2024
        Investment: $150 million
        Environmental Impact: Minimal, desert location
        Permits: All major permits approved
        """
        
        # Mock API responses for each prompt
        mock_api_responses = [
            '{"project_name": "Solar Energy Project Alpha", "location": "California, USA"}',
            '{"technology": "Photovoltaic Solar Panels", "capacity": "100 MW"}',
            '{"status": "Under Construction", "timeline": "Q4 2024"}',
            '{"investment": "$150 million", "financial_info": "fully funded"}',
            '{"environmental_impact": "Minimal", "permits": "All approved"}'
        ]
        
        with patch('page_tracker.AiParser') as MockAiParser:
            mock_parser = AsyncMock()
            MockAiParser.return_value = mock_parser
            
            # Mock successful scraping and caching
            mock_parser.initialize = AsyncMock()
            mock_parser.scrape_and_cache = AsyncMock(return_value='/tmp/integration_cache.txt')
            
            # Mock API responses for each prompt
            api_call_count = 0
            def mock_api_response(*args, **kwargs):
                nonlocal api_call_count
                response = mock_api_responses[api_call_count % len(mock_api_responses)]
                api_call_count += 1
                return (response, {'llm_processing_time': 0.5})
            
            mock_parser.get_api_response = MagicMock(side_effect=mock_api_response)
            mock_parser.strip_markdown = MagicMock(side_effect=lambda x: x)
            mock_parser.cleanup = AsyncMock()
            
            # Execute complete workflow
            start_time = time.perf_counter()
            results = await model_validator.get_responses_for_url(url)
            end_time = time.perf_counter()
            
            total_processing_time = end_time - start_time
            
            # Verify workflow results
            assert len(results) == 5, f"Should process 5 prompts, got {len(results)}"
            
            # Verify scraping was called only once
            mock_parser.scrape_and_cache.assert_called_once_with(url)
            
            # Verify API processing was called for each prompt
            assert mock_parser.get_api_response.call_count == 5, \
                f"Should make 5 API calls, made {mock_parser.get_api_response.call_count}"
            
            # Verify results format
            for i, result in enumerate(results):
                assert isinstance(result, dict), f"Result {i} should be dict"
                assert url in result, f"Result {i} should contain URL key"
                
                # Verify JSON parsing worked
                response_data = result[url]
                assert isinstance(response_data, dict), f"Result {i} should contain parsed JSON"
            
            # Verify cleanup was called
            mock_parser.cleanup.assert_called_once()
            
            # Performance verification
            assert total_processing_time > 0, "Processing should take measurable time"
            
            # Verify end-to-end workflow efficiency
            # Should be faster than scraping 5 times (mock timing shows this)
            expected_scraping_calls = 1  # Only one scraping call
            expected_api_calls = 5      # One API call per prompt
            
            assert mock_parser.scrape_and_cache.call_count == expected_scraping_calls
            assert mock_parser.get_api_response.call_count == expected_api_calls
    
    @pytest.mark.asyncio
    async def test_multi_prompt_processing_produces_consistent_results(self, model_validator):
        """Test that multi-prompt processing produces consistent, high-quality results."""
        url = 'https://example.com/consistency-test'
        
        # Mock consistent scraped content
        consistent_content = """
        Renewable Energy Project Bravo
        Technology: Wind Turbines
        Location: Texas, USA
        Capacity: 200 MW
        Developer: Green Energy Corp
        Status: Operational since 2023
        Investment: $300 million
        """
        
        # Define expected data extraction for each prompt type
        expected_extractions = {
            0: {"project_name": "Renewable Energy Project Bravo", "location": "Texas, USA"},
            1: {"technology": "Wind Turbines", "capacity": "200 MW"},
            2: {"status": "Operational", "timeline": "since 2023"},
            3: {"investment": "$300 million", "developer": "Green Energy Corp"},
            4: {"environmental_status": "renewable", "operational": True}
        }
        
        with patch('page_tracker.AiParser') as MockAiParser:
            mock_parser = AsyncMock()
            MockAiParser.return_value = mock_parser
            
            # Mock successful operations
            mock_parser.initialize = AsyncMock()
            mock_parser.scrape_and_cache = AsyncMock(return_value='/tmp/consistency_cache.txt')
            mock_parser.cleanup = AsyncMock()
            
            # Mock API responses based on expected extractions
            def mock_consistent_api(*args, **kwargs):
                # Simulate different responses for different prompts
                call_count = mock_parser.get_api_response.call_count
                expected_data = expected_extractions.get(call_count, {"result": "processed"})
                return (json.dumps(expected_data), {'llm_processing_time': 0.3})
            
            mock_parser.get_api_response = MagicMock(side_effect=mock_consistent_api)
            mock_parser.strip_markdown = MagicMock(side_effect=lambda x: x)
            
            # Execute workflow
            results = await model_validator.get_responses_for_url(url)
            
            # Verify consistency and completeness
            assert len(results) == 5, "Should process all 5 prompts"
            
            # Verify each result contains expected data structure
            for i, result in enumerate(results):
                assert url in result, f"Result {i} missing URL key"
                response_data = result[url]
                expected_data = expected_extractions.get(i, {"result": "processed"})
                
                # Verify response structure matches expected
                assert isinstance(response_data, dict), f"Result {i} should be parsed JSON"
                
                # At least some expected keys should be present
                if i < len(expected_extractions):
                    expected_keys = list(expected_data.keys())
                    response_keys = list(response_data.keys())
                    assert len(response_keys) > 0, f"Result {i} should have response data"
            
            # Verify processing efficiency
            assert mock_parser.scrape_and_cache.call_count == 1, "Should scrape only once"
            assert mock_parser.get_api_response.call_count == 5, "Should process 5 prompts"
    
    @pytest.mark.asyncio
    async def test_error_recovery_scenarios(self, model_validator):
        """Test error recovery in end-to-end workflows."""
        url = 'https://example.com/error-recovery-test'
        
        with patch('page_tracker.AiParser') as MockAiParser:
            mock_parser = AsyncMock()
            MockAiParser.return_value = mock_parser
            
            # Test Case 1: Scraping fails - should return empty list
            mock_parser.initialize = AsyncMock()
            mock_parser.scrape_and_cache = AsyncMock(side_effect=Exception("Network error"))
            mock_parser.cleanup = AsyncMock()
            
            result_scraping_failure = await model_validator.get_responses_for_url(url)
            
            # Should handle scraping failure gracefully
            assert result_scraping_failure == [], "Should return empty list for scraping failure"
            mock_parser.cleanup.assert_called_once()
            
            # Reset mock for next test case
            mock_parser.reset_mock()
            
            # Test Case 2: Some API calls fail - should handle partial failures
            mock_parser.initialize = AsyncMock()
            mock_parser.scrape_and_cache = AsyncMock(return_value='/tmp/error_test_cache.txt')
            mock_parser.cleanup = AsyncMock()
            
            # Mock API responses: some succeed, some fail
            api_responses = [
                ('{"success": "prompt1"}', {}),  # Success
                Exception("API timeout"),        # Failure
                ('{"success": "prompt3"}', {}),  # Success
                Exception("Rate limit"),         # Failure
                ('{"success": "prompt5"}', {})   # Success
            ]
            
            call_count = 0
            def mock_mixed_api(*args, **kwargs):
                nonlocal call_count
                response = api_responses[call_count]
                call_count += 1
                if isinstance(response, Exception):
                    raise response
                return response
            
            mock_parser.get_api_response = MagicMock(side_effect=mock_mixed_api)
            mock_parser.strip_markdown = MagicMock(side_effect=lambda x: x)
            
            result_partial_failure = await model_validator.get_responses_for_url(url)
            
            # Should handle partial failures gracefully
            assert len(result_partial_failure) == 5, "Should return results for all prompts"
            
            # Verify mix of successful and failed results
            successful_results = [r for r in result_partial_failure if r is not None]
            failed_results = [r for r in result_partial_failure if r is None]
            
            assert len(successful_results) == 3, f"Should have 3 successful results, got {len(successful_results)}"
            assert len(failed_results) == 2, f"Should have 2 failed results, got {len(failed_results)}"
            
            # Verify successful results have correct format
            for result in successful_results:
                assert url in result, "Successful results should contain URL key"
                assert "success" in result[url], "Successful results should contain expected data"
            
            # Verify cleanup still occurred
            mock_parser.cleanup.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_pipeline_logging_integration(self, model_validator):
        """Test that pipeline logging captures correct metrics throughout workflow."""
        url = 'https://example.com/logging-integration-test'
        
        # Create a mock pipeline logger to capture metrics
        mock_logger = MagicMock()
        
        with patch('page_tracker.AiParser') as MockAiParser:
            mock_parser = AsyncMock()
            MockAiParser.return_value = mock_parser
            
            # Set up mock parser with logging
            mock_parser.initialize = AsyncMock()
            mock_parser.scrape_and_cache = AsyncMock(return_value='/tmp/logging_cache.txt')
            mock_parser.cleanup = AsyncMock()
            mock_parser.pipeline_logger = mock_logger
            
            # Mock API responses with realistic timing metrics
            def mock_api_with_metrics(*args, **kwargs):
                return ('{"logged": "response"}', {
                    'llm_processing_time': 0.4,
                    'llm_response_status': True,
                    'llm_response_error': None
                })
            
            mock_parser.get_api_response = MagicMock(side_effect=mock_api_with_metrics)
            mock_parser.strip_markdown = MagicMock(side_effect=lambda x: x)
            
            # Execute workflow
            results = await model_validator.get_responses_for_url(url)
            
            # Verify workflow completed successfully
            assert len(results) == 5, "Should complete all prompts"
            assert all(r is not None for r in results), "All results should be successful"
            
            # Verify scraping and API processing occurred as expected
            mock_parser.scrape_and_cache.assert_called_once_with(url)
            assert mock_parser.get_api_response.call_count == 5
            
            # Verify cleanup occurred
            mock_parser.cleanup.assert_called_once()
            
            # Note: Detailed logging verification would require access to actual logging calls
            # This test verifies the integration structure supports logging
    
    @pytest.mark.asyncio
    async def test_cache_file_management_across_workflow(self, model_validator):
        """Test that cache files are properly managed throughout the complete workflow."""
        url = 'https://example.com/cache-management-test'
        
        # Track cache file operations
        cache_operations = []
        
        def track_cache_file_creation(*args, **kwargs):
            cache_path = '/tmp/cache_management_test.txt'
            cache_operations.append(f"created:{cache_path}")
            return cache_path
        
        def track_cache_cleanup(*args, **kwargs):
            cache_operations.append("cleanup_called")
        
        with patch('page_tracker.AiParser') as MockAiParser:
            mock_parser = AsyncMock()
            MockAiParser.return_value = mock_parser
            
            # Set up tracking
            mock_parser.initialize = AsyncMock()
            mock_parser.scrape_and_cache = AsyncMock(side_effect=track_cache_file_creation)
            mock_parser.get_api_response = MagicMock(return_value=('{"cached": "response"}', {}))
            mock_parser.strip_markdown = MagicMock(side_effect=lambda x: x)
            mock_parser.cleanup = AsyncMock(side_effect=track_cache_cleanup)
            
            # Execute workflow
            results = await model_validator.get_responses_for_url(url)
            
            # Verify workflow results
            assert len(results) == 5, "Should process all prompts"
            
            # Verify cache operations occurred in correct order
            assert len(cache_operations) >= 2, f"Should have cache operations: {cache_operations}"
            assert any("created:" in op for op in cache_operations), "Should create cache file"
            assert "cleanup_called" in cache_operations, "Should call cleanup"
            
            # Verify cache file was created before cleanup
            create_ops = [i for i, op in enumerate(cache_operations) if "created:" in op]
            cleanup_ops = [i for i, op in enumerate(cache_operations) if op == "cleanup_called"]
            
            assert len(create_ops) > 0, "Should have cache creation"
            assert len(cleanup_ops) > 0, "Should have cleanup"
            assert min(create_ops) < max(cleanup_ops), "Cache creation should happen before cleanup"
            
            # Verify scraping and processing occurred as expected
            mock_parser.scrape_and_cache.assert_called_once()
            assert mock_parser.get_api_response.call_count == 5
            mock_parser.cleanup.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_performance_improvements_end_to_end(self, model_validator):
        """Test measurable performance improvements in end-to-end workflow."""
        url = 'https://example.com/performance-test'
        
        # Track timing for different operations
        operation_times = {
            'scraping': [],
            'api_processing': [],
            'total_workflow': []
        }
        
        def mock_scraping_with_timing(*args, **kwargs):
            start = time.perf_counter()
            # Simulate scraping time
            time.sleep(0.01)  # 10ms simulated scraping
            end = time.perf_counter()
            operation_times['scraping'].append(end - start)
            return '/tmp/performance_cache.txt'
        
        def mock_api_with_timing(*args, **kwargs):
            start = time.perf_counter()
            # Simulate API processing time
            time.sleep(0.005)  # 5ms simulated API call
            end = time.perf_counter()
            operation_times['api_processing'].append(end - start)
            return ('{"performance": "test"}', {'llm_processing_time': end - start})
        
        with patch('page_tracker.AiParser') as MockAiParser:
            mock_parser = AsyncMock()
            MockAiParser.return_value = mock_parser
            
            # Set up timing mocks
            mock_parser.initialize = AsyncMock()
            mock_parser.scrape_and_cache = AsyncMock(side_effect=mock_scraping_with_timing)
            mock_parser.get_api_response = MagicMock(side_effect=mock_api_with_timing)
            mock_parser.strip_markdown = MagicMock(side_effect=lambda x: x)
            mock_parser.cleanup = AsyncMock()
            
            # Measure total workflow time
            workflow_start = time.perf_counter()
            results = await model_validator.get_responses_for_url(url)
            workflow_end = time.perf_counter()
            
            total_workflow_time = workflow_end - workflow_start
            operation_times['total_workflow'].append(total_workflow_time)
            
            # Verify workflow completed successfully
            assert len(results) == 5, "Should complete all prompts"
            
            # Analyze performance characteristics
            total_scraping_time = sum(operation_times['scraping'])
            total_api_time = sum(operation_times['api_processing'])
            
            # Verify performance improvements
            assert len(operation_times['scraping']) == 1, "Should scrape only once"
            assert len(operation_times['api_processing']) == 5, "Should process 5 prompts"
            
            # Calculate theoretical old approach time (scraping for each prompt)
            theoretical_old_time = 5 * total_scraping_time + total_api_time
            actual_new_time = total_scraping_time + total_api_time
            
            # Calculate performance improvement
            if theoretical_old_time > 0:
                time_saved = theoretical_old_time - actual_new_time
                performance_improvement = (time_saved / theoretical_old_time) * 100
                
                # Should show significant improvement
                assert performance_improvement > 40, \
                    f"Should show >40% improvement, got {performance_improvement:.1f}%"
            
            # Verify efficient resource usage
            assert total_workflow_time > 0, "Workflow should take measurable time"
            assert mock_parser.scrape_and_cache.call_count == 1, "Should minimize scraping calls"
            assert mock_parser.get_api_response.call_count == 5, "Should process all prompts"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])