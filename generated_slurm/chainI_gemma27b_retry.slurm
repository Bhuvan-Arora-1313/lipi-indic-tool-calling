#!/bin/bash
#SBATCH --job-name=chainI_gemma27b
#SBATCH --partition=gpu_h200_8
#SBATCH --qos=qos_gpu_h200
#SBATCH --gres=gpu:nvidia_h200_nvl:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=02:00:00
#SBATCH --output=/scratch/kudhru/dhruvkumar_indic_toolcalling/logs/chainI_gemma27b.log

set -x
source ~/miniconda3/etc/profile.d/conda.sh
conda activate /scratch/kudhru/dhruvkumar_indic_toolcalling/envs/indic-tc

export HF_HOME=/scratch/kudhru/dhruvkumar_indic_toolcalling/hf_cache
export PIP_CACHE_DIR=/scratch/kudhru/dhruvkumar_indic_toolcalling/pip_cache
export XDG_CACHE_HOME=/scratch/kudhru/dhruvkumar_indic_toolcalling/xdg_cache
export TORCH_HOME=/scratch/kudhru/dhruvkumar_indic_toolcalling/torch_cache
mkdir -p "$HF_HOME" "$XDG_CACHE_HOME" "$TORCH_HOME"
export VLLM_USE_V1=0

cd /scratch/kudhru/dhruvkumar_indic_toolcalling/repo

echo "=== GPU check ==="
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv

echo "=== bfcl generate: google/gemma-3-27b-it (num-gpus=1) ==="
stdbuf -oL -eL bfcl generate --model google/gemma-3-27b-it --test-category multiple,multiple_hi --num-gpus 1 --gpu-memory-utilization 0.85 --backend vllm
echo "=== GENERATE_EXIT=$? (google/gemma-3-27b-it) ==="
echo "=== bfcl evaluate: google/gemma-3-27b-it ==="
stdbuf -oL -eL bfcl evaluate --model google/gemma-3-27b-it --test-category multiple,multiple_hi
echo "=== EVALUATE_EXIT=$? (google/gemma-3-27b-it) ==="

echo "=== CHAIN_DONE ==="
