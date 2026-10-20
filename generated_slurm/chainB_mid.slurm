#!/bin/bash
#SBATCH --job-name=chainB_mid
#SBATCH --partition=gpu_v100_2
#SBATCH --qos=gpulimit
#SBATCH --gres=gpu:tesla_v100-pcie-32gb:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --output=/scratch/kudhru/dhruvkumar_indic_toolcalling/logs/chainB_mid.log

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
echo "=== Chain chainB_mid: 4 model(s), GPU held for the entire chain ==="

echo "=== [1/4] bfcl generate: Qwen/Qwen3-8B-FC, FULL run (200 English + 200 Hindi) ==="
bfcl generate --model Qwen/Qwen3-8B-FC --test-category multiple,multiple_hi --num-gpus 1 --gpu-memory-utilization 0.9 --backend vllm
echo "=== [1/4] GENERATE_EXIT=$? (Qwen/Qwen3-8B-FC) ==="

echo "=== [1/4] bfcl evaluate: Qwen/Qwen3-8B-FC ==="
bfcl evaluate --model Qwen/Qwen3-8B-FC --test-category multiple,multiple_hi
echo "=== [1/4] EVALUATE_EXIT=$? (Qwen/Qwen3-8B-FC) ==="

echo "=== [2/4] bfcl generate: tiiuae/Falcon3-7B-Instruct-FC, FULL run (200 English + 200 Hindi) ==="
bfcl generate --model tiiuae/Falcon3-7B-Instruct-FC --test-category multiple,multiple_hi --num-gpus 1 --gpu-memory-utilization 0.9 --backend vllm
echo "=== [2/4] GENERATE_EXIT=$? (tiiuae/Falcon3-7B-Instruct-FC) ==="

echo "=== [2/4] bfcl evaluate: tiiuae/Falcon3-7B-Instruct-FC ==="
bfcl evaluate --model tiiuae/Falcon3-7B-Instruct-FC --test-category multiple,multiple_hi
echo "=== [2/4] EVALUATE_EXIT=$? (tiiuae/Falcon3-7B-Instruct-FC) ==="

echo "=== [3/4] bfcl generate: meta-llama/Llama-3.1-8B-Instruct-FC, FULL run (200 English + 200 Hindi) ==="
bfcl generate --model meta-llama/Llama-3.1-8B-Instruct-FC --test-category multiple,multiple_hi --num-gpus 1 --gpu-memory-utilization 0.9 --backend vllm
echo "=== [3/4] GENERATE_EXIT=$? (meta-llama/Llama-3.1-8B-Instruct-FC) ==="

echo "=== [3/4] bfcl evaluate: meta-llama/Llama-3.1-8B-Instruct-FC ==="
bfcl evaluate --model meta-llama/Llama-3.1-8B-Instruct-FC --test-category multiple,multiple_hi
echo "=== [3/4] EVALUATE_EXIT=$? (meta-llama/Llama-3.1-8B-Instruct-FC) ==="

echo "=== [4/4] bfcl generate: MadeAgents/Hammer2.1-7b, FULL run (200 English + 200 Hindi) ==="
bfcl generate --model MadeAgents/Hammer2.1-7b --test-category multiple,multiple_hi --num-gpus 1 --gpu-memory-utilization 0.9 --backend vllm
echo "=== [4/4] GENERATE_EXIT=$? (MadeAgents/Hammer2.1-7b) ==="

echo "=== [4/4] bfcl evaluate: MadeAgents/Hammer2.1-7b ==="
bfcl evaluate --model MadeAgents/Hammer2.1-7b --test-category multiple,multiple_hi
echo "=== [4/4] EVALUATE_EXIT=$? (MadeAgents/Hammer2.1-7b) ==="

echo "=== CHAIN_DONE ==="
