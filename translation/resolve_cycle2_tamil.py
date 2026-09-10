"""
resolve_cycle2_tamil.py

Reads the completed Cycle 2 Tamil adjudication files (Rohan's Bucket 3 +
Bucket 4 tabs, Dhayanidhi's Bucket 4 tab), validates them against the
Cycle 2 assignment this project generated (`generate_cycle2_tamil.py`),
and produces the final resolved Tamil translation for all 200 items --
merging bucket 1/2 (already resolved after Cycle 1) with the bucket 3/4
adjudication decisions.

Raw Cycle 1 and Cycle 2 reviewer files are read-only here, never
modified. Output is a new, separate, fully-traceable layer (data
provenance policy -- see PROJECT_MANIFEST.md): every row records which
bucket it was, both reviewers' Cycle 1 verdicts, and (for bucket 3/4)
the Cycle 2 adjudicator and decision that produced the final text.

USAGE (run from inside berkeley-function-call-leaderboard):
    python translation/resolve_cycle2_tamil.py
"""

import json
from pathlib import Path

import openpyxl

CYCLE1_DIR = Path("reviewer annotated file downloaded from google sheets")
CYCLE1_FILES = {
    "Dhayanidhi": (CYCLE1_DIR / "Tamil_review_Dhayanidhi.xlsx", "Tamil Review Dhayanidhi"),
    "Rohan": (CYCLE1_DIR / "Tamil_review_Rohan.xlsx", "Tamil Review Rohan"),
}
CYCLE2_FILES = {
    "Rohan": CYCLE1_DIR / "Tamil_review_cycle_2_Rohan.xlsx",
    "Dhayanidhi": CYCLE1_DIR / "Tamil_review_cycle_2_Dhayanidhi.xlsx",
}
REVIEWERS = list(CYCLE1_FILES.keys())

ASSIGNMENT_PATH = Path("data/reviews/tamil_cycle2_bucket4_assignment.json")
OUT_DIR = Path("data/reviews")

CYCLE1_HEADER = ["base_id", "English Source", "Translation", "Automated check", "Correctness",
                 "Number/Value Issue", "Wrong Word/Mistranslation", "Grammar Error", "Meaning Changed",
                 "Missing Content", "Added Content", "Script/Formatting", "Invalid Swap", "Other",
                 "Corrected version", "Notes"]
B3_HEADER = ["base_id", "English Source", "Original Translation (you marked this Correct)",
             "Other reviewer's proposed fix", "Other reviewer's reasoning",
             "Decision", "Corrected version (only if 'Neither')", "Notes"]
B4_HEADER = ["base_id", "English Source", "Original Translation (both flagged Incorrect)",
             "Version A", "Version B", "Decision", "Corrected version (only if 'Neither')", "Notes"]

VALID_B3_DECISIONS = {"Original stands", "Accept fix", "Neither - write new"}
VALID_B4_DECISIONS = {"Version A", "Version B", "Neither - write new"}


def norm(s):
    return "" if s is None else s.rstrip()


def load_rows(path, sheet, header):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[sheet]
    rows = {}
    for r in range(2, ws.max_row + 1):
        values = [ws.cell(row=r, column=c).value for c in range(1, len(header) + 1)]
        row = dict(zip(header, values))
        if row["base_id"]:
            rows[row["base_id"]] = row
    return rows


def classify(cycle1):
    d, r = cycle1["Dhayanidhi"], cycle1["Rohan"]
    ids = sorted(d.keys(), key=lambda b: int(b.rsplit("_", 1)[-1]))
    buckets = {}
    for bid in ids:
        dc, rc = d[bid]["Correctness"], r[bid]["Correctness"]
        if dc == "Correct" and rc == "Correct":
            buckets[bid] = 1
        elif dc == "Incorrect" and rc == "Incorrect":
            buckets[bid] = 2 if norm(d[bid]["Corrected version"]) == norm(r[bid]["Corrected version"]) else 4
        else:
            buckets[bid] = 3
    return buckets


