import newspaper
import newspaper.settings
import numpy as np
import os, sys
import time
import json
import re

from newspaper import Source
from pathlib import Path

# Set the path of the cache
current_script_dir = Path(__file__).parent
newspaper.settings.MEMO_DIR = current_script_dir

class AiParser:

    def __init__(self, publication_url) -> None:
        self.publication = Source(publication_url)
        self.publication.build() 



    def get_articles_urls(self):
        article_urls = [x for x in self.publication.articles]
        return article_urls




    
breakpoint()

pv_mag = 'https://pv-magazine-usa.com/category/installations/commercial-industrial-pv/'

