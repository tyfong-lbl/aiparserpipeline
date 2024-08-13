import asyncio
import json
import logging
import os

from datetime import datetime
from pathlib import Path
import pandas as pd
from page_tracker import ModelValidator, AiParser

class MultiProjectValidator:
    def __init__(self, 
                 excel_path: str,
                 api_key: str,
                 api_url: str,
                 model: str,
                 prompt_directory: Path,
                 number_of_queries: int = 5,
                 prompt_filename_base: str = 'solar-projects-priority-prompt'):
        self.excel_path = excel_path
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.prompt_directory = prompt_directory
        self.number_of_queries = number_of_queries
        self.prompt_filename_base = prompt_filename_base
        
        self.url_df = None
        self.project_names = None
        self.common_params = None
        
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        self._load_excel_data()
        self._setup_common_params()

    def _load_excel_data(self):
        """Load data from Excel file and extract project names."""
        try:
            gt_df = pd.read_excel(self.excel_path, sheet_name=None)
            self.url_df = gt_df['urls']
            self.project_names = self.url_df['Project Name'].unique()
            self.logger.info(f"Loaded {len(self.project_names)} projects from Excel file.")
        except Exception as e:
            self.logger.error(f"Error loading Excel file: {e}")
            raise

    def _setup_common_params(self):
        """Set up common parameters for ModelValidator instances."""
        self.common_params = {
            'number_of_queries': self.number_of_queries,
            'prompt_dir_path': self.prompt_directory,
            'prompt_filename_base': self.prompt_filename_base,
            'api_key': self.api_key,
            'api_url': self.api_url,
            'model': self.model
        }

    def _get_checkpoint_path(self):
        return self.checkpoint_dir / "checkpoint.json"

    def _save_checkpoint(self):
        """Save the current state to a checkpoint file."""
        checkpoint_data = {
            "completed_projects": list(self.completed_projects)
        }
        with open(self._get_checkpoint_path(), 'w') as f:
            json.dump(checkpoint_data, f)
        self.logger.info(f"Checkpoint saved. Completed projects: {len(self.completed_projects)}")

    def _load_checkpoint(self):
        """Load the state from a checkpoint file if it exists."""
        checkpoint_path = self._get_checkpoint_path()
        if checkpoint_path.exists():
            with open(checkpoint_path, 'r') as f:
                checkpoint_data = json.load(f)
            self.completed_projects = set(checkpoint_data.get("completed_projects", []))
            self.logger.info(f"Checkpoint loaded. Resuming with {len(self.completed_projects)} completed projects.")
        else:
            self.logger.info("No checkpoint found. Starting from the beginning.")

    async def process_project(self, project_name: str) -> pd.DataFrame:
        """Process a single project."""
        if project_name in self.completed_projects:
            self.logger.info(f"Skipping already completed project: {project_name}")
            return pd.DataFrame()

        self.logger.info(f"Processing project: {project_name}")
        project_urls = self.url_df[self.url_df['Project Name'] == project_name]
        
        model_validator = ModelValidator(
            **self.common_params,
            project_name=project_name,
            url_df=project_urls
        )
        
        try:
            df = await model_validator.consolidate_responses()
            self.logger.info(f"Successfully processed project: {project_name}")
            self.completed_projects.add(project_name)
            self._save_checkpoint()
            return df
        except Exception as e:
            self.logger.error(f"Error processing project {project_name}: {e}")
            return pd.DataFrame()  # Return empty DataFrame on error

    async def process_all_projects(self) -> pd.DataFrame:
        """Process all projects concurrently."""
        self.logger.info("Starting to process all projects.")
        remaining_projects = [p for p in self.project_names if p not in self.completed_projects]
        tasks = [self.process_project(project_name) for project_name in remaining_projects]
        results = await asyncio.gather(*tasks)
        
        all_results = pd.concat(results, ignore_index=True)
        self.logger.info(f"Finished processing all projects. Total rows: {len(all_results)}")
        return all_results

    async def run(self, output_dir: Path):
        """Main method to run the entire process."""
        self.logger.info("Starting multi-project validation process.")
        results = await self.process_all_projects()
        self.save_results(results, output_dir)
        self.logger.info("Multi-project validation process completed.")
        # Clean up checkpoint after successful completion
        os.remove(self._get_checkpoint_path())
        self.logger.info("Checkpoint file removed after successful completion.")