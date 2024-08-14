#!/bin/bash

#SBATCH --account=ac_scsguest
#SBATCH --mail-user=tyfong@lbl.gov
#SBATCH --mail-type=ALL
#SBATCH --partition=lr3
#SBATCH --mincpus=32
#SBATCH --mem=248G
#SBATCH --nodes=1
#SBATCH --qos=lr_normal
#SBATCH --ntasks-per-node=2
#SBATCH --cpus-per-task=5
#SBATCH --time=24:0:0
#SBATCH --verbose
#SBATCH --kill-on-invalid-dep=yes

export OMP_NUM_THREADS=5
export OMP_PLACES=threads
export OMP_PROC_BIND=spread

cd /global/scratch/users/tyfong/code/aiparserpipeline
source aiparserpipeline/bin/activate
source /global/home/users/tyfong/groundtruth/ainewsparser/set_groundtruth_env.sh
source /global/home/users/tyfong/secret_management/lbl_ai_secret_management/set_cyclogpt_env.sh
python main.py >> error_output.txt 2>&1

