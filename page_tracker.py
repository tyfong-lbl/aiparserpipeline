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
from pathlib import Path
from string import Template
from tqdm import tqdm
from playwright.async_api import async_playwright 

from typing import Any, List

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
                 publication_url=None
                 ) -> None:
        self.model = model
        self.prompt = prompt,
        self.project_name = project_name
        self.api_key = api_key
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=api_url
        )
        self.publication_url = publication_url
        self.playwright = None 
        self.browser = None 

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
            return response.choices[0].message.content if response.choices else None
        except Exception as e:
            logger.error(f"Error in API call: {e}")
            return None


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
        try:
            page = await self.browser.new_page()
            await page.goto(url)
            title = await page.title()
            text = await page.evaluate('() => document.body.innerText')
            await page.close()
        except Exception as e:
            logger.error(f"Error fetching article: {e}")
            return None

        fulltext = f"{title}.\n\n{text}"
    
        try:
            response_content = self.get_api_response(fulltext=fulltext)
            if response_content is None:
                logger.error("No response content from API")
                return None
            stripped = self.strip_markdown(response_content)
            data = json.loads(stripped)
        except json.JSONDecodeError as e:
            logger.error(f"JSONDecodeError encountered: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during API response handling: {e}")
            return None

        tagged_data = {url: data} if include_url else data

        if avg_pause > 0:
            pause = abs(np.random.normal(avg_pause, avg_pause/2))
            await asyncio.sleep(pause)

        return tagged_data


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

                 ) -> None:
        self.number_of_queries = number_of_queries
        self.prompt_file_base = prompt_filename_base
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.parser = parser
        self.prompt_dir = prompt_dir_path
        self.project_name = project_name
        self.url_df = url_df[self.project_name]
    
    
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
                             project_name=self.project_name)
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

    async def preprocess_data(self, data) -> pd.DataFrame:
        try:
            flatten_data = [self.flatten_dict(queries) for element in data for queries in element]
        except TypeError:
            logger = logging.getLogger(__name__)
            logger.error("TypeError occurred during flattening")
            breakpoint()
            
        df = pd.DataFrame(flatten_data)
        logger.info("DataFrame created. Shape: %s", df.shape)
        logger.info("DataFrame columns: %s", df.columns)
        logger.info("DataFrame dtypes: %s", df.dtypes)
    
        return df

    @staticmethod
    def clean_and_validate_json(element: str) -> str:
        try:
            parsed = json.loads(element)
            if isinstance(parsed, list):
                cleaned_list = list({json.dumps(item) for item in parsed if item and str(item).lower() not in ['nan', 'none', '']})
                return json.dumps([json.loads(item) for item in cleaned_list])
            elif isinstance(parsed, dict):
                cleaned_dict = {k: v for k, v in parsed.items() if v and str(v).lower() not in ['nan', 'none', '']}
                return json.dumps(cleaned_dict)
        except (json.JSONDecodeError, TypeError):
            return None

    @staticmethod
    def process_element(element: str) -> str:
        if element is None or (isinstance(element, str) and element.lower() in ['nan', 'none', '']):
            return None
        
        valid_json = ModelValidator.clean_and_validate_json(element)
        if valid_json is not None:
            return valid_json
        
        elements = str(element).split(',')
        filtered_elements = [i.strip() for i in elements if i.strip().lower() not in ['nan', 'none', '']]
        return ', '.join(sorted(set(filtered_elements)))

    @staticmethod
    def clean_strings(series: pd.Series) -> pd.Series:
        return series.apply(ModelValidator.process_element)
    
    @staticmethod
    def json_group_concat(json_strings: List[str]) -> str:
        aggregated = []
        for value in json_strings:
            if not value:
                continue
            try:
                value_json = json.loads(value)
                if isinstance(value_json, list):
                    aggregated.extend(value_json)
                else:
                    aggregated.append(value_json)
            except (json.JSONDecodeError, TypeError):
                pass
        return json.dumps(list({json.dumps(item) for item in aggregated}))

    @staticmethod
    def setup_custom_aggregator(connection: sqlite3.Connection):
        connection.create_aggregate("json_group_concat", 1, ModelValidator.json_group_concat)
    
    async def preprocess_data(self, data: List[Any]) -> pd.DataFrame:
        try:
            flatten_data = [self.flatten_dict(queries) for element in data for queries in element]
        except TypeError:
            logger = logging.getLogger(__name__)
            logger.error("TypeError occurred during flattening")
            breakpoint()
            
        df = pd.DataFrame(flatten_data)
        logger = logging.getLogger(__name__)
        logger.info("DataFrame created. Shape: %s", df.shape)
        logger.info("DataFrame columns: %s", df.columns)
        logger.info("DataFrame dtypes: %s", df.dtypes)
        return df

    @staticmethod
    def convert_types(df: pd.DataFrame) -> pd.DataFrame:
        df['url'] = df['url'].astype(str)
        for col in df.select_dtypes(include=['object']):
            df[col] = df[col].astype(str)
        logger = logging.getLogger(__name__)
        logger.info("DataFrame after type conversions: %s", df.dtypes)
        return df

    def setup_database(self, df: pd.DataFrame) -> pd.DataFrame:
        conn = sqlite3.connect(':memory:')
        self.setup_custom_aggregator(conn)
        
        try:
            df.to_sql('responses', conn, index=False, if_exists='replace')
            
            group_concat_cols = [f"json_group_concat({col}) as {col}" for col in df.columns if col != 'url']
            group_concat_query = ", ".join(group_concat_cols)
            
            query = f"""
            SELECT url, {group_concat_query}
            FROM responses
            GROUP BY url
            """
    
            grouped_df = pd.read_sql_query(query, conn)
        finally:
            conn.close()
            
        return grouped_df

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        df.replace({pd.NA: None, 'nan': None, 'none': None, '': None}, inplace=True)
        for column in df.select_dtypes(include=['object']):
            df[column] = self.clean_strings(df[column])
        return df

    
