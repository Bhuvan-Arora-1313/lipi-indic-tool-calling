"""
generate_review_sheets_parasyno_translation.py

Builds one dual-candidate Cycle 1 review .xlsx per language (Hindi/Tamil/
Gujarati) for the PARA/SYNO Indic translations. Each row shows the
IndicTrans2 candidate AND the Google Translate candidate side by side --
reviewers judge each independently rather than being forced to pick one
up front, so a case where reviewers disagree on which source is "the"
correct one (one says IndicTrans2 is correct, the other says Google
Translate is correct) still resolves cleanly: it's just bucket 3
(asymmetric) on each source's own 4-bucket classification, handled by
the exact same Cycle 1/Cycle 2 machinery already used for the base NO
translations (generate_cycle2_*.py). If BOTH sources end up validated as
"Correct" for a given item, that's a real, expected outcome (two
independent correct translations) -- picking a final one at export time
is a separate, later decision, not something to resolve here.

Two independent "Correctness" dropdowns (one per source) rather than the
NO-translation template's single Correct/Incorrect, but the same shared
issue-type grid and free-text Notes (specify which source an issue
applies to there if both are marked Incorrect for different reasons) --
doubling all issue columns per source was considered and rejected as
unnecessary review burden for a distinction Notes already covers.

Each base_id's 3 rows now include a read-only NO REFERENCE row (grey
fill, no dropdowns) above its PARA and SYNO rows: the original English
NO query and its already-resolved NO translation (Hindi and Tamil since 2026-09-19,
Gujarati since 2026-10-20). A language without a resolved NO file falls
back to the pre-review IndicTrans2 NO translation, marked as such. This exists for a
specific, real failure mode a translation model can introduce that the
English-level PARA/SYNO review can't catch: the whole point of a
PARA/SYNO perturbation is a different surface form of the same query,
but a translation model can independently collapse that difference back
together -- e.g. English NO and English PARA are genuinely distinct
sentences, yet their Hindi translations come out identical or nearly so.
Reviewers need the NO translation sitting right next to PARA/SYNO to
actually check for that, hence the new "Same as NO Translation" issue
type below (confirmed with the user 2026-09-19).

Input: data/translations/multiple_translations.jsonl (IndicTrans2) +
data/translations/multiple_translations_google.jsonl (Google Translate),
both filtered to PARA/SYNO rows, plus data/perturbations/
en_multiple_perturbations.jsonl (English NO) and data/reviews/
{hindi,tamil,gujarati}_final_resolved.jsonl (resolved NO translations) for the
reference row. Automated check columns come from each source's own QA
file if present (check_translation_fidelity.py run against both).

USAGE (run from inside berkeley-function-call-leaderboard):
    python translation/generate_review_sheets_parasyno_translation.py          # all languages
    python translation/generate_review_sheets_parasyno_translation.py gu       # only the listed language(s)
"""

import json
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import FormulaRule
from openpyxl.utils import get_column_letter

INDICTRANS2_PATH = Path("data/translations/multiple_translations.jsonl")
INDICTRANS2_QA_PATH = Path("data/translations/multiple_translations_qa.jsonl")
GOOGLE_PATH = Path("data/translations/multiple_translations_google.jsonl")
GOOGLE_QA_PATH = Path("data/translations/multiple_translations_google_qa.jsonl")
EN_NO_PATH = Path("data/perturbations/en_multiple_perturbations.jsonl")
# Resolved (Cycle 1+2) NO translation per language, where available. Falls
# back to the raw pre-review IndicTrans2 NO translation for any language
# without a resolved file -- see load_no_reference below.
RESOLVED_NO_PATHS = {
    "hi": Path("data/reviews/hindi_final_resolved.jsonl"),
    "ta": Path("data/reviews/tamil_final_resolved.jsonl"),
    "gu": Path("data/reviews/gujarati_final_resolved.jsonl"),
}
OUT_DIR = Path("data/review_sheets")

LANG_NAMES = {"hi": "Hindi", "ta": "Tamil", "gu": "Gujarati"}

