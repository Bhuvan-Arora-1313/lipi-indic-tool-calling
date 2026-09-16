"""
generate_cycle2_parasyno.py

Same pipeline as generate_cycle2_tamil.py / generate_cycle2_hindi.py, for
the English PARA/SYNO perturbation review (reviewers Jayant Kapoor, Anshul
Gupta). See those scripts' docstrings for the general bucket/Cycle-2
design. Two things are specific to this dataset:

1. Composite key: PARA/SYNO rows are keyed by (base_id, perturbation_type),
   not base_id alone -- each base_id has two rows (its PARA and SYNO
   variant), both needing independent review.

2. The review sheet template merges the base_id and English Source cells
   across each PARA+SYNO pair (see build_perturbation_sheet in
   generate_review_sheets.py). openpyxl only returns a value on the
   top-left cell of a merged range -- reading naively without forward-
   filling silently collapsed all SYNO rows onto a single None key the
   first time this was tried (2026-09-14). Fixed here by forward-filling
   those two columns from the last non-empty value seen.

Two items needed manual handling, confirmed with the user before writing
anything (2026-09-16), because a reviewer marked "Incorrect" with zero
supporting detail -- no fix, no issue-type checkbox, no notes:
  - multiple_3 (PARA): Jayant said Incorrect with nothing to go on; Anshul
    (who said Correct) is normally the Cycle 2 adjudicator, but there's no
    proposed fix to show him. Sent to Cycle 2 anyway, with only two
    options instead of three (no "Accept fix", since there's nothing to
    accept) -- "Original stands" or "Neither - write new".
  - multiple_72 (SYNO): both said Incorrect (bucket 4), but only Jayant
    gave an actual fix; Anshul's side is blank. Rather than run this
    through the normal blinded A/B flow (degenerate with one side empty
    -- not a real alternative to weigh), it's resolved directly using
    Jayant's fix and does NOT get a Cycle 2 row at all. Recorded
    explicitly in the classification output, not silently dropped.

USAGE (run from inside berkeley-function-call-leaderboard):
    python translation/generate_cycle2_parasyno.py
"""

import json
from pathlib import Path

import openpyxl
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter

CYCLE1_DIR = Path("reviewer annotated file downloaded from google sheets")
CYCLE1_FILES = {
    "Jayant": (CYCLE1_DIR / "English_PARA_SYNO_Jayant_Kapoor.xlsx", "English PARA-SYNO Jayant"),
    "Anshul": (CYCLE1_DIR / "English_PARA_SYNO_Anshul_Gupta.xlsx", "English PARA-SYNO Anshul"),
}
REVIEWERS = list(CYCLE1_FILES.keys())

OUT_REVIEWS_DIR = Path("data/reviews")
OUT_SHEETS_DIR = Path("data/review_sheets/cycle2")

HEADER = ["base_id", "Perturbation type", "English Source", "Perturbed text", "Automated check", "Correctness",
          "Number/Value Issue", "Wrong Word/Mistranslation", "Grammar Error", "Meaning Changed",
          "Missing Content", "Added Content", "Script/Formatting", "Invalid Swap", "Other",
          "Corrected version", "Notes"]

# Items resolved by hand (not through the normal Cycle 2 mechanism) --
# confirmed with the user 2026-09-16, see docstring.
NO_FIX_GIVEN_BUCKET3 = {("multiple_3", "PARA")}  # 2-option Cycle 2 instead of 3
AUTO_RESOLVE_BUCKET4 = {("multiple_72", "SYNO")}  # resolved directly, no Cycle 2 row

READONLY_FILL = PatternFill(start_color="F0F4F8", end_color="F0F4F8", fill_type="solid")
HEADER_FILL = PatternFill(start_color="3D3A7A", end_color="3D3A7A", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True)
WRAP = Alignment(wrap_text=True, vertical="top")


def norm(s):
    return "" if s is None else s.rstrip()


def key_str(key):
    return f"{key[0]}|{key[1]}"


def load_cycle1_file(path, sheet_name):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[sheet_name]
    rows = {}
    last_base_id, last_source = None, None
    for r in range(2, ws.max_row + 1):
        values = [ws.cell(row=r, column=c).value for c in range(1, len(HEADER) + 1)]
        row = dict(zip(HEADER, values))
        # Forward-fill the merged base_id / English Source columns.
        if row["base_id"] is None:
            row["base_id"] = last_base_id
        else:
            last_base_id = row["base_id"]
        if row["English Source"] is None:
            row["English Source"] = last_source
        else:
            last_source = row["English Source"]
        if row["base_id"] is None or row["Perturbation type"] is None:
            continue
        key = (row["base_id"], row["Perturbation type"])
        rows[key] = row
    return rows


