"""
generate_cycle2_parasyno_translation.py

Cycle 1 -> Cycle 2 for the dual-candidate Indic PARA/SYNO translation review
(sheets built by generate_review_sheets_parasyno_translation.py). Each PARA or
SYNO item shows two machine candidates (IndicTrans2, Google Translate), each
judged Correct/Incorrect by both reviewers, plus an optional "Corrected
version" and a "Same as NO Translation" flag.

Resolution rule (user decision 2026-10-20), applied per item in this order:
  1. Both reviewers wrote the same "Corrected version" -> use it
     (human-written and agreed by both).
  2. Else, if anyone ticked "Same as NO Translation" -> Cycle 2, because a
     candidate can be an accurate translation yet lose the perturbation.
  3. Else, IndicTrans2 accepted by both -> IndicTrans2. It comes before
     Google because the FT-NO gold was built from IndicTrans2, so using the
     same MT system keeps the NO vs PARA/SYNO comparison free of an
     MT-engine switch.
  4. Else, Google accepted by both -> Google.
  5. Else -> Cycle 2.

Cycle 2 shows each unresolved item to one adjudicator, chosen by a seeded
(42), balanced random assignment. The sheet shows the English source, the
resolved NO translation for reference, both machine candidates, and the two
reviewers' corrections blinded as Version A / Version B. The adjudicator
picks one of the four texts or writes a new one.

Raw reviewer files are read-only here. Outputs are new, separate files.

USAGE (run from inside berkeley-function-call-leaderboard):
    python translation/generate_cycle2_parasyno_translation.py ta
"""

import json
import random
import sys
from collections import Counter
from pathlib import Path

import openpyxl
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

REVIEW_DIR = Path("data/human_review")
LANGS = {
    "ta": {
        "name": "Tamil",
        "reviewers": {
            "Rohan": REVIEW_DIR / "Tamil_PARA_SYNO_Rohan.xlsx",
            "Dhayanidhi": REVIEW_DIR / "Tamil_PARA_SYNO_Dhayanidhi.xlsx",
        },
        "resolved_no": Path("data/reviews/tamil_final_resolved.jsonl"),
        # Observed by reading the sheets, not detectable by rule. Recorded, not fixed.
        "known_data_issues": {
            "multiple_186|PARA": "Rohan marked IndicTrans2 'Correct' but his own note says it turns 'brownie' "
                                 "into 'பழச்சாறு' (fruit juice); likely a mis-click. Goes to Cycle 2 regardless.",
        },
    },
}
RANDOM_SEED = 42

# Column layout of the review tab (see generate_review_sheets_parasyno_translation.py).
COL = {"base_id": 1, "type": 2, "english": 3, "it2": 4, "it2_qa": 5, "google": 6, "google_qa": 7,
       "it2_verdict": 8, "google_verdict": 9, "same_as_no": 18, "corrected": 20, "notes": 21}
READONLY_COLS = range(2, 8)
N_COLS = 21

HEADER_FILL = PatternFill(start_color="3D3A7A", end_color="3D3A7A", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True)
READONLY_FILL = PatternFill(start_color="F0F4F8", end_color="F0F4F8", fill_type="solid")
WRAP = Alignment(wrap_text=True, vertical="top")
DECISIONS = ["IndicTrans2 candidate", "Google candidate", "Version A", "Version B", "Neither - write new"]


def norm(v):
    return "" if v is None else str(v).strip()


def id_key(item):
    bid, ptype = item.split("|")
    return (int(bid.rsplit("_", 1)[-1]), ptype)


def load_review(path, tab):
    ws = openpyxl.load_workbook(path, data_only=True)[tab]
    items, current_bid = {}, None
    for r in range(2, ws.max_row + 1):
        if norm(ws.cell(r, COL["base_id"]).value):
            current_bid = norm(ws.cell(r, COL["base_id"]).value)  # merged across the 3 rows of a base_id
        ptype = norm(ws.cell(r, COL["type"]).value)
        if ptype not in ("PARA", "SYNO"):
            continue
        items[f"{current_bid}|{ptype}"] = {
            "row": r,
            "cells": [norm(ws.cell(r, c).value) for c in range(1, N_COLS + 1)],
            "english": norm(ws.cell(r, COL["english"]).value),
            "it2": norm(ws.cell(r, COL["it2"]).value),
            "google": norm(ws.cell(r, COL["google"]).value),
            "it2_verdict": norm(ws.cell(r, COL["it2_verdict"]).value),
            "google_verdict": norm(ws.cell(r, COL["google_verdict"]).value),
            "same_as_no": norm(ws.cell(r, COL["same_as_no"]).value).upper() == "TRUE",
            "corrected": norm(ws.cell(r, COL["corrected"]).value),
            "notes": norm(ws.cell(r, COL["notes"]).value),
        }
    return items, ws


