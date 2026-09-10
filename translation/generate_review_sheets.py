"""
generate_review_sheets.py

Builds one .xlsx review template per language (Hindi/Tamil/Gujarati) and
one for the English PARA/SYNO perturbations, from the same canonical
data + QA files used to build the Label Studio projects. Reuses that
data, just changes the output format (a spreadsheet the user uploads to
Google Sheets and duplicates/renames per reviewer, since this session
has no direct Google Sheets access -- see LOG.md 2026-08-25).

Read-only columns: base_id, source text, the text being reviewed, and an
"Automated check" column -- blank for clean rows, a short note for
flagged ones (same silence-for-clean-rows principle as the Label Studio
qa_warning design: a "no issues" badge on every row risks automation
bias, reviewers trusting it instead of reading closely).

Editable columns: Correctness (dropdown), Issue type (free text -- Sheets
has no clean native multi-select in one cell), Corrected version, Notes.

Google Sheets imports .xlsx data validation and conditional formatting
reasonably well; it does NOT carry over Excel's own protection/locking,
which is a different, Sheets-native mechanism -- set "Protect ranges" on
the read-only columns manually after uploading each sheet.

USAGE (run from inside berkeley-function-call-leaderboard):
    python translation/generate_review_sheets.py
"""

import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import FormulaRule
from openpyxl.utils import get_column_letter

TRANSLATIONS_PATH = Path("data/translations/multiple_translations.jsonl")
TRANSLATIONS_QA_PATH = Path("data/translations/multiple_translations_qa.jsonl")
PERTURBATIONS_PATH = Path("data/perturbations/en_multiple_perturbations.jsonl")
PERTURBATIONS_QA_PATH = Path("data/perturbations/en_multiple_perturbations_qa.jsonl")
OUT_DIR = Path("data/review_sheets")

LANG_NAMES = {"hi": "Hindi", "ta": "Tamil", "gu": "Gujarati"}

# (short column header, full meaning for the Instructions tab legend).
# Checkbox columns, not free text: a reviewer ticks TRUE for every issue
# that applies, so multiple simultaneous issues on one item aren't lost
# the way a single free-text or single-select field would lose them, and
# the result stays cleanly aggregable later (consistent categories, not
# reviewer-to-reviewer free-text variation).
ISSUE_TYPES = [
    ("Number/Value Issue", "Number/value changed or dropped"),
    ("Wrong Word/Mistranslation", "Wrong word choice / mistranslation"),
    ("Grammar Error", "Grammar error"),
    ("Meaning Changed", "Meaning changed"),
    ("Missing Content", "Missing content"),
    ("Added Content", "Added content (hallucination)"),
    ("Script/Formatting", "Script/formatting issue"),
    ("Invalid Swap", "Not a valid paraphrase/synonym swap (too different, or unchanged) -- PARA/SYNO only"),
    ("Other", "Other"),
]

TRANSLATION_GUIDELINES = [
    "Are all numbers and values exactly preserved (nothing changed, dropped, or added)?",
    "Is the full meaning preserved -- nothing added, nothing left out?",
    "Are units, symbols, and exponents (e.g. %, ^, degrees) correctly conveyed, even if reworded as text?",
    "Is the word choice and grammar natural and accurate?",
]
PERTURBATION_EXTRA_GUIDELINES = [
    "For SYNO rows: is it a word-for-word synonym swap, not a full rewrite of the sentence?",
    "For PARA rows: does it still mean exactly the same thing as the original, just phrased differently?",
]

READONLY_FILL = PatternFill(start_color="F0F4F8", end_color="F0F4F8", fill_type="solid")
FLAG_FILL = PatternFill(start_color="FFF3CD", end_color="FFF3CD", fill_type="solid")
HEADER_FILL = PatternFill(start_color="3D3A7A", end_color="3D3A7A", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True)
WRAP = Alignment(wrap_text=True, vertical="top")


def load_jsonl(path):
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def build_qa_lookup(qa_path, key_fields):
    if not qa_path.exists():
        return {}
    lookup = {}
    for row in load_jsonl(qa_path):
        key = tuple(row[k] for k in key_fields)
        lookup[key] = row
    return lookup


