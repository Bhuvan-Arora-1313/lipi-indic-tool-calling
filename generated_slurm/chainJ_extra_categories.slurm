#!/bin/bash
#SBATCH --job-name=chainJ_extracat
#SBATCH --partition=gpu_h200_8
#SBATCH --qos=qos_gpu_h200
#SBATCH --gres=gpu:nvidia_h200_nvl:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=03:00:00
#SBATCH --output=/scratch/kudhru/dhruvkumar_indic_toolcalling/logs/chainJ_extracat.log

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

MODELS=(
  "Qwen/Qwen3-32B-FC"
  "google/gemma-3-27b-it"
)

for i in "${!MODELS[@]}"; do
  MODEL="${MODELS[$i]}"
  echo "=== [$((i+1))/${#MODELS[@]}] bfcl generate: $MODEL (multiple_ta,multiple_para,multiple_syno) ==="
  stdbuf -oL -eL bfcl generate --model "$MODEL" --test-category multiple_ta,multiple_para,multiple_syno --num-gpus 1 --gpu-memory-utilization 0.85 --backend vllm
  echo "=== [$((i+1))/${#MODELS[@]}] GENERATE_EXIT=$? ($MODEL) ==="
  echo "=== [$((i+1))/${#MODELS[@]}] bfcl evaluate: $MODEL ==="
  stdbuf -oL -eL bfcl evaluate --model "$MODEL" --test-category multiple_ta,multiple_para,multiple_syno
  echo "=== [$((i+1))/${#MODELS[@]}] EVALUATE_EXIT=$? ($MODEL) ==="
done

echo "=== CHAIN_DONE ==="
