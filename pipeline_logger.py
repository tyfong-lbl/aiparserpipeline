import csv
import threading
from datetime import datetime
from pathlib import Path
import logging

class PipelineLogger:
    """
    A thread-safe CSV logger for tracking URL processing through the AI parser pipeline.
    Logs text extraction and LLM processing metrics with timestamps.
    """
    
    def __init__(self, log_directory: Path):
        """
        Initialize the PipelineLogger with a log directory.
        
        Args:
            log_directory (Path): Directory where CSV log files will be stored
        """
        self.log_directory = Path(log_directory)
        self.log_directory.mkdir(parents=True, exist_ok=True)
        
        # Create timestamped filename
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        self.log_filename = f"pipeline_log_{timestamp}.csv"
        self.log_filepath = self.log_directory / self.log_filename
        
        # Thread safety
        self._lock = threading.Lock()
        self._headers_written = False
        
        # CSV headers matching the schema
        self.headers = [
            'URL',
            'project_name', 
            'timestamp',
            'text_extraction_status',
            'text_extraction_error',
            'text_length',
            'llm_response_status',
            'llm_response_error',
            'response_time_ms'
        ]
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
    def log_url_processing(self, 
                          url: str,
                          project_name: str,
                          timestamp: str,
                          text_extraction_status: str,
                          text_extraction_error: str,
                          text_length: int,
                          llm_response_status: str,
                          llm_response_error: str,
                          response_time_ms: int):
        """
        Log a URL processing event to the CSV file.
        
        Args:
            url (str): The URL being processed
            project_name (str): Project identifier
            timestamp (str): ISO 8601 timestamp with timezone
            text_extraction_status (str): "True" or "False"
            text_extraction_error (str): Error message or "None"
            text_length (int): Number of characters extracted
            llm_response_status (str): "True" or "False"
            llm_response_error (str): Error message or "None"
            response_time_ms (int): Total processing time in milliseconds
        """
        with self._lock:
            try:
                # Write headers if this is the first write
                if not self._headers_written:
                    self._write_headers()
                    self._headers_written = True
                
                # Write the data row
                with open(self.log_filepath, 'a', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow([
                        url,
                        project_name,
                        timestamp,
                        text_extraction_status,
                        text_extraction_error,
                        text_length,
                        llm_response_status,
                        llm_response_error,
                        response_time_ms
                    ])
                    
            except Exception as e:
                self.logger.error(f"Error writing to pipeline log: {e}")
                
    def _write_headers(self):
        """Write CSV headers to the file."""
        try:
            with open(self.log_filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(self.headers)
        except Exception as e:
            self.logger.error(f"Error writing headers to pipeline log: {e}")
            raise
    
    def get_log_filepath(self) -> Path:
        """Return the path to the current log file."""
        return self.log_filepath


# Simple test demonstration
if __name__ == "__main__":
    import tempfile
    import os
    
    print("Testing PipelineLogger...")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create logger instance
        logger = PipelineLogger(temp_path)
        print(f"Created logger with file: {logger.get_log_filepath()}")
        
        # Log a successful URL processing event
        test_timestamp = datetime.now().astimezone().isoformat()
        logger.log_url_processing(
            url="https://example.com/test-article",
            project_name="TestProject_Demo",
            timestamp=test_timestamp,
            text_extraction_status="True",
            text_extraction_error="None",
            text_length=1542,
            llm_response_status="True", 
            llm_response_error="None",
            response_time_ms=2340
        )
        
        # Verify the CSV file was created with correct content
        if logger.get_log_filepath().exists():
            print("✅ CSV file created successfully")
            
            with open(logger.get_log_filepath(), 'r', encoding='utf-8') as f:
                content = f.read()
                print("CSV Content:")
                print(content)
                
            # Basic validation
            lines = content.strip().split('\n')
            if len(lines) == 2:  # Header + 1 data row
                print("✅ Correct number of lines")
                
                header_line = lines[0]
                data_line = lines[1]
                
                if "URL,project_name,timestamp" in header_line:
                    print("✅ Headers are correct")
                    
                if "https://example.com/test-article,TestProject_Demo" in data_line:
                    print("✅ Data row contains expected values")
                    
                print("🎉 PipelineLogger test completed successfully!")
            else:
                print("❌ Incorrect number of lines in CSV")
        else:
            print("❌ CSV file was not created")