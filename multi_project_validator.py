import asyncio
import json
import logging
import os
import pickle
import traceback
import fcntl
import time

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
                 prompt_filename_base: str = 'solar-projects-priority-prompt',
                 logger=None):
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
        self.pipeline_logger = logger
        
        self.url_df = None
        self.project_names = None
        self.common_params = None
        self.completed_projects = set()
        
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Ensure diagnostic logging goes to a specific file
        if not self.logger.handlers:
            diagnostic_handler = logging.FileHandler('diagnostic_output.log')
            diagnostic_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            diagnostic_handler.setFormatter(diagnostic_formatter)
            self.logger.addHandler(diagnostic_handler)
            # Also add console output
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(diagnostic_formatter)
            self.logger.addHandler(console_handler)
        self.project_outputs = {}

        self._load_excel_data()
        self._setup_common_params()
        
        # Add process lock to prevent race conditions
        self.lock_file_path = self.checkpoint_dir / "process.lock"
        self.lock_file = None
        
        self._load_checkpoint()

        self.writing_complete = asyncio.Event()
        self.initiatlization_complete = asyncio.Event()

    async def initialize(self):
        self._load_checkpoint()
        self.initiatlization_complete.set()

    def _load_excel_data(self):
        """Load data from Excel file and extract project names."""
        try:
            gt_df = pd.read_excel(self.excel_path, sheet_name="urls")
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
    
    def _acquire_process_lock(self):
        """Acquire a file lock to prevent multiple processes from running simultaneously."""
        import os
        pid = os.getpid()
        
        # Check for stale lock file first
        if self.lock_file_path.exists():
            try:
                with open(self.lock_file_path, 'r') as f:
                    existing_pid = f.readline().strip()
                    existing_time = float(f.readline().strip())
                
                # Check if the process is still running
                try:
                    os.kill(int(existing_pid), 0)  # Signal 0 just checks existence
                    age = time.time() - existing_time
                    self.logger.info(f"PROCESS_LOCK: Active lock found - PID: {existing_pid}, Age: {age:.1f}s")
                except (OSError, ValueError):
                    # Process no longer exists, remove stale lock
                    self.lock_file_path.unlink()
                    self.logger.info(f"PROCESS_LOCK: Removed stale lock from PID: {existing_pid}")
            except Exception as e:
                self.logger.warning(f"PROCESS_LOCK: Error checking existing lock: {e}")
        
        try:
            self.checkpoint_dir.mkdir(exist_ok=True)
            self.lock_file = open(self.lock_file_path, 'w')
            
            # Try to acquire exclusive lock (non-blocking)
            fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            # Write PID to lock file for debugging
            self.lock_file.write(f"{pid}\n{time.time()}\n")
            self.lock_file.flush()
            
            self.logger.info(f"PROCESS_LOCK: Acquired lock - PID: {pid}")
            return True
            
        except (IOError, OSError) as e:
            if self.lock_file:
                self.lock_file.close()
                self.lock_file = None
            
            # Try to read existing lock info
            try:
                with open(self.lock_file_path, 'r') as f:
                    existing_pid = f.readline().strip()
                    existing_time = f.readline().strip()
                self.logger.warning(f"PROCESS_LOCK: Failed to acquire lock - PID: {pid}, Existing PID: {existing_pid}, Time: {existing_time}")
            except:
                self.logger.warning(f"PROCESS_LOCK: Failed to acquire lock - PID: {pid}, Error: {e}")
            
            return False
    
    def _release_process_lock(self):
        """Release the process lock."""
        if self.lock_file:
            try:
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                self.lock_file.close()
                self.lock_file = None
                
                # Remove lock file
                if self.lock_file_path.exists():
                    self.lock_file_path.unlink()
                
                pid = os.getpid()
                self.logger.info(f"PROCESS_LOCK: Released lock - PID: {pid}")
            except Exception as e:
                self.logger.error(f"PROCESS_LOCK: Error releasing lock: {e}")

    async def _save_checkpoint(self):
        """Save the current state to a checkpoint file."""
        self.checkpoint_dir = Path(self.checkpoint_dir)
        if self.checkpoint_dir is None:
            self.logger.error("checkpoint_dir is None, cannot save checkpoint")
        self.checkpoint_dir.mkdir(exist_ok=True)
        with open(self._get_checkpoint_path(), 'wb') as f:
            await asyncio.to_thread(pickle.dump, self.project_outputs, f)
        self.logger.info(f"Checkpoint saved. Completed projects: {len(self.completed_projects)}")

    def _load_checkpoint(self):
        """Load the state from a checkpoint file if it exists."""
        import os
        pid = os.getpid()
        checkpoint_path = self._get_checkpoint_path()
        
        self.logger.info(f"CHECKPOINT_LOAD: Checking for checkpoint at {checkpoint_path} - PID: {pid}")
        
        if checkpoint_path.exists():
            try:
                # Add file stats for debugging
                stat_info = checkpoint_path.stat()
                self.logger.info(f"CHECKPOINT_LOAD: Found checkpoint file, size: {stat_info.st_size}, mtime: {stat_info.st_mtime} - PID: {pid}")
                
                with open(checkpoint_path, 'rb') as f:
                    self.project_outputs = pickle.load(f)
                self.completed_projects = set(self.project_outputs.keys())
                self.logger.info(f"CHECKPOINT_LOAD: Loaded checkpoint with {len(self.completed_projects)} completed projects: {list(self.completed_projects)} - PID: {pid}")
            except Exception as e:
                self.logger.error(f"CHECKPOINT_LOAD: Error loading checkpoint - PID: {pid}, Error: {e}")
                self.project_outputs = {}
                self.completed_projects = set()
        else:
            self.logger.info(f"CHECKPOINT_LOAD: No checkpoint found. Starting from the beginning - PID: {pid}")
            self.project_outputs = {}
            self.completed_projects = set()

    async def process_project(self, project_name: str) -> pd.DataFrame:
        """Process a single project."""
        import os
        process_id = os.getpid()
        task_id = id(asyncio.current_task())
        
        # DIAGNOSTIC: Log process and task information
        self.logger.info(f"DIAGNOSTIC: Starting process_project for {project_name} - PID: {process_id}, Task ID: {task_id}")
        
        try:
            if project_name in self.completed_projects:
                self.logger.info(f"DIAGNOSTIC: Skipping already completed project: {project_name} - PID: {process_id}")
                return pd.DataFrame()

            self.logger.info(f"DIAGNOSTIC: Processing project: {project_name} - PID: {process_id}, Task ID: {task_id}")
            project_urls = self.url_df[project_name]
            
            # DIAGNOSTIC: Log URL count for this project
            url_count = len(project_urls.dropna())
            self.logger.info(f"DIAGNOSTIC: Project {project_name} has {url_count} URLs to process - PID: {process_id}")
            
            model_validator = ModelValidator(
                **self.common_params,
                project_name=project_name,
                url_df=project_urls,
                pipeline_logger=self.pipeline_logger
            )
            
            try:
                self.logger.info(f"DIAGNOSTIC: About to call consolidate_responses for {project_name} - PID: {process_id}")
                df = await model_validator.consolidate_responses()
                self.logger.info(f"DIAGNOSTIC: consolidate_responses completed for {project_name}, got {len(df)} rows - PID: {process_id}")
                
                self.project_outputs[project_name] = df
                self.logger.info(f"Successfully processed project: {project_name}")
                self.completed_projects.add(project_name)
                self.logger.info(f"DIAGNOSTIC: About to save checkpoint for {project_name} - PID: {process_id}")
                try:
                    await self._save_checkpoint()
                except TypeError as e:
                    print(e)
                self.logger.info(f"DIAGNOSTIC: Checkpoint saved for {project_name} - PID: {process_id}")
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
        import os
        process_id = os.getpid()
        
        self.logger.info(f"DIAGNOSTIC: Starting to process all projects - PID: {process_id}")
        remaining_projects = [p for p in self.project_names if p not in self.completed_projects]
        
        # DIAGNOSTIC: Log project counts and details
        self.logger.info(f"DIAGNOSTIC: Total projects: {len(self.project_names)}, Completed: {len(self.completed_projects)}, Remaining: {len(remaining_projects)} - PID: {process_id}")
        self.logger.info(f"DIAGNOSTIC: Remaining projects: {remaining_projects} - PID: {process_id}")
        self.logger.info(f"DIAGNOSTIC: Completed projects: {list(self.completed_projects)} - PID: {process_id}")
        
        if not remaining_projects:
            self.logger.info("All projects have already been processed. No new data to concatenate.")
            return pd.DataFrame()  # Return an empty DataFrame instead of trying to concatenate

        # DIAGNOSTIC: Log task creation
        self.logger.info(f"DIAGNOSTIC: Creating {len(remaining_projects)} async tasks - PID: {process_id}")
        tasks = [self.process_project(project_name) for project_name in remaining_projects]
        
        # DIAGNOSTIC: Log task IDs
        task_ids = [id(task) for task in tasks]
        self.logger.info(f"DIAGNOSTIC: Created task IDs: {task_ids} - PID: {process_id}")
        
        self.logger.info(f"DIAGNOSTIC: About to call asyncio.gather with {len(tasks)} tasks - PID: {process_id}")
        results = await asyncio.gather(*tasks)
        self.logger.info(f"DIAGNOSTIC: asyncio.gather completed, got {len(results)} results - PID: {process_id}")
        
        non_empty_results = [df for df in results if not df.empty]
        if non_empty_results:
            all_results = pd.concat(non_empty_results, ignore_index=True)
            self.logger.info(f"DIAGNOSTIC: Finished processing all projects. Total rows: {len(all_results)} - PID: {process_id}")
            return all_results
        else:
            self.logger.info(f"DIAGNOSTIC: No new data was processed. Returning an empty DataFrame - PID: {process_id}")
            return pd.DataFrame()

    async def run(self, output_dir: Path):
        """Main method to run the entire process."""
        import os
        pid = os.getpid()
        
        try:
            self.logger.info("Starting multi-project validation process.")
            await self.initialize()
            results = await self.process_all_projects()
            if results.empty:
                self.logger.info("No new results to save.")
            self.logger.info("Multi-project validation process completed.")
            self.writing_complete.set()
            # Clean up checkpoint after successful completion
            #checkpoint_path = self._get_checkpoint_path()
            #if checkpoint_path.exists():
        finally:
            pass