"""
remap_ids.py

Fixes a BFCL bug where results get saved by parsing each entry's ID
(e.g. "simple_python_0" -> category "simple_python"), ignoring the
--test-category argument entirely. Since our translated files reused
the original English IDs, Hindi/Tamil/English runs were all colliding
and overwriting each other in the same result file.

This renames every ID in both the translated question file and its
matching ground-truth file from "simple_python_N" to
"simple_python_hi_N" (or "_ta_N"), so BFCL correctly routes each
language to its own separate result file.

USAGE (run from inside berkeley-function-call-leaderboard):
    python remap_ids.py
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

FILES_TO_FIX = [
    ("hi", Path("bfcl_eval/data/BFCL_v4_simple_python_hi.json")),
    ("hi", Path("bfcl_eval/data/possible_answer/BFCL_v4_simple_python_hi.json")),
    ("ta", Path("bfcl_eval/data/BFCL_v4_simple_python_ta.json")),
    ("ta", Path("bfcl_eval/data/possible_answer/BFCL_v4_simple_python_ta.json")),
]


def remap_id(old_id, lang):
    # "simple_python_0" -> "simple_python_hi_0"
    prefix, num = old_id.rsplit("_", 1)
    return f"{prefix}_{lang}_{num}"


def fix_file(lang, path):
    if not path.exists():
        print(f"  SKIP: {path} not found")
        return

    backup_path = path.with_suffix(path.suffix + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(path, backup_path)

    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    already_done = entries and f"simple_python_{lang}_" in entries[0]["id"]
    if already_done:
        print(f"  {path}: already remapped, skipping")
        backup_path.unlink()  # remove the unnecessary backup we just made
        return

    for entry in entries:
        entry["id"] = remap_id(entry["id"], lang)

    with open(path, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"  Fixed {len(entries)} IDs in {path} (backed up to {backup_path.name})")


def main():
    for lang, path in FILES_TO_FIX:
        fix_file(lang, path)
    print("\nDone. IDs now look like 'simple_python_hi_0' and 'simple_python_ta_0'.")
    print("This means your previous generate runs for these categories are no longer valid")
    print("(they were saved under colliding IDs) -- you'll need to re-run generate for")
    print("simple_python_hi and simple_python_ta after this. Same for your English baseline,")
    print("since its result file may have been overwritten by the Hindi/Tamil runs.")


if __name__ == "__main__":
    main()
