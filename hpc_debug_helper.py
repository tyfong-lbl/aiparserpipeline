#!/usr/bin/env python3
"""
HPC Debug Helper Script
This script helps diagnose duplicate execution issues on HPC systems.
"""

import os
import sys
import time
import socket
import subprocess
from pathlib import Path

def check_hpc_environment():
    """Check for HPC-specific environment variables and configurations."""
    print("=== HPC Environment Check ===")
    
    # Check for SLURM
    slurm_vars = ['SLURM_JOB_ID', 'SLURM_ARRAY_TASK_ID', 'SLURM_PROCID', 'SLURM_NTASKS']
    slurm_found = False
    for var in slurm_vars:
        value = os.environ.get(var)
        if value:
            print(f"SLURM: {var} = {value}")
            slurm_found = True
    
    # Check for PBS/Torque
    pbs_vars = ['PBS_JOBID', 'PBS_ARRAYID', 'PBS_TASKNUM', 'PBS_VNODENUM']
    pbs_found = False
    for var in pbs_vars:
        value = os.environ.get(var)
        if value:
            print(f"PBS: {var} = {value}")
            pbs_found = True
    
    # Check for SGE
    sge_vars = ['SGE_TASK_ID', 'JOB_ID', 'SGE_TASK_FIRST', 'SGE_TASK_LAST']
    sge_found = False
    for var in sge_vars:
        value = os.environ.get(var)
        if value:
            print(f"SGE: {var} = {value}")
            sge_found = True
    
    if not (slurm_found or pbs_found or sge_found):
        print("No HPC scheduler environment variables detected")
    
    return slurm_found, pbs_found, sge_found

def check_process_info():
    """Check current process information."""
    print("\n=== Process Information ===")
    print(f"PID: {os.getpid()}")
    print(f"PPID: {os.getppid()}")
    print(f"Hostname: {socket.gethostname()}")
    print(f"Current Working Directory: {os.getcwd()}")
    print(f"Command Line: {' '.join(sys.argv)}")
    
    # Check if running under a job scheduler
    try:
        with open('/proc/self/cgroup', 'r') as f:
            cgroups = f.read()
            if 'slurm' in cgroups.lower():
                print("Running under SLURM cgroup")
            elif 'pbs' in cgroups.lower():
                print("Running under PBS cgroup")
    except:
        pass

def check_file_locks():
    """Check for existing lock files."""
    print("\n=== Lock File Check ===")
    
    current_dir = Path.cwd()
    checkpoint_dir = current_dir / 'checkpoints'
    
    lock_file = checkpoint_dir / 'process.lock'
    if lock_file.exists():
        try:
            with open(lock_file, 'r') as f:
                content = f.read().strip().split('\n')
                if len(content) >= 2:
                    pid = content[0]
                    timestamp = float(content[1])
                    age = time.time() - timestamp
                    print(f"Lock file exists: PID {pid}, Age: {age:.1f} seconds")
                    
                    # Check if process is still running
                    try:
                        os.kill(int(pid), 0)  # Signal 0 just checks if process exists
                        print(f"Process {pid} is still running")
                    except (OSError, ValueError):
                        print(f"Process {pid} is no longer running - stale lock file")
                else:
                    print("Lock file exists but has invalid format")
        except Exception as e:
            print(f"Error reading lock file: {e}")
    else:
        print("No lock file found")

def check_running_processes():
    """Check for other instances of this script."""
    print("\n=== Running Process Check ===")
    
    try:
        # Look for python processes running main.py
        result = subprocess.run(['pgrep', '-f', 'main.py'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            print(f"Found {len(pids)} processes running main.py:")
            for pid in pids:
                if pid.strip():
                    print(f"  PID: {pid}")
        else:
            print("No other main.py processes found")
    except Exception as e:
        print(f"Could not check running processes: {e}")

def main():
    print("HPC Duplicate Execution Debug Helper")
    print("=" * 40)
    
    check_hpc_environment()
    check_process_info()
    check_file_locks()
    check_running_processes()
    
    print("\n=== Recommendations ===")
    print("1. Check your job submission script for:")
    print("   - Multiple job submissions")
    print("   - Job arrays with overlapping tasks")
    print("   - Restart/requeue policies")
    
    print("\n2. If using SLURM, check:")
    print("   - squeue -u $USER")
    print("   - sacct -j $SLURM_JOB_ID")
    
    print("\n3. If using PBS, check:")
    print("   - qstat -u $USER")
    print("   - qstat -f $PBS_JOBID")
    
    print("\n4. Monitor the diagnostic logs for:")
    print("   - Multiple MAIN_START entries with different PIDs")
    print("   - PROCESS_LOCK messages")
    print("   - CHECKPOINT_LOAD race conditions")

if __name__ == "__main__":
    main()