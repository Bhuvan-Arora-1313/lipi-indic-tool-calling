"""
build_parasyno_test_categories.py

Converts the resolved English PARA/SYNO perturbations
(data/reviews/parasyno_final_resolved.jsonl) into two new BFCL test
categories, "multiple_para" and "multiple_syno" -- same 200 items each
as the base English "multiple" category, same function schemas, same
ground truth (a paraphrase or synonym swap never changes the target
tool call), just the user-facing question text swapped to the reviewed
PARA/SYNO variant. Kept as two separate categories (not merged) so
PARA-robustness and SYNO-robustness can be reported independently,
matching how the project already treats them as separate experimental
conditions throughout (see Indic_ToolCalling_Project_Plan.md).

IDs are rewritten as "multiple_para_N" / "multiple_syno_N" (not reused
from English's "multiple_N"), mirroring build_tamil_test_category.py /
build_hindi_test_category.py -- avoids the same id-collision resume-bug
those scripts document (BFCL's generate-resume logic filters by a flat
cross-category id list with no per-category check).

USAGE (run from inside berkeley-function-call-leaderboard):
    python translation/build_parasyno_test_categories.py
"""

import json
from pathlib import Path

EN_PROMPT_PATH = Path("bfcl_eval/data/BFCL_v4_multiple.json")
EN_ANSWER_PATH = Path("bfcl_eval/data/possible_answer/BFCL_v4_multiple.json")
PARASYNO_GOLD_PATH = Path("data/reviews/parasyno_final_resolved.jsonl")


def load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def build_category(ptype, en_entries, en_answers, gold_by_key):
    out_prompt_path = Path(f"bfcl_eval/data/BFCL_v4_multiple_{ptype.lower()}.json")
    out_answer_path = Path(f"bfcl_eval/data/possible_answer/BFCL_v4_multiple_{ptype.lower()}.json")

    out_entries = []
    out_answers = []
    for base_id, en_entry in sorted(en_entries.items(), key=lambda kv: int(kv[0].split("_")[1])):
        key = (base_id, ptype)
        if key not in gold_by_key:
            raise SystemExit(f"Missing {ptype} gold data for {base_id} -- aborting.")
        new_id = base_id.replace("multiple_", f"multiple_{ptype.lower()}_")
        text = gold_by_key[key]["final_text"]

        new_entry = dict(en_entry)
        new_entry["id"] = new_id
        new_entry["original_id"] = base_id
        new_entry["question"] = [
            [dict(msg, content=text) if msg["role"] == "user" else dict(msg) for msg in turn]
            for turn in en_entry["question"]
        ]
        out_entries.append(new_entry)

        new_answer = dict(en_answers[base_id])
        new_answer["id"] = new_id
        out_answers.append(new_answer)

    out_prompt_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_prompt_path, "w", encoding="utf-8") as f:
        for e in out_entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(f"Wrote {out_prompt_path} ({len(out_entries)} rows)")

    out_answer_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_answer_path, "w", encoding="utf-8") as f:
        for a in out_answers:
            f.write(json.dumps(a, ensure_ascii=False) + "\n")
    print(f"Wrote {out_answer_path} ({len(out_answers)} rows, ids rewritten to match)")

    check = load_jsonl(out_prompt_path)
    assert len(check) == 200
    assert {e["id"] for e in check} == {bid.replace("multiple_", f"multiple_{ptype.lower()}_") for bid in en_entries}
    assert not ({e["id"] for e in check} & set(en_entries)), f"{ptype} ids must not collide with English ids"
    sample = check[0]["question"][0][0]["content"]
    print(f"Sample ({check[0]['id']}, original {check[0]['original_id']}) {ptype} question: {sample}")
    print()


def main():
    en_entries = {e["id"]: e for e in load_jsonl(EN_PROMPT_PATH)}
    en_answers = {e["id"]: e for e in load_jsonl(EN_ANSWER_PATH)}
    gold_rows = load_jsonl(PARASYNO_GOLD_PATH)
    gold_by_key = {(r["base_id"], r["perturbation_type"]): r for r in gold_rows}

    for ptype in ("PARA", "SYNO"):
        build_category(ptype, en_entries, en_answers, gold_by_key)


if __name__ == "__main__":
    main()
