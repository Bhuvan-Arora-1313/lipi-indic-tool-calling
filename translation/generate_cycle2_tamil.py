"""
generate_cycle2_tamil.py

Reads the two completed Cycle 1 Tamil reviewer files (downloaded from
Google Sheets by the two independent reviewers, Dhayanidhi and Rohan),
classifies every item into the 4-bucket agreement scheme, and builds the
Cycle 2 adjudication .xlsx sheets for the items that need one.

Buckets (strict exact-string match, only trailing whitespace trimmed --
no fuzzy matching, per the project's human-eval matching rule):
    1. Both Correct                              -> resolved, no Cycle 2
    2. Both Incorrect, identical fix              -> resolved, no Cycle 2
    3. Asymmetric (one Correct, one Incorrect+fix) -> Cycle 2: adjudicator
       is whoever said Correct, shown the other's proposed fix.
    4. Both Incorrect, different fixes             -> Cycle 2: adjudicator
       randomly assigned, balanced across the two reviewers (fixed seed),
       shown both fixes blinded as Version A / Version B.

Raw Cycle 1 files are read-only here -- never modified. Cycle 2 outputs
and the bucket classification are written as new, separate files (data
provenance policy: raw / derived-findings / corrections stay in distinct,
traceable layers -- see PROJECT_MANIFEST.md).

USAGE (run from inside berkeley-function-call-leaderboard):
    python translation/generate_cycle2_tamil.py
"""

import json
import random
from pathlib import Path

import openpyxl
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter

CYCLE1_DIR = Path("data/human_review")
CYCLE1_FILES = {
    "Dhayanidhi": (CYCLE1_DIR / "Tamil_review_Dhayanidhi.xlsx", "Tamil Review Dhayanidhi"),
    "Rohan": (CYCLE1_DIR / "Tamil_review_Rohan.xlsx", "Tamil Review Rohan"),
}
REVIEWERS = list(CYCLE1_FILES.keys())

OUT_REVIEWS_DIR = Path("data/reviews")
OUT_SHEETS_DIR = Path("data/review_sheets/cycle2")

RANDOM_SEED = 42  # fixed for reproducibility -- see LOG.md

HEADER = ["base_id", "English Source", "Translation", "Automated check", "Correctness",
          "Number/Value Issue", "Wrong Word/Mistranslation", "Grammar Error", "Meaning Changed",
          "Missing Content", "Added Content", "Script/Formatting", "Invalid Swap", "Other",
          "Corrected version", "Notes"]
ISSUE_COLS = HEADER[5:14]

READONLY_FILL = PatternFill(start_color="F0F4F8", end_color="F0F4F8", fill_type="solid")
HEADER_FILL = PatternFill(start_color="3D3A7A", end_color="3D3A7A", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True)
WRAP = Alignment(wrap_text=True, vertical="top")


def norm(s):
    """Exact match, only trailing whitespace trimmed -- no fuzzy matching."""
    return "" if s is None else s.rstrip()


def load_cycle1_file(path, sheet_name):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[sheet_name]
    rows = {}
    for r in range(2, ws.max_row + 1):
        values = [ws.cell(row=r, column=c).value for c in range(1, len(HEADER) + 1)]
        row = dict(zip(HEADER, values))
        if row["base_id"]:
            rows[row["base_id"]] = row
    return rows


def classify(data):
    """Returns dict base_id -> bucket (1-4), sorted by numeric suffix."""
    d, r = data["Dhayanidhi"], data["Rohan"]
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


