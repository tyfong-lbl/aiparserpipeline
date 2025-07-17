# AiParser Refactoring Implementation Blueprint

## Overview

This document provides a comprehensive, step-by-step implementation plan for refactoring the AiParser class to eliminate redundant web scraping operations. The refactoring will scrape each webpage only once and reuse the scraped content for multiple LLM API calls with different prompts.

## Implementation Strategy

### Key Principles
- **Test-Driven Development**: Every step starts with writing tests first
- **Incremental Progress**: Small, safe steps that build on each other
- **No Breaking Changes**: Maintain functionality throughout the process
- **Performance Focus**: Achieve 60-80% performance improvement for multi-prompt scenarios
- **Thread Safety**: Support concurrent processing across multiple projects

### Step Dependencies
- Steps 1-2: Foundation (utilities and setup)
- Steps 3-4: Core AiParser enhancements
- Steps 5-6: Cache integration and cleanup
- Steps 7: ModelValidator integration
- Step 8: Comprehensive testing

---

## Implementation Prompts

### Step 1.1: Basic Environment Setup

```
You are refactoring the AiParser class in an AI web scraping pipeline to eliminate redundant scraping. This is Step 1.1 of a comprehensive refactoring that will scrape each webpage only once and reuse content for multiple prompts.

Current task: Set up the basic cache directory environment.

Requirements:
1. Create a `scraped_cache/` directory in the project root if it doesn't exist
2. Add `scraped_cache/` to `.gitignore` if not already present  
3. Verify the directory has proper write permissions
4. Add a simple test to verify the directory setup works

Follow test-driven development:
1. Write a test that verifies the cache directory exists and is writable
2. Implement the setup functionality to make the test pass
3. Ensure no existing functionality is broken

The cache directory will store temporary scraped webpage content during processing. Files will be automatically cleaned up after processing completes.

Do not implement any caching logic yet - this step only sets up the directory infrastructure.
```

### Step 1.2: Test Infrastructure Setup

```
You are continuing the AiParser refactoring project. This is Step 1.2: Set up test infrastructure for cache operations.

Previous step: Created `scraped_cache/` directory and added to .gitignore.

Current task: Create test infrastructure to support cache operation testing.

Requirements:
1. Create a test directory structure for cache-related tests
2. Set up test fixtures that can create/cleanup temporary cache files  
3. Create sample test data (URLs, project names, mock content)
4. Add utilities for test file management

Follow test-driven development:
1. Create test fixtures for temporary cache directory management
2. Create mock data generators for URLs, project names, and scraped content
3. Add helper functions for test file creation and cleanup
4. Write a simple test using these fixtures to verify they work

Focus on creating reusable test infrastructure that will support all future cache testing. Do not implement any actual caching logic yet.

Make sure all test files are created in appropriate test directories and follow the existing test patterns in the codebase.
```

### Step 2.1: Hash Generation Functions - URL Hash

```
You are continuing the AiParser refactoring project. This is Step 2.1: Implement URL hash generation function.

Previous steps: Set up cache directory and test infrastructure.

Current task: Create a utility function to generate consistent hashes from URLs.

Requirements:
1. Create a function that generates a 16-character hash from a URL string
2. Use SHA256 hashing algorithm
3. Ensure the hash is consistent (same URL always produces same hash)
4. Handle URL encoding/normalization properly
5. Function should be in a utility module that can be imported by AiParser

Follow test-driven development:
1. Write tests that verify:
   - Same URL produces same hash consistently
   - Different URLs produce different hashes
   - URL variations (with/without trailing slash, etc.) are handled appropriately
   - Hash length is exactly 16 characters
   - Hash contains only valid filename characters
2. Implement the hash generation function to pass all tests
3. Consider edge cases like very long URLs, special characters, unicode

Do not integrate this with AiParser yet - create it as a standalone utility function with comprehensive tests.

The hash will be used as part of cache filenames to uniquely identify URLs while keeping filenames manageable.
```

### Step 2.2: Project Hash Function

