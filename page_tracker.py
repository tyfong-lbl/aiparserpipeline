import ast
import asyncio
import openai
import numpy as np
import concurrent.futures
import logging
import pandas as pd
import re
import sqlite3
import time
import json
from datetime import datetime
from pathlib import Path
from string import Template
from tqdm import tqdm
from playwright.async_api import async_playwright
from typing import Optional

# Import cache utilities (will be used in later steps)
from cache_utils import (
    generate_cache_filename,
    atomic_write_file
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure diagnostic logging goes to a specific file
if not logger.handlers:
    diagnostic_handler = logging.FileHandler('diagnostic_output.log')
    diagnostic_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    diagnostic_handler.setFormatter(diagnostic_formatter)
    logger.addHandler(diagnostic_handler)
    # Also add console output
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(diagnostic_formatter)
    logger.addHandler(console_handler)

class AiParser:
    def __init__(self,
                 api_key:str,
                 api_url:str,
                 model:str,
                 prompt:str,
                 project_name:str,
                 publication_url=None,
                 pipeline_logger=None
                 ) -> None:
        self.model = model
        self.prompt = prompt
        self.project_name = project_name
        self.api_key = api_key
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=api_url
        )
        self.publication_url = publication_url
        self.playwright = None
        self.browser = None
        self.pipeline_logger = pipeline_logger
        
        # Cache-related instance variables for storing cache file path and content
        self._cache_file_path: Optional[str] = None
        self._cached_content: Optional[str] = None

    async def initialize(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch()

    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def scrape_and_cache(self, url: str) -> tuple:
        """
        Scrape a webpage and cache its content for reuse with multiple prompts.

        This method performs web scraping of the provided URL and stores the content
        in a cache file for efficient reuse across multiple LLM API calls with different
        prompts. This eliminates redundant network requests and improves performance
        when processing the same URL with multiple prompts.

        The method includes comprehensive error handling for:
        - Network failures and browser errors during scraping
        - Disk operation failures with retry logic via atomic write function
        - File system errors (permissions, disk full, etc.)
        - Memory pressure from large content
        - Unicode encoding issues

        The method:
        1. Validates the input URL parameter
        2. Scrapes the webpage content using Playwright browser automation
        3. Generates a unique cache filename based on URL, project name, and thread IDs
        4. Stores the scraped content atomically in the cache file with retry logic
        5. Returns a tuple containing the success status and the path to the cache file

        Args:
            url (str): The URL to scrape and cache. Must be a non-empty string
                      representing a valid web address.

        Returns:
            tuple: (scraping_successful, cache_file_path) where:
                - scraping_successful (bool): True if scraping was successful and returned non-empty content,
                                              False otherwise
                - cache_file_path (str): The full path to the cache file containing the scraped content.
                                        The cache file can be read later to retrieve the scraped content
                                        without re-scraping the webpage. Returns path even if scraping
                                        or file operations fail (for consistency in calling code).

        Raises:
            ValueError: If url is None, empty string, or contains only whitespace
            TypeError: If url is not a string

        Example:
            >>> ai_parser = AiParser(api_key="...", api_url="...", ...)
            >>> await ai_parser.initialize()
            >>> success, cache_path = await ai_parser.scrape_and_cache("https://example.com")
            >>> print(f"Content cached at: {cache_path}, Success: {success}")

        Note:
            This method is part of the AiParser refactoring to eliminate redundant
            web scraping. It uses atomic file operations with retry logic and
            comprehensive error handling to ensure reliable cache file creation.
        """
        # Parameter validation - ensure URL is valid
        if url is None:
            raise ValueError("URL cannot be None")

        if not isinstance(url, str):
            raise TypeError("URL must be a string")

        # Check for empty or whitespace-only URLs
        if not url or not url.strip():
            raise ValueError("URL cannot be empty or contain only whitespace")

        # Generate cache filename using utility functions
        # Store the cache file path regardless of success/failure for consistency
        cache_file_path = None
        try:
            cache_file_path = generate_cache_filename(url, self.project_name)
            self._cache_file_path = cache_file_path
            logger.debug(f"Generated cache file path: {cache_file_path}")
        except Exception as e:
            logger.error(f"Error generating cache filename for URL {url}: {type(e).__name__}: {e}")
            # If we can't generate cache filename, we still need to return something
            # Use a fallback approach
            import tempfile
            temp_dir = Path(tempfile.gettempdir()) / "scraped_cache_fallback"
            temp_dir.mkdir(exist_ok=True)
            cache_file_path = str(temp_dir / f"cache_fallback_{abs(hash(url))}.txt")
            self._cache_file_path = cache_file_path
            logger.warning(f"Using fallback cache file path: {cache_file_path}")

        # Web scraping operation with comprehensive error handling
        page = None
        fulltext = ""
        scraping_successful = False
        scraping_error = None

        try:
            logger.debug(f"Starting web scraping for URL: {url}")
            page = await self.browser.new_page()

            # Navigate to page with error handling
            try:
                await page.goto(url, timeout=30000)  # 30 second timeout
                logger.debug(f"Successfully navigated to URL: {url}")
            except Exception as nav_error:
                logger.error(f"Navigation failed for URL {url}: {type(nav_error).__name__}: {nav_error}")
                raise nav_error

            # Extract title and content with error handling
            try:
                title = await page.title()
                text = await page.evaluate('() => document.body.innerText')
                fulltext = f"{title}.\n\n{text}"

                # Check if the extracted content is empty or only whitespace
                if fulltext and fulltext.strip():
                    scraping_successful = True
                    logger.debug(f"Successfully scraped content from {url} (length: {len(fulltext)} chars)")

                    # Check for unusually large content and log warning
                    if len(fulltext) > 5 * 1024 * 1024:  # 5MB threshold
                        logger.warning(f"Large content detected for {url}: {len(fulltext)} characters")
                else:
                    logger.warning(f"No meaningful content extracted from {url}. Fulltext length: {len(fulltext)} chars")
                    scraping_successful = False

            except Exception as extract_error:
                logger.error(f"Content extraction failed for URL {url}: {type(extract_error).__name__}: {extract_error}")
                raise extract_error

        except Exception as e:
            # Handle all scraping errors comprehensively
            scraping_error = e
            error_type = type(e).__name__
            logger.error(f"Error during web scraping for URL {url}: {error_type}: {e}")

            # Log additional context for debugging
            logger.error(f"Scraping error context - URL: {url}, Project: {self.project_name}")

            # Set empty content on scraping error - this ensures file operations don't fail
            fulltext = ""
            scraping_successful = False

        finally:
            # Ensure browser page cleanup happens regardless of success/failure
            if page is not None:
                try:
                    await page.close()
                    logger.debug(f"Browser page closed for URL: {url}")
                except Exception as cleanup_error:
                    # Log cleanup errors but don't let them affect the main operation
                    logger.warning(f"Error during page cleanup for URL {url}: {type(cleanup_error).__name__}: {cleanup_error}")
                    # Continue execution - cleanup errors should not fail the entire operation

        # File writing operation with comprehensive error handling
        file_write_successful = False
        file_write_error = None

        try:
            logger.debug(f"Attempting to write cache file: {cache_file_path}")

            # Ensure the cache directory exists before writing
            cache_dir = Path(cache_file_path).parent
            try:
                cache_dir.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Cache directory confirmed/created: {cache_dir}")
            except Exception as dir_error:
                logger.error(f"Error creating cache directory {cache_dir}: {type(dir_error).__name__}: {dir_error}")
                # Continue with write attempt - atomic_write_file will handle directory creation

            # Use atomic write function (which includes retry logic)
            atomic_write_file(cache_file_path, fulltext)
            file_write_successful = True
            logger.debug(f"Successfully wrote cache file: {cache_file_path} ({len(fulltext)} chars)")

        except Exception as e:
            # Handle file writing errors comprehensively
            file_write_error = e
            error_type = type(e).__name__
            logger.error(f"Error writing cache file {cache_file_path}: {error_type}: {e}")

            # Log additional context for debugging
            logger.error(f"File write error context - Cache path: {cache_file_path}, Content length: {len(fulltext)}")
            logger.error(f"Project: {self.project_name}, URL: {url}")

            # Check for specific error types and provide actionable information
            if isinstance(e, PermissionError):
                logger.error(f"Permission denied writing to {cache_file_path}. Check file/directory permissions.")
            elif isinstance(e, OSError) and "No space left" in str(e):
                logger.error(f"Disk full error writing to {cache_file_path}. Free up disk space.")
            elif isinstance(e, OSError) and "Read-only file system" in str(e):
                logger.error(f"Read-only filesystem error writing to {cache_file_path}. Check filesystem mount options.")
            else:
                logger.error(f"Unexpected file system error: {e}")

        # Log final operation summary for debugging
        if scraping_successful and file_write_successful:
            logger.info(f"Successfully scraped and cached {url} -> {cache_file_path}")
        elif scraping_successful and not file_write_successful:
            logger.warning(f"Scraped {url} successfully but cache write failed -> {cache_file_path}")
        elif not scraping_successful and file_write_successful:
            logger.warning(f"Scraping failed for {url} but empty cache file created -> {cache_file_path}")
        else:
            logger.error(f"Both scraping and cache writing failed for {url} -> {cache_file_path}")

        # Return a tuple with success status and cache file path
        # This allows the calling code to properly handle cases where scraping failed
        # or returned empty content
        return (scraping_successful, cache_file_path)
      
    async def get_articles_urls(self) -> list:
        if not self.publication_url:
            return []
        
        page = await self.browser.new_page()
        await page.goto(self.publication_url)
        article_urls = await page.evaluate("""
            () => Array.from(document.querySelectorAll('a')).map(a => a.href)
                .filter(href => href.includes('/article/') || href.includes('/news/'))
        """)
        await page.close()
        return article_urls
    
    def get_api_response(self, **kwargs):
        """
        Generate an API response using cached content or provided content (deprecated).
        
        This method processes content through the LLM API using the configured prompt template.
        In the new implementation, content is read from the cache file path set by scrape_and_cache().
        
        The method includes backward compatibility for internal AiParser usage during the
        refactoring transition period. External usage with fulltext parameter is deprecated.
        
        Args:
            **kwargs: Keyword arguments. The 'fulltext' parameter is deprecated for external use
                     but temporarily supported for internal AiParser methods during refactoring.
        
        Returns:
            tuple: (response_content, llm_metrics) where:
                - response_content: The LLM's response content or None if failed
                - llm_metrics: Dictionary containing response status, error info, and timing
        
        Raises:
            ValueError: If external code uses deprecated fulltext parameter or cache file path is not set
            FileNotFoundError: If cache file doesn't exist (when using cache mode)
            IOError: If cache file cannot be read (when using cache mode)
        """
        # Handle backward compatibility for internal AiParser usage during refactoring
        fulltext = None
        using_cached_content = True
        
        if 'fulltext' in kwargs:
            # Temporary backward compatibility during refactoring transition
            # The fulltext parameter is deprecated but still supported in Step 5.1
            # It will be completely removed in Step 7
            fulltext = kwargs['fulltext']
            using_cached_content = False
            
            # Log deprecation warning
            import inspect
            frame = inspect.currentframe()
            try:
                caller_frame = frame.f_back
                caller_function = caller_frame.f_code.co_name if caller_frame else 'unknown'
                logger.warning(
                    f"DEPRECATED: Method '{caller_function}' using fulltext parameter in get_api_response(). "
                    "Parameter will be removed in Step 7. Use scrape_and_cache() + get_api_response() instead."
                )
            finally:
                del frame
        
        # Check for other unexpected parameters
        remaining_kwargs = {k: v for k, v in kwargs.items() if k != 'fulltext'}
        if remaining_kwargs:
            unexpected_params = list(remaining_kwargs.keys())
            raise TypeError(f"get_api_response() got unexpected keyword arguments: {unexpected_params}")
        
        # Read content from cache if not provided via deprecated fulltext parameter
        if using_cached_content:
            # Check if cache file path is set
            if not self._cache_file_path:
                raise ValueError("Cache file path not set. Call scrape_and_cache() first.")
            
            # Implement lazy loading with in-memory content caching
            # Check if content is already loaded in memory
            if self._cached_content is not None:
                # Use cached content from memory (avoids disk I/O)
                fulltext = self._cached_content
                logger.debug(f"Using cached content from memory ({len(fulltext)} chars)")
            else:
                # Content not in memory - read from cache file and store in memory
                try:
                    with open(self._cache_file_path, 'r', encoding='utf-8') as cache_file:
                        fulltext = cache_file.read()
                    
                    # Store content in memory for subsequent calls
                    self._cached_content = fulltext
                    logger.debug(f"Loaded and cached content from {self._cache_file_path} ({len(fulltext)} chars)")
                    
                except FileNotFoundError:
                    raise FileNotFoundError(f"Cache file not found: {self._cache_file_path}")
                except IOError as e:
                    raise IOError(f"Error reading cache file {self._cache_file_path}: {e}")
        
        # Prepare prompt with template substitution
        values = {"PROJECT": self.project_name}
        template = Template(self.prompt)
        prompt_for_submission = template.substitute(values)
        
        # Start timing for LLM processing
        llm_start_time = time.perf_counter()
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0.0,
                messages=[
                    {
                        "role": "user",
                        "content": f"{prompt_for_submission}{fulltext} "
                    }
                ]
            )
            llm_end_time = time.perf_counter()
            llm_processing_time = llm_end_time - llm_start_time
            
            response_content = response.choices[0].message.content if response.choices else None
            
            llm_metrics = {
                'llm_response_status': response_content is not None,
                'llm_response_error': None if response_content else "No response content from API",
                'llm_processing_time': llm_processing_time
            }
            
            return response_content, llm_metrics
            
        except Exception as e:
            llm_end_time = time.perf_counter()
            llm_processing_time = llm_end_time - llm_start_time
            
            logger.error(f"Error in API call: {e}")
            
            llm_metrics = {
                'llm_response_status': False,
                'llm_response_error': str(e),
                'llm_processing_time': llm_processing_time
            }
            
            return None, llm_metrics

    def clear_memory_cache(self):
        """
        Clear the in-memory cached content.
        
        This method clears the cached content stored in memory, forcing the next
        call to get_api_response() to re-read from the cache file. This can be
        useful for memory management or when you need to ensure fresh content
        is loaded.
        
        Note: This does not affect the cache file on disk, only the in-memory copy.
        """
        if self._cached_content is not None:
            content_size = len(self._cached_content)
            self._cached_content = None
            logger.debug(f"Cleared in-memory cached content ({content_size} chars)")
        else:
            logger.debug("No in-memory cached content to clear")

    def cleanup_cache_file(self):
        """
        Clean up cache files after processing is complete.
        
        This method performs comprehensive cleanup of both disk cache files and
        in-memory cached content. It's designed to be safe to call multiple times
        and handles errors gracefully without raising exceptions.
        
        The method:
        1. Removes the cache file from disk if it exists
        2. Clears the in-memory cached content
        3. Resets cache file path to None
        4. Logs cleanup operations for debugging
        5. Handles all cleanup errors gracefully (logs but doesn't fail)
        
        This method is automatically called during AiParser cleanup and can also
        be called manually when cache cleanup is needed.
        
        Note: This is a best-effort operation - if cleanup fails, it logs the
        error but continues execution to avoid breaking the application.
        """
        cleanup_operations = []
        
        # Step 1: Remove cache file from disk if it exists
        if self._cache_file_path:
            try:
                cache_path = Path(self._cache_file_path)
                if cache_path.exists() and cache_path.is_file():
                    file_size = cache_path.stat().st_size
                    cache_path.unlink()  # Remove the file
                    cleanup_operations.append(f"Removed cache file {self._cache_file_path} ({file_size} bytes)")
                    logger.debug(f"Successfully removed cache file: {self._cache_file_path}")
                elif cache_path.exists():
                    logger.warning(f"Cache path exists but is not a file: {self._cache_file_path}")
                    cleanup_operations.append(f"Skipped non-file cache path: {self._cache_file_path}")
                else:
                    logger.debug(f"Cache file does not exist (already cleaned?): {self._cache_file_path}")
                    cleanup_operations.append(f"Cache file already removed: {self._cache_file_path}")
                    
            except PermissionError as e:
                error_msg = f"Permission denied removing cache file {self._cache_file_path}: {e}"
                logger.error(error_msg)
                cleanup_operations.append(f"Permission error: {error_msg}")
            except OSError as e:
                error_msg = f"OS error removing cache file {self._cache_file_path}: {e}"
                logger.error(error_msg)
                cleanup_operations.append(f"OS error: {error_msg}")
            except Exception as e:
                error_msg = f"Unexpected error removing cache file {self._cache_file_path}: {type(e).__name__}: {e}"
                logger.error(error_msg)
                cleanup_operations.append(f"Unexpected error: {error_msg}")
        else:
            logger.debug("No cache file path set, skipping disk cleanup")
            cleanup_operations.append("No cache file path to clean")
        
        # Step 2: Clear in-memory cached content
        try:
            if self._cached_content is not None:
                content_size = len(self._cached_content)
                self._cached_content = None
                cleanup_operations.append(f"Cleared in-memory content ({content_size} chars)")
                logger.debug(f"Cleared in-memory cached content ({content_size} chars)")
            else:
                logger.debug("No in-memory cached content to clear")
                cleanup_operations.append("No in-memory content to clear")
        except Exception as e:
            error_msg = f"Error clearing in-memory cache: {type(e).__name__}: {e}"
            logger.error(error_msg)
            cleanup_operations.append(f"Memory clear error: {error_msg}")
        
        # Step 3: Reset cache file path
        try:
            if self._cache_file_path:
                old_path = self._cache_file_path
                self._cache_file_path = None
                cleanup_operations.append(f"Reset cache path: {old_path}")
                logger.debug(f"Reset cache file path: {old_path}")
            else:
                cleanup_operations.append("Cache path already None")
        except Exception as e:
            error_msg = f"Error resetting cache path: {type(e).__name__}: {e}"
            logger.error(error_msg)
            cleanup_operations.append(f"Path reset error: {error_msg}")
        
        # Log summary of cleanup operations
        if cleanup_operations:
            logger.info(f"Cache cleanup completed: {'; '.join(cleanup_operations)}")
        else:
            logger.debug("Cache cleanup completed with no operations needed")

    @staticmethod
    def strip_markdown(text):
        if text is None:
            return "{}"  # Return empty JSON object if text is None
        json_pattern = re.search(r'{.*}', text, re.DOTALL)
        if json_pattern:
            return json_pattern.group(0).strip()
        else:
            logger.warning(f"No JSON-like content found in the response: {text[:100]}...")  # Log first 100 chars
            return "{}"  # Return empty JSON object if no match found


    async def select_article_to_api(self, url:str, include_url:bool=True, avg_pause=0):
        # Start timing for text extraction
        text_extraction_start_time = time.perf_counter()
        text_extraction_status = False
        text_extraction_error = None
        text_length = 0
        
        try:
            page = await self.browser.new_page()
            await page.goto(url)
            title = await page.title()
            text = await page.evaluate('() => document.body.innerText')
            await page.close()
            
            fulltext = f"{title}.\n\n{text}"
            text_length = len(fulltext)
            if text_length == 0:
                text_extraction_status = False
                text_extraction_error = "Text length is {text_length}"
            
        except Exception as e:
            logger.error(f"Error fetching article: {e}")
            text_extraction_status = False
            text_extraction_error = str(e)
            fulltext = ""
            text_length = 0
            
            # DIAGNOSTIC: Log what type of error occurred
            logger.error(f"DIAGNOSTIC: Text extraction failed for {url} with error: {str(e)}")
            logger.error(f"DIAGNOSTIC: Pipeline logger exists: {self.pipeline_logger is not None}")
            
            # Store logging context for later use
            if self.pipeline_logger:
                self.current_logging_context = {
                    'url': url,
                    'project_name': self.project_name,
                    'text_extraction_start_time': text_extraction_start_time,
                    'text_extraction_status': text_extraction_status,
                    'text_extraction_error': text_extraction_error,
                    'text_length': text_length
                }
                
                # DIAGNOSTIC: Confirm context was stored
                logger.error(f"DIAGNOSTIC: Stored logging context for failed text extraction")
                
                # FIX: Complete logging cycle for text extraction failures
                # Create dummy LLM metrics since no LLM processing occurred
                dummy_llm_metrics = {
                    'llm_response_status': False,
                    'llm_response_error': 'Text extraction failed - no LLM processing attempted',
                    'llm_processing_time': 0
                }
                
                logger.error(f"DIAGNOSTIC: About to call _complete_logging_cycle for text extraction failure")
                self._complete_logging_cycle(dummy_llm_metrics)
                logger.error(f"DIAGNOSTIC: Completed logging cycle for text extraction failure")
            
            return None

        # Store logging context for successful text extraction
        if self.pipeline_logger:
            self.current_logging_context = {
                'url': url,
                'project_name': self.project_name,
                'text_extraction_start_time': text_extraction_start_time,
                'text_extraction_status': text_extraction_status,
                'text_extraction_error': text_extraction_error,
                'text_length': text_length
            }
    
        try:
            response_content, llm_metrics = self.get_api_response(fulltext=fulltext)
            if response_content is None:
                logger.error("No response content from API")
                # Complete logging cycle for failed LLM processing
                if self.pipeline_logger and hasattr(self, 'current_logging_context'):
                    self._complete_logging_cycle(llm_metrics)
                return None
            stripped = self.strip_markdown(response_content)
            data = json.loads(stripped)
        except json.JSONDecodeError as e:
            logger.error(f"JSONDecodeError encountered: {e}")
            # Complete logging cycle for failed JSON parsing
            if self.pipeline_logger and hasattr(self, 'current_logging_context'):
                llm_metrics = {
                    'llm_response_status': False,
                    'llm_response_error': f"JSONDecodeError: {str(e)}",
                    'llm_processing_time': 0
                }
                self._complete_logging_cycle(llm_metrics)
            return None
        except Exception as e:
            logger.error(f"Unexpected error during API response handling: {e}")
            # Complete logging cycle for unexpected errors
            if self.pipeline_logger and hasattr(self, 'current_logging_context'):
                llm_metrics = {
                    'llm_response_status': False,
                    'llm_response_error': str(e),
                    'llm_processing_time': 0
                }
                self._complete_logging_cycle(llm_metrics)
            return None

        # Complete logging cycle for successful processing
        if self.pipeline_logger and hasattr(self, 'current_logging_context'):
            self._complete_logging_cycle(llm_metrics)

        tagged_data = {url: data} if include_url else data

        if avg_pause > 0:
            pause = abs(np.random.normal(avg_pause, avg_pause/2))
            await asyncio.sleep(pause)

        return tagged_data

    def _complete_logging_cycle(self, llm_metrics):
        """Complete the logging cycle by writing to CSV with all collected metrics."""
        if not self.pipeline_logger or not hasattr(self, 'current_logging_context'):
            return
            
        context = self.current_logging_context
        
        # Calculate total response time
        text_extraction_time = time.perf_counter() - context['text_extraction_start_time']
        llm_processing_time = llm_metrics.get('llm_processing_time', 0)
        total_response_time_ms = int((text_extraction_time + llm_processing_time) * 1000)
        
        # Generate current timestamp
        current_timestamp = datetime.now().astimezone().isoformat()
        
        # Convert status values to strings and handle None errors
        text_extraction_status_str = "True" if context['text_extraction_status'] else "False"
        text_extraction_error_str = context['text_extraction_error'] if context['text_extraction_error'] else "None"
        
        llm_response_status_str = "True" if llm_metrics['llm_response_status'] else "False"
        llm_response_error_str = llm_metrics['llm_response_error'] if llm_metrics['llm_response_error'] else "None"
        
        # Log to CSV
        self.pipeline_logger.log_url_processing(
            url=context['url'],
            project_name=context['project_name'],
            timestamp=current_timestamp,
            text_extraction_status=text_extraction_status_str,
            text_extraction_error=text_extraction_error_str,
            text_length=context['text_length'],
            llm_response_status=llm_response_status_str,
            llm_response_error=llm_response_error_str,
            response_time_ms=total_response_time_ms
        )

    def articles_parser(self, urls: list, include_url=True, max_limit: int = None) -> list:
        if max_limit is None:
            max_limit = len(urls)
        data = [result for result in (self.select_article_to_api(url,include_url) for url in tqdm(urls[:max_limit], desc="Parsing articles")) if result is not None]
        return data
    
    async def cleanup(self):
        # Clean up cache files and memory first
        try:
            self.cleanup_cache_file()
        except Exception as e:
            # Log cache cleanup errors but don't let them prevent browser cleanup
            logger.error(f"Error during cache cleanup in AiParser.cleanup(): {type(e).__name__}: {e}")
        
        # Then clean up browser resources
        if self.browser:
            try:
                await self.browser.close()
            except Exception as e:
                logger.error(f"Error closing browser in AiParser.cleanup(): {type(e).__name__}: {e}")
        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception as e:
                logger.error(f"Error stopping playwright in AiParser.cleanup(): {type(e).__name__}: {e}")
    
