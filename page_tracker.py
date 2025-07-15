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

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

    async def initialize(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch()

    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
      
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
    
    def get_api_response(self, fulltext:str):
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
            text_extraction_status = True
            text_extraction_error = None
            
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

    @staticmethod
    def articles_parser(self, urls: list, include_url=True, max_limit: int = None) -> list:
        if max_limit is None:
            max_limit = len(urls)
        data = [result for result in (self.select_article_to_api(url,include_url) for url in tqdm(urls[:max_limit], desc="Parsing articles")) if result is not None]
        return data
    
    async def cleanup(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
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
        For a particular URL, get all the responses to prompts
        """
        prompts = self.get_all_prompts()
        responses = []
        ai_parser = AiParser(api_key=self.api_key,
                             api_url=self.api_url,
                             model=self.model,
                             prompt=prompts[0],
                             project_name=self.project_name,
                             pipeline_logger=self.pipeline_logger)
        try:
            await ai_parser.initialize()
            for prompt in prompts:
                ai_parser.prompt = prompt
                article_data = await ai_parser.select_article_to_api(url=url, 
                                                                 include_url=True,
                                                                 avg_pause=1)
                responses.append(article_data)
        
        finally:
            await ai_parser.cleanup()
        return responses
    
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
    #async def get_all_url_responses(self) -> dict:
    #    urls = [url for url in self.url_df.apply(self.extract_urls).dropna()]
    #    responses = [await self.get_responses_for_url(url[0]) for url in tqdm(urls, desc="Getting responses for URLs")]
    #    return responses


    def flatten_dict(self, input_dict)->list:
        """Make url into just one k:v pair alongside others"""
        if input_dict is None:
            logger.warning("Encountered None input in flatten_dict")
            return {}
        # Extract the single URL and its associated data
        url, attributes = next(iter(input_dict.items()))
        # Flatten
        flattened_dict = {k:v for k, v in attributes.items()}
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
    