```
You are continuing the AiParser refactoring project. This is Step 2.2: Implement project name hash generation function.

Previous steps: Created cache directory, test infrastructure, and URL hash function.

Current task: Create a utility function to generate consistent hashes from project names.

Requirements:
1. Create a function that generates an 8-character hash from a project name string
2. Use SHA256 hashing algorithm (consistent with URL hash function)
3. Ensure the hash is consistent (same project name always produces same hash)
4. Handle project name variations and special characters properly
5. Add function to the same utility module as the URL hash function

Follow test-driven development:
1. Write tests that verify:
   - Same project name produces same hash consistently
   - Different project names produce different hashes
   - Special characters and spaces in project names are handled
   - Hash length is exactly 8 characters
   - Hash contains only valid filename characters
2. Implement the project hash generation function to pass all tests
3. Test integration with existing URL hash function

Keep the function separate and focused - do not integrate with AiParser yet. Ensure the utility module now has both URL and project hash functions that work well together.

The project hash will combine with URL hash and thread IDs to create unique cache filenames.
```

### Step 2.3: Thread ID Utilities

```
You are continuing the AiParser refactoring project. This is Step 2.3: Implement thread/process ID extraction utilities.

Previous steps: Created hash functions for URLs and project names.

Current task: Create utility functions to extract unique thread and process identifiers.

Requirements:
1. Create a function to get the current process ID (PID)
2. Create a function to get the current asyncio task ID (or 0 if not in async context)
3. Ensure IDs are suitable for use in filenames (numeric, safe characters)
4. Handle edge cases like missing asyncio context gracefully
5. Add functions to the same utility module

Follow test-driven development:
1. Write tests that verify:
   - Process ID is retrieved correctly and is numeric
   - Asyncio task ID is retrieved when in async context
   - Function returns 0 or safe default when not in async context
   - Multiple calls in same context return same IDs
   - Different processes/tasks return different IDs
2. Implement the ID extraction functions to pass all tests
3. Test thread safety and concurrent access scenarios

Focus on creating reliable ID extraction that will ensure cache filename uniqueness across concurrent processes and tasks.

Do not integrate with AiParser yet - keep these as standalone utility functions. The IDs will be combined with URL and project hashes to create unique cache filenames.
```

### Step 2.4: Filename Generation

```
You are continuing the AiParser refactoring project. This is Step 2.4: Implement cache filename generation.

Previous steps: Created hash functions for URLs, project names, and thread ID utilities.

Current task: Create a function that combines all hash components into a unique cache filename.

Requirements:
1. Create a function that combines URL hash, project hash, PID, and task ID into a filename
2. Use format: `cache_{url_hash}_{project_hash}_{pid}_{task_id}.txt`
3. Ensure filename is valid across different operating systems
4. Return full path within the scraped_cache directory
5. Add function to the utility module

Follow test-driven development:
1. Write tests that verify:
   - Filename format matches specification exactly
   - Same inputs always produce same filename
   - Different inputs produce different filenames
   - Filename is valid for filesystem operations
   - Full path points to scraped_cache directory
   - Concurrent calls from different threads produce unique filenames
2. Implement the filename generation function using existing hash and ID functions
3. Test with various input combinations and edge cases

Create comprehensive tests for filename uniqueness across concurrent scenarios. Use the existing hash and ID functions you created in previous steps.

Do not integrate with AiParser yet - this is still utility function development. The filename generation will be used by the cache operations in later steps.
```

### Step 2.5: Atomic Write Function

```
You are continuing the AiParser refactoring project. This is Step 2.5: Implement basic atomic file write function.

Previous steps: Created complete filename generation utilities.

Current task: Create an atomic file write function for safe cache file creation.

Requirements:
1. Create a function that writes content to a file atomically (temp file + rename)
2. Write to temporary file first, then atomically rename to final filename
3. Ensure proper file handles and cleanup
4. Handle basic file write errors
5. Add function to utility module (do not add retry logic yet)

Follow test-driven development:
1. Write tests that verify:
   - Content is written correctly to final file
   - Temporary file is cleaned up after successful write
   - Atomic operation (other processes see complete file or no file)
   - File encoding is handled properly (UTF-8)
   - Basic error handling for write failures
   - Concurrent writes to different files work safely
2. Implement atomic write function using tempfile module
3. Test with various content sizes and types

Focus on the atomic write mechanism only - do not implement retry logic or complex error handling yet. That will come in the next step.

Use Python's tempfile module for safe temporary file creation. Ensure proper cleanup in both success and failure cases.

The atomic write function will be enhanced with retry logic in the next step, then used by the cache operations.
```

