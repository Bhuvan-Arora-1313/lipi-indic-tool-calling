#!/bin/bash
#SBATCH --job-name=chainG_largetier
#SBATCH --partition=gpu_h200_8
#SBATCH --qos=qos_gpu_h200
#SBATCH --gres=gpu:nvidia_h200_nvl:2
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=128G
#SBATCH --time=06:00:00
#SBATCH --output=/scratch/kudhru/dhruvkumar_indic_toolcalling/logs/chainG_largetier.log

set -x
source ~/miniconda3/etc/profile.d/conda.sh
conda activate /scratch/kudhru/dhruvkumar_indic_toolcalling/envs/indic-tc

export HF_HOME=/scratch/kudhru/dhruvkumar_indic_toolcalling/hf_cache
export PIP_CACHE_DIR=/scratch/kudhru/dhruvkumar_indic_toolcalling/pip_cache
export XDG_CACHE_HOME=/scratch/kudhru/dhruvkumar_indic_toolcalling/xdg_cache
export TORCH_HOME=/scratch/kudhru/dhruvkumar_indic_toolcalling/torch_cache
mkdir -p "$HF_HOME" "$XDG_CACHE_HOME" "$TORCH_HOME"
# Same fix confirmed necessary on bits-gpu (vLLM's V1 engine hung there);
# applied here too as a precaution, matching that box's working config.
export VLLM_USE_V1=0

cd /scratch/kudhru/dhruvkumar_indic_toolcalling/repo

echo "=== GPU check ==="
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv
echo "=== Chain chainG_largetier: holds this 2-GPU allocation for all 3 models, no release between them ==="

echo "=== [1/3] bfcl generate: google/gemma-3-27b-it (num-gpus=1) ==="
stdbuf -oL -eL bfcl generate --model google/gemma-3-27b-it --test-category multiple,multiple_hi --num-gpus 1 --gpu-memory-utilization 0.85 --backend vllm
echo "=== [1/3] GENERATE_EXIT=$? (google/gemma-3-27b-it) ==="
echo "=== [1/3] bfcl evaluate: google/gemma-3-27b-it ==="
stdbuf -oL -eL bfcl evaluate --model google/gemma-3-27b-it --test-category multiple,multiple_hi
echo "=== [1/3] EVALUATE_EXIT=$? (google/gemma-3-27b-it) ==="

echo "=== [2/3] bfcl generate: Qwen/Qwen3-32B-FC (num-gpus=1) ==="
stdbuf -oL -eL bfcl generate --model Qwen/Qwen3-32B-FC --test-category multiple,multiple_hi --num-gpus 1 --gpu-memory-utilization 0.85 --backend vllm
echo "=== [2/3] GENERATE_EXIT=$? (Qwen/Qwen3-32B-FC) ==="
echo "=== [2/3] bfcl evaluate: Qwen/Qwen3-32B-FC ==="
stdbuf -oL -eL bfcl evaluate --model Qwen/Qwen3-32B-FC --test-category multiple,multiple_hi
echo "=== [2/3] EVALUATE_EXIT=$? (Qwen/Qwen3-32B-FC) ==="

echo "=== [3/3] bfcl generate: meta-llama/Llama-3.3-70B-Instruct-FC (num-gpus=2, tensor-parallel) ==="
stdbuf -oL -eL bfcl generate --model meta-llama/Llama-3.3-70B-Instruct-FC --test-category multiple,multiple_hi --num-gpus 2 --gpu-memory-utilization 0.85 --backend vllm
echo "=== [3/3] GENERATE_EXIT=$? (meta-llama/Llama-3.3-70B-Instruct-FC) ==="
echo "=== [3/3] bfcl evaluate: meta-llama/Llama-3.3-70B-Instruct-FC ==="
stdbuf -oL -eL bfcl evaluate --model meta-llama/Llama-3.3-70B-Instruct-FC --test-category multiple,multiple_hi
echo "=== [3/3] EVALUATE_EXIT=$? (meta-llama/Llama-3.3-70B-Instruct-FC) ==="

echo "=== CHAIN_DONE ==="
