"""
Test suite for in-memory content caching in get_api_response() method.

This test suite verifies the lazy loading and memory caching functionality added in Step 5.3:
- Content is loaded from disk only on first call
- Subsequent calls use in-memory cached content
- In-memory content matches file content exactly
- Memory cache is properly initialized
- File is not read multiple times for same AiParser instance
- Memory usage is reasonable for large content
- Cache invalidation works if needed
"""

import pytest
import tempfile
import os
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open

# Import the modules we're testing
import sys
sys.path.append('/Users/TYFong/code/aiparserpipeline')

from page_tracker import AiParser


class TestMemoryCaching:
    """Test in-memory content caching in get_api_response() method."""

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
        temp_dir = tempfile.mkdtemp(prefix="test_memory_cache_")
        yield Path(temp_dir)
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_content_loaded_from_disk_only_on_first_call(self, ai_parser, temp_cache_dir):
        """Test that content is loaded from disk only on first call."""
        # Create test cache file
        cache_file = temp_cache_dir / "memory_test.txt"
        test_content = "Test content for memory caching"
        cache_file.write_text(test_content, encoding='utf-8')
        
        # Set cache file path
        ai_parser._cache_file_path = str(cache_file)
        
        # Mock API call
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "API response"
        ai_parser.client.chat.completions.create = MagicMock(return_value=mock_response)
        
        # Track file open calls
        original_open = open
        open_call_count = 0
        
        def counting_open(*args, **kwargs):
            nonlocal open_call_count
            if str(cache_file) in str(args[0]):
                open_call_count += 1
            return original_open(*args, **kwargs)
        
        with patch('builtins.open', side_effect=counting_open):
            # First call - should read from disk
            response1 = ai_parser.get_api_response()
            assert open_call_count == 1
            
            # Second call - should use memory cache (no additional disk read)
            response2 = ai_parser.get_api_response()
            assert open_call_count == 1  # Still only 1 call
            
            # Third call - should still use memory cache
            response3 = ai_parser.get_api_response()
            assert open_call_count == 1  # Still only 1 call
        
        # All calls should return same response content (ignore timing differences in metrics)
        assert response1[0] == response2[0] == response3[0]  # response_content should be identical
        assert response1[1]['llm_response_status'] == response2[1]['llm_response_status'] == response3[1]['llm_response_status']
        assert response1[1]['llm_response_error'] == response2[1]['llm_response_error'] == response3[1]['llm_response_error']

    def test_subsequent_calls_use_in_memory_cached_content(self, ai_parser, temp_cache_dir):
        """Test that subsequent calls use in-memory cached content."""
        # Create test cache file
        cache_file = temp_cache_dir / "memory_test2.txt"
        test_content = "Memory cached content test"
        cache_file.write_text(test_content, encoding='utf-8')
        
        # Set cache file path
        ai_parser._cache_file_path = str(cache_file)
        
        # Mock API call
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Memory response"
        ai_parser.client.chat.completions.create = MagicMock(return_value=mock_response)
        
        # First call - loads from disk and caches in memory
        ai_parser.get_api_response()
        
        # Verify content is now cached in memory
        assert ai_parser._cached_content is not None
        assert ai_parser._cached_content == test_content
        
        # Modify file on disk after first call
        cache_file.write_text("MODIFIED CONTENT", encoding='utf-8')
        
        # Second call - should use in-memory content, ignoring disk changes
        ai_parser.client.chat.completions.create.reset_mock()
        ai_parser.get_api_response()
        
        # Verify API was called with original content (from memory), not modified disk content
        call_args = ai_parser.client.chat.completions.create.call_args
        message_content = call_args.kwargs['messages'][0]['content']
        assert test_content in message_content
        assert "MODIFIED CONTENT" not in message_content

    def test_in_memory_content_matches_file_content_exactly(self, ai_parser, temp_cache_dir):
        """Test that in-memory content matches file content exactly."""
        # Create test cache file with specific content including unicode
        cache_file = temp_cache_dir / "exact_match_test.txt"
        test_content = "Exact content test: 测试 🚀 ünïcødé\nMultiple lines\n\nWith empty lines"
        cache_file.write_text(test_content, encoding='utf-8')
        
        # Set cache file path
        ai_parser._cache_file_path = str(cache_file)
        
        # Mock API call
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Exact match response"
        ai_parser.client.chat.completions.create = MagicMock(return_value=mock_response)
        
        # Make call to trigger loading
        ai_parser.get_api_response()
        
        # Verify in-memory content matches file content exactly
        assert ai_parser._cached_content == test_content
        
        # Verify the exact same content was used for API call
        call_args = ai_parser.client.chat.completions.create.call_args
        message_content = call_args.kwargs['messages'][0]['content']
        assert test_content in message_content

    def test_memory_cache_properly_initialized(self, ai_parser):
        """Test that memory cache is properly initialized."""
        # Initially, cached content should be None
        assert ai_parser._cached_content is None
        
        # After setting cache path but before calling get_api_response, should still be None
        ai_parser._cache_file_path = "/fake/path"
        assert ai_parser._cached_content is None

    def test_file_not_read_multiple_times_same_instance(self, ai_parser, temp_cache_dir):
        """Test that file is not read multiple times for same AiParser instance."""
        # Create test cache file
        cache_file = temp_cache_dir / "single_read_test.txt"
        test_content = "Single read test content"
        cache_file.write_text(test_content, encoding='utf-8')
        
        # Set cache file path
        ai_parser._cache_file_path = str(cache_file)
        
        # Mock API call
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Single read response"
        ai_parser.client.chat.completions.create = MagicMock(return_value=mock_response)
        
        # Mock file operations to count reads
        mock_file_content = mock_open(read_data=test_content)
        
        with patch('builtins.open', mock_file_content):
            # Make multiple calls
            ai_parser.get_api_response()
            ai_parser.get_api_response()
            ai_parser.get_api_response()
            
            # File should only be opened once
            assert mock_file_content.call_count == 1

    def test_memory_usage_reasonable_for_large_content(self, ai_parser, temp_cache_dir):
        """Test that memory usage is reasonable for large content."""
        # Create large test cache file (1MB)
        cache_file = temp_cache_dir / "large_memory_test.txt"
        large_content = "Large content for memory test.\n" * 50000  # ~1MB
        cache_file.write_text(large_content, encoding='utf-8')
        
        # Set cache file path
        ai_parser._cache_file_path = str(cache_file)
        
        # Mock API call
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Large content response"
        ai_parser.client.chat.completions.create = MagicMock(return_value=mock_response)
        
        # Load large content into memory
        ai_parser.get_api_response()
        
        # Verify content is cached in memory
        assert ai_parser._cached_content is not None
        assert len(ai_parser._cached_content) > 1000000  # Should be over 1MB
        assert ai_parser._cached_content == large_content
        
        # Subsequent calls should use cached content efficiently
        ai_parser.client.chat.completions.create.reset_mock()
        ai_parser.get_api_response()
        
        # Verify large content was used from memory
        call_args = ai_parser.client.chat.completions.create.call_args
        message_content = call_args.kwargs['messages'][0]['content']
        assert "Large content for memory test." in message_content

    def test_cache_invalidation_works(self, ai_parser, temp_cache_dir):
        """Test that cache invalidation works correctly."""
        # Create test cache file
        cache_file = temp_cache_dir / "invalidation_test.txt"
        initial_content = "Initial content"
        cache_file.write_text(initial_content, encoding='utf-8')
        
        # Set cache file path
        ai_parser._cache_file_path = str(cache_file)
        
        # Mock API call
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Invalidation response"
        ai_parser.client.chat.completions.create = MagicMock(return_value=mock_response)
        
        # First call - loads and caches content
        ai_parser.get_api_response()
        assert ai_parser._cached_content == initial_content
        
        # Modify file content
        updated_content = "Updated content after invalidation"
        cache_file.write_text(updated_content, encoding='utf-8')
        
        # Clear memory cache (invalidate)
        ai_parser.clear_memory_cache()
        assert ai_parser._cached_content is None
        
        # Next call should read updated content from disk
        ai_parser.client.chat.completions.create.reset_mock()
        ai_parser.get_api_response()
        
        # Verify updated content is now cached and used
        assert ai_parser._cached_content == updated_content
        call_args = ai_parser.client.chat.completions.create.call_args
        message_content = call_args.kwargs['messages'][0]['content']
        assert updated_content in message_content
        assert initial_content not in message_content

    def test_clear_memory_cache_method(self, ai_parser, temp_cache_dir):
        """Test the clear_memory_cache method functionality."""
        # Create test cache file
        cache_file = temp_cache_dir / "clear_cache_test.txt"
        test_content = "Content to be cleared"
        cache_file.write_text(test_content, encoding='utf-8')
        
        # Set cache file path and load content
        ai_parser._cache_file_path = str(cache_file)
        
        # Mock API call
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Clear cache response"
        ai_parser.client.chat.completions.create = MagicMock(return_value=mock_response)
        
        # Load content into memory
        ai_parser.get_api_response()
        assert ai_parser._cached_content is not None
        
        # Clear memory cache
        ai_parser.clear_memory_cache()
        assert ai_parser._cached_content is None
        
        # Calling clear on empty cache should be safe
        ai_parser.clear_memory_cache()  # Should not raise error
        assert ai_parser._cached_content is None

    def test_memory_cache_independent_across_instances(self, temp_cache_dir):
        """Test that memory cache is independent across different AiParser instances."""
        # Create test cache files
        cache_file1 = temp_cache_dir / "instance1_test.txt"
        cache_file2 = temp_cache_dir / "instance2_test.txt"
        content1 = "Content for instance 1"
        content2 = "Content for instance 2"
        cache_file1.write_text(content1, encoding='utf-8')
        cache_file2.write_text(content2, encoding='utf-8')
        
        # Create two AiParser instances
        parser1 = AiParser("key1", "url1", "model1", "prompt1", "project1")
        parser2 = AiParser("key2", "url2", "model2", "prompt2", "project2")
        
        # Set different cache paths
        parser1._cache_file_path = str(cache_file1)
        parser2._cache_file_path = str(cache_file2)
        
        # Mock API calls for both
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Instance response"
        parser1.client.chat.completions.create = MagicMock(return_value=mock_response)
        parser2.client.chat.completions.create = MagicMock(return_value=mock_response)
        
        # Load content in both instances
        parser1.get_api_response()
        parser2.get_api_response()
        
        # Verify each has its own cached content
        assert parser1._cached_content == content1
        assert parser2._cached_content == content2
        assert parser1._cached_content != parser2._cached_content
        
        # Clear cache in one instance - should not affect the other
        parser1.clear_memory_cache()
        assert parser1._cached_content is None
        assert parser2._cached_content == content2

    def test_error_handling_maintained_with_memory_caching(self, ai_parser, temp_cache_dir):
        """Test that existing error handling is maintained with memory caching."""
        # Test case: file doesn't exist
        ai_parser._cache_file_path = str(temp_cache_dir / "nonexistent.txt")
        with pytest.raises(FileNotFoundError):
            ai_parser.get_api_response()
        
        # Memory cache should remain None after error
        assert ai_parser._cached_content is None
        
        # Test case: no cache path set
        ai_parser._cache_file_path = None
        with pytest.raises(ValueError):
            ai_parser.get_api_response()
        
        assert ai_parser._cached_content is None


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])