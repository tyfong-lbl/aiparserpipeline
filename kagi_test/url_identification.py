import json
import os
import pandas as pd
import numpy as np
import requests
import re
from datetime import datetime
from joblib import Parallel, delayed
from tqdm import tqdm

STATEabb_to_name = {
        'AK': 'Alaska',
        'AL': 'Alabama',
        'AR': 'Arkansas',
        'AZ': 'Arizona',
        'CA': 'California',
        'CO': 'Colorado',
        'CT': 'Connecticut',
        'DC': 'District of Columbia',
        'DE': 'Delaware',
        'FL': 'Florida',
        'GA': 'Georgia',
        'HI': 'Hawaii',
        'IA': 'Iowa',
        'ID': 'Idaho',
        'IL': 'Illinois',
        'IN': 'Indiana',
        'KS': 'Kansas',
        'KY': 'Kentucky',
        'LA': 'Louisiana',
        'MA': 'Massachusetts',
        'MD': 'Maryland',
        'ME': 'Maine',
        'MI': 'Michigan',
        'MN': 'Minnesota',
        'MO': 'Missouri',
        'MS': 'Mississippi',
        'MT': 'Montana',
        'NC': 'North Carolina',
        'ND': 'North Dakota',
        'NE': 'Nebraska',
        'NH': 'New Hampshire',
        'NJ': 'New Jersey',
        'NM': 'New Mexico',
        'NV': 'Nevada',
        'NY': 'New York',
        'OH': 'Ohio',
        'OK': 'Oklahoma',
        'OR': 'Oregon',
        'PA': 'Pennsylvania',
        'RI': 'Rhode Island',
        'SC': 'South Carolina',
        'SD': 'South Dakota',
        'TN': 'Tennessee',
        'TX': 'Texas',
        'UT': 'Utah',
        'VA': 'Virginia',
        'VT': 'Vermont',
        'WA': 'Washington',
        'WI': 'Wisconsin',
        'WV': 'West Virginia',
        'WY': 'Wyoming',
        'PR': 'Puerto Rico',
        'VI': 'Virigin Islands'
    }

def main():
    project_csv_path = "G:\\Shared drives\\USS\\Automation\\2024_project_list.csv"
    # query_list_path = "C:\\Users\JMulvaneyKemp\Documents\\repos\AI_parser_pipeline_github\\aiparserpipeline\kagi_test\\test_queries.txt"
    query_list_path = ".\\kagi_test\\test_queries.txt" #"C:\\Users\\JMulvaneyKemp\\Documents\\repos\\AI_parser_pipeline_github\\aiparserpipeline\\kagi_test\\test_queries.txt"
    apikey = os.environ.get('KAGI_API_KEY')
    projects = pd.read_csv(project_csv_path)
    with open(query_list_path) as f:
        queries = f.read().splitlines()
    #standardize to lower case
    projects.columns = projects.columns.str.lower()
    if len(projects.state[0])==2:
        projects.rename(columns={'state':'state_abb'}, inplace=True)
        projects['state'] = projects.state_abb.replace(STATEabb_to_name)
    queries = [str.lower(i) for i in queries]
    
    #Execute web queries
    df = request_all_queries(projects, queries, par_njobs=1, verbose=False, token=apikey, checkpt_ix=4300)

    #Save results
    datetime_str = datetime.now().strftime('%Y-%m-%d-%H%M')
    df.to_csv(f".\\kagi_test\\results\\urlID_output_{datetime_str}.csv")

