import asyncio
import aiofiles
import os

from multi_project_validator import MultiProjectValidator
from pathlib import Path


async def create_directory(directory_path):
    await aiofiles.os.makedirs(directory_path, exist_ok=True)


async def main():
    excel_path = "/Users/TYFong/Desktop/worklogs/project_logs/ai_parser/Solar_Project_Tracker_ITexamples_2022.xlsx"
    api_key = os.environ.get('CYCLOGPT_API_KEY')
    api_url = "https://api.cborg.lbl.gov"
    model = 'lbl/llama-3'
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

if __name__ == "__main__":
    asyncio.run(main())