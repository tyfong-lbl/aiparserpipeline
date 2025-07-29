import pytest
import tempfile
import pandas as pd
import asyncio
import os
import csv
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

# Import the classes we need to test
from pipeline_logger import PipelineLogger
from multi_project_validator import MultiProjectValidator
from page_tracker import ModelValidator, AiParser


class TestPipelineLogging:
    """Comprehensive integration tests for the pipeline logging system."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test output."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def mock_openai_response(self):
        """Mock OpenAI API response."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"test": "response", "status": "success"}'
        return mock_response
    
    @pytest.fixture
    def test_project_data(self):
        """Create test project data."""
        return {
            'project_name': 'TestProject_Integration',
            'test_urls': [
                'https://httpbin.org/html',
                'https://example.com',
                'https://httpbin.org/json'
            ]
        }
    
    def test_pipeline_logger_basic_functionality(self, temp_dir):
        """Test basic PipelineLogger functionality."""
        logger = PipelineLogger(temp_dir)
        
        # Verify log file path
        assert logger.get_log_filepath().parent == temp_dir
        assert logger.get_log_filepath().name.startswith('pipeline_log_')
        assert logger.get_log_filepath().name.endswith('.csv')
        
        # Test logging a successful event
        test_timestamp = datetime.now().astimezone().isoformat()
        logger.log_url_processing(
            url="https://example.com/test",
            project_name="TestProject",
            timestamp=test_timestamp,
            text_extraction_status="True",
            text_extraction_error="None",
            text_length=1000,
            llm_response_status="True",
            llm_response_error="None",
            response_time_ms=1500
        )
        
        # Verify CSV file was created
        assert logger.get_log_filepath().exists()
        
        # Verify CSV content
        with open(logger.get_log_filepath(), 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
            
        assert len(rows) == 2  # Header + 1 data row
        
        # Check headers
        expected_headers = [
            'URL', 'project_name', 'timestamp', 'text_extraction_status',
            'text_extraction_error', 'text_length', 'llm_response_status',
            'llm_response_error', 'response_time_ms'
        ]
        assert rows[0] == expected_headers
        
        # Check data row
        data_row = rows[1]
        assert data_row[0] == "https://example.com/test"
        assert data_row[1] == "TestProject"
        assert data_row[3] == "True"  # text_extraction_status
        assert data_row[4] == "None"  # text_extraction_error
        assert data_row[5] == "1000"  # text_length
        assert data_row[6] == "True"  # llm_response_status
        assert data_row[7] == "None"  # llm_response_error
        assert data_row[8] == "1500"  # response_time_ms
    
    def test_multiple_url_logging(self, temp_dir):
        """Test logging multiple URLs to the same file."""
        logger = PipelineLogger(temp_dir)
        
        test_urls = [
            "https://example.com/article1",
            "https://example.com/article2", 
            "https://example.com/article3"
        ]
        
        # Log multiple URLs
        for i, url in enumerate(test_urls):
            test_timestamp = datetime.now().astimezone().isoformat()
            logger.log_url_processing(
                url=url,
                project_name="TestProject_Multi",
                timestamp=test_timestamp,
                text_extraction_status="True",
                text_extraction_error="None",
                text_length=1000 + i * 100,
                llm_response_status="True",
                llm_response_error="None",
                response_time_ms=1500 + i * 200
            )
        
        # Verify all URLs were logged to the same file
        with open(logger.get_log_filepath(), 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        assert len(rows) == 4  # Header + 3 data rows
        
        # Verify each URL is present
        logged_urls = [row[0] for row in rows[1:]]  # Skip header
        assert set(logged_urls) == set(test_urls)
        
        # Verify project name consistency
        project_names = [row[1] for row in rows[1:]]  # Skip header
        assert all(name == "TestProject_Multi" for name in project_names)
    
    @patch('page_tracker.async_playwright')
    @patch('openai.OpenAI')
    def test_aiparser_logging_integration(self, mock_openai_class, mock_playwright, temp_dir, mock_openai_response):
        """Test AiParser integration with logging."""
        # Set up mocks
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_openai_response
        
        # Mock Playwright
        mock_playwright_instance = AsyncMock()
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        
        mock_playwright.return_value.start = AsyncMock(return_value=mock_playwright_instance)
        mock_playwright_instance.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_browser.new_page = AsyncMock(return_value=mock_page)
        mock_page.goto = AsyncMock()
        mock_page.title = AsyncMock(return_value="Test Article Title")
        mock_page.evaluate = AsyncMock(return_value="Test article content for logging integration test.")
        mock_page.close = AsyncMock()
        
        # Create logger outside async function
        logger = PipelineLogger(temp_dir)
        
        async def run_test():
            ai_parser = AiParser(
                api_key="test_key",
                api_url="https://test.api.com",
                model="test_model",
                prompt="Test prompt for $PROJECT",
                project_name="TestProject_AiParser",
                pipeline_logger=logger
            )
            
            # Initialize browser
            await ai_parser.initialize()
            
            # Process a test URL
            result = await ai_parser.select_article_to_api("https://example.com/test-article")
            
            # Clean up
            await ai_parser.cleanup()
            
            return result
        
        # Run the async test
        result = asyncio.run(run_test())
        
        # Verify the result
        assert result is not None
        assert "https://example.com/test-article" in result
        
        # Verify logging occurred
        assert logger.get_log_filepath().exists()
        
        with open(logger.get_log_filepath(), 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        assert len(rows) == 2  # Header + 1 data row
        
        data_row = rows[1]
        assert data_row[0] == "https://example.com/test-article"
        assert data_row[1] == "TestProject_AiParser"
        assert data_row[3] == "True"  # text_extraction_status
        assert data_row[4] == "None"  # text_extraction_error
        assert int(data_row[5]) > 0  # text_length
        assert data_row[6] == "True"  # llm_response_status
        assert data_row[7] == "None"  # llm_response_error
        assert int(data_row[8]) >= 0  # response_time_ms (can be 0 for very fast operations)
    
    def test_csv_output_validation(self, temp_dir):
        """Test CSV output format validation."""
        logger = PipelineLogger(temp_dir)
        
        # Log a test event
        test_timestamp = datetime.now().astimezone().isoformat()
        logger.log_url_processing(
            url="https://httpbin.org/html",
            project_name="TestProject_Validation",
            timestamp=test_timestamp,
            text_extraction_status="True",
            text_extraction_error="None",
            text_length=2500,
            llm_response_status="True",
            llm_response_error="None",
            response_time_ms=3200
        )
        
        # Read and validate CSV
        df = pd.read_csv(logger.get_log_filepath())
        
        # Check column names
        expected_columns = [
            'URL', 'project_name', 'timestamp', 'text_extraction_status',
            'text_extraction_error', 'text_length', 'llm_response_status',
            'llm_response_error', 'response_time_ms'
        ]
        assert list(df.columns) == expected_columns
        
        # Check data types and values
        row = df.iloc[0]
        assert isinstance(row['URL'], str)
        assert isinstance(row['project_name'], str)
        assert isinstance(row['timestamp'], str)
        # CSV stores "True"/"False" as strings, but pandas may convert to boolean
        assert str(row['text_extraction_status']) in ['True', 'False']
        # Check that text_length is numeric (can be int, float, or numpy types)
        assert str(row['text_length']).isdigit() or isinstance(row['text_length'], (int, float))
        assert str(row['llm_response_status']) in ['True', 'False']
        # Check that response_time_ms is numeric (can be int, float, or numpy types)
        assert str(row['response_time_ms']).isdigit() or isinstance(row['response_time_ms'], (int, float))
        
        # Validate timestamp format (should be ISO 8601)
        try:
            datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00'))
        except ValueError:
            pytest.fail("Timestamp is not in valid ISO 8601 format")
        
        # Validate reasonable response time
        assert 0 < row['response_time_ms'] < 30000  # Should be between 0 and 30 seconds
    
    def test_error_handling_logging(self, temp_dir):
        """Test logging of error scenarios."""
        logger = PipelineLogger(temp_dir)
        
        # Log a failed text extraction
        test_timestamp = datetime.now().astimezone().isoformat()
        logger.log_url_processing(
            url="https://invalid-url-for-testing.com",
            project_name="TestProject_Errors",
            timestamp=test_timestamp,
            text_extraction_status="False",
            text_extraction_error="TimeoutError: Page load timeout",
            text_length=0,
            llm_response_status="False",
            llm_response_error="No text to process",
            response_time_ms=5000
        )
        
        # Verify error logging
        with open(logger.get_log_filepath(), 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        data_row = rows[1]
        assert data_row[3] == "False"  # text_extraction_status
        assert "TimeoutError" in data_row[4]  # text_extraction_error
        assert data_row[5] == "0"  # text_length
        assert data_row[6] == "False"  # llm_response_status
        assert "No text to process" in data_row[7]  # llm_response_error
    
    def test_concurrent_logging(self, temp_dir):
        """Test thread-safe concurrent logging."""
        import threading
        import time
        
        logger = PipelineLogger(temp_dir)
        results = []
        
        def log_worker(worker_id):
            for i in range(5):
                test_timestamp = datetime.now().astimezone().isoformat()
                logger.log_url_processing(
                    url=f"https://example.com/worker{worker_id}/article{i}",
                    project_name=f"TestProject_Worker{worker_id}",
                    timestamp=test_timestamp,
                    text_extraction_status="True",
                    text_extraction_error="None",
                    text_length=1000 + i,
                    llm_response_status="True",
                    llm_response_error="None",
                    response_time_ms=1500 + i * 100
                )
                time.sleep(0.01)  # Small delay to simulate real processing
        
        # Create and start multiple threads
        threads = []
        for worker_id in range(3):
            thread = threading.Thread(target=log_worker, args=(worker_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all entries were logged
        with open(logger.get_log_filepath(), 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        # Should have header + 15 data rows (3 workers × 5 entries each)
        assert len(rows) == 16
        
        # Verify no data corruption
        for i, row in enumerate(rows[1:], 1):  # Skip header
            assert len(row) == 9  # All columns present
            assert row[0].startswith("https://example.com/worker")  # Valid URL format
            assert row[1].startswith("TestProject_Worker")  # Valid project name format


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])