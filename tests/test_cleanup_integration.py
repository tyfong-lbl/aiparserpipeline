"""
Test suite for cleanup integration into AiParser lifecycle.

This test suite verifies that cache cleanup is properly integrated into
AiParser lifecycle methods and error handling as specified in Step 6.2:
- Cleanup is called when AiParser.cleanup() is called
- Cleanup is called in error handling paths
- Existing browser cleanup still works correctly
- Multiple cleanup calls don't cause issues
- Cleanup works in various error scenarios
- Cache files don't accumulate during testing
"""

import pytest
import tempfile
import asyncio
import shutil
import logging
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock

# Import the modules we're testing
import sys
sys.path.append('/Users/TYFong/code/aiparserpipeline')

from page_tracker import AiParser


class TestCleanupIntegration:
    """Test cleanup integration into AiParser lifecycle."""

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
        return parser

    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary directory for cache file testing."""
        temp_dir = tempfile.mkdtemp(prefix="test_cleanup_integration_")
        yield Path(temp_dir)
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_cleanup_called_when_aiparser_cleanup_called(self, ai_parser, temp_cache_dir):
        """Test that cache cleanup is called when AiParser.cleanup() is called."""
        # Create test cache file
        cache_file = temp_cache_dir / "integration_test.txt"
        test_content = "Cache cleanup integration test"
        cache_file.write_text(test_content, encoding='utf-8')
        
        # Set up cache state
        ai_parser._cache_file_path = str(cache_file)
        ai_parser._cached_content = test_content
        
        # Mock browser cleanup to verify it still works
        ai_parser.browser = MagicMock()
        ai_parser.playwright = MagicMock()
        ai_parser.browser.close = AsyncMock()
        ai_parser.playwright.stop = AsyncMock()
        
        # Verify cache file exists and state is set
        assert cache_file.exists()
        assert ai_parser._cache_file_path is not None
        assert ai_parser._cached_content is not None
        
        # Call AiParser cleanup
        await ai_parser.cleanup()
        
        # Verify cache cleanup occurred
        assert not cache_file.exists()  # File should be deleted
        assert ai_parser._cache_file_path is None  # Path should be reset
        assert ai_parser._cached_content is None  # Memory should be cleared
        
        # Verify browser cleanup still occurred
        ai_parser.browser.close.assert_called_once()
        ai_parser.playwright.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_existing_browser_cleanup_still_works_correctly(self, ai_parser):
        """Test that existing browser cleanup behavior is preserved."""
        # Mock browser and playwright objects
        mock_browser = AsyncMock()
        mock_playwright = AsyncMock()
        ai_parser.browser = mock_browser
        ai_parser.playwright = mock_playwright
        
        # Call cleanup
        await ai_parser.cleanup()
        
        # Verify browser cleanup was called
        mock_browser.close.assert_called_once()
        mock_playwright.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_works_when_no_browser_objects(self, ai_parser, temp_cache_dir):
        """Test that cleanup works correctly when browser objects are None."""
        # Create test cache file
        cache_file = temp_cache_dir / "no_browser_test.txt" 
        test_content = "No browser cleanup test"
        cache_file.write_text(test_content, encoding='utf-8')
        
        # Set up cache state but no browser objects
        ai_parser._cache_file_path = str(cache_file)
        ai_parser._cached_content = test_content
        ai_parser.browser = None
        ai_parser.playwright = None
        
        # Verify initial state
        assert cache_file.exists()
        assert ai_parser._cache_file_path is not None
        
        # Call cleanup - should not raise error
        await ai_parser.cleanup()
        
        # Verify cache cleanup occurred
        assert not cache_file.exists()
        assert ai_parser._cache_file_path is None
        assert ai_parser._cached_content is None

    @pytest.mark.asyncio
    async def test_multiple_cleanup_calls_dont_cause_issues(self, ai_parser, temp_cache_dir):
        """Test that multiple cleanup calls don't cause issues."""
        # Create test cache file
        cache_file = temp_cache_dir / "multiple_cleanup_test.txt"
        test_content = "Multiple cleanup test"
        cache_file.write_text(test_content, encoding='utf-8')
        
        # Set up cache state
        ai_parser._cache_file_path = str(cache_file)
        ai_parser._cached_content = test_content
        
        # Mock browser objects
        ai_parser.browser = AsyncMock()
        ai_parser.playwright = AsyncMock()
        
        # First cleanup call
        await ai_parser.cleanup()
        
        # Verify cleanup worked
        assert not cache_file.exists()
        assert ai_parser._cache_file_path is None
        assert ai_parser._cached_content is None
        
        # Second cleanup call - should not raise error
        await ai_parser.cleanup()
        
        # Third cleanup call - should still not raise error
        await ai_parser.cleanup()
        
        # Browser cleanup should have been called on each cleanup
        assert ai_parser.browser.close.call_count == 3
        assert ai_parser.playwright.stop.call_count == 3

    @pytest.mark.asyncio
    async def test_cleanup_works_in_error_scenarios(self, ai_parser, temp_cache_dir):
        """Test that cleanup works correctly in various error scenarios."""
        # Create test cache file
        cache_file = temp_cache_dir / "error_cleanup_test.txt"
        test_content = "Error scenario cleanup test"
        cache_file.write_text(test_content, encoding='utf-8')
        
        # Set up cache state
        ai_parser._cache_file_path = str(cache_file)
        ai_parser._cached_content = test_content
        
        # Mock browser to raise error during cleanup
        ai_parser.browser = AsyncMock()
        ai_parser.playwright = AsyncMock()
        ai_parser.browser.close.side_effect = Exception("Browser cleanup error")
        ai_parser.playwright.stop.side_effect = Exception("Playwright cleanup error")
        
        # Verify initial state
        assert cache_file.exists()
        
        # Cleanup should not raise errors despite browser cleanup failures
        await ai_parser.cleanup()
        
        # Cache cleanup should still have occurred
        assert not cache_file.exists()
        assert ai_parser._cache_file_path is None
        assert ai_parser._cached_content is None

    @pytest.mark.asyncio
    async def test_cache_files_dont_accumulate_during_testing(self, ai_parser, temp_cache_dir):
        """Test that cache files don't accumulate - they get cleaned up."""
        cache_files = []
        
        # Create multiple cache files and clean them up
        for i in range(5):
            cache_file = temp_cache_dir / f"accumulation_test_{i}.txt"
            test_content = f"Accumulation test content {i}"
            cache_file.write_text(test_content, encoding='utf-8')
            cache_files.append(cache_file)
            
            # Set cache state
            ai_parser._cache_file_path = str(cache_file)
            ai_parser._cached_content = test_content
            
            # Verify file exists
            assert cache_file.exists()
            
            # Cleanup
            await ai_parser.cleanup()
            
            # Verify file was cleaned up
            assert not cache_file.exists()
            assert ai_parser._cache_file_path is None
            assert ai_parser._cached_content is None
        
        # Verify no cache files remain
        for cache_file in cache_files:
            assert not cache_file.exists()

    @pytest.mark.asyncio  
    async def test_cleanup_integration_with_scrape_and_cache_workflow(self, ai_parser, temp_cache_dir):
        """Test cleanup integration with typical scrape and cache workflow."""
        # Create scraped_cache directory within temp_cache_dir for atomic_write_file
        scraped_cache_dir = temp_cache_dir / "scraped_cache"
        scraped_cache_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Mock both the cache directory function and filename generation
            with patch('cache_utils._get_cache_directory') as mock_get_cache_dir, \
                 patch('page_tracker.generate_cache_filename') as mock_generate_filename:
                
                # Make _get_cache_directory return our test directory
                mock_get_cache_dir.return_value = scraped_cache_dir
                
                # Set up cache file path in the scraped_cache directory
                cache_file = scraped_cache_dir / "workflow_test.txt"
                mock_generate_filename.return_value = str(cache_file)
                
                # Mock browser for scraping
                mock_page = AsyncMock()
                mock_page.title.return_value = "Test Title"
                mock_page.evaluate.return_value = "Test content"
                
                ai_parser.browser = AsyncMock()
                ai_parser.browser.new_page.return_value = mock_page
                ai_parser.playwright = AsyncMock()
                
                # Simulate scrape and cache workflow (atomic_write_file will now create the actual file)
                cache_path = await ai_parser.scrape_and_cache("https://test.com")
                
                # Verify cache was set up (cache file should be created by atomic_write_file)
                assert ai_parser._cache_file_path is not None
                assert cache_file.exists()  # Should exist because atomic_write_file actually wrote it
                
                # Now cleanup
                await ai_parser.cleanup()
                
                # Verify complete cleanup
                assert not cache_file.exists()
                assert ai_parser._cache_file_path is None
                assert ai_parser._cached_content is None
        finally:
            # Ensure scraped_cache directory is cleaned up
            if scraped_cache_dir.exists():
                shutil.rmtree(scraped_cache_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_cleanup_preserves_error_handling_behavior(self, ai_parser, temp_cache_dir, caplog):
        """Test that cleanup integration preserves existing error handling behavior."""
        # Create test cache file
        cache_file = temp_cache_dir / "error_handling_test.txt"
        test_content = "Error handling integration test"
        cache_file.write_text(test_content, encoding='utf-8')
        
        # Set up cache state
        ai_parser._cache_file_path = str(cache_file)
        ai_parser._cached_content = test_content
        
        # Mock browser objects with different error scenarios
        ai_parser.browser = AsyncMock()
        ai_parser.playwright = AsyncMock()
        
        # Test scenario 1: Browser close fails
        ai_parser.browser.close.side_effect = ConnectionError("Browser connection lost")
        
        with caplog.at_level(logging.ERROR):
            # Should not raise exception despite browser error
            await ai_parser.cleanup()
        
        # Cache should still be cleaned up
        assert not cache_file.exists()
        assert ai_parser._cache_file_path is None

    @pytest.mark.asyncio
    async def test_cleanup_during_initialization_state(self, ai_parser):
        """Test cleanup behavior when AiParser is in various initialization states."""
        # Test cleanup when nothing is initialized
        await ai_parser.cleanup()  # Should not raise error
        
        # Test cleanup when only browser is set
        ai_parser.browser = AsyncMock()
        await ai_parser.cleanup()
        ai_parser.browser.close.assert_called_once()
        
        # Test cleanup when only playwright is set  
        ai_parser.browser = None
        ai_parser.playwright = AsyncMock()
        await ai_parser.cleanup() 
        ai_parser.playwright.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_method_maintains_async_behavior(self, ai_parser, temp_cache_dir):
        """Test that cleanup method maintains proper async behavior."""
        # Create test cache file
        cache_file = temp_cache_dir / "async_test.txt"
        test_content = "Async behavior test"
        cache_file.write_text(test_content, encoding='utf-8')
        
        # Set up cache state
        ai_parser._cache_file_path = str(cache_file)
        ai_parser._cached_content = test_content
        
        # Mock async browser operations
        ai_parser.browser = AsyncMock()
        ai_parser.playwright = AsyncMock()
        
        # Ensure cleanup is awaitable and works properly
        await ai_parser.cleanup()
        
        # Verify async operations were called
        ai_parser.browser.close.assert_called_once()
        ai_parser.playwright.stop.assert_called_once()
        
        # Verify cache cleanup occurred
        assert not cache_file.exists()
        assert ai_parser._cache_file_path is None

    @pytest.mark.asyncio
    async def test_cleanup_integration_comprehensive_scenario(self, ai_parser, temp_cache_dir):
        """Test comprehensive cleanup integration scenario."""
        # Set up complete AiParser state
        cache_file = temp_cache_dir / "comprehensive_test.txt"
        test_content = "Comprehensive cleanup integration test"
        cache_file.write_text(test_content, encoding='utf-8')
        
        # Set up all state
        ai_parser._cache_file_path = str(cache_file)
        ai_parser._cached_content = test_content
        ai_parser.browser = AsyncMock()
        ai_parser.playwright = AsyncMock()
        
        # Verify initial state
        assert cache_file.exists()
        assert ai_parser._cache_file_path is not None
        assert ai_parser._cached_content is not None
        assert ai_parser.browser is not None
        assert ai_parser.playwright is not None
        
        # Perform cleanup
        await ai_parser.cleanup()
        
        # Verify complete cleanup
        assert not cache_file.exists()          # Cache file removed
        assert ai_parser._cache_file_path is None    # Path reset
        assert ai_parser._cached_content is None     # Memory cleared
        ai_parser.browser.close.assert_called_once()      # Browser cleaned up
        ai_parser.playwright.stop.assert_called_once()    # Playwright cleaned up


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])