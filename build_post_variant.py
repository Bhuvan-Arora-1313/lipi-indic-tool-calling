"""
build_post_variant.py

Builds MLCL's "POST" (Post-Translation) baseline. Unlike PT and PRE,
this does NOT need a new `bfcl generate` run -- POST operates on the
model's OUTPUT, not its input, so we reuse your existing Hindi
generation results and translate only the parameter VALUES that came
back in a non-English script, using the same model, before scoring.
Everything else (which function was called, which parameters were
filled) is left untouched, matching MLCL's protocol (Appendix A.3.3).

Reads:  result/<model>/non_live/BFCL_v4_simple_python_hi_result.json
        (your existing Hindi generate output -- no new tool-calling cost)
Writes: a new result file + matching ground truth under a new
        "simple_python_hi_post" category, ready for `bfcl evaluate`
        directly.

Only calls the API to translate parameter values that actually contain
non-ASCII characters (i.e. likely Hindi script) -- values already in
English are left alone and don't cost anything.

USAGE (run from inside berkeley-function-call-leaderboard, AFTER your
simple_python_hi generate run has already completed):
    python build_post_variant.py --model gpt-4o-mini-2024-07-18-FC
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

RESULT_DIR_TEMPLATE = "result/{model}/non_live"
SOURCE_QUESTIONS = Path("bfcl_eval/data/BFCL_v4_simple_python_hi.json")
SOURCE_ANSWERS = Path("bfcl_eval/data/possible_answer/BFCL_v4_simple_python_hi.json")
OUT_QUESTIONS = Path("bfcl_eval/data/BFCL_v4_simple_python_hi_post.json")
OUT_ANSWERS = Path("bfcl_eval/data/possible_answer/BFCL_v4_simple_python_hi_post.json")

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
    """
    result_field looks like: [{"func_name": "{\"param\": \"value\", ...}"}]
    Returns the same shape with non-English string parameter values translated,
    plus a count of how many values were actually translated.
    """
    if not isinstance(result_field, list):
        # No function call was made (plain text response) -- nothing to translate
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
    parser.add_argument("--model", default="gpt-4o-mini-2024-07-18-FC", help="Model registry name (must match your result folder name)")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    result_dir = Path(RESULT_DIR_TEMPLATE.format(model=args.model))
    source_result_path = result_dir / "BFCL_v4_simple_python_hi_result.json"
    out_result_path = result_dir / "BFCL_v4_simple_python_hi_post_result.json"

    if not source_result_path.exists():
        print(f"ERROR: {source_result_path} not found.")
        print("Make sure you've already run bfcl generate for simple_python_hi.")
        sys.exit(1)
    if not SOURCE_ANSWERS.exists():
        print(f"ERROR: {SOURCE_ANSWERS} not found.")
        sys.exit(1)

    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found. Run this from the berkeley-function-call-leaderboard folder.")
        sys.exit(1)
    # Use the plain (non -FC) model name for the translation calls
    translate_model = args.model[:-3] if args.model.endswith("-FC") else args.model
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=30.0, max_retries=2)

    entries = load_jsonl(source_result_path)
    if args.limit:
        entries = entries[: args.limit]

    done_ids = set()
    if out_result_path.exists():
        for e in load_jsonl(out_result_path):
            done_ids.add(e["id"])

    print(f"Post-translating parameter values for {len(entries)} entries using {translate_model}...")
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

    # Ground truth just needs ID remapping, same as before
    answers = load_jsonl(SOURCE_ANSWERS)
    new_answers = []
    for entry in answers:
        new_entry = json.loads(json.dumps(entry))
        new_entry["id"] = remap_id(entry["id"])
        new_answers.append(new_entry)
    save_jsonl(OUT_ANSWERS, new_answers)

    # bfcl evaluate also loads the original question file by category name --
    # content is unchanged from simple_python_hi (POST only modifies the
    # OUTPUT, not the input), just needs the same ID remapping.
    if not SOURCE_QUESTIONS.exists():
        print(f"ERROR: {SOURCE_QUESTIONS} not found.")
        sys.exit(1)
    questions = load_jsonl(SOURCE_QUESTIONS)
    new_questions = []
    for entry in questions:
        new_entry = json.loads(json.dumps(entry))
        new_entry["id"] = remap_id(entry["id"])
        new_questions.append(new_entry)
    save_jsonl(OUT_QUESTIONS, new_questions)

    print(f"\nDone. Translated {total_values_translated} non-English parameter value(s) total.")
    print(f"Wrote {out_result_path}")
    print(f"Wrote {OUT_ANSWERS}")
    print(f"Wrote {OUT_QUESTIONS}")
    print()
    print("Next steps:")
    print("  python register_category.py simple_python_hi_post")
    print(f"  bfcl evaluate --model {args.model} --test-category simple_python_hi_post")
    print("  (no `bfcl generate` needed -- the result file already exists)")


if __name__ == "__main__":
    main()