ISSUE_TYPES = [
    ("Number/Value Issue", "Number/value changed or dropped"),
    ("Wrong Word/Mistranslation", "Wrong word choice / mistranslation"),
    ("Grammar Error", "Grammar error"),
    ("Meaning Changed", "Meaning changed"),
    ("Missing Content", "Missing content"),
    ("Added Content", "Added content (hallucination)"),
    ("Script/Formatting", "Script/formatting issue"),
    ("Invalid Swap", "Not a valid paraphrase/synonym swap (too different, or unchanged) -- PARA/SYNO only"),
    ("Same as NO Translation", "Reads the same, or nearly the same, as the NO translation shown above -- "
                               "the perturbation's distinctiveness got lost in translation, even if the "
                               "English source was a valid paraphrase/synonym swap"),
    ("Other", "Other"),
]

GUIDELINES = [
    "Each query now shows 3 rows: NO (grey, reference only -- the original English query and its "
    "already-reviewed translation, not editable), then PARA and SYNO (the rows you actually review).",
    "IMPORTANT: compare PARA's and SYNO's translations against the NO translation above them. The whole "
    "point of PARA/SYNO is a different phrasing of the same query -- if the Hindi/Tamil/Gujarati translation "
    "reads the same (or nearly the same) as the NO translation, that defeats the purpose even if the English "
    "PARA/SYNO text itself was a perfectly good paraphrase. Tick 'Same as NO Translation' when you see this.",
    "You will see TWO candidate translations per PARA/SYNO row: one from IndicTrans2 (a dedicated MT model), "
    "one from Google Translate. Judge each independently -- mark each Correct or Incorrect on its own merits.",
    "It's normal and fine for BOTH to be Correct (two valid ways to translate the same sentence), "
    "or for only one, or for neither.",
    "Are all numbers and values exactly preserved (nothing changed, dropped, or added)?",
    "Is the full meaning preserved -- nothing added, nothing left out?",
    "Are units, symbols, and exponents (e.g. %, ^, degrees) correctly conveyed, even if reworded as text?",
    "Is the word choice and grammar natural and accurate?",
    "For SYNO rows: is it a word-for-word synonym swap, not a full rewrite of the sentence?",
    "For PARA rows: does it still mean exactly the same thing as the original, just phrased differently?",
]

READONLY_FILL = PatternFill(start_color="F0F4F8", end_color="F0F4F8", fill_type="solid")
REFERENCE_FILL = PatternFill(start_color="E2E2E2", end_color="E2E2E2", fill_type="solid")
FLAG_FILL = PatternFill(start_color="FFF3CD", end_color="FFF3CD", fill_type="solid")
HEADER_FILL = PatternFill(start_color="3D3A7A", end_color="3D3A7A", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True)
WRAP = Alignment(wrap_text=True, vertical="top")


def load_jsonl(path):
    if not path.exists():
        return []
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def build_qa_lookup(qa_path):
    lookup = {}
    for row in load_jsonl(qa_path):
        key = (row["base_id"], row["language"], row["perturbation_type"])
        lookup[key] = row
    return lookup


def format_qa_note(qa_row):
    if qa_row is None:
        return ""
    flags = qa_row.get("flags", ["ok"])
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


def load_no_reference(lang):
    """Returns {base_id: (english_no_text, translated_no_text, is_finalized)}."""
    en_no = {e["base_id"]: e["text"] for e in load_jsonl(EN_NO_PATH) if e["perturbation_type"] == "NO"}

    resolved_path = RESOLVED_NO_PATHS.get(lang)
    if resolved_path and resolved_path.exists():
        resolved = {e["base_id"]: e["final_text"] for e in load_jsonl(resolved_path)}
        return {bid: (en_no[bid], resolved[bid], True) for bid in en_no if bid in resolved}

    # Fallback: not yet Cycle-2-resolved for this language -- use the raw
    # pre-review IndicTrans2 NO translation instead, clearly marked as such.
    raw = {e["base_id"]: e["text"] for e in load_jsonl(INDICTRANS2_PATH)
           if e["language"] == lang and e["perturbation_type"] == "NO"}
    return {bid: (en_no[bid], raw[bid], False) for bid in en_no if bid in raw}


def write_instructions_sheet(wb):
    ws = wb.create_sheet("Instructions", 0)
    ws.column_dimensions["A"].width = 100
    row = 1
    ws.cell(row=row, column=1, value="How to review -- NO reference + two translation candidates").font = Font(bold=True, size=14)
    row += 2
    for g in GUIDELINES:
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
             value="Only fill in the issue-type columns and Notes if at least one Correctness = Incorrect, "
                   "or if you ticked 'Same as NO Translation'. If both are Incorrect for different reasons, "
                   "say which candidate each issue applies to in Notes. 'Corrected version' is optional -- "
                   "only fill it in if you want to suggest a better translation than both candidates shown.").font = Font(italic=True)


