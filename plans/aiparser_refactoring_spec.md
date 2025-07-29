# AiParser Refactoring Specification

## Project Overview

### Objective
Refactor the `AiParser` class in `page_tracker.py` to eliminate redundant web scraping operations by scraping each webpage only once and reusing the scraped content for multiple LLM API calls with different prompts.

### Current Problem
The existing implementation scrapes the same webpage multiple times (once per prompt) when processing different prompts for the same URL, causing significant performance bottlenecks when processing tens of thousands of pages.

### Expected Benefits
- 60-80% reduction in processing time for multi-prompt scenarios
- Elimination of redundant network I/O operations
- Memory-safe processing for large-scale operations
- Improved scalability for concurrent processing

## Requirements

### Functional Requirements
1. **Single Scrape Per URL**: Each webpage must be scraped exactly once per thread/process
2. **Content Reuse**: Scraped content must be reused across multiple prompts for the same URL
3. **Disk-Based Caching**: Large content (>250MB) must be stored on disk to prevent memory overrun
4. **Automatic Cleanup**: Cache files must be automatically deleted after all prompts for a URL are processed
5. **Concurrency Support**: Multiple threads/processes must be able to process different URLs simultaneously
6. **Thread Safety**: Same URL processing by different threads must not cause conflicts

### Non-Functional Requirements
1. **Performance**: Significant reduction in total processing time
2. **Memory Efficiency**: No memory overrun for large pages
3. **Disk Management**: Automatic cleanup when cache exceeds 10TB
4. **Reliability**: Atomic operations to prevent file corruption
5. **Maintainability**: Clear separation of concerns between scraping and API processing

## Architecture Design

### Core Components

#### 1. Enhanced AiParser Class
- **New Method**: `scrape_and_cache()` - handles web scraping and caching
- **Modified Method**: `get_api_response()` - processes prompts using cached content
- **Instance Variables**: Cache file path and in-memory content storage

#### 2. Cache Management System
- **Directory Structure**: `scraped_cache/` (excluded from git via .gitignore)
- **File Naming**: `cache_{url_hash}_{project_hash}_{pid}_{task_id}.txt`
- **Atomic Operations**: Temporary file creation followed by atomic rename
- **Cleanup Strategy**: Per-thread cleanup after prompt completion

#### 3. Integration Points
- **ModelValidator Class**: Modified to coordinate scraping and prompt processing
- **Pipeline Logger**: Enhanced to track cache operations and disk usage

### Data Flow Architecture

```
1. ModelValidator.get_responses_for_url(url)
   ↓
2. AiParser.scrape_and_cache()
   → Scrape webpage content
   → Write to temporary file
   → Atomically rename to cache file
   → Return cache file path
   ↓
3. Loop through prompts:
   AiParser.get_api_response()
   → Read cache file into memory (first call only)
   → Process prompt with cached content
   → Return API response
   ↓
4. Cleanup cache file after all prompts complete
```

## Detailed Implementation Specification

### 1. New Method: `scrape_and_cache()`

#### Method Signature
```python
async def scrape_and_cache(self, url: str) -> str:
    """
    Scrape webpage content and cache to disk.
    
    Args:
        url: The URL to scrape
        
    Returns:
        str: Path to the cached file containing scraped content
        
    Raises:
        Exception: If scraping fails or disk operations fail after retries
    """
```

#### Implementation Details
1. **Content Scraping**:
   - Use existing Playwright browser instance
   - Extract title and body text as currently implemented
   - Combine into fulltext format: `f"{title}.\n\n{text}"`

2. **Cache File Creation**:
   - Generate filename using format: `cache_{url_hash}_{project_hash}_{pid}_{task_id}.txt`
   - Create temporary file with `.tmp` extension
   - Write content to temporary file
   - Atomically rename temporary file to final filename

3. **Hash Generation**:
   ```python
   import hashlib
   import os
   import asyncio
   
   # URL hash (first 16 chars of SHA256)
   url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
   
   # Project hash (first 8 chars of SHA256)
   project_hash = hashlib.sha256(self.project_name.encode()).hexdigest()[:8]
   
   # Process and task IDs
   pid = os.getpid()
   task_id = id(asyncio.current_task()) if asyncio.current_task() else 0
   
   filename = f"cache_{url_hash}_{project_hash}_{pid}_{task_id}.txt"
   ```

