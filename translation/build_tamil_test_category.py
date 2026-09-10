"""
build_tamil_test_category.py

Converts the resolved Tamil gold translations (data/reviews/tamil_final_resolved.jsonl)
into a new BFCL test category, "multiple_ta" -- same 200 items as the English
"multiple" category, same function schemas, same ground truth (translating the
query never changes the target tool call), just the user-facing question text
swapped to the reviewed Tamil.

IDs are deliberately NOT reused verbatim from English ("multiple_0", ...) --
they're rewritten as "multiple_ta_0" etc. Found the hard way (real pipeline-check
run on the cluster, 2026-09-10): BFCL's own generate-resume logic builds one flat
"already done" id list across every category in a run and filters purely by id
string, with no per-category check. Reusing identical ids across "multiple" and
"multiple_ta" made it silently treat Tamil items as already-generated the moment
the English ones existed, skipping Tamil entirely with no error. Distinct ids
per category side-steps this; original_id is kept in each entry for traceability
back to the shared English base_id / ground truth.

This is purely a read of already-finalized data (tamil_final_resolved.jsonl) --
does not touch Cycle 1/Cycle 2 raw files or re-derive anything. Output is a new,
separate category, so the original English "multiple" category is untouched.

USAGE (run from inside berkeley-function-call-leaderboard):
    python translation/build_tamil_test_category.py
"""

import json
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

    en_answers = {e["id"]: e for e in load_jsonl(EN_ANSWER_PATH)}

    out_entries = []
    out_answers = []
    for base_id, en_entry in sorted(en_entries.items(), key=lambda kv: int(kv[0].split("_")[1])):
        new_id = base_id.replace("multiple_", "multiple_ta_")
        tamil_text = tamil_gold[base_id]["final_text"]

        new_entry = dict(en_entry)  # keep "function" schema and structure identical
        new_entry["id"] = new_id
        new_entry["original_id"] = base_id  # traceability back to the shared English base_id
        # question is [[{"role": "user", "content": ...}]] -- single turn, single message
        new_entry["question"] = [
            [dict(msg, content=tamil_text) if msg["role"] == "user" else dict(msg) for msg in turn]
            for turn in en_entry["question"]
        ]
        out_entries.append(new_entry)

        # Ground truth is identical to English -- translation is meaning-preserving,
        # the target tool call never changes (see Indic_ToolCalling_Project_Plan.md sec. 7).
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

    # Sanity check: reload and confirm ids are distinct from English, and text actually changed language.
    check = load_jsonl(OUT_PROMPT_PATH)
    assert len(check) == 200
    assert {e["id"] for e in check} == {bid.replace("multiple_", "multiple_ta_") for bid in en_entries}
    assert not ({e["id"] for e in check} & set(en_entries)), "Tamil ids must not collide with English ids"
    sample = check[0]["question"][0][0]["content"]
    print(f"Sample ({check[0]['id']}, original {check[0]['original_id']}) Tamil question: {sample}")


if __name__ == "__main__":
    main()
