import pytest
import os
import threading
import concurrent.futures
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, mock_open
from tests.cache.test_fixtures import CacheTestFixtures


class TestAtomicWrite(CacheTestFixtures):
    """Test suite for atomic file write functionality."""
    
    def test_content_written_correctly_to_final_file(self, temp_cache_dir):
        """Test that content is written correctly to final file."""
        from cache_utils import atomic_write_file
        
        test_content = "This is test content for atomic write operation."
        test_file = temp_cache_dir / "test_file.txt"
        
        # Write content atomically
        atomic_write_file(str(test_file), test_content)
        
        # Verify file exists and content is correct
        assert test_file.exists(), "Final file should exist after atomic write"
        
        written_content = test_file.read_text(encoding='utf-8')
        assert written_content == test_content, "Written content should match input content"
    
    def test_temporary_file_cleaned_up_after_successful_write(self, temp_cache_dir):
        """Test that temporary file is cleaned up after successful write."""
        from cache_utils import atomic_write_file
        
        test_content = "Content for cleanup test."
        test_file = temp_cache_dir / "cleanup_test.txt"
        
        # Track temp files before write
        temp_files_before = list(temp_cache_dir.glob("*.tmp"))
        
        # Write content atomically
        atomic_write_file(str(test_file), test_content)
        
        # Track temp files after write
        temp_files_after = list(temp_cache_dir.glob("*.tmp"))
        
        # Should have same number of temp files (cleanup occurred)
        assert len(temp_files_after) <= len(temp_files_before), "Temporary files should be cleaned up"
        
        # Final file should exist with correct content
        assert test_file.exists()
        assert test_file.read_text(encoding='utf-8') == test_content
    
    def test_atomic_operation_behavior(self, temp_cache_dir):
        """Test atomic operation (other processes see complete file or no file)."""
        from cache_utils import atomic_write_file
        
        test_content = "A" * 10000  # Larger content to increase write time
        test_file = temp_cache_dir / "atomic_test.txt"
        
        # Before write, file should not exist
        assert not test_file.exists(), "File should not exist before write"
        
        # Write content atomically
        atomic_write_file(str(test_file), test_content)
        
        # After write, file should exist with complete content
        assert test_file.exists(), "File should exist after write"
        written_content = test_file.read_text(encoding='utf-8')
        assert written_content == test_content, "Content should be complete and correct"
        assert len(written_content) == len(test_content), "All content should be written"
    
    def test_file_encoding_handled_properly_utf8(self, temp_cache_dir):
        """Test that file encoding is handled properly (UTF-8)."""
        from cache_utils import atomic_write_file
        
        # Test content with various UTF-8 characters
        test_content = """
        English: Hello World!
        Spanish: ¡Hola Mundo!
        Chinese: 你好世界！
        Arabic: مرحبا بالعالم!
        Russian: Привет мир!
        Emoji: 🌍🚀⭐
        Special chars: àáâãäåæçèéêë
        """
        
        test_file = temp_cache_dir / "utf8_test.txt"
        
        # Write UTF-8 content atomically
        atomic_write_file(str(test_file), test_content)
        
        # Verify file exists and UTF-8 content is preserved
        assert test_file.exists(), "UTF-8 test file should exist"
        
        written_content = test_file.read_text(encoding='utf-8')
        assert written_content == test_content, "UTF-8 content should be preserved exactly"
        
        # Also test reading with explicit UTF-8 encoding
        with open(test_file, 'r', encoding='utf-8') as f:
            read_content = f.read()
        assert read_content == test_content, "UTF-8 content should be readable correctly"
    
    def test_basic_error_handling_for_write_failures(self, temp_cache_dir):
        """Test basic error handling for write failures."""
        from cache_utils import atomic_write_file
        
        # Test with invalid file path
        invalid_path = "/nonexistent/directory/file.txt"
        
        with pytest.raises((OSError, IOError, PermissionError)):
            atomic_write_file(invalid_path, "test content")
        
        # Test with empty content (should succeed)
        test_file = temp_cache_dir / "empty_test.txt"
        atomic_write_file(str(test_file), "")
        
        assert test_file.exists()
        assert test_file.read_text(encoding='utf-8') == ""
        
        # Test with None content (should raise error)
        with pytest.raises((TypeError, ValueError)):
            atomic_write_file(str(temp_cache_dir / "none_test.txt"), None)
    
    def test_concurrent_writes_to_different_files_work_safely(self, temp_cache_dir):
        """Test that concurrent writes to different files work safely."""
        from cache_utils import atomic_write_file
        
        results = []
        
        def worker(file_id):
            """Worker function for concurrent writing."""
            try:
                test_content = f"Content for file {file_id}: " + "X" * 1000
                test_file = temp_cache_dir / f"concurrent_test_{file_id}.txt"
                
                atomic_write_file(str(test_file), test_content)
                
                # Verify write was successful
                if test_file.exists():
                    written_content = test_file.read_text(encoding='utf-8')
                    success = (written_content == test_content)
                    results.append((file_id, success, len(written_content)))
                else:
                    results.append((file_id, False, 0))
                    
            except Exception as e:
                results.append((file_id, False, str(e)))
        
        # Run multiple concurrent writes
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker, i) for i in range(5)]
            concurrent.futures.wait(futures)
        
        # Verify all writes succeeded
        assert len(results) == 5, "Should have results from all concurrent writes"
        
        for file_id, success, content_length in results:
            assert success, f"Concurrent write {file_id} should succeed, got: {content_length}"
            if isinstance(content_length, int):
                assert content_length > 1000, f"File {file_id} should have substantial content"
    
    def test_atomic_write_with_existing_file_overwrite(self, temp_cache_dir):
        """Test atomic write when target file already exists (should overwrite)."""
        from cache_utils import atomic_write_file
        
        test_file = temp_cache_dir / "overwrite_test.txt"
        
        # Create initial file with content
        initial_content = "Initial content"
        test_file.write_text(initial_content, encoding='utf-8')
        assert test_file.read_text(encoding='utf-8') == initial_content
        
        # Overwrite with atomic write
        new_content = "New content after atomic write"
        atomic_write_file(str(test_file), new_content)
        
        # Verify file was overwritten
        assert test_file.exists()
        written_content = test_file.read_text(encoding='utf-8')
        assert written_content == new_content, "File should be overwritten with new content"
        assert written_content != initial_content, "Old content should be replaced"
    
    def test_atomic_write_creates_parent_directories(self, temp_cache_dir):
        """Test that atomic write creates parent directories if they don't exist."""
        from cache_utils import atomic_write_file
        
        # Test nested directory structure
        nested_file = temp_cache_dir / "level1" / "level2" / "nested_file.txt"
        test_content = "Content in nested directories"
        
        # Parent directories should not exist initially
        assert not nested_file.parent.exists(), "Parent directories should not exist initially"
        
        # Atomic write should create directories
        atomic_write_file(str(nested_file), test_content)
        
        # Verify file and directories were created
        assert nested_file.exists(), "Nested file should be created"
        assert nested_file.parent.exists(), "Parent directories should be created"
        
        written_content = nested_file.read_text(encoding='utf-8')
        assert written_content == test_content, "Content should be written correctly"
    
    def test_atomic_write_temp_file_in_same_directory(self, temp_cache_dir):
        """Test that temporary file is created in same directory as target file."""
        from cache_utils import atomic_write_file
        
        test_file = temp_cache_dir / "same_dir_test.txt"
        test_content = "Testing temp file location"
        
        # Monitor directory during write
        files_before = set(temp_cache_dir.iterdir())
        
        atomic_write_file(str(test_file), test_content)
        
        files_after = set(temp_cache_dir.iterdir())
        
        # Should only have added the final file (temp file cleaned up)
        new_files = files_after - files_before
        assert len(new_files) == 1, "Should only have one new file after write"
        assert test_file in new_files, "New file should be the target file"
        
        # Verify content
        assert test_file.read_text(encoding='utf-8') == test_content
    
    def test_atomic_write_handles_large_content(self, temp_cache_dir):
        """Test atomic write with large content."""
        from cache_utils import atomic_write_file
        
        # Create large content (1MB)
        large_content = "A" * (1024 * 1024)
        test_file = temp_cache_dir / "large_content_test.txt"
        
        # Write large content atomically
        atomic_write_file(str(test_file), large_content)
        
        # Verify large content was written correctly
        assert test_file.exists(), "Large content file should exist"
        
        written_content = test_file.read_text(encoding='utf-8')
        assert len(written_content) == len(large_content), "Large content length should match"
        assert written_content == large_content, "Large content should be identical"
    
    def test_atomic_write_function_signature_and_types(self, temp_cache_dir):
        """Test atomic write function signature and type handling."""
        from cache_utils import atomic_write_file
        
        test_file = temp_cache_dir / "signature_test.txt"
        
        # Test with string path
        atomic_write_file(str(test_file), "string path test")
        assert test_file.read_text(encoding='utf-8') == "string path test"
        
        # Test with Path object
        test_file2 = temp_cache_dir / "path_object_test.txt"
        atomic_write_file(test_file2, "path object test")
        assert test_file2.read_text(encoding='utf-8') == "path object test"
        
        # Test parameter validation
        with pytest.raises((TypeError, ValueError)):
            atomic_write_file(None, "content")
        
        with pytest.raises((TypeError, ValueError)):
            atomic_write_file("", "content")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])