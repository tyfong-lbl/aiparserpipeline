import os
import pandas as pd
import re

from page_tracker import ModelValidator 
from pathlib import Path
from string import Template 


# Note that you must be on the lab VPN for this to work. 
api_key = os.environ.get('CYCLOGPT_API_KEY')
api_url = "https://api.cyclogpt.lbl.gov"
model = 'lbl/cyclogpt:chat-v1'


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

model_validator = ModelValidator(number_of_queries=5,
                                 prompt_dir_path=prompt_directory,
                                 prompt_filename_base='solar-projects-priority-prompt',
                                 api_key=api_key,
                                 api_url=api_url,
                                 model=model,
                                 project_name=project_name,
                                 url_df=url_df)

df = model_validator.consolidate_responses()
breakpoint()






