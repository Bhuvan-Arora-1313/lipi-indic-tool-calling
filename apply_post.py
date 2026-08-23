"""
apply_post.py

Generalized version of build_post_variant.py -- applies MLCL's "POST"
(Post-Translation) step to an EXISTING result set, translating only
the non-English parameter values found in it. Works on any category
you've already run, not just the raw NT-Hindi baseline, which means
this same script builds both:

    POST on the raw baseline:
        python apply_post.py --source-category simple_python_hi

    PT+POST combination (POST applied on top of your PT results):
        python apply_post.py --source-category simple_python_hi_pt

Neither of these needs a new `bfcl generate` run -- POST is defined as
a post-processing step on already-generated output, so this reuses
whatever result file already exists for --source-category. Output
category name is always <source-category>_post.

Only calls the API to translate parameter values that actually contain
non-ASCII characters -- values already in English cost nothing.

USAGE (run from inside berkeley-function-call-leaderboard):
    python apply_post.py --source-category simple_python_hi_pt --model gpt-4o-mini-2024-07-18-FC
"""

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

RESULT_DIR_TEMPLATE = "result/{model}/non_live"

TRANSLATE_SYSTEM_PROMPT = (
    "Translate the following text into natural English. If it is already in English, "
    "return it unchanged. Output ONLY the translation, nothing else -- no quotes, no notes."
)


def has_non_ascii(value):
    return isinstance(value, str) and any(ord(c) > 127 for c in value)


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
    return f"{prefix}_post_{num}"


def translate_value(client, model, text):
    resp = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": TRANSLATE_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
    )
    return resp.choices[0].message.content.strip()


def post_translate_result(client, model, result_field):
    if not isinstance(result_field, list):
        return result_field, 0

    n_translated = 0
    new_result = []
    for call in result_field:
        new_call = {}
        for func_name, args_json_str in call.items():
            try:
                args = json.loads(args_json_str)
            except (json.JSONDecodeError, TypeError):
                new_call[func_name] = args_json_str
                continue

            for key, value in args.items():
                if has_non_ascii(value):
                    args[key] = translate_value(client, model, value)
                    n_translated += 1
                elif isinstance(value, list):
                    args[key] = [
                        translate_value(client, model, v) if has_non_ascii(v) else v
                        for v in value
                    ]
                    n_translated += sum(1 for v in value if has_non_ascii(v))

            new_call[func_name] = json.dumps(args, ensure_ascii=False)
        new_result.append(new_call)

    return new_result, n_translated


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-category", required=True, help="The category whose existing results POST should be applied to, e.g. simple_python_hi or simple_python_hi_pt")
    parser.add_argument("--model", default="gpt-4o-mini-2024-07-18-FC", help="Model registry name (must match your result folder name)")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    out_category = f"{args.source_category}_post"

    result_dir = Path(RESULT_DIR_TEMPLATE.format(model=args.model))
    source_result_path = result_dir / f"BFCL_v4_{args.source_category}_result.json"
    out_result_path = result_dir / f"BFCL_v4_{out_category}_result.json"

    source_questions_path = Path(f"bfcl_eval/data/BFCL_v4_{args.source_category}.json")
    source_answers_path = Path(f"bfcl_eval/data/possible_answer/BFCL_v4_{args.source_category}.json")
    out_questions_path = Path(f"bfcl_eval/data/BFCL_v4_{out_category}.json")
    out_answers_path = Path(f"bfcl_eval/data/possible_answer/BFCL_v4_{out_category}.json")

    for p, label in [(source_result_path, "result file"), (source_questions_path, "question file"), (source_answers_path, "ground truth file")]:
        if not p.exists():
            print(f"ERROR: {label} not found at {p}")
            print(f"Make sure --source-category '{args.source_category}' has already been generated and/or built.")
            sys.exit(1)

    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found. Run this from the berkeley-function-call-leaderboard folder.")
        sys.exit(1)
    translate_model = args.model[:-3] if args.model.endswith("-FC") else args.model
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=30.0, max_retries=2)

    entries = load_jsonl(source_result_path)
    if args.limit:
        entries = entries[: args.limit]

    done_ids = set()
    if out_result_path.exists():
        for e in load_jsonl(out_result_path):
            done_ids.add(e["id"])

    print(f"Applying POST to '{args.source_category}' -> '{out_category}', {len(entries)} entries, using {translate_model}...")
    if done_ids:
        print(f"({len(done_ids)} already done in a previous run, resuming)")

    total_values_translated = 0
    with open(out_result_path, "a", encoding="utf-8") as out_f:
        for i, entry in enumerate(entries):
            new_id = remap_id(entry["id"])
            if new_id in done_ids:
                continue

            try:
                new_result_field, n = post_translate_result(client, translate_model, entry["result"])
            except Exception as e:
                print(f"\nERROR on {entry['id']}: {e}")
                print("Re-run this same command to resume from here.")
                sys.exit(1)

            total_values_translated += n
            new_entry = {"id": new_id, "result": new_result_field}
            out_f.write(json.dumps(new_entry, ensure_ascii=False) + "\n")
            out_f.flush()

            flag = f" ({n} value(s) translated)" if n else ""
            print(f"  [{i + 1}/{len(entries)}] {entry['id']} -> {new_id}{flag}")

    for source_path, out_path in [(source_answers_path, out_answers_path), (source_questions_path, out_questions_path)]:
        entries_to_remap = load_jsonl(source_path)
        remapped = []
        for entry in entries_to_remap:
            new_entry = json.loads(json.dumps(entry))
            new_entry["id"] = remap_id(entry["id"])
            remapped.append(new_entry)
        save_jsonl(out_path, remapped)

    print(f"\nDone. Translated {total_values_translated} non-English parameter value(s) total.")
    print(f"Wrote {out_result_path}")
    print(f"Wrote {out_answers_path}")
    print(f"Wrote {out_questions_path}")
    print()
    print("Next steps:")
    print(f"  python register_category.py {out_category}")
    print(f"  bfcl evaluate --model {args.model} --test-category {out_category}")
    print("  (no `bfcl generate` needed -- the result file already exists)")


if __name__ == "__main__":
    main()
