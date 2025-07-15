#!/usr/bin/env python3
"""
Deployment verification script for the pipeline logging system.
Tests the complete pipeline with realistic configuration to ensure logging works correctly.
"""

import asyncio
import os
import sys
import tempfile
import csv
import time
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, Mock, AsyncMock

# Import the pipeline components
from pipeline_logger import PipelineLogger
from page_tracker import AiParser
from multi_project_validator import MultiProjectValidator


class DeploymentVerifier:
    """Verifies that the pipeline logging system is working correctly in production."""
    
    def __init__(self):
        self.results = []
        self.start_time = time.time()
        
    def log_result(self, test_name: str, success: bool, message: str, duration: float = 0):
        """Log a test result."""
        status = "✅ PASS" if success else "❌ FAIL"
        self.results.append({
            'test': test_name,
            'status': status,
            'message': message,
            'duration': duration
        })
        print(f"{status} {test_name}: {message} ({duration:.3f}s)")
    
    def test_logger_initialization(self):
        """Test that PipelineLogger can be initialized correctly."""
        test_start = time.time()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                logger = PipelineLogger(Path(temp_dir))
                
                # Check that log file path is created correctly
                log_path = logger.get_log_filepath()
                assert log_path.parent.exists(), "Log directory not created"
                assert log_path.name.startswith('pipeline_log_'), "Invalid log filename format"
                assert log_path.name.endswith('.csv'), "Log file should be CSV"
                
                duration = time.time() - test_start
                self.log_result("Logger Initialization", True, "Logger initialized successfully", duration)
                return True
                
        except Exception as e:
            duration = time.time() - test_start
            self.log_result("Logger Initialization", False, f"Failed: {str(e)}", duration)
            return False
    
    def test_directory_creation(self):
        """Test that pipeline_logs directory can be created."""
        test_start = time.time()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                pipeline_logs_dir = Path(temp_dir) / 'pipeline_logs'
                pipeline_logs_dir.mkdir(parents=True, exist_ok=True)
                
                assert pipeline_logs_dir.exists(), "Pipeline logs directory not created"
                assert pipeline_logs_dir.is_dir(), "Pipeline logs path is not a directory"
                
                duration = time.time() - test_start
                self.log_result("Directory Creation", True, "Pipeline logs directory created", duration)
                return True
                
        except Exception as e:
            duration = time.time() - test_start
            self.log_result("Directory Creation", False, f"Failed: {str(e)}", duration)
            return False
    
    @patch('page_tracker.async_playwright')
    @patch('openai.OpenAI')
    async def test_single_url_processing(self, mock_openai_class, mock_playwright):
        """Test processing a single URL end-to-end with logging."""
        test_start = time.time()
        try:
            # Set up mocks
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = '{"test": "verification", "status": "success"}'
            
            mock_client = Mock()
            mock_openai_class.return_value = mock_client
            mock_client.chat.completions.create.return_value = mock_response
            
            # Mock Playwright - mimics: playwright = await async_playwright().start()
            mock_playwright_instance = AsyncMock()
            mock_browser = AsyncMock()
            mock_page = AsyncMock()
            
            mock_playwright.return_value.start = AsyncMock(return_value=mock_playwright_instance)
            mock_playwright_instance.chromium.launch = AsyncMock(return_value=mock_browser)
            mock_browser.new_page = AsyncMock(return_value=mock_page)
            mock_page.goto = AsyncMock()
            mock_page.title = AsyncMock(return_value="Deployment Verification Test Article")
            mock_page.evaluate = AsyncMock(return_value="This is test content for deployment verification of the pipeline logging system.")
            mock_page.close = AsyncMock()
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create logger
                logger = PipelineLogger(Path(temp_dir))
                
                # Create AiParser with logger
                ai_parser = AiParser(
                    api_key="test_deployment_key",
                    api_url="https://test.deployment.api.com",
                    model="test_deployment_model",
                    prompt="Deployment test prompt for $PROJECT",
                    project_name="DeploymentVerification_Project",
                    pipeline_logger=logger
                )
                
                # Initialize and process URL
                await ai_parser.initialize()
                result = await ai_parser.select_article_to_api("https://example.com/deployment-test")
                await ai_parser.cleanup()
                
                # Verify result
                assert result is not None, "No result returned from URL processing"
                assert "https://example.com/deployment-test" in result, "URL not found in result"
                
                # Verify CSV file creation
                log_file = logger.get_log_filepath()
                assert log_file.exists(), "CSV log file not created"
                
                # Verify CSV content
                with open(log_file, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                
                assert len(rows) == 2, f"Expected 2 rows (header + data), got {len(rows)}"
                
                # Verify header
                expected_headers = [
                    'URL', 'project_name', 'timestamp', 'text_extraction_status',
                    'text_extraction_error', 'text_length', 'llm_response_status',
                    'llm_response_error', 'response_time_ms'
                ]
                assert rows[0] == expected_headers, "CSV headers don't match expected format"
                
                # Verify data row
                data_row = rows[1]
                assert data_row[0] == "https://example.com/deployment-test", "URL mismatch in CSV"
                assert data_row[1] == "DeploymentVerification_Project", "Project name mismatch in CSV"
                assert data_row[3] == "True", "Text extraction should be successful"
                assert data_row[6] == "True", "LLM response should be successful"
                assert int(data_row[8]) >= 0, "Response time should be non-negative"
                
                duration = time.time() - test_start
                self.log_result("Single URL Processing", True, "URL processed and logged successfully", duration)
                return True
                
        except Exception as e:
            duration = time.time() - test_start
            self.log_result("Single URL Processing", False, f"Failed: {str(e)}", duration)
            return False
    
    def test_csv_file_validation(self):
        """Test CSV file format and content validation."""
        test_start = time.time()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                logger = PipelineLogger(Path(temp_dir))
                
                # Log test data
                test_timestamp = datetime.now().astimezone().isoformat()
                logger.log_url_processing(
                    url="https://deployment-test.example.com",
                    project_name="DeploymentTest_CSV",
                    timestamp=test_timestamp,
                    text_extraction_status="True",
                    text_extraction_error="None",
                    text_length=1234,
                    llm_response_status="True",
                    llm_response_error="None",
                    response_time_ms=5678
                )
                
                # Validate file exists and has correct format
                log_file = logger.get_log_filepath()
                assert log_file.exists(), "CSV file not created"
                
                # Check file naming convention
                filename = log_file.name
                assert filename.startswith('pipeline_log_'), "Incorrect filename prefix"
                assert filename.endswith('.csv'), "Incorrect file extension"
                
                # Validate timestamp in filename (YYYY-MM-DD_HH-MM-SS format)
                timestamp_part = filename.replace('pipeline_log_', '').replace('.csv', '')
                datetime.strptime(timestamp_part, '%Y-%m-%d_%H-%M-%S')  # Will raise if invalid
                
                # Validate CSV content structure
                with open(log_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.strip().split('\n')
                    assert len(lines) == 2, "Should have header + 1 data line"
                    
                    # Check that data is properly comma-separated
                    data_line = lines[1]
                    fields = data_line.split(',')
                    assert len(fields) == 9, f"Should have 9 fields, got {len(fields)}"
                
                duration = time.time() - test_start
                self.log_result("CSV File Validation", True, "CSV format and content validated", duration)
                return True
                
        except Exception as e:
            duration = time.time() - test_start
            self.log_result("CSV File Validation", False, f"Failed: {str(e)}", duration)
            return False
    
    def test_performance_measurement(self):
        """Test performance characteristics of logging system."""
        test_start = time.time()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                logger = PipelineLogger(Path(temp_dir))
                
                # Measure logging performance
                num_entries = 100
                log_start = time.time()
                
                for i in range(num_entries):
                    test_timestamp = datetime.now().astimezone().isoformat()
                    logger.log_url_processing(
                        url=f"https://performance-test-{i}.example.com",
                        project_name="PerformanceTest",
                        timestamp=test_timestamp,
                        text_extraction_status="True",
                        text_extraction_error="None",
                        text_length=1000 + i,
                        llm_response_status="True",
                        llm_response_error="None",
                        response_time_ms=1500 + i * 10
                    )
                
                log_duration = time.time() - log_start
                avg_time_per_entry = log_duration / num_entries
                
                # Verify all entries were logged
                with open(logger.get_log_filepath(), 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                
                assert len(rows) == num_entries + 1, f"Expected {num_entries + 1} rows, got {len(rows)}"
                
                # Performance should be reasonable (less than 10ms per entry)
                assert avg_time_per_entry < 0.01, f"Logging too slow: {avg_time_per_entry:.4f}s per entry"
                
                duration = time.time() - test_start
                message = f"Logged {num_entries} entries in {log_duration:.3f}s (avg: {avg_time_per_entry*1000:.2f}ms/entry)"
                self.log_result("Performance Measurement", True, message, duration)
                return True
                
        except Exception as e:
            duration = time.time() - test_start
            self.log_result("Performance Measurement", False, f"Failed: {str(e)}", duration)
            return False
    
    def print_summary(self):
        """Print a summary of all test results."""
        total_duration = time.time() - self.start_time
        passed = sum(1 for r in self.results if "✅ PASS" in r['status'])
        failed = sum(1 for r in self.results if "❌ FAIL" in r['status'])
        
        print("\n" + "="*80)
        print("DEPLOYMENT VERIFICATION SUMMARY")
        print("="*80)
        print(f"Total Tests: {len(self.results)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Total Duration: {total_duration:.3f}s")
        print()
        
        if failed == 0:
            print("🎉 ALL TESTS PASSED - Pipeline logging system is ready for production!")
            return True
        else:
            print("⚠️  SOME TESTS FAILED - Please review and fix issues before deployment.")
            print("\nFailed Tests:")
            for result in self.results:
                if "❌ FAIL" in result['status']:
                    print(f"  - {result['test']}: {result['message']}")
            return False


async def main():
    """Run the deployment verification."""
    print("🚀 Starting Pipeline Logging Deployment Verification")
    print("="*80)
    
    verifier = DeploymentVerifier()
    
    # Run all verification tests
    tests = [
        verifier.test_logger_initialization,
        verifier.test_directory_creation,
        verifier.test_single_url_processing,
        verifier.test_csv_file_validation,
        verifier.test_performance_measurement
    ]
    
    success_count = 0
    for test in tests:
        try:
            if asyncio.iscoroutinefunction(test):
                result = await test()
            else:
                result = test()
            if result:
                success_count += 1
        except Exception as e:
            print(f"❌ FAIL {test.__name__}: Unexpected error: {str(e)}")
    
    # Print summary and exit with appropriate code
    all_passed = verifier.print_summary()
    return 0 if all_passed else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Verification interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Verification failed with unexpected error: {str(e)}")
        sys.exit(1)