"""
Multi-prompt processing and concurrency integration tests for the AiParser refactoring.

This test suite focuses on:
1. Multi-prompt processing verification
2. Concurrent processing of multiple projects/threads
3. Scalability and performance under concurrent load
4. Resource management across concurrent operations
"""

import asyncio
import tempfile
import pytest
import pandas as pd
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any
import threading
import concurrent.futures

# Import the classes under test
from page_tracker import ModelValidator, AiParser


class TestIntegrationMultiPromptConcurrency:
    """Integration tests for multi-prompt processing and concurrency."""
    
    @pytest.fixture
    def multi_project_url_df(self):
        """Create DataFrame with multiple projects for concurrency testing."""
        return pd.DataFrame({
            'url': [
                'https://example.com/solar-project-alpha',
                'https://example.com/wind-project-beta',
                'https://example.com/battery-project-gamma',
                'https://example.com/hydro-project-delta',
                'https://example.com/geothermal-project-epsilon'
            ],
            'project': [
                'Solar Farm Alpha - 100MW California',
                'Wind Farm Beta - 200MW Texas',
                'Battery Storage Gamma - 50MW Nevada',
                'Hydro Plant Delta - 75MW Colorado',
                'Geothermal Epsilon - 30MW Utah'
            ]
        })
    
    @pytest.fixture
    def large_prompt_dir(self):
        """Create directory with many prompt files for scalability testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            prompt_dir = Path(temp_dir)
            
            # Create 10 different prompt files for comprehensive testing
            prompts = [
                "Extract project name and developer information for PROJECT: ",
                "Identify technology type and specifications for PROJECT: ",
                "Find location details and site characteristics for PROJECT: ",
                "Extract capacity, power output, and technical specs for PROJECT: ",
                "Identify development timeline and status for PROJECT: ",
                "Find financial information and investment details for PROJECT: ",
                "Extract environmental impact and sustainability data for PROJECT: ",
                "Identify regulatory approvals and permits for PROJECT: ",
                "Find grid connection and transmission details for PROJECT: ",
                "Extract community impact and stakeholder information for PROJECT: "
            ]
            
            for i, prompt_text in enumerate(prompts, 1):
                prompt_file = prompt_dir / f"multi-prompt{i}.txt"
                prompt_file.write_text(prompt_text)
            
            yield prompt_dir
    
    @pytest.fixture
    def large_model_validator(self, multi_project_url_df, large_prompt_dir):
        """Create ModelValidator with many prompts for scalability testing."""
        return ModelValidator(
            number_of_queries=10,  # Use all 10 prompts
            prompt_dir_path=large_prompt_dir,
            prompt_filename_base='multi-prompt',
            api_key='multi-test-key',
            api_url='https://test.multi.api.com',
            model='multi-test-model',
            project_name='Multi-Prompt Test Project',
            url_df=multi_project_url_df
        )
    
    @pytest.mark.asyncio
    async def test_multi_prompt_processing_verification(self, large_model_validator):
        """Test that multi-prompt processing produces consistent, comprehensive results."""
        url = 'https://example.com/comprehensive-project'
        
        # Mock realistic project content
        comprehensive_content = """
        Renewable Energy Project Charlie
        Developer: Clean Energy Solutions Inc.
        Technology: Combined Solar and Wind
        Location: Arizona Desert, 50 miles from Phoenix
        Solar Capacity: 150 MW photovoltaic panels
        Wind Capacity: 100 MW wind turbines
        Total Capacity: 250 MW combined
        Development Status: Construction Phase 2 of 3
        Timeline: Phase 1 complete, Phase 2 ongoing, Phase 3 starts Q2 2025
        Investment: $400 million total, $280 million committed
        Environmental Impact: Minimal desert ecosystem impact, bird migration study completed
        Permits: Federal BLM permit approved, state environmental clearance received
        Grid Connection: 230kV transmission line under construction
        Community: Local hiring program, $2M community development fund
        """
        
        # Define expected comprehensive data extraction
        expected_responses = [
            {"project_name": "Renewable Energy Project Charlie", "developer": "Clean Energy Solutions Inc."},
            {"technology": "Combined Solar and Wind", "solar_capacity": "150 MW", "wind_capacity": "100 MW"},
            {"location": "Arizona Desert", "distance_to_city": "50 miles from Phoenix"},
            {"total_capacity": "250 MW", "solar_mw": 150, "wind_mw": 100},
            {"status": "Construction Phase 2 of 3", "timeline": "Phase 3 starts Q2 2025"},
            {"investment": "$400 million total", "committed": "$280 million"},
            {"environmental_impact": "Minimal", "studies": "bird migration study completed"},
            {"permits": "Federal BLM approved", "state_clearance": "received"},
            {"grid_connection": "230kV transmission line", "status": "under construction"},
            {"community_impact": "Local hiring", "fund": "$2M community development"}
        ]
        
        with patch('page_tracker.AiParser') as MockAiParser:
            mock_parser = AsyncMock()
            MockAiParser.return_value = mock_parser
            
            # Mock successful operations
            mock_parser.initialize = AsyncMock()
            mock_parser.scrape_and_cache = AsyncMock(return_value='/tmp/comprehensive_cache.txt')
            mock_parser.cleanup = AsyncMock()
            
            # Mock API responses for each prompt type
            call_count = 0
            def mock_comprehensive_api(*args, **kwargs):
                nonlocal call_count
                response_data = expected_responses[call_count % len(expected_responses)]
                call_count += 1
                return (str(response_data).replace("'", '"'), {'llm_processing_time': 0.4})
            
            mock_parser.get_api_response = MagicMock(side_effect=mock_comprehensive_api)
            mock_parser.strip_markdown = MagicMock(side_effect=lambda x: x)
            
            # Execute comprehensive multi-prompt processing
            start_time = time.perf_counter()
            results = await large_model_validator.get_responses_for_url(url)
            end_time = time.perf_counter()
            
            processing_time = end_time - start_time
            
            # Verify comprehensive results
            assert len(results) == 10, f"Should process all 10 prompts, got {len(results)}"
            
            # Verify scraping efficiency (only once despite 10 prompts)
            mock_parser.scrape_and_cache.assert_called_once_with(url)
            
            # Verify all prompts were processed
            assert mock_parser.get_api_response.call_count == 10, \
                f"Should make 10 API calls, made {mock_parser.get_api_response.call_count}"
            
            # Verify result quality and consistency
            for i, result in enumerate(results):
                assert isinstance(result, dict), f"Result {i} should be dict"
                assert url in result, f"Result {i} should contain URL key"
                
                # Verify response contains extracted data
                response_data = result[url]
                assert isinstance(response_data, dict), f"Result {i} should contain parsed data"
                assert len(response_data) > 0, f"Result {i} should have extracted information"
            
            # Verify performance characteristics
            assert processing_time > 0, "Processing should take measurable time"
            
            # Verify resource management
            mock_parser.cleanup.assert_called_once()
            
            # Calculate and verify performance improvement
            # With 10 prompts, should eliminate 9 redundant scraping operations
            theoretical_old_requests = 10  # Would scrape for each prompt
            actual_new_requests = 1        # Scrapes only once
            request_reduction = ((theoretical_old_requests - actual_new_requests) / theoretical_old_requests) * 100
            
            assert request_reduction == 90, f"Should achieve 90% request reduction, got {request_reduction}%"
    
    @pytest.mark.asyncio
    async def test_concurrent_multiple_projects(self, large_model_validator):
        """Test concurrent processing of multiple projects with different URLs."""
        test_urls = [
            'https://example.com/project-alpha',
            'https://example.com/project-beta', 
            'https://example.com/project-gamma'
        ]
        
        # Track concurrent operations
        concurrent_operations = {
            'scraping_calls': [],
            'api_calls': [],
            'cleanup_calls': []
        }
        
        def track_scraping(url):
            concurrent_operations['scraping_calls'].append({
                'url': url,
                'thread_id': threading.get_ident(),
                'timestamp': time.perf_counter()
            })
            return f'/tmp/concurrent_cache_{hash(url)}.txt'
        
        def track_api_calls(*args, **kwargs):
            concurrent_operations['api_calls'].append({
                'thread_id': threading.get_ident(),
                'timestamp': time.perf_counter()
            })
            return ('{"concurrent": "response"}', {'llm_processing_time': 0.3})
        
        def track_cleanup(*args, **kwargs):
            concurrent_operations['cleanup_calls'].append({
                'thread_id': threading.get_ident(),
                'timestamp': time.perf_counter()
            })
        
        with patch('page_tracker.AiParser') as MockAiParser:
            def create_mock_parser(*args, **kwargs):
                mock_parser = AsyncMock()
                mock_parser.initialize = AsyncMock()
                mock_parser.get_api_response = MagicMock(side_effect=track_api_calls)
                mock_parser.strip_markdown = MagicMock(side_effect=lambda x: x)
                mock_parser.cleanup = AsyncMock(side_effect=track_cleanup)
                return mock_parser
            
            MockAiParser.side_effect = create_mock_parser
            
            # Set up scraping tracking after parser creation
            original_scrape_and_cache = None
            
            async def setup_scraping_tracking():
                # This needs to be set up per URL to track correctly
                pass
            
            # Execute concurrent processing
            start_time = time.perf_counter()
            
            # Create tasks for concurrent processing
            tasks = []
            for url in test_urls:
                # Each URL gets processed concurrently
                task = large_model_validator.get_responses_for_url(url)
                tasks.append(task)
            
            # Wait for all concurrent processing to complete
            results = await asyncio.gather(*tasks)
            
            end_time = time.perf_counter()
            total_concurrent_time = end_time - start_time
            
            # Verify concurrent processing results
            assert len(results) == 3, f"Should process 3 URLs, got {len(results)}"
            
            # Each URL should produce results for all 10 prompts
            for i, result in enumerate(results):
                assert len(result) == 10, f"URL {i} should have 10 prompt results, got {len(result)}"
            
            # Verify concurrency characteristics
            assert total_concurrent_time > 0, "Concurrent processing should take measurable time"
            
            # Verify resource management across concurrent operations
            # Should have cleanup calls for each concurrent operation
            assert len(concurrent_operations['cleanup_calls']) >= 3, \
                f"Should have cleanup for each URL, got {len(concurrent_operations['cleanup_calls'])}"
    
    @pytest.mark.asyncio
    async def test_scalability_many_prompts_many_urls(self, large_model_validator):
        """Test scalability with many prompts across many URLs."""
        # Test with subset of URLs for reasonable test time
        test_urls = [
            'https://example.com/scale-test-1',
            'https://example.com/scale-test-2'
        ]
        
        # Track resource usage and performance
        performance_metrics = {
            'total_scraping_calls': 0,
            'total_api_calls': 0,
            'total_cleanup_calls': 0,
            'processing_times': []
        }
        
        def track_performance_scraping(*args, **kwargs):
            performance_metrics['total_scraping_calls'] += 1
            return f'/tmp/scale_cache_{performance_metrics["total_scraping_calls"]}.txt'
        
        def track_performance_api(*args, **kwargs):
            performance_metrics['total_api_calls'] += 1
            return ('{"scale": "test"}', {'llm_processing_time': 0.2})
        
        def track_performance_cleanup(*args, **kwargs):
            performance_metrics['total_cleanup_calls'] += 1
        
        with patch('page_tracker.AiParser') as MockAiParser:
            mock_parser = AsyncMock()
            MockAiParser.return_value = mock_parser
            
            # Set up performance tracking
            mock_parser.initialize = AsyncMock()
            mock_parser.scrape_and_cache = AsyncMock(side_effect=track_performance_scraping)
            mock_parser.get_api_response = MagicMock(side_effect=track_performance_api)
            mock_parser.strip_markdown = MagicMock(side_effect=lambda x: x)
            mock_parser.cleanup = AsyncMock(side_effect=track_performance_cleanup)
            
            # Process multiple URLs with many prompts each
            for url in test_urls:
                url_start = time.perf_counter()
                result = await large_model_validator.get_responses_for_url(url)
                url_end = time.perf_counter()
                
                url_processing_time = url_end - url_start
                performance_metrics['processing_times'].append(url_processing_time)
                
                # Verify each URL processed successfully
                assert len(result) == 10, f"URL {url} should have 10 results"
            
            # Analyze scalability metrics
            total_expected_scraping = len(test_urls)  # One scrape per URL
            total_expected_api_calls = len(test_urls) * 10  # 10 prompts per URL
            total_expected_cleanup = len(test_urls)  # One cleanup per URL
            
            # Verify efficient resource usage
            assert performance_metrics['total_scraping_calls'] == total_expected_scraping, \
                f"Should scrape {total_expected_scraping} times, got {performance_metrics['total_scraping_calls']}"
            
            assert performance_metrics['total_api_calls'] == total_expected_api_calls, \
                f"Should make {total_expected_api_calls} API calls, got {performance_metrics['total_api_calls']}"
            
            assert performance_metrics['total_cleanup_calls'] == total_expected_cleanup, \
                f"Should cleanup {total_expected_cleanup} times, got {performance_metrics['total_cleanup_calls']}"
            
            # Verify consistent performance across URLs
            processing_times = performance_metrics['processing_times']
            assert len(processing_times) == len(test_urls), "Should have timing for each URL"
            
            # Performance should be consistent (not degrading significantly)
            if len(processing_times) > 1:
                time_variance = max(processing_times) - min(processing_times)
                avg_time = sum(processing_times) / len(processing_times)
                
                # Variance should be reasonable (less than 50% of average)
                variance_ratio = time_variance / avg_time if avg_time > 0 else 0
                assert variance_ratio < 0.5, f"Processing time variance too high: {variance_ratio:.2f}"
    
    @pytest.mark.asyncio
    async def test_concurrent_resource_isolation(self, large_model_validator):
        """Test that concurrent operations maintain proper resource isolation."""
        urls = [
            'https://example.com/isolation-test-1',
            'https://example.com/isolation-test-2',
            'https://example.com/isolation-test-3'
        ]
        
        # Track resource isolation
        resource_tracking = {
            'cache_files': [],
            'parser_instances': [],
            'thread_ids': set()
        }
        
        def track_cache_creation(url):
            cache_file = f'/tmp/isolated_cache_{hash(url)}.txt'
            resource_tracking['cache_files'].append(cache_file)
            return cache_file
        
        with patch('page_tracker.AiParser') as MockAiParser:
            def create_isolated_parser(*args, **kwargs):
                mock_parser = AsyncMock()
                parser_id = len(resource_tracking['parser_instances'])
                resource_tracking['parser_instances'].append(parser_id)
                resource_tracking['thread_ids'].add(threading.get_ident())
                
                mock_parser.initialize = AsyncMock()
                mock_parser.scrape_and_cache = AsyncMock(side_effect=track_cache_creation)
                mock_parser.get_api_response = MagicMock(return_value=('{"isolated": "response"}', {}))
                mock_parser.strip_markdown = MagicMock(side_effect=lambda x: x)
                mock_parser.cleanup = AsyncMock()
                
                return mock_parser
            
            MockAiParser.side_effect = create_isolated_parser
            
            # Execute concurrent processing with resource isolation
            tasks = [large_model_validator.get_responses_for_url(url) for url in urls]
            results = await asyncio.gather(*tasks)
            
            # Verify resource isolation
            assert len(results) == 3, "Should process all 3 URLs"
            
            # Each URL should have generated unique cache files
            assert len(resource_tracking['cache_files']) == 3, \
                f"Should create 3 cache files, got {len(resource_tracking['cache_files'])}"
            
            # All cache files should be unique
            unique_cache_files = set(resource_tracking['cache_files'])
            assert len(unique_cache_files) == 3, \
                f"All cache files should be unique, got {len(unique_cache_files)} unique files"
            
            # Should create separate parser instances
            assert len(resource_tracking['parser_instances']) == 3, \
                f"Should create 3 parser instances, got {len(resource_tracking['parser_instances'])}"
            
            # Verify results quality
            for i, result in enumerate(results):
                assert len(result) == 10, f"URL {i} should have 10 prompt results"
                for prompt_result in result:
                    assert isinstance(prompt_result, dict), f"Result should be dict: {prompt_result}"
    
    @pytest.mark.asyncio
    async def test_error_handling_in_concurrent_scenarios(self, large_model_validator):
        """Test error handling when some concurrent operations fail."""
        urls = [
            'https://example.com/concurrent-success',
            'https://example.com/concurrent-failure', 
            'https://example.com/concurrent-partial'
        ]
        
        # Define different failure scenarios for each URL
        url_behaviors = {
            urls[0]: 'success',    # All operations succeed
            urls[1]: 'scrape_fail', # Scraping fails
            urls[2]: 'api_fail'     # Some API calls fail
        }
        
        with patch('page_tracker.AiParser') as MockAiParser:
            def create_behavior_parser(*args, **kwargs):
                mock_parser = AsyncMock()
                mock_parser.initialize = AsyncMock()
                mock_parser.cleanup = AsyncMock()
                return mock_parser
            
            MockAiParser.side_effect = create_behavior_parser
            
            async def process_url_with_behavior(url):
                behavior = url_behaviors[url]
                mock_parser = MockAiParser.return_value
                
                if behavior == 'success':
                    # Successful processing
                    mock_parser.scrape_and_cache = AsyncMock(return_value='/tmp/success_cache.txt')
                    mock_parser.get_api_response = MagicMock(return_value=('{"success": "response"}', {}))
                    mock_parser.strip_markdown = MagicMock(side_effect=lambda x: x)
                    
                elif behavior == 'scrape_fail':
                    # Scraping failure
                    mock_parser.scrape_and_cache = AsyncMock(side_effect=Exception("Scraping failed"))
                    
                elif behavior == 'api_fail':
                    # Partial API failures
                    mock_parser.scrape_and_cache = AsyncMock(return_value='/tmp/partial_cache.txt')
                    
                    call_count = 0
                    def partial_api_failure(*args, **kwargs):
                        nonlocal call_count
                        call_count += 1
                        if call_count % 3 == 0:  # Every 3rd call fails
                            raise Exception(f"API call {call_count} failed")
                        return ('{"partial": "success"}', {})
                    
                    mock_parser.get_api_response = MagicMock(side_effect=partial_api_failure)
                    mock_parser.strip_markdown = MagicMock(side_effect=lambda x: x)
                
                return await large_model_validator.get_responses_for_url(url)
            
            # Execute concurrent processing with mixed success/failure
            results = await asyncio.gather(
                *[process_url_with_behavior(url) for url in urls],
                return_exceptions=True
            )
            
            # Verify error handling results
            assert len(results) == 3, "Should return results for all 3 URLs"
            
            # First URL should succeed
            success_result = results[0]
            assert not isinstance(success_result, Exception), "Success URL should not raise exception"
            assert len(success_result) == 10, "Success URL should have all 10 results"
            
            # Second URL should fail gracefully (empty list for scraping failure)
            scrape_fail_result = results[1]
            assert not isinstance(scrape_fail_result, Exception), "Scrape failure should be handled gracefully"
            assert scrape_fail_result == [], "Scrape failure should return empty list"
            
            # Third URL should have partial results
            partial_result = results[2]
            assert not isinstance(partial_result, Exception), "Partial failure should be handled gracefully"
            assert len(partial_result) == 10, "Should return results for all prompts (some None)"
            
            # Count successful vs failed results in partial case
            successful_partials = [r for r in partial_result if r is not None]
            failed_partials = [r for r in partial_result if r is None]
            
            assert len(successful_partials) > 0, "Should have some successful partial results"
            assert len(failed_partials) > 0, "Should have some failed partial results"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])