4. **Error Handling**:
   - Retry disk operations up to 3 times with exponential backoff
   - Log failures to diagnostic log
   - Raise exception if all retries fail

### 2. Modified Method: `get_api_response()`

#### Method Signature Changes
```python
def get_api_response(self) -> Tuple[str, Dict]:
    """
    Process cached content with current prompt.
    
    Returns:
        Tuple[str, Dict]: API response content and metrics
    """
```

#### Implementation Details
1. **Content Loading**:
   - Check if content already loaded in memory (`self._cached_content`)
   - If not loaded, read from cache file path (`self._cache_file_path`)
   - Store content in instance variable for subsequent calls

2. **Instance Variables**:
   ```python
   self._cache_file_path: Optional[str] = None  # Set by scrape_and_cache()
   self._cached_content: Optional[str] = None   # Lazy-loaded content
   ```

3. **File Reading**:
   ```python
   if self._cached_content is None:
       with open(self._cache_file_path, 'r', encoding='utf-8') as f:
           self._cached_content = f.read()
   ```

### 3. Cache Management Implementation

#### Directory Structure
```
scraped_cache/
├── cache_a1b2c3d4_e5f6g7h8_12345_67890.txt
├── cache_x9y8z7w6_v5u4t3s2_12346_67891.txt
└── ...
```

#### Atomic File Operations
```python
import tempfile
import os

def atomic_write(filepath: str, content: str, max_retries: int = 3):
    """Write content to file atomically with retries."""
    for attempt in range(max_retries):
        try:
            # Create temporary file in same directory
            temp_fd, temp_path = tempfile.mkstemp(
                dir=os.path.dirname(filepath),
                suffix='.tmp'
            )
            
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())  # Force write to disk
            
            # Atomic rename
            os.rename(temp_path, filepath)
            return True
            
        except Exception as e:
            logger.warning(f"Atomic write attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # Exponential backoff
```

#### Cleanup Strategy
```python
def cleanup_cache_file(self):
    """Remove cache file for current thread."""
    if self._cache_file_path and os.path.exists(self._cache_file_path):
        try:
            os.remove(self._cache_file_path)
            logger.info(f"Cleaned up cache file: {self._cache_file_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup cache file {self._cache_file_path}: {e}")
```

### 4. ModelValidator Integration

#### Modified `get_responses_for_url()` Method
```python
async def get_responses_for_url(self, url: str) -> list:
    """Process all prompts for a single URL."""
    prompts = self.get_all_prompts()
    responses = []
    
    # Create AiParser instance
    ai_parser = AiParser(
        api_key=self.api_key,
        api_url=self.api_url,
        model=self.model,
        prompt=prompts[0],  # Initial prompt
        project_name=self.project_name,
        pipeline_logger=self.pipeline_logger
    )
    
    try:
        await ai_parser.initialize()
        
        # Step 1: Scrape and cache content once
        cache_path = await ai_parser.scrape_and_cache(url)
        logger.info(f"Cached content for {url} at {cache_path}")
        
        # Step 2: Process all prompts using cached content
        for i, prompt in enumerate(prompts):
            ai_parser.prompt = prompt
            response_content, llm_metrics = ai_parser.get_api_response()
            
            if response_content:
                # Process response as before
                stripped = ai_parser.strip_markdown(response_content)
                data = json.loads(stripped)
                tagged_data = {url: data}
                responses.append(tagged_data)
            
    finally:
        # Step 3: Cleanup cache and browser
        ai_parser.cleanup_cache_file()
        await ai_parser.cleanup()
    
    return responses
```

## Error Handling Strategy

### 1. Scraping Failures
- **Timeout Errors**: Log error, return None, continue with next URL
- **Network Errors**: Retry with exponential backoff (3 attempts max)
- **Content Parsing Errors**: Log warning, continue with available content

### 2. Disk Operation Failures
- **Write Failures**: Retry up to 3 times with exponential backoff
- **Disk Space Issues**: Trigger cleanup of oldest cache files
- **Permission Errors**: Log error, fall back to in-memory processing

### 3. Cache File Corruption
- **Read Failures**: Re-scrape content and create new cache file
- **Invalid Content**: Log error, mark URL as failed