def main():
    cycle1 = {}
    for reviewer, (path, sheet) in CYCLE1_FILES.items():
        cycle1[reviewer] = load_rows(path, sheet, CYCLE1_HEADER)
    buckets = classify(cycle1)

    with open(ASSIGNMENT_PATH, encoding="utf-8") as f:
        assignment = json.load(f)["bucket4_assignment"]

    rohan_b3 = load_rows(CYCLE2_FILES["Rohan"], "Bucket 3 - Asymmetric", B3_HEADER)
    rohan_b4 = load_rows(CYCLE2_FILES["Rohan"], "Bucket 4 - Conflicting Fixes", B4_HEADER)
    dhaya_b4 = load_rows(CYCLE2_FILES["Dhayanidhi"], "Bucket 4 - Conflicting Fixes", B4_HEADER)
    bucket4_rows = {**rohan_b4, **dhaya_b4}

    bucket3_ids = sorted([b for b, v in buckets.items() if v == 3], key=lambda b: int(b.rsplit("_", 1)[-1]))
    bucket4_ids = sorted([b for b, v in buckets.items() if v == 4], key=lambda b: int(b.rsplit("_", 1)[-1]))

    # --- Validate Cycle 2 completeness/correctness before trusting it ---
    errors = []
    if set(rohan_b3.keys()) != set(bucket3_ids):
        errors.append(f"Bucket 3 id mismatch: sheet has {set(rohan_b3.keys())}, expected {set(bucket3_ids)}")
    if set(bucket4_rows.keys()) != set(bucket4_ids):
        errors.append(f"Bucket 4 id mismatch: sheet has {set(bucket4_rows.keys())}, expected {set(bucket4_ids)}")
    for bid in bucket3_ids:
        row = rohan_b3.get(bid, {})
        dec = row.get("Decision")
        if dec not in VALID_B3_DECISIONS:
            errors.append(f"{bid}: invalid bucket-3 decision {dec!r}")
        if dec == "Neither - write new" and not row.get("Corrected version (only if 'Neither')"):
            errors.append(f"{bid}: 'Neither' chosen but no Corrected version given")
    for bid in bucket4_ids:
        expected_adjudicator = assignment[bid]["adjudicator"]
        actual_sheet = "Rohan" if bid in rohan_b4 else ("Dhayanidhi" if bid in dhaya_b4 else None)
        if actual_sheet != expected_adjudicator:
            errors.append(f"{bid}: expected adjudicator {expected_adjudicator}, found in {actual_sheet}'s sheet")
        row = bucket4_rows.get(bid, {})
        dec = row.get("Decision")
        if dec not in VALID_B4_DECISIONS:
            errors.append(f"{bid}: invalid bucket-4 decision {dec!r}")
        if dec == "Neither - write new" and not row.get("Corrected version (only if 'Neither')"):
            errors.append(f"{bid}: 'Neither' chosen but no Corrected version given")

    if errors:
        print("VALIDATION ERRORS:")
        for e in errors:
            print(" -", e)
        raise SystemExit("Aborting -- fix the above before resolving.")
    print("Cycle 2 validation: all 20 bucket-3/4 items present, valid decisions, clean.")

    # --- Resolve final text per item ---
    final_rows = []
    resolution_stats = {"bucket3": {}, "bucket4": {}}
    for bid in sorted(buckets.keys(), key=lambda b: int(b.rsplit("_", 1)[-1])):
        b = buckets[bid]
        d_row, r_row = cycle1["Dhayanidhi"][bid], cycle1["Rohan"][bid]
        english_source = d_row["English Source"]
        pre_review_text = d_row["Translation"]

        entry = {
            "base_id": bid,
            "language": "ta",
            "bucket": b,
            "english_source": english_source,
            "pre_review_translation": pre_review_text,
            "cycle1_dhayanidhi_correctness": d_row["Correctness"],
            "cycle1_rohan_correctness": r_row["Correctness"],
        }

        if b == 1:
            entry["final_text"] = pre_review_text
            entry["resolution"] = "both_correct"
        elif b == 2:
            entry["final_text"] = norm(d_row["Corrected version"])
            entry["resolution"] = "both_incorrect_identical_fix"
        elif b == 3:
            row = rohan_b3[bid]
            dec = row["Decision"]
            resolution_stats["bucket3"][dec] = resolution_stats["bucket3"].get(dec, 0) + 1
            if dec == "Original stands":
                entry["final_text"] = pre_review_text
            elif dec == "Accept fix":
                entry["final_text"] = norm(d_row["Corrected version"])  # Dhayanidhi's proposed fix
            else:
                entry["final_text"] = norm(row["Corrected version (only if 'Neither')"])
            entry["cycle2_adjudicator"] = "Rohan"
            entry["cycle2_decision"] = dec
        else:  # bucket 4
            row = bucket4_rows[bid]
            dec = row["Decision"]
            adjudicator = assignment[bid]["adjudicator"]
            resolution_stats["bucket4"][dec] = resolution_stats["bucket4"].get(dec, 0) + 1
            if dec == "Version A":
                entry["final_text"] = norm(row["Version A"])
                chosen_author = assignment[bid]["version_a_author"]
            elif dec == "Version B":
                entry["final_text"] = norm(row["Version B"])
                chosen_author = assignment[bid]["version_a_author"] if False else assignment[bid]["version_b_author"]
            else:
                entry["final_text"] = norm(row["Corrected version (only if 'Neither')"])
                chosen_author = None
            entry["cycle2_adjudicator"] = adjudicator
            entry["cycle2_decision"] = dec
            entry["cycle2_chosen_fix_author"] = chosen_author
            entry["cycle2_adjudicator_picked_own_fix"] = (chosen_author == adjudicator) if chosen_author else None

        final_rows.append(entry)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "tamil_final_resolved.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for entry in final_rows:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"Wrote {out_path} ({len(final_rows)} rows)")

    # Also snapshot the raw Cycle 2 decisions as their own layer (separate from the resolved/merged output)
    decisions_snapshot = {
        "bucket3_rohan": rohan_b3,
        "bucket4_rohan": rohan_b4,
        "bucket4_dhayanidhi": dhaya_b4,
    }
    with open(OUT_DIR / "tamil_cycle2_decisions.json", "w", encoding="utf-8") as f:
        json.dump(decisions_snapshot, f, ensure_ascii=False, indent=2)
    print(f"Wrote {OUT_DIR / 'tamil_cycle2_decisions.json'}")

    print("\nBucket 3 resolution breakdown:", resolution_stats["bucket3"])
    print("Bucket 4 resolution breakdown:", resolution_stats["bucket4"])
    own_fix_count = sum(1 for e in final_rows if e.get("cycle2_adjudicator_picked_own_fix"))
    other_fix_count = sum(1 for e in final_rows if e.get("cycle2_adjudicator_picked_own_fix") is False)
    print(f"Bucket 4: adjudicator picked their OWN fix {own_fix_count}x, the OTHER's fix {other_fix_count}x "
          f"(out of {own_fix_count + other_fix_count} A/B decisions; blinded labels, so this is a post-hoc check).")


if __name__ == "__main__":
    main()
