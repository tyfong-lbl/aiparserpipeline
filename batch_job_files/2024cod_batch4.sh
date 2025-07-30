#!/bin/bash

#SBATCH --account=pc_ussjmk
#SBATCH --job-name=omni
#SBATCH --mail-user=jmulvaneykemp@lbl.gov
#SBATCH --mail-type=ALL
#SBATCH --partition=lr5
#SBATCH --mincpus=20
#SBATCH --mem=124G
#SBATCH --nodes=1
#SBATCH --qos=lr_normal
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=20
#SBATCH --time=9:0:0
#SBATCH --verbose
#SBATCH --kill-on-invalid-dep=yes

export OMP_NUM_THREADS=20
export OMP_PLACES=threads
export OMP_PROC_BIND=close

cd /global/scratch/users/jmulvaneykemp/code/aiparserpipeline
source /global/home/users/jmulvaneykemp/virtualenvs/aiparserpipeline/bin/activate
python main.py "/global/home/users/jmulvaneykemp/aiparserinputs/production_inputs/2024cod_batch4.xlsx"