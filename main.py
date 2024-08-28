import asyncio
import aiofiles
import logging
import os
import pandas as pd
import pickle

from datetime import datetime
from multi_project_validator import MultiProjectValidator
from pathlib import Path

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler('log_file.log'),
        logging.StreamHandler()
    ]
                    )


async def create_directory(directory_path):
    dir_path = Path(directory_path)
    dir_path.mkdir(parents=True, exist_ok=True)

async def main():
    logging.info("Test log message")
    print("test message")
    excel_path = "/Users/TYFong/Desktop/worklogs/project_logs/ai_parser/solar_project_tests.xlsx"
    api_key = os.environ.get('CYCLOGPT_API_KEY')
    api_url = "https://api.cborg.lbl.gov"
    model = 'lbl/cborg-chat:latest'
    prompt_directory = Path(__file__).resolve().parent / 'test_prompts'
    output_dir = Path(__file__).resolve().parent / 'results'
    checkpoint_dir = Path(__file__).resolve().parent / 'checkpoints'
    await create_directory(prompt_directory)
    await create_directory(output_dir)
    await create_directory(checkpoint_dir)

    multi_validator = MultiProjectValidator(
        excel_path=excel_path,
        api_key=api_key,
        api_url=api_url,
        model=model,
        prompt_directory=prompt_directory,
        checkpoint_dir=checkpoint_dir
    )

    await multi_validator.run(output_dir)

def save_pickle(filename):
    pickle_dir = Path(__file__).resolve().parent / 'checkpoints'
    file_path = Path(pickle_dir,filename)
    with open(file_path, 'rb') as file:
        dataframes_dict = pickle.load(file)
        # Concatenate dataframes, including all columns and filling missing values with NaN
        concatenated_df = pd.concat(dataframes_dict.values(), ignore_index=True, sort=False)
        now = datetime.now()
        datetime_str = now.strftime('%Y-%m-%d-%H%M')
        csv_name = f"readout_{datetime_str}.csv"
        output_dir = Path(__file__).resolve().parent / 'results'
        output_file_path = Path(output_dir,csv_name)
        # Write to CSV
        concatenated_df.to_csv(output_file_path, index=False)
        termination_message = f"Wrote data to {output_file_path}"
        print(termination_message)

if __name__ == "__main__":
    asyncio.run(main())
    save_pickle('checkpoint.pkl')
