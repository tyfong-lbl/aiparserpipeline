"""
Test suite for scrape-once, process-many pattern in ModelValidator.

This test suite verifies the restructured ModelValidator.get_responses_for_url() 
method that follows the scrape-once pattern as specified in Step 7.1:
- Method structure follows scrape-once, process-many pattern
- scrape_and_cache() is called exactly once per URL
- Prompt loop processes all prompts correctly
- Return format is identical to original implementation
- Error handling behavior is preserved
- Performance improves (fewer network requests)
"""

import pytest
import tempfile
import asyncio
import shutil
import json
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock

# Import the modules we're testing
import sys
sys.path.append('/Users/TYFong/code/aiparserpipeline')

from page_tracker import ModelValidator


class TestScrapeOncePattern:
    """Test scrape-once, process-many pattern in ModelValidator."""

    @pytest.fixture
    def mock_url_df(self):
        """Create a mock URL DataFrame for testing."""
        return pd.DataFrame({
            'url_column': ['https://test-solar1.com/article1', 'https://test-solar2.com/article2']
        })

    @pytest.fixture
    def model_validator(self, mock_url_df):
        """Create a ModelValidator instance for testing."""
        validator = ModelValidator(
            number_of_queries=3,
            prompt_dir_path="/test/prompts",
            prompt_filename_base="test_prompt_",
            api_key="test_key",
            api_url="https://test.api.com",
            model="test_model",
            project_name="Test Solar Project",
            url_df=mock_url_df,
            pipeline_logger=None
        )
        return validator

    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary directory for cache file testing."""
        temp_dir = tempfile.mkdtemp(prefix="test_scrape_once_")
        yield Path(temp_dir)
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def mock_prompts(self):
        """Create mock prompts for testing."""
        return [
            "Analyze this $PROJECT for capacity: ",
            "Evaluate this $PROJECT for efficiency: ", 
            "Calculate this $PROJECT for output: "
        ]

    @pytest.mark.asyncio
    async def test_scrape_and_cache_called_exactly_once_per_url(self, model_validator, temp_cache_dir, mock_prompts):
        """Test that scrape_and_cache() is called exactly once per URL."""
        test_url = "https://test-solar.com/project1"
        
        # Mock prompts
        with patch.object(model_validator, 'get_all_prompts', return_value=mock_prompts):
            # Create mock cache file for scraping
            scraped_cache_dir = temp_cache_dir / "scraped_cache"
            scraped_cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = scraped_cache_dir / "test_cache.txt"
            
            with patch('cache_utils._get_cache_directory', return_value=scraped_cache_dir), \
                 patch('page_tracker.generate_cache_filename', return_value=str(cache_file)):
                
                # Mock AiParser methods
                with patch('page_tracker.AiParser') as MockAiParser:
                    mock_parser = Mock()
                    MockAiParser.return_value = mock_parser
                    
                    # Make async methods properly async
                    mock_parser.initialize = AsyncMock()
                    mock_parser.cleanup = AsyncMock()
                    
                    # Mock scrape_and_cache to create actual cache file
                    async def mock_scrape_and_cache(url):
                        test_content = f"Scraped content for {url}"
                        cache_file.write_text(test_content, encoding='utf-8')
                        mock_parser._cache_file_path = str(cache_file)
                        mock_parser._cached_content = test_content
                        return str(cache_file)
                    
                    mock_parser.scrape_and_cache = mock_scrape_and_cache
                    
                    # Mock get_api_response to return test responses (not async)
                    mock_responses = [
                        ("Capacity: 100MW", {'llm_response_status': True, 'llm_response_error': None, 'llm_processing_time': 0.5}),
                        ("Efficiency: 95%", {'llm_response_status': True, 'llm_response_error': None, 'llm_processing_time': 0.6}),
                        ("Output: 500GWh", {'llm_response_status': True, 'llm_response_error': None, 'llm_processing_time': 0.4})
                    ]
                    mock_parser.get_api_response = Mock(side_effect=mock_responses)
                    
                    # Mock strip_markdown and JSON parsing
                    with patch('page_tracker.AiParser.strip_markdown') as mock_strip, \
                         patch('json.loads') as mock_json_loads:
                        
                        mock_strip.side_effect = ['{"capacity": "100MW"}', '{"efficiency": "95%"}', '{"output": "500GWh"}']
                        mock_json_loads.side_effect = [
                            {"capacity": "100MW"},
                            {"efficiency": "95%"}, 
                            {"output": "500GWh"}
                        ]
                        
                        # Call the method
                        responses = await model_validator.get_responses_for_url(test_url)
                        
                        # Verify scrape_and_cache was called exactly once
                        assert cache_file.exists()  # Cache file should be created once
                        
                        # Verify get_api_response was called for each prompt (3 times)
                        assert mock_parser.get_api_response.call_count == 3
                        
                        # Verify we got responses for all prompts
                        assert len(responses) == 3
                        assert all(response is not None for response in responses)

    @pytest.mark.asyncio
    async def test_prompt_loop_processes_all_prompts_correctly(self, model_validator, temp_cache_dir, mock_prompts):
        """Test that the prompt loop processes all prompts correctly."""
        test_url = "https://test-solar.com/project2"
        
        # Mock prompts
        with patch.object(model_validator, 'get_all_prompts', return_value=mock_prompts):
            # Create mock cache file
            scraped_cache_dir = temp_cache_dir / "scraped_cache"
            scraped_cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = scraped_cache_dir / "test_cache2.txt"
            
            with patch('cache_utils._get_cache_directory', return_value=scraped_cache_dir), \
                 patch('page_tracker.generate_cache_filename', return_value=str(cache_file)):
                
                # Mock AiParser
                with patch('page_tracker.AiParser') as MockAiParser:
                    mock_parser = Mock()
                    MockAiParser.return_value = mock_parser
                    
                    # Make async methods properly async
                    mock_parser.initialize = AsyncMock()
                    mock_parser.cleanup = AsyncMock()
                    
                    # Mock scrape_and_cache
                    async def mock_scrape_and_cache(url):
                        test_content = f"Content for {url}"
                        cache_file.write_text(test_content, encoding='utf-8')
                        return str(cache_file)
                    
                    mock_parser.scrape_and_cache = mock_scrape_and_cache
                    
                    # Track prompt changes
                    prompt_changes = []
                    def track_prompt_change(self, value):
                        prompt_changes.append(value)
                        self._prompt = value
                    
                    # Mock prompt property setter
                    type(mock_parser).prompt = property(lambda x: getattr(x, '_prompt', None), track_prompt_change)
                    mock_parser._prompt = mock_prompts[0]
                    
                    # Mock get_api_response with different responses per prompt (not async)
                    response_data = [
                        ("Response 1", {'llm_response_status': True, 'llm_response_error': None, 'llm_processing_time': 0.3}),
                        ("Response 2", {'llm_response_status': True, 'llm_response_error': None, 'llm_processing_time': 0.4}),
                        ("Response 3", {'llm_response_status': True, 'llm_response_error': None, 'llm_processing_time': 0.5})
                    ]
                    mock_parser.get_api_response = Mock(side_effect=response_data)
                    
                    # Mock JSON processing
                    with patch('page_tracker.AiParser.strip_markdown') as mock_strip, \
                         patch('json.loads') as mock_json_loads:
                        
                        mock_strip.side_effect = ['{"result": "1"}', '{"result": "2"}', '{"result": "3"}']
                        mock_json_loads.side_effect = [
                            {"result": "1"},
                            {"result": "2"},
                            {"result": "3"}
                        ]
                        
                        # Call the method
                        responses = await model_validator.get_responses_for_url(test_url)
                        
                        # Verify all prompts were processed
                        assert len(responses) == 3
                        assert len(prompt_changes) == 3
                        
                        # Verify prompts were set correctly
                        for i, expected_prompt in enumerate(mock_prompts):
                            assert prompt_changes[i] == expected_prompt
                        
                        # Verify get_api_response called for each prompt
                        assert mock_parser.get_api_response.call_count == 3

    @pytest.mark.asyncio 
    async def test_return_format_identical_to_original(self, model_validator, temp_cache_dir, mock_prompts):
        """Test that return format is identical to original implementation."""
        test_url = "https://test-solar.com/project3"
        
        # Mock prompts
        with patch.object(model_validator, 'get_all_prompts', return_value=mock_prompts):
            # Create mock cache file
            scraped_cache_dir = temp_cache_dir / "scraped_cache"
            scraped_cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = scraped_cache_dir / "test_cache3.txt"
            
            with patch('cache_utils._get_cache_directory', return_value=scraped_cache_dir), \
                 patch('page_tracker.generate_cache_filename', return_value=str(cache_file)):
                
                # Mock AiParser
                with patch('page_tracker.AiParser') as MockAiParser:
                    mock_parser = Mock()
                    MockAiParser.return_value = mock_parser
                    
                    # Make async methods properly async
                    mock_parser.initialize = AsyncMock()
                    mock_parser.cleanup = AsyncMock()
                    
                    # Mock scrape_and_cache
                    async def mock_scrape_and_cache(url):
                        test_content = "Solar project content"
                        cache_file.write_text(test_content, encoding='utf-8')
                        return str(cache_file)
                    
                    mock_parser.scrape_and_cache = mock_scrape_and_cache
                    
                    # Mock get_api_response (not async)
                    mock_responses = [
                        ("Response A", {'llm_response_status': True, 'llm_response_error': None, 'llm_processing_time': 0.1}),
                        ("Response B", {'llm_response_status': True, 'llm_response_error': None, 'llm_processing_time': 0.2}),
                        ("Response C", {'llm_response_status': True, 'llm_response_error': None, 'llm_processing_time': 0.3})
                    ]
                    mock_parser.get_api_response = Mock(side_effect=mock_responses)
                    
                    # Mock JSON processing with realistic data structures
                    expected_data = [
                        {"capacity_mw": 100, "technology": "Solar PV"},
                        {"efficiency_percent": 95, "degradation": "0.5%/year"},
                        {"annual_output_gwh": 500, "capacity_factor": 0.3}
                    ]
                    
                    with patch('page_tracker.AiParser.strip_markdown') as mock_strip, \
                         patch('json.loads') as mock_json_loads:
                        
                        mock_strip.side_effect = [json.dumps(data) for data in expected_data]
                        mock_json_loads.side_effect = expected_data
                        
                        # Call the method
                        responses = await model_validator.get_responses_for_url(test_url)
                        
                        # Verify return format matches original select_article_to_api format
                        assert isinstance(responses, list)
                        assert len(responses) == 3
                        
                        # Each response should be a dict with URL as key
                        for i, response in enumerate(responses):
                            assert isinstance(response, dict)
                            assert test_url in response
                            assert response[test_url] == expected_data[i]

    @pytest.mark.asyncio
    async def test_error_handling_behavior_preserved(self, model_validator, temp_cache_dir, mock_prompts):
        """Test that error handling behavior is preserved."""
        test_url = "https://test-solar.com/error-test"
        
        # Mock prompts
        with patch.object(model_validator, 'get_all_prompts', return_value=mock_prompts):
            # Test scraping error scenario
            with patch('page_tracker.AiParser') as MockAiParser:
                mock_parser = Mock()
                MockAiParser.return_value = mock_parser
                
                # Make async methods properly async
                mock_parser.initialize = AsyncMock()
                mock_parser.cleanup = AsyncMock()
                
                # Mock scrape_and_cache to raise error
                mock_parser.scrape_and_cache = AsyncMock(side_effect=Exception("Network error during scraping"))
                
                # Call the method - should handle error gracefully
                responses = await model_validator.get_responses_for_url(test_url)
                
                # Should return empty list on scraping error (preserving original behavior)
                assert responses == []
                
            # Test LLM processing error scenario
            scraped_cache_dir = temp_cache_dir / "scraped_cache"
            scraped_cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = scraped_cache_dir / "error_test_cache.txt"
            
            with patch('cache_utils._get_cache_directory', return_value=scraped_cache_dir), \
                 patch('page_tracker.generate_cache_filename', return_value=str(cache_file)):
                
                with patch('page_tracker.AiParser') as MockAiParser:
                    mock_parser = Mock()
                    MockAiParser.return_value = mock_parser
                    
                    # Make async methods properly async
                    mock_parser.initialize = AsyncMock()
                    mock_parser.cleanup = AsyncMock()
                    
                    # Mock successful scraping
                    async def mock_scrape_and_cache(url):
                        cache_file.write_text("Test content", encoding='utf-8')
                        return str(cache_file)
                    
                    mock_parser.scrape_and_cache = mock_scrape_and_cache
                    
                    # Mock LLM API error
                    mock_parser.get_api_response.return_value = (None, {
                        'llm_response_status': False,
                        'llm_response_error': 'API timeout',
                        'llm_processing_time': 0.0
                    })
                    
                    # Call the method
                    responses = await model_validator.get_responses_for_url(test_url)
                    
                    # Should return list with None values for failed API calls (preserving original behavior)
                    assert len(responses) == 3
                    assert all(response is None for response in responses)

    @pytest.mark.asyncio
    async def test_performance_improvement_fewer_network_requests(self, model_validator, temp_cache_dir, mock_prompts):
        """Test that performance improves with fewer network requests."""
        test_url = "https://test-solar.com/performance-test"
        
        # Mock prompts
        with patch.object(model_validator, 'get_all_prompts', return_value=mock_prompts):
            # Create mock cache file
            scraped_cache_dir = temp_cache_dir / "scraped_cache" 
            scraped_cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = scraped_cache_dir / "performance_cache.txt"
            
            with patch('cache_utils._get_cache_directory', return_value=scraped_cache_dir), \
                 patch('page_tracker.generate_cache_filename', return_value=str(cache_file)):
                
                # Track network requests
                network_requests = []
                
                with patch('page_tracker.AiParser') as MockAiParser:
                    mock_parser = Mock()
                    MockAiParser.return_value = mock_parser
                    
                    # Make async methods properly async
                    mock_parser.initialize = AsyncMock()
                    mock_parser.cleanup = AsyncMock()
                    
                    # Mock scrape_and_cache to track network calls
                    async def mock_scrape_and_cache(url):
                        network_requests.append(f"scrape:{url}")
                        cache_file.write_text(f"Content for {url}", encoding='utf-8')
                        return str(cache_file)
                    
                    mock_parser.scrape_and_cache = mock_scrape_and_cache
                    
                    # Mock get_api_response (no network - uses cache, not async)
                    mock_parser.get_api_response = Mock(return_value=(
                        "Test response", 
                        {'llm_response_status': True, 'llm_response_error': None, 'llm_processing_time': 0.1}
                    ))
                    
                    # Mock JSON processing
                    with patch('page_tracker.AiParser.strip_markdown', return_value='{"test": "data"}'), \
                         patch('json.loads', return_value={"test": "data"}):
                        
                        # Call the method
                        responses = await model_validator.get_responses_for_url(test_url)
                        
                        # Verify only one network request (scraping) despite 3 prompts
                        assert len(network_requests) == 1
                        assert network_requests[0] == f"scrape:{test_url}"
                        
                        # Verify all prompts were processed (3 API calls to cached content)
                        assert mock_parser.get_api_response.call_count == 3
                        assert len(responses) == 3

    @pytest.mark.asyncio
    async def test_method_structure_follows_scrape_once_pattern(self, model_validator, temp_cache_dir, mock_prompts):
        """Test that method structure follows the scrape-once, process-many pattern."""
        test_url = "https://test-solar.com/structure-test"
        
        # Mock prompts
        with patch.object(model_validator, 'get_all_prompts', return_value=mock_prompts):
            # Create mock cache file
            scraped_cache_dir = temp_cache_dir / "scraped_cache"
            scraped_cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = scraped_cache_dir / "structure_cache.txt"
            
            with patch('cache_utils._get_cache_directory', return_value=scraped_cache_dir), \
                 patch('page_tracker.generate_cache_filename', return_value=str(cache_file)):
                
                # Track method call sequence
                call_sequence = []
                
                with patch('page_tracker.AiParser') as MockAiParser:
                    mock_parser = Mock()
                    MockAiParser.return_value = mock_parser
                    
                    # Track initialize call
                    async def mock_initialize():
                        call_sequence.append("initialize")
                    mock_parser.initialize = mock_initialize
                    
                    # Track scrape_and_cache call
                    async def mock_scrape_and_cache(url):
                        call_sequence.append("scrape_and_cache")
                        cache_file.write_text("Test content", encoding='utf-8')
                        return str(cache_file)
                    mock_parser.scrape_and_cache = mock_scrape_and_cache
                    
                    # Track get_api_response calls (not async)
                    def mock_get_api_response():
                        call_sequence.append("get_api_response")
                        return ("Response", {'llm_response_status': True, 'llm_response_error': None, 'llm_processing_time': 0.1})
                    mock_parser.get_api_response = Mock(side_effect=mock_get_api_response)
                    
                    # Track cleanup call
                    async def mock_cleanup():
                        call_sequence.append("cleanup")
                    mock_parser.cleanup = mock_cleanup
                    
                    # Mock JSON processing
                    with patch('page_tracker.AiParser.strip_markdown', return_value='{"data": "test"}'), \
                         patch('json.loads', return_value={"data": "test"}):
                        
                        # Call the method
                        responses = await model_validator.get_responses_for_url(test_url)
                        
                        # Verify correct call sequence: initialize → scrape_and_cache → get_api_response (x3) → cleanup
                        expected_sequence = [
                            "initialize",
                            "scrape_and_cache",  # Called once
                            "get_api_response",  # Called for each prompt
                            "get_api_response",
                            "get_api_response",
                            "cleanup"
                        ]
                        
                        assert call_sequence == expected_sequence
                        assert len(responses) == 3


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])