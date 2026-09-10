"""
generate_perturbations.py

Generates PARA (paraphrase) and SYNO (synonym substitution) English
perturbations of the base BFCL_v4_multiple.json queries (199 examples --
the full category, not a subset), using google/gemini-3.7-flash via
OpenRouter.

Prompts are verbatim from MLCL (arXiv 2601.05366), Appendix A.8 (PARA) and
A.9 (SYNO), for direct methodological comparability.

Output: data/perturbations/en_multiple_perturbations.jsonl -- one row per
(base_id, perturbation_type), including a "NO" row (the untouched original)
for every base query, so all three conditions are queryable from one file.
This JSONL is the canonical source of truth; any BFCL-ready category file
built later is a derived export from it, never hand-edited.

Idempotent: re-running skips any (base_id, perturbation_type) pair already
present in the output file, so an interrupted run costs nothing to resume.

USAGE (run from inside berkeley-function-call-leaderboard):
    python translation/generate_perturbations.py
    python translation/generate_perturbations.py --limit 5   # smoke test first
"""

import argparse
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MODEL = "google/gemini-3.7-flash"
SOURCE_PATH = Path("bfcl_eval/data/BFCL_v4_multiple.json")
OUTPUT_PATH = Path("data/perturbations/en_multiple_perturbations.jsonl")

# Verbatim from MLCL (arXiv 2601.05366), Appendix A.8.
PARA_SYSTEM_PROMPT = (
    "You are a helpful assistant helping rephrase user requests, while "
    "accurately preserving their meaning, including numbers and names if "
    "they exist. Do not answer the requirement; just produce another one "
    "that is identical in meaning but is phrased differently. Produce "
    "ONLY the rephrased requirement, without further thoughts or "
    "explanations."
)

# Verbatim from MLCL (arXiv 2601.05366), Appendix A.9, including the
# worked few-shot example, structured as actual message turns below.
SYNO_SYSTEM_PROMPT = (
    "You are a helpful assistant that replaces words with synonyms of "
    "similar meaning while maintaining semantic correctness. Your task is "
    "to process word by word and replace each word with a synonym if "
    "possible.\n"
    "IMPORTANT RULES: 1. Replace words with appropriate synonyms "
    "2. Maintain the semantic meaning and grammatical structure "
    "3. Do NOT perform general paraphrasing, only synonym replacement "
    "4. Process word by word, not phrase by phrase 5. If a word has no "
    "suitable synonym or is a proper noun, keep it unchanged\n"
    "Produce ONLY the modified text with synonyms, without further "
    "thoughts or explanations."
)
SYNO_EXAMPLE_USER = (
    "Can I find the dimensions and properties of a triangle, if it is "
    "known that its three sides are 5 units, 4 units and 3 units long?"
)
SYNO_EXAMPLE_ASSISTANT = (
    "Can I discover the measurements and characteristics of a triangle, "
    "if it is known that its three sides are 5 units, 4 units and 3 "
    "units long?"
)

write_lock = threading.Lock()


def load_jsonl(path):
    if not path.exists():
        return []
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def append_jsonl(path, entry):
    with write_lock:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def get_query_text(entry):
    return entry["question"][0][0]["content"]


def build_messages(perturbation_type, query_text):
    if perturbation_type == "PARA":
        return [
            {"role": "system", "content": PARA_SYSTEM_PROMPT},
            {"role": "user", "content": query_text},
        ]
    elif perturbation_type == "SYNO":
        return [
            {"role": "system", "content": SYNO_SYSTEM_PROMPT},
            {"role": "user", "content": SYNO_EXAMPLE_USER},
            {"role": "assistant", "content": SYNO_EXAMPLE_ASSISTANT},
            {"role": "user", "content": query_text},
        ]
    raise ValueError(perturbation_type)


def generate_one(client, base_id, source_text, perturbation_type):
    messages = build_messages(perturbation_type, source_text)
    resp = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        messages=messages,
    )
    text = resp.choices[0].message.content.strip()
    usage = resp.usage
    return {
        "base_id": base_id,
        "perturbation_type": perturbation_type,
        "text": text,
        "source_text": source_text,
        "model": MODEL,
        "prompt_version": f"{perturbation_type.lower()}_v1_mlcl",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_tokens": usage.prompt_tokens if usage else None,
        "output_tokens": usage.completion_tokens if usage else None,
        "review_status": "pending",
        "review_notes": "",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None,
                         help="Only process the first N base queries (for a smoke test).")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found. Run this from the berkeley-function-call-leaderboard folder.")
        return
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=30.0, max_retries=2)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    source_entries = load_jsonl(SOURCE_PATH)
    if args.limit:
        source_entries = source_entries[: args.limit]

    existing = load_jsonl(OUTPUT_PATH)
    already_done = {(e["base_id"], e["perturbation_type"]) for e in existing}

    # NO rows (the untouched originals) -- no API call, write directly.
    no_written = 0
    for entry in source_entries:
        base_id = entry["id"]
        if (base_id, "NO") in already_done:
            continue
        query_text = get_query_text(entry)
        append_jsonl(OUTPUT_PATH, {
            "base_id": base_id,
            "perturbation_type": "NO",
            "text": query_text,
            "source_text": query_text,
            "model": None,
            "prompt_version": None,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "input_tokens": None,
            "output_tokens": None,
            "review_status": "not_applicable",
            "review_notes": "",
        })
        no_written += 1
    print(f"Wrote {no_written} NO rows (skipped {len(source_entries) - no_written} already present).")

    # PARA and SYNO rows -- one API call each, in parallel.
    jobs = []
    for entry in source_entries:
        base_id = entry["id"]
        query_text = get_query_text(entry)
        for ptype in ("PARA", "SYNO"):
            if (base_id, ptype) not in already_done:
                jobs.append((base_id, query_text, ptype))

    print(f"Generating {len(jobs)} perturbations ({len(jobs) // 2} queries x 2 types), "
          f"skipping {len(source_entries) * 2 - len(jobs)} already present...")

    n_done, n_error = 0, 0
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(generate_one, client, base_id, query_text, ptype): (base_id, ptype)
            for base_id, query_text, ptype in jobs
        }
        for future in as_completed(futures):
            base_id, ptype = futures[future]
            try:
                result = future.result()
                append_jsonl(OUTPUT_PATH, result)
                n_done += 1
                if n_done % 20 == 0:
                    print(f"  {n_done}/{len(jobs)} done...")
            except Exception as e:
                n_error += 1
                print(f"  ERROR on {base_id} {ptype}: {e}")

    print(f"\nDone. {n_done} generated, {n_error} errors.")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
