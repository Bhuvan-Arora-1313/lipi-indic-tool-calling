"""
build_gujarati_test_category.py

Converts the resolved Gujarati gold translations (data/reviews/gujarati_final_resolved.jsonl)
into a new BFCL test category, "multiple_gu" -- same 200 items as the English
"multiple" category, same function schemas, same ground truth, just the
user-facing question text swapped to the reviewed Gujarati. Mirrors
build_tamil_test_category.py exactly -- see that script's docstring for
the id-collision resume-bug this avoids by rewriting ids to "multiple_gu_N".

USAGE (run from inside berkeley-function-call-leaderboard):
    python translation/build_gujarati_test_category.py
"""

import json
from pathlib import Path

EN_PROMPT_PATH = Path("bfcl_eval/data/BFCL_v4_multiple.json")
EN_ANSWER_PATH = Path("bfcl_eval/data/possible_answer/BFCL_v4_multiple.json")
GUJARATI_GOLD_PATH = Path("data/reviews/gujarati_final_resolved.jsonl")

OUT_PROMPT_PATH = Path("bfcl_eval/data/BFCL_v4_multiple_gu.json")
OUT_ANSWER_PATH = Path("bfcl_eval/data/possible_answer/BFCL_v4_multiple_gu.json")


def load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main():
    en_entries = {e["id"]: e for e in load_jsonl(EN_PROMPT_PATH)}
    gujarati_gold = {e["base_id"]: e for e in load_jsonl(GUJARATI_GOLD_PATH)}

    missing = set(en_entries) - set(gujarati_gold)
    if missing:
        raise SystemExit(f"Gujarati gold data is missing {len(missing)} ids, e.g. {sorted(missing)[:5]} -- aborting.")

    en_answers = {e["id"]: e for e in load_jsonl(EN_ANSWER_PATH)}

    out_entries = []
    out_answers = []
    for base_id, en_entry in sorted(en_entries.items(), key=lambda kv: int(kv[0].split("_")[1])):
        new_id = base_id.replace("multiple_", "multiple_gu_")
        gujarati_text = gujarati_gold[base_id]["final_text"]

        new_entry = dict(en_entry)
        new_entry["id"] = new_id
        new_entry["original_id"] = base_id
        new_entry["question"] = [
            [dict(msg, content=gujarati_text) if msg["role"] == "user" else dict(msg) for msg in turn]
            for turn in en_entry["question"]
        ]
        out_entries.append(new_entry)

        new_answer = dict(en_answers[base_id])
        new_answer["id"] = new_id
        out_answers.append(new_answer)

    OUT_PROMPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PROMPT_PATH, "w", encoding="utf-8") as f:
        for e in out_entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(f"Wrote {OUT_PROMPT_PATH} ({len(out_entries)} rows)")

    OUT_ANSWER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_ANSWER_PATH, "w", encoding="utf-8") as f:
        for a in out_answers:
            f.write(json.dumps(a, ensure_ascii=False) + "\n")
    print(f"Wrote {OUT_ANSWER_PATH} ({len(out_answers)} rows, ids rewritten to match)")

    check = load_jsonl(OUT_PROMPT_PATH)
    assert len(check) == 200
    assert {e["id"] for e in check} == {bid.replace("multiple_", "multiple_gu_") for bid in en_entries}
    assert not ({e["id"] for e in check} & set(en_entries)), "Gujarati ids must not collide with English ids"
    sample = check[0]["question"][0][0]["content"]
    print(f"Sample ({check[0]['id']}, original {check[0]['original_id']}) Gujarati question: {sample}")


if __name__ == "__main__":
    main()
