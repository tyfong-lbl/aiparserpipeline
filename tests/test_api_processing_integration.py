"""
Test suite for API processing integration with cached content.

This test suite verifies that cached content integrates seamlessly with existing
LLM API processing logic as specified in Step 5.4:
- API calls work correctly with cached content
- Prompt template substitution works as before
- API response timing metrics are accurate
- Pipeline logging captures correct information
- Error handling for API failures is preserved
- Method return format is unchanged
- Multiple prompts with same cached content work correctly
"""

import pytest
import tempfile
import time
import shutil
import logging
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import the modules we're testing
import sys
sys.path.append('/Users/TYFong/code/aiparserpipeline')

from page_tracker import AiParser


class TestAPIProcessingIntegration:
    """Test API processing integration with cached content."""

    @pytest.fixture
    def ai_parser(self):
        """Create an AiParser instance for testing."""
        parser = AiParser(
            api_key="test_key",
            api_url="https://test.api.com",
            model="test_model", 
            prompt="Analyze this $PROJECT content: ",
            project_name="Solar Project Alpha"
        )
        return parser

    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary directory for cache file testing."""
        temp_dir = tempfile.mkdtemp(prefix="test_api_integration_")
        yield Path(temp_dir)
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_api_calls_work_correctly_with_cached_content(self, ai_parser, temp_cache_dir):
        """Test that API calls work correctly with cached content."""
        # Create test cache file
        cache_file = temp_cache_dir / "api_test.txt"
        test_content = "This is solar project content for API analysis."
        cache_file.write_text(test_content, encoding='utf-8')
        
        # Set cache file path
        ai_parser._cache_file_path = str(cache_file)
        
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Analysis: Solar project has 100MW capacity."
        ai_parser.client.chat.completions.create = MagicMock(return_value=mock_response)
        
        # Call method
        response_content, llm_metrics = ai_parser.get_api_response()
        
        # Verify API call was made correctly
        ai_parser.client.chat.completions.create.assert_called_once_with(
            model="test_model",
            temperature=0.0,
            messages=[
                {
                    "role": "user",
                    "content": "Analyze this Solar Project Alpha content: This is solar project content for API analysis. "
                }
            ]
        )
        
        # Verify response
        assert response_content == "Analysis: Solar project has 100MW capacity."
        assert llm_metrics['llm_response_status'] is True
        assert llm_metrics['llm_response_error'] is None

    def test_prompt_template_substitution_works_as_before(self, ai_parser, temp_cache_dir):
        """Test that prompt template substitution works correctly."""
        # Test various template patterns
        test_cases = [
            ("Process $PROJECT data: ", "Process Solar Project Alpha data: "),
            ("$PROJECT analysis report", "Solar Project Alpha analysis report"),
            ("Analyze $PROJECT for efficiency", "Analyze Solar Project Alpha for efficiency"),
            ("No template variables", "No template variables"),
        ]
        
        # Create test cache file
        cache_file = temp_cache_dir / "template_test.txt"
        test_content = "Template test content"
        cache_file.write_text(test_content, encoding='utf-8')
        ai_parser._cache_file_path = str(cache_file)
        
        # Mock API response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Template response"
        ai_parser.client.chat.completions.create = MagicMock(return_value=mock_response)
        
        for template, expected_substitution in test_cases:
            # Reset mock for each test
            ai_parser.client.chat.completions.create.reset_mock()
            ai_parser.prompt = template
            
            # Call method
            ai_parser.get_api_response()
            
            # Verify template substitution
            call_args = ai_parser.client.chat.completions.create.call_args
            actual_content = call_args.kwargs['messages'][0]['content']
            
            # Should contain substituted template and cached content
            assert actual_content == f"{expected_substitution}{test_content} "

    def test_api_response_timing_metrics_are_accurate(self, ai_parser, temp_cache_dir):
        """Test that API call timing and metrics are accurate."""
        # Create test cache file
        cache_file = temp_cache_dir / "timing_test.txt"
        test_content = "Timing test content"
        cache_file.write_text(test_content, encoding='utf-8')
        ai_parser._cache_file_path = str(cache_file)
        
        # Mock API response with controlled timing
        def mock_api_call(*args, **kwargs):
            time.sleep(0.1)  # Simulate 100ms API call
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Timing response"
            return mock_response
        
        ai_parser.client.chat.completions.create = mock_api_call
        
        # Call method and measure timing
        start_time = time.perf_counter()
        response_content, llm_metrics = ai_parser.get_api_response()
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # Verify timing metrics
        assert 'llm_processing_time' in llm_metrics
        processing_time = llm_metrics['llm_processing_time']
        
        # Processing time should be approximately 100ms (within reasonable bounds)
        assert 0.08 < processing_time < 0.15  # Allow for some timing variation
        
        # Total time should be close to processing time (cache read is very fast)
        assert abs(total_time - processing_time) < 0.01

    def test_pipeline_logging_captures_correct_information(self, ai_parser, temp_cache_dir):
        """Test that pipeline logging integration works correctly."""
        # Create test cache file
        cache_file = temp_cache_dir / "logging_test.txt"
        test_content = "Pipeline logging test content"
        cache_file.write_text(test_content, encoding='utf-8')
        ai_parser._cache_file_path = str(cache_file)
        
        # Mock API response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Logging test response"
        ai_parser.client.chat.completions.create = MagicMock(return_value=mock_response)
        
        # Call method
        response_content, llm_metrics = ai_parser.get_api_response()
        
        # Verify llm_metrics structure for pipeline logging compatibility
        required_keys = ['llm_response_status', 'llm_response_error', 'llm_processing_time']
        for key in required_keys:
            assert key in llm_metrics, f"Required key '{key}' missing from llm_metrics"
        
        # Verify data types for pipeline logging
        assert isinstance(llm_metrics['llm_response_status'], bool)
        assert llm_metrics['llm_response_error'] is None or isinstance(llm_metrics['llm_response_error'], str)
        assert isinstance(llm_metrics['llm_processing_time'], (int, float))
        
        # Verify successful response metrics
        assert llm_metrics['llm_response_status'] is True
        assert llm_metrics['llm_response_error'] is None
        assert llm_metrics['llm_processing_time'] > 0

    def test_error_handling_for_api_failures_is_preserved(self, ai_parser, temp_cache_dir):
        """Test that existing error handling for API failures is preserved."""
        # Create test cache file
        cache_file = temp_cache_dir / "error_test.txt"
        test_content = "Error handling test content"
        cache_file.write_text(test_content, encoding='utf-8')
        ai_parser._cache_file_path = str(cache_file)
        
        # Test various API error scenarios
        api_errors = [
            Exception("API connection failed"),
            ConnectionError("Network unreachable"),
            TimeoutError("Request timeout"),
            ValueError("Invalid API response"),
        ]
        
        for api_error in api_errors:
            # Mock API call to raise error
            ai_parser.client.chat.completions.create = MagicMock(side_effect=api_error)
            
            # Call method - should handle error gracefully
            response_content, llm_metrics = ai_parser.get_api_response()
            
            # Verify error handling
            assert response_content is None
            assert llm_metrics['llm_response_status'] is False
            assert str(api_error) in llm_metrics['llm_response_error']
            assert isinstance(llm_metrics['llm_processing_time'], (int, float))

    def test_method_returns_same_format_as_before(self, ai_parser, temp_cache_dir):
        """Test that method return format is unchanged."""
        # Create test cache file
        cache_file = temp_cache_dir / "format_test.txt"
        test_content = "Return format test content"
        cache_file.write_text(test_content, encoding='utf-8')
        ai_parser._cache_file_path = str(cache_file)
        
        # Mock API response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Format test response"
        ai_parser.client.chat.completions.create = MagicMock(return_value=mock_response)
        
        # Call method
        result = ai_parser.get_api_response()
        
        # Verify return format: tuple with 2 elements
        assert isinstance(result, tuple)
        assert len(result) == 2
        
        response_content, llm_metrics = result
        
        # Verify response_content type
        assert isinstance(response_content, str)
        
        # Verify llm_metrics type and structure
        assert isinstance(llm_metrics, dict)
        expected_keys = {'llm_response_status', 'llm_response_error', 'llm_processing_time'}
        assert expected_keys.issubset(llm_metrics.keys())

    def test_multiple_prompts_with_same_cached_content(self, ai_parser, temp_cache_dir):
        """Test that multiple prompts work correctly with same cached content."""
        # Create test cache file
        cache_file = temp_cache_dir / "multi_prompt_test.txt"
        test_content = "Multi-prompt test content for solar analysis"
        cache_file.write_text(test_content, encoding='utf-8')
        ai_parser._cache_file_path = str(cache_file)
        
        # Test different prompts
        prompts = [
            "Analyze $PROJECT efficiency: ",
            "Calculate $PROJECT capacity: ",
            "Evaluate $PROJECT performance: ",
        ]
        
        expected_responses = [
            "Efficiency analysis complete",
            "Capacity calculation done", 
            "Performance evaluation finished",
        ]
        
        results = []
        
        for i, prompt in enumerate(prompts):
            # Set new prompt
            ai_parser.prompt = prompt
            
            # Mock appropriate response
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = expected_responses[i]
            ai_parser.client.chat.completions.create = MagicMock(return_value=mock_response)
            
            # Call method
            response_content, llm_metrics = ai_parser.get_api_response()
            results.append((response_content, llm_metrics))
            
            # Verify API call used correct prompt and same content
            call_args = ai_parser.client.chat.completions.create.call_args
            message_content = call_args.kwargs['messages'][0]['content']
            
            # Should contain prompt with project substitution and cached content
            expected_prompt = prompt.replace('$PROJECT', 'Solar Project Alpha')
            assert message_content == f"{expected_prompt}{test_content} "
            
            # Verify response
            assert response_content == expected_responses[i]
            assert llm_metrics['llm_response_status'] is True
        
        # All calls should have used the same cached content but different prompts
        assert len(results) == 3
        assert all(result[1]['llm_response_status'] for result in results)

    def test_end_to_end_flow_from_cache_to_api_response(self, ai_parser, temp_cache_dir):
        """Test complete flow from cache file to API response."""
        # Create test cache file with realistic content
        cache_file = temp_cache_dir / "end_to_end_test.txt"
        realistic_content = """
        Solar Project Alpha - Technical Specifications
        
        Capacity: 250 MW DC
        Location: California Desert
        Technology: Photovoltaic panels
        Annual Generation: 500 GWh
        Operational Date: 2024
        
        Environmental Impact:
        - CO2 reduction: 200,000 tons/year
        - Water usage: Minimal
        - Land use: 1,200 acres
        """
        cache_file.write_text(realistic_content, encoding='utf-8')
        ai_parser._cache_file_path = str(cache_file)
        
        # Mock realistic API response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """
        {
            "project_name": "Solar Project Alpha",
            "capacity_mw": 250,
            "technology": "Photovoltaic",
            "annual_generation_gwh": 500,
            "co2_reduction_tons": 200000
        }
        """
        ai_parser.client.chat.completions.create = MagicMock(return_value=mock_response)
        
        # Set realistic prompt
        ai_parser.prompt = "Extract key metrics from this $PROJECT data in JSON format: "
        
        # Execute complete flow
        response_content, llm_metrics = ai_parser.get_api_response()
        
        # Verify complete integration
        call_args = ai_parser.client.chat.completions.create.call_args
        api_message = call_args.kwargs['messages'][0]['content']
        
        # Should contain prompt template substitution
        assert "Extract key metrics from this Solar Project Alpha data in JSON format: " in api_message
        
        # Should contain cached content
        assert "Capacity: 250 MW DC" in api_message
        assert "CO2 reduction: 200,000 tons/year" in api_message
        
        # Should return proper response
        assert "Solar Project Alpha" in response_content
        assert "250" in response_content
        
        # Should have proper metrics
        assert llm_metrics['llm_response_status'] is True
        assert llm_metrics['llm_response_error'] is None
        assert llm_metrics['llm_processing_time'] > 0

    def test_api_call_parameters_preservation(self, ai_parser, temp_cache_dir):
        """Test that all API call parameters are preserved correctly."""
        # Create test cache file
        cache_file = temp_cache_dir / "params_test.txt"
        test_content = "API parameters test content"
        cache_file.write_text(test_content, encoding='utf-8')
        ai_parser._cache_file_path = str(cache_file)
        
        # Mock API response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Parameters test response"
        ai_parser.client.chat.completions.create = MagicMock(return_value=mock_response)
        
        # Call method
        ai_parser.get_api_response()
        
        # Verify all API parameters are correct
        call_args = ai_parser.client.chat.completions.create.call_args
        
        # Check model parameter
        assert call_args.kwargs['model'] == "test_model"
        
        # Check temperature parameter
        assert call_args.kwargs['temperature'] == 0.0
        
        # Check messages structure
        messages = call_args.kwargs['messages']
        assert len(messages) == 1
        assert messages[0]['role'] == 'user'
        assert 'content' in messages[0]
        
        # Check content includes both prompt and cached content
        content = messages[0]['content']
        assert "Analyze this Solar Project Alpha content: " in content
        assert test_content in content


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])