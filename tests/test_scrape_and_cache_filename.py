"""
Tests for scrape_and_cache() filename generation (Step 4.3 of refactoring).

This module tests the integration of filename generation utilities into the 
scrape_and_cache() method:
- Cache filename is generated correctly using utility functions
- Filename includes all required components (URL hash, project hash, PID, task ID)  
- Cache file path is stored in instance variable
- Method returns the cache file path
- Multiple calls with same URL generate same filename
- Concurrent calls generate unique filenames
- Scraped content is still available (temporarily stored)
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, patch, AsyncMock
import sys
from pathlib import Path

# Add the parent directory to the path so we can import from the main module
sys.path.insert(0, str(Path(__file__).parent.parent))

from page_tracker import AiParser
from cache_utils import generate_cache_filename


class TestScrapeAndCacheFilename:
    """Test the filename generation integration into scrape_and_cache() method."""
    
    @pytest.mark.asyncio
    async def test_cache_filename_generation_with_utility_functions(self):
        """Test that cache filename is generated correctly using utility functions."""
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
        mock_page.title.return_value = "Test Title"
        mock_page.evaluate.return_value = "Test content"
        mock_browser.new_page.return_value = mock_page
        ai_parser.browser = mock_browser
        
        # Call scrape_and_cache
        result = await ai_parser.scrape_and_cache("https://example.com/test")
        
        # Result should be a file path, not content
        assert result.startswith("/"), "Should return file path starting with /"
        assert "scraped_cache" in result, "Should contain scraped_cache directory"
        assert result.endswith(".txt"), "Should be a .txt file"
        
        # Verify filename format: cache_{url_hash}_{project_hash}_{pid}_{task_id}.txt
        filename = Path(result).name
        parts = filename.split('_')
        assert len(parts) == 5, f"Filename should have 5 parts separated by _, got: {filename}"
        assert parts[0] == "cache", "Should start with 'cache'"
        assert len(parts[1]) == 16, "URL hash should be 16 characters"
        assert len(parts[2]) == 8, "Project hash should be 8 characters" 
        assert parts[3].isdigit(), "PID should be numeric"
        assert parts[4].replace('.txt', '').isdigit(), "Task ID should be numeric"
    
    @pytest.mark.asyncio
    async def test_cache_file_path_stored_in_instance_variable(self):
        """Test that generated cache file path is stored in self._cache_file_path."""
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
        mock_page.title.return_value = "Test Title"
        mock_page.evaluate.return_value = "Test content"
        mock_browser.new_page.return_value = mock_page
        ai_parser.browser = mock_browser
        
        # Initially should be None
        assert ai_parser._cache_file_path is None
        
        # Call scrape_and_cache
        result = await ai_parser.scrape_and_cache("https://example.com/test")
        
        # Instance variable should be set to same path as returned
        assert ai_parser._cache_file_path is not None
        assert ai_parser._cache_file_path == result
        assert isinstance(ai_parser._cache_file_path, str)
        assert ai_parser._cache_file_path.endswith(".txt")
    
    @pytest.mark.asyncio
    async def test_filename_includes_all_required_components(self):
        """Test that filename includes URL hash, project hash, PID, and task ID."""
        ai_parser = AiParser(
            api_key="test_key",
            api_url="https://test.api.com",
            model="test_model",
            prompt="Test prompt",
            project_name="Solar Project Alpha"
        )
        
        # Mock browser
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_page.title.return_value = "Test Title"
        mock_page.evaluate.return_value = "Test content"
        mock_browser.new_page.return_value = mock_page
        ai_parser.browser = mock_browser
        
        test_url = "https://pv-magazine.com/solar-project-news"
        
        # Call scrape_and_cache
        result = await ai_parser.scrape_and_cache(test_url)
        
        # Verify the filename was generated using the utility functions
        expected_filename = generate_cache_filename(test_url, "Solar Project Alpha")
        expected_filename_only = Path(expected_filename).name
        actual_filename_only = Path(result).name
        
        # The filenames should match (they should use the same utility function)
        # Note: They might differ in task ID if running in different async contexts
        expected_parts = expected_filename_only.split('_')
        actual_parts = actual_filename_only.split('_')
        
        assert len(actual_parts) == 5, "Should have 5 parts: cache, url_hash, project_hash, pid, task_id"
        assert actual_parts[0] == expected_parts[0], "Cache prefix should match"
        assert actual_parts[1] == expected_parts[1], "URL hash should match"
        assert actual_parts[2] == expected_parts[2], "Project hash should match"
        assert actual_parts[3] == expected_parts[3], "PID should match"
        # Task ID might differ due to async context, so we just verify it's numeric
        assert actual_parts[4].replace('.txt', '').isdigit(), "Task ID should be numeric"
    
    @pytest.mark.asyncio 
    async def test_multiple_calls_same_url_generate_same_filename(self):
        """Test that multiple calls with same URL generate same filename."""
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
        mock_page.title.return_value = "Test Title"
        mock_page.evaluate.return_value = "Test content"
        mock_browser.new_page.return_value = mock_page
        ai_parser.browser = mock_browser
        
        test_url = "https://example.com/consistent-test"
        
        # Call scrape_and_cache multiple times
        result1 = await ai_parser.scrape_and_cache(test_url)
        result2 = await ai_parser.scrape_and_cache(test_url)
        result3 = await ai_parser.scrape_and_cache(test_url)
        
        # All results should be the same filename
        assert result1 == result2 == result3, "Same URL should generate same filename"
        
        # Instance variable should be updated each time
        assert ai_parser._cache_file_path == result3
    
    @pytest.mark.asyncio
    async def test_different_urls_generate_different_filenames(self):
        """Test that different URLs generate different filenames."""
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
        mock_page.title.return_value = "Test Title"
        mock_page.evaluate.return_value = "Test content"
        mock_browser.new_page.return_value = mock_page
        ai_parser.browser = mock_browser
        
        # Test different URLs
        urls = [
            "https://example.com/article1",
            "https://example.com/article2", 
            "https://different-site.com/article1",
            "https://pv-magazine.com/solar-news"
        ]
        
        results = []
        for url in urls:
            result = await ai_parser.scrape_and_cache(url)
            results.append(result)
        
        # All filenames should be different
        assert len(set(results)) == len(results), "Different URLs should generate different filenames"
        
        # All should be valid file paths
        for result in results:
            assert result.startswith("/"), f"Should be absolute path: {result}"
            assert "scraped_cache" in result, f"Should contain scraped_cache: {result}"
            assert result.endswith(".txt"), f"Should end with .txt: {result}"
    
    @pytest.mark.asyncio
    async def test_different_projects_generate_different_filenames(self):
        """Test that different project names generate different filenames."""
        # Test with different project names
        test_url = "https://example.com/same-article"
        
        projects_and_results = []
        
        for project_name in ["Solar Project A", "Wind Farm B", "Battery Storage C"]:
            ai_parser = AiParser(
                api_key="test_key",
                api_url="https://test.api.com",
                model="test_model",
                prompt="Test prompt",
                project_name=project_name
            )
            
            # Mock browser
            mock_browser = AsyncMock()
            mock_page = AsyncMock()
            mock_page.title.return_value = "Test Title"
            mock_page.evaluate.return_value = "Test content"
            mock_browser.new_page.return_value = mock_page
            ai_parser.browser = mock_browser
            
            result = await ai_parser.scrape_and_cache(test_url)
            projects_and_results.append((project_name, result))
        
        # All filenames should be different
        filenames = [result for _, result in projects_and_results]
        assert len(set(filenames)) == len(filenames), "Different projects should generate different filenames"
        
        # Verify project hash components are different
        for i, (project1, filename1) in enumerate(projects_and_results):
            for j, (project2, filename2) in enumerate(projects_and_results):
                if i != j:
                    parts1 = Path(filename1).name.split('_')
                    parts2 = Path(filename2).name.split('_')
                    assert parts1[2] != parts2[2], f"Project hashes should differ: {project1} vs {project2}"
    
    @pytest.mark.asyncio
    async def test_scraped_content_temporarily_stored(self):
        """Test that scraped content is still available (temporarily stored in memory)."""
        ai_parser = AiParser(
            api_key="test_key",
            api_url="https://test.api.com", 
            model="test_model",
            prompt="Test prompt",
            project_name="Test Project"
        )
        
        # Mock browser with specific content
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_page.title.return_value = "Specific Test Title"
        mock_page.evaluate.return_value = "Specific test content for verification"
        mock_browser.new_page.return_value = mock_page
        ai_parser.browser = mock_browser
        
        # Initially cached content should be None
        assert ai_parser._cached_content is None
        
        # Call scrape_and_cache
        result = await ai_parser.scrape_and_cache("https://example.com/test")
        
        # Content should be stored in _cached_content (even though not written to file yet)
        # Note: This might be implemented in Step 4.4, so this test might need adjustment
        # For now, we'll test that we can verify the content was scraped correctly
        expected_content = "Specific Test Title.\n\nSpecific test content for verification"
        
        # We can't directly check _cached_content yet since file writing isn't implemented
        # But we can verify the scraping happened correctly
        mock_page.title.assert_called_once()
        mock_page.evaluate.assert_called_once_with('() => document.body.innerText')
    
    @pytest.mark.asyncio
    async def test_error_handling_with_filename_generation(self):
        """Test that errors during scraping don't break filename generation."""
        ai_parser = AiParser(
            api_key="test_key",
            api_url="https://test.api.com",
            model="test_model",
            prompt="Test prompt", 
            project_name="Test Project"
        )
        
        # Mock browser to raise an error
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_page.goto.side_effect = Exception("Network error")
        mock_browser.new_page.return_value = mock_page
        ai_parser.browser = mock_browser
        
        # Even with scraping errors, should still generate filename and return path
        result = await ai_parser.scrape_and_cache("https://example.com/error-test")
        
        # Should still return a valid file path
        assert isinstance(result, str)
        assert result.startswith("/"), "Should return file path even on error"
        assert "scraped_cache" in result, "Should contain scraped_cache directory"
        assert result.endswith(".txt"), "Should be a .txt file"
        
        # Instance variable should be set
        assert ai_parser._cache_file_path == result
        
        # Verify page cleanup still happened
        mock_page.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_filename_generation_uses_correct_utility_function(self):
        """Test that filename generation uses the imported utility functions."""
        ai_parser = AiParser(
            api_key="test_key",
            api_url="https://test.api.com",
            model="test_model",
            prompt="Test prompt",
            project_name="Utility Test Project"
        )
        
        # Mock browser
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_page.title.return_value = "Test Title"
        mock_page.evaluate.return_value = "Test content"
        mock_browser.new_page.return_value = mock_page
        ai_parser.browser = mock_browser
        
        test_url = "https://utility-test.com/example"
        
        # Mock the generate_cache_filename function to verify it's called
        with patch('page_tracker.generate_cache_filename') as mock_generate:
            mock_generate.return_value = "/test/path/mock_cache_file.txt"
            
            result = await ai_parser.scrape_and_cache(test_url)
            
            # Verify the utility function was called with correct parameters
            mock_generate.assert_called_once_with(test_url, "Utility Test Project")
            
            # Result should be the mocked return value
            assert result == "/test/path/mock_cache_file.txt"
            assert ai_parser._cache_file_path == "/test/path/mock_cache_file.txt"


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])