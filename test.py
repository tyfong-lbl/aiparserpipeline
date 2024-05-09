import openai
import newspaper
import os, sys
import json
import re

# read the prompt template
with open('solar-projects-prompt-2.txt', 'r') as file:
    prompt = file.read()

# fetch and parse a newspaper article
# pip install newspaper3k for this module
# https://newspaper.readthedocs.io/en/latest/
from newspaper import Article
url = "https://pv-magazine-usa.com/2022/01/06/construction-begins-on-100-mw-50-mwh-solar-storage-project-in-california/"
a = Article(url)
a.download()
a.parse()
fulltext = a.title + ".\n\n" + a.text
api_key = os.environ.get('CYCLOGPT_API_KEY')
client = openai.OpenAI(
    api_key=api_key,
    base_url="https://api.cyclogpt.lbl.gov"
)

try:
    response = client.chat.completions.create(
        #model="openai/gpt-3.5-turbo",
        model="lbl/cyclogpt:chat-v1",
        temperature=0.0,
        messages = [
            {
                "role": "user",
                "content": prompt + fulltext
            }
        ]
    )
except Exception as e:
    print(f"An error occurred: {str(e)}")

def strip_markdown(text):
    return re.sub(r'^```json(.*)```', r'\1', text, flags=re.DOTALL)

data = json.loads(strip_markdown(response.choices[0].message.content))
breakpoint()

print(json.dumps(data, indent=4))

