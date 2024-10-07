import argparse
import asyncio
import aiofiles
import logging
import os
import pandas as pd
import pickle
import tracemalloc
import shutil
import sys
import traceback
from contextlib import asynccontextmanager

from datetime import datetime
from multi_project_validator import MultiProjectValidator
from pathlib import Path

tracemalloc.start()
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler('log_file.log'),
        logging.StreamHandler()
    ]
                    )


async def create_directory(directory_path):
    dir_path = Path(directory_path)
    dir_path.mkdir(parents=True, exist_ok=True)

def save_pickle(file_path):
    with open(file_path, 'rb') as file:
        dataframes_dict = pickle.load(file)
        # Concatenate dataframes, including all columns and filling missing values with NaN
        concatenated_df = pd.concat(dataframes_dict.values(), ignore_index=True, sort=False)
        concatenated_df = concatenated_df.drop('Unnamed: 0', axis=1)
        now = datetime.now()
        datetime_str = now.strftime('%Y-%m-%d-%H%M')
        csv_name = f"readout_{datetime_str}.csv"
        output_dir = Path(__file__).resolve().parent / 'results'
        output_file_path = Path(output_dir,csv_name)
        # Write to CSV
        concatenated_df.to_csv(output_file_path, index=False)
        termination_message = f"Wrote data to {output_file_path}"
        print(termination_message)

async def async_save_pickle(file_path, save_complete_event):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, save_pickle, file_path)
    save_complete_event.set()  # Signal that saving is complete

async def cleanup_checkpoint(checkpoint_path, keep_checkpoint, cleanup_event):
    await cleanup_event.wait()  # Wait for the signal that it's safe to cleanup
    if not keep_checkpoint and os.path.exists(checkpoint_path):
        os.remove(checkpoint_path)
        logging.info(f"Checkpoint file {checkpoint_path} has been deleted.")
    elif keep_checkpoint:
        logging.info(f"Checkpoint file {checkpoint_path} has been kept.")

@asynccontextmanager
async def manage_checkpoint(checkpoint_path, keep_checkpoint):
    save_complete_event = asyncio.Event()
    cleanup_event = asyncio.Event()
    cleanup_task = asyncio.create_task(cleanup_checkpoint(checkpoint_path, keep_checkpoint, cleanup_event))
    try:
        yield save_complete_event, cleanup_event
    finally:
        cleanup_event.set()
        await cleanup_task

async def main():
    parser = argparse.ArgumentParser(description="Run multi-project validation")
    parser.add_argument('--keep-checkpoint', action='store_true', help='Keep the checkpoint file after completion')
    args = parser.parse_args()

    logging.info("Test log message")
    print("test message")
    excel_path = "/Users/TYFong/Desktop/worklogs/project_logs/ai_parser/Solar_Project_Tracker_ITexamples_2022.xlsx"
    api_key = os.environ.get('CYCLOGPT_API_KEY')
    api_url = "https://api.cborg.lbl.gov"
    model = 'lbl/cborg-chat:latest'
    prompt_directory = Path(__file__).resolve().parent / 'test_prompts'
    output_dir = Path(__file__).resolve().parent / 'results'
    checkpoint_dir = Path(__file__).resolve().parent / 'checkpoints'
    checkpoint_filename = 'checkpoint.pkl'
    await create_directory(prompt_directory)
    await create_directory(output_dir)
    await create_directory(checkpoint_dir)

    checkpoint_path = Path(checkpoint_dir, checkpoint_filename)

    multi_validator = MultiProjectValidator(
        excel_path=excel_path,
        api_key=api_key,
        api_url=api_url,
        model=model,
        prompt_directory=prompt_directory,
        checkpoint_dir=checkpoint_dir
    )

    async with manage_checkpoint(checkpoint_path, args.keep_checkpoint) as (save_complete_event, cleanup_event):
        try:
            await multi_validator.run(output_dir)
            # Wait for the writing to complete
            await multi_validator.writing_complete.wait()
            # Now safe to call save_pickle
            await async_save_pickle(checkpoint_path, save_complete_event)
            # Wait for save_pickle to complete
            await save_complete_event.wait()
        except Exception as e:
            logging.error(f"An error occurred during main execution: {e}")
            logging.error(traceback.format_exc())
            # Don't set cleanup_event, so checkpoint won't be deleted
            return 1  # Indicate error

    logging.info("Main process completed successfully.")
    return 0  # Indicate successful completion

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        logging.error(traceback.format_exc())
        logging.info("Checkpoint preserved for potential resume.")
        sys.exit(1)  # Exit with a non-zero status code
    finally:
        logging.info("Script execution finished.")
        tracemalloc.stop()  # Stop tracemalloc
        # Perform any final cleanup or resource release here if needed
        # For example, you might want to close any open file handles or network connections