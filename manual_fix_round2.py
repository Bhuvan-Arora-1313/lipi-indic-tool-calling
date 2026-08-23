"""
manual_fix_round2.py

Manually applies Tamil translations for two examples that repeatedly
triggered a repetition-loop failure via the API (both attempts at
temperature 0 and 0.3 failed) -- both are finance/dollar-amount
questions, a pattern worth noting rather than continuing to burn API
credits retrying the same failure.

USAGE (run from inside berkeley-function-call-leaderboard):
    python manual_fix_round2.py
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

TA_FILE = Path("bfcl_eval/data/BFCL_v4_simple_python_ta.json")

FIXES = {
    "simple_python_ta_128": (
        "100 மில்லியன் நிலுவை பங்குகளையும் மொத்தம் 50 மில்லியன் டாலர் டிவிடெண்ட் "
        "செலுத்தும் ஒரு நிறுவனத்தின் ஒரு பங்குக்கான காலாண்டு டிவிடெண்ட் எவ்வளவு?"
    ),
    "simple_python_ta_135": (
        "ஒரு பங்கு $20க்கு வாங்கி, $25க்கு விற்று, $2 டிவிடெண்ட் பெற்றால், "
        "அதன் முதலீட்டு வருமானத்தை கணக்கிடவும்."
    ),
}


def main():
    if not TA_FILE.exists():
        print(f"ERROR: {TA_FILE} not found.")
        return

    backup_path = TA_FILE.with_suffix(TA_FILE.suffix + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(TA_FILE, backup_path)
    print(f"Backed up {TA_FILE} -> {backup_path}")

    entries = []
    with open(TA_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    applied = 0
    for ex in entries:
        if ex["id"] in FIXES:
            old = ex["question"][0][0]["content"]
            new = FIXES[ex["id"]]
            ex["question"][0][0]["content"] = new
            print(f"\n  {ex['id']}")
            print(f"     OLD: {old[:100]}...")
            print(f"     NEW: {new}")
            applied += 1

    with open(TA_FILE, "w", encoding="utf-8") as f:
        for ex in entries:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    print(f"\nApplied {applied} manual fix(es) to {TA_FILE}")
    print("NOTE: these are my own translations, not run through the automated pipeline --")
    print("worth a native-speaker spot-check given the unusual circumstance, same as other manual fixes.")


if __name__ == "__main__":
    main()
