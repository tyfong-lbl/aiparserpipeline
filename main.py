import asyncio
import os

from multi_project_validator import MultiProjectValidator
from pathlib import Path


async def main():
    scratch_path = Path("/global/scratch/users/tyfong")
    excel_path = os.environ.get('ENERGY_GROUNDTRUTH') 
    api_key = os.environ.get('CYCLOGPT_API_KEY')
    api_url = "https://api.cborg.lbl.gov"
    model = 'lbl/llama-3'
    prompt_directory = Path(__file__).resolve().parent / 'test_prompts'
    output_dir = Path(__file__).resolve().parent / 'results'
    checkpoint_dir = Path(__file__).resolve().parent / 'checkpoints'

    checkpoint_dir.mkdir(exist_ok=True)

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
