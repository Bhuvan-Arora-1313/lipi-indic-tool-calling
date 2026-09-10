"""
generate_cycle2_hindi.py

Same pipeline as generate_cycle2_tamil.py, run on the Hindi Cycle 1
files (Jayant Kapoor, Anshul Gupta). See that script's docstring for the
general bucket/Cycle-2 design.

One Hindi-specific wrinkle, confirmed with the user (2026-09-09), not
guessed at: Anshul marked every single row "Correct" (200/200) in the
Correctness dropdown, but filled in a "Corrected version" (plus an
issue checkbox and, usually, a real linguistic note) on 10 of them. The
user confirmed this is a workflow misunderstanding, not 10 genuine
"correct but I'll also suggest a tweak" calls: Anshul read "Correct" as
"is my correction below correct", not "is the original translation
correct". So for Anshul specifically -- and only Anshul, this is not a
general rule -- a row with a non-empty Corrected version is treated as
effectively Incorrect for bucket classification, regardless of what his
Correctness cell literally says. His raw Correctness column is left
untouched in the source file and in the loaded data; the override is
applied only when classifying, and is recorded explicitly in the output
(`anshul_correctness_reinterpreted: true` in the classification file)
so this is traceable rather than a silent correction.

USAGE (run from inside berkeley-function-call-leaderboard):
    python translation/generate_cycle2_hindi.py
"""

import json
import random
from pathlib import Path

import openpyxl
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter

CYCLE1_DIR = Path("reviewer annotated file downloaded from google sheets")
CYCLE1_FILES = {
    "Jayant": (CYCLE1_DIR / "Hindi review_cycle_1 - Jayant Kapoor.xlsx", "Hindi Review jayant kapoor"),
    "Anshul": (CYCLE1_DIR / "Hindi review_cycle_1 Anshul Gupta.xlsx", "Hindi review Anshul"),
}
REVIEWERS = list(CYCLE1_FILES.keys())

# Reviewer(s) whose Correctness field is known (user-confirmed) to be
# unreliable when a Corrected version is present -- see docstring.
REINTERPRET_AS_INCORRECT_IF_FIX_GIVEN = {"Anshul"}

OUT_REVIEWS_DIR = Path("data/reviews")
OUT_SHEETS_DIR = Path("data/review_sheets/cycle2")

RANDOM_SEED = 42  # fixed for reproducibility -- see LOG.md

HEADER = ["base_id", "English Source", "Translation", "Automated check", "Correctness",
          "Number/Value Issue", "Wrong Word/Mistranslation", "Grammar Error", "Meaning Changed",
          "Missing Content", "Added Content", "Script/Formatting", "Invalid Swap", "Other",
          "Corrected version", "Notes"]

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


def effective_correctness(reviewer, row):
    if reviewer in REINTERPRET_AS_INCORRECT_IF_FIX_GIVEN and row["Corrected version"]:
        return "Incorrect"
    return row["Correctness"]


def classify(data):
    """Returns dict base_id -> bucket (1-4), using effective_correctness."""
    r1, r2 = REVIEWERS
    d1, d2 = data[r1], data[r2]
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


def assign_bucket4(bucket4_ids):
    rng = random.Random(RANDOM_SEED)
    ids = sorted(bucket4_ids, key=lambda b: int(b.rsplit("_", 1)[-1]))
    adjudicators = (REVIEWERS * (len(ids) // len(REVIEWERS) + 1))[: len(ids)]
    rng.shuffle(adjudicators)
    assignment = {}
    for bid, adjudicator in zip(ids, adjudicators):
        ab = list(REVIEWERS)
        rng.shuffle(ab)
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
    print("Bucket counts (with Anshul correctness-field reinterpretation applied):", counts)

    bucket3_ids = [bid for bid, b in buckets.items() if b == 3]
    bucket4_ids = [bid for bid, b in buckets.items() if b == 4]

    bucket3_by_adjudicator = {r: [] for r in REVIEWERS}
    for bid in bucket3_ids:
        c1 = effective_correctness(REVIEWERS[0], data[REVIEWERS[0]][bid])
        correct_reviewer = REVIEWERS[0] if c1 == "Correct" else REVIEWERS[1]
        incorrect_reviewer = REVIEWERS[1] if correct_reviewer == REVIEWERS[0] else REVIEWERS[0]
        bucket3_by_adjudicator[correct_reviewer].append((bid, correct_reviewer, incorrect_reviewer))

    bucket4_assignment = assign_bucket4(bucket4_ids)
    bucket4_by_adjudicator = {r: [] for r in REVIEWERS}
    for bid, a in bucket4_assignment.items():
        bucket4_by_adjudicator[a["adjudicator"]].append(bid)
    for r in REVIEWERS:
        bucket4_by_adjudicator[r].sort(key=lambda b: int(b.rsplit("_", 1)[-1]))

    print("Bucket 3 adjudicator counts:", {r: len(v) for r, v in bucket3_by_adjudicator.items()})
    print("Bucket 4 adjudicator counts:", {r: len(v) for r, v in bucket4_by_adjudicator.items()})

    OUT_REVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    classification_out = {
        "language": "hi",
        "cycle1_source_files": {r: str(CYCLE1_FILES[r][0]) for r in REVIEWERS},
        "matching_rule": "exact string match, only trailing whitespace trimmed",
        "anshul_correctness_reinterpreted": True,
        "anshul_correctness_reinterpretation_note": (
            "Anshul marked Correctness='Correct' on all 200 rows, including 10 where he also "
            "filled in a Corrected version + issue checkbox + note. User confirmed (2026-09-09) "
            "this was a misunderstanding -- he was answering 'is my correction below correct', "
            "not 'is the original translation correct'. For classification purposes only, any "
            "Anshul row with a non-empty Corrected version is treated as Incorrect. His raw "
            "Correctness column is untouched in the source file and in loaded data."
        ),
        "bucket_counts": counts,
        "buckets": buckets,
    }
    with open(OUT_REVIEWS_DIR / "hindi_cycle1_classification.json", "w", encoding="utf-8") as f:
        json.dump(classification_out, f, ensure_ascii=False, indent=2)
    print(f"Wrote {OUT_REVIEWS_DIR / 'hindi_cycle1_classification.json'}")

    assignment_out = {
        "language": "hi",
        "random_seed": RANDOM_SEED,
        "note": "version_a_author/version_b_author are NOT shown to the adjudicator -- blinded as Version A/B in the sheet.",
        "bucket4_assignment": bucket4_assignment,
    }
    with open(OUT_REVIEWS_DIR / "hindi_cycle2_bucket4_assignment.json", "w", encoding="utf-8") as f:
        json.dump(assignment_out, f, ensure_ascii=False, indent=2)
    print(f"Wrote {OUT_REVIEWS_DIR / 'hindi_cycle2_bucket4_assignment.json'}")

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
            "You are adjudicating disagreements from Cycle 1 Hindi review.",
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

        out_path = OUT_SHEETS_DIR / f"Hindi_Cycle2_{reviewer}.xlsx"
        wb.save(out_path)
        print(f"  Wrote {out_path} (bucket3={len(b3_items)}, bucket4={len(b4_items)})")

    print("\nDone. Upload each .xlsx to Google Sheets as before. Raw Cycle 1 files were not modified.")


if __name__ == "__main__":
    main()