### Step 2.6: Retry Logic Addition

```
You are continuing the AiParser refactoring project. This is Step 2.6: Add retry logic to atomic write function.

Previous steps: Created basic atomic write function.

Current task: Enhance the atomic write function with retry logic and exponential backoff.

Requirements:
1. Modify existing atomic write function to support retries (up to 3 attempts)
2. Implement exponential backoff between retry attempts (1s, 2s, 4s)
3. Add comprehensive error logging for retry attempts
4. Raise final exception if all retries fail
5. Maintain same function interface as before

Follow test-driven development:
1. Write tests that verify:
   - Successful write on first attempt works as before
   - Retry logic activates on write failures
   - Exponential backoff timing is correct
   - Final exception is raised after max retries
   - Retry attempts are logged properly
   - Different types of write failures are handled
2. Enhance the existing atomic write function with retry logic
3. Test with simulated disk failures and edge cases

Build upon the existing atomic write function - do not create a new function. Add retry logic while maintaining backward compatibility.

Use proper logging to track retry attempts. Handle different types of file system errors appropriately (disk full, permissions, etc.).

This completes the utility functions needed for cache operations. Next steps will integrate these utilities into the AiParser class.
```

### Step 3.1: Add Instance Variables

```
You are continuing the AiParser refactoring project. This is Step 3.1: Add cache-related instance variables to AiParser class.

Previous steps: Completed all utility functions for cache operations.

Current task: Add new instance variables to AiParser class for cache management.

Requirements:
1. Add `_cache_file_path: Optional[str] = None` instance variable 
2. Add `_cached_content: Optional[str] = None` instance variable
3. Modify `__init__` method to initialize these variables
4. Do not change any existing functionality or method signatures
5. Ensure variables are private (underscore prefix)

Follow test-driven development:
1. Write tests that verify:
   - New instance variables are initialized to None
   - Existing AiParser functionality is unchanged
   - Instance can be created with same parameters as before
   - New variables can be accessed by instance methods
   - Multiple instances have independent variable values
2. Modify AiParser.__init__ to initialize new instance variables
3. Test that existing functionality still works exactly as before

This is a purely additive change - do not modify any existing methods or functionality. The new instance variables will be used by the cache methods in subsequent steps.

Import the utility functions you created in previous steps, but do not use them yet. Focus only on adding the instance variables needed for cache state management.

Verify that all existing tests for AiParser still pass after adding the instance variables. On completion, write a completion summary in markdown to /plans/completion_summaries
```

### Step 4.1: Method Structure

```
You are continuing the AiParser refactoring project. This is Step 4.1: Create scrape_and_cache() method structure.

Previous steps: Added cache instance variables to AiParser class.

Current task: Create the basic structure for the new scrape_and_cache() method.

Requirements:
1. Add async method `scrape_and_cache(self, url: str) -> str` to AiParser class
2. Add comprehensive docstring explaining purpose, parameters, and return value
3. Add basic parameter validation (url must be non-empty string)
4. Add placeholder implementation that raises NotImplementedError
5. Do not implement actual scraping or caching logic yet

Follow test-driven development:
1. Write tests that verify:
   - Method exists and has correct signature
   - Method is async and returns string type hint
   - Parameter validation works (rejects empty/None URLs)
   - NotImplementedError is raised when called
   - Method can be called on AiParser instance
   - Docstring is present and properly formatted
2. Add the method structure to AiParser class
3. Test method signature and basic validation

Focus only on method structure and interface - do not implement any scraping or file operations yet. This establishes the method contract that will be filled in during subsequent steps.

Use the existing AiParser patterns for parameter validation and error handling. Ensure the method signature matches the specification exactly.

The method will return the cache file path when fully implemented, but for now should just raise NotImplementedError after parameter validation.
```

### Step 4.2: Scraping Logic Movement

