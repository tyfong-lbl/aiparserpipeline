"""
Test suite for cache file reading logic in get_api_response() method.

This test suite verifies the cache file reading functionality added in Step 5.2:
- Content is read correctly from cache file
- File reading errors are handled appropriately  
- Method fails gracefully if cache file path is not set
- Method fails gracefully if cache file doesn't exist
- File encoding (UTF-8) is handled correctly
- Read content is used for API calls correctly
"""

import pytest
import tempfile
import os
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import the modules we're testing
import sys
sys.path.append('/Users/TYFong/code/aiparserpipeline')

from page_tracker import AiParser


class TestCacheFileReading:
    """Test cache file reading logic in get_api_response() method."""

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
        temp_dir = tempfile.mkdtemp(prefix="test_cache_reading_")
        yield Path(temp_dir)
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_read_content_from_cache_file(self, ai_parser, temp_cache_dir):
        """Test that content is read correctly from cache file."""
        # Create test cache file
        cache_file = temp_cache_dir / "test_cache.txt"
        test_content = "This is test cached content.\n\nIt has multiple lines."
        cache_file.write_text(test_content, encoding='utf-8')
        
        # Set cache file path
        ai_parser._cache_file_path = str(cache_file)
        
        # Mock API call to focus on cache reading
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "API response"
        ai_parser.client.chat.completions.create = MagicMock(return_value=mock_response)
        
        # Call method
        response_content, llm_metrics = ai_parser.get_api_response()
        
        # Verify API was called with cached content
        ai_parser.client.chat.completions.create.assert_called_once()
        call_args = ai_parser.client.chat.completions.create.call_args
        message_content = call_args.kwargs['messages'][0]['content']
        
        # The cached content should be included in the API call
        assert test_content in message_content
        assert "Test prompt for Test Project" in message_content

    def test_cache_file_path_not_set_error(self, ai_parser):
        """Test that method fails gracefully if cache file path is not set."""
        # Ensure cache file path is not set
        ai_parser._cache_file_path = None
        
        # Should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            ai_parser.get_api_response()
        
        assert "Cache file path not set" in str(exc_info.value)
        assert "Call scrape_and_cache() first" in str(exc_info.value)

    def test_cache_file_does_not_exist_error(self, ai_parser, temp_cache_dir):
        """Test that method fails gracefully if cache file doesn't exist."""
        # Set cache file path to non-existent file
        non_existent_file = temp_cache_dir / "non_existent.txt"
        ai_parser._cache_file_path = str(non_existent_file)
        
        # Should raise FileNotFoundError
        with pytest.raises(FileNotFoundError) as exc_info:
            ai_parser.get_api_response()
        
        assert "Cache file not found" in str(exc_info.value)
        assert str(non_existent_file) in str(exc_info.value)

    def test_cache_file_read_permission_error(self, ai_parser, temp_cache_dir):
        """Test handling of file permission errors."""
        # Create cache file
        cache_file = temp_cache_dir / "permission_test.txt"
        cache_file.write_text("Test content", encoding='utf-8')
        
        # Set cache file path
        ai_parser._cache_file_path = str(cache_file)
        
        # Mock open to raise PermissionError
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            with pytest.raises(IOError) as exc_info:
                ai_parser.get_api_response()
            
            assert "Error reading cache file" in str(exc_info.value)
            assert "Permission denied" in str(exc_info.value)

    def test_utf8_encoding_handling(self, ai_parser, temp_cache_dir):
        """Test that file encoding (UTF-8) is handled correctly."""
        # Create cache file with unicode content
        cache_file = temp_cache_dir / "unicode_test.txt"
        unicode_content = "Test with unicode: 测试内容 🚀 ünïcødé"
        cache_file.write_text(unicode_content, encoding='utf-8')
        
        # Set cache file path
        ai_parser._cache_file_path = str(cache_file)
        
        # Mock API call
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Unicode response"
        ai_parser.client.chat.completions.create = MagicMock(return_value=mock_response)
        
        # Call method
        response_content, llm_metrics = ai_parser.get_api_response()
        
        # Verify unicode content was read correctly
        call_args = ai_parser.client.chat.completions.create.call_args
        message_content = call_args.kwargs['messages'][0]['content']
        assert unicode_content in message_content

    def test_large_cache_file_handling(self, ai_parser, temp_cache_dir):
        """Test handling of large cache files."""
        # Create large cache file (1MB)
        cache_file = temp_cache_dir / "large_test.txt"
        large_content = "Large content line.\n" * 50000  # ~1MB
        cache_file.write_text(large_content, encoding='utf-8')
        
        # Set cache file path
        ai_parser._cache_file_path = str(cache_file)
        
        # Mock API call
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Large file response"
        ai_parser.client.chat.completions.create = MagicMock(return_value=mock_response)
        
        # Call method - should handle large files without issues
        response_content, llm_metrics = ai_parser.get_api_response()
        
        # Verify large content was processed
        call_args = ai_parser.client.chat.completions.create.call_args
        message_content = call_args.kwargs['messages'][0]['content']
        assert "Large content line." in message_content
        assert len(message_content) > 1000000  # Should be over 1MB

    def test_empty_cache_file_handling(self, ai_parser, temp_cache_dir):
        """Test handling of empty cache files."""
        # Create empty cache file
        cache_file = temp_cache_dir / "empty_test.txt"
        cache_file.write_text("", encoding='utf-8')
        
        # Set cache file path
        ai_parser._cache_file_path = str(cache_file)
        
        # Mock API call
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Empty file response"
        ai_parser.client.chat.completions.create = MagicMock(return_value=mock_response)
        
        # Call method
        response_content, llm_metrics = ai_parser.get_api_response()
        
        # Verify empty content was handled correctly
        call_args = ai_parser.client.chat.completions.create.call_args
        message_content = call_args.kwargs['messages'][0]['content']
        
        # Should contain prompt but no additional content
        assert "Test prompt for Test Project" in message_content
        # The content should essentially be just the prompt + empty string + space
        # Since fulltext is empty, the message should be "Test prompt for Test Project "
        assert message_content == "Test prompt for Test Project "

    def test_disk_read_with_cache_invalidation(self, ai_parser, temp_cache_dir):
        """Test that content can be re-read from disk when memory cache is cleared."""
        # Create cache file
        cache_file = temp_cache_dir / "disk_read_test.txt"
        initial_content = "Initial content"
        cache_file.write_text(initial_content, encoding='utf-8')
        
        # Set cache file path
        ai_parser._cache_file_path = str(cache_file)
        
        # Mock API call
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response"
        ai_parser.client.chat.completions.create = MagicMock(return_value=mock_response)
        
        # First call - loads content into memory cache
        ai_parser.get_api_response()
        first_call_args = ai_parser.client.chat.completions.create.call_args
        first_message = first_call_args.kwargs['messages'][0]['content']
        assert initial_content in first_message
        
        # Reset mock for second call
        ai_parser.client.chat.completions.create.reset_mock()
        
        # Modify cache file content
        updated_content = "Updated content"
        cache_file.write_text(updated_content, encoding='utf-8')
        
        # Clear memory cache to force re-reading from disk
        ai_parser.clear_memory_cache()
        
        # Second call - should read updated content from disk
        ai_parser.get_api_response()
        second_call_args = ai_parser.client.chat.completions.create.call_args
        second_message = second_call_args.kwargs['messages'][0]['content']
        
        # Should contain updated content (proving cache invalidation works)
        assert updated_content in second_message
        assert initial_content not in second_message

    def test_content_used_for_api_call_logic(self, ai_parser, temp_cache_dir):
        """Test that read content is used correctly for existing API call logic."""
        # Create cache file with specific content
        cache_file = temp_cache_dir / "api_logic_test.txt"
        test_content = "Specific test content for API processing"
        cache_file.write_text(test_content, encoding='utf-8')
        
        # Set cache file path
        ai_parser._cache_file_path = str(cache_file)
        
        # Mock API call
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "API processed response"
        ai_parser.client.chat.completions.create = MagicMock(return_value=mock_response)
        
        # Call method
        response_content, llm_metrics = ai_parser.get_api_response()
        
        # Verify API call was made with correct parameters
        ai_parser.client.chat.completions.create.assert_called_once_with(
            model="test_model",
            temperature=0.0,
            messages=[
                {
                    "role": "user",
                    "content": f"Test prompt for Test Project{test_content} "
                }
            ]
        )
        
        # Verify response format is correct
        assert response_content == "API processed response"
        assert isinstance(llm_metrics, dict)
        assert 'llm_response_status' in llm_metrics
        assert 'llm_response_error' in llm_metrics
        assert 'llm_processing_time' in llm_metrics

    def test_error_handling_with_corrupt_cache_file(self, ai_parser, temp_cache_dir):
        """Test handling of corrupted or unreadable cache files."""
        # Create cache file
        cache_file = temp_cache_dir / "corrupt_test.txt"
        cache_file.write_text("Test content", encoding='utf-8')
        
        # Set cache file path
        ai_parser._cache_file_path = str(cache_file)
        
        # Mock file read to raise IOError (simulating corruption)
        with patch('builtins.open') as mock_open:
            mock_open.side_effect = IOError("File is corrupted")
            
            with pytest.raises(IOError) as exc_info:
                ai_parser.get_api_response()
            
            assert "Error reading cache file" in str(exc_info.value)
            assert "File is corrupted" in str(exc_info.value)

    def test_cache_path_validation(self, ai_parser):
        """Test validation of cache file path values."""
        # Test with empty string
        ai_parser._cache_file_path = ""
        with pytest.raises(ValueError):
            ai_parser.get_api_response()
        
        # Test with None
        ai_parser._cache_file_path = None
        with pytest.raises(ValueError):
            ai_parser.get_api_response()
        
        # Test with whitespace only
        ai_parser._cache_file_path = "   "
        # This should attempt to open the file and fail with FileNotFoundError
        with pytest.raises(FileNotFoundError):
            ai_parser.get_api_response()


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])