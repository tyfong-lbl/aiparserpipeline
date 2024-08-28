import asyncio
import json
import logging
import os
import pickle
import traceback

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
                 checkpoint_dir: Path,
                 number_of_queries: int = 5,
                 prompt_filename_base: str = 'solar-projects-priority-prompt'):
        self.excel_path = excel_path
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.prompt_directory = prompt_directory
        self.checkpoint_dir = Path(checkpoint_dir)
        if self.checkpoint_dir is None:
            raise ValueError("checkpoint_dir cannot be None")
        self.number_of_queries = number_of_queries
        self.prompt_filename_base = prompt_filename_base
        
        self.url_df = None
        self.project_names = None
        self.common_params = None
        self.completed_projects = set()
        
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.project_outputs = {}

        self._load_excel_data()
        self._setup_common_params()
        self._load_checkpoint()

    def _load_excel_data(self):
        """Load data from Excel file and extract project names."""
        try:
            gt_df = pd.read_excel(self.excel_path, sheet_name="Sheet1")
            self.url_df = gt_df
            self.project_names = self.url_df.columns.unique()
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
        return self.checkpoint_dir / "checkpoint.pkl"

    def _save_checkpoint(self):
        """Save the current state to a checkpoint file."""
        self.checkpoint_dir = Path(self.checkpoint_dir)
        if self.checkpoint_dir is None:
            self.logger.error("checkpoint_dir is None, cannot save checkpoint")
        self.checkpoint_dir.mkdir(exist_ok=True)
        with open(self._get_checkpoint_path(), 'wb') as f:
            pickle.dump(self.project_outputs, f)
        self.logger.info(f"Checkpoint saved. Completed projects: {len(self.completed_projects)}")

    async def _load_checkpoint(self):
        """Load the state from a checkpoint file if it exists."""
        checkpoint_path = self._get_checkpoint_path()
        if checkpoint_path.exists():
            with open(checkpoint_path, 'rb') as f:
                self.project_outputs= pickle.load(f)
            self.completed_projects = set(self.project_outputs.keys())
            self.logger.info(f"Checkpoint loaded. Resuming with {len(self.completed_projects)} completed projects")
        else:
            self.logger.info("No checkpoint found. Starting from the beginning.")

    async def process_project(self, project_name: str) -> pd.DataFrame:
        """Process a single project."""
        try:
            if project_name in self.completed_projects:
                self.logger.info(f"Skipping already completed project: {project_name}")
                return pd.DataFrame()

            self.logger.info(f"Processing project: {project_name}")
            project_urls = self.url_df[project_name]
            
            model_validator = ModelValidator(
                **self.common_params,
                project_name=project_name,
                url_df=project_urls
            )
            
            try:
                df = await model_validator.consolidate_responses()
                self.project_outputs[project_name] = df
                self.logger.info(f"Successfully processed project: {project_name}")
                self.completed_projects.add(project_name)
                self.logger.info("About to save checkpoint...")
                try:
                    await asyncio.to_thread(self._save_checkpoint())
                except TypeError as e:
                    print(e)
                self.logger.info("Checkpoint saved")
                return df
            except Exception as e:
                import traceback
                self.logger.error(f"Error processing project {project_name}: {e}")
                self.logger.error(traceback.format_exc())
                return pd.DataFrame()  # Return empty DataFrame on error
        except Exception as e:
            self.logger.error(f"Unexpected error processing project {project_name}: {e}")
            self.logger.error(traceback.format_exc())
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


    async def save_results(self, results, output_dir):
        now = datetime.now()
        datetime_str = now.strftime('%Y-%m-%d-%H%M')
        # Edit the model name to remove the slash
        p = Path(self.model)
        stripped_path = p.relative_to("lbl")
        model_name = str(stripped_path)
        csv_name = f"readout_{model_name}_{datetime_str}.csv"
        output_path = Path(output_dir,csv_name)
        results.to_csv(output_path)

    async def run(self, output_dir: Path):
        """Main method to run the entire process."""
        self.logger.info("Starting multi-project validation process.")
        await self._load_checkpoint()
        results = await self.process_all_projects()
        await self.save_results(results, output_dir)
        self.logger.info("Multi-project validation process completed.")
        # Clean up checkpoint after successful completion
        #checkpoint_path = self._get_checkpoint_path()
        #if checkpoint_path.exists():
        #    os.remove(checkpoint_path)