```
You are continuing the AiParser refactoring project. This is Step 4.2: Move existing scraping logic into scrape_and_cache() method.

Previous steps: Created scrape_and_cache() method structure.

Current task: Move the web scraping logic from select_article_to_api() into scrape_and_cache().

Requirements:
1. Extract the scraping logic from select_article_to_api method (lines ~146-155)
2. Move it into scrape_and_cache method exactly as-is (no modifications)
3. Replace NotImplementedError with the scraping logic
4. Return the scraped fulltext content temporarily (not cache path yet)
5. Do not modify select_article_to_api method yet - keep it working

Follow test-driven development:
1. Write tests that verify:
   - scrape_and_cache() scrapes webpage content correctly
   - Same scraping behavior as original select_article_to_api
   - Title and body text are combined correctly
   - Scraping errors are handled the same way
   - Browser instance is used properly
   - Original select_article_to_api still works unchanged
2. Move scraping logic into scrape_and_cache method
3. Test that both methods work and produce same scraping results

Extract only the web scraping portion (browser operations, title/text extraction, fulltext creation). Do not move any LLM API logic or logging logic.

Keep the original select_article_to_api method fully functional for now. This ensures you can test that both methods produce identical scraping results.

In the next steps, you'll add file caching to scrape_and_cache and then update select_article_to_api to use it. On completion, write a completion summary in markdown to /plans/completion_summaries
```

### Step 4.3: Filename Generation Integration

```
You are continuing the AiParser refactoring project. This is Step 4.3: Add cache filename generation to scrape_and_cache() method.

Previous steps: Moved scraping logic into scrape_and_cache() method.

Current task: Integrate filename generation utilities and store cache file path.

Requirements:
1. Import and use the filename generation utilities created in Step 2.4
2. Generate cache filename using URL, project name, and thread IDs
3. Store the generated cache file path in self._cache_file_path instance variable
4. Return the cache file path instead of scraped content
5. Do not write to file yet - just generate and store the path

Follow test-driven development:
1. Write tests that verify:
   - Cache filename is generated correctly using utility functions
   - Filename includes all required components (URL hash, project hash, PID, task ID)
   - Cache file path is stored in instance variable
   - Method returns the cache file path
   - Multiple calls with same URL generate same filename
   - Concurrent calls generate unique filenames
   - Scraped content is still available (temporarily store it)
2. Integrate filename generation into scrape_and_cache method
3. Test filename generation with various URLs and project names

Use the utility functions you created in steps 2.1-2.4. Import them at the top of the page_tracker.py file.

Temporarily store the scraped content in a local variable or instance variable so it can be used for file writing in the next step. The method should now return the cache file path instead of the scraped content.

Verify that the filename generation produces unique, valid filenames that match the specification format. On completion, write a completion summary in markdown to /plans/completion_summaries
```

### Step 4.4: File Writing Integration

```
You are continuing the AiParser refactoring project. This is Step 4.4: Add atomic file writing to scrape_and_cache() method.

Previous steps: Added filename generation to scrape_and_cache() method.

Current task: Integrate atomic file writing to save scraped content to cache file.

Requirements:
1. Use the atomic write function created in Step 2.6 to write scraped content to cache file
2. Write the fulltext content to the cache file path generated in previous step
3. Ensure the scraped_cache directory exists before writing
4. Handle file writing errors appropriately
5. Still return the cache file path

Follow test-driven development:
1. Write tests that verify:
   - Scraped content is written to correct cache file
   - File content matches exactly what was scraped
   - Atomic write function is used (temp file + rename)
   - Cache directory is created if it doesn't exist
   - File writing errors are handled appropriately
   - Cache file path is returned correctly
   - Multiple concurrent writes work safely
2. Integrate atomic file writing into scrape_and_cache method
3. Test with various content sizes and concurrent operations

Use the atomic write function with retry logic that you created in Step 2.6. Import it at the top of the file.

Ensure the scraped_cache directory exists before attempting to write (create it if necessary). Handle the case where the directory might not exist yet.

The method should now complete the full scrape-and-cache workflow: scrape webpage → generate filename → write to cache file → return cache path.

Add appropriate error handling for file system errors while maintaining existing scraping error handling. On completion, write a completion summary in markdown to /plans/completion_summaries
```

### Step 4.5: Error Handling Addition

