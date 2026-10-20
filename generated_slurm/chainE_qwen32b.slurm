#!/bin/bash
#SBATCH --job-name=chainE_qwen32b
#SBATCH --partition=gpu_h200_8
#SBATCH --qos=qos_gpu_h200
#SBATCH --gres=gpu:nvidia_h200_nvl:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --output=/scratch/kudhru/dhruvkumar_indic_toolcalling/logs/chainE_qwen32b.log

set -x
source ~/miniconda3/etc/profile.d/conda.sh
conda activate /scratch/kudhru/dhruvkumar_indic_toolcalling/envs/indic-tc

export HF_HOME=/scratch/kudhru/dhruvkumar_indic_toolcalling/hf_cache
export PIP_CACHE_DIR=/scratch/kudhru/dhruvkumar_indic_toolcalling/pip_cache
export XDG_CACHE_HOME=/scratch/kudhru/dhruvkumar_indic_toolcalling/xdg_cache
export TORCH_HOME=/scratch/kudhru/dhruvkumar_indic_toolcalling/torch_cache
# vLLM's V1 engine hung indefinitely on the bits-gpu box (confirmed via
# frozen engine-core CPU time, not just slow); V0 fixed it there and is
# applied here too as a precaution before hitting the same issue mid-batch.
export VLLM_USE_V1=0
mkdir -p "$HF_HOME" "$XDG_CACHE_HOME" "$TORCH_HOME"

cd /scratch/kudhru/dhruvkumar_indic_toolcalling/repo

echo "=== GPU check ==="
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv
echo "=== Chain chainE_qwen32b: 1 model(s), GPU held for the entire chain ==="

echo "=== [1/1] bfcl generate: Qwen/Qwen3-32B-FC, FULL run (200 English + 200 Hindi) ==="
bfcl generate --model Qwen/Qwen3-32B-FC --test-category multiple,multiple_hi --num-gpus 1 --gpu-memory-utilization 0.9 --backend vllm
echo "=== [1/1] GENERATE_EXIT=$? (Qwen/Qwen3-32B-FC) ==="

echo "=== [1/1] bfcl evaluate: Qwen/Qwen3-32B-FC ==="
bfcl evaluate --model Qwen/Qwen3-32B-FC --test-category multiple,multiple_hi
echo "=== [1/1] EVALUATE_EXIT=$? (Qwen/Qwen3-32B-FC) ==="

echo "=== CHAIN_DONE ==="
