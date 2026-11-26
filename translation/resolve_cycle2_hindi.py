"""
resolve_cycle2_hindi.py

Reads the completed Cycle 2 Hindi adjudication files (Anshul's Bucket 3 +
Bucket 4 tabs, Jayant's Bucket 3 + Bucket 4 tabs), validates them against
the Cycle 2 assignment this project generated (`generate_cycle2_hindi.py`),
and produces the final resolved Hindi translation for all 200 items --
merging bucket 1/2 (already resolved after Cycle 1) with the bucket 3/4
adjudication decisions.

Carries over the Anshul correctness-field reinterpretation from
generate_cycle2_hindi.py: bucket assignment for a handful of items relies
on treating an Anshul row with a non-empty Corrected version as
effectively Incorrect, even though his raw Correctness cell says
"Correct" (confirmed workflow misunderstanding, see that script's
docstring). Bucket-1 final text still comes from the pre-review
Translation column, same as everywhere else -- the reinterpretation only
ever affects which bucket an item lands in, never the resolved text.

Raw Cycle 1 and Cycle 2 reviewer files are read-only here, never
modified. Output is a new, separate, fully-traceable layer: every row
records both reviewers' Cycle 1 verdicts and (for bucket 3/4) the Cycle 2
adjudicator and decision that produced the final text.

USAGE (run from inside berkeley-function-call-leaderboard):
    python translation/resolve_cycle2_hindi.py
"""

import json
from pathlib import Path

import openpyxl

CYCLE1_DIR = Path("data/human_review")
CYCLE1_FILES = {
    "Jayant": (CYCLE1_DIR / "Hindi review_cycle_1 - Jayant Kapoor.xlsx", "Hindi Review jayant kapoor"),
    "Anshul": (CYCLE1_DIR / "Hindi review_cycle_1 Anshul Gupta.xlsx", "Hindi review Anshul"),
}
CYCLE2_FILES = {
    "Anshul": CYCLE1_DIR / "Hindi cycle_2  review Anshul Gupta.xlsx",
    "Jayant": CYCLE1_DIR / "Hindi cycle_2  review - Jayant Kapoor.xlsx",
}
REVIEWERS = list(CYCLE1_FILES.keys())

REINTERPRET_AS_INCORRECT_IF_FIX_GIVEN = {"Anshul"}

ASSIGNMENT_PATH = Path("data/reviews/hindi_cycle2_bucket4_assignment.json")
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


def effective_correctness(reviewer, row):
    if reviewer in REINTERPRET_AS_INCORRECT_IF_FIX_GIVEN and row["Corrected version"]:
        return "Incorrect"
    return row["Correctness"]


