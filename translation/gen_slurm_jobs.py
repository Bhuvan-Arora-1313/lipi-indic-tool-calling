"""
gen_slurm_jobs.py

Generates one SLURM job script per GPU "chain" for the 15-model Hindi
batch (5 families x small/medium/large: Qwen3, Gemma3, Falcon3,
Llama-3.x, Hammer2.1). Each chain claims a GPU allocation ONCE and holds
it for every model assigned to that chain, looping `bfcl generate` +
`bfcl evaluate` per model sequentially inside the same SLURM job --
the GPU is never released and re-queued between models within a chain
(explicit user requirement: don't lose the allocation to another job
mid-batch on this shared, contended cluster). Each generate call still
runs BOTH English ("multiple") and Hindi ("multiple_hi") together, same
as the working Tamil pattern.

Not run automatically -- writes .slurm files to ./generated_slurm/ for
review before scp'ing to Sharanga and submitting.

USAGE (run from inside berkeley-function-call-leaderboard):
    python translation/gen_slurm_jobs.py
"""

from pathlib import Path

REPO_DIR = "/scratch/kudhru/dhruvkumar_indic_toolcalling/repo"
BASE_DIR = "/scratch/kudhru/dhruvkumar_indic_toolcalling"
OUT_DIR = Path("generated_slurm")

# (chain_tag, partition, qos, num_gpus, gres_gpu_type, time_limit, [model_names])
CHAINS = [
    # Temporarily on gpu_h100_4, not gpu_v100_2 (its intended, right-sized home) --
    # V100_2 is physically monopolized by another lab's 4 long-running jobs (1-2+
    # days each, no account-level job-count limit to work around, purely a
    # physical-availability wait), while h100_4 had a free GPU and room under our
    # account's own qos_gpu_h100 job cap (0/3 used) at submission time (2026-09-19).
    # This chain is small enough (<=4B) to run fine on an H100, just not its ideal
    # hardware fit -- move back to V100 once that partition frees up.
    ("chainA_tiny", "gpu_h100_4", "qos_gpu_h100", 1, "nvidia_h100_80gb_hbm3", "04:00:00", [
        "Qwen/Qwen3-1.7B-FC",
        "google/gemma-3-4b-it",
        "tiiuae/Falcon3-3B-Instruct-FC",
        "meta-llama/Llama-3.2-3B-Instruct-FC",
        "MadeAgents/Hammer2.1-0.5b",
        "MadeAgents/Hammer2.1-1.5b",
    ]),
    ("chainB_mid", "gpu_v100_2", "gpulimit", 1, "tesla_v100-pcie-32gb", "04:00:00", [
        "Qwen/Qwen3-8B-FC",
        "tiiuae/Falcon3-7B-Instruct-FC",
        "meta-llama/Llama-3.1-8B-Instruct-FC",
        "MadeAgents/Hammer2.1-7b",
    ]),
    ("chainC_12b", "gpu_a100_8", "qos_gpu_a100", 1, "nvidia_a100-sxm4-80gb", "02:30:00", [
        "google/gemma-3-12b-it",
        "tiiuae/Falcon3-10B-Instruct-FC",
    ]),
    # Retargeted from gpu_h100_4 to gpu_h200_8: this account's own qos_gpu_h100
    # job quota (MaxJobsPU=3) is already fully used by other labmates' running
    # +pending jobs under the shared account, so a100/h100 both just queue
    # behind existing work regardless of physical GPU availability. h200's
    # quota (MaxJobsPU=2) had room at submission time (2026-09-19).
    ("chainD_gemma27b", "gpu_h200_8", "qos_gpu_h200", 1, "nvidia_h200_nvl", "02:00:00", [
        "google/gemma-3-27b-it",
    ]),
    ("chainE_qwen32b", "gpu_h200_8", "qos_gpu_h200", 1, "nvidia_h200_nvl", "02:00:00", [
        "Qwen/Qwen3-32B-FC",
    ]),
    ("chainF_llama70b", "gpu_h200_8", "qos_gpu_h200", 2, "nvidia_h200_nvl", "03:00:00", [
        "meta-llama/Llama-3.3-70B-Instruct-FC",
    ]),
]

HEADER_TEMPLATE = """#!/bin/bash
#SBATCH --job-name={tag}
#SBATCH --partition={partition}
{qos_line}#SBATCH --gres=gpu:{gres_type}:{num_gpus}
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time={time_limit}
#SBATCH --output={base_dir}/logs/{tag}.log

set -x
source ~/miniconda3/etc/profile.d/conda.sh
conda activate {base_dir}/envs/indic-tc

export HF_HOME={base_dir}/hf_cache
export PIP_CACHE_DIR={base_dir}/pip_cache
export XDG_CACHE_HOME={base_dir}/xdg_cache
export TORCH_HOME={base_dir}/torch_cache
# vLLM's V1 engine hung indefinitely on the bits-gpu box (confirmed via
# frozen engine-core CPU time, not just slow); V0 fixed it there and is
# applied here too as a precaution before hitting the same issue mid-batch.
export VLLM_USE_V1=0
mkdir -p "$HF_HOME" "$XDG_CACHE_HOME" "$TORCH_HOME"

cd {repo_dir}

echo "=== GPU check ==="
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv
echo "=== Chain {tag}: {n_models} model(s), GPU held for the entire chain ==="
"""

MODEL_BLOCK_TEMPLATE = """
echo "=== [{idx}/{n_models}] bfcl generate: {model}, FULL run (200 English + 200 Hindi) ==="
bfcl generate --model {model} --test-category multiple,multiple_hi --num-gpus {num_gpus} --gpu-memory-utilization 0.9 --backend vllm
echo "=== [{idx}/{n_models}] GENERATE_EXIT=$? ({model}) ==="

echo "=== [{idx}/{n_models}] bfcl evaluate: {model} ==="
bfcl evaluate --model {model} --test-category multiple,multiple_hi
echo "=== [{idx}/{n_models}] EVALUATE_EXIT=$? ({model}) ==="
"""

FOOTER = """
echo "=== CHAIN_DONE ==="
"""


def main():
    OUT_DIR.mkdir(exist_ok=True)
    for tag, partition, qos, num_gpus, gres_type, time_limit, models in CHAINS:
        qos_line = f"#SBATCH --qos={qos}\n" if qos else ""
        content = HEADER_TEMPLATE.format(
            tag=tag, partition=partition, qos_line=qos_line, gres_type=gres_type,
            num_gpus=num_gpus, time_limit=time_limit, base_dir=BASE_DIR,
            repo_dir=REPO_DIR, n_models=len(models),
        )
        for idx, model in enumerate(models, start=1):
            content += MODEL_BLOCK_TEMPLATE.format(idx=idx, n_models=len(models), model=model, num_gpus=num_gpus)
        content += FOOTER

        out_path = OUT_DIR / f"{tag}.slurm"
        out_path.write_text(content)
        print(f"Wrote {out_path} ({len(models)} models, partition={partition}, gpus={num_gpus}x{gres_type}, time={time_limit})")

    total_models = sum(len(m) for *_, m in CHAINS)
    print(f"\n{len(CHAINS)} chain job scripts written to {OUT_DIR}/, covering {total_models} models total.")


if __name__ == "__main__":
    main()
