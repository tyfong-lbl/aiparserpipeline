import os 

from page_tracker import AiParser
from pathlib import Path


pv_mag = 'https://pv-magazine-usa.com/category/installations/commercial-industrial-pv/'
with open('solar-projects-prompt-2.txt', 'r') as file:
    prompt = file.read()

api_key = os.environ.get('CYCLOGPT_API_KEY')
api_url = "https://api.cyclogpt.lbl.gov"
model = 'lbl/cyclogpt:chat-v1'

tool = AiParser(publication_url=pv_mag,
                api_key=api_key,
                api_url=api_url,
                model=model,
                prompt=prompt)

articles = tool.get_articles_urls()

data = tool.articles_parser(urls=articles,
                            max_limit=10)

breakpoint()