def classify(cycle1):
    r1, r2 = REVIEWERS
    d1, d2 = cycle1[r1], cycle1[r2]
    ids = sorted(d1.keys(), key=lambda b: int(b.rsplit("_", 1)[-1]))
    buckets = {}
    for bid in ids:
        c1 = effective_correctness(r1, d1[bid])
        c2 = effective_correctness(r2, d2[bid])
        if c1 == "Correct" and c2 == "Correct":
            buckets[bid] = 1
        elif c1 == "Incorrect" and c2 == "Incorrect":
            buckets[bid] = 2 if norm(d1[bid]["Corrected version"]) == norm(d2[bid]["Corrected version"]) else 4
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

    anshul_b3 = load_rows(CYCLE2_FILES["Anshul"], "Bucket 3 - Asymmetric", B3_HEADER)
    jayant_b3 = load_rows(CYCLE2_FILES["Jayant"], "Bucket 3 - Asymmetric", B3_HEADER)
    bucket3_rows = {**anshul_b3, **jayant_b3}

    anshul_b4 = load_rows(CYCLE2_FILES["Anshul"], "Bucket 4 - Conflicting Fixes", B4_HEADER)
    jayant_b4 = load_rows(CYCLE2_FILES["Jayant"], "Bucket 4 - Conflicting Fixes", B4_HEADER)
    bucket4_rows = {**anshul_b4, **jayant_b4}

    bucket3_ids = sorted([b for b, v in buckets.items() if v == 3], key=lambda b: int(b.rsplit("_", 1)[-1]))
    bucket4_ids = sorted([b for b, v in buckets.items() if v == 4], key=lambda b: int(b.rsplit("_", 1)[-1]))

    # --- Validate Cycle 2 completeness/correctness before trusting it ---
    errors = []
    incomplete_bucket4 = []
    if set(bucket3_rows.keys()) != set(bucket3_ids):
        errors.append(f"Bucket 3 id mismatch: sheets have {set(bucket3_rows.keys())}, expected {set(bucket3_ids)}")
    if set(bucket4_rows.keys()) != set(bucket4_ids):
        errors.append(f"Bucket 4 id mismatch: sheets have {set(bucket4_rows.keys())}, expected {set(bucket4_ids)}")
    for bid in bucket3_ids:
        row = bucket3_rows.get(bid, {})
        dec = row.get("Decision")
        if dec not in VALID_B3_DECISIONS:
            errors.append(f"{bid}: invalid/missing bucket-3 decision {dec!r}")
        if dec == "Neither - write new" and not row.get("Corrected version (only if 'Neither')"):
            errors.append(f"{bid}: 'Neither' chosen but no Corrected version given")
    for bid in bucket4_ids:
        expected_adjudicator = assignment[bid]["adjudicator"]
        actual_sheet = "Anshul" if bid in anshul_b4 else ("Jayant" if bid in jayant_b4 else None)
        if actual_sheet != expected_adjudicator:
            errors.append(f"{bid}: expected adjudicator {expected_adjudicator}, found in {actual_sheet}'s sheet")
        row = bucket4_rows.get(bid, {})
        dec = row.get("Decision")
        if dec not in VALID_B4_DECISIONS:
            incomplete_bucket4.append(bid)
            continue
        if dec == "Neither - write new" and not row.get("Corrected version (only if 'Neither')"):
            errors.append(f"{bid}: 'Neither' chosen but no Corrected version given")

    if errors:
        print("VALIDATION ERRORS:")
        for e in errors:
            print(" -", e)
        raise SystemExit("Aborting -- fix the above before resolving.")

    if incomplete_bucket4:
        print(f"NOTE: {len(incomplete_bucket4)} bucket-4 item(s) have no Decision yet, still pending from the "
              f"adjudicator: {incomplete_bucket4}. Resolving everything else; these will be marked 'pending' "
              "and excluded from the final dataset until Jayant fills them in.")

    print(f"Cycle 2 validation: bucket-3 ({len(bucket3_ids)}) clean; "
          f"bucket-4 ({len(bucket4_ids) - len(incomplete_bucket4)}/{len(bucket4_ids)}) resolved.")

    # --- Resolve final text per item ---
    final_rows = []
    pending_rows = []
    resolution_stats = {"bucket3": {}, "bucket4": {}}
    for bid in sorted(buckets.keys(), key=lambda b: int(b.rsplit("_", 1)[-1])):
        b = buckets[bid]
        j_row, a_row = cycle1["Jayant"][bid], cycle1["Anshul"][bid]
        english_source = j_row["English Source"]
        pre_review_text = j_row["Translation"]

        entry = {
            "base_id": bid,
            "language": "hi",
            "bucket": b,
            "english_source": english_source,
            "pre_review_translation": pre_review_text,
            "cycle1_jayant_correctness": j_row["Correctness"],
            "cycle1_anshul_correctness": a_row["Correctness"],
            "cycle1_anshul_correctness_reinterpreted": effective_correctness("Anshul", a_row) != a_row["Correctness"],
        }

        if b == 1:
            entry["final_text"] = pre_review_text
            entry["resolution"] = "both_correct"
        elif b == 2:
            entry["final_text"] = norm(j_row["Corrected version"])
            entry["resolution"] = "both_incorrect_identical_fix"
        elif b == 3:
            row = bucket3_rows[bid]
            adjudicator = "Jayant" if bid in jayant_b3 else "Anshul"
            dec = row["Decision"]
            resolution_stats["bucket3"][dec] = resolution_stats["bucket3"].get(dec, 0) + 1
            if dec == "Original stands":
                entry["final_text"] = pre_review_text
            elif dec == "Accept fix":
                other = "Anshul" if adjudicator == "Jayant" else "Jayant"
                entry["final_text"] = norm(cycle1[other][bid]["Corrected version"])
            else:
                entry["final_text"] = norm(row["Corrected version (only if 'Neither')"])
            entry["cycle2_adjudicator"] = adjudicator
            entry["cycle2_decision"] = dec
        else:  # bucket 4
            if bid in incomplete_bucket4:
                entry["resolution"] = "pending_cycle2_decision"
                entry["cycle2_adjudicator"] = assignment[bid]["adjudicator"]
                pending_rows.append(bid)
                continue
            row = bucket4_rows[bid]
            dec = row["Decision"]
            adjudicator = assignment[bid]["adjudicator"]
            resolution_stats["bucket4"][dec] = resolution_stats["bucket4"].get(dec, 0) + 1
            if dec == "Version A":
                entry["final_text"] = norm(row["Version A"])
                chosen_author = assignment[bid]["version_a_author"]
            elif dec == "Version B":
                entry["final_text"] = norm(row["Version B"])
                chosen_author = assignment[bid]["version_b_author"]
            else:
                entry["final_text"] = norm(row["Corrected version (only if 'Neither')"])
                chosen_author = None
            entry["cycle2_adjudicator"] = adjudicator
            entry["cycle2_decision"] = dec
            entry["cycle2_chosen_fix_author"] = chosen_author
            entry["cycle2_adjudicator_picked_own_fix"] = (chosen_author == adjudicator) if chosen_author else None

        final_rows.append(entry)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "hindi_final_resolved.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for entry in final_rows:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"Wrote {out_path} ({len(final_rows)}/200 rows resolved; {len(pending_rows)} pending: {pending_rows})")

    decisions_snapshot = {
        "bucket3_anshul": anshul_b3,
        "bucket3_jayant": jayant_b3,
        "bucket4_anshul": anshul_b4,
        "bucket4_jayant": jayant_b4,
    }
    with open(OUT_DIR / "hindi_cycle2_decisions.json", "w", encoding="utf-8") as f:
        json.dump(decisions_snapshot, f, ensure_ascii=False, indent=2)
    print(f"Wrote {OUT_DIR / 'hindi_cycle2_decisions.json'}")

    print("\nBucket 3 resolution breakdown:", resolution_stats["bucket3"])
    print("Bucket 4 resolution breakdown:", resolution_stats["bucket4"])
    if pending_rows:
        print(f"\nSTILL PENDING: {pending_rows} -- Jayant has not filled in a Decision for these bucket-4 "
              "items yet. Ask him to complete Bucket 4 in 'Hindi cycle_2 review - Jayant Kapoor.xlsx', "
              "then re-run this script.")


if __name__ == "__main__":
    main()