def style_sheet(ws, headers, readonly_cols, correctness_cols, issue_col_range, flag_cols,
                reference_rows, editable_rows):
    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = WRAP
    ws.freeze_panes = "A2"

    widths = {"base_id": 14, "Perturbation type": 14, "English Source": 40,
              "IndicTrans2 Translation": 40, "Google Translate Translation": 40,
              "IndicTrans2 Automated check": 26, "Google Translate Automated check": 26,
              "IndicTrans2 Correctness": 16, "Google Translate Correctness": 16,
              "Corrected version": 40, "Notes": 30}
    issue_short_names = {short for short, _ in ISSUE_TYPES}
    for col_idx, header in enumerate(headers, start=1):
        width = 16 if header in issue_short_names else widths.get(header, 22)
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    n_cols = len(headers)
    for r in reference_rows:
        for col_idx in range(1, n_cols + 1):
            ws.cell(row=r, column=col_idx).fill = REFERENCE_FILL
            ws.cell(row=r, column=col_idx).alignment = WRAP

    for col_idx in readonly_cols:
        for r in editable_rows:
            ws.cell(row=r, column=col_idx).fill = READONLY_FILL
            ws.cell(row=r, column=col_idx).alignment = WRAP

    # Dropdowns only ever apply to editable (PARA/SYNO) rows, never the
    # grey NO reference row -- there's nothing for a reviewer to decide there.
    editable_ranges = _to_ranges(editable_rows)
    for col_idx in correctness_cols:
        dv = DataValidation(type="list", formula1='"Correct,Incorrect"', allow_blank=True)
        ws.add_data_validation(dv)
        col_letter = get_column_letter(col_idx)
        for start, end in editable_ranges:
            dv.add(f"{col_letter}{start}:{col_letter}{end}")

    issue_dv = DataValidation(type="list", formula1='"TRUE,FALSE"', allow_blank=True)
    ws.add_data_validation(issue_dv)
    start_col, end_col = issue_col_range
    for col_idx in range(start_col, end_col + 1):
        col_letter = get_column_letter(col_idx)
        for start, end in editable_ranges:
            issue_dv.add(f"{col_letter}{start}:{col_letter}{end}")

    for flag_col_idx in flag_cols:
        flag_letter = get_column_letter(flag_col_idx)
        for start, end in editable_ranges:
            ws.conditional_formatting.add(
                f"{flag_letter}{start}:{flag_letter}{end}",
                FormulaRule(formula=[f'{flag_letter}{start}<>""'], fill=FLAG_FILL),
            )


def _to_ranges(sorted_rows):
    """Collapses a sorted list of row numbers into contiguous (start, end) ranges."""
    if not sorted_rows:
        return []
    ranges = []
    start = prev = sorted_rows[0]
    for r in sorted_rows[1:]:
        if r == prev + 1:
            prev = r
        else:
            ranges.append((start, prev))
            start = prev = r
    ranges.append((start, prev))
    return ranges