```
You are continuing the AiParser refactoring project. This is Step 4.5: Add comprehensive error handling to scrape_and_cache() method.

Previous steps: Integrated atomic file writing into scrape_and_cache() method.

Current task: Add robust error handling for disk operations and scraping failures.

Requirements:
1. Add proper exception handling for disk operation failures
2. Ensure retry logic from atomic write function is utilized
3. Add logging for cache operation failures
4. Handle scraping failures without causing file operation errors
5. Maintain existing error behavior but add disk operation error handling

Follow test-driven development:
1. Write tests that verify:
   - Disk write failures are handled gracefully
   - Retry logic is invoked for temporary disk issues
   - Scraping failures don't cause file system errors
   - Appropriate errors are logged for debugging
   - Method fails fast for permanent disk issues
   - Partial files are not left behind on failures
   - Original scraping error handling is preserved
2. Add comprehensive error handling to scrape_and_cache method
3. Test various failure scenarios (disk full, permissions, network issues)

Build upon the existing error handling in the AiParser class. Use the same logging patterns and error reporting style.

The retry logic should be handled by the atomic write function you created earlier. Focus on handling the errors that the atomic write function might raise after exhausting retries.

Consider the interaction between scraping failures and file operations - ensure that scraping failures don't leave cache files in inconsistent states.

Add appropriate logging messages that will help with debugging cache operation issues in production. On completion, write a completion summary in markdown to /plans/completion_summaries
```

### Step 5.1: Remove fulltext Parameter

```
You are continuing the AiParser refactoring project. This is Step 5.1: Modify get_api_response() method signature.

Previous steps: Completed scrape_and_cache() method with full functionality.

Current task: Remove the fulltext parameter from get_api_response() method and prepare for cache-based content loading.

Requirements:
1. Remove `fulltext: str` parameter from get_api_response() method signature
2. Update method docstring to reflect the change
3. Add temporary backward compatibility check/warning for any callers still passing fulltext
4. Do not change the API call logic yet - focus only on signature change
5. Ensure method still works with existing functionality

Follow test-driven development:
1. Write tests that verify:
   - Method signature no longer accepts fulltext parameter
   - Method can be called without fulltext parameter
   - Backward compatibility warnings work if fulltext is passed
   - Existing API call functionality is preserved
   - Method return format remains unchanged
   - Pipeline logging still works correctly
2. Modify get_api_response method signature
3. Test that signature change doesn't break existing functionality

This is a breaking change to the method interface, so add appropriate warnings or error handling for code that might still try to pass the fulltext parameter.

Update any internal calls to get_api_response() within the AiParser class to use the new signature. Check if the method is called elsewhere in the codebase.

The method should still execute the same API logic, but will need to get content from cache in the next step rather than from the fulltext parameter. On completion, write a completion summary in markdown to /plans/completion_summaries
```

### Step 5.2: Add Cache File Reading

```
You are continuing the AiParser refactoring project. This is Step 5.2: Add cache file reading logic to get_api_response() method.

Previous steps: Removed fulltext parameter from get_api_response() method.

Current task: Add logic to read scraped content from cache file when needed.

Requirements:
1. Add logic to read content from self._cache_file_path when it's set
2. Handle case where cache file path is not set (error condition)
3. Add basic file reading with proper error handling
4. Do not implement in-memory caching yet - read from disk each time
5. Use the content for existing API call logic

Follow test-driven development:
1. Write tests that verify:
   - Content is read correctly from cache file
   - File reading errors are handled appropriately
   - Method fails gracefully if cache file path is not set
   - Method fails gracefully if cache file doesn't exist
   - File encoding (UTF-8) is handled correctly
   - Read content is used for API calls correctly
2. Add cache file reading logic to get_api_response method
3. Test with various cache file scenarios (missing, corrupted, large files)

Add appropriate error handling for file system errors. Use similar error handling patterns as elsewhere in the AiParser class.

The method should check if self._cache_file_path is set, read the content from that file, and use it for the existing API call logic.

Consider what should happen if the cache file is missing or corrupted - should it raise an exception or handle gracefully?

Do not add in-memory caching yet - that will come in the next step. For now, read from disk each time the method is called. On completion, write a completion summary in markdown to /plans/completion_summaries
```

### Step 5.3: Add Memory Caching

