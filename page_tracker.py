import newspaper
import openai
import newspaper as news
import numpy as np
import concurrent.futures
import os, sys
import pandas as pd
import re
import time
import json
import re

from newspaper import Article, Source
from pathlib import Path
from tqdm import tqdm

# Set the path of the cache
# Requires setting of API key 
class AiParser:

    def __init__(self, 
                 api_key:str,
                 api_url:str,
                 model:str,
                 prompt:str,
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
        self.prompt_path = prompt
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
    
    @staticmethod 
    def get_api_response(self,fulltext:str):
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.0,
            messages=[
                {
                    "role":"user",
                    "content": f"{self.prompt_path}{fulltext} "
                }
            ]
        )
        return response 
   

    @staticmethod
    def strip_markdown(self, text):
        return re.sub(r'^```json(.*)```', r'\1', text, flags=re.DOTALL)


    @staticmethod
    def select_article_to_api(self, url:str, include_url:True, avg_pause=1,):
        """
        Download, parse, and submit one article from a url
        """
        # Download an article
        try:
            a = newspaper.Article(url)
        # Catch exceptions when there is a boolean in the urls
        except AttributeError:
            return
        a.download()
        # Parse the text 
        a.parse()
        fulltext = f"{a.title}.\n\n{a.text}"
        # Run the text through the AI api, return formated text 
        response = self.get_api_response(fulltext)
        stripped = self.strip_markdown(response.choices[0].message.content)
        # Error handling when the article does not mention solar projects
        try:
            data = json.loads(stripped)
        except json.decoder.JSONDecodeError:
            # Should I have error logging here??
            return
        # Error handling when there is no article at the link
        try:
            if include_url:
                tagged_data = {url:data[0]}
            else:
                tagged_data = {data[0]}
        except IndexError:
            return
        pause = np.random.normal(avg_pause, avg_pause/2)
        time.sleep(pause)
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
                 url_df: pd.df ,
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
        prompt_filenames = [Path(self.prompt_dir,f'{self.prompt_file_base}{x}') 
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
                               prompt=prompt
                               )
            article_data = ai_parser.select_article_to_api(url)
            responses.append(article_data)
        return responses 
    
    @staticmethod
    def extract_urls(text):
        url_pattern = re.compile(r'(https?://\S+)')
        urls = url_pattern.findall(text)
        return urls if urls else None


    def get_all_url_responses(self)->dict:
        """Get all responses for urls for project"""
        # for the column of urls, get an array of URLs
        urls = [url for url in self.url_df.apply(self.extract_urls).dropna()]
        # feed each url to the api
        responses = [self.get_responses_for_url(url) for url
                     in urls]
        return responses 


    def consolidate_responses(self)->pd.df:
        """Put together all responses for one project name"""
        responses = self.get_all_url_responses()
        all_data = [
            {**project, "project_name": self.project_name}
            for response_list in responses for response in response_list if response
            for projects in response.values() for project in projects
        ]

        final_df = pd.DataFrame(all_data) if all_data else pd.DataFrame()
        return final_df
        # Make a pandas dataframe that has as the project name as 
        # a column with the rest of the column headers made up of the json keys
        return final_df