def build_sheet_for_lang(lang):
    lang_name = LANG_NAMES[lang]
    it2_entries = {(e["base_id"], e["perturbation_type"]): e
                   for e in load_jsonl(INDICTRANS2_PATH) if e["language"] == lang and e["perturbation_type"] in ("PARA", "SYNO")}
    goog_entries = {(e["base_id"], e["perturbation_type"]): e
                    for e in load_jsonl(GOOGLE_PATH) if e["language"] == lang and e["perturbation_type"] in ("PARA", "SYNO")}

    if not it2_entries or not goog_entries:
        print(f"  {lang_name}: missing data (IndicTrans2={len(it2_entries)}, Google={len(goog_entries)} PARA/SYNO rows), skipping.")
        return

    it2_qa = build_qa_lookup(INDICTRANS2_QA_PATH)
    goog_qa = build_qa_lookup(GOOGLE_QA_PATH)
    no_reference = load_no_reference(lang)
    no_is_finalized = all(v[2] for v in no_reference.values()) if no_reference else True

    by_base_id = {}
    for key, e in it2_entries.items():
        by_base_id.setdefault(key[0], {})[key[1]] = e
    base_ids = sorted(by_base_id.keys(), key=lambda b: int(b.rsplit("_", 1)[-1]))

    wb = Workbook()
    wb.remove(wb.active)
    write_instructions_sheet(wb)
    ws = wb.create_sheet(f"{lang_name} PARA-SYNO Review")  # sheet names cap at 31 chars in Excel

    issue_headers = [short for short, _ in ISSUE_TYPES]
    headers = (["base_id", "Perturbation type", "English Source",
                "IndicTrans2 Translation", "IndicTrans2 Automated check",
                "Google Translate Translation", "Google Translate Automated check",
                "IndicTrans2 Correctness", "Google Translate Correctness"]
               + issue_headers + ["Corrected version", "Notes"])

    r = 2
    skipped = []
    reference_rows = []
    editable_rows = []
    for base_id in base_ids:
        by_type = by_base_id[base_id]
        if "PARA" not in by_type or "SYNO" not in by_type:
            skipped.append(base_id)
            continue
        if (base_id, "PARA") not in goog_entries or (base_id, "SYNO") not in goog_entries:
            skipped.append(base_id)
            continue
        if base_id not in no_reference:
            skipped.append(base_id)
            continue

        english_no, translated_no, finalized = no_reference[base_id]
        start_row = r

        # NO reference row -- grey, read-only, no dropdowns.
        ws.cell(row=r, column=1, value=base_id)
        ws.cell(row=r, column=2, value="NO (reference)")
        ws.cell(row=r, column=3, value=english_no)
        ws.cell(row=r, column=4, value=translated_no)
        ws.cell(row=r, column=5, value="" if finalized else "NOT YET Cycle-2-resolved -- pre-review IndicTrans2 text shown")
        reference_rows.append(r)
        r += 1

        for ptype in ("PARA", "SYNO"):
            it2_row = by_type[ptype]
            goog_row = goog_entries[(base_id, ptype)]
            it2_qa_row = it2_qa.get((base_id, lang, ptype))
            goog_qa_row = goog_qa.get((base_id, lang, ptype))

            ws.cell(row=r, column=1, value=base_id)
            ws.cell(row=r, column=2, value=ptype)
            ws.cell(row=r, column=3, value=it2_row["source_text"])
            ws.cell(row=r, column=4, value=it2_row["text"])
            ws.cell(row=r, column=5, value=format_qa_note(it2_qa_row))
            ws.cell(row=r, column=6, value=goog_row["text"])
            ws.cell(row=r, column=7, value=format_qa_note(goog_qa_row))
            editable_rows.append(r)
            r += 1

        ws.merge_cells(start_row=start_row, start_column=1, end_row=start_row + 2, end_column=1)

    n_rows = r - 2
    if skipped:
        print(f"  {lang_name}: skipped {len(skipped)} base_id(s) missing full data in one or more sources: {skipped}")
    if not no_is_finalized:
        print(f"  {lang_name}: NO reference not yet Cycle-2-resolved -- using pre-review IndicTrans2 NO text "
              f"(clearly marked in the sheet). Re-run this script after {lang_name}'s NO translation is finalized "
              f"to refresh the reference column.")

    n_issue = len(ISSUE_TYPES)
    style_sheet(ws, headers, readonly_cols=[1, 2, 3, 4, 5, 6, 7],
                correctness_cols=[8, 9], issue_col_range=(10, 9 + n_issue),
                flag_cols=[5, 7], reference_rows=reference_rows, editable_rows=editable_rows)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{lang_name}_ParaSyno_Translation_review_template.xlsx"
    wb.save(out_path)
    print(f"  Wrote {out_path} ({n_rows} rows, {len(reference_rows)} reference + {len(editable_rows)} to review)")


def main():
    print("Building dual-candidate PARA/SYNO translation review templates (with NO reference row)...")
    langs = sys.argv[1:] or ["hi", "ta", "gu"]
    unknown = [l for l in langs if l not in LANG_NAMES]
    if unknown:
        raise SystemExit(f"Unknown language code(s) {unknown}; use any of {list(LANG_NAMES)}")
    for lang in langs:
        build_sheet_for_lang(lang)
    print("\nDone. Upload each .xlsx to Google Sheets, duplicate per reviewer, and rename.")


if __name__ == "__main__":
    main()