def format_qa_note(qa_row):
    """Plain text, not HTML -- this is a real spreadsheet cell, not a UI
    template, so there's no markup-in-data concern to begin with (see
    LOG.md 2026-08-24 for why that mattered in Label Studio)."""
    if qa_row is None:
        return ""
    flags = qa_row.get("flags")
    if flags is None:
        flags = [qa_row.get("flag", "ok")]
    if not flags or flags == ["ok"]:
        return ""
    parts = []
    if "number_mismatch" in flags:
        missing = qa_row.get("missing_numbers", [])
        added = qa_row.get("added_numbers", [])
        detail = []
        if missing:
            detail.append(f"missing from translation: {missing}")
        if added:
            detail.append(f"not in source: {added}")
        parts.append("Possible number mismatch -- " + "; ".join(detail))
    if "marker_dropped" in flags:
        dropped = qa_row.get("dropped_markers", {})
        parts.append(f"Possible dropped unit/exponent marker ({', '.join(dropped.keys())})")
    return " | ".join(parts)


def write_instructions_sheet(wb, guidelines):
    ws = wb.create_sheet("Instructions", 0)
    ws.column_dimensions["A"].width = 100
    row = 1
    ws.cell(row=row, column=1, value="How to review").font = Font(bold=True, size=14)
    row += 2
    for g in guidelines:
        ws.cell(row=row, column=1, value=f"- {g}")
        row += 1
    row += 1
    ws.cell(row=row, column=1, value="Issue type columns -- tick TRUE for every one that applies:").font = Font(bold=True)
    row += 1
    for short, full in ISSUE_TYPES:
        ws.cell(row=row, column=1, value=f"- {short}: {full}")
        row += 1
    row += 1
    ws.cell(row=row, column=1,
             value="Only fill in the issue-type columns, 'Corrected version', and 'Notes' if Correctness = "
                   "Incorrect. Leave them blank if Correct. More than one issue type can be TRUE at once.").font = Font(italic=True)


def style_sheet(ws, headers, readonly_cols, correctness_col_idx, issue_col_range, flag_col_idx, n_rows):
    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = WRAP
    ws.freeze_panes = "A2"

    widths = {"base_id": 14, "Perturbation type": 14, "English Source": 45, "Translation": 45,
              "PARA": 45, "SYNO": 45, "Automated check": 30, "Correctness": 12,
              "Corrected version": 45, "Notes": 30}
    issue_short_names = {short for short, _ in ISSUE_TYPES}
    for col_idx, header in enumerate(headers, start=1):
        width = 14 if header in issue_short_names else widths.get(header, 22)
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    for col_idx in readonly_cols:
        for r in range(2, n_rows + 2):
            ws.cell(row=r, column=col_idx).fill = READONLY_FILL
            ws.cell(row=r, column=col_idx).alignment = WRAP

    # Correctness dropdown
    dv = DataValidation(type="list", formula1='"Correct,Incorrect"', allow_blank=True)
    ws.add_data_validation(dv)
    col_letter = get_column_letter(correctness_col_idx)
    dv.add(f"{col_letter}2:{col_letter}{n_rows + 1}")

    # Issue-type checkbox columns: a TRUE/FALSE dropdown per column, one
    # per issue type, so a reviewer can tick multiple simultaneous issues
    # rather than being forced into one free-text field or one choice.
    issue_dv = DataValidation(type="list", formula1='"TRUE,FALSE"', allow_blank=True)
    ws.add_data_validation(issue_dv)
    start_col, end_col = issue_col_range
    for col_idx in range(start_col, end_col + 1):
        col_letter = get_column_letter(col_idx)
        issue_dv.add(f"{col_letter}2:{col_letter}{n_rows + 1}")

    # Highlight the automated-check cell yellow when non-empty
    flag_letter = get_column_letter(flag_col_idx)
    ws.conditional_formatting.add(
        f"{flag_letter}2:{flag_letter}{n_rows + 1}",
        FormulaRule(formula=[f'{flag_letter}2<>""'], fill=FLAG_FILL),
    )


