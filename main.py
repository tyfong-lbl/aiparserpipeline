import argparse
import asyncio
# import aiofiles
import logging
import os
import pandas as pd
import pickle
import tracemalloc
import shutil
import sys
import traceback
import fcntl
import time
from contextlib import asynccontextmanager

from datetime import datetime
from multi_project_validator import MultiProjectValidator
from pathlib import Path
from pipeline_logger import PipelineLogger

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

def acquire_process_lock():
    """Acquire a file lock to prevent multiple processes from running simultaneously."""
    lock_file_path = Path(__file__).resolve().parent / 'process.lock'
    pid = os.getpid()
    
    try:
        # CRITICAL FIX: Use atomic file creation with exclusive lock
        # This prevents the race condition where multiple processes
        # can both see no lock file and both create one
        
        logging.info(f"PROCESS_LOCK: Attempting to acquire lock - PID: {pid}")
        
        # Create lock file with exclusive access - this is atomic
        lock_file = open(lock_file_path, 'x')  # 'x' mode fails if file exists
        
        try:
            # Acquire exclusive lock on the file descriptor
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            # Write PID and timestamp to lock file
            lock_file.write(f"{pid}\n{time.time()}\n")
            lock_file.flush()
            
            logging.info(f"PROCESS_LOCK: Successfully acquired lock - PID: {pid}")
            return True, lock_file
            
        except (BlockingIOError, OSError) as e:
            # Lock is held by another process
            lock_file.close()
            logging.warning(f"PROCESS_LOCK: Failed to acquire lock - PID: {pid}, Error: {e}")
            return False, None
            
    except FileExistsError:
        # Lock file already exists - check if process is still running
        try:
            with open(lock_file_path, 'r') as f:
                existing_pid = int(f.readline().strip())
                existing_time = float(f.readline().strip())
            
            # Check if the process is still running
            try:
                os.kill(existing_pid, 0)  # Signal 0 checks if process exists
                age = time.time() - existing_time
                logging.info(f"PROCESS_LOCK: Active lock found - PID: {existing_pid}, Age: {age:.1f}s")
                return False, None
            except (OSError, ProcessLookupError):
                # Process doesn't exist, remove stale lock and retry
                lock_file_path.unlink()
                logging.info(f"PROCESS_LOCK: Removed stale lock from PID: {existing_pid}, retrying...")
                # Recursive call to retry after removing stale lock
                return acquire_process_lock()
                
        except Exception as e:
            logging.warning(f"PROCESS_LOCK: Error checking existing lock: {e}")
            return False, None
            
    except Exception as e:
        logging.error(f"PROCESS_LOCK: Unexpected error acquiring lock: {e}")
        return False, None

def release_process_lock(lock_file):
    """Release the process lock."""
    if lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            lock_file.close()
            
            # Remove lock file
            lock_file_path = Path(__file__).resolve().parent / 'process.lock'
            if lock_file_path.exists():
                lock_file_path.unlink()
                
            pid = os.getpid()
            logging.info(f"PROCESS_LOCK: Released lock - PID: {pid}")
        except Exception as e:
            logging.error(f"PROCESS_LOCK: Error releasing lock: {e}")

