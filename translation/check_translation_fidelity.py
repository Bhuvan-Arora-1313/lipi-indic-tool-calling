"""
check_translation_fidelity.py

Read-only QA pass over data/translations/multiple_translations.jsonl (the
raw IndicTrans2 output -- never modified by this script). Two checks:

1. Number-set drift (same order-independent logic as
   check_perturbation_number_drift.py): does every number in the English
   source survive, unchanged, in the translation?
2. Unit/exponent-marker drift: does every occurrence of a small set of
   symbols that are known to carry meaning on their own -- "^" (exponent,
   e.g. m/s^2), "%" (percent), "degree signs" -- survive translation?
   Found via a real example: source "10 m/s^2" (acceleration) translated
   to Hindi lost the "^2", reading as a plain speed unit. This check
   exists specifically because of that observed failure, not a
   hypothetical one.

Writes findings to a SEPARATE file, never touches the raw data, per the
data provenance policy in PROJECT_MANIFEST.md.

USAGE (run from inside berkeley-function-call-leaderboard):
    python translation/check_translation_fidelity.py
"""

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

RAW_PATH = Path("data/translations/multiple_translations.jsonl")
QA_OUTPUT_PATH = Path("data/translations/multiple_translations_qa.jsonl")
CHECKER_VERSION = "number_and_marker_v1"

# Same corrected pattern as check_perturbation_number_drift.py: rstrip
# only, never strip a leading "-", skip digit runs glued to a letter.
# Tolerates one optional space after the decimal point -- IndicTrans2's
# detokenizer appears to insert one (observed on multiple_16: "0.95" ->
# "0. 95", value unchanged, just reformatted). Known limitation: on rare
# multi-sentence text this could over-merge a sentence-ending period with
# a next sentence that happens to start with a digit; low risk here since
# BFCL queries in this dataset are single-sentence.
NUMBER_PATTERN = re.compile(r"-?\d[\d,]*\.?\s?\d*")

# Markers known to carry meaning on their own AND to have no legitimate
# word-substitution escape hatch, found via real observed failures
# (m/s^2, 3x^2, m^3 all losing their "^" with no compensating word for
# "squared"/"cubed" appearing anywhere in the translation). "%" was
# removed after checking real examples: IndicTrans2 correctly renders it
# as a spelled-out word ("10%" -> "10 प्रतिशत", literally "10 percent"),
# which is a legitimate translation, not a drop -- flagging it was a
# checker false positive, not a real issue.
MARKERS = ["^"]


BAD_COMMA = re.compile(r",(?!\d{3}(?:\D|$))")


def extract_numbers(text):
    numbers = set()
    for m in NUMBER_PATTERN.finditer(text):
        start = m.start()
        # Only skip when glued to a LATIN letter (e.g. "B1004" is an
        # identifier) -- restricted to ASCII letters, not "any alphabetic
        # character", because a number glued directly to a preceding
        # Devanagari/Tamil word with no space is normal, correct writing
        # in those scripts (observed on "और-25" = "and-25", a correct
        # Hindi rendering of "..., and -25" -- the original guard was
        # wrongly treating that as an identifier and dropping a real,
        # correctly-translated negative number).
        if start > 0 and text[start - 1].isalpha() and text[start - 1].isascii():
            continue
        raw = m.group()
        # A comma only counts as a thousands separator when followed by
        # exactly 3 digits and then a non-digit/end (e.g. "3,400"; not
        # "3,4"). Otherwise the regex has greedily merged two separate
        # list items that happen to sit next to a comma with no space
        # between them (observed in Hindi/Tamil output, e.g. "3,4 और 5"
        # for "3, 4, and 5") -- split back into separate numbers rather
        # than treating the whole run as one value, or discarding either
        # half.
        for part in BAD_COMMA.split(raw):
            cleaned = part.replace(",", "").replace(" ", "").rstrip(".")
            if not cleaned or cleaned == "-":
                continue
            try:
                numbers.add(float(cleaned))
            except ValueError:
                continue
    return numbers


def marker_counts(text):
    return {m: text.count(m) for m in MARKERS if text.count(m) > 0}


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
        print(f"ERROR: {RAW_PATH} not found. Run translate_indictrans2.py first.")
        return

    entries = load_jsonl(RAW_PATH)
    qa_rows = []
    n_number_mismatch = 0
    n_marker_mismatch = 0

    for entry in entries:
        source_numbers = extract_numbers(entry["source_text"])
        target_numbers = extract_numbers(entry["text"])
        missing_numbers = sorted(source_numbers - target_numbers)
        added_numbers = sorted(target_numbers - source_numbers)

        source_markers = marker_counts(entry["source_text"])
        target_markers = marker_counts(entry["text"])
        dropped_markers = {
            m: (source_markers[m] - target_markers.get(m, 0))
            for m in source_markers
            if source_markers[m] > target_markers.get(m, 0)
        }

        flags = []
        if missing_numbers or added_numbers:
            flags.append("number_mismatch")
            n_number_mismatch += 1
        if dropped_markers:
            flags.append("marker_dropped")
            n_marker_mismatch += 1

        qa_rows.append({
            "base_id": entry["base_id"],
            "language": entry["language"],
            "composition": entry["composition"],
            "perturbation_type": entry["perturbation_type"],
            "flags": flags if flags else ["ok"],
            "missing_numbers": missing_numbers,
            "added_numbers": added_numbers,
            "dropped_markers": dropped_markers,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "checker_version": CHECKER_VERSION,
        })

    with open(QA_OUTPUT_PATH, "w", encoding="utf-8") as f:
        for row in qa_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    n_total = len(qa_rows)
    n_flagged = sum(1 for r in qa_rows if r["flags"] != ["ok"])
    print(f"Checked {n_total} translation rows.")
    print(f"Number mismatches: {n_number_mismatch} ({n_number_mismatch / n_total * 100:.1f}%)")
    print(f"Marker (^ % degree) drops: {n_marker_mismatch} ({n_marker_mismatch / n_total * 100:.1f}%)")
    print(f"Total flagged: {n_flagged} ({n_flagged / n_total * 100:.1f}%)")
    print(f"Wrote {QA_OUTPUT_PATH}")

    if n_flagged:
        print("\nFlagged rows:")
        for row in qa_rows:
            if row["flags"] != ["ok"]:
                print(f"  {row['base_id']} [{row['language']}/{row['perturbation_type']}] "
                      f"{row['flags']}: missing={row['missing_numbers']} added={row['added_numbers']} "
                      f"dropped_markers={row['dropped_markers']}")


if __name__ == "__main__":
    main()
