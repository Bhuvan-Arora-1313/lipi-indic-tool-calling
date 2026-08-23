"""
check_regression.py

Compares a "before" score file against an "after" (fixed/variant) score
file for the same underlying examples, and reports exactly which
example IDs flipped correct->incorrect (regressions) and which flipped
incorrect->correct (improvements).

Score files only list entries that were WRONG (plus a one-line summary
{"accuracy", "correct_count", "total_count"} on line 1) -- entries not
listed are correct. So "correct" for each side = all_ids - wrong_ids.

USAGE:
    python check_regression.py \
        --before score/.../BFCL_v4_simple_python_hi_score.json \
        --after  score/.../BFCL_v4_simple_python_hi_numfix_score.json \
        --before-suffix "" --after-suffix "_numfix"
"""

import argparse
import json
from pathlib import Path


def load_score_file(path):
    """Returns (summary_dict, {id: entry_dict for wrong entries})."""
    with open(path, "r", encoding="utf-8") as f:
        lines = [l for l in f if l.strip()]
    summary = json.loads(lines[0])
    wrong = {}
    for line in lines[1:]:
        entry = json.loads(line)
        wrong[entry["id"]] = entry
    return summary, wrong


def strip_suffix(entry_id, suffix):
    if suffix and "_" + suffix.strip("_") + "_" in entry_id:
        # remap_id inserts suffix as "_numfix_" between prefix and number
        prefix, num = entry_id.rsplit("_", 1)
        marker = "_" + suffix.strip("_")
        if prefix.endswith(marker):
            prefix = prefix[: -len(marker)]
        return f"{prefix}_{num}"
    return entry_id


def get_call_args(entry):
    """Extract {func_name: args_dict} from model_result_decoded, best-effort."""
    decoded = entry.get("model_result_decoded")
    if not decoded or not isinstance(decoded, list):
        return None
    out = {}
    for call in decoded:
        if isinstance(call, dict):
            out.update(call)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", required=True)
    parser.add_argument("--after", required=True)
    parser.add_argument("--after-suffix", default="_numfix",
                         help="Suffix inserted into IDs in the 'after' file (default: _numfix)")
    parser.add_argument("--show", type=int, default=15,
                         help="How many regression examples to print in full (default 15)")
    args = parser.parse_args()

    before_summary, before_wrong = load_score_file(args.before)
    after_summary, after_wrong = load_score_file(args.after)

    total = before_summary["total_count"]
    assert total == after_summary["total_count"], "mismatched total_count between files"

    # Normalize after-file IDs back to base IDs for comparison.
    after_wrong_norm = {}
    for eid, entry in after_wrong.items():
        base_id = strip_suffix(eid, args.after_suffix)
        after_wrong_norm[base_id] = entry

    before_wrong_ids = set(before_wrong.keys())
    after_wrong_ids = set(after_wrong_norm.keys())

    regressions = sorted(after_wrong_ids - before_wrong_ids,
                          key=lambda x: int(x.rsplit("_", 1)[-1]))
    improvements = sorted(before_wrong_ids - after_wrong_ids,
                           key=lambda x: int(x.rsplit("_", 1)[-1]))
    still_wrong = before_wrong_ids & after_wrong_ids

    print(f"BEFORE: {before_summary['correct_count']}/{total} = {before_summary['accuracy']:.4f}")
    print(f"AFTER:  {after_summary['correct_count']}/{total} = {after_summary['accuracy']:.4f}")
    print()
    print(f"Regressions (correct -> incorrect): {len(regressions)}")
    print(f"Improvements (incorrect -> correct): {len(improvements)}")
    print(f"Still wrong both sides:              {len(still_wrong)}")
    print(f"Net change: {len(improvements) - len(regressions)} "
          f"(matches correct_count delta: {after_summary['correct_count'] - before_summary['correct_count']})")
    print()

    if regressions:
        print(f"=== REGRESSIONS (showing up to {args.show}) ===")
        for base_id in regressions[: args.show]:
            after_entry = after_wrong_norm[base_id]
            print(f"\n--- {base_id} ---")
            question = after_entry.get("prompt", {}).get("question", [[{}]])[0][0].get("content", "")
            print(f"  question (native): {question}")
            print(f"  question_en:       {after_entry.get('prompt', {}).get('question_en', '')}")
            print(f"  after (wrong):      {after_entry.get('model_result_decoded')}")
            print(f"  error:              {after_entry.get('error')}")
            print(f"  possible_answer:    {after_entry.get('possible_answer')}")

    if improvements:
        print(f"\n=== IMPROVEMENTS (showing up to {args.show}) ===")
        for base_id in improvements[: args.show]:
            before_entry = before_wrong[base_id]
            print(f"\n--- {base_id} ---")
            print(f"  before (wrong):     {before_entry.get('model_result_decoded')}")
            print(f"  before error:       {before_entry.get('error')}")


if __name__ == "__main__":
    main()
