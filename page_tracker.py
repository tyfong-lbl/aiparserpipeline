import newspaper
import numpy as np
import os, sys
import json
import re

from newspaper import Source
from pathlib import Path

pv_mag = Source('https://pv-magazine-usa.com/category/installations/commercial-industrial-pv/')
pv_mag.build()

# Get a list of articles
article_urls = [* pv_mag.articles]
# Get only 10 articles
article_urls = article_urls[0:10]

def mass_download(urls):
    # Download a list of articles 
    rv = np.random.normal(2,1)
    for url in urls:
        url.download
    
breakpoint()


