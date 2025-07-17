import pytest
import time
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from tests.cache.test_fixtures import CacheTestFixtures


class TestAtomicWriteRetry(CacheTestFixtures):
    """Test suite for atomic write retry logic functionality."""
    
    def test_successful_write_on_first_attempt_works_as_before(self, temp_cache_dir):
        """Test that successful write on first attempt works as before."""
        from cache_utils import atomic_write_file
        
        test_content = "Test content for first attempt success."
        test_file = temp_cache_dir / "first_attempt_test.txt"
        
        start_time = time.time()
        atomic_write_file(str(test_file), test_content)
        end_time = time.time()
        
        # Should complete quickly (no retries)
        assert (end_time - start_time) < 0.5, "Should complete quickly without retries"
        
        # Verify file exists and content is correct
        assert test_file.exists()
        written_content = test_file.read_text(encoding='utf-8')
        assert written_content == test_content
    
    def test_retry_logic_activates_on_write_failures(self, temp_cache_dir, caplog):
        """Test that retry logic activates on write failures."""
        from cache_utils import atomic_write_file
        
        test_file = temp_cache_dir / "retry_test.txt"
        test_content = "Content for retry test"
        
        # Mock tempfile.mkstemp to fail first 2 times, succeed on 3rd
        call_count = 0
        def mock_mkstemp(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise OSError(f"Simulated failure #{call_count}")
            # Success on 3rd attempt
            return 999, str(test_file.with_suffix('.tmp'))
        
        with patch('cache_utils.tempfile.mkstemp', side_effect=mock_mkstemp), \
             patch('cache_utils.os.fdopen', mock_open()), \
             patch('cache_utils.Path.rename'), \
             caplog.at_level(logging.WARNING):
            
            atomic_write_file(str(test_file), test_content)
            
            # Should have made 3 attempts
            assert call_count == 3, f"Should have made 3 attempts, made {call_count}"
            
            # Should have logged retry attempts
            retry_logs = [record for record in caplog.records if 'retry' in record.message.lower()]
            assert len(retry_logs) >= 2, "Should have logged retry attempts"
    
    def test_exponential_backoff_timing_is_correct(self, temp_cache_dir):
        """Test that exponential backoff timing is correct."""
        from cache_utils import atomic_write_file
        
        test_file = temp_cache_dir / "backoff_test.txt"
        test_content = "Content for backoff test"
        
        retry_times = []
        
        # Mock tempfile.mkstemp to fail first 2 times, succeed on 3rd
        call_count = 0
        def mock_mkstemp(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            retry_times.append(time.time())
            if call_count <= 2:
                raise OSError(f"Simulated failure for backoff test #{call_count}")
            # Success on 3rd attempt
            return 999, str(test_file.with_suffix('.tmp'))
        
        with patch('cache_utils.tempfile.mkstemp', side_effect=mock_mkstemp), \
             patch('cache_utils.os.fdopen', mock_open()), \
             patch('cache_utils.Path.rename'):
            
            start_time = time.time()
            atomic_write_file(str(test_file), test_content)
            
            # Verify timing between attempts
            if len(retry_times) >= 3:
                # First retry should be ~1 second after first attempt
                first_retry_delay = retry_times[1] - retry_times[0]
                assert 0.8 <= first_retry_delay <= 1.5, f"First retry delay should be ~1s, got {first_retry_delay:.2f}s"
                
                # Second retry should be ~2 seconds after second attempt  
                second_retry_delay = retry_times[2] - retry_times[1]
                assert 1.8 <= second_retry_delay <= 2.5, f"Second retry delay should be ~2s, got {second_retry_delay:.2f}s"
    
    def test_final_exception_raised_after_max_retries(self, temp_cache_dir, caplog):
        """Test that final exception is raised after max retries."""
        from cache_utils import atomic_write_file
        
        test_file = temp_cache_dir / "max_retries_test.txt"
        test_content = "Content for max retries test"
        
        # Mock tempfile.mkstemp to always fail
        def mock_mkstemp(*args, **kwargs):
            raise OSError("Persistent failure for max retries test")
        
        with patch('cache_utils.tempfile.mkstemp', side_effect=mock_mkstemp), \
             caplog.at_level(logging.ERROR):
            
            # Should raise exception after max retries
            with pytest.raises(OSError, match="Persistent failure"):
                atomic_write_file(str(test_file), test_content)
            
            # Should have logged all retry attempts
            error_logs = [record for record in caplog.records if record.levelname == 'ERROR']
            assert len(error_logs) >= 1, "Should have logged final error"
    
    def test_retry_attempts_are_logged_properly(self, temp_cache_dir, caplog):
        """Test that retry attempts are logged properly."""
        from cache_utils import atomic_write_file
        
        test_file = temp_cache_dir / "logging_test.txt"
        test_content = "Content for logging test"
        
        # Mock tempfile.mkstemp to fail first time, succeed on 2nd
        call_count = 0
        def mock_mkstemp(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise OSError("Simulated failure for logging test")
            # Success on 2nd attempt
            return 999, str(test_file.with_suffix('.tmp'))
        
        with patch('cache_utils.tempfile.mkstemp', side_effect=mock_mkstemp), \
             patch('cache_utils.os.fdopen', mock_open()), \
             patch('cache_utils.Path.rename'), \
             caplog.at_level(logging.WARNING):
            
            atomic_write_file(str(test_file), test_content)
            
            # Check for appropriate log messages
            log_messages = [record.message for record in caplog.records]
            
            # Should have logged the retry attempt
            retry_messages = [msg for msg in log_messages if 'retry' in msg.lower() or 'attempt' in msg.lower()]
            assert len(retry_messages) >= 1, f"Should have logged retry attempts, got: {log_messages}"
            
            # Should include relevant details in log messages
            for msg in retry_messages:
                assert str(test_file) in msg or 'atomic_write_file' in msg, f"Log should include context: {msg}"
    
    def test_different_types_of_write_failures_are_handled(self, temp_cache_dir, caplog):
        """Test that different types of write failures are handled."""
        from cache_utils import atomic_write_file
        
        test_file = temp_cache_dir / "error_types_test.txt"
        test_content = "Content for error types test"
        
        # Test different error types
        error_types = [
            OSError("Disk full"),
            PermissionError("Permission denied"),
            IOError("I/O error occurred"),
        ]
        
        for i, error in enumerate(error_types):
            call_count = 0
            def mock_mkstemp(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise error
                # Success on 2nd attempt
                return 999, str(test_file.with_suffix(f'.tmp{i}'))
            
            with patch('cache_utils.tempfile.mkstemp', side_effect=mock_mkstemp), \
                 patch('cache_utils.os.fdopen', mock_open()), \
                 patch('cache_utils.Path.rename'), \
                 caplog.at_level(logging.WARNING):
                
                # Should succeed after retry
                atomic_write_file(str(test_file), test_content)
                
                # Should have logged the specific error type
                recent_logs = caplog.records[-5:]  # Check recent logs
                error_logged = any(str(error) in record.message for record in recent_logs)
                assert error_logged, f"Should have logged {type(error).__name__}: {error}"
    
    def test_maintains_same_function_interface(self, temp_cache_dir):
        """Test that function maintains same interface as before."""
        from cache_utils import atomic_write_file
        import inspect
        
        # Check function signature hasn't changed
        sig = inspect.signature(atomic_write_file)
        params = list(sig.parameters.keys())
        
        assert params == ['file_path', 'content'], f"Function signature changed: {params}"
        assert sig.return_annotation is None or sig.return_annotation == type(None), "Return annotation should be None"
        
        # Test that function still works with both string and Path objects
        test_content = "Interface compatibility test"
        
        # Test with string path
        string_path = str(temp_cache_dir / "interface_string.txt")
        atomic_write_file(string_path, test_content)
        assert Path(string_path).read_text(encoding='utf-8') == test_content
        
        # Test with Path object
        path_object = temp_cache_dir / "interface_path.txt"
        atomic_write_file(path_object, test_content)
        assert path_object.read_text(encoding='utf-8') == test_content
    
    def test_retry_logic_with_partial_failures(self, temp_cache_dir, caplog):
        """Test retry logic with partial failures (some operations succeed, others fail)."""
        from cache_utils import atomic_write_file
        
        test_file = temp_cache_dir / "partial_failure_test.txt"
        test_content = "Content for partial failure test"
        
        # Mock scenario: temp file creation succeeds, but writing fails first time
        call_count = 0
        def mock_fdopen(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise IOError("Write operation failed")
            # Return a mock file object that works
            mock_file = MagicMock()
            mock_file.__enter__ = MagicMock(return_value=mock_file)
            mock_file.__exit__ = MagicMock(return_value=None)
            return mock_file
        
        with patch('cache_utils.tempfile.mkstemp', return_value=(999, str(test_file.with_suffix('.tmp')))), \
             patch('cache_utils.os.fdopen', side_effect=mock_fdopen), \
             patch('cache_utils.Path.rename'), \
             caplog.at_level(logging.WARNING):
            
            atomic_write_file(str(test_file), test_content)
            
            # Should have made 2 attempts (1 failure + 1 success)
            assert call_count == 2, f"Should have made 2 attempts, made {call_count}"
    
    def test_cleanup_occurs_during_retry_failures(self, temp_cache_dir):
        """Test that cleanup occurs properly during retry failures."""
        from cache_utils import atomic_write_file
        
        test_file = temp_cache_dir / "cleanup_test.txt"
        test_content = "Content for cleanup test"
        
        temp_files_created = []
        
        # Mock tempfile.mkstemp to track created temp files
        call_count = 0
        def mock_mkstemp(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            temp_path = test_file.with_suffix(f'.tmp{call_count}')
            temp_files_created.append(temp_path)
            
            if call_count <= 2:
                # Create actual temp file then fail
                temp_path.touch()
                raise OSError(f"Simulated failure #{call_count}")
            
            # Success on 3rd attempt  
            return 999, str(temp_path)
        
        with patch('cache_utils.tempfile.mkstemp', side_effect=mock_mkstemp), \
             patch('cache_utils.os.fdopen', mock_open()), \
             patch('cache_utils.Path.rename'):
            
            atomic_write_file(str(test_file), test_content)
            
            # First two temp files should have been cleaned up
            for i, temp_file in enumerate(temp_files_created[:2]):
                assert not temp_file.exists(), f"Temp file {i+1} should have been cleaned up: {temp_file}"
    
    def test_backward_compatibility_with_existing_code(self, temp_cache_dir):
        """Test that existing code using atomic_write_file continues to work."""
        from cache_utils import atomic_write_file
        
        # Test scenarios that existing code might use
        test_cases = [
            ("simple_content.txt", "Simple content"),
            ("empty_content.txt", ""),
            ("unicode_content.txt", "Unicode: 你好世界 🌍"),
            ("large_content.txt", "A" * 10000),
        ]
        
        for filename, content in test_cases:
            test_file = temp_cache_dir / filename
            
            # Should work exactly as before
            atomic_write_file(str(test_file), content)
            
            assert test_file.exists()
            written_content = test_file.read_text(encoding='utf-8')
            assert written_content == content, f"Content mismatch for {filename}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])