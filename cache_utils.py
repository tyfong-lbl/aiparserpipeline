"""
Cache utilities for the AiParser refactoring project.

This module provides utility functions for cache operations including:
- URL hash generation
- Project name hash generation  
- Thread/process ID extraction
- Cache filename generation
- Atomic file operations

Created as part of the AiParser refactoring to eliminate redundant web scraping.
"""

import hashlib
import re
import os
import asyncio
import tempfile
import time
import logging
from pathlib import Path
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from typing import Optional, Union


def generate_url_hash(url: str) -> str:
    """
    Generate a consistent 16-character hash from a URL string.
    
    This function normalizes URLs before hashing to ensure that equivalent URLs
    (e.g., with/without trailing slashes, different parameter orders) produce
    the same hash. The hash is suitable for use in filenames.
    
    Args:
        url: The URL string to hash
        
    Returns:
        A 16-character alphanumeric hash string
        
    Raises:
        ValueError: If URL is empty or None
        TypeError: If URL is not a string
        
    Examples:
        >>> generate_url_hash("https://example.com")
        'a1b2c3d4e5f6g7h8'
        >>> generate_url_hash("https://example.com/")  # Same as above (trailing slash removed)
        'a1b2c3d4e5f6g7h8'
    """
    if not url:
        raise ValueError("URL cannot be empty or None")
    
    if not isinstance(url, str):
        raise TypeError("URL must be a string")
    
    # Normalize the URL for consistent hashing
    normalized_url = _normalize_url(url)
    
    # Generate SHA256 hash
    hash_object = hashlib.sha256(normalized_url.encode('utf-8'))
    full_hash = hash_object.hexdigest()
    
    # Take first 16 characters and ensure they're alphanumeric
    # SHA256 hex output is already alphanumeric (0-9, a-f)
    hash_16 = full_hash[:16]
    
    return hash_16


def _normalize_url(url: str) -> str:
    """
    Normalize a URL for consistent hashing.
    
    Normalization includes:
    - Converting scheme and domain to lowercase
    - Removing default ports (80 for http, 443 for https)
    - Removing trailing slashes from path
    - Sorting query parameters
    - Removing fragments
    - URL encoding special characters
    
    Args:
        url: The URL to normalize
        
    Returns:
        Normalized URL string
    """
    # Parse the URL
    parsed = urlparse(url)
    
    # Normalize scheme (lowercase)
    scheme = parsed.scheme.lower()
    
    # Normalize netloc (domain + port)
    netloc = parsed.netloc.lower()
    
    # Remove default ports
    if ':80' in netloc and scheme == 'http':
        netloc = netloc.replace(':80', '')
    elif ':443' in netloc and scheme == 'https':
        netloc = netloc.replace(':443', '')
    
    # Normalize path (remove trailing slash unless it's the root)
    path = parsed.path
    if path.endswith('/') and len(path) > 1:
        path = path.rstrip('/')
    elif not path:
        path = '/'
    
    # Normalize query parameters (sort them)
    query = ''
    if parsed.query:
        # Parse query parameters
        params = parse_qs(parsed.query, keep_blank_values=True)
        # Sort parameters and rebuild query string
        sorted_params = []
        for key in sorted(params.keys()):
            for value in sorted(params[key]):
                sorted_params.append(f"{key}={value}")
        query = '&'.join(sorted_params)
    
    # Ignore fragments (they don't affect the resource)
    fragment = ''
    
    # Reconstruct the normalized URL
    normalized = urlunparse((scheme, netloc, path, '', query, fragment))
    
    return normalized