def request_all_queries(projectdf, query_template_list, par_njobs=1,verbose=False, url='https://kagi.com/api/v0/search', token=os.environ.get('KAGI_API_KEY'), checkpt_ix=0):
    df = generate_formatted_queries(projectdf, query_template_list)
    if par_njobs>1:
        raise Exception("Don't recommend current parallel functionality due to lack of saving checkpoints")
        # idx=tqdm(df.index.to_list())
        # # response_dfs = Parallel(n_jobs=par_njobs, return_as='list')(
        # #                         delayed(dummy_api_query)(df.loc[i,'formatted_query']) for i in idx
        # #                     )
        # response_dfs = Parallel(n_jobs=par_njobs, return_as='list')(
        #     delayed(api_query_single)(df.loc[i,'formatted_query'], verbose, url, token) for i in idx
        # )
        # responses_concat = pd.concat([response_dfs[i][0] for i in range(len(response_dfs))])
        # responses_concat.to_csv("url_id_raw_responses.csv")
        # df = df.merge(responses_concat, how='left', on='formatted_query', validate='1:m')
    else:
        responses = []
        if checkpt_ix>0:
            checkpt_df = pd.read_csv(".\\kagi_test\\results\\responses_checkpoint_"+str(checkpt_ix)+".csv", index_col=0)
        for i in df.index.difference(range(checkpt_ix)):
            responses = responses + [api_query_single(df.loc[i,'formatted_query'], verbose, url, token)[0]]#[dummy_api_query(df.loc[i,'formatted_query'])]
            if (i % 100 ==0) & (i>0):
                if checkpt_ix>0:
                    pd.concat([checkpt_df, pd.concat(responses)]).to_csv(".\\kagi_test\\results\\responses_checkpoint_"+str(i)+".csv")
                else:
                    pd.concat(responses).to_csv(".\\kagi_test\\results\\responses_checkpoint_"+str(i)+".csv")
            # responses = pd.concat([api_query_single(df.loc[i,'formatted_query'], verbose, url, token)[0] for i in df.index])
        df = df.merge(pd.concat([checkpt_df, pd.concat(responses)]), how='left', on='formatted_query', validate='1:m')
    return df

def generate_formatted_queries(projects, queries):
    # Regular expression to find placeholders in the format strings
    pattern = r'\{([\w\s]+)\}'
    # Set to store unique column names
    column_names = set()
    # Iterate over each format string
    for fmt in queries:
        # Find all matches of the pattern in the format string
        matches = re.findall(pattern, fmt)
        # Add matches to the set of column names
        column_names.update(matches)
    if len(column_names - set(projects.columns.values))>0:
        print(column_names - set(projects.columns.values))
        raise Exception("queries require data fields not in projects dataframe column names")
    else:
        df = pd.DataFrame(index=pd.MultiIndex.from_arrays([projects[i] for i in column_names], names=column_names), 
                          columns=pd.Index(queries, name='query'), 
                          data='')
        df = df.stack().reset_index()
        df['formatted_query'] = df.apply(lambda row: row['query'].format(**row), axis=1)

    return df

def api_query_single(query, verbose=False, url='https://kagi.com/api/v0/search', token=os.environ.get('KAGI_API_KEY')):
    headers = {
        'Authorization': f'Bot {token}'
    }
    params = {
        'q': f'{query}'  # Search query parameter
    }
    try:
        # Make the API request
        response = requests.get(url, headers=headers, params=params)
        if verbose:
            # Print response details (optional)
            print(query)
            print(f'Status code: {response.status_code}')
            # print('Response content:')
            # print(response.text)

        data = json.loads(response.text)
        df = pd.DataFrame(data['data'])
        df.insert(0,"formatted_query",[query] * len(df.index))
    except Exception as err:
        print(f"{query} resulted in unexpected error: {err}")
        df = pd.DataFrame({'formatted_query':query, 'url':err, 'title':"API REQUEST FAILED", 'snippet':"API REQUEST FAILED"})
    # Get rid of the related search row
    if "url" in df.columns:
        df_cleaned = df.dropna(subset=['url'])
    else: 
        df_cleaned=df
    return df_cleaned, response.status_code

def dummy_api_query(query):
    df = pd.DataFrame({'formatted_query':query, 'url':np.arange(10), 'title':np.arange(10), 'snippet':np.arange(10), 'published':np.arange(10)})
    return df#, 'success'

# def accumulator_update(df, generator):
#     for val in generator:
#         df.update(val, overwrite=False)
#     return df

if __name__ == "__main__":
    main()