class RateLimitWrapper:
    """
    Used to test requests per minute and then limit 
    """
    def __init__(self, ai_parser, limit=None):
        self.ai_parser = ai_parser
        self.limit = limit
        self.last_reset = time.time()
        self.calls = 0
        self.max_calls = 0


def remove_nan(x):
    print(f"Received value: {x}")
    if isinstance(x, str) and x.startswith('['):
        x = ast.literal_eval(x) 
        x = [i for i in x if i != 'nan']
        return x
    elif isinstance(x, list):
        return [i for i in x if not pd.isnull(i)]
    else:
        return x

class ModelValidator:
    def __init__(self,
                 number_of_queries: int,
                 prompt_dir_path,
                 prompt_filename_base: str,
                 api_key: str,
                 api_url: str,
                 model: str,
                 project_name:str,
                 url_df: pd.DataFrame,
                 parser=AiParser,
                 pipeline_logger=None

                 ) -> None:
        self.number_of_queries = number_of_queries
        self.prompt_file_base = prompt_filename_base
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.prompt_dir = prompt_dir_path
        self.project_name = project_name
        self.url_df = url_df
        self.pipeline_logger = pipeline_logger
    
    
    def read_file(self, file_path):
        try:
            with open(file_path, 'r') as file:
                return file.read()
        except FileNotFoundError:
            print(f"Error: File '{file_path}' not found.")
            return None
        except Exception as e:
            print(f"Error: An error occurred while reading '{file_path}': {e}")
            return None


    def read_files_concurrently(self, file_paths):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            contents = list(executor.map(self.read_file, file_paths))
        return contents


    def get_all_prompts(self)-> dict:
        """Get prompts and output into an array"""
        prompt_nums = range(1,self.number_of_queries+1)
        prompt_filenames = [Path(self.prompt_dir,f'{self.prompt_file_base}{x}.txt') 
                            for x in prompt_nums ]
        prompts = self.read_files_concurrently(prompt_filenames)
        return prompts
    

    async def get_responses_for_url(self,url)->list:
        """
        For a particular URL, get all the responses to prompts using scrape-once pattern.
        
        This method has been restructured to follow the scrape-once, process-many pattern:
        1. Scrape the URL content once and cache it
        2. Process all prompts against the cached content
        3. Return results in the same format as the original implementation
        
        This eliminates redundant network requests while maintaining identical behavior.
        """
        import os
        process_id = os.getpid()
        task_id = id(asyncio.current_task()) if asyncio.current_task() else "NO_TASK"
        
        # DIAGNOSTIC: Log URL processing start
        logger.info(f"DIAGNOSTIC: Starting get_responses_for_url for {url} in project {self.project_name} - PID: {process_id}, Task ID: {task_id}")
        
        # Start timing for text extraction (pipeline logging)
        text_extraction_start_time = time.perf_counter()
        text_extraction_status = False
        text_extraction_error = None
        text_length = 0
        
        prompts = self.get_all_prompts()
        responses = []
        
        # DIAGNOSTIC: Log prompt count
        logger.info(f"DIAGNOSTIC: Processing {len(prompts)} prompts for URL {url} - PID: {process_id}")
        
        ai_parser = AiParser(api_key=self.api_key,
                             api_url=self.api_url,
                             model=self.model,
                             prompt=prompts[0],
                             project_name=self.project_name,
                             pipeline_logger=self.pipeline_logger)
        
        # Store logging context for pipeline logging
        if self.pipeline_logger:
            logging_context = {
                'url': url,
                'project_name': self.project_name,
                'text_extraction_start_time': text_extraction_start_time,
                'text_extraction_status': text_extraction_status,
                'text_extraction_error': text_extraction_error,
                'text_length': text_length
            }
        
        # Ensure cleanup happens under all conditions, including initialization failures
        try:
            # Step 1: Initialize browser
            await ai_parser.initialize()
            
            # Step 2: Scrape and cache the URL content once
            try:
                # scrape_and_cache now returns a tuple (scraping_successful, cache_path)
                scraping_result = await ai_parser.scrape_and_cache(url)
                scraping_successful = scraping_result[0]
                cache_path = scraping_result[1]

                logger.info(f"DIAGNOSTIC: Scraped {url} -> {cache_path} - Success: {scraping_successful} - PID: {process_id}")

                # Set text extraction status based on actual scraping success
                text_extraction_status = scraping_successful
                text_extraction_error = None if scraping_successful else "No meaningful content extracted"

                # Get text length from cached content
                try:
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        cached_content = f.read()
                        text_length = len(cached_content)
                except Exception:
                    text_length = 0  # Fallback if we can't read cache

                if self.pipeline_logger:
                    logging_context.update({
                        'text_extraction_status': text_extraction_status,
                        'text_extraction_error': text_extraction_error,
                        'text_length': text_length
                    })

                # Only consider this successful if we actually got meaningful content
                if not scraping_successful:
                    logger.warning(f"DIAGNOSTIC: Scraping returned empty/whitespace content for {url} - PID: {process_id}")
                    return []

            except Exception as scraping_error:
                # Handle scraping errors - return empty list to preserve original behavior
                logger.error(f"DIAGNOSTIC: Scraping failed for {url} - PID: {process_id}: {type(scraping_error).__name__}: {scraping_error}")

                # Update text extraction metrics for failed scraping
                text_extraction_status = False
                text_extraction_error = str(scraping_error)
                text_length = 0
                
                # Log the failed text extraction to pipeline logger
                if self.pipeline_logger:
                    logging_context.update({
                        'text_extraction_status': text_extraction_status,
                        'text_extraction_error': text_extraction_error,
                        'text_length': text_length
                    })
                    
                    # Create dummy LLM metrics since no LLM processing occurred
                    dummy_llm_metrics = {
                        'llm_response_status': False,
                        'llm_response_error': 'Text extraction failed - no LLM processing attempted',
                        'llm_processing_time': 0
                    }
                    
                    self._complete_logging_cycle_for_url(logging_context, dummy_llm_metrics)
                
                return []
            
            # Step 3: Process all prompts against the cached content
            successful_responses = 0
            total_llm_processing_time = 0
            last_llm_error = None
            
            for i, prompt in enumerate(prompts):
                # DIAGNOSTIC: Log each prompt processing
                logger.info(f"DIAGNOSTIC: Processing prompt {i+1}/{len(prompts)} for URL {url} - PID: {process_id}")
                ai_parser.prompt = prompt
                
                try:
                    # Get LLM response using cached content (no scraping)
                    response_content, llm_metrics = ai_parser.get_api_response()
                    
                    # Accumulate LLM metrics
                    if llm_metrics:
                        total_llm_processing_time += llm_metrics.get('llm_processing_time', 0)
                        if llm_metrics.get('llm_response_status'):
                            successful_responses += 1
                        else:
                            last_llm_error = llm_metrics.get('llm_response_error', 'Unknown LLM error')
                    
                    if response_content is None:
                        logger.error(f"DIAGNOSTIC: No response content from API for prompt {i+1} - PID: {process_id}")
                        responses.append(None)
                        continue
                    
                    # Process the response (same as original select_article_to_api logic)
                    stripped = ai_parser.strip_markdown(response_content)
                    data = json.loads(stripped)
                    
                    # Format response with URL key (same as original include_url=True behavior)
                    tagged_data = {url: data}
                    responses.append(tagged_data)
                    
                except json.JSONDecodeError as e:
                    logger.error(f"DIAGNOSTIC: JSONDecodeError for prompt {i+1} - PID: {process_id}: {e}")
                    responses.append(None)
                    last_llm_error = f"JSONDecodeError: {str(e)}"
                except Exception as e:
                    logger.error(f"DIAGNOSTIC: Unexpected error for prompt {i+1} - PID: {process_id}: {e}")
                    responses.append(None)
                    last_llm_error = str(e)
                
            # Log overall processing results to pipeline logger
            if self.pipeline_logger:
                # Determine overall LLM success
                llm_response_status = successful_responses > 0
                llm_response_error = "None" if llm_response_status else (last_llm_error or "All LLM processing failed")
                
                combined_llm_metrics = {
                    'llm_response_status': llm_response_status,
                    'llm_response_error': llm_response_error,
                    'llm_processing_time': total_llm_processing_time
                }
                
                self._complete_logging_cycle_for_url(logging_context, combined_llm_metrics)
        
        finally:
            # Ensure cleanup always happens, even if initialization or processing fails
            try:
                await ai_parser.cleanup()
                logger.debug(f"DIAGNOSTIC: Cleaned up resources for {url} - PID: {process_id}")
            except Exception as cleanup_error:
                # Log cleanup errors but don't let them mask original errors
                logger.error(f"DIAGNOSTIC: Error during cleanup for {url} - PID: {process_id}: {cleanup_error}")
                # Don't re-raise cleanup errors - they shouldn't mask the original processing errors
            
        # DIAGNOSTIC: Log completion
        logger.info(f"DIAGNOSTIC: Completed get_responses_for_url for {url}, got {len(responses)} responses - PID: {process_id}")
        return responses

    def _complete_logging_cycle_for_url(self, logging_context, llm_metrics):
        """Complete the logging cycle by writing to CSV with all collected metrics for get_responses_for_url."""
        if not self.pipeline_logger:
            return
            
        # Calculate total response time
        text_extraction_time = time.perf_counter() - logging_context['text_extraction_start_time']
        llm_processing_time = llm_metrics.get('llm_processing_time', 0)
        total_response_time_ms = int((text_extraction_time + llm_processing_time) * 1000)
        
        # Generate current timestamp
        current_timestamp = datetime.now().astimezone().isoformat()
        
        # Convert status values to strings and handle None errors - matching existing log format
        text_extraction_status_str = "True" if logging_context['text_extraction_status'] else "False"
        text_extraction_error_str = logging_context['text_extraction_error'] if logging_context['text_extraction_error'] else "None"
        
        llm_response_status_str = "True" if llm_metrics['llm_response_status'] else "False"
        llm_response_error_str = llm_metrics['llm_response_error'] if llm_metrics['llm_response_error'] else "None"
        
        # Log to CSV using the exact same format as existing pipeline logs
        self.pipeline_logger.log_url_processing(
            url=logging_context['url'],
            project_name=logging_context['project_name'],
            timestamp=current_timestamp,
            text_extraction_status=text_extraction_status_str,
            text_extraction_error=text_extraction_error_str,
            text_length=logging_context['text_length'],
            llm_response_status=llm_response_status_str,
            llm_response_error=llm_response_error_str,
            response_time_ms=total_response_time_ms
        )
    
    @staticmethod
    def extract_urls(text):
        url_pattern = re.compile(r'(https?://\S+)')
        try: 
            urls = url_pattern.findall(text)
        # Deal with NaN values 
        except TypeError:
            return None 
        return urls if urls else None


    async def get_all_url_responses(self) -> dict:
        urls = [url for url in self.url_df.apply(self.extract_urls).dropna()]
        responses = []

        for url in tqdm(urls, desc="Getting responses for URLs"):
            response = await self.get_responses_for_url(url[0])
            if response:
                responses.append(response)
            else:
                logger.warning(f"No response for URL: {url[0]}")
    
        return responses
    # ORIGINAL PROBLEMATIC IMPLEMENTATION (DO NOT USE):
    # This concurrent approach caused race conditions on HPC systems:
    #async def get_all_url_responses(self) -> dict:
    #    urls = [url for url in self.url_df.apply(self.extract_urls).dropna()]
    #    responses = [await self.get_responses_for_url(url[0]) for url in tqdm(urls, desc="Getting responses for URLs")]
    #    return responses
    # ISSUE: List comprehension with await creates all tasks simultaneously,
    # causing browser instance conflicts and resource contention on multi-core systems


    def flatten_dict(self, input_dict)->list:
        """Make url into just one k:v pair alongside others"""
        if input_dict is None:
            logger.warning("Encountered None input in flatten_dict")
            return {}
        
        # Extract the single URL and its associated data
        url, attributes = next(iter(input_dict.items()))
        
        # Check if we have nested project data (LLM returned project names as keys)
        if all(isinstance(v, dict) for v in attributes.values() if v is not None) and len(attributes) > 0:
            logger.info(f"FLATTEN_DICT: Detected nested project structure, extracting data for {self.project_name}")
            
            # Find any project that matches our expected name and extract its data
            expected_name = self.project_name.lower()
            project_data = None
            
            for project_name, data in attributes.items():
                if isinstance(data, dict) and expected_name in project_name.lower():
                    logger.info(f"FLATTEN_DICT: Found matching project '{project_name}', extracting data")
                    project_data = data
                    break
            
            if project_data:
                # Use the project data but with our standardized project name
                flattened_dict = {k: v for k, v in project_data.items()}
                flattened_dict['project_name'] = self.project_name  # Use input project name, not LLM's version
                logger.info(f"FLATTEN_DICT: Using standardized project name: {self.project_name}")
            else:
                # No matching project found
                flattened_dict = {}
                logger.warning(f"FLATTEN_DICT: No matching project found for {self.project_name}")
        else:
            # Normal flat structure (original behavior)
            flattened_dict = {k: v for k, v in attributes.items()}
            # Ensure we always have a consistent project_name field
            if 'project_name' not in flattened_dict:
                flattened_dict['project_name'] = self.project_name
        
        flattened_dict['url'] = url
        return flattened_dict
    
    
    @staticmethod
    def custom_agg(series):
        non_null_values = series.dropna().unique().tolist()
        return non_null_values if non_null_values else [None]


    def log_value_types(self, df):
        for col in df.columns:
            for i, val in enumerate(df[col]):
                print(f"Row {i}, Column '{col}': Value '{val}', Type {type(val)}")

    def clean_strings(self, series):
        def process_string(x):
            if isinstance(x, (float, type(None))):
                return ""
            if isinstance(x, list):
                elements = [str(i).strip() for i in x if str(i).strip().lower() not in ['nan', 'none', '']]
            else:
                elements = str(x).split(',')
                filtered_elements = [i.strip() for i in elements if i.strip().lower() not in ['nan', 'none', '']]
            return ', '.join(sorted(set(filtered_elements)))

        return series.apply(process_string)
    

    def aggregate_data(self, group):
        result = {}
        for column in group.columns:
            if column != 'url':  # Skip the 'url' column
                unique_values = group[column].dropna().unique()
                if len(unique_values) == 1:
                    result[column] = unique_values[0]
                elif len(unique_values) > 1:
                    result[column] = list(unique_values)
                else:
                    result[column] = None
        return pd.Series(result)

    async def consolidate_responses(self) -> pd.DataFrame:
        data = await self.get_all_url_responses()
        logger.info("Data received: %s", data)

        for element in data:
            if element is None:
                logger.error("Encoutnered None element in data")
                continue

        try:
            # data has a list of lists
                # outermost list is each url 
                    # 2nd level list is the queries for each url
                        # 2d level is all dicts of dicts
                        # outer dict key is the url
                            # Inner dict has keys for all query cols
            # Replace line 465 with:
            rows = [self.flatten_dict(query_response) 
                    for url_responses in data 
                    for query_response in url_responses 
                    if query_response is not None]

            #rows = [self.flatten_dict(queries) for element in data for queries in element]
        except TypeError:
            logger.error("TypeError occurred during flattening")
            breakpoint()

        df = pd.DataFrame(rows)
        logger.info(f"DataFrame created. Shape: {df.shape}")  # Add this line
        logger.info(f"DataFrame columns: {df.columns}")  # Add this line
        logger.info(f"DataFrame dtypes: {df.dtypes}")  # Add this line
        df['name'] = self.project_name
        df['url'] = df['url'].astype(str)
        try:
            for col in df.columns:
                df[col] = df[col].astype(str)
                #df[col] = df[col].apply(lambda x: str(x) if isinstance(x,(list,dict)) else x)
            grouped_df = df.groupby('url', as_index=False).apply(self.aggregate_data)
            # Write to csv to normalize data or else remove nan fails
            grouped_df.to_csv("temp.csv")
            df_csv = pd.read_csv("temp.csv")
            output_df = df_csv.map(remove_nan)
        except Exception as e:
            logger.error(f"error is {e}")
            logger.error("Dataframe at time of error:")
            logger.error(df.head())
        return output_df 
    
