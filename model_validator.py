import os
import pandas as pd
import re

from page_tracker import AiParser
from pathlib import Path
from string import Template 

api_key = os.environ.get('CYCLOGPT_API_KEY')
api_url = "https://api.cyclogpt.lbl.gov"
model = 'lbl/cyclogpt:chat-v1'

prompt_filename = 'test_prompts/solar-projects-prompt-2.txt'
with open(prompt_filename, 'r') as file:
    content = file.read()

variables = { 
    "PROJECT": "Slate Hybrid"
}
template = Template(content)

modified_query = template.substitute(variables)

# Get ground truth
gt_file_path = os.environ.get('ENERGY_GROUNDTRUTH')
# Read in both sheets
gt_df = pd.read_excel(gt_file_path, sheet_name=None)

url_df = gt_df['urls']

project_name = 'Slate Hybrid'
urls_column = url_df[project_name]
urls_column = urls_column.dropna()

def extract_urls(text):
    url_pattern = re.compile(r'(https?://\S+)')
    urls = url_pattern.findall(text)
    return urls if urls else None


urls_list = [url for urls in urls_column.apply(extract_urls).dropna() for url in urls]
breakpoint()








