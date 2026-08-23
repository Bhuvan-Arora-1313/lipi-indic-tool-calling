"""
check_number_drift.py

Compares the numbers present in the ORIGINAL Hindi/Tamil query against
the numbers present in its English translation (from your existing
build_pre_variant.py output, which already saves both side by side).
No ground truth needed -- this is exactly the self-contained check you
described: does translation silently change, drop, or add a number?

Handles:
  - Western digits (0-9)
  - Devanagari digits (Hindi: ०-९)
  - Thousand separators (commas) and decimals

Does NOT yet handle spelled-out number words ("fifty", "पचास") --
starting with digit-based detection first to measure the scale of the
problem before deciding if word-based extraction is worth adding.

USAGE (run from inside berkeley-function-call-leaderboard):
    python check_number_drift.py --lang hi
    python check_number_drift.py --lang ta
"""

import argparse
import json
import re
from pathlib import Path

DEVANAGARI_DIGITS = "०१२३४५६७८९"
DEVANAGARI_TO_WESTERN = {d: str(i) for i, d in enumerate(DEVANAGARI_DIGITS)}

NUMBER_PATTERN = re.compile(r"-?\d[\d,]*\.?\d*")


def normalize_digits(text):
    return "".join(DEVANAGARI_TO_WESTERN.get(c, c) for c in text)


def extract_numbers(text):
    normalized = normalize_digits(text)
    numbers = []
    for match in NUMBER_PATTERN.findall(normalized):
        cleaned = match.replace(",", "").strip("-.")
        if not cleaned:
            continue
        try:
            value = float(cleaned) if "." in cleaned else int(cleaned)
            numbers.append(value)
        except ValueError:
            continue
    return numbers


def numbers_equivalent(a, b):
    try:
        return float(a) == float(b)
    except (ValueError, TypeError):
        return a == b


def compare(source_numbers, translated_numbers):
    """Returns (missing, added) -- numbers present in source but not in
    translation, and numbers present in translation but not in source."""
    remaining_translated = list(translated_numbers)
    missing = []
    for n in source_numbers:
        match_idx = next((i for i, t in enumerate(remaining_translated) if numbers_equivalent(n, t)), None)
        if match_idx is not None:
            remaining_translated.pop(match_idx)
        else:
            missing.append(n)
    added = remaining_translated
    return missing, added


def load_jsonl(path):
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", required=True, choices=["hi", "ta"])
    args = parser.parse_args()

    path = Path(f"bfcl_eval/data/BFCL_v4_simple_python_{args.lang}_pre.json")
    if not path.exists():
        print(f"ERROR: {path} not found.")
        return

    entries = load_jsonl(path)
    source_field = f"question_{args.lang}"

    n_total = 0
    n_no_numbers = 0
    n_match = 0
    n_drift = 0
    drifted_examples = []

    for entry in entries:
        source_text = entry.get(source_field)
        translated_text = entry["question"][0][0]["content"]
        if not source_text:
            continue
        n_total += 1

        source_numbers = extract_numbers(source_text)
        translated_numbers = extract_numbers(translated_text)

        if not source_numbers and not translated_numbers:
            n_no_numbers += 1
            continue

        missing, added = compare(source_numbers, translated_numbers)
        if not missing and not added:
            n_match += 1
        else:
            n_drift += 1
            drifted_examples.append((entry["id"], source_text, translated_text, missing, added))

    print(f"Total examples checked: {n_total}")
    print(f"  No numbers present in either version: {n_no_numbers}")
    print(f"  Numbers match exactly: {n_match}")
    print(f"  DRIFT detected (numbers differ): {n_drift}")
    print()

    if drifted_examples:
        print(f"Showing up to 10 of {len(drifted_examples)} drifted examples:\n")
        for ex_id, src, trans, missing, added in drifted_examples[:10]:
            print(f"  {ex_id}")
            print(f"    Source ({args.lang}): {src}")
            print(f"    English: {trans}")
            if missing:
                print(f"    MISSING from translation: {missing}")
            if added:
                print(f"    ADDED in translation (not in source): {added}")
            print()


if __name__ == "__main__":
    main()
