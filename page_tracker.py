import newspaper
import openai
import numpy as np
import os, sys
import time
import json
import re

from newspaper import Source
from pathlib import Path

# Set the path of the cache
# Requires setting of API key 
class AiParser:

    def __init__(self, 
                 publication_url:str, 
                 api_key:str,
                 api_url:str,
                 model:str,
                 prompt:Path
                 ) -> None:
        # Set the path of the 
        current_script_dir = Path(__file__).parent
        memo_dir = Path(current_script_dir, 'memoized')
        newspaper.settings.MEMO_DIR = memo_dir
        self.publication = Source(publication_url)
        self.publication.build() 
        self.model = model
        self.prompt_path = prompt
        # Get api key 
        api_key = os.environ.get(api_key)
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=api_url
        )
        

    def get_articles_urls(self) -> list:
        """Get all the articles"""
        breakpoint()
        article_urls = [x for x in self.publication.articles]

        return article_urls
    
    
    def get_api_response(self,fulltext:str):
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.0,
            messages=[
                {
                    "role":"user",
                    "content": f"{self.prompt}{fulltext} "
                }
            ]
        )
        return response 
   

    def strip_markdown(self, text):
        return re.sub(r'^```json(.*)```', r'\1', text, flags=re.DOTALL)


    def select_article_to_api(self, url:str, avg_pause=2):
        """
        Download, parse, and submit one article from a url
        """
        # Download an article
         
        a = newspaper.Article(url)
        a.download()
        # Parse the text 
        a.parse()
        breakpoint()
        fulltext = f"{a.title}.\n\n{a.text}"
        # Run the text through the AI api, return formated text 
        response = self.get_api_response(fulltext)
        stripped = self.strip_markdown(response.choices[0].message.content)
        data = json.loads(stripped)
        pause = np.random(avg_pause, avg_pause/2)
        time.sleep(pause)
        return data  

    
    def articles_parser(self,
                        urls: list,
                        max_limit: int = None) -> list:
        if max_limit is None:
            max_limit = len(urls)
        data = [self.select_article_to_api(x) for x in urls[:max_limit]]
        breakpoint()
        return data
    

    

pv_mag = 'https://pv-magazine-usa.com/category/installations/commercial-industrial-pv/'