```
You are continuing the AiParser refactoring project. This is Step 5.3: Add in-memory content caching to get_api_response() method.

Previous steps: Added cache file reading to get_api_response() method.

Current task: Implement lazy loading with in-memory content storage to avoid repeated disk reads.

Requirements:
1. Check if self._cached_content is already loaded before reading from disk
2. If content is not in memory, read from cache file once and store in self._cached_content
3. Use in-memory content for subsequent calls instead of re-reading file
4. Handle memory clearing and cache invalidation appropriately
5. Maintain existing error handling for file operations

Follow test-driven development:
1. Write tests that verify:
   - Content is loaded from disk only on first call
   - Subsequent calls use in-memory cached content
   - In-memory content matches file content exactly
   - Memory cache is properly initialized
   - File is not read multiple times for same AiParser instance
   - Memory usage is reasonable for large content
   - Cache invalidation works if needed
2. Add lazy loading logic to get_api_response method
3. Test performance improvement from memory caching

Implement a simple lazy loading pattern: check if self._cached_content is None, and if so, read from file and store. Otherwise, use the cached content.

Consider edge cases like what happens if the cache file changes between calls (unlikely in this use case, but good to consider).

The performance improvement should be significant for multiple prompts on the same URL, since the file will only be read once per AiParser instance.

Test both the caching behavior and the memory usage implications for large scraped content. On completion, write a completion summary in markdown to /plans/completion_summaries
```

### Step 5.4: API Processing Integration

```
You are continuing the AiParser refactoring project. This is Step 5.4: Complete API processing integration with cached content.

Previous steps: Added memory caching to get_api_response() method.

Current task: Ensure cached content integrates seamlessly with existing LLM API processing logic.

Requirements:
1. Verify cached content works with existing prompt template substitution
2. Ensure API call timing and metrics are preserved
3. Maintain existing error handling for API responses
4. Preserve existing logging and pipeline integration
5. Ensure method returns same format as before

Follow test-driven development:
1. Write tests that verify:
   - API calls work correctly with cached content
   - Prompt template substitution works as before
   - API response timing metrics are accurate
   - Pipeline logging captures correct information
   - Error handling for API failures is preserved
   - Method return format is unchanged
   - Multiple prompts with same cached content work correctly
2. Verify all existing API processing logic works with cached content
3. Test end-to-end flow from cache file to API response

This step is primarily about verification and testing rather than new code. The existing API processing logic should work seamlessly with the cached content.

Test the complete flow: scrape_and_cache() creates cache file → get_api_response() reads and caches content → processes with LLM API → returns response.

Pay special attention to the prompt template substitution (Template(self.prompt).substitute(values)) and ensure it works correctly with cached content.

Verify that the pipeline logging captures the correct metrics and that the existing error handling paths all work properly.

The get_api_response() method should now be fully functional using cached content instead of the original fulltext parameter. On completion, write a completion summary in markdown to /plans/completion_summaries
```

### Step 6.1: Cleanup Method

```
You are continuing the AiParser refactoring project. This is Step 6.1: Create cleanup_cache_file() method.

Previous steps: Completed get_api_response() method with cache integration.

Current task: Create a method to clean up cache files after processing is complete.

Requirements:
1. Add `cleanup_cache_file(self)` method to AiParser class
2. Remove cache file from disk if it exists
3. Clear in-memory cached content
4. Handle cleanup errors gracefully (log but don't fail)
5. Make method safe to call multiple times

Follow test-driven development:
1. Write tests that verify:
   - Cache file is deleted from disk if it exists
   - In-memory cached content is cleared
   - Method handles case where cache file doesn't exist
   - Method handles file deletion errors gracefully
   - Multiple calls to cleanup are safe
   - Method works when cache was never created
   - Appropriate logging for cleanup operations
2. Implement cleanup_cache_file method
3. Test various cleanup scenarios and error conditions

Focus on safe cleanup that won't crash the application even if file operations fail. Use appropriate logging to track cleanup operations for debugging.

The method should:
- Check if self._cache_file_path exists and points to a real file
- Delete the file if it exists
- Set self._cache_file_path = None
- Set self._cached_content = None
- Log cleanup operations appropriately

Handle file deletion errors (permissions, file in use, etc.) by logging the error but not raising exceptions. The cleanup is a best-effort operation.On completion, write a completion summary in markdown to /plans/completion_summaries
```

### Step 6.2: Cleanup Integration

