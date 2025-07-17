"""
Test suite for cleanup_cache_file() method.

This test suite verifies the cache file cleanup functionality added in Step 6.1:
- Cache file is deleted from disk if it exists
- In-memory cached content is cleared
- Method handles case where cache file doesn't exist
- Method handles file deletion errors gracefully
- Multiple calls to cleanup are safe
- Method works when cache was never created
- Appropriate logging for cleanup operations
"""

import pytest
import tempfile
import os
import shutil
import stat
import logging
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import the modules we're testing
import sys
sys.path.append('/Users/TYFong/code/aiparserpipeline')

from page_tracker import AiParser


class TestCleanupCacheFile:
    """Test cleanup_cache_file() method functionality."""

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
        temp_dir = tempfile.mkdtemp(prefix="test_cleanup_")
        yield Path(temp_dir)
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_cache_file_deleted_from_disk_if_exists(self, ai_parser, temp_cache_dir):
        """Test that cache file is deleted from disk if it exists."""
        # Create test cache file
        cache_file = temp_cache_dir / "test_cleanup.txt"
        test_content = "Test content for cleanup"
        cache_file.write_text(test_content, encoding='utf-8')
        
        # Set up AiParser with cache
        ai_parser._cache_file_path = str(cache_file)
        ai_parser._cached_content = test_content
        
        # Verify file exists before cleanup
        assert cache_file.exists()
        assert ai_parser._cache_file_path is not None
        assert ai_parser._cached_content is not None
        
        # Perform cleanup
        ai_parser.cleanup_cache_file()
        
        # Verify file was deleted
        assert not cache_file.exists()
        
        # Verify cache state was reset
        assert ai_parser._cache_file_path is None
        assert ai_parser._cached_content is None

    def test_in_memory_cached_content_is_cleared(self, ai_parser, temp_cache_dir):
        """Test that in-memory cached content is cleared."""
        # Set up in-memory cache without file
        test_content = "In-memory test content"
        ai_parser._cached_content = test_content
        ai_parser._cache_file_path = None
        
        # Verify content is cached
        assert ai_parser._cached_content == test_content
        
        # Perform cleanup
        ai_parser.cleanup_cache_file()
        
        # Verify content was cleared
        assert ai_parser._cached_content is None

    def test_handles_case_where_cache_file_doesnt_exist(self, ai_parser, temp_cache_dir, caplog):
        """Test that method handles case where cache file doesn't exist."""
        # Set cache path to non-existent file
        non_existent_file = temp_cache_dir / "non_existent.txt"
        ai_parser._cache_file_path = str(non_existent_file)
        ai_parser._cached_content = "Some content"
        
        # Verify file doesn't exist
        assert not non_existent_file.exists()
        
        with caplog.at_level(logging.DEBUG):
            # Perform cleanup - should not raise error
            ai_parser.cleanup_cache_file()
        
        # Verify state was still reset
        assert ai_parser._cache_file_path is None
        assert ai_parser._cached_content is None
        
        # Verify appropriate logging
        assert any("Cache file does not exist" in record.message for record in caplog.records)

    def test_handles_file_deletion_errors_gracefully(self, ai_parser, temp_cache_dir, caplog):
        """Test that method handles file deletion errors gracefully."""
        # Create test cache file
        cache_file = temp_cache_dir / "permission_test.txt"
        cache_file.write_text("Test content", encoding='utf-8')
        
        # Set up AiParser
        ai_parser._cache_file_path = str(cache_file)
        ai_parser._cached_content = "Test content"
        
        # Make file read-only to simulate permission error
        cache_file.chmod(stat.S_IRUSR)  # Read-only for owner
        
        with caplog.at_level(logging.ERROR):
            # Perform cleanup - should not raise error
            ai_parser.cleanup_cache_file()
        
        # Should have logged the error but continued
        error_logs = [record for record in caplog.records if record.levelname == 'ERROR']
        assert any("Permission denied" in record.message or "OS error" in record.message for record in error_logs)
        
        # Memory should still be cleared even if file deletion failed
        assert ai_parser._cached_content is None
        assert ai_parser._cache_file_path is None
        
        # Clean up - restore permissions for teardown
        try:
            cache_file.chmod(stat.S_IWUSR | stat.S_IRUSR)
            cache_file.unlink()
        except:
            pass  # Best effort cleanup

    def test_multiple_calls_to_cleanup_are_safe(self, ai_parser, temp_cache_dir):
        """Test that multiple calls to cleanup are safe."""
        # Create test cache file
        cache_file = temp_cache_dir / "multiple_cleanup_test.txt"
        cache_file.write_text("Test content", encoding='utf-8')
        
        # Set up AiParser
        ai_parser._cache_file_path = str(cache_file)
        ai_parser._cached_content = "Test content"
        
        # First cleanup
        ai_parser.cleanup_cache_file()
        
        # Verify cleanup worked
        assert not cache_file.exists()
        assert ai_parser._cache_file_path is None
        assert ai_parser._cached_content is None
        
        # Second cleanup - should not raise error
        ai_parser.cleanup_cache_file()
        
        # Third cleanup - should still not raise error
        ai_parser.cleanup_cache_file()
        
        # State should remain clean
        assert ai_parser._cache_file_path is None
        assert ai_parser._cached_content is None

    def test_works_when_cache_was_never_created(self, ai_parser, caplog):
        """Test that method works when cache was never created."""
        # Ensure no cache was ever created
        assert ai_parser._cache_file_path is None
        assert ai_parser._cached_content is None
        
        with caplog.at_level(logging.DEBUG):
            # Perform cleanup - should work fine
            ai_parser.cleanup_cache_file()
        
        # State should remain None
        assert ai_parser._cache_file_path is None
        assert ai_parser._cached_content is None
        
        # Should have logged that no cleanup was needed
        assert any("No cache file path set" in record.message for record in caplog.records)

    def test_appropriate_logging_for_cleanup_operations(self, ai_parser, temp_cache_dir, caplog):
        """Test that appropriate logging occurs for cleanup operations."""
        # Create test cache file
        cache_file = temp_cache_dir / "logging_test.txt"
        test_content = "Logging test content"
        cache_file.write_text(test_content, encoding='utf-8')
        
        # Set up AiParser
        ai_parser._cache_file_path = str(cache_file)
        ai_parser._cached_content = test_content
        
        with caplog.at_level(logging.DEBUG):
            # Perform cleanup
            ai_parser.cleanup_cache_file()
        
        # Verify comprehensive logging
        log_messages = [record.message for record in caplog.records]
        
        # Should log successful file removal
        assert any("Successfully removed cache file" in msg for msg in log_messages)
        
        # Should log memory content clearing
        assert any("Cleared in-memory cached content" in msg for msg in log_messages)
        
        # Should log cache path reset
        assert any("Reset cache file path" in msg for msg in log_messages)
        
        # Should have summary log
        info_logs = [record for record in caplog.records if record.levelname == 'INFO']
        assert any("Cache cleanup completed" in record.message for record in info_logs)

    def test_file_size_logging(self, ai_parser, temp_cache_dir, caplog):
        """Test that file size is logged during cleanup."""
        # Create test cache file with known content
        cache_file = temp_cache_dir / "size_test.txt"
        test_content = "X" * 1000  # 1000 bytes
        cache_file.write_text(test_content, encoding='utf-8')
        
        # Set up AiParser
        ai_parser._cache_file_path = str(cache_file)
        ai_parser._cached_content = test_content
        
        with caplog.at_level(logging.INFO):
            # Perform cleanup
            ai_parser.cleanup_cache_file()
        
        # Verify file size was logged
        info_logs = [record.message for record in caplog.records if "Cache cleanup completed" in record.message]
        assert len(info_logs) > 0
        
        # Should mention file size in bytes
        assert any("1000 bytes" in msg for msg in info_logs)

    def test_non_file_path_handling(self, ai_parser, temp_cache_dir, caplog):
        """Test handling when cache path points to a directory instead of file."""
        # Create a directory at the cache path
        cache_dir = temp_cache_dir / "cache_directory"
        cache_dir.mkdir()
        
        # Set up AiParser with directory path
        ai_parser._cache_file_path = str(cache_dir)
        ai_parser._cached_content = "Test content"
        
        with caplog.at_level(logging.WARNING):
            # Perform cleanup
            ai_parser.cleanup_cache_file()
        
        # Should log warning about non-file path
        warning_logs = [record for record in caplog.records if record.levelname == 'WARNING']
        assert any("Cache path exists but is not a file" in record.message for record in warning_logs)
        
        # Should still clear memory and reset path
        assert ai_parser._cached_content is None
        assert ai_parser._cache_file_path is None
        
        # Directory should still exist (not deleted)
        assert cache_dir.exists()

    def test_error_during_memory_clearing(self, ai_parser, caplog):
        """Test handling of errors during memory clearing."""
        # Set up cache state
        ai_parser._cache_file_path = "/fake/path"
        ai_parser._cached_content = "Test content"
        
        # Mock the memory clearing to raise an error
        with patch.object(ai_parser, '_cached_content', 
                         new_callable=lambda: MagicMock(side_effect=Exception("Memory error"))):
            with caplog.at_level(logging.ERROR):
                # Perform cleanup
                ai_parser.cleanup_cache_file()
        
        # Should log the error
        error_logs = [record for record in caplog.records if record.levelname == 'ERROR']
        assert any("Error clearing in-memory cache" in record.message for record in error_logs)

    def test_error_during_path_reset(self, ai_parser, temp_cache_dir, caplog):
        """Test handling of errors during cache path reset."""
        # Create and set up cache file
        cache_file = temp_cache_dir / "path_reset_test.txt"
        cache_file.write_text("Test content", encoding='utf-8')
        ai_parser._cache_file_path = str(cache_file)
        
        # This test is more theoretical since path reset is simple assignment
        # But we ensure the method structure handles potential errors
        with caplog.at_level(logging.DEBUG):
            ai_parser.cleanup_cache_file()
        
        # Normal operation should complete successfully
        assert ai_parser._cache_file_path is None
        assert not cache_file.exists()

    def test_comprehensive_cleanup_integration(self, ai_parser, temp_cache_dir):
        """Test comprehensive cleanup integration scenario."""
        # Set up complex cache state
        cache_file = temp_cache_dir / "comprehensive_test.txt"
        test_content = "Comprehensive cleanup test content"
        cache_file.write_text(test_content, encoding='utf-8')
        
        ai_parser._cache_file_path = str(cache_file)
        ai_parser._cached_content = test_content
        
        # Verify initial state
        assert cache_file.exists()
        assert ai_parser._cache_file_path is not None
        assert ai_parser._cached_content is not None
        
        # Perform comprehensive cleanup
        ai_parser.cleanup_cache_file()
        
        # Verify complete cleanup
        assert not cache_file.exists()                    # File removed from disk
        assert ai_parser._cache_file_path is None         # Path reset
        assert ai_parser._cached_content is None          # Memory cleared
        
        # Subsequent operations should work correctly
        # (This would be tested in integration with other methods)


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])