def classify(data):
    d1, d2 = data[REVIEWERS[0]], data[REVIEWERS[1]]
    keys = sorted(d1.keys(), key=lambda k: (int(k[0].split("_")[1]), k[1]))
    buckets = {}
    for key in keys:
        c1, c2 = d1[key]["Correctness"], d2[key]["Correctness"]
        if c1 == "Correct" and c2 == "Correct":
            buckets[key] = 1
        elif c1 == "Incorrect" and c2 == "Incorrect":
            buckets[key] = 2 if norm(d1[key]["Corrected version"]) == norm(d2[key]["Corrected version"]) else 4
        else:
            buckets[key] = 3
    return buckets


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


def style_tab(ws, headers, decision_col_idx, n_rows, per_row_options):
    """per_row_options: list (len n_rows) of the decision-list string for
    that row -- lets a single row (multiple_3) get a different dropdown
    than the rest without a second tab."""
    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = WRAP
    ws.freeze_panes = "A2"

    widths = {"base_id": 14, "Perturbation type": 14, "English Source": 38}
    for col_idx, header in enumerate(headers, start=1):
        ws.column_dimensions[get_column_letter(col_idx)].width = widths.get(header, 36)

    readonly_cols = list(range(1, decision_col_idx))
    for col_idx in readonly_cols:
        for r in range(2, n_rows + 2):
            ws.cell(row=r, column=col_idx).fill = READONLY_FILL
            ws.cell(row=r, column=col_idx).alignment = WRAP
    for r in range(2, n_rows + 2):
        for col_idx in range(decision_col_idx, len(headers) + 1):
            ws.cell(row=r, column=col_idx).alignment = WRAP

    col_letter = get_column_letter(decision_col_idx)
    for r, options in enumerate(per_row_options, start=2):
        dv = DataValidation(type="list", formula1=f'"{options}"', allow_blank=True)
        ws.add_data_validation(dv)
        dv.add(f"{col_letter}{r}")


def build_bucket3_rows(wb, items, data):
    if not items:
        return
    ws = wb.create_sheet("Bucket 3 - Asymmetric")
    headers = ["base_id", "Perturbation type", "English Source", "Original Perturbed text (you marked this Correct)",
               "Other reviewer's proposed fix", "Other reviewer's reasoning",
               "Decision", "Corrected version (only if 'Neither')", "Notes"]
    per_row_options = []
    for r, (key, correct_reviewer, incorrect_reviewer) in enumerate(items, start=2):
        own_row = data[correct_reviewer][key]
        other_row = data[incorrect_reviewer][key]
        ws.cell(row=r, column=1, value=key[0])
        ws.cell(row=r, column=2, value=key[1])
        ws.cell(row=r, column=3, value=own_row["English Source"])
        ws.cell(row=r, column=4, value=own_row["Perturbed text"])
        if key in NO_FIX_GIVEN_BUCKET3:
            ws.cell(row=r, column=5, value="(No fix or reason given -- the other reviewer marked this Incorrect with no explanation.)")
            ws.cell(row=r, column=6, value="")
            per_row_options.append("Original stands,Neither - write new")
        else:
            ws.cell(row=r, column=5, value=other_row["Corrected version"])
            ws.cell(row=r, column=6, value=other_row["Notes"] or "")
            per_row_options.append("Original stands,Accept fix,Neither - write new")
    style_tab(ws, headers, decision_col_idx=7, n_rows=len(items), per_row_options=per_row_options)


