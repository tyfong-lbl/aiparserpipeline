"""
Tests for AiParser instance variables (Step 3.1 of refactoring).

This module tests the addition of cache-related instance variables to the AiParser class:
- _cache_file_path: Optional[str] = None
- _cached_content: Optional[str] = None

Tests verify that:
1. New instance variables are initialized to None
2. Existing AiParser functionality is unchanged
3. Instance can be created with same parameters as before
4. New variables can be accessed by instance methods
5. Multiple instances have independent variable values
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add the parent directory to the path so we can import from the main module
sys.path.insert(0, str(Path(__file__).parent.parent))

from page_tracker import AiParser


class TestAiParserInstanceVariables:
    """Test the addition of cache-related instance variables to AiParser class."""
    
    def test_aiparser_initialization_with_cache_variables(self):
        """Test that AiParser initializes with new cache instance variables set to None."""
        # Create AiParser instance with standard parameters
        ai_parser = AiParser(
            api_key="test_key",
            api_url="https://test.api.com",
            model="test_model",
            prompt="Test prompt for {PROJECT}",
            project_name="Test Project",
            publication_url="https://test.com",
            pipeline_logger=None
        )
        
        # Verify new instance variables are initialized to None
        assert hasattr(ai_parser, '_cache_file_path'), "AiParser should have _cache_file_path attribute"
        assert hasattr(ai_parser, '_cached_content'), "AiParser should have _cached_content attribute"
        
        assert ai_parser._cache_file_path is None, "_cache_file_path should be initialized to None"
        assert ai_parser._cached_content is None, "_cached_content should be initialized to None"
    
    def test_aiparser_existing_attributes_unchanged(self):
        """Test that existing AiParser attributes are still initialized correctly."""
        test_api_key = "test_api_key_12345"
        test_api_url = "https://test.api.endpoint.com"
        test_model = "test_model_v1"
        test_prompt = "Test prompt with {PROJECT} placeholder"
        test_project_name = "Solar Project Alpha"
        test_publication_url = "https://publication.test.com"
        mock_logger = Mock()
        
        ai_parser = AiParser(
            api_key=test_api_key,
            api_url=test_api_url,
            model=test_model,
            prompt=test_prompt,
            project_name=test_project_name,
            publication_url=test_publication_url,
            pipeline_logger=mock_logger
        )
        
        # Verify all existing attributes are set correctly
        assert ai_parser.api_key == test_api_key
        assert ai_parser.model == test_model
        assert ai_parser.prompt == test_prompt
        assert ai_parser.project_name == test_project_name
        assert ai_parser.publication_url == test_publication_url
        assert ai_parser.pipeline_logger is mock_logger
        
        # Verify OpenAI client is initialized
        assert ai_parser.client is not None
        assert hasattr(ai_parser.client, 'chat')
        
        # Verify playwright/browser attributes are initialized to None
        assert ai_parser.playwright is None
        assert ai_parser.browser is None
    
    def test_aiparser_instance_isolation(self):
        """Test that multiple AiParser instances have independent cache variables."""
        # Create first instance
        ai_parser_1 = AiParser(
            api_key="key1",
            api_url="https://api1.com",
            model="model1",
            prompt="Prompt 1",
            project_name="Project 1"
        )
        
        # Create second instance
        ai_parser_2 = AiParser(
            api_key="key2",
            api_url="https://api2.com",
            model="model2",
            prompt="Prompt 2",
            project_name="Project 2"
        )
        
        # Initially both should have None values
        assert ai_parser_1._cache_file_path is None
        assert ai_parser_1._cached_content is None
        assert ai_parser_2._cache_file_path is None
        assert ai_parser_2._cached_content is None
        
        # Modify values on first instance
        ai_parser_1._cache_file_path = "/path/to/cache1.txt"
        ai_parser_1._cached_content = "cached content 1"
        
        # Verify second instance is unaffected
        assert ai_parser_2._cache_file_path is None
        assert ai_parser_2._cached_content is None
        
        # Modify values on second instance
        ai_parser_2._cache_file_path = "/path/to/cache2.txt"  
        ai_parser_2._cached_content = "cached content 2"
        
        # Verify both instances have independent values
        assert ai_parser_1._cache_file_path == "/path/to/cache1.txt"
        assert ai_parser_1._cached_content == "cached content 1"
        assert ai_parser_2._cache_file_path == "/path/to/cache2.txt"
        assert ai_parser_2._cached_content == "cached content 2"
    
    def test_aiparser_cache_variables_accessible_by_methods(self):
        """Test that new cache variables can be accessed by instance methods."""
        ai_parser = AiParser(
            api_key="test_key",
            api_url="https://test.api.com",
            model="test_model",
            prompt="Test prompt",
            project_name="Test Project"
        )
        
        # Define a test method that accesses the cache variables
        def test_method(self):
            return (self._cache_file_path, self._cached_content)
        
        # Bind the test method to the instance
        import types
        ai_parser.test_method = types.MethodType(test_method, ai_parser)
        
        # Verify method can access variables
        cache_path, cached_content = ai_parser.test_method()
        assert cache_path is None
        assert cached_content is None
        
        # Set values and verify method can access them
        ai_parser._cache_file_path = "/test/path"
        ai_parser._cached_content = "test content"
        
        cache_path, cached_content = ai_parser.test_method()
        assert cache_path == "/test/path"
        assert cached_content == "test content"
    
    def test_aiparser_creation_with_minimal_parameters(self):
        """Test that AiParser can be created with minimal parameters and cache vars are still initialized."""
        # Create with minimal required parameters
        ai_parser = AiParser(
            api_key="test_key",
            api_url="https://test.api.com", 
            model="test_model",
            prompt="Test prompt",
            project_name="Test Project"
            # Optional parameters: publication_url=None, pipeline_logger=None
        )
        
        # Verify cache variables are initialized even with minimal parameters
        assert hasattr(ai_parser, '_cache_file_path')
        assert hasattr(ai_parser, '_cached_content')
        assert ai_parser._cache_file_path is None
        assert ai_parser._cached_content is None
        
        # Verify optional parameters defaulted correctly
        assert ai_parser.publication_url is None
        assert ai_parser.pipeline_logger is None
    
    def test_aiparser_cache_variables_are_private(self):
        """Test that cache variables follow private naming convention."""
        ai_parser = AiParser(
            api_key="test_key",
            api_url="https://test.api.com",
            model="test_model", 
            prompt="Test prompt",
            project_name="Test Project"
        )
        
        # Verify variables start with underscore (private convention)
        assert '_cache_file_path' in dir(ai_parser)
        assert '_cached_content' in dir(ai_parser)
        
        # Verify they're not in the public interface (don't appear without underscore)
        assert 'cache_file_path' not in [attr for attr in dir(ai_parser) if not attr.startswith('_')]
        assert 'cached_content' not in [attr for attr in dir(ai_parser) if not attr.startswith('_')]
    
    @pytest.mark.asyncio
    async def test_aiparser_initialization_and_cleanup_unchanged(self):
        """Test that existing initialization and cleanup functionality is unchanged."""
        ai_parser = AiParser(
            api_key="test_key",
            api_url="https://test.api.com",
            model="test_model",
            prompt="Test prompt",
            project_name="Test Project"
        )
        
        # Verify initial state
        assert ai_parser.playwright is None
        assert ai_parser.browser is None
        
        # Mock playwright to avoid actual browser launch in tests
        with patch('page_tracker.async_playwright') as mock_playwright:
            mock_playwright_instance = Mock()
            mock_playwright.return_value.start = Mock(return_value=mock_playwright_instance)
            mock_browser = Mock()
            mock_playwright_instance.chromium.launch = Mock(return_value=mock_browser)
            
            # Make the async methods return proper awaitable objects
            async def mock_start():
                return mock_playwright_instance
            
            async def mock_launch():
                return mock_browser
            
            mock_playwright.return_value.start = mock_start
            mock_playwright_instance.chromium.launch = mock_launch
            
            # Test initialization
            await ai_parser.initialize()
            
            # Verify browser and playwright are set
            assert ai_parser.playwright is mock_playwright_instance
            assert ai_parser.browser is mock_browser
            
            # Mock browser and playwright close methods as async
            async def mock_close():
                pass
            
            async def mock_stop():
                pass
                
            mock_browser.close = mock_close
            mock_playwright_instance.stop = mock_stop
            
            # Test cleanup - this should work the same as before
            await ai_parser.cleanup()
            
            # Verify cleanup was called (just check that they were assigned)
            assert ai_parser.browser is mock_browser
            assert ai_parser.playwright is mock_playwright_instance
    
    def test_type_hints_for_cache_variables(self):
        """Test that cache variables can hold Optional[str] values (None or string)."""
        ai_parser = AiParser(
            api_key="test_key",
            api_url="https://test.api.com",
            model="test_model",
            prompt="Test prompt",
            project_name="Test Project"
        )
        
        # Note: Since we're adding instance variables in __init__, 
        # we won't have class-level annotations. This test verifies
        # that the variables can hold string values or None as per Optional[str].
        
        # Test that variables can be set to None
        ai_parser._cache_file_path = None
        ai_parser._cached_content = None
        assert ai_parser._cache_file_path is None
        assert ai_parser._cached_content is None
        
        # Test that variables can be set to string values
        ai_parser._cache_file_path = "/path/to/cache.txt"
        ai_parser._cached_content = "cached content string"
        assert isinstance(ai_parser._cache_file_path, str)
        assert isinstance(ai_parser._cached_content, str)
        assert ai_parser._cache_file_path == "/path/to/cache.txt"
        assert ai_parser._cached_content == "cached content string"
        
        # Test that variables can be set back to None (demonstrating Optional behavior)
        ai_parser._cache_file_path = None
        ai_parser._cached_content = None
        assert ai_parser._cache_file_path is None
        assert ai_parser._cached_content is None


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])