"""
build_pre_variant.py (generalized)

Builds MLCL's "PRE" (Pre-Translation) baseline for any language --
back-translates each query to English using the SAME model that will
do the tool-calling, per MLCL's protocol (Appendix A.3.2).

USAGE (run from inside berkeley-function-call-leaderboard, AFTER
remap_ids.py has already been run for the language in question):
    python build_pre_variant.py --lang hi --model gpt-4o-mini-2024-07-18
    python build_pre_variant.py --lang ta --model gpt-4o-mini-2024-07-18
"""

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

LANG_NAMES = {"hi": "Hindi", "ta": "Tamil"}


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
    return f"{prefix}_pre_{num}"


import zlib


def looks_degenerate(text, source_text):
    """Catches runaway repetition-loop failures using compression ratio --
    genuine repeated-pattern garbage compresses extremely well (ratio
    below ~0.1), while normal English text does not (ratio typically
    0.8-1.1 for short sentences). Validated against real examples: this
    cleanly separates known-good translations (ratio 0.81-1.09) from
    known-bad repetition garbage (ratio 0.025) with a huge margin, unlike
    character-frequency thresholds which false-positive on ordinary
    English sentences."""
    if not text:
        return True
    if len(text) > max(300, len(source_text) * 5):
        return True
    if len(text) > 50:
        compressed_len = len(zlib.compress(text.encode("utf-8")))
        original_len = len(text.encode("utf-8"))
        if compressed_len / original_len < 0.5:
            return True
    return False


def back_translate(client, model, text, lang_name):
    system_prompt = (
        f"Translate the following {lang_name} text into natural English. "
        "CRITICAL: Do NOT solve any problem, compute any answer, or add any information "
        "not present in the original text -- even if it looks like a math or logic problem "
        "and the answer seems obvious. Your only job is translation.\n"
        "Output ONLY the English translation, nothing else -- no quotes, no notes."
    )

    def call(temperature):
        resp = client.chat.completions.create(
            model=model,
            temperature=temperature,
            max_tokens=100,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
        )
        return resp.choices[0].message.content.strip()

    result = call(temperature=0)
    if looks_degenerate(result, text):
        # temperature=0 is deterministic, so retrying identically would just
        # reproduce the same failure -- nudge temperature up to escape the loop.
        result = call(temperature=0.3)
        if looks_degenerate(result, text):
            raise RuntimeError(
                f"Degenerate/repetitive output persisted after retry for input: {text[:80]}..."
            )
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", required=True, choices=["hi", "ta"])
    parser.add_argument(
        "--model", default="gpt-4o-mini-2024-07-18",
        help="Model used for BOTH back-translation and (later) tool-calling -- keep these the same per MLCL's protocol.",
    )
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    lang_name = LANG_NAMES[args.lang]
    source_questions = Path(f"bfcl_eval/data/BFCL_v4_simple_python_{args.lang}.json")
    source_answers = Path(f"bfcl_eval/data/possible_answer/BFCL_v4_simple_python_{args.lang}.json")
    out_questions = Path(f"bfcl_eval/data/BFCL_v4_simple_python_{args.lang}_pre.json")
    out_answers = Path(f"bfcl_eval/data/possible_answer/BFCL_v4_simple_python_{args.lang}_pre.json")

    if not source_questions.exists():
        print(f"ERROR: {source_questions} not found. Run remap_ids.py for --lang {args.lang} first.")
        sys.exit(1)

    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found. Run this from the berkeley-function-call-leaderboard folder.")
        sys.exit(1)
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=30.0, max_retries=2)

    questions = load_jsonl(source_questions)
    answers = load_jsonl(source_answers)
    if args.limit:
        questions = questions[: args.limit]
        keep_ids = {q["id"] for q in questions}
        answers = [a for a in answers if a["id"] in keep_ids]

    done_ids = set()
    if out_questions.exists():
        for entry in load_jsonl(out_questions):
            done_ids.add(entry["id"])

    print(f"Back-translating {len(questions)} {lang_name} questions to English using {args.model}...")
    if done_ids:
        print(f"({len(done_ids)} already done in a previous run, resuming)")

    with open(out_questions, "a", encoding="utf-8") as out_f:
        for i, entry in enumerate(questions):
            new_id = remap_id(entry["id"])
            if new_id in done_ids:
                continue

            source_text = entry["question"][0][0]["content"]
            try:
                english_text = back_translate(client, args.model, source_text, lang_name)
            except Exception as e:
                print(f"\nERROR on {entry['id']}: {e}")
                print("Re-run this same command to resume from here.")
                sys.exit(1)

            new_entry = json.loads(json.dumps(entry))
            new_entry["id"] = new_id
            new_entry["question"][0][0]["content"] = english_text
            new_entry[f"question_{args.lang}"] = source_text

            out_f.write(json.dumps(new_entry, ensure_ascii=False) + "\n")
            out_f.flush()
            print(f"  [{i + 1}/{len(questions)}] {entry['id']} -> {new_id}")
            print(f"     {args.lang.upper()}: {source_text}")
            print(f"     EN: {english_text}")

    new_answers = []
    for entry in answers:
        new_entry = json.loads(json.dumps(entry))
        new_entry["id"] = remap_id(entry["id"])
        new_answers.append(new_entry)
    save_jsonl(out_answers, new_answers)

    out_category = f"simple_python_{args.lang}_pre"
    print(f"\nWrote questions to {out_questions}")
    print(f"Wrote ground truth to {out_answers}")
    print()
    print("Next steps:")
    print(f"  python register_category.py {out_category}")
    print(f"  bfcl generate --model {args.model}-FC --test-category {out_category} --num-threads 4")
    print(f"  bfcl evaluate --model {args.model}-FC --test-category {out_category}")


if __name__ == "__main__":
    main()
