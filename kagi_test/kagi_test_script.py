import json
import os
import  pandas as pd
import requests

token = os.environ.get('KAGI_API_KEY')
if not token:
    raise ValueError("TOKEN environment variable not set")

project_name = "Grassfield Solar"

project_state = "VA"

query = f"""{project_name} {project_state} capacity 'ac' mw """

# Define request parameters
url = 'https://kagi.com/api/v0/search'
headers = {
    'Authorization': f'Bot {token}'
}
params = {
    'q': f'{query}'  # Search query parameter
}

# Make the API request
response = requests.get(url, headers=headers, params=params)

# Print response details (optional)
print(f'Status code: {response.status_code}')
print('Response content:')
print(response.text)

data = json.loads(response.text)
df = pd.DataFrame(data['data'])
breakpoint()
query_col_data = [query] * len(df.index)
df.insert(0,"query",query_col_data)
# Get rid of the related search row
df_cleaned = df.dropna(subset=['url'])

file_name = 'test_kagi_output.xlsx'

df.to_excel(file_name)

print(f'Output to {file_name}')