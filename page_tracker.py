import newspaper
import openai
import newspaper as news
import numpy as np
import os, sys
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
                 publication_url:str, 
                 api_key:str,
                 api_url:str,
                 model:str,
                 prompt:str,
                 memoized=False
                 ) -> None:
        # Set the path of the 
        current_script_dir = Path(__file__).parent
        memo_dir = Path(current_script_dir, 'memoized')
        newspaper.settings.MEMO_DIR = memo_dir
        #self.publication = Source(publication_url)
        #self.publication.build() 
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
   

    def strip_markdown(self, text):
        return re.sub(r'^```json(.*)```', r'\1', text, flags=re.DOTALL)


    def select_article_to_api(self, url:str, avg_pause=1):
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
            tagged_data = {url:data[0]}
        except IndexError:
            return
        pause = np.random.normal(avg_pause, avg_pause/2)
        time.sleep(pause)
        return tagged_data

    
    def articles_parser(self,
                        urls: list,
                        max_limit: int = None) -> list:
        if max_limit is None:
            max_limit = len(urls)
        data = [result for result in (self.select_article_to_api(url) for url in tqdm(urls[:max_limit], desc="Parsing articles")) if result is not None]
        #with tqdm(total=max_limit, 
        #          desc="Parsing articles",
        #          ) as pbar:
            #data = [result for result in ((pbar.update(1) or 
            #        self.select_article_to_api(x)) for x in urls[:max_limit]) 
            #        if result is not None or True]
        return data
    

    


