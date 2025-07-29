import json

import os 

from google import genai
from google.genai.types import Tool, GenerateContentConfig, GoogleSearch
from pathlib import Path
from pprint import pprint, pformat

current_file_path = Path(__file__).resolve().parents[0]

api_key=os.environ.get('EMA_GOOGLE_API') # Please do not store your API key in the code
client = genai.Client(api_key=api_key)

model = "gemini-2.0-flash"

google_search_tool = Tool(google_search=GoogleSearch())

test_prompt = """
                You are an analyst that conducts solar energy project research.
You have access to Google Search to look up news about solar energy projects from the last three months. You are trying to find out about NEW solar energy projects that have been annouced or started building. 

                 Question: Search the web for articles posted in the last three months about specific solar energy projects in the USA and return direct links to the articles, and NOT to pages that LINK to the articles. ONLY GET REAL EXISTING ARTICLES. The links MUST go to the SPECIFIC article. 
                 Format: Return the data in a json format with the title of the article, url, and description as keys. 
"""
output_file_path = Path(current_file_path, "gemini_test_chunks.txt") 
with output_file_path.open('w') as file: 
    file.write(test_prompt)
    file.write('\n')

response = client.models.generate_content(
    model=model,
    contents=test_prompt,
    config=GenerateContentConfig(
        tools=[google_search_tool],
        response_modalities=["TEXT"]
        )
)

d = response.model_dump_json()
grounding_chunks = json.loads(d)['candidates'][0]['grounding_metadata']['grounding_chunks']
formatted_chunks = pformat(grounding_chunks)

try:
    with output_file_path.open('a') as file:
        file.write(formatted_chunks)

    print('Wrote results to file')
except:
    print(f"Error calling model {model}")