async def main():
    # DIAGNOSTIC: Add process and environment logging for HPC debugging
    import socket
    import time
    pid = os.getpid()
    ppid = os.getppid()
    hostname = socket.gethostname()
    start_time = time.time()
    
    logging.info(f"MAIN_START: PID={pid}, PPID={ppid}, HOST={hostname}, TIME={start_time}")
    logging.info(f"MAIN_ARGS: {sys.argv}")
    logging.info(f"MAIN_ENV_SLURM: SLURM_JOB_ID={os.environ.get('SLURM_JOB_ID')}, SLURM_ARRAY_TASK_ID={os.environ.get('SLURM_ARRAY_TASK_ID')}")
    logging.info(f"MAIN_ENV_PBS: PBS_JOBID={os.environ.get('PBS_JOBID')}, PBS_ARRAYID={os.environ.get('PBS_ARRAYID')}")
    logging.info(f"MAIN_CWD: {os.getcwd()}")
    
    # DIAGNOSTIC: Add checkpoint to confirm this is where duplication occurs
    logging.info(f"MAIN_CHECKPOINT_1: About to parse arguments - PID={pid}")
    
    parser = argparse.ArgumentParser(description="Run multi-project validation")
    parser.add_argument('--keep-checkpoint', action='store_true', help='Keep the checkpoint file after completion')
    args = parser.parse_args()
    
    # CRITICAL FIX: Acquire process lock BEFORE creating MultiProjectValidator
    logging.info(f"MAIN_CHECKPOINT_LOCK: About to acquire process lock - PID={pid}")
    lock_acquired, lock_file = acquire_process_lock()
    
    if not lock_acquired:
        logging.warning(f"PROCESS_LOCK: Another process is already running, exiting - PID: {pid}")
        return 1  # Exit gracefully
    
    logging.info(f"MAIN_CHECKPOINT_LOCK_SUCCESS: Process lock acquired - PID={pid}")

    logging.info("Test log message")
    print("test message")
    #excel_path = "G:\\Shared drives\\USS\\Automation\\Solar_Project_Tracker_ITexamples_2022_noPDFs.xlsx"
    #excel_path = "/Users/TYFong/Desktop/worklogs/project_logs/ai_parser/25_sample_columns.xlsx"
    home_path = Path.home()
    excel_path = Path(home_path,"code/aiparserpipeline/diagnostics/Solar_Project_Tracker_ITexamples_2022_noPDFs_250521smalltest.xlsx")
    api_key = os.environ.get('CBORG_API_KEY')
    api_url = "https://api.cborg.lbl.gov"
    model = 'lbl/llama' #lbl/cborg-chat:latest' # option list found here: https://cborg.lbl.gov/models/
    #model = 'google/gemini-pro'
    prompt_directory = Path(__file__).resolve().parent / 'test_prompts'
    output_dir = Path(__file__).resolve().parent / 'results'
    checkpoint_dir = Path(__file__).resolve().parent / 'checkpoints'
    checkpoint_filename = 'checkpoint.pkl'
    await create_directory(prompt_directory)
    await create_directory(output_dir)
    await create_directory(checkpoint_dir)
    await create_directory(Path(__file__).resolve().parent / 'pipeline_logs')

    checkpoint_path = Path(checkpoint_dir, checkpoint_filename)

    pipeline_logs_dir = Path(__file__).resolve().parent / 'pipeline_logs'
    logger = PipelineLogger(pipeline_logs_dir)
    
    # DIAGNOSTIC: Add checkpoint before creating MultiProjectValidator
    logging.info(f"MAIN_CHECKPOINT_2: About to create MultiProjectValidator - PID={pid}")
    
    # Calculate max concurrent projects based on memory allocation
    # Assuming ~75MB per project, with 62GB total allocation
    # Leave buffer for OS and other processes
    max_concurrent_projects = 50  # Conservative limit for 62GB allocation
    
    multi_validator = MultiProjectValidator(
        excel_path=excel_path,
        api_key=api_key,
        api_url=api_url,
        model=model,
        prompt_directory=prompt_directory,
        checkpoint_dir=checkpoint_dir,
        logger=logger,
        max_concurrent_projects=max_concurrent_projects
    )
    
    # DIAGNOSTIC: Add checkpoint after creating MultiProjectValidator
    logging.info(f"MAIN_CHECKPOINT_3: Created MultiProjectValidator - PID={pid}")

    try:
        async with manage_checkpoint(checkpoint_path, args.keep_checkpoint) as (save_complete_event, cleanup_event):
            try:
                # DIAGNOSTIC: Add checkpoint before calling run() - this is where process lock should be
                logging.info(f"MAIN_CHECKPOINT_4: About to call multi_validator.run() - PID={pid}")
                await multi_validator.run(output_dir)
                # DIAGNOSTIC: Add checkpoint after calling run()
                logging.info(f"MAIN_CHECKPOINT_5: Completed multi_validator.run() - PID={pid}")
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
        
    finally:
        # CRITICAL: Always release the process lock
        release_process_lock(lock_file)

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