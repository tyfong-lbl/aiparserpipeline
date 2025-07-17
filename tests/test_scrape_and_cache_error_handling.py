"""
Test suite for scrape_and_cache() method comprehensive error handling.

This test suite verifies that the scrape_and_cache() method handles various
error conditions correctly, including:
- Disk operation failures and retry logic
- Scraping failures without causing file system errors  
- Appropriate error logging for debugging
- Various failure scenarios (disk full, permissions, network issues)
"""

import pytest
import asyncio
import tempfile
import os
import shutil
import logging
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from playwright.async_api import Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError

# Import the modules we're testing
import sys
sys.path.append('/Users/TYFong/code/aiparserpipeline')

from page_tracker import AiParser
from cache_utils import atomic_write_file


class TestScrapeAndCacheErrorHandling:
    """Test comprehensive error handling in scrape_and_cache() method."""

    @pytest.fixture
    def ai_parser(self):
        """Create an AiParser instance for testing."""
        parser = AiParser(
            api_key="test_key",
            api_url="https://test.api.com",
            model="test_model", 
            prompt="Test prompt for $PROJECT",
            project_name="Test Project"
        )
        # Mock the browser initialization
        parser.browser = AsyncMock()
        return parser

    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary directory for cache operations testing."""
        temp_dir = tempfile.mkdtemp(prefix="test_cache_")
        yield Path(temp_dir)
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_disk_write_failure_retries(self, ai_parser, temp_cache_dir):
        """Test that disk write failures trigger retry logic in atomic_write_file."""
        test_url = "https://example.com/test"
        
        # Mock successful scraping
        mock_page = AsyncMock()
        mock_page.title.return_value = "Test Title"
        mock_page.evaluate.return_value = "Test content"
        ai_parser.browser.new_page.return_value = mock_page
        
        # Test the retry logic by calling atomic_write_file directly with mocked file operations
        # This tests that the retry logic in atomic_write_file works correctly
        temp_file = temp_cache_dir / "test_retry.txt"
        
        # Mock tempfile.mkstemp to fail first 2 times, succeed on 3rd
        call_count = 0
        original_mkstemp = tempfile.mkstemp
        
        def mock_mkstemp(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise OSError(f"Simulated disk error - attempt {call_count}")
            else:
                # Use the real function for final success
                return original_mkstemp(*args, **kwargs)
        
        with patch('tempfile.mkstemp', side_effect=mock_mkstemp):
            # Should succeed after retries
            atomic_write_file(str(temp_file), "Test content with retries")
            
            # Verify file was created successfully
            assert temp_file.exists()
            
            # Verify content was written correctly
            content = temp_file.read_text(encoding='utf-8')
            assert content == "Test content with retries"
            
            # Verify retry logic was invoked
            assert call_count == 3

    @pytest.mark.asyncio 
    async def test_disk_write_permanent_failure(self, ai_parser, caplog):
        """Test handling of permanent disk write failures."""
        test_url = "https://example.com/test"
        
        # Mock successful scraping
        mock_page = AsyncMock()
        mock_page.title.return_value = "Test Title"
        mock_page.evaluate.return_value = "Test content"
        ai_parser.browser.new_page.return_value = mock_page
        
        # Mock atomic_write_file to always fail
        def mock_atomic_write_fail(file_path, content):
            raise PermissionError("Permanent disk permission error")
        
        with patch('page_tracker.atomic_write_file', side_effect=mock_atomic_write_fail):
            with caplog.at_level(logging.ERROR):
                # Should still return cache path despite write failure
                cache_path = await ai_parser.scrape_and_cache(test_url)
                
                # Verify cache path is returned (for consistency)
                assert cache_path is not None
                assert "cache_" in cache_path
                
                # Verify error was logged
                assert any("Error writing cache file" in record.message for record in caplog.records)
                assert any("PermissionError" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_scraping_failure_no_file_errors(self, ai_parser, caplog):
        """Test that scraping failures don't cause file system errors."""
        test_url = "https://example.com/test"
        
        # Mock scraping failure
        ai_parser.browser.new_page.side_effect = PlaywrightTimeoutError("Network timeout")
        
        with caplog.at_level(logging.ERROR):
            cache_path = await ai_parser.scrape_and_cache(test_url)
            
            # Should still return cache path
            assert cache_path is not None
            
            # Verify scraping error was logged
            assert any("Error during web scraping" in record.message for record in caplog.records)
            
            # Verify file operations were attempted with empty content
            # The cache file should be created with empty content
            if os.path.exists(cache_path):
                with open(cache_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    assert content == ""  # Empty content due to scraping failure

    @pytest.mark.asyncio
    async def test_browser_page_cleanup_on_error(self, ai_parser):
        """Test that browser pages are properly cleaned up on scraping errors."""
        test_url = "https://example.com/test"
        
        # Mock page that raises error after creation
        mock_page = AsyncMock()
        mock_page.goto.side_effect = PlaywrightError("Page navigation failed")
        ai_parser.browser.new_page.return_value = mock_page
        
        # Execute scrape_and_cache
        cache_path = await ai_parser.scrape_and_cache(test_url)
        
        # Verify page cleanup was attempted
        mock_page.close.assert_called_once()
        
        # Verify cache path is still returned
        assert cache_path is not None

    @pytest.mark.asyncio
    async def test_page_close_error_handled(self, ai_parser):
        """Test that errors during page cleanup are handled gracefully."""
        test_url = "https://example.com/test"
        
        # Mock page that errors on both navigation and close
        mock_page = AsyncMock()
        mock_page.goto.side_effect = PlaywrightError("Navigation failed")
        mock_page.close.side_effect = PlaywrightError("Close failed")
        ai_parser.browser.new_page.return_value = mock_page
        
        # Should not raise exception despite cleanup errors
        cache_path = await ai_parser.scrape_and_cache(test_url)
        assert cache_path is not None

    @pytest.mark.asyncio
    async def test_cache_directory_creation_error(self, ai_parser, caplog):
        """Test handling of cache directory creation failures."""
        test_url = "https://example.com/test"
        
        # Mock successful scraping
        mock_page = AsyncMock()
        mock_page.title.return_value = "Test Title"
        mock_page.evaluate.return_value = "Test content"
        ai_parser.browser.new_page.return_value = mock_page
        
        # Mock directory creation failure
        def mock_atomic_write_dir_fail(file_path, content):
            raise OSError("Cannot create directory - permission denied")
        
        with patch('page_tracker.atomic_write_file', side_effect=mock_atomic_write_dir_fail):
            with caplog.at_level(logging.ERROR):
                cache_path = await ai_parser.scrape_and_cache(test_url)
                
                # Should still return cache path
                assert cache_path is not None
                
                # Verify error was logged
                assert any("Error writing cache file" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_concurrent_scraping_errors(self, ai_parser):
        """Test that concurrent scraping operations handle errors independently."""
        test_urls = [
            "https://example.com/page1",
            "https://example.com/page2", 
            "https://example.com/page3"
        ]
        
        # Mock mixed success/failure scenarios
        call_count = 0
        
        async def mock_new_page():
            nonlocal call_count
            call_count += 1
            mock_page = AsyncMock()
            
            if call_count == 2:
                # Second call fails
                mock_page.goto.side_effect = PlaywrightTimeoutError("Timeout")
            else:
                # Other calls succeed
                mock_page.title.return_value = f"Title {call_count}"
                mock_page.evaluate.return_value = f"Content {call_count}"
            
            return mock_page
        
        ai_parser.browser.new_page.side_effect = mock_new_page
        
        # Run concurrent scraping operations
        tasks = [ai_parser.scrape_and_cache(url) for url in test_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should return cache paths (no exceptions raised)
        assert len(results) == 3
        for result in results:
            assert isinstance(result, str)  # Should be cache path strings
            assert "cache_" in result

    @pytest.mark.asyncio
    async def test_memory_pressure_handling(self, ai_parser):
        """Test handling of memory pressure during large content scraping."""
        test_url = "https://example.com/large-page"
        
        # Mock large content scraping
        large_content = "X" * (10 * 1024 * 1024)  # 10MB of content
        mock_page = AsyncMock()
        mock_page.title.return_value = "Large Page Title"
        mock_page.evaluate.return_value = large_content
        ai_parser.browser.new_page.return_value = mock_page
        
        # Should handle large content without errors
        cache_path = await ai_parser.scrape_and_cache(test_url)
        
        # Verify cache file was created
        assert cache_path is not None
        assert os.path.exists(cache_path)
        
        # Verify content size
        file_size = os.path.getsize(cache_path)
        assert file_size > 10 * 1024 * 1024  # Should be at least 10MB

    @pytest.mark.asyncio
    async def test_unicode_content_error_handling(self, ai_parser):
        """Test handling of unicode content that might cause encoding errors."""
        test_url = "https://example.com/unicode-page"
        
        # Mock unicode content that might cause issues
        unicode_content = "测试内容 🚀 ünïcødé çhåråctërs áccénts"
        mock_page = AsyncMock()
        mock_page.title.return_value = "Unicode Title 测试"
        mock_page.evaluate.return_value = unicode_content
        ai_parser.browser.new_page.return_value = mock_page
        
        # Should handle unicode content correctly
        cache_path = await ai_parser.scrape_and_cache(test_url)
        
        # Verify file was created and content is correct
        assert os.path.exists(cache_path)
        with open(cache_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Unicode Title 测试" in content
            assert unicode_content in content

    @pytest.mark.asyncio
    async def test_network_error_recovery(self, ai_parser, caplog):
        """Test recovery from various network errors."""
        test_url = "https://example.com/network-error"
        
        network_errors = [
            PlaywrightTimeoutError("Request timeout"),
            PlaywrightError("Network error"),
            PlaywrightError("DNS resolution failed")
        ]
        
        for error in network_errors:
            ai_parser.browser.new_page.side_effect = error
            
            with caplog.at_level(logging.ERROR):
                cache_path = await ai_parser.scrape_and_cache(test_url)
                
                # Should return cache path despite network error
                assert cache_path is not None
                
                # Should log the error
                assert any("Error during web scraping" in record.message for record in caplog.records)
            
            # Clear logs for next iteration
            caplog.clear()

    @pytest.mark.asyncio
    async def test_error_logging_format(self, ai_parser, caplog):
        """Test that error logging provides useful debugging information."""
        test_url = "https://example.com/test"
        
        # Mock specific error
        error_message = "Specific network timeout error"
        ai_parser.browser.new_page.side_effect = PlaywrightTimeoutError(error_message)
        
        with caplog.at_level(logging.ERROR):
            await ai_parser.scrape_and_cache(test_url)
            
            # Verify error logging includes useful details
            error_logs = [record for record in caplog.records if record.levelname == 'ERROR']
            assert len(error_logs) > 0
            
            # Check that error message is preserved
            assert any(error_message in record.message for record in error_logs)
            assert any("Error during web scraping" in record.message for record in error_logs)

    @pytest.mark.asyncio
    async def test_file_system_edge_cases(self, ai_parser, caplog):
        """Test various file system edge cases and error conditions."""
        test_url = "https://example.com/test"
        
        # Mock successful scraping
        mock_page = AsyncMock()
        mock_page.title.return_value = "Test Title"
        mock_page.evaluate.return_value = "Test content"
        ai_parser.browser.new_page.return_value = mock_page
        
        # Test various file system errors
        fs_errors = [
            OSError("Disk full"),
            PermissionError("Permission denied"),
            FileNotFoundError("Directory not found"),
            IOError("I/O operation failed")
        ]
        
        for fs_error in fs_errors:
            with patch('page_tracker.atomic_write_file', side_effect=fs_error):
                with caplog.at_level(logging.ERROR):
                    cache_path = await ai_parser.scrape_and_cache(test_url)
                    
                    # Should still return cache path
                    assert cache_path is not None
                    
                    # Should log the file system error
                    assert any("Error writing cache file" in record.message for record in caplog.records)
                    assert any(str(fs_error) in record.message for record in caplog.records)
            
            # Clear logs for next iteration
            caplog.clear()


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])