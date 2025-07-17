import pytest
from pathlib import Path
from tests.cache.test_fixtures import (
    CacheTestFixtures, 
    MockDataGenerators,
    test_urls,
    test_project_names, 
    mock_scraped_content,
    complete_test_data
)


class TestCacheInfrastructure(CacheTestFixtures):
    """Test suite to verify cache test infrastructure works correctly."""
    
    def test_temp_cache_dir_fixture(self, temp_cache_dir):
        """Test that temp_cache_dir fixture creates a working directory."""
        # Verify the directory exists and is writable
        assert temp_cache_dir.exists()
        assert temp_cache_dir.is_dir()
        
        # Test writing to the directory
        test_file = temp_cache_dir / "test_write.txt"
        test_content = "Test content for infrastructure verification"
        test_file.write_text(test_content)
        
        # Verify file was created and content is correct
        assert test_file.exists()
        assert test_file.read_text() == test_content
    
    def test_cache_file_manager_fixture(self, cache_file_manager):
        """Test that cache_file_manager fixture provides working utilities."""
        # Test creating a cache file
        test_content = "Cache file manager test content"
        cache_file = cache_file_manager.create_cache_file("test_cache.txt", test_content)
        
        # Verify file was created correctly
        assert cache_file.exists()
        assert cache_file_manager.file_exists("test_cache.txt")
        assert cache_file_manager.read_file("test_cache.txt") == test_content
        
        # Test listing files
        files = cache_file_manager.list_files()
        assert "test_cache.txt" in files
        
        # Test cleanup
        cache_file_manager.cleanup_files()
        assert not cache_file_manager.file_exists("test_cache.txt")
    
    def test_temp_cache_file_creation(self, cache_file_manager):
        """Test temporary cache file creation with random names."""
        test_content = "Temporary cache file content"
        temp_file = cache_file_manager.create_temp_cache_file(test_content)
        
        # Verify file was created with correct content
        assert temp_file.exists()
        assert temp_file.name.startswith("temp_cache_")
        assert temp_file.name.endswith(".txt")
        assert cache_file_manager.read_file(temp_file.name) == test_content
    
    def test_mock_data_generators(self):
        """Test that mock data generators produce valid test data."""
        # Test URL generation
        urls = MockDataGenerators.generate_test_urls(3)
        assert len(urls) == 3
        assert all(url.startswith("http") for url in urls)
        assert len(set(urls)) == 3  # All URLs should be unique
        
        # Test project name generation
        project_names = MockDataGenerators.generate_project_names(4)
        assert len(project_names) == 4
        assert all(len(name) > 0 for name in project_names)
        
        # Test content generation
        article_content = MockDataGenerators.generate_scraped_content("article")
        project_content = MockDataGenerators.generate_scraped_content("project")
        news_content = MockDataGenerators.generate_scraped_content("news")
        
        # Verify content is substantial and different
        assert len(article_content) > 100
        assert len(project_content) > 100
        assert len(news_content) > 100
        assert article_content != project_content != news_content
        
        # Verify content contains expected keywords
        assert "solar" in article_content.lower()
        assert "project" in project_content.lower()
        assert "news" in news_content.lower()
    
    def test_complete_test_data_set(self, complete_test_data):
        """Test that complete test data set fixture works correctly."""
        # Verify all expected keys are present
        expected_keys = ['urls', 'project_names', 'article_content', 'project_content', 'news_content']
        assert all(key in complete_test_data for key in expected_keys)
        
        # Verify data types and content
        assert isinstance(complete_test_data['urls'], list)
        assert isinstance(complete_test_data['project_names'], list)
        assert isinstance(complete_test_data['article_content'], str)
        assert isinstance(complete_test_data['project_content'], str)
        assert isinstance(complete_test_data['news_content'], str)
        
        # Verify data is substantial
        assert len(complete_test_data['urls']) == 3
        assert len(complete_test_data['project_names']) == 3
        assert len(complete_test_data['article_content']) > 100
    
    def test_isolated_cache_dir_fixture(self, isolated_cache_dir):
        """Test that isolated_cache_dir fixture works for session-level testing."""
        # Verify the directory exists and is writable
        assert isolated_cache_dir.exists()
        assert isolated_cache_dir.is_dir()
        
        # Create multiple files to test persistence
        for i in range(3):
            test_file = isolated_cache_dir / f"persistent_test_{i}.txt"
            test_file.write_text(f"Persistent content {i}")
            assert test_file.exists()
        
        # Verify all files exist
        files = list(isolated_cache_dir.glob("persistent_test_*.txt"))
        assert len(files) == 3
    
    def test_fixture_integration_scenario(self, cache_file_manager, test_urls, test_project_names, mock_scraped_content):
        """Test a realistic scenario using multiple fixtures together."""
        # Simulate creating cache files for multiple URLs and projects
        for i, (url, project_name) in enumerate(zip(test_urls[:2], test_project_names[:2])):
            # Create a cache filename (simplified version of what will be implemented)
            cache_filename = f"cache_test_{i}_{hash(url) % 10000}_{hash(project_name) % 1000}.txt"
            
            # Create cache file with mock content
            cache_file = cache_file_manager.create_cache_file(cache_filename, mock_scraped_content)
            
            # Verify file creation
            assert cache_file.exists()
            assert cache_file_manager.file_exists(cache_filename)
            
            # Verify content matches
            stored_content = cache_file_manager.read_file(cache_filename)
            assert stored_content == mock_scraped_content
        
        # Verify we created the expected number of files
        files = cache_file_manager.list_files()
        assert len(files) >= 2
        
        # Test cleanup
        cache_file_manager.cleanup_files()
        remaining_files = cache_file_manager.list_files()
        assert len(remaining_files) == 0
    
    def test_concurrent_file_operations(self, cache_file_manager):
        """Test that file operations work correctly with multiple files."""
        # Create multiple cache files simultaneously
        contents = ["Content A", "Content B", "Content C"]
        filenames = ["cache_a.txt", "cache_b.txt", "cache_c.txt"]
        
        created_files = []
        for filename, content in zip(filenames, contents):
            cache_file = cache_file_manager.create_cache_file(filename, content)
            created_files.append((cache_file, content))
        
        # Verify all files were created correctly
        assert len(created_files) == 3
        all_files = cache_file_manager.list_files()
        assert len(all_files) >= 3
        
        # Verify each file has correct content
        for cache_file, expected_content in created_files:
            stored_content = cache_file_manager.read_file(cache_file.name)
            assert stored_content == expected_content
        
        # Test partial cleanup
        cache_file_manager.cleanup_files()
        assert len(cache_file_manager.list_files()) == 0


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])