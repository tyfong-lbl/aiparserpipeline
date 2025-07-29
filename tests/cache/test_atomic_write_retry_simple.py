import pytest
import time
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock, call
from tests.cache.test_fixtures import CacheTestFixtures


class TestAtomicWriteRetrySimple(CacheTestFixtures):
    """Simplified test suite for atomic write retry logic functionality."""
    
    def test_successful_write_on_first_attempt_works_as_before(self, temp_cache_dir):
        """Test that successful write on first attempt works as before (no retry delays)."""
        from cache_utils import atomic_write_file
        
        test_content = "Test content for first attempt success."
        test_file = temp_cache_dir / "first_attempt_test.txt"
        
        start_time = time.time()
        atomic_write_file(str(test_file), test_content)
        end_time = time.time()
        
        # Should complete quickly (no retries)
        assert (end_time - start_time) < 1.0, "Should complete quickly without retries"
        
        # Verify file exists and content is correct
        assert test_file.exists()
        written_content = test_file.read_text(encoding='utf-8')
        assert written_content == test_content
    
    def test_retry_logic_activates_on_write_failures(self, temp_cache_dir, caplog):
        """Test that retry logic activates on write failures.""" 
        from cache_utils import atomic_write_file
        
        test_file = temp_cache_dir / "retry_test.txt"
        test_content = "Content for retry test"
        
        # Mock tempfile.mkstemp to fail first time, succeed second time
        attempts = []
        def mock_mkstemp(*args, **kwargs):
            attempts.append(len(attempts) + 1)
            if len(attempts) == 1:
                raise OSError("Simulated failure for retry test")
            # Success on 2nd attempt - return actual temp file
            import tempfile
            return tempfile.mkstemp(suffix='.tmp', dir=test_file.parent)
        
        with patch('cache_utils.tempfile.mkstemp', side_effect=mock_mkstemp), \
             patch('cache_utils.time.sleep') as mock_sleep, \
             caplog.at_level(logging.WARNING):
            
            atomic_write_file(str(test_file), test_content)
            
            # Should have made 2 attempts
            assert len(attempts) == 2, f"Should have made 2 attempts, made {len(attempts)}"
            
            # Should have called sleep once (for the retry delay)
            assert mock_sleep.call_count == 1, "Should have slept once for retry delay"
            assert mock_sleep.call_args[0][0] == 1, "First retry should have 1s delay"
            
            # Should have logged retry attempt
            retry_logs = [record for record in caplog.records if 'retry' in record.message.lower()]
            assert len(retry_logs) >= 1, "Should have logged retry attempt"
    
    def test_exponential_backoff_timing_is_correct(self, temp_cache_dir):
        """Test that exponential backoff timing is correct."""
        from cache_utils import atomic_write_file
        
        test_file = temp_cache_dir / "backoff_test.txt"
        test_content = "Content for backoff test"
        
        # Mock tempfile.mkstemp to fail 2 times, succeed on 3rd
        attempts = []
        def mock_mkstemp(*args, **kwargs):
            attempts.append(len(attempts) + 1)
            if len(attempts) <= 2:
                raise OSError(f"Simulated failure #{len(attempts)}")
            # Success on 3rd attempt
            import tempfile
            return tempfile.mkstemp(suffix='.tmp', dir=test_file.parent)
        
        with patch('cache_utils.tempfile.mkstemp', side_effect=mock_mkstemp), \
             patch('cache_utils.time.sleep') as mock_sleep:
            
            atomic_write_file(str(test_file), test_content)
            
            # Should have called sleep twice (for 2 retries)
            assert mock_sleep.call_count == 2, f"Should have slept twice, called {mock_sleep.call_count} times"
            
            # Check sleep call arguments for exponential backoff
            sleep_calls = [call_args[0][0] for call_args in mock_sleep.call_args_list]
            assert sleep_calls[0] == 1, f"First retry should be 1s, got {sleep_calls[0]}"
            assert sleep_calls[1] == 2, f"Second retry should be 2s, got {sleep_calls[1]}"
    
    def test_final_exception_raised_after_max_retries(self, temp_cache_dir, caplog):
        """Test that final exception is raised after max retries."""
        from cache_utils import atomic_write_file
        
        test_file = temp_cache_dir / "max_retries_test.txt"
        test_content = "Content for max retries test"
        
        # Mock tempfile.mkstemp to always fail
        def mock_mkstemp(*args, **kwargs):
            raise OSError("Persistent failure for max retries test")
        
        with patch('cache_utils.tempfile.mkstemp', side_effect=mock_mkstemp), \
             patch('cache_utils.time.sleep') as mock_sleep, \
             caplog.at_level(logging.ERROR):
            
            # Should raise exception after max retries
            with pytest.raises(OSError, match="Persistent failure"):
                atomic_write_file(str(test_file), test_content)
            
            # Should have slept 2 times (for 2 retries before final failure)
            assert mock_sleep.call_count == 2, f"Should have slept twice, called {mock_sleep.call_count} times"
            
            # Should have logged final error
            error_logs = [record for record in caplog.records if record.levelname == 'ERROR']
            assert len(error_logs) >= 1, "Should have logged final error"
    
    def test_retry_attempts_are_logged_properly(self, temp_cache_dir, caplog):
        """Test that retry attempts are logged properly."""
        from cache_utils import atomic_write_file
        
        test_file = temp_cache_dir / "logging_test.txt"
        test_content = "Content for logging test"
        
        # Mock tempfile.mkstemp to fail first time, succeed on 2nd
        attempts = []
        def mock_mkstemp(*args, **kwargs):
            attempts.append(len(attempts) + 1)
            if len(attempts) == 1:
                raise OSError("Simulated failure for logging test")
            import tempfile
            return tempfile.mkstemp(suffix='.tmp', dir=test_file.parent)
        
        with patch('cache_utils.tempfile.mkstemp', side_effect=mock_mkstemp), \
             patch('cache_utils.time.sleep'), \
             caplog.at_level(logging.WARNING):
            
            atomic_write_file(str(test_file), test_content)
            
            # Check for appropriate log messages
            log_messages = [record.message for record in caplog.records]
            
            # Should have logged the retry attempt
            retry_messages = [msg for msg in log_messages if 'retry' in msg.lower() or 'attempt' in msg.lower()]
            assert len(retry_messages) >= 1, f"Should have logged retry attempts, got: {log_messages}"
            
            # Should include relevant details in log messages
            for msg in retry_messages:
                assert str(test_file) in msg, f"Log should include file path: {msg}"
                assert 'OSError' in msg or 'Simulated failure' in msg, f"Log should include error details: {msg}"
    
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
            attempts = []
            def mock_mkstemp(*args, **kwargs):
                attempts.append(len(attempts) + 1)
                if len(attempts) == 1:
                    raise error
                import tempfile
                return tempfile.mkstemp(suffix='.tmp', dir=test_file.parent)
            
            with patch('cache_utils.tempfile.mkstemp', side_effect=mock_mkstemp), \
                 patch('cache_utils.time.sleep'), \
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
    
    def test_max_attempts_configuration(self, temp_cache_dir):
        """Test that max attempts is correctly configured to 3."""
        from cache_utils import atomic_write_file
        
        test_file = temp_cache_dir / "max_attempts_test.txt"
        test_content = "Content for max attempts test"
        
        # Mock tempfile.mkstemp to always fail
        attempts = []
        def mock_mkstemp(*args, **kwargs):
            attempts.append(len(attempts) + 1)
            raise OSError(f"Failure #{len(attempts)}")
        
        with patch('cache_utils.tempfile.mkstemp', side_effect=mock_mkstemp), \
             patch('cache_utils.time.sleep') as mock_sleep:
            
            with pytest.raises(OSError):
                atomic_write_file(str(test_file), test_content)
            
            # Should have attempted exactly 3 times
            assert len(attempts) == 3, f"Should have made 3 attempts, made {len(attempts)}"
            
            # Should have slept 2 times (between the 3 attempts)
            assert mock_sleep.call_count == 2, f"Should have slept twice, called {mock_sleep.call_count} times"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])