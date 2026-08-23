"""
manual_fixes.py

Applies a small set of precise, pre-verified fixes to specific examples
in the translated Hindi/Tamil files -- used here to fix two issues that
came out of the previous automated fix pass:

1. Three Hindi examples (simple_python_2, _105, _132) lost their
   Devanagari numerals during the strict re-translation. Fixed here
   with deterministic digit conversion (and correct Indian lakh/crore
   grouping for the large currency figures in #132) rather than another
   LLM call, since the goal is precision, and code is more reliable
   than a model for pure digit/grouping conversion.

2. One Tamil example (simple_python_295) had its artist name ("Queen")
   dropped entirely during the previous fix, rather than just having
   its redundant phrasing cleaned up. Fixed here with a hand-written
   corrected translation.

This script is intentionally NOT a general-purpose tool -- the fixes
are hardcoded because each one was individually verified. Back up your
files before running, same as always (the script does this
automatically).

USAGE (run from inside berkeley-function-call-leaderboard):
    python manual_fixes.py
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

HI_FILE = Path("bfcl_eval/data/BFCL_v4_simple_python_hi.json")
TA_FILE = Path("bfcl_eval/data/BFCL_v4_simple_python_ta.json")

# Pre-verified corrected translations, keyed by id
HI_FIXES = {
    "simple_python_2": "दूसरी दो भुजाओं की लंबाई ४ और ५ होने पर समकोण त्रिभुज की कर्णिका की गणना करें।",
    "simple_python_105": "३ की घात ४ की शक्ति की गणना करें।",
    "simple_python_132": (
        "कंपनी की इक्विटी पर रिटर्न की गणना करें, जब इसकी शुद्ध आय $२०,००,०००, "
        "शेयरधारकों की इक्विटी $१,००,००,०००, और भुगतान किए गए लाभांश $२,००,००० हैं।"
    ),
}

TA_FIXES = {
    "simple_python_295": "குவீன் பாடிய 'Bohemian Rhapsody' பாடலின் வரிகளை கண்டுபிடிக்கவும்.",
}


def apply_fixes(file_path, fixes):
    if not fixes:
        return
    if not file_path.exists():
        print(f"  SKIP: {file_path} not found")
        return

    backup_path = file_path.with_suffix(file_path.suffix + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(file_path, backup_path)
    print(f"Backed up {file_path} -> {backup_path}")

    examples = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                examples.append(json.loads(line))

    applied = 0
    for ex in examples:
        if ex["id"] in fixes:
            old = ex["question"][0][0]["content"]
            new = fixes[ex["id"]]
            ex["question"][0][0]["content"] = new
            print(f"\n  {ex['id']}")
            print(f"     OLD: {old}")
            print(f"     NEW: {new}")
            applied += 1

    with open(file_path, "w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    print(f"\nApplied {applied} fix(es) to {file_path}")


def main():
    print("Fixing Hindi numeral regression...")
    apply_fixes(HI_FILE, HI_FIXES)
    print("\nFixing Tamil dropped-artist issue...")
    apply_fixes(TA_FILE, TA_FIXES)
    print("\nDone.")


if __name__ == "__main__":
    main()