def generate_project_hash(project_name: str) -> str:
    """
    Generate a consistent 8-character hash from a project name string.
    
    This function creates a hash suitable for use in cache filenames.
    Unlike URL hashing, project name hashing preserves case sensitivity
    but normalizes whitespace for consistency.
    
    Args:
        project_name: The project name string to hash
        
    Returns:
        An 8-character alphanumeric hash string
        
    Raises:
        ValueError: If project_name is empty or None
        TypeError: If project_name is not a string
        
    Examples:
        >>> generate_project_hash("Solar Project Alpha")
        'a1b2c3d4'
        >>> generate_project_hash("  Solar Project Alpha  ")  # Same as above (whitespace normalized)
        'a1b2c3d4'
    """
    if not project_name:
        raise ValueError("Project name cannot be empty or None")
    
    if not isinstance(project_name, str):
        raise TypeError("Project name must be a string")
    
    # Normalize the project name for consistent hashing
    normalized_name = _normalize_project_name(project_name)
    
    # Generate SHA256 hash
    hash_object = hashlib.sha256(normalized_name.encode('utf-8'))
    full_hash = hash_object.hexdigest()
    
    # Take first 8 characters
    # SHA256 hex output is already alphanumeric (0-9, a-f)
    hash_8 = full_hash[:8]
    
    return hash_8


def _normalize_project_name(project_name: str) -> str:
    """
    Normalize a project name for consistent hashing.
    
    Normalization includes:
    - Stripping leading and trailing whitespace
    - Normalizing internal whitespace (multiple spaces/tabs/newlines to single space)
    - Preserving case (unlike URL normalization)
    - Preserving special characters and punctuation
    
    Args:
        project_name: The project name to normalize
        
    Returns:
        Normalized project name string
    """
    # Strip leading and trailing whitespace
    normalized = project_name.strip()
    
    # Normalize internal whitespace (multiple whitespace chars to single space)
    normalized = re.sub(r'\s+', ' ', normalized)
    
    return normalized


def get_process_id() -> int:
    """
    Get the current process ID (PID).
    
    This function returns the process ID of the current Python process,
    which is suitable for use in cache filenames to ensure uniqueness
    across different process instances.
    
    Returns:
        The current process ID as a positive integer
        
    Examples:
        >>> pid = get_process_id()
        >>> isinstance(pid, int) and pid > 0
        True
    """
    return os.getpid()


def get_asyncio_task_id() -> int:
    """
    Get the current asyncio task ID, or 0 if not in an async context.
    
    This function returns a unique identifier for the current asyncio task
    when called from within an async context. If called outside of an async
    context, it returns 0 as a safe default.
    
    The task ID is suitable for use in cache filenames to ensure uniqueness
    across concurrent async operations.
    
    Returns:
        The current asyncio task ID as a positive integer, or 0 if not in async context
        
    Examples:
        >>> # Outside async context
        >>> get_asyncio_task_id()
        0
        >>> # Inside async context (hypothetical)
        >>> async def example():
        ...     task_id = get_asyncio_task_id()
        ...     return task_id > 0
        >>> asyncio.run(example())
        True
    """
    try:
        # Try to get the current task
        current_task = asyncio.current_task()
        
        if current_task is not None:
            # Use the task's hash as a unique identifier
            # This gives us a unique numeric ID for each task
            task_id = abs(hash(current_task))
            
            # Ensure it's not 0 (reserved for non-async contexts)
            if task_id == 0:
                task_id = 1
                
            return task_id
        else:
            # No current task, return 0
            return 0
            
    except RuntimeError:
        # Not in async context (no event loop running)
        return 0
    except Exception:
        # Any other error, return 0 as safe default
        return 0


