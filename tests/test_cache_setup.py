import os
import tempfile
import pytest
from pathlib import Path


class TestCacheDirectorySetup:
    """Test suite for cache directory setup functionality."""
    
    def test_scraped_cache_directory_exists(self):
        """Test that scraped_cache directory exists in project root."""
        project_root = Path(__file__).parent.parent
        cache_dir = project_root / "scraped_cache"
        
        assert cache_dir.exists(), "scraped_cache directory should exist"
        assert cache_dir.is_dir(), "scraped_cache should be a directory"
    
    def test_scraped_cache_directory_is_writable(self):
        """Test that scraped_cache directory has write permissions."""
        project_root = Path(__file__).parent.parent
        cache_dir = project_root / "scraped_cache"
        
        # Test write permissions by creating and deleting a test file
        test_file = cache_dir / "test_write_permissions.txt"
        try:
            test_file.write_text("test content")
            assert test_file.exists(), "Should be able to create files in cache directory"
            
            content = test_file.read_text()
            assert content == "test content", "Should be able to read files from cache directory"
        finally:
            # Clean up test file
            if test_file.exists():
                test_file.unlink()
    
    def test_cache_directory_in_gitignore(self):
        """Test that scraped_cache directory is added to .gitignore."""
        project_root = Path(__file__).parent.parent
        gitignore_path = project_root / ".gitignore"
        
        assert gitignore_path.exists(), ".gitignore file should exist"
        
        gitignore_content = gitignore_path.read_text()
        assert "scraped_cache/" in gitignore_content, "scraped_cache/ should be in .gitignore"


def setup_cache_directory():
    """
    Set up the cache directory environment.
    
    This function ensures that:
    1. The scraped_cache directory exists
    2. The directory has proper write permissions
    3. The directory is added to .gitignore
    
    Returns:
        Path: Path to the created cache directory
    """
    project_root = Path(__file__).parent.parent
    cache_dir = project_root / "scraped_cache"
    
    # Create directory if it doesn't exist
    cache_dir.mkdir(exist_ok=True)
    
    # Verify write permissions
    if not os.access(cache_dir, os.W_OK):
        raise PermissionError(f"Cache directory {cache_dir} is not writable")
    
    # Check .gitignore
    gitignore_path = project_root / ".gitignore"
    if gitignore_path.exists():
        gitignore_content = gitignore_path.read_text()
        if "scraped_cache/" not in gitignore_content:
            # Add to .gitignore
            with gitignore_path.open("a") as f:
                f.write("\n# scraped cache files\nscraped_cache/\n")
    
    return cache_dir


if __name__ == "__main__":
    # Run setup when script is executed directly
    cache_dir = setup_cache_directory()
    print(f"Cache directory setup complete: {cache_dir}")