def build_translation_sheet(lang):
    lang_name = LANG_NAMES[lang]
    entries = [e for e in load_jsonl(TRANSLATIONS_PATH) if e["language"] == lang and e["perturbation_type"] == "NO"]
    if not entries:
        print(f"  No {lang_name} data found, skipping.")
        return
    qa_lookup = build_qa_lookup(TRANSLATIONS_QA_PATH, ("base_id", "language", "perturbation_type"))
    entries.sort(key=lambda e: int(e["base_id"].rsplit("_", 1)[-1]))

    wb = Workbook()
    wb.remove(wb.active)
    write_instructions_sheet(wb, TRANSLATION_GUIDELINES)
    ws = wb.create_sheet(f"{lang_name} Review")

    issue_headers = [short for short, _ in ISSUE_TYPES]
    headers = (["base_id", "English Source", "Translation", "Automated check", "Correctness"]
               + issue_headers + ["Corrected version", "Notes"])
    for r, e in enumerate(entries, start=2):
        qa_row = qa_lookup.get((e["base_id"], lang, "NO"))
        ws.cell(row=r, column=1, value=e["base_id"])
        ws.cell(row=r, column=2, value=e["source_text"])
        ws.cell(row=r, column=3, value=e["text"])
        ws.cell(row=r, column=4, value=format_qa_note(qa_row))

    n_issue = len(ISSUE_TYPES)
    style_sheet(ws, headers, readonly_cols=[1, 2, 3, 4], correctness_col_idx=5,
                issue_col_range=(6, 5 + n_issue), flag_col_idx=4, n_rows=len(entries))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{lang_name}_review_template.xlsx"
    wb.save(out_path)
    print(f"  Wrote {out_path} ({len(entries)} rows)")


def build_perturbation_sheet():
    entries = load_jsonl(PERTURBATIONS_PATH)
    by_base_id = {}
    for e in entries:
        if e["perturbation_type"] in ("PARA", "SYNO"):
            by_base_id.setdefault(e["base_id"], {})[e["perturbation_type"]] = e
    qa_lookup = build_qa_lookup(PERTURBATIONS_QA_PATH, ("base_id", "perturbation_type"))
    base_ids = sorted(by_base_id.keys(), key=lambda b: int(b.rsplit("_", 1)[-1]))

    wb = Workbook()
    wb.remove(wb.active)
    write_instructions_sheet(wb, TRANSLATION_GUIDELINES + PERTURBATION_EXTRA_GUIDELINES)
    ws = wb.create_sheet("PARA-SYNO Review")

    issue_headers = [short for short, _ in ISSUE_TYPES]
    headers = (["base_id", "Perturbation type", "English Source", "Perturbed text", "Automated check", "Correctness"]
               + issue_headers + ["Corrected version", "Notes"])
    r = 2
    for base_id in base_ids:
        by_type = by_base_id[base_id]
        if "PARA" not in by_type or "SYNO" not in by_type:
            continue
        source_text = by_type["PARA"]["source_text"]
        start_row = r
        for ptype in ("PARA", "SYNO"):
            row = by_type[ptype]
            qa_row = qa_lookup.get((base_id, ptype))
            ws.cell(row=r, column=1, value=base_id)
            ws.cell(row=r, column=2, value=ptype)
            ws.cell(row=r, column=3, value=source_text)
            ws.cell(row=r, column=4, value=row["text"])
            ws.cell(row=r, column=5, value=format_qa_note(qa_row))
            r += 1
        ws.merge_cells(start_row=start_row, start_column=1, end_row=start_row + 1, end_column=1)
        ws.merge_cells(start_row=start_row, start_column=3, end_row=start_row + 1, end_column=3)

    n_rows = r - 2
    n_issue = len(ISSUE_TYPES)
    style_sheet(ws, headers, readonly_cols=[1, 2, 3, 4, 5], correctness_col_idx=6,
                issue_col_range=(7, 6 + n_issue), flag_col_idx=5, n_rows=n_rows)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "PARA_SYNO_review_template.xlsx"
    wb.save(out_path)
    print(f"  Wrote {out_path} ({n_rows} rows)")


def main():
    print("Building review sheet templates...")
    for lang in ("hi", "ta", "gu"):
        build_translation_sheet(lang)
    build_perturbation_sheet()
    print("\nDone. Upload each .xlsx to Google Sheets, duplicate per reviewer, and rename.")


if __name__ == "__main__":
    main()
