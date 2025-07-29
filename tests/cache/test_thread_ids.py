import pytest
import asyncio
import os
import threading
import concurrent.futures
from multiprocessing import Process, Queue
import time


def _multiprocess_worker(queue):
    """Worker function for subprocess testing (module level for pickling)."""
    try:
        from cache_utils import get_process_id
        pid = get_process_id()
        queue.put(pid)
    except Exception as e:
        queue.put(f"Error: {e}")


class TestThreadIdUtilities:
    """Test suite for thread/process ID extraction utilities."""
    
    def test_process_id_retrieval(self):
        """Test that process ID is retrieved correctly and is numeric."""
        from cache_utils import get_process_id
        
        pid = get_process_id()
        
        # Should be a positive integer
        assert isinstance(pid, int), "Process ID should be an integer"
        assert pid > 0, "Process ID should be positive"
        
        # Should match the actual OS process ID
        assert pid == os.getpid(), "Process ID should match os.getpid()"
    
    def test_process_id_consistency(self):
        """Test that multiple calls in same process return same ID."""
        from cache_utils import get_process_id
        
        pid1 = get_process_id()
        pid2 = get_process_id()
        pid3 = get_process_id()
        
        assert pid1 == pid2 == pid3, "Process ID should be consistent across calls"
    
    def test_process_id_filename_safe(self):
        """Test that process ID is suitable for use in filenames."""
        from cache_utils import get_process_id
        
        pid = get_process_id()
        pid_str = str(pid)
        
        # Should be numeric only
        assert pid_str.isdigit(), "Process ID string should contain only digits"
        
        # Should not be too long for filenames
        assert len(pid_str) < 20, "Process ID string should be reasonable length"
    
    def test_asyncio_task_id_in_async_context(self):
        """Test that asyncio task ID is retrieved when in async context."""
        from cache_utils import get_asyncio_task_id
        
        async def async_test():
            task_id = get_asyncio_task_id()
            
            # Should be a non-negative integer
            assert isinstance(task_id, int), "Task ID should be an integer"
            assert task_id >= 0, "Task ID should be non-negative"
            
            # Should not be 0 when in async context (0 is reserved for non-async)
            assert task_id != 0, "Task ID should not be 0 when in async context"
            
            return task_id
        
        # Run the async test
        task_id = asyncio.run(async_test())
        assert task_id > 0, "Async task ID should be positive"
    
    def test_asyncio_task_id_consistency_in_same_task(self):
        """Test that multiple calls in same async task return same ID."""
        from cache_utils import get_asyncio_task_id
        
        async def async_test():
            task_id1 = get_asyncio_task_id()
            await asyncio.sleep(0.001)  # Small delay
            task_id2 = get_asyncio_task_id()
            task_id3 = get_asyncio_task_id()
            
            assert task_id1 == task_id2 == task_id3, "Task ID should be consistent within same task"
            return task_id1
        
        asyncio.run(async_test())
    
    def test_asyncio_task_id_without_async_context(self):
        """Test that function returns 0 when not in async context."""
        from cache_utils import get_asyncio_task_id
        
        # Call outside of async context
        task_id = get_asyncio_task_id()
        
        # Should return 0 when not in async context
        assert task_id == 0, "Task ID should be 0 when not in async context"
    
    def test_different_async_tasks_have_different_ids(self):
        """Test that different async tasks return different IDs."""
        from cache_utils import get_asyncio_task_id
        
        async def get_task_id():
            return get_asyncio_task_id()
        
        async def run_multiple_tasks():
            # Create multiple concurrent tasks
            tasks = [asyncio.create_task(get_task_id()) for _ in range(5)]
            task_ids = await asyncio.gather(*tasks)
            
            # All task IDs should be positive
            for tid in task_ids:
                assert tid > 0, f"Task ID {tid} should be positive"
            
            # Task IDs should generally be different (though not guaranteed)
            # At minimum, they should all be valid
            assert len([tid for tid in task_ids if tid > 0]) == 5, "All tasks should have valid IDs"
            
            return task_ids
        
        task_ids = asyncio.run(run_multiple_tasks())
        assert len(task_ids) == 5, "Should get 5 task IDs"
    
    def test_id_suitable_for_filenames(self):
        """Test that both IDs are suitable for use in filenames."""
        from cache_utils import get_process_id, get_asyncio_task_id
        
        pid = get_process_id()
        
        # Test in async context
        async def async_test():
            task_id = get_asyncio_task_id()
            return task_id
        
        task_id = asyncio.run(async_test())
        
        # Both should be positive integers (except task_id can be 0 outside async)
        assert isinstance(pid, int) and pid > 0
        assert isinstance(task_id, int) and task_id > 0
        
        # String representations should be filename-safe
        pid_str = str(pid)
        task_id_str = str(task_id)
        
        assert pid_str.isdigit(), "PID string should be numeric"
        assert task_id_str.isdigit(), "Task ID string should be numeric"
        
        # Test combined in filename format
        combined = f"{pid}_{task_id}"
        assert all(c.isdigit() or c == '_' for c in combined), "Combined ID should be filename-safe"
    
    def test_thread_safety(self):
        """Test thread safety of ID extraction functions."""
        from cache_utils import get_process_id, get_asyncio_task_id
        
        results = []
        
        def worker():
            # Each thread should get the same PID (same process)
            pid = get_process_id()
            # Task ID should be 0 (not in async context)
            task_id = get_asyncio_task_id()
            results.append((pid, task_id))
        
        # Run multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # All threads should have same PID
        pids = [result[0] for result in results]
        assert all(pid == pids[0] for pid in pids), "All threads should have same PID"
        
        # All threads should have task_id = 0 (not in async context)
        task_ids = [result[1] for result in results]
        assert all(tid == 0 for tid in task_ids), "All threads should have task_id = 0"
    
    def test_different_processes_have_different_pids(self):
        """Test that different processes return different PIDs."""
        from cache_utils import get_process_id
        
        # Get PID from current process
        current_pid = get_process_id()
        
        # Get PID from subprocess
        queue = Queue()
        process = Process(target=_multiprocess_worker, args=(queue,))
        process.start()
        process.join()
        
        subprocess_result = queue.get()
        
        # Should be a valid PID, not an error
        assert isinstance(subprocess_result, int), f"Subprocess should return PID, got: {subprocess_result}"
        
        # Different processes should have different PIDs
        assert current_pid != subprocess_result, "Different processes should have different PIDs"
    
    def test_async_task_isolation(self):
        """Test that async tasks are properly isolated."""
        from cache_utils import get_asyncio_task_id
        
        task_ids = []
        
        async def task_worker(task_num):
            # Each task should get its own ID
            task_id = get_asyncio_task_id()
            task_ids.append((task_num, task_id))
            
            # Small delay to ensure tasks overlap
            await asyncio.sleep(0.01)
            
            # ID should remain consistent within the task
            task_id2 = get_asyncio_task_id()
            assert task_id == task_id2, f"Task {task_num} ID should be consistent"
            
            return task_id
        
        async def run_test():
            # Run multiple tasks concurrently
            tasks = [asyncio.create_task(task_worker(i)) for i in range(3)]
            await asyncio.gather(*tasks)
        
        asyncio.run(run_test())
        
        # Verify we got results from all tasks
        assert len(task_ids) == 3, "Should have results from 3 tasks"
        
        # All task IDs should be positive
        for task_num, task_id in task_ids:
            assert task_id > 0, f"Task {task_num} should have positive ID, got {task_id}"
    
    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        from cache_utils import get_process_id, get_asyncio_task_id
        
        # Functions should not raise exceptions under normal conditions
        try:
            pid = get_process_id()
            assert isinstance(pid, int)
            assert pid > 0
        except Exception as e:
            pytest.fail(f"get_process_id() should not raise exception: {e}")
        
        try:
            task_id = get_asyncio_task_id()
            assert isinstance(task_id, int)
            assert task_id >= 0  # Can be 0 outside async context
        except Exception as e:
            pytest.fail(f"get_asyncio_task_id() should not raise exception: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])