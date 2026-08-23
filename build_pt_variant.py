"""
build_pt_variant.py (generalized)

Builds MLCL's "PT" (Prompt-Level Instruction) baseline as a new BFCL
test category, for any language. Same mechanism as before -- a
system-role message gets prepended to the question, which BFCL
automatically merges with its own default system prompt.

USAGE (run from inside berkeley-function-call-leaderboard, AFTER
remap_ids.py has already been run for the language in question):
    python build_pt_variant.py --lang hi
    python build_pt_variant.py --lang ta
"""

import argparse
import json
from pathlib import Path

PT_INSTRUCTION = "IMPORTANT: Pass all parameter values in English."


def load_jsonl(path):
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def save_jsonl(path, entries):
    with open(path, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def remap_id(old_id):
    prefix, num = old_id.rsplit("_", 1)
    return f"{prefix}_pt_{num}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", required=True, choices=["hi", "ta"])
    args = parser.parse_args()

    source_questions = Path(f"bfcl_eval/data/BFCL_v4_simple_python_{args.lang}.json")
    source_answers = Path(f"bfcl_eval/data/possible_answer/BFCL_v4_simple_python_{args.lang}.json")
    out_questions = Path(f"bfcl_eval/data/BFCL_v4_simple_python_{args.lang}_pt.json")
    out_answers = Path(f"bfcl_eval/data/possible_answer/BFCL_v4_simple_python_{args.lang}_pt.json")

    if not source_questions.exists():
        print(f"ERROR: {source_questions} not found. Run remap_ids.py for --lang {args.lang} first.")
        return
    if not source_answers.exists():
        print(f"ERROR: {source_answers} not found.")
        return

    questions = load_jsonl(source_questions)
    answers = load_jsonl(source_answers)

    new_questions = []
    for entry in questions:
        new_entry = json.loads(json.dumps(entry))
        new_entry["id"] = remap_id(entry["id"])
        original_turn = new_entry["question"][0]
        new_entry["question"][0] = [{"role": "system", "content": PT_INSTRUCTION}] + original_turn
        new_questions.append(new_entry)

    new_answers = []
    for entry in answers:
        new_entry = json.loads(json.dumps(entry))
        new_entry["id"] = remap_id(entry["id"])
        new_answers.append(new_entry)

    save_jsonl(out_questions, new_questions)
    save_jsonl(out_answers, new_answers)

    out_category = f"simple_python_{args.lang}_pt"
    print(f"Wrote {len(new_questions)} PT-variant questions to {out_questions}")
    print(f"Wrote {len(new_answers)} matching ground-truth entries to {out_answers}")
    print()
    print("Next steps:")
    print(f"  python register_category.py {out_category}")
    print(f"  bfcl generate --model gpt-4o-mini-2024-07-18-FC --test-category {out_category} --num-threads 4")
    print(f"  bfcl evaluate --model gpt-4o-mini-2024-07-18-FC --test-category {out_category}")


if __name__ == "__main__":
    main()
