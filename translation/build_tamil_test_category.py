"""
build_tamil_test_category.py

Converts the resolved Tamil gold translations (data/reviews/tamil_final_resolved.jsonl)
into a new BFCL test category, "multiple_ta" -- same 200 items as the English
"multiple" category, same function schemas, same ground truth (translating the
query never changes the target tool call), just the user-facing question text
swapped to the reviewed Tamil.

This is purely a read of already-finalized data (tamil_final_resolved.jsonl) --
does not touch Cycle 1/Cycle 2 raw files or re-derive anything. Output is a new,
separate category, so the original English "multiple" category is untouched.

USAGE (run from inside berkeley-function-call-leaderboard):
    python translation/build_tamil_test_category.py
"""

import json
import shutil
from pathlib import Path

EN_PROMPT_PATH = Path("bfcl_eval/data/BFCL_v4_multiple.json")
EN_ANSWER_PATH = Path("bfcl_eval/data/possible_answer/BFCL_v4_multiple.json")
TAMIL_GOLD_PATH = Path("data/reviews/tamil_final_resolved.jsonl")

OUT_PROMPT_PATH = Path("bfcl_eval/data/BFCL_v4_multiple_ta.json")
OUT_ANSWER_PATH = Path("bfcl_eval/data/possible_answer/BFCL_v4_multiple_ta.json")


def load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main():
    en_entries = {e["id"]: e for e in load_jsonl(EN_PROMPT_PATH)}
    tamil_gold = {e["base_id"]: e for e in load_jsonl(TAMIL_GOLD_PATH)}

    missing = set(en_entries) - set(tamil_gold)
    if missing:
        raise SystemExit(f"Tamil gold data is missing {len(missing)} ids, e.g. {sorted(missing)[:5]} -- aborting.")

    out_entries = []
    for base_id, en_entry in sorted(en_entries.items(), key=lambda kv: int(kv[0].split("_")[1])):
        tamil_text = tamil_gold[base_id]["final_text"]
        new_entry = dict(en_entry)  # keep "function" schema and structure identical
        # question is [[{"role": "user", "content": ...}]] -- single turn, single message
        new_entry["question"] = [
            [dict(msg, content=tamil_text) if msg["role"] == "user" else dict(msg) for msg in turn]
            for turn in en_entry["question"]
        ]
        out_entries.append(new_entry)

    OUT_PROMPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PROMPT_PATH, "w", encoding="utf-8") as f:
        for e in out_entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(f"Wrote {OUT_PROMPT_PATH} ({len(out_entries)} rows)")

    # Ground truth is identical to English -- translation is meaning-preserving,
    # the target tool call never changes (see Indic_ToolCalling_Project_Plan.md sec. 7).
    OUT_ANSWER_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(EN_ANSWER_PATH, OUT_ANSWER_PATH)
    print(f"Wrote {OUT_ANSWER_PATH} (copied unchanged from English -- same ground truth)")

    # Sanity check: reload and confirm ids match, and that text actually changed language.
    check = load_jsonl(OUT_PROMPT_PATH)
    assert len(check) == 200
    assert {e["id"] for e in check} == set(en_entries)
    sample = check[0]["question"][0][0]["content"]
    print(f"Sample (multiple_0) Tamil question: {sample}")


if __name__ == "__main__":
    main()
