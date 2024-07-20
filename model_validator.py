import asyncio 
import os
import pandas as pd
import re

from datetime import datetime
from page_tracker import ModelValidator 
from pathlib import Path
from string import Template 

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
    model_validator = ModelValidator(number_of_queries=5,
                                 prompt_dir_path=prompt_directory,
                                 prompt_filename_base='solar-projects-priority-prompt',
                                 api_key=api_key,
                                 api_url=api_url,
                                 model=model,
                                 project_name=project_name,
                                 url_df=url_df)

    df = await model_validator.consolidate_responses()
    now = datetime.now()
    datetime_str = now.strftime('%Y-%m-%d-%H%M')
    # Maybe edit the output name to show the model name!
    # Edit the model name to remove the slash
    p = Path(model)
    stripped_path = p.relative_to("lbl")
    model_name = str(stripped_path)
    csv_name = f"test_readout_{model_name}_{datetime_str}.csv"
    df.to_csv(csv_name)


if __name__=="__main__":
    asyncio.run(main())







