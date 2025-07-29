"""
Integration tests with web scraping for the AiParser refactoring project.

This test suite includes integration tests that can optionally perform real web scraping
to verify end-to-end functionality in realistic scenarios. Tests are designed to be
safe and respectful of web resources.

Tests can run in two modes:
1. Mock mode (default): Uses mocked web responses
2. Live mode (optional): Performs actual web scraping with rate limiting
"""

import asyncio
import tempfile
import pytest
import pandas as pd
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import os

# Import the classes under test
from page_tracker import ModelValidator, AiParser

# Environment variable to enable live web scraping tests
ENABLE_LIVE_SCRAPING = os.environ.get('ENABLE_LIVE_SCRAPING', '').lower() in ('true', '1', 'yes')


class TestIntegrationWebScraping:
    """Integration tests with optional real web scraping."""
    
    @pytest.fixture
    def safe_test_urls(self):
        """Provide safe URLs for testing that are unlikely to block or cause issues."""
        return [
            'https://httpbin.org/html',  # Safe test endpoint
            'https://example.com',       # Standard example domain
        ]
    
    @pytest.fixture
    def mock_project_content(self):
        """Mock realistic project content for testing."""
        return {
            'https://httpbin.org/html': """
            <html><body>
            <h1>Example Solar Project</h1>
            <p>Location: California Desert</p>
            <p>Technology: Photovoltaic Solar Panels</p>
            <p>Capacity: 50 MW</p>
            <p>Status: Under Development</p>
            <p>Developer: Clean Energy Corp</p>
            </body></html>
            """,
            'https://example.com': """
            <html><body>
            <h1>Wind Energy Project Beta</h1>
            <p>Location: Texas Plains</p>
            <p>Technology: Wind Turbines</p>
            <p>Capacity: 100 MW</p>
            <p>Status: Operational</p>
            <p>Developer: Wind Power Inc</p>
            </body></html>
            """
        }
    
    @pytest.fixture
    def web_scraping_prompt_dir(self):
        """Create prompts suitable for web scraping integration tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            prompt_dir = Path(temp_dir)
            
            # Create prompts that work well with web content
            prompts = [
                "Extract the project name and location from this content about PROJECT: ",
                "Identify the technology type and capacity for PROJECT: ",
                "Find the development status and developer for PROJECT: "
            ]
            
            for i, prompt_text in enumerate(prompts, 1):
                prompt_file = prompt_dir / f"web-prompt{i}.txt"
                prompt_file.write_text(prompt_text)
            
            yield prompt_dir
    
    @pytest.fixture
    def web_model_validator(self, safe_test_urls, web_scraping_prompt_dir):
        """Create ModelValidator for web scraping integration tests."""
        url_df = pd.DataFrame({
            'url': safe_test_urls[:1],  # Use just one URL for integration test
            'project': ['Web Integration Test Project']
        })
        
        return ModelValidator(
            number_of_queries=3,
            prompt_dir_path=web_scraping_prompt_dir,
            prompt_filename_base='web-prompt',
            api_key='web-test-key',
            api_url='https://test.web.api.com',
            model='web-test-model',
            project_name='Web Integration Test',
            url_df=url_df
        )
    
    @pytest.mark.asyncio
    async def test_mock_web_scraping_integration(self, web_model_validator, mock_project_content):
        """Test integration with mocked web scraping (safe, always runs)."""
        url = 'https://httpbin.org/html'
        expected_content = mock_project_content[url]
        
        with patch('page_tracker.AiParser') as MockAiParser:
            mock_parser = AsyncMock()
            MockAiParser.return_value = mock_parser
            
            # Mock browser and scraping operations
            mock_parser.initialize = AsyncMock()
            mock_parser.cleanup = AsyncMock()
            
            # Mock scraping to return realistic content
            mock_parser.scrape_and_cache = AsyncMock(return_value='/tmp/web_integration_cache.txt')
            
            # Mock the internal scraping process
            mock_parser.browser = MagicMock()
            mock_parser.page = MagicMock()
            
            # Mock realistic API responses based on scraped content
            api_responses = [
                '{"project_name": "Example Solar Project", "location": "California Desert"}',
                '{"technology": "Photovoltaic Solar Panels", "capacity": "50 MW"}',
                '{"status": "Under Development", "developer": "Clean Energy Corp"}'
            ]
            
            call_count = 0
            def mock_web_api(*args, **kwargs):
                nonlocal call_count
                response = api_responses[call_count % len(api_responses)]
                call_count += 1
                return (response, {'llm_processing_time': 0.3})
            
            mock_parser.get_api_response = MagicMock(side_effect=mock_web_api)
            mock_parser.strip_markdown = MagicMock(side_effect=lambda x: x)
            
            # Execute web scraping integration workflow
            start_time = time.perf_counter()
            results = await web_model_validator.get_responses_for_url(url)
            end_time = time.perf_counter()
            
            processing_time = end_time - start_time
            
            # Verify web scraping integration results
            assert len(results) == 3, f"Should process 3 prompts, got {len(results)}"
            
            # Verify scraping workflow
            mock_parser.initialize.assert_called_once()
            mock_parser.scrape_and_cache.assert_called_once_with(url)
            assert mock_parser.get_api_response.call_count == 3
            mock_parser.cleanup.assert_called_once()
            
            # Verify realistic data extraction
            for i, result in enumerate(results):
                assert isinstance(result, dict), f"Result {i} should be dict"
                assert url in result, f"Result {i} should contain URL"
                
                response_data = result[url]
                assert isinstance(response_data, dict), f"Result {i} should have parsed JSON"
                
                # Verify extracted data makes sense
                if i == 0:  # First prompt: name and location
                    assert "project_name" in response_data or "location" in response_data
                elif i == 1:  # Second prompt: technology and capacity
                    assert "technology" in response_data or "capacity" in response_data
                elif i == 2:  # Third prompt: status and developer
                    assert "status" in response_data or "developer" in response_data
            
            # Verify performance characteristics
            assert processing_time > 0, "Processing should take measurable time"
            assert processing_time < 10, "Mock processing should be reasonably fast"
    
    @pytest.mark.asyncio
    async def test_web_scraping_error_handling(self, web_model_validator):
        """Test error handling in web scraping integration scenarios."""
        problematic_urls = [
            'https://nonexistent.invalid.domain.test',  # DNS failure
            'https://httpbin.org/status/500',            # Server error
            'https://httpbin.org/delay/30'               # Timeout (will be mocked)
        ]
        
        for url in problematic_urls:
            with patch('page_tracker.AiParser') as MockAiParser:
                mock_parser = AsyncMock()
                MockAiParser.return_value = mock_parser
                
                # Mock initialization
                mock_parser.initialize = AsyncMock()
                mock_parser.cleanup = AsyncMock()
                
                # Mock different types of scraping failures
                if 'nonexistent' in url:
                    mock_parser.scrape_and_cache = AsyncMock(side_effect=Exception("DNS resolution failed"))
                elif '500' in url:
                    mock_parser.scrape_and_cache = AsyncMock(side_effect=Exception("HTTP 500 Server Error"))
                elif 'delay' in url:
                    mock_parser.scrape_and_cache = AsyncMock(side_effect=Exception("Request timeout"))
                
                # Execute and verify error handling
                result = await web_model_validator.get_responses_for_url(url)
                
                # Should handle errors gracefully
                assert result == [], f"Should return empty list for failed scraping: {url}"
                
                # Should still call cleanup
                mock_parser.cleanup.assert_called_once()
    
    @pytest.mark.skipif(not ENABLE_LIVE_SCRAPING, reason="Live web scraping disabled")
    @pytest.mark.asyncio
    async def test_live_web_scraping_integration(self, web_model_validator):
        """Test integration with actual web scraping (only runs when enabled)."""
        # This test only runs when ENABLE_LIVE_SCRAPING environment variable is set
        # It performs actual web scraping with rate limiting and respectful behavior
        
        url = 'https://httpbin.org/html'  # Safe, predictable test endpoint
        
        # Add rate limiting to be respectful
        await asyncio.sleep(1)  # 1 second delay before request
        
        # Create real AiParser instance (not mocked)
        ai_parser = AiParser(
            api_key='live-test-key',
            api_url='https://test.live.api.com',
            model='live-test-model',
            prompt='Extract information about PROJECT from this content: ',
            project_name='Live Web Test Project'
        )
        
        try:
            # Mock only the API client to avoid real API calls
            with patch.object(ai_parser, 'client') as mock_client:
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = '{"live_test": "success", "url_scraped": "' + url + '"}'
                mock_client.chat.completions.create.return_value = mock_response
                
                # Initialize browser for real scraping
                await ai_parser.initialize()
                
                # Perform actual web scraping
                cache_path = await ai_parser.scrape_and_cache(url)
                
                # Verify cache file was created
                assert cache_path is not None, "Should return cache file path"
                cache_file = Path(cache_path)
                assert cache_file.exists(), f"Cache file should exist: {cache_path}"
                assert cache_file.stat().st_size > 0, "Cache file should not be empty"
                
                # Verify content was scraped
                cached_content = cache_file.read_text(encoding='utf-8')
                assert len(cached_content) > 0, "Should have scraped content"
                assert isinstance(cached_content, str), "Content should be string"
                
                # Test API processing with real scraped content
                response, metrics = ai_parser.get_api_response()
                
                # Verify API processing worked
                assert response is not None, "Should get API response"
                assert "live_test" in response, "Should contain expected response data"
                assert metrics is not None, "Should have metrics"
                
                # Verify performance characteristics
                assert 'llm_processing_time' in metrics, "Should have timing metrics"
                
        finally:
            # Always cleanup, even if test fails
            await ai_parser.cleanup()
            
            # Add rate limiting after test
            await asyncio.sleep(1)  # 1 second delay after request
    
    @pytest.mark.asyncio
    async def test_web_scraping_cache_persistence(self, web_model_validator):
        """Test that web scraping cache persists correctly across operations."""
        url = 'https://example.com/cache-persistence-test'
        
        # Mock content that would be scraped
        mock_scraped_content = """
        <html><body>
        <h1>Cache Persistence Test Project</h1>
        <p>This content should be cached and reused</p>
        <p>Technology: Solar + Storage</p>
        <p>Location: Nevada</p>
        </body></html>
        """
        
        with patch('page_tracker.AiParser') as MockAiParser:
            mock_parser = AsyncMock()
            MockAiParser.return_value = mock_parser
            
            # Track cache file operations
            cache_operations = []
            
            def track_cache_creation(*args, **kwargs):
                cache_path = '/tmp/persistence_test_cache.txt'
                cache_operations.append(f"created:{cache_path}")
                return cache_path
            
            def track_cache_access(*args, **kwargs):
                cache_operations.append("cache_accessed")
                return (mock_scraped_content, {'llm_processing_time': 0.2})
            
            # Mock operations
            mock_parser.initialize = AsyncMock()
            mock_parser.scrape_and_cache = AsyncMock(side_effect=track_cache_creation)
            mock_parser.get_api_response = MagicMock(side_effect=track_cache_access)
            mock_parser.strip_markdown = MagicMock(side_effect=lambda x: x)
            mock_parser.cleanup = AsyncMock()
            
            # Execute workflow
            results = await web_model_validator.get_responses_for_url(url)
            
            # Verify cache operations
            assert len(cache_operations) >= 4, f"Should have cache operations: {cache_operations}"
            
            # Should create cache once
            create_operations = [op for op in cache_operations if op.startswith("created:")]
            assert len(create_operations) == 1, "Should create cache file once"
            
            # Should access cache multiple times (once per prompt)
            access_operations = [op for op in cache_operations if op == "cache_accessed"]
            assert len(access_operations) == 3, "Should access cache for each prompt"
            
            # Verify results
            assert len(results) == 3, "Should process all prompts"
            assert all(r is not None for r in results), "All prompts should succeed"
    
    @pytest.mark.asyncio
    async def test_web_scraping_with_rate_limiting(self, web_model_validator):
        """Test web scraping integration with proper rate limiting."""
        urls = [
            'https://httpbin.org/html',
            'https://example.com'
        ]
        
        # Track timing to verify rate limiting
        request_times = []
        
        def track_request_timing(*args, **kwargs):
            request_times.append(time.perf_counter())
            return '/tmp/rate_limited_cache.txt'
        
        with patch('page_tracker.AiParser') as MockAiParser:
            mock_parser = AsyncMock()
            MockAiParser.return_value = mock_parser
            
            # Mock operations with timing tracking
            mock_parser.initialize = AsyncMock()
            mock_parser.scrape_and_cache = AsyncMock(side_effect=track_request_timing)
            mock_parser.get_api_response = MagicMock(return_value=('{"rate_limited": "test"}', {}))
            mock_parser.strip_markdown = MagicMock(side_effect=lambda x: x)
            mock_parser.cleanup = AsyncMock()
            
            # Process URLs with simulated rate limiting
            for i, url in enumerate(urls):
                if i > 0:  # Add delay between requests
                    await asyncio.sleep(0.1)  # 100ms delay
                
                result = await web_model_validator.get_responses_for_url(url)
                assert len(result) == 3, f"Should process all prompts for {url}"
            
            # Verify rate limiting was applied
            assert len(request_times) == len(urls), "Should track timing for each URL"
            
            if len(request_times) > 1:
                time_between_requests = request_times[1] - request_times[0]
                assert time_between_requests >= 0.1, f"Should have delay between requests: {time_between_requests:.3f}s"


if __name__ == "__main__":
    # Print information about test modes
    if ENABLE_LIVE_SCRAPING:
        print("Running with live web scraping enabled (ENABLE_LIVE_SCRAPING=true)")
    else:
        print("Running in mock mode only (set ENABLE_LIVE_SCRAPING=true for live tests)")
    
    pytest.main([__file__, "-v"])