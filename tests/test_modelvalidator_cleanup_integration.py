"""
Test cleanup integration in ModelValidator error handling paths.

This test suite verifies that cache cleanup occurs properly under all error conditions
in the ModelValidator class, as required by Step 7.2 of the AiParser refactoring.
"""

import asyncio
import json
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call

# Import the classes under test
from page_tracker import ModelValidator, AiParser


class TestModelValidatorCleanupIntegration:
    """Test cleanup integration in ModelValidator error handling paths."""
    
    @pytest.fixture
    def mock_url_df(self):
        """Create a mock URL DataFrame for testing."""
        import pandas as pd
        return pd.DataFrame({
            'url': ['https://example.com/test1', 'https://example.com/test2'],
            'project': ['Test Project 1', 'Test Project 2']
        })
    
    @pytest.fixture
    def temp_prompt_dir(self):
        """Create temporary directory with test prompt files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            prompt_dir = Path(temp_dir)
            
            # Create test prompt files
            for i in range(1, 4):  # 3 prompts
                prompt_file = prompt_dir / f"test-prompt{i}.txt"
                prompt_file.write_text(f"Test prompt {i}: Extract data from PROJECT")
            
            yield prompt_dir
    
    @pytest.fixture
    def model_validator(self, mock_url_df, temp_prompt_dir):
        """Create ModelValidator instance for testing."""
        return ModelValidator(
            number_of_queries=3,
            prompt_dir_path=temp_prompt_dir,
            prompt_filename_base='test-prompt',
            api_key='test-key',
            api_url='https://test.api.com',
            model='test-model',
            project_name='Test Project',
            url_df=mock_url_df
        )
    
    @pytest.mark.asyncio
    async def test_cleanup_on_scraping_failure(self, model_validator):
        """Test cleanup occurs when scraping fails."""
        url = 'https://example.com/fail-scrape'
        
        # Mock AiParser to fail during scraping
        with patch('page_tracker.AiParser') as MockAiParser:
            mock_parser = AsyncMock()
            MockAiParser.return_value = mock_parser
            
            # Mock initialize to succeed
            mock_parser.initialize = AsyncMock()
            
            # Mock scrape_and_cache to fail
            mock_parser.scrape_and_cache = AsyncMock(side_effect=Exception("Scraping failed"))
            
            # Mock cleanup method
            mock_parser.cleanup = AsyncMock()
            
            # Call get_responses_for_url
            result = await model_validator.get_responses_for_url(url)
            
            # Verify cleanup was called despite scraping failure
            mock_parser.cleanup.assert_called_once()
            
            # Verify method returns empty list (preserves original behavior)
            assert result == []
    
    @pytest.mark.asyncio
    async def test_cleanup_on_api_processing_failure(self, model_validator):
        """Test cleanup occurs when API processing fails."""
        url = 'https://example.com/fail-api'
        
        with patch('page_tracker.AiParser') as MockAiParser:
            mock_parser = AsyncMock()
            MockAiParser.return_value = mock_parser
            
            # Mock successful initialization and scraping
            mock_parser.initialize = AsyncMock()
            mock_parser.scrape_and_cache = AsyncMock(return_value='/tmp/cache_file.txt')
            
            # Mock API response to fail
            def api_fail_side_effect(*args, **kwargs):
                raise Exception("API failed")
            mock_parser.get_api_response = MagicMock(side_effect=api_fail_side_effect)
            
            # Mock cleanup method
            mock_parser.cleanup = AsyncMock()
            
            # Call get_responses_for_url
            result = await model_validator.get_responses_for_url(url)
            
            # Verify cleanup was called despite API failure
            mock_parser.cleanup.assert_called_once()
            
            # Verify method returns list with None values for failed prompts
            assert len(result) == 3  # 3 prompts
            assert all(response is None for response in result)
    
    @pytest.mark.asyncio
    async def test_cleanup_on_json_decode_failure(self, model_validator):
        """Test cleanup occurs when JSON decoding fails."""
        url = 'https://example.com/fail-json'
        
        with patch('page_tracker.AiParser') as MockAiParser:
            mock_parser = AsyncMock()
            MockAiParser.return_value = mock_parser
            
            # Mock successful initialization and scraping
            mock_parser.initialize = AsyncMock()
            mock_parser.scrape_and_cache = AsyncMock(return_value='/tmp/cache_file.txt')
            
            # Mock API response to return invalid JSON
            def api_json_side_effect(*args, **kwargs):
                return ("invalid json", {})
            mock_parser.get_api_response = MagicMock(side_effect=api_json_side_effect)
            mock_parser.strip_markdown = MagicMock(return_value="invalid json")
            
            # Mock cleanup method
            mock_parser.cleanup = AsyncMock()
            
            # Call get_responses_for_url
            result = await model_validator.get_responses_for_url(url)
            
            # Verify cleanup was called despite JSON decode failure
            mock_parser.cleanup.assert_called_once()
            
            # Verify method returns list with None values for failed JSON parsing
            assert len(result) == 3  # 3 prompts
            assert all(response is None for response in result)
    
    @pytest.mark.asyncio
    async def test_cleanup_on_initialization_failure(self, model_validator):
        """Test cleanup occurs when browser initialization fails."""
        url = 'https://example.com/fail-init'
        
        with patch('page_tracker.AiParser') as MockAiParser:
            mock_parser = AsyncMock()
            MockAiParser.return_value = mock_parser
            
            # Mock initialize to fail
            mock_parser.initialize = AsyncMock(side_effect=Exception("Init failed"))
            
            # Mock cleanup method
            mock_parser.cleanup = AsyncMock()
            
            # Call get_responses_for_url and expect it to raise exception
            with pytest.raises(Exception, match="Init failed"):
                await model_validator.get_responses_for_url(url)
            
            # Verify cleanup was called despite initialization failure
            mock_parser.cleanup.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_multiple_calls_safe(self, model_validator):
        """Test that multiple cleanup calls are safe."""
        url = 'https://example.com/multiple-cleanup'
        
        with patch('page_tracker.AiParser') as MockAiParser:
            mock_parser = AsyncMock()
            MockAiParser.return_value = mock_parser
            
            # Mock successful operations
            mock_parser.initialize = AsyncMock()
            mock_parser.scrape_and_cache = AsyncMock(return_value='/tmp/cache_file.txt')
            def api_success_side_effect(*args, **kwargs):
                return ('{"key": "value"}', {})
            mock_parser.get_api_response = MagicMock(side_effect=api_success_side_effect)
            mock_parser.strip_markdown = MagicMock(return_value='{"key": "value"}')
            
            # Mock cleanup method to track calls
            mock_parser.cleanup = AsyncMock()
            
            # Manually call cleanup multiple times to test safety
            await mock_parser.cleanup()
            await mock_parser.cleanup()
            
            # Call get_responses_for_url (which will call cleanup again)
            result = await model_validator.get_responses_for_url(url)
            
            # Verify cleanup was called multiple times safely
            assert mock_parser.cleanup.call_count >= 3
    
    @pytest.mark.asyncio
    async def test_cleanup_with_partial_prompt_failure(self, model_validator):
        """Test cleanup when some prompts succeed and others fail."""
        url = 'https://example.com/partial-fail'
        
        with patch('page_tracker.AiParser') as MockAiParser:
            mock_parser = AsyncMock()
            MockAiParser.return_value = mock_parser
            
            # Mock successful initialization and scraping
            mock_parser.initialize = AsyncMock()
            mock_parser.scrape_and_cache = AsyncMock(return_value='/tmp/cache_file.txt')
            
            # Mock API responses: first succeeds, second fails, third succeeds
            api_responses = [
                ('{"success": "first"}', {}),
                Exception("Second prompt failed"),
                ('{"success": "third"}', {})
            ]
            
            def api_side_effect(*args, **kwargs):
                response = api_responses.pop(0)
                if isinstance(response, Exception):
                    raise response
                return response
            
            mock_parser.get_api_response = MagicMock(side_effect=api_side_effect)
            mock_parser.strip_markdown = MagicMock(side_effect=lambda x: x)
            
            # Mock cleanup method
            mock_parser.cleanup = AsyncMock()
            
            # Call get_responses_for_url
            result = await model_validator.get_responses_for_url(url)
            
            # Verify cleanup was called
            mock_parser.cleanup.assert_called_once()
            
            # Verify results: first and third succeed, second fails
            assert len(result) == 3
            assert result[0] == {url: {"success": "first"}}
            assert result[1] is None  # Failed prompt
            assert result[2] == {url: {"success": "third"}}
    
    @pytest.mark.asyncio
    async def test_cleanup_preserves_error_information(self, model_validator):
        """Test that cleanup doesn't interfere with error reporting."""
        url = 'https://example.com/error-info'
        
        with patch('page_tracker.AiParser') as MockAiParser:
            mock_parser = AsyncMock()
            MockAiParser.return_value = mock_parser
            
            # Mock initialize to fail with specific error
            test_error = ValueError("Specific test error")
            mock_parser.initialize = AsyncMock(side_effect=test_error)
            
            # Mock cleanup method
            mock_parser.cleanup = AsyncMock()
            
            # Call get_responses_for_url and verify specific error is raised
            with pytest.raises(ValueError, match="Specific test error"):
                await model_validator.get_responses_for_url(url)
            
            # Verify cleanup was called
            mock_parser.cleanup.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_failure_doesnt_mask_original_error(self, model_validator):
        """Test that cleanup failures don't mask original processing errors."""
        url = 'https://example.com/cleanup-failure'
        
        with patch('page_tracker.AiParser') as MockAiParser:
            mock_parser = AsyncMock()
            MockAiParser.return_value = mock_parser
            
            # Mock successful initialization but scraping failure
            mock_parser.initialize = AsyncMock()
            scraping_error = RuntimeError("Original scraping error")
            mock_parser.scrape_and_cache = AsyncMock(side_effect=scraping_error)
            
            # Mock cleanup to fail
            cleanup_error = IOError("Cleanup failed")
            mock_parser.cleanup = AsyncMock(side_effect=cleanup_error)
            
            # The original scraping error should be preserved (returns empty list)
            # Cleanup error should be logged but not raised
            result = await model_validator.get_responses_for_url(url)
            
            # Verify cleanup was attempted despite failure
            mock_parser.cleanup.assert_called_once()
            
            # Verify original behavior is preserved (empty list for scraping failure)
            assert result == []
    
    @pytest.mark.asyncio 
    async def test_cleanup_during_prompt_processing_loop(self, model_validator):
        """Test cleanup occurs even when errors happen during prompt processing loop."""
        url = 'https://example.com/loop-error'
        
        with patch('page_tracker.AiParser') as MockAiParser:
            mock_parser = AsyncMock()
            MockAiParser.return_value = mock_parser
            
            # Mock successful initialization and scraping
            mock_parser.initialize = AsyncMock()
            mock_parser.scrape_and_cache = AsyncMock(return_value='/tmp/cache_file.txt')
            
            # Mock first prompt to succeed, then raise an unexpected error
            call_count = 0
            def api_side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return ('{"success": "first"}', {})
                else:
                    # Simulate an unexpected error during processing
                    raise KeyboardInterrupt("Simulated interruption")
            
            mock_parser.get_api_response = MagicMock(side_effect=api_side_effect)
            mock_parser.strip_markdown = MagicMock(side_effect=lambda x: x)
            
            # Mock cleanup method
            mock_parser.cleanup = AsyncMock()
            
            # Call should raise the KeyboardInterrupt but cleanup should still happen
            with pytest.raises(KeyboardInterrupt, match="Simulated interruption"):
                await model_validator.get_responses_for_url(url)
            
            # Verify cleanup was called despite the interruption
            mock_parser.cleanup.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_successful_processing_still_calls_cleanup(self, model_validator):
        """Test that cleanup is called even when everything succeeds."""
        url = 'https://example.com/success'
        
        with patch('page_tracker.AiParser') as MockAiParser:
            mock_parser = AsyncMock()
            MockAiParser.return_value = mock_parser
            
            # Mock all operations to succeed
            mock_parser.initialize = AsyncMock()
            mock_parser.scrape_and_cache = AsyncMock(return_value='/tmp/cache_file.txt')
            mock_parser.get_api_response = MagicMock(return_value=('{"data": "test"}', {}))
            mock_parser.strip_markdown = MagicMock(return_value='{"data": "test"}')
            mock_parser.cleanup = AsyncMock()
            
            # Call get_responses_for_url
            result = await model_validator.get_responses_for_url(url)
            
            # Verify cleanup was called
            mock_parser.cleanup.assert_called_once()
            
            # Verify successful processing
            assert len(result) == 3  # 3 prompts
            assert all(response == {url: {"data": "test"}} for response in result)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])