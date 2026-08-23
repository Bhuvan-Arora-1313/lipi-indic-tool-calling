"""
scan_base_files.py

Scans the BASE translated files (BFCL_v4_simple_python_hi.json /
_ta.json -- the ones every other experiment in this project was built
from) for the repetition-garbage failure mode, using the same
compression-ratio detector validated earlier on the PRE back-translation
data. This checks whether the corruption found in one PRE example
(ta_pre_135) traces back to the base dataset itself, which would affect
every downstream experiment (NT, PT, POST, and all typefix variants),
not just PRE.

USAGE (run from inside berkeley-function-call-leaderboard):
    python scan_base_files.py
"""

import json
import zlib
from pathlib import Path


def looks_degenerate(text, source_text):
    """Same validated check used in build_pre_variant.py /
    fix_degenerate_translations.py: genuine repetition garbage
    compresses extremely well (ratio ~0.02-0.1), normal text does not
    (ratio ~0.8-1.1 for short sentences)."""
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


def scan_file(path, lang_label):
    if not path.exists():
        print(f"  {path} not found, skipping.")
        return []

    entries = load_jsonl(path)
    flagged = []
    for entry in entries:
        text = entry["question"][0][0]["content"]
        source_text = entry.get("question_en", "")
        if looks_degenerate(text, source_text):
            flagged.append(entry)

    print(f"\n{lang_label}: scanned {len(entries)} entries, found {len(flagged)} degenerate.")
    for entry in flagged:
        text = entry["question"][0][0]["content"]
        print(f"  {entry['id']}")
        print(f"    EN source: {entry.get('question_en', '(not found)')}")
        print(f"    Flagged text (truncated to 200 chars): {text[:200]}...")
    return flagged


def main():
    hi_path = Path("bfcl_eval/data/BFCL_v4_simple_python_hi.json")
    ta_path = Path("bfcl_eval/data/BFCL_v4_simple_python_ta.json")

    hi_flagged = scan_file(hi_path, "Hindi base file")
    ta_flagged = scan_file(ta_path, "Tamil base file")

    total = len(hi_flagged) + len(ta_flagged)
    print(f"\n{'='*50}")
    if total == 0:
        print("No degenerate entries found in either base file. Clean.")
    else:
        print(f"TOTAL: {total} degenerate entries found across both base files.")
        print("These affect every downstream experiment built from these IDs")
        print("(NT, PT, POST, PT+POST, and all typefix variants) -- not just PRE.")


if __name__ == "__main__":
    main()
