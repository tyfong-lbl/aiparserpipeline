async def _load_checkpoint(self):
    """Load the state from a checkpoint file if it exists."""
    checkpoint_path = self._get_checkpoint_path()
    if checkpoint_path.exists():
        try:
            with open(checkpoint_path, 'rb') as f:
                self.project_outputs = pickle.load(f)
            self.completed_projects = set(self.project_outputs.keys())
            self.logger.info(f"Checkpoint loaded. Resuming with {len(self.completed_projects)} completed projects")
        except Exception as e:
            self.logger.error(f"Error loading checkpoint: {e}")
            # If loading fails, start fresh
            self.project_outputs = {}
            self.completed_projects = set()
    else:
        self.logger.info("No checkpoint found. Starting from the beginning.")

async def _save_checkpoint(self):
    """Save the current state to a checkpoint file."""
    if not self.project_outputs:
        self.logger.info("No data to save, skipping checkpoint save")
        return
        
    try:
        self.checkpoint_dir.mkdir(exist_ok=True)
        with open(self._get_checkpoint_path(), 'wb') as f:
            await asyncio.to_thread(pickle.dump, self.project_outputs, f)
        self.logger.info(f"Checkpoint saved. Completed projects: {len(self.completed_projects)}")
    except Exception as e:
        self.logger.error(f"Error saving checkpoint: {e}")

async def run(self, output_dir: Path):
    """Main method to run the entire process."""
    self.logger.info("Starting multi-project validation process.")
    await self.initialize()
    
    results = await self.process_all_projects()
    
    if not results.empty:
        now = datetime.now()
        datetime_str = now.strftime('%Y-%m-%d-%H%M')
        csv_name = f"multi_project_readout_{datetime_str}.csv"
        results.to_csv(output_dir / csv_name)
        self.logger.info(f"Results saved to {output_dir / csv_name}")
        
        # Only save checkpoint if we have results
        await self._save_checkpoint()
        self.logger.info("Checkpoint saved")
    else:
        self.logger.warning("No data was collected. No results to save.")
    
    self.logger.info("Multi-project validation process completed.")
    self.writing_complete.set()

async def initialize(self):
    try:
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch()
        self.logger.info("Browser initialized successfully")
    except Exception as e:
        self.logger.error(f"Failed to initialize browser: {e}")
        raise RuntimeError("Browser initialization failed")

async def async_save_pickle(file_path, save_complete_event):
    loop = asyncio.get_running_loop()
    if not os.path.exists(file_path):
        logging.info("No checkpoint file found, skipping save")
        save_complete_event.set()
        return
        
    await loop.run_in_executor(None, save_pickle, file_path)
    save_complete_event.set()  # Signal that saving is complete

async def main():
    # ... previous code ...
    
    async with manage_checkpoint(checkpoint_path, args.keep_checkpoint) as (save_complete_event, cleanup_event):
        try:
            await multi_validator.run(output_dir)
            # Wait for the writing to complete
            await multi_validator.writing_complete.wait()
            
            # Only try to save pickle if we have results
            if not multi_validator.project_outputs:
                logging.info("No results to save, skipping final checkpoint save")
            else:
                await async_save_pickle(checkpoint_path, save_complete_event)
                # Wait for save_pickle to complete
                await save_complete_event.wait()
                
        except Exception as e:
            logging.error(f"An error occurred during main execution: {e}")
            logging.error(traceback.format_exc())
            # Don't set cleanup_event, so checkpoint won't be deleted
