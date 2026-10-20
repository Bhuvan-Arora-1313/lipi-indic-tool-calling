#!/bin/bash
#SBATCH --job-name=chainC_12b
#SBATCH --partition=gpu_a100_8
#SBATCH --qos=qos_gpu_a100
#SBATCH --gres=gpu:nvidia_a100-sxm4-80gb:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=02:30:00
#SBATCH --output=/scratch/kudhru/dhruvkumar_indic_toolcalling/logs/chainC_12b.log

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
echo "=== Chain chainC_12b: 2 model(s), GPU held for the entire chain ==="

echo "=== [1/2] bfcl generate: google/gemma-3-12b-it, FULL run (200 English + 200 Hindi) ==="
bfcl generate --model google/gemma-3-12b-it --test-category multiple,multiple_hi --num-gpus 1 --gpu-memory-utilization 0.9 --backend vllm
echo "=== [1/2] GENERATE_EXIT=$? (google/gemma-3-12b-it) ==="

echo "=== [1/2] bfcl evaluate: google/gemma-3-12b-it ==="
bfcl evaluate --model google/gemma-3-12b-it --test-category multiple,multiple_hi
echo "=== [1/2] EVALUATE_EXIT=$? (google/gemma-3-12b-it) ==="

echo "=== [2/2] bfcl generate: tiiuae/Falcon3-10B-Instruct-FC, FULL run (200 English + 200 Hindi) ==="
bfcl generate --model tiiuae/Falcon3-10B-Instruct-FC --test-category multiple,multiple_hi --num-gpus 1 --gpu-memory-utilization 0.9 --backend vllm
echo "=== [2/2] GENERATE_EXIT=$? (tiiuae/Falcon3-10B-Instruct-FC) ==="

echo "=== [2/2] bfcl evaluate: tiiuae/Falcon3-10B-Instruct-FC ==="
bfcl evaluate --model tiiuae/Falcon3-10B-Instruct-FC --test-category multiple,multiple_hi
echo "=== [2/2] EVALUATE_EXIT=$? (tiiuae/Falcon3-10B-Instruct-FC) ==="

echo "=== CHAIN_DONE ==="
