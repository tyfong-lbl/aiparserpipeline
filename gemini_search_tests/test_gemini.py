import openai 
import os 

client = openai.OpenAI(
    api_key=os.environ.get('CBORG_API_KEY'), # Please do not store your API key in the code
    base_url="https://api.cborg.lbl.gov" # Local clients can also use https://api-local.cborg.lbl.gov
)

model = "google/gemini-pro"

test_prompt = """Context: https://www.ehn.org/massive-solar-project-moves-forward-at-contaminated-nuclear-site-2671295736.html
                 Question: I would like to find more articles like the one regarding Hanford's solar project. The page should have details about the size of the project in megawatts, cost, and so on. Only get pages that describe specific projects.
"""

response = client.chat.completions.create(
    model=model,
    temperature=0.0,
    messages = [{
        "role": "user",
        "content": test_prompt 
    }]
)
try:
    print(f"""Model: {model}\nResponse: {response.choices[0].message.content}""")
except:
    print(f"Error calling model {model}")