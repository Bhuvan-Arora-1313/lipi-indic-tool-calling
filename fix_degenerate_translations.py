"""
fix_degenerate_translations.py

Scans an already-completed PRE-translation file (built by
build_pre_variant.py) for entries with degenerate/repetitive output
(the "wall of repeated characters" failure) and re-translates ONLY
those specific entries, leaving the other ~398 untouched. Much cheaper
and faster than redoing the whole file when only a couple of entries
are affected.

USAGE (run from inside berkeley-function-call-leaderboard):
    python fix_degenerate_translations.py --lang ta
    python fix_degenerate_translations.py --lang hi
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


def back_translate(client, model, text, lang_name, temperature):
    system_prompt = (
        f"Translate the following {lang_name} text into natural English. "
        "CRITICAL: Do NOT solve any problem, compute any answer, or add any information "
        "not present in the original text -- even if it looks like a math or logic problem "
        "and the answer seems obvious. Your only job is translation.\n"
        "Output ONLY the English translation, nothing else -- no quotes, no notes."
    )
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", required=True, choices=["hi", "ta"])
    parser.add_argument("--model", default="gpt-4o-mini-2024-07-18")
    args = parser.parse_args()

    lang_name = LANG_NAMES[args.lang]
    path = Path(f"bfcl_eval/data/BFCL_v4_simple_python_{args.lang}_pre.json")

    if not path.exists():
        print(f"ERROR: {path} not found.")
        sys.exit(1)

    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found. Run this from the berkeley-function-call-leaderboard folder.")
        sys.exit(1)
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=30.0, max_retries=2)

    entries = load_jsonl(path)
    source_field = f"question_{args.lang}"

    print(f"Scanning {len(entries)} entries in {path} for degenerate output...")

    broken = []
    for entry in entries:
        translated = entry["question"][0][0]["content"]
        source_text = entry.get(source_field, "")
        if looks_degenerate(translated, source_text):
            broken.append(entry)

    if not broken:
        print("No degenerate entries found. Nothing to fix.")
        return

    print(f"Found {len(broken)} degenerate entr{'y' if len(broken) == 1 else 'ies'}: {[e['id'] for e in broken]}")
    print()

    for entry in broken:
        source_text = entry[source_field]
        print(f"  Fixing {entry['id']}...")
        print(f"    Source: {source_text}")
        print(f"    Originally-flagged text was: {entry['question'][0][0]['content']!r}")

        fixed_text = None
        for attempt, temp in enumerate([0.3, 0.7], start=1):
            try:
                candidate = back_translate(client, args.model, source_text, lang_name, temperature=temp)
            except Exception as e:
                print(f"    ERROR on attempt {attempt}: {e}")
                continue
            if not looks_degenerate(candidate, source_text):
                fixed_text = candidate
                break
            print(f"    Attempt at temperature={temp} REJECTED. Candidate was:")
            print(f"      {candidate!r}")

        if fixed_text is None:
            print(f"    COULD NOT FIX {entry['id']} automatically after multiple attempts.")
            print(f"    This one needs manual attention -- paste this back to Claude.")
            continue

        entry["question"][0][0]["content"] = fixed_text
        print(f"    Fixed: {fixed_text}")
        print()

    save_jsonl(path, entries)
    print(f"Saved updated {path}")
    print()
    print("Since only the question TEXT changed (not any IDs), you don't need to rebuild")
    print("the ground-truth file -- just re-run generate/evaluate for this category:")
    print(f"  bfcl generate --model {args.model}-FC --test-category simple_python_{args.lang}_pre --num-threads 4")
    print(f"  bfcl evaluate --model {args.model}-FC --test-category simple_python_{args.lang}_pre")


if __name__ == "__main__":
    main()
