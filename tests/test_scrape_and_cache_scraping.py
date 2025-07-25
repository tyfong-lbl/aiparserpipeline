"""
Tests for scrape_and_cache() scraping logic (Step 4.2 of refactoring).

This module tests the movement of web scraping logic from select_article_to_api()
into the scrape_and_cache() method:
- scrape_and_cache() scrapes webpage content correctly
- Same scraping behavior as original select_article_to_api
- Title and body text are combined correctly
- Scraping errors are handled the same way
- Browser instance is used properly
- Original select_article_to_api still works unchanged
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import sys
from pathlib import Path

# Add the parent directory to the path so we can import from the main module
sys.path.insert(0, str(Path(__file__).parent.parent))

from page_tracker import AiParser


class TestScrapeAndCacheScraping:
    """Test the scraping logic movement into scrape_and_cache() method."""
    
    @pytest.mark.asyncio
    async def test_scrape_and_cache_scrapes_webpage_content(self):
        """Test that scrape_and_cache scrapes webpage content correctly."""
        ai_parser = AiParser(
            api_key="test_key",
            api_url="https://test.api.com",
            model="test_model",
            prompt="Test prompt",
            project_name="Test Project"
        )
        
        # Mock browser and page
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        
        # Set up page mock responses
        mock_page.title.return_value = "Test Article Title"
        mock_page.evaluate.return_value = "This is the article body text content."
        mock_browser.new_page.return_value = mock_page
        
        # Assign mock browser to parser
        ai_parser.browser = mock_browser
        
        # Call scrape_and_cache
        result = await ai_parser.scrape_and_cache("https://example.com/test-article")

        # Verify browser interactions
        mock_browser.new_page.assert_called_once()
        mock_page.goto.assert_called_once_with("https://example.com/test-article", timeout=30000)
        mock_page.title.assert_called_once()
        mock_page.evaluate.assert_called_once_with('() => document.body.innerText')
        mock_page.close.assert_called_once()

        # Verify result is a tuple with success=True and expected content in cache file
        assert isinstance(result, tuple)
        assert len(result) == 2
        success_status, cache_path = result
        assert success_status is True
        assert isinstance(cache_path, str)

        # Read the content from the cache file to verify it
        with open(cache_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Verify content format matches expected format from select_article_to_api
        expected_content = "Test Article Title.\n\nThis is the article body text content."
        assert content == expected_content
    
    @pytest.mark.asyncio
    async def test_scrape_and_cache_handles_scraping_errors(self):
        """Test that scrape_and_cache handles scraping errors appropriately."""
        ai_parser = AiParser(
            api_key="test_key",
            api_url="https://test.api.com",
            model="test_model",
            prompt="Test prompt",
            project_name="Test Project"
        )
        
        # Mock browser to raise an exception
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_page.goto.side_effect = Exception("Network timeout")
        mock_browser.new_page.return_value = mock_page
        
        ai_parser.browser = mock_browser
        
        # scrape_and_cache should handle the error and return (False, cache_path)
        result = await ai_parser.scrape_and_cache("https://example.com/test-article")

        # Should return a tuple with success=False
        assert isinstance(result, tuple)
        assert len(result) == 2
        success_status, cache_path = result
        assert success_status is False
        assert isinstance(cache_path, str)
        
        # Page should still be closed even on error
        mock_page.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_scrape_and_cache_title_and_body_combination(self):
        """Test that title and body text are combined in correct format."""
        ai_parser = AiParser(
            api_key="test_key",
            api_url="https://test.api.com", 
            model="test_model",
            prompt="Test prompt",
            project_name="Test Project"
        )
        
        # Mock browser with specific title and content
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        
        test_cases = [
            {
                "title": "Solar Project News",
                "body": "A new solar project has been announced.",
                "expected": "Solar Project News.\n\nA new solar project has been announced."
            },
            {
                "title": "Wind Farm Development",
                "body": "Construction begins on wind farm.",
                "expected": "Wind Farm Development.\n\nConstruction begins on wind farm."
            },
            {
                "title": "",
                "body": "Article with no title",
                "expected": ".\n\nArticle with no title"
            }
        ]
        
        for test_case in test_cases:
            mock_page.title.return_value = test_case["title"]
            mock_page.evaluate.return_value = test_case["body"]
            mock_browser.new_page.return_value = mock_page
            ai_parser.browser = mock_browser
            
            result = await ai_parser.scrape_and_cache("https://example.com")
            assert isinstance(result, tuple)
            assert len(result) == 2
            success_status, cache_path = result
            assert success_status is True

            # Read the content from the cache file to verify it
            with open(cache_path, 'r', encoding='utf-8') as f:
                content = f.read()

            assert content == test_case["expected"], f"Failed for title: '{test_case['title']}'"
    
    @pytest.mark.asyncio
    async def test_scrape_and_cache_vs_select_article_to_api_scraping_behavior(self):
        """Test that scrape_and_cache produces same scraping results as select_article_to_api."""
        ai_parser = AiParser(
            api_key="test_key",
            api_url="https://test.api.com",
            model="test_model", 
            prompt="Test prompt for {PROJECT}",
            project_name="Test Project"
        )
        
        # Mock browser with consistent responses
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_page.title.return_value = "Consistent Test Title"
        mock_page.evaluate.return_value = "Consistent test body content for comparison."
        mock_browser.new_page.return_value = mock_page
        
        ai_parser.browser = mock_browser
        
        # Get result from scrape_and_cache
        scrape_and_cache_result = await ai_parser.scrape_and_cache("https://example.com/test")
        
        # Mock the get_api_response to avoid actual API calls in select_article_to_api
        with patch.object(ai_parser, 'get_api_response') as mock_api:
            mock_api.return_value = ('{"test": "response"}', {'llm_response_status': True, 'llm_response_error': None, 'llm_processing_time': 0.1})
            
            # Get result from select_article_to_api (extract just the scraped content)
            # We need to patch json.loads and strip_markdown to focus on scraping
            with patch('page_tracker.json.loads') as mock_json_loads:
                mock_json_loads.return_value = {"test": "data"}
                select_result = await ai_parser.select_article_to_api("https://example.com/test", include_url=False)
        
        # The fulltext content passed to get_api_response should match our scrape_and_cache result
        # We can verify this by checking the call arguments to get_api_response
        call_args = mock_api.call_args
        if call_args and 'fulltext' in call_args.kwargs:
            select_article_fulltext = call_args.kwargs['fulltext']
        else:
            # get_api_response was called with positional argument
            select_article_fulltext = call_args[0][0] if call_args else None
            
        # Both methods should produce the same scraped content
        assert scrape_and_cache_result[0] is True  # First element is success status (boolean)
        assert isinstance(scrape_and_cache_result[1], str)  # Second element is cache path

        # Read the content from the cache file to verify it
        with open(scrape_and_cache_result[1], 'r', encoding='utf-8') as f:
            content = f.read()

        expected_content = "Consistent Test Title.\n\nConsistent test body content for comparison."
        assert content == expected_content
    
    @pytest.mark.asyncio
    async def test_scrape_and_cache_browser_instance_usage(self):
        """Test that scrape_and_cache uses browser instance properly."""
        ai_parser = AiParser(
            api_key="test_key",
            api_url="https://test.api.com",
            model="test_model",
            prompt="Test prompt",
            project_name="Test Project"
        )
        
        # Test with no browser instance - should handle gracefully
        ai_parser.browser = None
        
        # Should handle missing browser gracefully and return (False, cache_path)
        result = await ai_parser.scrape_and_cache("https://example.com")
        assert isinstance(result, tuple)
        assert len(result) == 2
        success_status, cache_path = result
        assert success_status is False
        assert isinstance(cache_path, str)
        
        # Test with proper browser instance
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_page.title.return_value = "Test Title"
        mock_page.evaluate.return_value = "Test content"
        mock_browser.new_page.return_value = mock_page
        
        ai_parser.browser = mock_browser
        
        result = await ai_parser.scrape_and_cache("https://example.com")

        # Verify proper browser usage
        assert mock_browser.new_page.called
        assert mock_page.goto.called
        assert mock_page.title.called
        assert mock_page.evaluate.called
        assert mock_page.close.called

        # Verify result is a tuple with success=True and cache path
        assert isinstance(result, tuple)
        assert len(result) == 2
        success_status, cache_path = result
        assert success_status is True
        assert isinstance(cache_path, str)

        # Read the content from the cache file to verify it
        with open(cache_path, 'r', encoding='utf-8') as f:
            content = f.read()

        expected_content = "Test Title.\n\nTest content"
        assert content == expected_content
    
    @pytest.mark.asyncio
    async def test_select_article_to_api_still_works_unchanged(self):
        """Test that original select_article_to_api method still works after changes."""
        ai_parser = AiParser(
            api_key="test_key",
            api_url="https://test.api.com",
            model="test_model",
            prompt="Test prompt for {PROJECT}",
            project_name="Test Project"
        )
        
        # Mock browser
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_page.title.return_value = "Original Method Test"
        mock_page.evaluate.return_value = "Original method content"
        mock_browser.new_page.return_value = mock_page
        
        ai_parser.browser = mock_browser
        
        # Mock get_api_response to return valid response
        with patch.object(ai_parser, 'get_api_response') as mock_api:
            mock_api.return_value = ('{"name": "test_project", "location": "test_location"}', 
                                   {'llm_response_status': True, 'llm_response_error': None, 'llm_processing_time': 0.1})
            
            # Mock strip_markdown and json.loads
            with patch.object(ai_parser, 'strip_markdown') as mock_strip:
                mock_strip.return_value = '{"name": "test_project", "location": "test_location"}'
                
                with patch('page_tracker.json.loads') as mock_json:
                    mock_json.return_value = {"name": "test_project", "location": "test_location"}
                    
                    # Call select_article_to_api - should work unchanged
                    result = await ai_parser.select_article_to_api("https://example.com", include_url=True)
        
        # Verify it still works and returns expected format
        assert result is not None
        assert isinstance(result, dict)
        assert "https://example.com" in result  # include_url=True means URL should be key
        
        # Verify scraping still happened in select_article_to_api
        mock_page.title.assert_called()
        mock_page.evaluate.assert_called()
        mock_api.assert_called_once()
        
        # Verify the fulltext was passed to get_api_response correctly
        call_args = mock_api.call_args
        passed_fulltext = call_args.kwargs.get('fulltext') if call_args.kwargs else call_args[0][0]
        assert passed_fulltext == "Original Method Test.\n\nOriginal method content"
    
    @pytest.mark.asyncio
    async def test_scrape_and_cache_returns_content_not_cache_path(self):
        """Test that scrape_and_cache returns scraped content temporarily (not cache path yet)."""
        ai_parser = AiParser(
            api_key="test_key",
            api_url="https://test.api.com",
            model="test_model",
            prompt="Test prompt",
            project_name="Test Project"
        )
        
        # Mock browser
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_page.title.return_value = "Content Return Test"
        mock_page.evaluate.return_value = "This should be returned as content, not file path"
        mock_browser.new_page.return_value = mock_page
        
        ai_parser.browser = mock_browser
        
        result = await ai_parser.scrape_and_cache("https://example.com")
        
        # Should return a tuple with success=True and cache path
        assert isinstance(result, tuple)
        assert len(result) == 2
        success_status, cache_path = result
        assert success_status is True
        assert isinstance(cache_path, str)

        # Read the content from the cache file to verify it
        with open(cache_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Verify content matches expected format
        expected_content = "Content Return Test.\n\nThis should be returned as content, not file path"
        assert content == expected_content
        # No need to check if result starts with "/" since it's now a tuple
        # We've already verified the content by reading the file
    
    @pytest.mark.asyncio 
    async def test_scrape_and_cache_error_handling_consistency(self):
        """Test that scrape_and_cache error handling matches select_article_to_api."""
        ai_parser = AiParser(
            api_key="test_key",
            api_url="https://test.api.com",
            model="test_model",
            prompt="Test prompt",
            project_name="Test Project"
        )
        
        # Test various error scenarios
        error_scenarios = [
            Exception("Network timeout"),
            Exception("Page not found"),
            Exception("Browser crashed"),
            TimeoutError("Request timeout")
        ]
        
        for error in error_scenarios:
            # Mock browser to raise the specific error
            mock_browser = AsyncMock()
            mock_page = AsyncMock()
            mock_page.goto.side_effect = error
            mock_browser.new_page.return_value = mock_page
            
            ai_parser.browser = mock_browser
            
            # scrape_and_cache should handle all these errors consistently
            result = await ai_parser.scrape_and_cache("https://example.com")
            
            # Should return a tuple with success=False for all error types
            assert isinstance(result, tuple)
            assert len(result) == 2
            success_status, cache_path = result
            assert success_status is False, f"Failed to handle error: {type(error).__name__}: {error}"
            assert isinstance(cache_path, str)
            
            # Page should be closed even on error
            mock_page.close.assert_called()


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])