import pytest
import tempfile
import os
import shutil
from pathlib import Path
from typing import Generator, Dict, List, Optional
from unittest.mock import Mock
import random
import string


class CacheTestFixtures:
    """Test fixtures and utilities for cache operation testing."""
    
    @pytest.fixture
    def temp_cache_dir(self) -> Generator[Path, None, None]:
        """
        Create a temporary cache directory for testing.
        
        This fixture creates a temporary directory that mimics the scraped_cache
        structure and automatically cleans up after the test.
        
        Yields:
            Path: Path to the temporary cache directory
        """
        with tempfile.TemporaryDirectory(prefix="test_cache_") as temp_dir:
            cache_dir = Path(temp_dir) / "scraped_cache"
            cache_dir.mkdir(exist_ok=True)
            yield cache_dir
    
    @pytest.fixture
    def isolated_cache_dir(self) -> Generator[Path, None, None]:
        """
        Create an isolated cache directory that persists during the test session.
        
        This fixture creates a cache directory that can be used across multiple
        test functions but is cleaned up at the end of the session.
        
        Yields:
            Path: Path to the isolated cache directory
        """
        temp_dir = Path(tempfile.mkdtemp(prefix="test_cache_session_"))
        cache_dir = temp_dir / "scraped_cache"
        cache_dir.mkdir(exist_ok=True)
        
        try:
            yield cache_dir
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def cache_file_manager(self, temp_cache_dir):
        """
        Provide utilities for managing cache files during tests.
        
        Returns:
            CacheFileManager: Helper class for cache file operations
        """
        return CacheFileManager(temp_cache_dir)


class CacheFileManager:
    """Helper class for managing cache files during testing."""
    
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.created_files: List[Path] = []
    
    def create_cache_file(self, filename: str, content: str) -> Path:
        """
        Create a cache file with specified content.
        
        Args:
            filename: Name of the cache file to create
            content: Content to write to the file
            
        Returns:
            Path: Path to the created file
        """
        file_path = self.cache_dir / filename
        file_path.write_text(content, encoding='utf-8')
        self.created_files.append(file_path)
        return file_path
    
    def create_temp_cache_file(self, content: str) -> Path:
        """
        Create a temporary cache file with random filename.
        
        Args:
            content: Content to write to the file
            
        Returns:
            Path: Path to the created file
        """
        filename = f"temp_cache_{self._random_string(8)}.txt"
        return self.create_cache_file(filename, content)
    
    def cleanup_files(self):
        """Clean up all created files."""
        for file_path in self.created_files:
            if file_path.exists():
                file_path.unlink()
        self.created_files.clear()
    
    def file_exists(self, filename: str) -> bool:
        """Check if a cache file exists."""
        return (self.cache_dir / filename).exists()
    
    def read_file(self, filename: str) -> str:
        """Read content from a cache file."""
        return (self.cache_dir / filename).read_text(encoding='utf-8')
    
    def list_files(self) -> List[str]:
        """List all files in the cache directory."""
        return [f.name for f in self.cache_dir.iterdir() if f.is_file()]
    
    @staticmethod
    def _random_string(length: int) -> str:
        """Generate a random string of specified length."""
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


