import json
import os
import  pandas as pd
import requests

token = os.environ.get('KAGI_API_KEY')
if not token:
    raise ValueError("TOKEN environment variable not set")

project_name = "Atrisco Solar LLC" #"Grassfield Solar"

state = "New Mexico" #"VA"
state_abb = 'NM'

# query = f"""{project_name} {project_state} capacity "ac" mw """
# query = f"""{project_name} {project_state} ("dc" mw OR "MWdc")"""
query = f'{project_name} ({state} OR {state_abb}) (power purchase agreement OR "ppa" OR offtake)'

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
# breakpoint()
query_col_data = [query] * len(df.index)
df.insert(0,"query",query_col_data)
# Get rid of the related search row
df_cleaned = df.dropna(subset=['url'])

file_name = f'./kagi_test/results/test_kagi_output_{project_name}.csv'
if os.path.exists(file_name):
    df_old = pd.read_csv(file_name)
    pd.concat([df_old, df_cleaned]).to_csv(file_name)
else:
    df_cleaned.to_csv(file_name)

print(f'Output to {file_name}')