### 4. Concurrency Issues
- **File Conflicts**: Prevented by unique filename generation
- **Resource Contention**: Handled by atomic operations

## Testing Plan

### 1. Unit Tests

#### Test `scrape_and_cache()` Method
```python
class TestAiParserScraping:
    def test_scrape_and_cache_success(self):
        """Test successful scraping and caching."""
        
    def test_scrape_and_cache_network_failure(self):
        """Test handling of network failures."""
        
    def test_scrape_and_cache_disk_failure(self):
        """Test handling of disk write failures."""
        
    def test_cache_filename_uniqueness(self):
        """Test that cache filenames are unique per thread."""
```

#### Test `get_api_response()` Method
```python
class TestAiParserApiResponse:
    def test_get_api_response_cached_content(self):
        """Test API response using cached content."""
        
    def test_get_api_response_lazy_loading(self):
        """Test lazy loading of cache file content."""
        
    def test_get_api_response_file_not_found(self):
        """Test handling when cache file is missing."""
```

### 2. Integration Tests

#### Test End-to-End Flow
```python
class TestIntegrationFlow:
    def test_single_url_multiple_prompts(self):
        """Test processing one URL with multiple prompts."""
        
    def test_multiple_urls_concurrent(self):
        """Test concurrent processing of multiple URLs."""
        
    def test_cache_cleanup(self):
        """Test automatic cleanup of cache files."""
```

### 3. Performance Tests

#### Benchmark Improvements
```python
class TestPerformance:
    def test_scraping_performance_improvement(self):
        """Measure performance improvement vs. old implementation."""
        
    def test_memory_usage_large_pages(self):
        """Test memory usage with large web pages."""
        
    def test_concurrent_processing_scalability(self):
        """Test scalability with multiple concurrent processes."""
```

### 4. Stress Tests

#### High-Volume Testing
```python
class TestStressScenarios:
    def test_ten_thousand_urls(self):
        """Test processing 10,000 URLs."""
        
    def test_disk_space_management(self):
        """Test automatic cleanup when approaching disk limits."""
        
    def test_concurrent_project_processing(self):
        """Test multiple projects processing simultaneously."""
```

## Deployment Considerations

### 1. Environment Setup
- Ensure `scraped_cache/` directory is created and writable
- Add `scraped_cache/` to `.gitignore`
- Configure appropriate disk space monitoring

### 2. Configuration Parameters
```python
# Cache configuration
CACHE_DIR = "scraped_cache"
MAX_CACHE_SIZE_TB = 10
DISK_WRITE_RETRIES = 3
CLEANUP_ON_COMPLETION = True

# Memory thresholds
LARGE_PAGE_THRESHOLD_MB = 250
```

### 3. Monitoring and Logging
- Track cache hit/miss rates
- Monitor disk space usage
- Log cleanup operations
- Track performance improvements

### 4. Rollback Plan
- Keep existing implementation as backup
- Feature flag to switch between old/new implementations
- Gradual rollout with performance monitoring

## Timeline and Milestones

### Phase 1: Core Implementation (Week 1)
- Implement `scrape_and_cache()` method
- Modify `get_api_response()` method
- Add cache management utilities

### Phase 2: Integration (Week 2)
- Update `ModelValidator` class integration
- Implement cleanup mechanisms
- Add comprehensive error handling

### Phase 3: Testing (Week 3)
- Unit test coverage
- Integration testing
- Performance benchmarking

### Phase 4: Deployment (Week 4)
- Production deployment with feature flag
- Performance monitoring
- Gradual rollout and optimization

## Success Metrics

### Performance Metrics
- **Processing Time**: 60-80% reduction for multi-prompt scenarios
- **Network Requests**: Reduction from N×P to N requests (N=URLs, P=prompts)
- **Memory Usage**: Stable memory consumption regardless of page count

### Reliability Metrics
- **Error Rate**: No increase in processing failures
- **Data Integrity**: 100% consistency between old and new implementations
- **Concurrency**: Successful processing of multiple concurrent projects

### Scalability Metrics
- **Throughput**: Process 10,000+ URLs without memory issues
- **Disk Usage**: Automatic cleanup maintaining <10TB cache size
- **Resource Utilization**: Improved CPU/memory efficiency