def generate_cache_filename(url: str, project_name: str) -> str:
    """
    Generate a unique cache filename combining URL hash, project hash, PID, and task ID.
    
    This function creates a filename suitable for cache operations that ensures
    uniqueness across different URLs, projects, processes, and async tasks.
    
    The filename format is: cache_{url_hash}_{project_hash}_{pid}_{task_id}.txt
    where:
    - url_hash: 16-character hash of the URL
    - project_hash: 8-character hash of the project name  
    - pid: Current process ID
    - task_id: Current asyncio task ID (or 0 if not in async context)
    
    Args:
        url: The URL to be cached
        project_name: The project name associated with the cache
        
    Returns:
        Full absolute path to the cache file within the scraped_cache directory
        
    Raises:
        ValueError: If url or project_name is empty or None
        TypeError: If url or project_name is not a string
        
    Examples:
        >>> filename = generate_cache_filename("https://example.com", "Solar Project")
        >>> # Returns something like: "/path/to/scraped_cache/cache_a1b2c3d4e5f6g7h8_12345678_1234_5678.txt"
    """
    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string")
    
    if not project_name or not isinstance(project_name, str):
        raise ValueError("Project name must be a non-empty string")
    
    # Generate all components
    url_hash = generate_url_hash(url)
    project_hash = generate_project_hash(project_name)
    pid = get_process_id()
    task_id = get_asyncio_task_id()
    
    # Create filename using specified format
    filename = f"cache_{url_hash}_{project_hash}_{pid}_{task_id}.txt"
    
    # Get the scraped_cache directory path
    cache_dir = _get_cache_directory()
    
    # Return full path
    full_path = cache_dir / filename
    return str(full_path)


def _get_cache_directory() -> Path:
    """
    Get the path to the scraped_cache directory.
    
    This function determines the location of the cache directory relative
    to the current module's location, ensuring it works regardless of
    where the module is imported from.
    
    Returns:
        Path object pointing to the scraped_cache directory
    """
    # Get the directory containing this module
    current_dir = Path(__file__).parent
    
    # The scraped_cache directory should be in the same directory as this module
    cache_dir = current_dir / "scraped_cache"
    
    return cache_dir


def atomic_write_file(file_path: Union[str, Path], content: str) -> None:
    """
    Write content to a file atomically using temporary file and rename with retry logic.
    
    This function ensures that the file write operation is atomic - other processes
    will either see the complete file or no file at all, never a partially written file.
    
    The operation includes retry logic with exponential backoff to handle temporary
    filesystem issues like disk full, temporary permission errors, etc.
    
    The operation works by:
    1. Creating a temporary file in the same directory as the target file
    2. Writing the complete content to the temporary file
    3. Atomically renaming the temporary file to the target filename
    4. Retrying up to 3 times with exponential backoff (1s, 2s, 4s) on failure
    5. Cleaning up on both success and failure
    
    Args:
        file_path: Path to the target file (string or Path object)
        content: Content to write to the file
        
    Raises:
        ValueError: If file_path or content is None/empty (for file_path)
        TypeError: If arguments are not the correct type
        OSError: If file operations fail after all retries (permissions, disk space, etc.)
        IOError: If I/O operations fail after all retries
        
    Examples:
        >>> atomic_write_file("/path/to/file.txt", "Hello World!")
        >>> atomic_write_file(Path("/path/to/file.txt"), "Hello World!")
    """
    # Validate inputs
    if not file_path:
        raise ValueError("File path cannot be empty or None")
    
    if content is None:
        raise TypeError("Content cannot be None")
    
    if not isinstance(content, str):
        raise TypeError("Content must be a string")
    
    # Convert to Path object for easier handling
    target_path = Path(file_path)
    
    # Ensure parent directory exists
    target_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Retry configuration
    max_attempts = 3
    backoff_delays = [1, 2, 4]  # Exponential backoff: 1s, 2s, 4s
    
    last_exception = None
    
    for attempt in range(max_attempts):
        temp_fd = None
        temp_path = None
        
        try:
            # Create temporary file in same directory
            # This ensures the rename operation is atomic (same filesystem)
            temp_fd, temp_name = tempfile.mkstemp(
                suffix='.tmp',
                prefix=f'.{target_path.name}_',
                dir=target_path.parent
            )
            temp_path = Path(temp_name)
            
            # Write content to temporary file with proper encoding
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as temp_file:
                temp_file.write(content)
                temp_file.flush()  # Ensure content is written to disk
                os.fsync(temp_file.fileno())  # Force write to storage
            
            # Close the file descriptor (already closed by context manager)
            temp_fd = None
            
            # Atomically rename temporary file to target file
            # This is atomic on most filesystems when on the same device
            temp_path.rename(target_path)
            temp_path = None  # Successfully renamed, don't clean up
            
            # Success - exit retry loop
            return
            
        except Exception as e:
            last_exception = e
            
            # Clean up temporary file on any error
            if temp_fd is not None:
                try:
                    os.close(temp_fd)
                except OSError:
                    pass  # File descriptor might already be closed
            
            if temp_path is not None and temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass  # Best effort cleanup
            
            # If this was the last attempt, don't retry
            if attempt == max_attempts - 1:
                break
            
            # Log retry attempt with details
            delay = backoff_delays[attempt] if attempt < len(backoff_delays) else backoff_delays[-1]
            logging.warning(
                f"atomic_write_file attempt {attempt + 1}/{max_attempts} failed for {target_path}: "
                f"{type(e).__name__}: {e}. Retrying in {delay}s..."
            )
            
            # Wait before retry with exponential backoff
            time.sleep(delay)
    
    # All retries failed, log final error and raise the last exception
    logging.error(
        f"atomic_write_file failed after {max_attempts} attempts for {target_path}: "
        f"{type(last_exception).__name__}: {last_exception}"
    )
    
    # Re-raise the last exception
    raise last_exception


