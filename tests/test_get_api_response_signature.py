"""
Test suite for get_api_response() method signature changes.

This test suite verifies the signature changes for get_api_response() method
as part of Step 5.1 of the AiParser refactoring:
- Method no longer accepts fulltext parameter
- Backward compatibility warnings work correctly
- Existing API call functionality is preserved
- Method return format remains unchanged
"""

import pytest
import warnings
import logging
from unittest.mock import Mock, patch, MagicMock

# Import the modules we're testing
import sys
sys.path.append('/Users/TYFong/code/aiparserpipeline')

from page_tracker import AiParser


class TestGetApiResponseSignature:
    """Test signature changes in get_api_response() method."""

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

    def test_method_signature_no_fulltext_parameter(self, ai_parser):
        """Test that method signature no longer accepts fulltext parameter."""
        import inspect
        
        # Get method signature
        sig = inspect.signature(ai_parser.get_api_response)
        
        # Verify fulltext parameter is not in signature
        assert 'fulltext' not in sig.parameters, "fulltext parameter should be removed from method signature"
        
        # Verify method can be called without parameters (assuming cache-based content)
        # This will fail until we implement cache reading, but tests the signature
        try:
            # Mock the cache file reading for now
            with patch.object(ai_parser, '_cache_file_path', '/fake/cache/path'):
                with patch('builtins.open', create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = "Test content"
                    # Should not raise TypeError for missing fulltext parameter
                    result = ai_parser.get_api_response()
                    # Method should return tuple (response_content, llm_metrics)
                    assert isinstance(result, tuple)
                    assert len(result) == 2
        except Exception as e:
            # The method might fail for other reasons (API call, etc.) but not due to signature
            assert "fulltext" not in str(e), f"Error should not be related to fulltext parameter: {e}"

    def test_backward_compatibility_warning(self, ai_parser, caplog):
        """Test that passing fulltext parameter generates appropriate deprecation warning."""
        # Mock API call to avoid actual network requests
        from unittest.mock import MagicMock
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        ai_parser.client.chat.completions.create = MagicMock(return_value=mock_response)
        
        import logging
        with caplog.at_level(logging.WARNING):
            # Should work but generate deprecation warning
            result = ai_parser.get_api_response(fulltext="test content")
            
            # Should return proper result format
            assert isinstance(result, tuple)
            assert len(result) == 2
            
            # Should log deprecation warning
            warning_logs = [record for record in caplog.records if record.levelname == 'WARNING']
            assert len(warning_logs) > 0
            
            deprecation_warning = any("DEPRECATED" in record.message and "fulltext parameter" in record.message 
                                    for record in warning_logs)
            assert deprecation_warning, "Should log deprecation warning for fulltext parameter"

    def test_method_exists_and_callable(self, ai_parser):
        """Test that method still exists and is callable."""
        # Method should exist
        assert hasattr(ai_parser, 'get_api_response')
        
        # Method should be callable
        assert callable(getattr(ai_parser, 'get_api_response'))

    def test_return_format_unchanged(self, ai_parser):
        """Test that method return format is identical to original implementation."""
        # Mock successful API call and cache file reading
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test API response"
        
        # Mock the OpenAI client
        ai_parser.client.chat.completions.create = MagicMock(return_value=mock_response)
        
        # Mock cache file reading
        with patch.object(ai_parser, '_cache_file_path', '/fake/cache/path'):
            with patch('builtins.open', create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = "Test cached content"
                
                # Call method without fulltext parameter
                result = ai_parser.get_api_response()
                
                # Verify return format: (response_content, llm_metrics)
                assert isinstance(result, tuple)
                assert len(result) == 2
                
                response_content, llm_metrics = result
                
                # Verify response content
                assert response_content == "Test API response"
                
                # Verify llm_metrics format
                assert isinstance(llm_metrics, dict)
                expected_keys = {'llm_response_status', 'llm_response_error', 'llm_processing_time'}
                assert expected_keys.issubset(llm_metrics.keys())
                assert llm_metrics['llm_response_status'] is True
                assert llm_metrics['llm_response_error'] is None
                assert isinstance(llm_metrics['llm_processing_time'], (int, float))

    def test_api_call_logic_preserved(self, ai_parser):
        """Test that existing API call logic is preserved."""
        # Mock successful API call and cache file reading
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "API response content"
        
        # Mock the OpenAI client
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        ai_parser.client = mock_client
        
        # Mock cache file reading
        test_content = "This is test cached content"
        with patch.object(ai_parser, '_cache_file_path', '/fake/cache/path'):
            with patch('builtins.open', create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = test_content
                
                # Call method
                response_content, llm_metrics = ai_parser.get_api_response()
                
                # Verify API was called correctly
                mock_client.chat.completions.create.assert_called_once()
                call_args = mock_client.chat.completions.create.call_args
                
                # Verify API call parameters
                assert call_args.kwargs['model'] == "test_model"
                assert call_args.kwargs['temperature'] == 0.0
                assert len(call_args.kwargs['messages']) == 1
                
                # Verify message content includes prompt template substitution and cached content
                message_content = call_args.kwargs['messages'][0]['content']
                assert "Test prompt for Test Project" in message_content
                assert test_content in message_content

    def test_error_handling_preserved(self, ai_parser):
        """Test that existing error handling is preserved."""
        # Mock API call failure
        ai_parser.client.chat.completions.create = MagicMock(side_effect=Exception("API Error"))
        
        # Mock cache file reading
        with patch.object(ai_parser, '_cache_file_path', '/fake/cache/path'):
            with patch('builtins.open', create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = "Test content"
                
                # Call method
                response_content, llm_metrics = ai_parser.get_api_response()
                
                # Verify error handling
                assert response_content is None
                assert llm_metrics['llm_response_status'] is False
                assert "API Error" in llm_metrics['llm_response_error']
                assert isinstance(llm_metrics['llm_processing_time'], (int, float))

    def test_prompt_template_substitution(self, ai_parser):
        """Test that prompt template substitution works correctly."""
        # Set a prompt with template variables
        ai_parser.prompt = "Analyze this content for project $PROJECT: "
        
        # Mock successful API call and cache file reading
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Analysis result"
        
        ai_parser.client.chat.completions.create = MagicMock(return_value=mock_response)
        
        # Mock cache file reading
        with patch.object(ai_parser, '_cache_file_path', '/fake/cache/path'):
            with patch('builtins.open', create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = "Content to analyze"
                
                # Call method
                ai_parser.get_api_response()
                
                # Verify template substitution
                call_args = ai_parser.client.chat.completions.create.call_args
                message_content = call_args.kwargs['messages'][0]['content']
                
                # Should contain substituted project name
                assert "Analyze this content for project Test Project:" in message_content
                # Should not contain template variable
                assert "$PROJECT" not in message_content

    def test_pipeline_logging_compatibility(self, ai_parser):
        """Test that pipeline logging integration is maintained."""
        # Mock successful API call and cache file reading
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response content"
        
        ai_parser.client.chat.completions.create = MagicMock(return_value=mock_response)
        
        # Mock cache file reading
        with patch.object(ai_parser, '_cache_file_path', '/fake/cache/path'):
            with patch('builtins.open', create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = "Cached content"
                
                # Call method
                response_content, llm_metrics = ai_parser.get_api_response()
                
                # Verify llm_metrics structure is compatible with pipeline logging
                required_keys = ['llm_response_status', 'llm_response_error', 'llm_processing_time']
                for key in required_keys:
                    assert key in llm_metrics, f"Required key '{key}' missing from llm_metrics"
                
                # Verify data types are correct for logging
                assert isinstance(llm_metrics['llm_response_status'], bool)
                assert llm_metrics['llm_response_error'] is None or isinstance(llm_metrics['llm_response_error'], str)
                assert isinstance(llm_metrics['llm_processing_time'], (int, float))


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])