import newspaper
import openai
import newspaper as news
import numpy as np
import concurrent.futures
import logging
import pandas as pd
import re
import sqlite3
import time
import json
import re


from pathlib import Path
from ratelimit import limits, sleep_and_retry
from string import Template
from tqdm import tqdm


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set the path of the cache
# Requires setting of API key 
class AiParser:

    def __init__(self, 
                 api_key:str,
                 api_url:str,
                 model:str,
                 prompt:str,
                 project_name:str,
                 memoized=False,
                 publication_url=None
                 ) -> None:
        # Set the path of the 
        current_script_dir = Path(__file__).parent
        memo_dir = Path(current_script_dir, 'memoized')
        newspaper.settings.MEMO_DIR = memo_dir
        if publication_url: 
            self.publication = news.build(url=publication_url,
                                      memoize_articles=memoized)
        self.model = model
        self.prompt = prompt,
        self.project_name = project_name
        # Get api key 
        self.api_key = api_key
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=api_url
        )
        

    def get_articles_urls(self) -> list:
        """Get all the articles"""
        # What are these objects? 
        article_urls = [article.url for article in self.publication.articles]
        return article_urls

    @sleep_and_retry
    @limits(calls=10, period=60)
    def get_api_response(self, fulltext:str):
        #breakpointe)
        values = {"PROJECT":self.project_name}
        template = Template(self.prompt[0])
        prompt_for_submission = template.substitute(values)
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.0,
            messages=[
                {
                    "role":"user",
                    "content": f"{prompt_for_submission}{fulltext} "
                }
            ]
        )
        return response 
   

    @staticmethod
    def strip_markdown(text):
        json_pattern = re.search(r'{.*}', text, re.DOTALL)
        json_str = json_pattern.group(0).strip() 
        #stripped_markdown = re.sub(r'^```json(.*)```', r'\1', text, flags=re.DOTALL)
        return json_str

    @sleep_and_retry
    @limits(calls=5, period=60)
    def select_article_to_api(self, url:str, include_url:True, avg_pause=0,):
        """
        Download, parse, and submit one article from a url
        """
        # Download an article
        try:
            a = newspaper.Article(url)
            a.download()
            # Parse the text 
            a.parse()
        except AttributeError as e:
            logger.error(f"AttributeError encountered: {e}")
            return None
        except newspaper.article.ArticleException as e:
            logger.error(f"ArticleException encountered: {e}")
            return None
        except Exception as e: 
            logger.error(f"Unexpected error: {e}")
            
        fulltext = f"{a.title}.\n\n{a.text}"
        #breakpoint()
        try:
            # Run the text through the AI api, return formated text 
            response = self.get_api_response(fulltext=fulltext)
            stripped = self.strip_markdown(response.choices[0].message.content)
            # Error handling when the article does not mention solar projects
            data = json.loads(stripped)
        except json.decoder.JSONDecodeError as e:
            logger.error(f"JSONDecodeError encountered: {e}")
            breakpoint()
            return None
        except Exception as e:
            logger.error(f"Unexpected error during API response handling: {e}")
            return None
        # Error handling when there is no article at the link
        try:
            if include_url:
                tagged_data = {url:data}
            else:
                tagged_data = data
        except IndexError as e:
            logger.error(f"IndexError encountered: {e}")
            return None
        if avg_pause > 0:
            pause = abs(np.random.normal(avg_pause, avg_pause/2))
            time.sleep(pause)
            return tagged_data
        else:
            return tagged_data

    
    @staticmethod
    def articles_parser(self,
                        urls: list,
                        include_url=True,
                        max_limit: int = None) -> list:
        if max_limit is None:
            max_limit = len(urls)
        data = [result for result in (self.select_article_to_api(url,include_url) for url in tqdm(urls[:max_limit], desc="Parsing articles")) if result is not None]
        return data
    
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
    

    def get_responses_for_url(self,url)->list:
        """
        For a particular URL, get all the responses to prompts
        """
        prompts = self.get_all_prompts()
        responses = []
        # Hit the url with each prompt in turn
        for prompt in prompts:
            ai_parser = AiParser(api_key=self.api_key,
                               api_url=self.api_url, 
                               model=self.model,
                               prompt=prompt,
                               project_name=self.project_name,
                               )
            article_data = ai_parser.select_article_to_api(url=url, 
                                                           include_url=True,
                                                           avg_pause=1
                                                           )
            responses.append(article_data)
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


    def get_all_url_responses(self)->dict:
        """Get all responses for urls for project"""
        # for the column of urls, get an array of URLs
        urls = [url for url in self.url_df.apply(self.extract_urls).dropna()]
        # feed each url to the api
        responses = [self.get_responses_for_url(url[0]) for url in tqdm(urls, desc="Getting responses for URLs")]
        return responses 


    def flatten_dict(self, input_dict)->list:
        """Make url into just one k:v pair alongside others"""
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


    def consolidate_responses(self)->pd.DataFrame:
        """Put together all responses for one project name"""
        data = self.get_all_url_responses()
        try:
            # data has a list of lists
                # outermost list is each url 
                    # 2nd level list is the queries for each url
                        # 2d level is all dicts of dicts
                        # outer dict key is the url
                            # Inner dict has keys for all query cols
            rows = [self.flatten_dict(queries) for element in data for queries in element]
        except TypeError:
            breakpoint()

        df = pd.DataFrame(rows)
        df.name = self.project_name
        df['url'] = df['url'].astype(str)
        breakpoint()
        try:
            conn = sqlite3.connect(':memory:')
            df.to_sql('responses', conn, index=False, if_exists='replace')

            query = """
            SELECT url,
                   GROUP_CONCAT(owner) as owner,
                   GROUP_CONCAT(offtaker) as offtaker,
                   GROUP_CONCAT(storage_energy) as storage_energy,
                   GROUP_CONCAT(storage_power) as storage_power
            FROM responses
            GROUP BY url
            """

            grouped_df = pd.read_sql_query(query, conn)

            for col in ['owner', 'offtaker', 'storage_energy', 'storage_power']:
                grouped_df[col] = grouped_df[col].apply(lambda x: x.split(',') if x else [None])

            conn.close()
        except TypeError as e:
            print(f"error is {e}")
            breakpoint()

        return grouped_df 