def main():
    lang = sys.argv[1] if len(sys.argv) > 1 else "ta"
    cfg = LANGS[lang]
    name = cfg["name"]
    tab = f"{name} PARA-SYNO Review"
    r1, r2 = list(cfg["reviewers"])

    template_ws = openpyxl.load_workbook(
        f"data/review_sheets/{name}_ParaSyno_Translation_review_template.xlsx", data_only=True)[tab]
    data = {r: load_review(path, tab)[0] for r, path in cfg["reviewers"].items()}

    # --- Validate ---
    errors = []
    for r in (r1, r2):
        if len(data[r]) != 400:
            errors.append(f"{r}: {len(data[r])} PARA/SYNO items, expected 400")
        for item, x in data[r].items():
            for c in READONLY_COLS:
                if x["cells"][c - 1] != norm(template_ws.cell(x["row"], c).value):
                    errors.append(f"{r} {item}: read-only column {c} differs from the template")
            for v in ("it2_verdict", "google_verdict"):
                if x[v] not in ("Correct", "Incorrect"):
                    errors.append(f"{r} {item}: {v} is {x[v]!r}")
    if set(data[r1]) != set(data[r2]):
        errors.append("item sets differ between reviewers")
    if errors:
        print("VALIDATION ERRORS:")
        for e in errors[:50]:
            print(" -", e)
        raise SystemExit("Aborting.")

    resolved_no = {}
    with open(cfg["resolved_no"], encoding="utf-8") as f:
        for line in f:
            e = json.loads(line)
            resolved_no[e["base_id"]] = e["final_text"]

    # --- Classify ---
    classification, cycle2_items = {}, []
    for item in sorted(data[r1], key=id_key):
        a, b = data[r1][item], data[r2][item]
        entry = {
            "english_source": a["english"],
            "verdicts": {r1: {"it2": a["it2_verdict"], "google": a["google_verdict"]},
                         r2: {"it2": b["it2_verdict"], "google": b["google_verdict"]}},
            "same_as_no_flag": {r1: a["same_as_no"], r2: b["same_as_no"]},
        }
        if a["corrected"] and a["corrected"] == b["corrected"]:
            entry.update(step=1, resolution="agreed_human_correction", final_text=a["corrected"])
        elif a["same_as_no"] or b["same_as_no"]:
            entry.update(step=2, resolution="cycle2_same_as_no")
        elif a["it2_verdict"] == b["it2_verdict"] == "Correct":
            entry.update(step=3, resolution="indictrans2_accepted_by_both", final_text=a["it2"])
        elif a["google_verdict"] == b["google_verdict"] == "Correct":
            entry.update(step=4, resolution="google_accepted_by_both", final_text=a["google"])
        else:
            entry.update(step=5, resolution="cycle2_no_agreed_text")
        if entry["resolution"].startswith("cycle2"):
            cycle2_items.append(item)
        if item in cfg["known_data_issues"]:
            entry["known_data_issue"] = cfg["known_data_issues"][item]
        classification[item] = entry

    counts = Counter(e["resolution"] for e in classification.values())
    print(f"{name} PARA/SYNO Cycle 1 resolution:", dict(counts))

    # --- Cycle 2 assignment (seeded, balanced, blinded) ---
    rng = random.Random(RANDOM_SEED)
    adjudicators = ([r1, r2] * (len(cycle2_items) // 2 + 1))[: len(cycle2_items)]
    rng.shuffle(adjudicators)
    assignment = {}
    for item, adj in zip(cycle2_items, adjudicators):
        order = [r1, r2]
        rng.shuffle(order)
        assignment[item] = {"adjudicator": adj, "version_a_author": order[0], "version_b_author": order[1]}

    out_reviews = Path("data/reviews")
    prefix = f"{name.lower()}_parasyno_translation"
    with open(out_reviews / f"{prefix}_cycle1_classification.json", "w", encoding="utf-8") as f:
        json.dump({
            "language": lang,
            "source_files": {r: str(p) for r, p in cfg["reviewers"].items()},
            "rule": "1 agreed human correction > 2 Same-as-NO -> Cycle 2 > 3 IndicTrans2 accepted by both > "
                    "4 Google accepted by both > 5 Cycle 2 (user decision 2026-10-20)",
            "counts": dict(counts),
            "items": classification,
        }, f, ensure_ascii=False, indent=2)
    with open(out_reviews / f"{prefix}_cycle2_assignment.json", "w", encoding="utf-8") as f:
        json.dump({"language": lang, "random_seed": RANDOM_SEED,
                   "note": "version_a_author/version_b_author are hidden from the adjudicator (blinded as Version A/B).",
                   "assignment": assignment}, f, ensure_ascii=False, indent=2)
    print(f"Wrote {out_reviews / (prefix + '_cycle1_classification.json')} and "
          f"{out_reviews / (prefix + '_cycle2_assignment.json')}")

    # --- Cycle 2 sheets ---
    out_sheets = Path("data/review_sheets/cycle2")
    out_sheets.mkdir(parents=True, exist_ok=True)
    headers = ["Item", "English Source", f"{name} NO translation (reference)", "IndicTrans2 candidate",
               "Google candidate", "Version A", "Version B", "Decision", "Corrected version (only if 'Neither')",
               "Notes"]
    for reviewer in (r1, r2):
        mine = [i for i in cycle2_items if assignment[i]["adjudicator"] == reviewer]
        if not mine:
            print(f"  {reviewer}: no Cycle 2 items.")
            continue
        wb = Workbook()
        ws_i = wb.active
        ws_i.title = "Instructions"
        ws_i.column_dimensions["A"].width = 110
        lines = [
            f"Cycle 2 -- {name} PARA/SYNO translation adjudication",
            "",
            "For each item below, the two reviewers did not agree on one final translation.",
            "You see the English PARA/SYNO source, the already-final NO translation (for reference only),",
            "both machine candidates, and the two reviewers' own corrections shown as Version A and Version B",
            "(not labelled by reviewer, to avoid bias).",
            "",
            "Pick the single best translation in 'Decision':",
            "  - IndicTrans2 candidate / Google candidate / Version A / Version B: use that text as-is.",
            "  - Neither - write new: write your own translation in 'Corrected version'.",
            "",
            "The chosen text must be a correct translation AND read as a different phrasing from the NO "
            "translation (the PARA/SYNO difference must survive translation).",
            "Only fill 'Corrected version' if you chose 'Neither - write new'. Notes are optional.",
        ]
        for i, line in enumerate(lines, start=1):
            ws_i.cell(row=i, column=1, value=line).font = Font(bold=(i == 1), size=(14 if i == 1 else 11))
        ws = wb.create_sheet("Cycle 2 - Conflicts")
        for c, h in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=c, value=h)
            cell.fill, cell.font, cell.alignment = HEADER_FILL, HEADER_FONT, WRAP
            ws.column_dimensions[get_column_letter(c)].width = 18 if c in (1, 8) else 38
        ws.freeze_panes = "A2"
        for r, item in enumerate(mine, start=2):
            bid = item.split("|")[0]
            a = assignment[item]
            src = data[r1][item]
            values = [item.replace("|", " "), src["english"], resolved_no[bid], src["it2"], src["google"],
                      data[a["version_a_author"]][item]["corrected"], data[a["version_b_author"]][item]["corrected"]]
            for c, v in enumerate(values, start=1):
                cell = ws.cell(row=r, column=c, value=v)
                cell.fill, cell.alignment = READONLY_FILL, WRAP
            for c in (8, 9, 10):
                ws.cell(row=r, column=c).alignment = WRAP
        dv = DataValidation(type="list", formula1='"' + ",".join(DECISIONS) + '"', allow_blank=True)
        ws.add_data_validation(dv)
        dv.add(f"H2:H{len(mine) + 1}")
        out = out_sheets / f"{name}_ParaSyno_Cycle2_{reviewer}.xlsx"
        wb.save(out)
        print(f"  Wrote {out} ({len(mine)} items: {mine})")


if __name__ == "__main__":
    main()