class MockDataGenerators:
    """Generators for mock test data."""
    
    @staticmethod
    def generate_test_urls(count: int = 5) -> List[str]:
        """
        Generate a list of test URLs.
        
        Args:
            count: Number of URLs to generate
            
        Returns:
            List of test URLs
        """
        base_urls = [
            "https://example.com",
            "https://httpbin.org/html",
            "https://httpbin.org/json",
            "https://pv-magazine-usa.com/test-article",
            "https://solarpowerworldonline.com/test-project",
            "https://renewableenergyworld.com/test-solar",
            "https://greentechmedia.com/test-story"
        ]
        
        urls = []
        for i in range(count):
            base_url = random.choice(base_urls)
            if i > 0:  # Add variation to make URLs unique
                urls.append(f"{base_url}-{i}")
            else:
                urls.append(base_url)
        
        return urls
    
    @staticmethod
    def generate_project_names(count: int = 5) -> List[str]:
        """
        Generate a list of test project names.
        
        Args:
            count: Number of project names to generate
            
        Returns:
            List of test project names
        """
        project_types = ["Solar", "Wind", "Hydro", "Geothermal", "Battery"]
        company_types = ["LLC", "Inc", "Corp", "Energy", "Power", "Systems"]
        locations = ["California", "Texas", "Nevada", "Arizona", "Florida", "Colorado"]
        
        names = []
        for i in range(count):
            project_type = random.choice(project_types)
            company_type = random.choice(company_types)
            location = random.choice(locations)
            
            # Generate different name patterns
            patterns = [
                f"{location} {project_type} {company_type}",
                f"{project_type} {location} Project",
                f"{company_type} {project_type} {location}",
                f"Test {project_type} Project {i+1}"
            ]
            
            names.append(random.choice(patterns))
        
        return names
    
    @staticmethod
    def generate_scraped_content(content_type: str = "article") -> str:
        """
        Generate mock scraped content.
        
        Args:
            content_type: Type of content to generate ('article', 'project', 'news')
            
        Returns:
            Mock scraped content string
        """
        if content_type == "article":
            return """
Solar Energy Project Announcement

Title: Major Solar Installation Planned for Desert Region

Content: A new 500MW solar photovoltaic installation is planned for construction
in the desert region. The project will feature advanced solar panel technology
and is expected to generate clean energy for approximately 125,000 homes.

Project Details:
- Capacity: 500 MW
- Technology: Solar PV
- Location: Desert Region
- Expected Completion: 2025
- Investment: $800 million

The project represents a significant step forward in renewable energy development
and will contribute to the region's clean energy goals.

Environmental Impact: The project has been designed to minimize environmental
impact while maximizing energy production efficiency.
"""
        elif content_type == "project":
            return """
Renewable Energy Project Database Entry

Project Name: Sunshine Valley Solar Farm
Developer: Green Energy Solutions LLC
Location: Nevada, USA
Status: Under Development
Capacity: 200 MW
Technology: Solar Photovoltaic
Timeline: 2024-2026

Project Description:
This utility-scale solar photovoltaic project will be constructed on 1,200 acres
of land in Nevada. The facility will use state-of-the-art solar tracking systems
to maximize energy production throughout the day.

Key Features:
- Single-axis tracking systems
- High-efficiency solar modules
- Advanced inverter technology
- On-site battery storage: 50 MWh

Grid Connection: The project will connect to the existing transmission infrastructure
through a new 230kV substation.
"""
        else:  # news
            return """
Renewable Energy News Update

Breaking: New Solar Project Receives Approval

Date: March 15, 2024
Location: Arizona

A major solar energy project has received final regulatory approval and is set
to begin construction in Q2 2024. The 300MW facility will be one of the largest
solar installations in the southwestern United States.

Key Points:
- 300MW capacity solar PV facility
- Creates 400 construction jobs
- Powers 75,000 homes annually
- $450 million total investment

Industry experts note that this project demonstrates the continued growth
of the renewable energy sector and the increasing competitiveness of solar
power generation.

The project developer expects commercial operations to begin by end of 2025.
"""
    
    @staticmethod
    def generate_test_data_set() -> Dict:
        """
        Generate a complete test data set with URLs, project names, and content.
        
        Returns:
            Dictionary containing test URLs, project names, and mock content
        """
        return {
            'urls': MockDataGenerators.generate_test_urls(3),
            'project_names': MockDataGenerators.generate_project_names(3),
            'article_content': MockDataGenerators.generate_scraped_content('article'),
            'project_content': MockDataGenerators.generate_scraped_content('project'),
            'news_content': MockDataGenerators.generate_scraped_content('news')
        }


# Convenience fixtures that can be imported and used in other test files
@pytest.fixture
def test_urls():
    """Generate test URLs for cache testing."""
    return MockDataGenerators.generate_test_urls()


@pytest.fixture 
def test_project_names():
    """Generate test project names for cache testing."""
    return MockDataGenerators.generate_project_names()


@pytest.fixture
def mock_scraped_content():
    """Generate mock scraped content for cache testing."""
    return MockDataGenerators.generate_scraped_content()


@pytest.fixture
def complete_test_data():
    """Generate complete test data set for cache testing."""
    return MockDataGenerators.generate_test_data_set()