def assign_bucket4(bucket4_ids):
    """Balanced random adjudicator assignment + blinded A/B ordering, fixed seed."""
    rng = random.Random(RANDOM_SEED)
    ids = sorted(bucket4_ids, key=lambda b: int(b.rsplit("_", 1)[-1]))
    adjudicators = REVIEWERS * (len(ids) // len(REVIEWERS)) + REVIEWERS[: len(ids) % len(REVIEWERS)]
    rng.shuffle(adjudicators)
    assignment = {}
    for bid, adjudicator in zip(ids, adjudicators):
        ab = list(REVIEWERS)
        rng.shuffle(ab)  # who is "Version A" vs "Version B" for this item
        assignment[bid] = {"adjudicator": adjudicator, "version_a_author": ab[0], "version_b_author": ab[1]}
    return assignment


def write_instructions_sheet(wb, lines):
    ws = wb.create_sheet("Instructions", 0)
    ws.column_dimensions["A"].width = 100
    row = 1
    ws.cell(row=row, column=1, value="Cycle 2 -- adjudication").font = Font(bold=True, size=14)
    row += 2
    for line in lines:
        cell = ws.cell(row=row, column=1, value=line)
        if line.endswith(":"):
            cell.font = Font(bold=True)
        row += 1


def style_tab(ws, headers, decision_col_idx, decision_options, n_rows):
    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = WRAP
    ws.freeze_panes = "A2"

    widths = {"base_id": 14, "English Source": 40}
    for col_idx, header in enumerate(headers, start=1):
        ws.column_dimensions[get_column_letter(col_idx)].width = widths.get(header, 38)

    readonly_cols = list(range(1, decision_col_idx))
    for col_idx in readonly_cols:
        for r in range(2, n_rows + 2):
            ws.cell(row=r, column=col_idx).fill = READONLY_FILL
            ws.cell(row=r, column=col_idx).alignment = WRAP
    for r in range(2, n_rows + 2):
        for col_idx in range(decision_col_idx, len(headers) + 1):
            ws.cell(row=r, column=col_idx).alignment = WRAP

    dv = DataValidation(type="list", formula1=f'"{decision_options}"', allow_blank=True)
    ws.add_data_validation(dv)
    col_letter = get_column_letter(decision_col_idx)
    dv.add(f"{col_letter}2:{col_letter}{n_rows + 1}")


def build_bucket3_rows(wb, items, data):
    """items: list of (base_id, correct_reviewer, incorrect_reviewer)."""
    if not items:
        return
    ws = wb.create_sheet("Bucket 3 - Asymmetric")
    headers = ["base_id", "English Source", "Original Translation (you marked this Correct)",
               "Other reviewer's proposed fix", "Other reviewer's reasoning",
               "Decision", "Corrected version (only if 'Neither')", "Notes"]
    for r, (bid, correct_reviewer, incorrect_reviewer) in enumerate(items, start=2):
        own_row = data[correct_reviewer][bid]
        other_row = data[incorrect_reviewer][bid]
        ws.cell(row=r, column=1, value=bid)
        ws.cell(row=r, column=2, value=own_row["English Source"])
        ws.cell(row=r, column=3, value=own_row["Translation"])
        ws.cell(row=r, column=4, value=other_row["Corrected version"])
        ws.cell(row=r, column=5, value=other_row["Notes"] or "")
    style_tab(ws, headers, decision_col_idx=6,
              decision_options="Original stands,Accept fix,Neither - write new", n_rows=len(items))


def build_bucket4_rows(wb, items, data, assignment):
    """items: list of base_ids assigned to THIS adjudicator, already filtered."""
    if not items:
        return
    ws = wb.create_sheet("Bucket 4 - Conflicting Fixes")
    headers = ["base_id", "English Source", "Original Translation (both flagged Incorrect)",
               "Version A", "Version B", "Decision", "Corrected version (only if 'Neither')", "Notes"]
    for r, bid in enumerate(items, start=2):
        a = assignment[bid]
        any_row = data[REVIEWERS[0]][bid]
        version_a_text = data[a["version_a_author"]][bid]["Corrected version"]
        version_b_text = data[a["version_b_author"]][bid]["Corrected version"]
        ws.cell(row=r, column=1, value=bid)
        ws.cell(row=r, column=2, value=any_row["English Source"])
        ws.cell(row=r, column=3, value=any_row["Translation"])
        ws.cell(row=r, column=4, value=version_a_text)
        ws.cell(row=r, column=5, value=version_b_text)
    style_tab(ws, headers, decision_col_idx=6,
              decision_options="Version A,Version B,Neither - write new", n_rows=len(items))


def main():
    data = {}
    for reviewer, (path, sheet) in CYCLE1_FILES.items():
        data[reviewer] = load_cycle1_file(path, sheet)
        print(f"Loaded {reviewer}: {len(data[reviewer])} rows from {path.name}")

    ids_sets = [set(rows.keys()) for rows in data.values()]
    if ids_sets[0] != ids_sets[1]:
        raise SystemExit("base_id sets differ between reviewers -- aborting, needs manual check.")

    buckets = classify(data)
    counts = {b: sum(1 for v in buckets.values() if v == b) for b in (1, 2, 3, 4)}
    print("Bucket counts:", counts)

    bucket3_ids = [bid for bid, b in buckets.items() if b == 3]
    bucket4_ids = [bid for bid, b in buckets.items() if b == 4]

    # Bucket 3: adjudicator is whichever reviewer said Correct for that item.
    bucket3_by_adjudicator = {r: [] for r in REVIEWERS}
    for bid in bucket3_ids:
        correct_reviewer = "Dhayanidhi" if data["Dhayanidhi"][bid]["Correctness"] == "Correct" else "Rohan"
        incorrect_reviewer = "Rohan" if correct_reviewer == "Dhayanidhi" else "Dhayanidhi"
        bucket3_by_adjudicator[correct_reviewer].append((bid, correct_reviewer, incorrect_reviewer))

    bucket4_assignment = assign_bucket4(bucket4_ids)
    bucket4_by_adjudicator = {r: [] for r in REVIEWERS}
    for bid, a in bucket4_assignment.items():
        bucket4_by_adjudicator[a["adjudicator"]].append(bid)
    for r in REVIEWERS:
        bucket4_by_adjudicator[r].sort(key=lambda b: int(b.rsplit("_", 1)[-1]))

    print("Bucket 3 adjudicator counts:", {r: len(v) for r, v in bucket3_by_adjudicator.items()})
    print("Bucket 4 adjudicator counts:", {r: len(v) for r, v in bucket4_by_adjudicator.items()})

    # --- Save derived classification + assignment (separate layer, raw files untouched) ---
    OUT_REVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    classification_out = {
        "language": "ta",
        "cycle1_source_files": {r: str(CYCLE1_FILES[r][0]) for r in REVIEWERS},
        "matching_rule": "exact string match, only trailing whitespace trimmed",
        "bucket_counts": counts,
        "buckets": buckets,
    }
    with open(OUT_REVIEWS_DIR / "tamil_cycle1_classification.json", "w", encoding="utf-8") as f:
        json.dump(classification_out, f, ensure_ascii=False, indent=2)
    print(f"Wrote {OUT_REVIEWS_DIR / 'tamil_cycle1_classification.json'}")

    assignment_out = {
        "language": "ta",
        "random_seed": RANDOM_SEED,
        "note": "version_a_author/version_b_author are NOT shown to the adjudicator -- blinded as Version A/B in the sheet.",
        "bucket4_assignment": bucket4_assignment,
    }
    with open(OUT_REVIEWS_DIR / "tamil_cycle2_bucket4_assignment.json", "w", encoding="utf-8") as f:
        json.dump(assignment_out, f, ensure_ascii=False, indent=2)
    print(f"Wrote {OUT_REVIEWS_DIR / 'tamil_cycle2_bucket4_assignment.json'}")

    # --- Build per-adjudicator Cycle 2 sheets ---
    OUT_SHEETS_DIR.mkdir(parents=True, exist_ok=True)
    for reviewer in REVIEWERS:
        b3_items = bucket3_by_adjudicator[reviewer]
        b4_items = bucket4_by_adjudicator[reviewer]
        if not b3_items and not b4_items:
            print(f"  {reviewer}: no Cycle 2 items, skipping.")
            continue

        wb = Workbook()
        wb.remove(wb.active)
        instr = [
            "You are adjudicating disagreements from Cycle 1 Tamil review.",
            "",
            "Bucket 3 tab (if present): you marked the original translation Correct, the other "
            "reviewer marked it Incorrect and proposed a fix. Decide:",
            "  - Original stands: the translation is fine as-is.",
            "  - Accept fix: the other reviewer's proposed fix is correct.",
            "  - Neither - write new: neither is right; write your own correction in 'Corrected version'.",
            "",
            "Bucket 4 tab (if present): both reviewers flagged this as Incorrect but proposed "
            "different fixes, shown here blinded as Version A / Version B (not labeled by reviewer, "
            "to avoid bias). Decide:",
            "  - Version A / Version B: pick whichever fix is correct.",
            "  - Neither - write new: neither is right; write your own correction in 'Corrected version'.",
            "",
            "Only fill in 'Corrected version' if you chose 'Neither - write new'. Notes are optional.",
        ]
        write_instructions_sheet(wb, instr)
        build_bucket3_rows(wb, b3_items, data)
        build_bucket4_rows(wb, b4_items, data, bucket4_assignment)

        out_path = OUT_SHEETS_DIR / f"Tamil_Cycle2_{reviewer}.xlsx"
        wb.save(out_path)
        print(f"  Wrote {out_path} (bucket3={len(b3_items)}, bucket4={len(b4_items)})")

    print("\nDone. Upload each .xlsx to Google Sheets as before. Raw Cycle 1 files were not modified.")


if __name__ == "__main__":
    main()
