"""
Tests for scrape_and_cache() method structure (Step 4.1 of refactoring).

This module tests the basic structure for the new scrape_and_cache() method:
- Method exists with correct signature
- Method is async and returns string type hint
- Parameter validation works (rejects empty/None URLs)
- NotImplementedError is raised when called
- Method can be called on AiParser instance
- Docstring is present and properly formatted

Tests verify the method contract that will be filled in during subsequent steps.
"""

import pytest
import asyncio
import inspect
from unittest.mock import Mock
import sys
from pathlib import Path

# Add the parent directory to the path so we can import from the main module
sys.path.insert(0, str(Path(__file__).parent.parent))

from page_tracker import AiParser


class TestScrapeAndCacheMethodStructure:
    """Test the basic structure of the scrape_and_cache() method."""
    
    def test_scrape_and_cache_method_exists(self):
        """Test that scrape_and_cache method exists on AiParser class."""
        ai_parser = AiParser(
            api_key="test_key",
            api_url="https://test.api.com",
            model="test_model",
            prompt="Test prompt",
            project_name="Test Project"
        )
        
        # Verify method exists
        assert hasattr(ai_parser, 'scrape_and_cache'), "AiParser should have scrape_and_cache method"
        assert callable(getattr(ai_parser, 'scrape_and_cache')), "scrape_and_cache should be callable"
    
    def test_scrape_and_cache_method_signature(self):
        """Test that scrape_and_cache has the correct method signature."""
        ai_parser = AiParser(
            api_key="test_key",
            api_url="https://test.api.com",
            model="test_model",
            prompt="Test prompt",
            project_name="Test Project"
        )
        
        # Get method signature
        method = getattr(ai_parser, 'scrape_and_cache')
        signature = inspect.signature(method)
        
        # Verify parameters
        params = list(signature.parameters.keys())
        assert 'url' in params, "Method should have 'url' parameter"
        
        # Verify url parameter type hint
        url_param = signature.parameters['url']
        assert url_param.annotation == str, "url parameter should be annotated as str"
        
        # Verify return type hint
        assert signature.return_annotation == str, "Method should return str type"
    
    def test_scrape_and_cache_is_async(self):
        """Test that scrape_and_cache is an async method."""
        ai_parser = AiParser(
            api_key="test_key",
            api_url="https://test.api.com",
            model="test_model",
            prompt="Test prompt",
            project_name="Test Project"
        )
        
        # Verify method is async
        method = getattr(ai_parser, 'scrape_and_cache')
        assert asyncio.iscoroutinefunction(method), "scrape_and_cache should be an async method"
    
    def test_scrape_and_cache_docstring_exists(self):
        """Test that scrape_and_cache has a comprehensive docstring."""
        ai_parser = AiParser(
            api_key="test_key",
            api_url="https://test.api.com",
            model="test_model",
            prompt="Test prompt",
            project_name="Test Project"
        )
        
        # Verify docstring exists and is comprehensive
        method = getattr(ai_parser, 'scrape_and_cache')
        docstring = method.__doc__
        
        assert docstring is not None, "scrape_and_cache should have a docstring"
        assert len(docstring.strip()) > 50, "Docstring should be comprehensive"
        
        # Check for key docstring components
        docstring_lower = docstring.lower()
        assert 'url' in docstring_lower, "Docstring should mention URL parameter"
        assert 'return' in docstring_lower, "Docstring should describe return value"
        assert 'str' in docstring_lower, "Docstring should mention string return type"
    
    @pytest.mark.asyncio
    async def test_scrape_and_cache_parameter_validation_empty_url(self):
        """Test that scrape_and_cache validates URL parameter - rejects empty string."""
        ai_parser = AiParser(
            api_key="test_key",
            api_url="https://test.api.com",
            model="test_model",
            prompt="Test prompt",
            project_name="Test Project"
        )
        
        # Test with empty string URL
        with pytest.raises((ValueError, TypeError)) as exc_info:
            await ai_parser.scrape_and_cache("")
        
        error_message = str(exc_info.value).lower()
        assert 'url' in error_message or 'empty' in error_message, "Error should mention URL or empty"
    
    @pytest.mark.asyncio
    async def test_scrape_and_cache_parameter_validation_none_url(self):
        """Test that scrape_and_cache validates URL parameter - rejects None."""
        ai_parser = AiParser(
            api_key="test_key",
            api_url="https://test.api.com",
            model="test_model",
            prompt="Test prompt",
            project_name="Test Project"
        )
        
        # Test with None URL
        with pytest.raises((ValueError, TypeError)) as exc_info:
            await ai_parser.scrape_and_cache(None)
        
        error_message = str(exc_info.value).lower()
        assert 'url' in error_message or 'none' in error_message, "Error should mention URL or None"
    
    @pytest.mark.asyncio
    async def test_scrape_and_cache_parameter_validation_non_string_url(self):
        """Test that scrape_and_cache validates URL parameter - rejects non-string types."""
        ai_parser = AiParser(
            api_key="test_key",
            api_url="https://test.api.com",
            model="test_model",
            prompt="Test prompt",
            project_name="Test Project"
        )
        
        # Test with non-string URL types
        invalid_urls = [123, [], {}, True, False]
        
        for invalid_url in invalid_urls:
            with pytest.raises((ValueError, TypeError)) as exc_info:
                await ai_parser.scrape_and_cache(invalid_url)
            
            error_message = str(exc_info.value).lower()
            assert 'url' in error_message or 'string' in error_message or 'str' in error_message, \
                f"Error should mention URL or string type for input: {invalid_url}"
    
    @pytest.mark.asyncio
    async def test_scrape_and_cache_raises_not_implemented_error(self):
        """Test that scrape_and_cache raises NotImplementedError when called with valid URL."""
        ai_parser = AiParser(
            api_key="test_key",
            api_url="https://test.api.com",
            model="test_model",
            prompt="Test prompt",
            project_name="Test Project"
        )
        
        # Test with valid URL - should raise NotImplementedError
        with pytest.raises(NotImplementedError):
            await ai_parser.scrape_and_cache("https://example.com")
    
    @pytest.mark.asyncio
    async def test_scrape_and_cache_parameter_validation_before_not_implemented(self):
        """Test that parameter validation happens before NotImplementedError is raised."""
        ai_parser = AiParser(
            api_key="test_key",
            api_url="https://test.api.com",
            model="test_model",
            prompt="Test prompt",
            project_name="Test Project"
        )
        
        # Parameter validation errors should be raised instead of NotImplementedError
        with pytest.raises((ValueError, TypeError)):
            await ai_parser.scrape_and_cache("")
        
        with pytest.raises((ValueError, TypeError)):
            await ai_parser.scrape_and_cache(None)
        
        # Valid URL should raise NotImplementedError
        with pytest.raises(NotImplementedError):
            await ai_parser.scrape_and_cache("https://valid.url.com")
    
    def test_scrape_and_cache_method_bound_to_instance(self):
        """Test that scrape_and_cache is properly bound to AiParser instances."""
        # Create two different instances
        ai_parser_1 = AiParser(
            api_key="key1",
            api_url="https://api1.com",
            model="model1",
            prompt="Prompt 1",
            project_name="Project 1"
        )
        
        ai_parser_2 = AiParser(
            api_key="key2",
            api_url="https://api2.com",
            model="model2",
            prompt="Prompt 2",
            project_name="Project 2"
        )
        
        # Verify methods are bound to different instances
        method_1 = getattr(ai_parser_1, 'scrape_and_cache')
        method_2 = getattr(ai_parser_2, 'scrape_and_cache')
        
        assert method_1.__self__ is ai_parser_1, "Method should be bound to first instance"
        assert method_2.__self__ is ai_parser_2, "Method should be bound to second instance"
        assert method_1.__self__ is not method_2.__self__, "Methods should be bound to different instances"
    
    def test_scrape_and_cache_method_accessible_from_class(self):
        """Test that scrape_and_cache method is accessible from the AiParser class."""
        # Verify method exists at class level
        assert hasattr(AiParser, 'scrape_and_cache'), "AiParser class should have scrape_and_cache method"
        
        # Verify it's a method (not just an attribute)
        class_method = getattr(AiParser, 'scrape_and_cache')
        assert callable(class_method), "scrape_and_cache should be callable at class level"
        assert asyncio.iscoroutinefunction(class_method), "scrape_and_cache should be async at class level"
    
    @pytest.mark.asyncio
    async def test_scrape_and_cache_url_whitespace_handling(self):
        """Test that scrape_and_cache handles URLs with whitespace appropriately."""
        ai_parser = AiParser(
            api_key="test_key",
            api_url="https://test.api.com",
            model="test_model",
            prompt="Test prompt",
            project_name="Test Project"
        )
        
        # URLs with only whitespace should be rejected
        whitespace_urls = ["   ", "\t", "\n", "\r\n", " \t \n "]
        
        for whitespace_url in whitespace_urls:
            with pytest.raises((ValueError, TypeError)) as exc_info:
                await ai_parser.scrape_and_cache(whitespace_url)
            
            error_message = str(exc_info.value).lower()
            assert 'url' in error_message or 'empty' in error_message, \
                f"Error should mention URL or empty for whitespace input: '{whitespace_url}'"


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])