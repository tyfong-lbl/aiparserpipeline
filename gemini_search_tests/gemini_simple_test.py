from google import genai
import os

api_key=os.environ.get('EMA_GOOGLE_API') # Please do not store your API key in the code
client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents="Explain how AI works",
)

print(response.text)
