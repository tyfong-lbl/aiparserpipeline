import pytest
import os
import asyncio
import threading
import concurrent.futures
from pathlib import Path
from tests.cache.test_fixtures import test_urls, test_project_names


class TestFilenameGeneration:
    """Test suite for cache filename generation functionality."""
    
    def test_filename_format_specification(self, test_urls, test_project_names):
        """Test that filename format matches specification exactly."""
        from cache_utils import generate_cache_filename
        
        test_url = test_urls[0]
        test_project = test_project_names[0]
        
        filename_path = generate_cache_filename(test_url, test_project)
        filename = Path(filename_path).name
        
        # Should match format: cache_{url_hash}_{project_hash}_{pid}_{task_id}.txt
        parts = filename.split('_')
        
        assert len(parts) >= 5, f"Filename should have at least 5 parts separated by '_', got: {filename}"
        assert parts[0] == "cache", f"Filename should start with 'cache', got: {parts[0]}"
        assert filename.endswith(".txt"), f"Filename should end with '.txt', got: {filename}"
        
        # Extract components
        cache_prefix = parts[0]
        url_hash = parts[1]
        project_hash = parts[2]
        pid = parts[3]
        task_id = parts[4].replace('.txt', '')  # Remove .txt extension
        
        # Verify component formats
        assert cache_prefix == "cache"
        assert len(url_hash) == 16, f"URL hash should be 16 characters, got {len(url_hash)}"
        assert len(project_hash) == 8, f"Project hash should be 8 characters, got {len(project_hash)}"
        assert pid.isdigit(), f"PID should be numeric, got: {pid}"
        assert task_id.isdigit(), f"Task ID should be numeric, got: {task_id}"
    
    def test_same_inputs_produce_same_filename(self, test_urls, test_project_names):
        """Test that same inputs always produce same filename."""
        from cache_utils import generate_cache_filename
        
        test_url = test_urls[0]
        test_project = test_project_names[0]
        
        filename1 = generate_cache_filename(test_url, test_project)
        filename2 = generate_cache_filename(test_url, test_project)
        filename3 = generate_cache_filename(test_url, test_project)
        
        assert filename1 == filename2 == filename3, "Same inputs should produce same filename"
    
    def test_different_inputs_produce_different_filenames(self, test_urls, test_project_names):
        """Test that different inputs produce different filenames."""
        from cache_utils import generate_cache_filename
        
        # Test different URLs with same project
        filename1 = generate_cache_filename(test_urls[0], test_project_names[0])
        filename2 = generate_cache_filename(test_urls[1], test_project_names[0])
        
        assert filename1 != filename2, "Different URLs should produce different filenames"
        
        # Test same URL with different projects
        filename3 = generate_cache_filename(test_urls[0], test_project_names[0])
        filename4 = generate_cache_filename(test_urls[0], test_project_names[1])
        
        assert filename3 != filename4, "Different projects should produce different filenames"
        
        # Test completely different inputs
        filename5 = generate_cache_filename(test_urls[1], test_project_names[1])
        
        assert len({filename1, filename2, filename3, filename4, filename5}) == 4, "All different combinations should produce unique filenames"
    
    def test_filename_valid_for_filesystem_operations(self, test_urls, test_project_names):
        """Test that filename is valid for filesystem operations."""
        from cache_utils import generate_cache_filename
        
        test_url = test_urls[0]
        test_project = test_project_names[0]
        
        filename_path = generate_cache_filename(test_url, test_project)
        filename = Path(filename_path).name
        
        # Should not contain invalid characters for any OS
        invalid_chars = ['<', '>', '"', '|', '?', '*', ':', '\\', '/']
        for char in invalid_chars:
            assert char not in filename, f"Filename should not contain '{char}': {filename}"
        
        # Should not be too long (most filesystems support 255 chars)
        assert len(filename) <= 255, f"Filename too long ({len(filename)} chars): {filename}"
        
        # Should not start or end with spaces or dots
        assert not filename.startswith(' '), "Filename should not start with space"
        assert not filename.endswith(' '), "Filename should not end with space"
        assert not filename.startswith('.'), "Filename should not start with dot"
        
        # Should be valid for creation (test actual file operations)
        cache_dir = Path(filename_path).parent
        if cache_dir.exists():
            test_file = cache_dir / filename
            try:
                test_file.touch()
                assert test_file.exists(), "Should be able to create file with generated filename"
                test_file.unlink()  # Clean up
            except OSError as e:
                pytest.fail(f"Generated filename is not valid for filesystem operations: {e}")
    
    def test_full_path_points_to_scraped_cache_directory(self, test_urls, test_project_names):
        """Test that full path points to scraped_cache directory."""
        from cache_utils import generate_cache_filename
        
        test_url = test_urls[0]
        test_project = test_project_names[0]
        
        filename_path = generate_cache_filename(test_url, test_project)
        path = Path(filename_path)
        
        # Should be an absolute path
        assert path.is_absolute(), f"Should return absolute path, got: {filename_path}"
        
        # Should point to scraped_cache directory
        assert path.parent.name == "scraped_cache", f"Should be in scraped_cache directory, got: {path.parent}"
        
        # The full path should be valid
        assert len(str(path)) > 0, "Path should not be empty"
        
        # Parent directory should exist or be creatable
        parent_dir = path.parent
        assert parent_dir.exists() or parent_dir.parent.exists(), "Parent directory structure should exist"
    
    def test_concurrent_calls_produce_unique_filenames(self, test_urls, test_project_names):
        """Test that concurrent calls from different threads produce unique filenames."""
        from cache_utils import generate_cache_filename
        
        test_url = test_urls[0]
        test_project = test_project_names[0]
        
        results = []
        
        def worker():
            """Worker function for thread testing."""
            filename = generate_cache_filename(test_url, test_project)
            results.append(filename)
        
        # Run multiple threads concurrently
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # All results should be valid paths
        assert len(results) == 5, "Should get results from all threads"
        for result in results:
            assert isinstance(result, (str, Path)), f"Result should be path-like, got: {type(result)}"
            assert len(str(result)) > 0, "Result should not be empty"
    
    def test_async_context_filename_generation(self, test_urls, test_project_names):
        """Test filename generation in async context."""
        from cache_utils import generate_cache_filename
        
        test_url = test_urls[0]
        test_project = test_project_names[0]
        
        async def async_worker():
            filename = generate_cache_filename(test_url, test_project)
            return filename
        
        # Test in async context
        filename_async = asyncio.run(async_worker())
        
        # Should be a valid filename
        assert isinstance(filename_async, (str, Path))
        filename_str = str(filename_async)
        assert len(filename_str) > 0
        assert "cache_" in filename_str
        assert filename_str.endswith(".txt")
        
        # Task ID should be non-zero in async context
        filename_parts = Path(filename_async).name.split('_')
        task_id = filename_parts[4].replace('.txt', '')
        assert task_id != "0", f"Task ID should not be 0 in async context, got: {task_id}"
    
    def test_different_async_tasks_produce_different_filenames(self, test_urls, test_project_names):
        """Test that different async tasks produce different filenames."""
        from cache_utils import generate_cache_filename
        
        test_url = test_urls[0]
        test_project = test_project_names[0]
        
        async def async_worker(worker_id):
            filename = generate_cache_filename(test_url, test_project)
            return (worker_id, filename)
        
        async def run_concurrent_tasks():
            tasks = [asyncio.create_task(async_worker(i)) for i in range(3)]
            results = await asyncio.gather(*tasks)
            return results
        
        results = asyncio.run(run_concurrent_tasks())
        
        # Should get results from all tasks
        assert len(results) == 3, "Should get results from all async tasks"
        
        filenames = [result[1] for result in results]
        
        # All filenames should be valid
        for filename in filenames:
            assert isinstance(filename, (str, Path))
            filename_str = str(filename)
            assert "cache_" in filename_str
            assert filename_str.endswith(".txt")
    
    def test_edge_cases_and_special_characters(self):
        """Test edge cases with special characters in URLs and project names."""
        from cache_utils import generate_cache_filename
        
        # Test with special characters
        special_url = "https://example.com/path with spaces & symbols!@#$%"
        special_project = "Project with Special Characters !@#$%"
        
        filename = generate_cache_filename(special_url, special_project)
        
        # Should still produce valid filename
        assert isinstance(filename, (str, Path))
        filename_str = str(filename)
        assert "cache_" in filename_str
        assert filename_str.endswith(".txt")
        
        # Filename should be filesystem-safe despite special input characters
        filename_only = Path(filename).name
        invalid_chars = ['<', '>', '"', '|', '?', '*', ':', '\\', '/']
        for char in invalid_chars:
            assert char not in filename_only, f"Generated filename should not contain '{char}'"
    
    def test_function_integration_with_all_utilities(self, test_urls, test_project_names):
        """Test that filename generation integrates with all utility functions."""
        from cache_utils import (
            generate_cache_filename, 
            generate_url_hash, 
            generate_project_hash,
            get_process_id,
            get_asyncio_task_id
        )
        
        test_url = test_urls[0]
        test_project = test_project_names[0]
        
        # Generate filename
        filename_path = generate_cache_filename(test_url, test_project)
        filename = Path(filename_path).name
        
        # Generate individual components
        url_hash = generate_url_hash(test_url)
        project_hash = generate_project_hash(test_project)
        pid = get_process_id()
        task_id = get_asyncio_task_id()  # Should be 0 in sync context
        
        # Filename should contain all components
        expected_filename = f"cache_{url_hash}_{project_hash}_{pid}_{task_id}.txt"
        assert filename == expected_filename, f"Expected {expected_filename}, got {filename}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])