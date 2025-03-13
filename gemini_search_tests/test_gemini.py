from google import genai
from google.genai.types import Tool, GenerateContentConfig, GoogleSearch
import os 

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

response = client.models.generate_content(
    model=model,
    contents=test_prompt,
    config=GenerateContentConfig(
        tools=[google_search_tool],
        response_modalities=["TEXT"]
        )
)
try:
    print(response.text)
except:
    print(f"Error calling model {model}")
