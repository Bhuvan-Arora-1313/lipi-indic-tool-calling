"""
check_perturbation_number_drift.py

Read-only QA pass over data/perturbations/en_multiple_perturbations.jsonl
(the raw PARA/SYNO generation output -- never modified by this script).

Compares the SET of numbers in each perturbed text against the SET of
numbers in its source_text. Order-independent by design: paraphrasing
routinely reorders numbers while preserving meaning (e.g. "sides 5, 4, 3"
-> "sides 3, 4, 5" for a triangle, where order doesn't matter), and that is
not a defect. This only flags a genuine meaning change -- a number dropped,
added, or substituted for a different one.

Writes findings to a SEPARATE file (never touches the raw generation file),
per the data provenance policy in PROJECT_MANIFEST.md.

USAGE (run from inside berkeley-function-call-leaderboard):
    python translation/check_perturbation_number_drift.py
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

RAW_PATH = Path("data/perturbations/en_multiple_perturbations.jsonl")
QA_OUTPUT_PATH = Path("data/perturbations/en_multiple_perturbations_qa.jsonl")
CHECKER_VERSION = "number_set_v1"

# Same pattern as the (fixed) number extractor in fix_number_matching.py
# (see archive/pilot-hindi-tamil-simple-python branch, LOG.md 2026-08-23):
# rstrip only, never strip a leading "-" (that silently deletes negative
# signs), and skip digit runs glued to a preceding letter (identifiers
# like "B1004" aren't quantities).
NUMBER_PATTERN = re.compile(r"-?\d[\d,]*\.?\d*")


def extract_numbers(text):
    numbers = set()
    for m in NUMBER_PATTERN.finditer(text):
        start = m.start()
        if start > 0 and text[start - 1].isalpha():
            continue
        cleaned = m.group().replace(",", "").rstrip(".")
        if not cleaned or cleaned == "-":
            continue
        try:
            numbers.add(float(cleaned))
        except ValueError:
            continue
    return numbers


def load_jsonl(path):
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def main():
    if not RAW_PATH.exists():
        print(f"ERROR: {RAW_PATH} not found. Run generate_perturbations.py first.")
        return

    entries = load_jsonl(RAW_PATH)
    qa_rows = []
    n_mismatch = 0

    for entry in entries:
        if entry["perturbation_type"] == "NO":
            continue  # identical to source by construction, nothing to check

        source_numbers = extract_numbers(entry["source_text"])
        perturbed_numbers = extract_numbers(entry["text"])
        missing = sorted(source_numbers - perturbed_numbers)
        added = sorted(perturbed_numbers - source_numbers)
        flag = "number_mismatch" if (missing or added) else "ok"
        if flag == "number_mismatch":
            n_mismatch += 1

        qa_rows.append({
            "base_id": entry["base_id"],
            "perturbation_type": entry["perturbation_type"],
            "flag": flag,
            "source_numbers": sorted(source_numbers),
            "perturbed_numbers": sorted(perturbed_numbers),
            "missing_numbers": missing,
            "added_numbers": added,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "checker_version": CHECKER_VERSION,
        })

    with open(QA_OUTPUT_PATH, "w", encoding="utf-8") as f:
        for row in qa_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Checked {len(qa_rows)} PARA/SYNO rows.")
    print(f"Flagged: {n_mismatch} ({n_mismatch / len(qa_rows) * 100:.1f}%)" if qa_rows else "Flagged: 0")
    print(f"Wrote {QA_OUTPUT_PATH}")
    if n_mismatch:
        print("\nFlagged rows:")
        for row in qa_rows:
            if row["flag"] == "number_mismatch":
                print(f"  {row['base_id']} [{row['perturbation_type']}]: "
                      f"missing={row['missing_numbers']} added={row['added_numbers']}")


if __name__ == "__main__":
    main()
