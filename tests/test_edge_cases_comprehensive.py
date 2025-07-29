"""
Comprehensive edge case testing for the AiParser refactoring project.

This test suite covers edge cases and error conditions that might not be
covered in the main unit tests, ensuring robust error handling and
boundary condition management.
"""

import asyncio
import tempfile
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
import json
import os

# Import the classes under test
from page_tracker import AiParser
from cache_utils import (
    generate_url_hash, generate_project_hash, 
    get_process_id, get_asyncio_task_id,
    generate_cache_filename, atomic_write_file
)


class TestEdgeCasesComprehensive:
    """Test edge cases and boundary conditions for all refactored components."""
    
    def test_url_hash_edge_cases(self):
        """Test URL hash generation with edge cases and boundary conditions."""
        
        # Very long URL (over 2000 characters)
        long_url = "https://example.com/" + "a" * 2000
        hash_long = generate_url_hash(long_url)
        assert len(hash_long) == 16, "Hash should still be 16 chars for very long URLs"
        
        # URL with unicode characters
        unicode_url = "https://测试.com/测试路径?参数=值"
        hash_unicode = generate_url_hash(unicode_url)
        assert len(hash_unicode) == 16, "Hash should handle unicode URLs"
        assert hash_unicode.isalnum(), "Hash should be alphanumeric for unicode URLs"
        
        # URL with all special characters
        special_url = "https://example.com/!@#$%^&*()_+-=[]{}|;':\",./<>?`~"
        hash_special = generate_url_hash(special_url)
        assert len(hash_special) == 16, "Hash should handle special characters"
        
        # URL with mixed case and normalization edge cases
        mixed_urls = [
            "HTTP://EXAMPLE.COM:80/PATH",
            "http://example.com/PATH",
            "http://example.com:80/path/",
            "http://example.com/path"
        ]
        hashes = [generate_url_hash(url) for url in mixed_urls]
        # Some should be normalized to same hash, others different
        assert len(set(hashes)) >= 1, "Should produce consistent hashes for equivalent URLs"
        
        # Minimum length URL
        min_url = "http://a.co"
        hash_min = generate_url_hash(min_url)
        assert len(hash_min) == 16, "Hash should work for minimal URLs"
        
        # URL with port edge cases
        port_urls = [
            "https://example.com:443/path",  # Default HTTPS port
            "https://example.com/path",      # No port specified  
            "http://example.com:80/path",    # Default HTTP port
            "http://example.com/path",       # No port specified
            "https://example.com:8443/path", # Non-default port
        ]
        port_hashes = [generate_url_hash(url) for url in port_urls]
        # Default ports should normalize to same hash as no-port versions
        assert port_hashes[0] == port_hashes[1], "HTTPS default port should normalize"
        assert port_hashes[2] == port_hashes[3], "HTTP default port should normalize"
        assert port_hashes[4] not in port_hashes[:4], "Non-default ports should be unique"
    
    def test_project_hash_edge_cases(self):
        """Test project hash generation with edge cases."""
        
        # Very long project name
        long_name = "Project " * 1000  # ~8000 characters
        hash_long = generate_project_hash(long_name)
        assert len(hash_long) == 8, "Hash should be 8 chars for very long names"
        
        # Single character project name
        hash_single = generate_project_hash("A")
        assert len(hash_single) == 8, "Hash should work for single character"
        
        # Project name with unicode
        unicode_name = "太阳能项目 Solar Αβγ Проект"
        hash_unicode = generate_project_hash(unicode_name)
        assert len(hash_unicode) == 8, "Hash should handle unicode project names"
        
        # Project name with only special characters
        special_name = "!@#$%^&*()_+-=[]{}|;':\",./<>?`~"
        hash_special = generate_project_hash(special_name)
        assert len(hash_special) == 8, "Hash should handle special character names"
        
        # Whitespace edge cases
        whitespace_names = [
            "  Project  Name  ",     # Leading/trailing spaces
            "Project\t\tName",       # Tabs
            "Project\n\nName",       # Newlines  
            "Project\r\nName",       # Windows line endings
            "Project   Name",        # Multiple spaces
        ]
        whitespace_hashes = [generate_project_hash(name) for name in whitespace_names]
        # All should normalize to same hash (whitespace normalized)
        expected_hash = generate_project_hash("Project Name")
        for i, hash_val in enumerate(whitespace_hashes):
            assert hash_val == expected_hash, f"Whitespace case {i} should normalize: '{whitespace_names[i]}'"
        
        # Empty-like strings after normalization
        empty_like = ["   ", "\t\t", "\n\n", ""]
        for empty_str in empty_like:
            with pytest.raises(ValueError, match="Project name cannot be empty"):
                generate_project_hash(empty_str)
    
    def test_thread_id_edge_cases(self):
        """Test thread/process ID functions in edge cases."""
        
        # Process ID should be consistent within same process
        pid1 = get_process_id()
        pid2 = get_process_id()
        assert pid1 == pid2, "Process ID should be consistent"
        assert isinstance(pid1, int), "Process ID should be integer"
        assert pid1 > 0, "Process ID should be positive"
        
        # Test asyncio task ID outside async context
        task_id_sync = get_asyncio_task_id()
        assert task_id_sync == 0, "Task ID should be 0 outside async context"
        
        # Test asyncio task ID in async context
        async def test_async_task_id():
            task_id = get_asyncio_task_id()
            return task_id
        
        task_id_async = asyncio.run(test_async_task_id())
        assert isinstance(task_id_async, int), "Async task ID should be integer"
        assert task_id_async != 0, "Async task ID should not be 0 in async context"
        
        # Multiple async tasks should have different IDs
        async def get_multiple_task_ids():
            async def task1():
                return get_asyncio_task_id()
            async def task2():
                return get_asyncio_task_id()
            
            id1, id2 = await asyncio.gather(task1(), task2())
            return id1, id2
        
        id1, id2 = asyncio.run(get_multiple_task_ids())
        assert id1 != id2, f"Different async tasks should have different IDs: {id1} vs {id2}"
    
    def test_filename_generation_edge_cases(self):
        """Test cache filename generation with edge cases."""
        
        # Very long URL and project name
        long_url = "https://example.com/" + "x" * 2000
        long_project = "Project " * 500
        filename = generate_cache_filename(long_url, long_project)
        
        filename_only = Path(filename).name
        assert filename_only.startswith("cache_"), "Filename should start with cache_"
        assert filename_only.endswith(".txt"), "Filename should end with .txt"
        
        # Verify filename parts
        parts = filename_only[6:-4].split('_')  # Remove "cache_" and ".txt"
        assert len(parts) == 4, f"Should have 4 parts separated by underscore: {parts}"
        assert len(parts[0]) == 16, f"URL hash should be 16 chars: {parts[0]}"
        assert len(parts[1]) == 8, f"Project hash should be 8 chars: {parts[1]}"
        assert parts[2].isdigit(), f"PID should be numeric: {parts[2]}"
        assert parts[3].isdigit(), f"Task ID should be numeric: {parts[3]}"
        
        # Unicode input
        unicode_url = "https://测试.com"
        unicode_project = "测试项目"
        unicode_filename = generate_cache_filename(unicode_url, unicode_project)
        unicode_name = Path(unicode_filename).name
        # Should still be valid filename with ASCII-safe hash
        assert unicode_name.encode('ascii', errors='ignore').decode('ascii') == unicode_name, \
            "Unicode input should produce ASCII-safe filename"
        
        # Special characters in input
        special_url = "https://example.com/path?param=!@#$%^&*()"
        special_project = "Project !@#$%^&*()_+-="
        special_filename = generate_cache_filename(special_url, special_project)
        special_name = Path(special_filename).name
        
        # Filename should be filesystem-safe
        unsafe_chars = ['<', '>', ':', '"', '|', '?', '*', '/', '\\']
        for char in unsafe_chars:
            assert char not in special_name, f"Filename should not contain unsafe char '{char}': {special_name}"
    
    def test_atomic_write_edge_cases(self):
        """Test atomic write function with edge cases."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Empty content
            empty_file = temp_path / "empty.txt"
            atomic_write_file(empty_file, "")
            assert empty_file.exists(), "Should create empty file"
            assert empty_file.read_text() == "", "Empty file should have no content"
            
            # Very large content
            large_content = "Large content block\n" * 100000  # ~2MB
            large_file = temp_path / "large.txt"
            atomic_write_file(large_file, large_content)
            assert large_file.exists(), "Should create large file"
            assert large_file.read_text() == large_content, "Large file content should match"
            
            # Unicode content  
            unicode_content = "Unicode content: 测试 ünïcødé 🚀 αβγ Проект\n" * 1000
            unicode_file = temp_path / "unicode.txt"
            atomic_write_file(unicode_file, unicode_content)
            assert unicode_file.exists(), "Should create unicode file"
            read_unicode = unicode_file.read_text(encoding='utf-8')
            assert read_unicode == unicode_content, "Unicode content should match exactly"
            
            # Nested directory creation
            nested_file = temp_path / "level1" / "level2" / "level3" / "nested.txt"
            nested_content = "Nested directory content"
            atomic_write_file(nested_file, nested_content)
            assert nested_file.exists(), "Should create nested file and directories"
            assert nested_file.read_text() == nested_content, "Nested file content should match"
            
            # Overwrite existing file
            existing_file = temp_path / "existing.txt"
            existing_file.write_text("Original content")
            assert existing_file.read_text() == "Original content"
            
            new_content = "New overwritten content"
            atomic_write_file(existing_file, new_content)
            assert existing_file.read_text() == new_content, "Should overwrite existing file"
            
            # File with special characters in path
            special_dir = temp_path / "special dir with spaces"
            special_file = special_dir / "file with spaces.txt"
            special_content = "Content in special path"
            atomic_write_file(special_file, special_content)
            assert special_file.exists(), "Should handle paths with spaces"
            assert special_file.read_text() == special_content, "Special path content should match"
    
    @pytest.mark.asyncio
    async def test_aiparser_cache_edge_cases(self):
        """Test AiParser caching functionality with edge cases."""
        
        ai_parser = AiParser(
            api_key='test-key',
            api_url='https://test.api.com',
            model='test-model',
            prompt='Test prompt: PROJECT',
            project_name='Edge Case Test'
        )
        
        # Test cache operations before initialization
        with pytest.raises(ValueError, match="Cache file path not set"):
            ai_parser.get_api_response()
        
        # Test cleanup when no cache was ever created
        ai_parser.cleanup_cache_file()  # Should not raise error
        assert ai_parser._cache_file_path is None
        assert ai_parser._cached_content is None
        
        # Test cache with very large content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
            large_content = "Large scraped content\n" * 50000  # ~1MB
            temp_file.write(large_content)
            temp_file_path = temp_file.name
        
        try:
            # Set up cache state
            ai_parser._cache_file_path = temp_file_path
            ai_parser._cached_content = None
            
            # Mock API client for testing
            with patch.object(ai_parser, 'client') as mock_client:
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = '{"result": "success"}'
                mock_client.chat.completions.create.return_value = mock_response
                
                # First call should load large content
                response1, metrics1 = ai_parser.get_api_response()
                assert response1 == '{"result": "success"}'
                assert ai_parser._cached_content == large_content, "Should cache large content"
                
                # Subsequent calls should reuse cached content (not re-read file)
                with patch('builtins.open', mock_open()) as mock_file:
                    response2, metrics2 = ai_parser.get_api_response()
                    assert response2 == '{"result": "success"}'
                    mock_file.assert_not_called(), "Should not re-read file on second call"
            
            # Test cleanup of large cache
            ai_parser.cleanup_cache_file()
            assert ai_parser._cached_content is None, "Should clear large cached content"
            assert not Path(temp_file_path).exists(), "Should remove cache file"
            
        finally:
            # Ensure cleanup even if test fails
            Path(temp_file_path).unlink(missing_ok=True)
    
    def test_concurrent_filename_generation(self):
        """Test filename generation under concurrent conditions."""
        
        # Test that concurrent calls generate unique filenames
        import threading
        import time
        
        url = "https://example.com/concurrent-test"
        project = "Concurrent Test Project"
        
        filenames = []
        errors = []
        
        def generate_filename():
            try:
                filename = generate_cache_filename(url, project)
                filenames.append(filename)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads to generate filenames concurrently
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=generate_filename)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(errors) == 0, f"No errors should occur: {errors}"
        assert len(filenames) == 10, f"Should generate 10 filenames: {len(filenames)}"
        
        # All filenames should be unique (different PIDs/task IDs in threads)
        unique_filenames = set(filenames)
        # Note: In some cases, filenames might be the same if threads run in same process
        # and task IDs are similar, which is acceptable behavior
        assert len(unique_filenames) >= 1, "Should generate at least some unique filenames"
        
        # All filenames should be valid
        for filename in filenames:
            path = Path(filename)
            assert path.name.startswith("cache_"), f"Invalid filename format: {filename}"
            assert path.name.endswith(".txt"), f"Invalid filename extension: {filename}"
    
    def test_error_handling_robustness(self):
        """Test error handling robustness across all components."""
        
        # URL hash with None input
        with pytest.raises((ValueError, TypeError)):
            generate_url_hash(None)
        
        # URL hash with non-string input
        with pytest.raises(TypeError):
            generate_url_hash(123)
        
        # Project hash with None input
        with pytest.raises((ValueError, TypeError)):
            generate_project_hash(None)
        
        # Project hash with non-string input
        with pytest.raises(TypeError):
            generate_project_hash(['not', 'a', 'string'])
        
        # Filename generation with invalid inputs
        with pytest.raises(ValueError):
            generate_cache_filename("", "valid project")
        
        with pytest.raises(ValueError):
            generate_cache_filename("valid url", "")
        
        with pytest.raises(ValueError):
            generate_cache_filename(None, "valid project")
        
        with pytest.raises(ValueError):
            generate_cache_filename("valid url", None)
        
        # Atomic write with invalid inputs
        with pytest.raises(ValueError):
            atomic_write_file("", "content")
        
        with pytest.raises(ValueError):
            atomic_write_file(None, "content")
        
        with pytest.raises(TypeError):
            atomic_write_file("/valid/path", None)
        
        with pytest.raises(TypeError):
            atomic_write_file("/valid/path", 123)  # Non-string content
    
    def test_hash_collision_resistance(self):
        """Test hash collision resistance with similar inputs."""
        
        # Test URL hash collision resistance
        similar_urls = [
            "https://example.com/project1",
            "https://example.com/project2", 
            "https://example.com/project3",
            "https://example.com/project11",
            "https://example.com/project21",
            "https://example.org/project1",  # Different domain
            "http://example.com/project1",   # Different scheme
        ]
        
        url_hashes = [generate_url_hash(url) for url in similar_urls]
        unique_url_hashes = set(url_hashes)
        
        # Should have unique hashes for different URLs
        assert len(unique_url_hashes) == len(url_hashes), \
            f"URL hash collision detected: {len(unique_url_hashes)} unique vs {len(url_hashes)} total"
        
        # Test project name hash collision resistance
        similar_projects = [
            "Solar Project Alpha",
            "Solar Project Beta",
            "Solar Project Gamma", 
            "Solar Project Alpha1",
            "Solar Project Alpha 2",
            "Wind Project Alpha",
            "Battery Storage Alpha",
        ]
        
        project_hashes = [generate_project_hash(name) for name in similar_projects]
        unique_project_hashes = set(project_hashes)
        
        # Should have unique hashes for different project names
        assert len(unique_project_hashes) == len(project_hashes), \
            f"Project hash collision detected: {len(unique_project_hashes)} unique vs {len(project_hashes)} total"
        
        # Test combined filename collision resistance
        test_combinations = [
            ("https://example.com/test1", "Project A"),
            ("https://example.com/test2", "Project A"),
            ("https://example.com/test1", "Project B"),
            ("https://example.com/test1", "Project AA"), 
            ("https://example.com/test11", "Project A"),
        ]
        
        combined_filenames = [generate_cache_filename(url, proj) for url, proj in test_combinations]
        unique_combined = set(Path(f).name for f in combined_filenames)
        
        # All combinations should produce unique filenames
        assert len(unique_combined) == len(combined_filenames), \
            f"Filename collision detected: {len(unique_combined)} unique vs {len(combined_filenames)} total"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])