```
You are continuing the AiParser refactoring project. This is Step 6.2: Integrate cleanup calls into AiParser lifecycle.

Previous steps: Created cleanup_cache_file() method.

Current task: Add cleanup calls to appropriate places in AiParser lifecycle and error handling.

Requirements:
1. Add cleanup call to existing cleanup/close methods in AiParser
2. Ensure cleanup happens in error handling paths
3. Add cleanup to any existing cleanup logic in select_article_to_api if appropriate
4. Do not modify ModelValidator yet - focus only on AiParser internal cleanup
5. Maintain existing cleanup behavior for browser/playwright

Follow test-driven development:
1. Write tests that verify:
   - Cleanup is called when AiParser.cleanup() is called
   - Cleanup is called in error handling paths
   - Existing browser cleanup still works correctly
   - Multiple cleanup calls don't cause issues
   - Cleanup works in various error scenarios
   - Cache files don't accumulate during testing
2. Add cleanup calls to appropriate AiParser methods
3. Test cleanup integration with existing error handling

Look at the existing AiParser.cleanup() method (line ~294) and add cache cleanup to it. Also check if there are other cleanup paths in error handling that should include cache cleanup.

The goal is to ensure cache files are automatically cleaned up when an AiParser instance is done processing, without requiring manual cleanup calls from external code.

Do not modify any ModelValidator code yet - that will come in Step 7. Focus only on making AiParser clean up after itself automatically.

Test that the cleanup integration doesn't interfere with existing browser cleanup or error handling behavior.On completion, write a completion summary in markdown to /plans/completion_summaries
```

### Step 7.1: Method Structure Change

```
You are continuing the AiParser refactoring project. This is Step 7.1: Modify ModelValidator.get_responses_for_url() structure.

Previous steps: Completed AiParser cache functionality with automatic cleanup.

Current task: Restructure ModelValidator.get_responses_for_url() to use scrape-once, process-many pattern.

Requirements:
1. Modify get_responses_for_url() to call scrape_and_cache() once before the prompt loop
2. Keep the prompt processing loop but remove scraping from each iteration
3. Maintain exact same return format and behavior
4. Ensure error handling preserves existing behavior
5. Do not modify select_article_to_api calls yet - focus on method structure

Follow test-driven development:
1. Write tests that verify:
   - Method structure follows scrape-once, process-many pattern
   - scrape_and_cache() is called exactly once per URL
   - Prompt loop processes all prompts correctly
   - Return format is identical to original implementation
   - Error handling behavior is preserved
   - Performance improves (less network requests)
2. Restructure get_responses_for_url method
3. Test that method behavior is functionally identical to original

The new structure should be:
1. Create AiParser instance
2. Initialize browser
3. Call scrape_and_cache(url) once
4. Loop through prompts calling get_api_response() (not select_article_to_api)
5. Cleanup and return results

This is a significant structural change, so comprehensive testing is critical to ensure no behavioral changes.

Keep the existing error handling and logging patterns. The method should produce identical results to the original implementation, just more efficiently. On completion, write a completion summary in markdown to /plans/completion_summaries
```

### Step 7.2: Cleanup Integration

```
You are continuing the AiParser refactoring project. This is Step 7.2: Add cleanup integration to ModelValidator.

Previous steps: Restructured ModelValidator.get_responses_for_url() for scrape-once pattern.

Current task: Ensure proper cleanup happens in ModelValidator error handling paths.

Requirements:
1. Add explicit cleanup calls in ModelValidator error handling
2. Ensure cleanup happens even if processing fails partway through
3. Use try/finally patterns to guarantee cleanup
4. Maintain existing error reporting and logging behavior
5. Test cleanup under various error conditions

Follow test-driven development:
1. Write tests that verify:
   - Cleanup occurs even when processing fails
   - Cleanup occurs even when scraping fails
   - Cleanup occurs even when API calls fail
   - Multiple cleanup calls are safe
   - Error messages and logging are preserved
   - Resources are properly cleaned up under all conditions
2. Add cleanup integration to ModelValidator error handling
3. Test various failure scenarios to ensure cleanup always happens

Look at the existing error handling in get_responses_for_url() and ensure that cache cleanup is added to all error paths.

Use try/finally blocks or context managers to ensure cleanup happens even if exceptions are raised during processing.

The cleanup should be in addition to the automatic cleanup in AiParser - this provides an extra safety net for the ModelValidator integration.

Pay special attention to the case where scrape_and_cache() succeeds but subsequent prompt processing fails - the cache file should still be cleaned up.

This completes the integration of the cache system with the existing ModelValidator workflow. On completion, write a completion summary in markdown to /plans/completion_summaries
```

