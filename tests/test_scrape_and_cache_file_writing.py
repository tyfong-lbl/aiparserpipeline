"""
Tests for scrape_and_cache() file writing integration (Step 4.4 of refactoring).

This module tests the integration of atomic file writing into the 
scrape_and_cache() method:
- Scraped content is written to correct cache file
- File content matches exactly what was scraped
- Atomic write function is used (temp file + rename)
- Cache directory is created if it doesn't exist
- File writing errors are handled appropriately
- Cache file path is returned correctly
- Multiple concurrent writes work safely
"""

import pytest
import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, mock_open
import sys

# Add the parent directory to the path so we can import from the main module
sys.path.insert(0, str(Path(__file__).parent.parent))

from page_tracker import AiParser


class TestScrapeAndCacheFileWriting:
    """Test the atomic file writing integration into scrape_and_cache() method."""
    
    @pytest.mark.asyncio
    async def test_scraped_content_written_to_cache_file(self):
        """Test that scraped content is written to the correct cache file."""
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
        mock_page.title.return_value = "Test Article Title"
        mock_page.evaluate.return_value = "This is the test article content."
        mock_browser.new_page.return_value = mock_page
        ai_parser.browser = mock_browser
        
        # Mock atomic_write_file to capture what gets written
        with patch('page_tracker.atomic_write_file') as mock_write:
            result = await ai_parser.scrape_and_cache("https://example.com/test-article")
            
            # Verify atomic_write_file was called with correct parameters
            mock_write.assert_called_once()
            call_args = mock_write.call_args
            
            # Check file path argument
            written_file_path = call_args[0][0]
            assert written_file_path == result, "File path should match returned result"
            assert written_file_path.endswith(".txt"), "Should write to .txt file"
            assert "scraped_cache" in written_file_path, "Should write to scraped_cache directory"
            
            # Check content argument  
            written_content = call_args[0][1]
            expected_content = "Test Article Title.\n\nThis is the test article content."
            assert written_content == expected_content, "Written content should match scraped content"
    
    @pytest.mark.asyncio
    async def test_file_content_matches_scraped_content_exactly(self):
        """Test that file content matches exactly what was scraped."""
        ai_parser = AiParser(
            api_key="test_key",
            api_url="https://test.api.com",
            model="test_model",
            prompt="Test prompt",
            project_name="Content Test Project"
        )
        
        # Mock browser with specific content
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_page.title.return_value = "Complex Title with Special Characters: !@#$%"
        mock_page.evaluate.return_value = "Complex content with\nmultiple lines\nand special characters: 测试 ünïcødé 🚀"
        mock_browser.new_page.return_value = mock_page
        ai_parser.browser = mock_browser
        
        # Mock atomic_write_file to capture content
        with patch('page_tracker.atomic_write_file') as mock_write:
            await ai_parser.scrape_and_cache("https://example.com/complex-content")
            
            # Verify the exact content that would be written
            written_content = mock_write.call_args[0][1]
            expected_content = "Complex Title with Special Characters: !@#$%.\n\nComplex content with\nmultiple lines\nand special characters: 测试 ünïcødé 🚀"
            
            assert written_content == expected_content, "Content should preserve all characters and formatting"
            assert "\n\n" in written_content, "Should contain title/body separator"
            assert written_content.endswith("🚀"), "Should preserve unicode characters"
    
    @pytest.mark.asyncio
    async def test_atomic_write_function_used(self):
        """Test that the atomic write function is used for file operations."""
        ai_parser = AiParser(
            api_key="test_key",
            api_url="https://test.api.com",
            model="test_model",
            prompt="Test prompt",
            project_name="Atomic Test Project"
        )
        
        # Mock browser
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_page.title.return_value = "Atomic Test Title"
        mock_page.evaluate.return_value = "Atomic test content"
        mock_browser.new_page.return_value = mock_page
        ai_parser.browser = mock_browser
        
        # Verify atomic_write_file is called (not regular file operations)
        with patch('page_tracker.atomic_write_file') as mock_atomic_write:
            with patch('builtins.open', mock_open()) as mock_file_open:
                await ai_parser.scrape_and_cache("https://example.com/atomic-test")
                
                # atomic_write_file should be called
                mock_atomic_write.assert_called_once()
                
                # Regular file open should NOT be called
                mock_file_open.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_cache_directory_creation(self):
        """Test that scraped_cache directory is created if it doesn't exist."""
        ai_parser = AiParser(
            api_key="test_key",
            api_url="https://test.api.com",
            model="test_model",
            prompt="Test prompt",
            project_name="Directory Test Project"
        )
        
        # Mock browser
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_page.title.return_value = "Directory Test"
        mock_page.evaluate.return_value = "Directory test content"
        mock_browser.new_page.return_value = mock_page
        ai_parser.browser = mock_browser
        
        # Mock atomic_write_file to simulate directory creation
        with patch('page_tracker.atomic_write_file') as mock_write:
            result = await ai_parser.scrape_and_cache("https://example.com/directory-test")
            
            # Verify the atomic_write_file function was called
            # (The atomic_write_file function itself handles directory creation)
            mock_write.assert_called_once()
            
            # Verify the path includes the cache directory
            written_path = mock_write.call_args[0][0]
            assert "scraped_cache" in written_path, "Should use scraped_cache directory"
    
    @pytest.mark.asyncio
    async def test_file_writing_error_handling(self):
        """Test that file writing errors are handled appropriately."""
        ai_parser = AiParser(
            api_key="test_key",
            api_url="https://test.api.com",
            model="test_model",
            prompt="Test prompt",
            project_name="Error Test Project"
        )
        
        # Mock browser
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_page.title.return_value = "Error Test"
        mock_page.evaluate.return_value = "Error test content"
        mock_browser.new_page.return_value = mock_page
        ai_parser.browser = mock_browser
        
        # Mock atomic_write_file to raise an error
        with patch('page_tracker.atomic_write_file') as mock_write:
            mock_write.side_effect = OSError("Disk full")
            
            # Should handle the error and still return cache path
            result = await ai_parser.scrape_and_cache("https://example.com/error-test")
            
            # Should still return a cache file path
            assert isinstance(result, str)
            assert result.endswith(".txt")
            assert "scraped_cache" in result
            
            # atomic_write_file should have been attempted
            mock_write.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cache_file_path_returned_correctly(self):
        """Test that cache file path is returned correctly after writing."""
        ai_parser = AiParser(
            api_key="test_key",
            api_url="https://test.api.com",
            model="test_model",
            prompt="Test prompt",
            project_name="Path Test Project"
        )
        
        # Mock browser
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_page.title.return_value = "Path Test"
        mock_page.evaluate.return_value = "Path test content"
        mock_browser.new_page.return_value = mock_page
        ai_parser.browser = mock_browser
        
        # Mock atomic_write_file to succeed
        with patch('page_tracker.atomic_write_file') as mock_write:
            result = await ai_parser.scrape_and_cache("https://example.com/path-test")
            
            # Verify return value is the cache file path
            assert result == ai_parser._cache_file_path, "Should return same path as stored in instance variable"
            
            # Verify the path was used for writing
            written_path = mock_write.call_args[0][0]
            assert written_path == result, "Written path should match returned path"
    
    @pytest.mark.asyncio
    async def test_multiple_concurrent_writes_safe(self):
        """Test that multiple concurrent writes work safely."""
        # Create multiple parser instances for concurrent testing
        parsers = []
        for i in range(3):
            parser = AiParser(
                api_key="test_key",
                api_url="https://test.api.com",
                model="test_model",
                prompt="Test prompt",
                project_name=f"Concurrent Test Project {i}"
            )
            parsers.append(parser)
        
        # Mock browser for all parsers
        for parser in parsers:
            mock_browser = AsyncMock()
            mock_page = AsyncMock()
            mock_page.title.return_value = f"Concurrent Test {parsers.index(parser)}"
            mock_page.evaluate.return_value = f"Concurrent content {parsers.index(parser)}"
            mock_browser.new_page.return_value = mock_page
            parser.browser = mock_browser
        
        # Mock atomic_write_file to track all calls
        with patch('page_tracker.atomic_write_file') as mock_write:
            # Run all scraping operations concurrently
            tasks = [
                parser.scrape_and_cache(f"https://example.com/concurrent-test-{i}")
                for i, parser in enumerate(parsers)
            ]
            results = await asyncio.gather(*tasks)
            
            # Verify all writes were attempted
            assert mock_write.call_count == 3, "Should have attempted 3 writes"
            
            # Verify all results are unique file paths
            assert len(set(results)) == 3, "Should generate unique file paths"
            
            # Verify all results are valid cache paths
            for result in results:
                assert result.endswith(".txt")
                assert "scraped_cache" in result
    
    @pytest.mark.asyncio
    async def test_scraping_error_still_attempts_file_writing(self):
        """Test that scraping errors don't prevent file writing attempt."""
        ai_parser = AiParser(
            api_key="test_key",
            api_url="https://test.api.com",
            model="test_model",
            prompt="Test prompt",
            project_name="Scraping Error Project"
        )
        
        # Mock browser to fail during scraping
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_page.goto.side_effect = Exception("Network timeout")
        mock_browser.new_page.return_value = mock_page
        ai_parser.browser = mock_browser
        
        # Mock atomic_write_file to track if it's called
        with patch('page_tracker.atomic_write_file') as mock_write:
            result = await ai_parser.scrape_and_cache("https://example.com/scraping-error")
            
            # Should still return cache file path
            assert result.endswith(".txt")
            
            # Should still attempt to write (with empty content)
            mock_write.assert_called_once()
            written_content = mock_write.call_args[0][1]
            assert written_content == "", "Should write empty content on scraping error"
    
    @pytest.mark.asyncio
    async def test_file_writing_with_large_content(self):
        """Test file writing with large content to verify no truncation."""
        ai_parser = AiParser(
            api_key="test_key",
            api_url="https://test.api.com",
            model="test_model",
            prompt="Test prompt",
            project_name="Large Content Project"
        )
        
        # Create large content
        large_title = "Very Long Title " * 100  # ~1.7KB title
        large_content = "This is a very long article content. " * 1000  # ~38KB content
        
        # Mock browser with large content
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_page.title.return_value = large_title
        mock_page.evaluate.return_value = large_content
        mock_browser.new_page.return_value = mock_page
        ai_parser.browser = mock_browser
        
        # Mock atomic_write_file to capture large content
        with patch('page_tracker.atomic_write_file') as mock_write:
            await ai_parser.scrape_and_cache("https://example.com/large-content")
            
            # Verify large content is written correctly
            written_content = mock_write.call_args[0][1]
            expected_content = f"{large_title}.\n\n{large_content}"
            
            assert written_content == expected_content, "Large content should be written without truncation"
            assert len(written_content) > 38000, "Content should be properly large"
    
    @pytest.mark.asyncio
    async def test_file_writing_error_logging(self):
        """Test that file writing errors are properly logged."""
        ai_parser = AiParser(
            api_key="test_key",
            api_url="https://test.api.com",
            model="test_model",
            prompt="Test prompt",
            project_name="Logging Test Project"
        )
        
        # Mock browser
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_page.title.return_value = "Logging Test"
        mock_page.evaluate.return_value = "Logging test content"
        mock_browser.new_page.return_value = mock_page
        ai_parser.browser = mock_browser
        
        # Mock atomic_write_file to raise an error
        with patch('page_tracker.atomic_write_file') as mock_write:
            mock_write.side_effect = OSError("Permission denied")
            
            # Mock logger to capture log messages
            with patch('page_tracker.logger') as mock_logger:
                result = await ai_parser.scrape_and_cache("https://example.com/logging-test")
                
                # Should still return result
                assert result.endswith(".txt")
                
                # Should log the file writing error
                mock_logger.error.assert_called()
                error_calls = [call for call in mock_logger.error.call_args_list 
                             if 'Permission denied' in str(call) or 'file' in str(call).lower()]
                assert len(error_calls) > 0, "Should log file writing errors"


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])