def main():
    data = {}
    for reviewer, (path, sheet) in CYCLE1_FILES.items():
        data[reviewer] = load_cycle1_file(path, sheet)
        print(f"Loaded {reviewer}: {len(data[reviewer])} rows from {path.name}")

    key_sets = [set(rows.keys()) for rows in data.values()]
    if key_sets[0] != key_sets[1]:
        raise SystemExit("(base_id, perturbation_type) keys differ between reviewers -- aborting, needs manual check.")

    buckets = classify(data)
    counts = {b: sum(1 for v in buckets.values() if v == b) for b in (1, 2, 3, 4)}
    print("Bucket counts:", counts)

    bucket3_keys = [k for k, b in buckets.items() if b == 3]
    bucket4_keys = [k for k, b in buckets.items() if b == 4]

    bucket3_by_adjudicator = {r: [] for r in REVIEWERS}
    for key in bucket3_keys:
        c1 = data[REVIEWERS[0]][key]["Correctness"]
        correct_reviewer = REVIEWERS[0] if c1 == "Correct" else REVIEWERS[1]
        incorrect_reviewer = REVIEWERS[1] if correct_reviewer == REVIEWERS[0] else REVIEWERS[0]
        bucket3_by_adjudicator[correct_reviewer].append((key, correct_reviewer, incorrect_reviewer))

    # Bucket 4: only one item, and it's the auto-resolve special case --
    # no random-assignment machinery needed this round, but keep the
    # bookkeeping explicit rather than silently skip it.
    auto_resolved_bucket4 = {}
    manual_bucket4_keys = []
    for key in bucket4_keys:
        if key in AUTO_RESOLVE_BUCKET4:
            d1_fix = norm(data[REVIEWERS[0]][key]["Corrected version"])
            d2_fix = norm(data[REVIEWERS[1]][key]["Corrected version"])
            chosen_fix = d1_fix if d1_fix else d2_fix
            chosen_reviewer = REVIEWERS[0] if d1_fix else REVIEWERS[1]
            auto_resolved_bucket4[key_str(key)] = {"final_text": chosen_fix, "resolved_by": chosen_reviewer,
                                                    "reason": "other reviewer gave no competing fix -- auto-resolved, no Cycle 2 row"}
        else:
            manual_bucket4_keys.append(key)

    if manual_bucket4_keys:
        raise SystemExit(f"Unexpected bucket-4 items with no handling plan: {manual_bucket4_keys} -- "
                          "extend AUTO_RESOLVE_BUCKET4 or add random-assignment logic before proceeding.")

    print("Bucket 3 adjudicator counts:", {r: len(v) for r, v in bucket3_by_adjudicator.items()})
    print("Bucket 4: auto-resolved (no Cycle 2 needed):", list(auto_resolved_bucket4.keys()))

    OUT_REVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    classification_out = {
        "language": "en_para_syno",
        "cycle1_source_files": {r: str(CYCLE1_FILES[r][0]) for r in REVIEWERS},
        "matching_rule": "exact string match, only trailing whitespace trimmed",
        "bucket_counts": counts,
        "buckets": {key_str(k): v for k, v in buckets.items()},
        "manual_handling": {
            "no_fix_given_bucket3": [key_str(k) for k in NO_FIX_GIVEN_BUCKET3],
            "auto_resolve_bucket4": auto_resolved_bucket4,
        },
    }
    with open(OUT_REVIEWS_DIR / "parasyno_cycle1_classification.json", "w", encoding="utf-8") as f:
        json.dump(classification_out, f, ensure_ascii=False, indent=2)
    print(f"Wrote {OUT_REVIEWS_DIR / 'parasyno_cycle1_classification.json'}")

    OUT_SHEETS_DIR.mkdir(parents=True, exist_ok=True)
    for reviewer in REVIEWERS:
        b3_items = bucket3_by_adjudicator[reviewer]
        if not b3_items:
            print(f"  {reviewer}: no Cycle 2 items, skipping.")
            continue

        wb = Workbook()
        wb.remove(wb.active)
        instr = [
            "You are adjudicating disagreements from Cycle 1 English PARA/SYNO review.",
            "",
            "Bucket 3 tab: you marked the original perturbed text Correct, the other reviewer",
            "marked it Incorrect. Decide:",
            "  - Original stands: the text is fine as-is.",
            "  - Accept fix: the other reviewer's proposed fix is correct.",
            "    (Not offered on rows where no fix was given -- see that row's notes.)",
            "  - Neither - write new: neither is right; write your own correction in 'Corrected version'.",
            "",
            "Only fill in 'Corrected version' if you chose 'Neither - write new'. Notes are optional.",
        ]
        write_instructions_sheet(wb, instr)
        build_bucket3_rows(wb, b3_items, data)

        out_path = OUT_SHEETS_DIR / f"ParaSyno_Cycle2_{reviewer}.xlsx"
        wb.save(out_path)
        print(f"  Wrote {out_path} (bucket3={len(b3_items)})")

    print("\nDone. Upload each .xlsx to Google Sheets as before. Raw Cycle 1 files were not modified.")


if __name__ == "__main__":
    main()