### Step 8.1: Unit Test Completion

```
You are continuing the AiParser refactoring project. This is Step 8.1: Complete comprehensive unit test coverage.

Previous steps: Completed full integration of cache system with ModelValidator.

Current task: Ensure comprehensive unit test coverage for all new functionality.

Requirements:
1. Review and complete unit tests for all utility functions
2. Add comprehensive unit tests for all new AiParser methods
3. Add edge case testing for error conditions
4. Add performance regression tests
5. Verify test coverage meets requirements

Follow test-driven development:
1. Analyze test coverage for all new code:
   - Hash generation functions
   - Filename generation
   - Atomic write operations
   - scrape_and_cache() method
   - Modified get_api_response() method
   - cleanup_cache_file() method
2. Add missing unit tests for any gaps found
3. Add edge case and error condition testing
4. Add performance tests to verify improvements

Focus on achieving high test coverage while ensuring tests are meaningful and catch real issues.

Include tests for:
- Concurrent operations and thread safety
- Error conditions and recovery
- Performance characteristics
- Memory usage with large content
- File system edge cases

Create tests that verify the refactoring achieves its performance goals:
- Fewer network requests for multi-prompt scenarios
- Proper memory usage
- Correct cache file cleanup

This step should result in a comprehensive test suite that gives confidence in the refactored implementation.On completion, write a completion summary in markdown to /plans/completion_summaries
```

### Step 8.2: Integration Testing

```
You are continuing the AiParser refactoring project. This is Step 8.2: Create comprehensive integration test suite.

Previous steps: Completed unit test coverage for all components.

Current task: Create integration tests that verify end-to-end functionality and performance improvements.

Requirements:
1. Create end-to-end workflow tests from ModelValidator through AiParser
2. Add multi-prompt processing verification tests
3. Add concurrency testing for multiple projects/threads
4. Add performance benchmark tests comparing old vs new implementation
5. Add integration tests with real web scraping (if safe to do so)

Follow test-driven development:
1. Create integration tests that verify:
   - Complete workflow from URL input to final results
   - Multi-prompt processing produces same results as original
   - Performance improvements are measurable
   - Concurrent processing works correctly
   - Cache files are properly managed across full workflows
   - Pipeline logging captures correct metrics
   - Error handling works end-to-end
2. Implement comprehensive integration test suite
3. Run performance benchmarks to verify improvements

Focus on tests that verify the system works correctly as a whole, not just individual components.

Include performance benchmarks that demonstrate:
- Reduced processing time for multi-prompt scenarios
- Fewer network requests
- Proper memory usage patterns
- Scalability improvements

Test various scenarios:
- Single URL, multiple prompts
- Multiple URLs, multiple prompts each
- Concurrent processing of different projects
- Error recovery scenarios

The integration tests should provide confidence that the refactoring achieves all its goals: better performance, maintained functionality, and reliable operation at scale.

This completes the comprehensive refactoring of the AiParser class to eliminate redundant web scraping while maintaining all existing functionality. On completion, write a completion summary in markdown to /plans/completion_summaries
```

---

## Implementation Summary

This blueprint provides 16 carefully designed implementation steps that:

### **Ensure Safety**
- Start with low-risk foundation work
- Build incrementally without breaking existing functionality
- Provide comprehensive testing at each stage
- Include rollback capabilities

### **Maximize Performance**
- Eliminate redundant web scraping operations
- Implement memory-safe disk caching
- Support concurrent processing
- Provide automatic resource cleanup

### **Maintain Quality**
- Follow test-driven development principles
- Preserve all existing functionality
- Add comprehensive error handling
- Include performance benchmarks

### **Expected Outcomes**
- 60-80% reduction in processing time for multi-prompt scenarios
- Memory-safe processing of large web pages
- Thread-safe concurrent processing
- Comprehensive test coverage
- Production-ready implementation

Each step builds upon the previous work, ensuring no orphaned code and maintaining integration throughout the refactoring process.