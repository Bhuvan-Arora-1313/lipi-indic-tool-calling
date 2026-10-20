#!/bin/bash
#SBATCH --job-name=chainA_tiny
#SBATCH --partition=gpu_h100_4
#SBATCH --qos=qos_gpu_h100
#SBATCH --gres=gpu:nvidia_h100_80gb_hbm3:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --output=/scratch/kudhru/dhruvkumar_indic_toolcalling/logs/chainA_tiny.log

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
echo "=== Chain chainA_tiny: 6 model(s), GPU held for the entire chain ==="

echo "=== [1/6] bfcl generate: Qwen/Qwen3-1.7B-FC, FULL run (200 English + 200 Hindi) ==="
bfcl generate --model Qwen/Qwen3-1.7B-FC --test-category multiple,multiple_hi --num-gpus 1 --gpu-memory-utilization 0.9 --backend vllm
echo "=== [1/6] GENERATE_EXIT=$? (Qwen/Qwen3-1.7B-FC) ==="

echo "=== [1/6] bfcl evaluate: Qwen/Qwen3-1.7B-FC ==="
bfcl evaluate --model Qwen/Qwen3-1.7B-FC --test-category multiple,multiple_hi
echo "=== [1/6] EVALUATE_EXIT=$? (Qwen/Qwen3-1.7B-FC) ==="

echo "=== [2/6] bfcl generate: google/gemma-3-4b-it, FULL run (200 English + 200 Hindi) ==="
bfcl generate --model google/gemma-3-4b-it --test-category multiple,multiple_hi --num-gpus 1 --gpu-memory-utilization 0.9 --backend vllm
echo "=== [2/6] GENERATE_EXIT=$? (google/gemma-3-4b-it) ==="

echo "=== [2/6] bfcl evaluate: google/gemma-3-4b-it ==="
bfcl evaluate --model google/gemma-3-4b-it --test-category multiple,multiple_hi
echo "=== [2/6] EVALUATE_EXIT=$? (google/gemma-3-4b-it) ==="

echo "=== [3/6] bfcl generate: tiiuae/Falcon3-3B-Instruct-FC, FULL run (200 English + 200 Hindi) ==="
bfcl generate --model tiiuae/Falcon3-3B-Instruct-FC --test-category multiple,multiple_hi --num-gpus 1 --gpu-memory-utilization 0.9 --backend vllm
echo "=== [3/6] GENERATE_EXIT=$? (tiiuae/Falcon3-3B-Instruct-FC) ==="

echo "=== [3/6] bfcl evaluate: tiiuae/Falcon3-3B-Instruct-FC ==="
bfcl evaluate --model tiiuae/Falcon3-3B-Instruct-FC --test-category multiple,multiple_hi
echo "=== [3/6] EVALUATE_EXIT=$? (tiiuae/Falcon3-3B-Instruct-FC) ==="

echo "=== [4/6] bfcl generate: meta-llama/Llama-3.2-3B-Instruct-FC, FULL run (200 English + 200 Hindi) ==="
bfcl generate --model meta-llama/Llama-3.2-3B-Instruct-FC --test-category multiple,multiple_hi --num-gpus 1 --gpu-memory-utilization 0.9 --backend vllm
echo "=== [4/6] GENERATE_EXIT=$? (meta-llama/Llama-3.2-3B-Instruct-FC) ==="

echo "=== [4/6] bfcl evaluate: meta-llama/Llama-3.2-3B-Instruct-FC ==="
bfcl evaluate --model meta-llama/Llama-3.2-3B-Instruct-FC --test-category multiple,multiple_hi
echo "=== [4/6] EVALUATE_EXIT=$? (meta-llama/Llama-3.2-3B-Instruct-FC) ==="

echo "=== [5/6] bfcl generate: MadeAgents/Hammer2.1-0.5b, FULL run (200 English + 200 Hindi) ==="
bfcl generate --model MadeAgents/Hammer2.1-0.5b --test-category multiple,multiple_hi --num-gpus 1 --gpu-memory-utilization 0.9 --backend vllm
echo "=== [5/6] GENERATE_EXIT=$? (MadeAgents/Hammer2.1-0.5b) ==="

echo "=== [5/6] bfcl evaluate: MadeAgents/Hammer2.1-0.5b ==="
bfcl evaluate --model MadeAgents/Hammer2.1-0.5b --test-category multiple,multiple_hi
echo "=== [5/6] EVALUATE_EXIT=$? (MadeAgents/Hammer2.1-0.5b) ==="

echo "=== [6/6] bfcl generate: MadeAgents/Hammer2.1-1.5b, FULL run (200 English + 200 Hindi) ==="
bfcl generate --model MadeAgents/Hammer2.1-1.5b --test-category multiple,multiple_hi --num-gpus 1 --gpu-memory-utilization 0.9 --backend vllm
echo "=== [6/6] GENERATE_EXIT=$? (MadeAgents/Hammer2.1-1.5b) ==="

echo "=== [6/6] bfcl evaluate: MadeAgents/Hammer2.1-1.5b ==="
bfcl evaluate --model MadeAgents/Hammer2.1-1.5b --test-category multiple,multiple_hi
echo "=== [6/6] EVALUATE_EXIT=$? (MadeAgents/Hammer2.1-1.5b) ==="

echo "=== CHAIN_DONE ==="
