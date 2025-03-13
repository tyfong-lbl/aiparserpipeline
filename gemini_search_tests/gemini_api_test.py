import sys
print(sys.path)
import os
from google import genai

from google.genai.types import (
    GenerateContentConfig,
    GoogleSearch,
    HttpOptions,
    Tool,
)

api_key = os.getenv("EMA_GOOGLE_KEY")
client = genai.Client(http_options=HttpOptions(api_version="v1",api_key=api_key))

response = client.models.generate_content(
    model="gemini-2.0-flash-001",
    contents="When is the next total solar eclipse in the United States?",
    config=GenerateContentConfig(
        tools=[
            # Use Google Search Tool
            Tool(google_search=GoogleSearch())
        ],
    ),
)

print(response.text)
# Example response:
# 'The next total solar eclipse in the United States will occur on ...'
