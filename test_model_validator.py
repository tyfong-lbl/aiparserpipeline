import asyncio
import pandas as pd
import os
from model_validator import ModelValidator 

from pathlib import Path
# Note that you must be on the lab VPN for this to work. 
api_key = os.environ.get('CYCLOGPT_API_KEY')
api_url = "https://api.cborg.lbl.gov"

model = 'lbl/llama-3'


variables = { 
    "PROJECT": "Slate Hybrid"
}
# Get ground truth
gt_file_path = os.environ.get('ENERGY_GROUNDTRUTH')
# Read in both sheets
gt_df = pd.read_excel(gt_file_path, sheet_name=None)

url_df = gt_df['urls']

project_name = 'Slate Hybrid'
current_directory = Path(__file__).resolve().parent
prompt_directory = Path(current_directory,'test_prompts')
async def main():
    project_name = 'example_project'
    model_validator = ModelValidator(number_of_queries=5,
                                 prompt_dir_path=prompt_directory,
                                 prompt_filename_base='solar-projects-priority-prompt',
                                 api_key=api_key,
                                 api_url=api_url,
                                 model=model,
                                 project_name=project_name,
                                 url_df=url_df)
    # Mock the async function get_all_url_responses
    async def mock_get_all_url_responses():
        # Provide mock data as needed
        return [
            [{'url': 'http://example.com', 'response': '{"key": "value"}'}],
            [{'url': 'http://example.com', 'response': '{"key2": "value2"}'}]
        ]
    
    # Assign the mock function to the instance
    model_validator.get_all_url_responses = mock_get_all_url_responses
   
    # Mock the flatten_dict function
    model_validator.flatten_dict = lambda x: x  # Replace with actual flatten_dict logic
    
    # Run the consolidate_responses method and print the resulting DataFrame
    df = await model_validator.consolidate_responses()
    print(df)

if __name__ == "__main__":
    asyncio.run(main())