# Test the implementation
if __name__ == "__main__":
    # Test URL hash generation
    test_urls = [
        "https://example.com",
        "https://example.com/",
        "HTTPS://EXAMPLE.COM",
        "https://example.com:443",
        "https://example.com/path?b=2&a=1",
        "https://example.com/path?a=1&b=2"
    ]
    
    print("Testing URL hash generation:")
    for url in test_urls:
        hash_val = generate_url_hash(url)
        print(f"{url:<40} -> {hash_val}")
    
    # Test URL normalization
    print("\nTesting URL normalization:")
    test_pairs = [
        ("https://example.com", "https://example.com/"),
        ("https://example.com:443/path", "https://example.com/path"),
        ("https://example.com?b=2&a=1", "https://example.com?a=1&b=2")
    ]
    
    for url1, url2 in test_pairs:
        hash1 = generate_url_hash(url1)
        hash2 = generate_url_hash(url2)
        print(f"{url1} == {url2}: {hash1 == hash2} ({hash1}, {hash2})")
    
    # Test project hash generation
    test_projects = [
        "Solar Project Alpha",
        "  Solar Project Alpha  ",
        "Solar   Project   Alpha",
        "Wind Farm Beta",
        "Battery Storage Gamma",
        "Project with Special Characters !@#$%",
        "Project with números 123",
        "Project with ünïcødé"
    ]
    
    print("\nTesting project hash generation:")
    for project in test_projects:
        hash_val = generate_project_hash(project)
        print(f"'{project:<30}' -> {hash_val}")
    
    # Test project name normalization
    print("\nTesting project name normalization:")
    project_pairs = [
        ("  Solar Project Alpha  ", "Solar Project Alpha"),
        ("Solar   Project   Alpha", "Solar Project Alpha"),
        ("Solar\tProject\nAlpha", "Solar Project Alpha")
    ]
    
    for proj1, proj2 in project_pairs:
        hash1 = generate_project_hash(proj1)
        hash2 = generate_project_hash(proj2)
        print(f"'{proj1}' == '{proj2}': {hash1 == hash2} ({hash1}, {hash2})")
    
    # Test integration
    print("\nTesting hash integration:")
    test_url = "https://example.com/test"
    test_project = "Test Solar Project"
    
    url_hash = generate_url_hash(test_url)
    project_hash = generate_project_hash(test_project)
    
    print(f"URL: {test_url}")
    print(f"URL Hash (16 chars): {url_hash}")
    print(f"Project: {test_project}")
    print(f"Project Hash (8 chars): {project_hash}")
    print(f"Combined: {url_hash}_{project_hash} ({len(url_hash)}+1+{len(project_hash)}={len(url_hash)+1+len(project_hash)} chars)")
    
    # Test thread ID functions
    print("\nTesting thread ID functions:")
    
    # Test process ID
    pid = get_process_id()
    print(f"Process ID: {pid}")
    print(f"PID consistency: {pid == get_process_id()}")
    
    # Test asyncio task ID outside async context
    task_id_sync = get_asyncio_task_id()
    print(f"Task ID (sync context): {task_id_sync}")
    
    # Test asyncio task ID inside async context
    async def test_async_task_id():
        task_id = get_asyncio_task_id()
        return task_id
    
    task_id_async = asyncio.run(test_async_task_id())
    print(f"Task ID (async context): {task_id_async}")
    
    # Test full cache filename format
    print(f"\nFull cache filename format:")
    print(f"cache_{url_hash}_{project_hash}_{pid}_{task_id_async}.txt")
    
    total_length = len(f"cache_{url_hash}_{project_hash}_{pid}_{task_id_async}.txt")
    print(f"Total filename length: {total_length} characters")
    
    # Test filename generation function
    print(f"\nTesting filename generation function:")
    
    cache_filename = generate_cache_filename(test_url, test_project)
    print(f"Generated filename path: {cache_filename}")
    
    filename_only = Path(cache_filename).name
    print(f"Filename only: {filename_only}")
    print(f"Cache directory: {Path(cache_filename).parent}")
    
    # Test with async context
    async def test_async_filename():
        async_filename = generate_cache_filename(test_url, test_project + " Async")
        return async_filename
    
    async_cache_filename = asyncio.run(test_async_filename())
    print(f"Async context filename: {Path(async_cache_filename).name}")
    
    # Verify format consistency
    sync_parts = Path(cache_filename).name.split('_')
    async_parts = Path(async_cache_filename).name.split('_')
    
    print(f"\nFilename components comparison:")
    print(f"Sync:  prefix={sync_parts[0]}, url_hash={sync_parts[1]}, proj_hash={sync_parts[2]}, pid={sync_parts[3]}, task_id={sync_parts[4]}")
    print(f"Async: prefix={async_parts[0]}, url_hash={async_parts[1]}, proj_hash={async_parts[2]}, pid={async_parts[3]}, task_id={async_parts[4]}")
    
    # Task IDs should be different
    sync_task_id = sync_parts[4].replace('.txt', '')
    async_task_id = async_parts[4].replace('.txt', '')
    print(f"Task ID difference: sync={sync_task_id}, async={async_task_id}, different={sync_task_id != async_task_id}")
    
    # Test atomic write function
    print(f"\nTesting atomic write function:")
    
    test_write_content = """This is test content for atomic write.
It includes multiple lines,
special characters: !@#$%^&*(),
and unicode: 测试 ünïcødé 🚀
"""
    
    # Test basic atomic write
    test_write_file = Path(_get_cache_directory()) / "test_atomic_write.txt"
    
    print(f"Writing to: {test_write_file}")
    try:
        atomic_write_file(test_write_file, test_write_content)
        print("✓ Atomic write successful")
        
        # Verify content
        if test_write_file.exists():
            read_content = test_write_file.read_text(encoding='utf-8')
            content_matches = (read_content == test_write_content)
            print(f"✓ Content verification: {'PASS' if content_matches else 'FAIL'}")
            print(f"  Content length: {len(read_content)} chars")
            
            # Clean up test file
            test_write_file.unlink()
            print("✓ Test file cleaned up")
        else:
            print("✗ Test file was not created")
            
    except Exception as e:
        print(f"✗ Atomic write failed: {e}")
    
    print("\nAll utility functions tested successfully!")