"""
resolve_cycle2_gujarati.py

Reads the completed Gujarati Cycle 2 adjudication (Samarth Patel, Dhruv
Kunvarani), validates it against the Cycle 2 assignment built by
`generate_cycle2_gujarati.py`, and writes the final resolved Gujarati
translation for all 200 items. Bucket 1/2 items (resolved after Cycle 1),
the 6 "prefer Dhruv's better translation" items, and the bucket 3/4
adjudication decisions are merged into one file.

Gujarati specifics (see generate_cycle2_gujarati.py's docstring):
- The Google Sheets downloads returned on 2026-10-20 reuse the Cycle 1
  filenames. Each workbook holds the Cycle 1 sheet plus the "Bucket 3" and
  "Bucket 4" Cycle 2 tabs, so Cycle 1 and Cycle 2 are read from the same
  files. The script first checks that the Cycle 1 sheets still give exactly
  the buckets saved in gujarati_cycle1_classification.json, so a later edit
  to a Cycle 1 answer cannot silently change the result.
- No Correctness reinterpretation (that was a Hindi/Anshul-only issue).
- The 6 prefer-Dhruv items resolve to Dhruv's "better translation", recorded
  as their own resolution category.
- multiple_154: the English source is taken from Dhruv's copy (canonical);
  Samarth's copy has a reference-column drift ("What was" vs "Who was").
- Duplicate English queries: BFCL `multiple` repeats 4 English questions
  with different candidate functions (108/195, 109/196, 110/197, 111/198).
  Hindi and Tamil translate each pair identically. In Gujarati, 108 and 195
  were reviewed separately and ended with different wordings. Per the user's
  decision (2026-10-20), 195 takes 108's reviewed text so that the identical
  question reads identically. 108's text is the later, fuller Cycle 2 rewrite
  by Dhruv. The override is applied after normal resolution and recorded on
  the row (`harmonized_with`, `text_before_harmonization`).

Raw reviewer files are read-only here. Output is a new, separate,
fully traceable layer: every row records both reviewers' Cycle 1 verdicts
and, for bucket 3/4, the Cycle 2 adjudicator and decision.

USAGE (run from inside berkeley-function-call-leaderboard):
    python translation/resolve_cycle2_gujarati.py
"""

import json
from collections import Counter
from pathlib import Path

import openpyxl

REVIEW_DIR = Path("data/human_review")
FILES = {
    "Samarth": (REVIEW_DIR / "Gujarati_review_Samarth_Patel.xlsx", "Gujarati Review Samarth Patel"),
    "Dhruv": (REVIEW_DIR / "Gujarati Review - Dhruv Kunvarani.xlsx", "Dhruv Kunvarani Gujarati Review"),
}
REVIEWERS = list(FILES.keys())

CLASSIFICATION_PATH = Path("data/reviews/gujarati_cycle1_classification.json")
ASSIGNMENT_PATH = Path("data/reviews/gujarati_cycle2_bucket4_assignment.json")
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
B3_TAB = "Bucket 3 - Asymmetric"
B4_TAB = "Bucket 4 - Conflicting Fixes"

VALID_B3_DECISIONS = {"Original stands", "Accept fix", "Neither - write new"}
VALID_B4_DECISIONS = {"Version A", "Version B", "Neither - write new"}
NEW_TEXT_COL = "Corrected version (only if 'Neither')"

# {item: source item}. Both must have the identical English query (checked at run time).
HARMONIZE_DUPLICATES = {"multiple_195": "multiple_108"}


def norm(s):
    return "" if s is None else str(s).rstrip()


def id_key(bid):
    return int(bid.rsplit("_", 1)[-1])


def load_rows(wb, sheet, header):
    ws = wb[sheet]
    rows = {}
    for r in range(2, ws.max_row + 1):
        values = [ws.cell(row=r, column=c).value for c in range(1, len(header) + 1)]
        row = dict(zip(header, values))
        if row["base_id"]:
            rows[row["base_id"]] = row
    return rows


def classify(cycle1):
    d1, d2 = cycle1[REVIEWERS[0]], cycle1[REVIEWERS[1]]
    buckets = {}
    for bid in d1:
        c1, c2 = d1[bid]["Correctness"], d2[bid]["Correctness"]
        if c1 == "Correct" and c2 == "Correct":
            buckets[bid] = 1
        elif c1 == "Incorrect" and c2 == "Incorrect":
            buckets[bid] = 2 if norm(d1[bid]["Corrected version"]) == norm(d2[bid]["Corrected version"]) else 4
        else:
            buckets[bid] = 3
    return buckets


def main():
    workbooks = {r: openpyxl.load_workbook(path, data_only=True) for r, (path, _) in FILES.items()}
    cycle1 = {r: load_rows(workbooks[r], FILES[r][1], CYCLE1_HEADER) for r in REVIEWERS}
    b3 = {r: load_rows(workbooks[r], B3_TAB, B3_HEADER) for r in REVIEWERS}
    b4 = {r: load_rows(workbooks[r], B4_TAB, B4_HEADER) for r in REVIEWERS}

    with open(CLASSIFICATION_PATH, encoding="utf-8") as f:
        classification = json.load(f)
    with open(ASSIGNMENT_PATH, encoding="utf-8") as f:
        assignment = json.load(f)["bucket4_assignment"]
    saved_buckets = classification["buckets"]
    prefer_dhruv = classification["prefer_dhruv_better_translation"]

    # --- Validate before trusting anything ---
    errors = []
    for r in REVIEWERS:
        if len(cycle1[r]) != 200:
            errors.append(f"{r}: Cycle 1 sheet has {len(cycle1[r])} rows, expected 200")
    if set(cycle1["Samarth"]) != set(cycle1["Dhruv"]):
        errors.append("Cycle 1 base_id sets differ between reviewers")
    for bid in cycle1["Dhruv"]:
        if norm(cycle1["Samarth"][bid]["Translation"]) != norm(cycle1["Dhruv"][bid]["Translation"]):
            errors.append(f"{bid}: the Translation under review differs between the two copies")

    buckets = classify(cycle1)
    changed = {b: (saved_buckets[b], buckets[b]) for b in buckets if saved_buckets.get(b) != buckets[b]}
    if changed:
        errors.append(f"Cycle 1 answers changed since Cycle 2 was built (saved, now): {changed}")
    for bid, item in prefer_dhruv.items():
        if buckets.get(bid) != 1 or norm(cycle1["Dhruv"][bid]["Corrected version"]) != item["final_text"]:
            errors.append(f"{bid}: prefer-Dhruv item no longer matches the saved classification")

    bucket3_ids = sorted((b for b, v in buckets.items() if v == 3), key=id_key)
    bucket4_ids = sorted((b for b, v in buckets.items() if v == 4), key=id_key)
    bucket3_rows = {**b3["Samarth"], **b3["Dhruv"]}
    bucket4_rows = {**b4["Samarth"], **b4["Dhruv"]}
    if set(bucket3_rows) != set(bucket3_ids) or set(b3["Samarth"]) & set(b3["Dhruv"]):
        errors.append(f"Bucket 3 id mismatch: sheets {sorted(bucket3_rows, key=id_key)} vs expected {bucket3_ids}")
    if set(bucket4_rows) != set(bucket4_ids) or set(b4["Samarth"]) & set(b4["Dhruv"]):
        errors.append(f"Bucket 4 id mismatch: sheets {sorted(bucket4_rows, key=id_key)} vs expected {bucket4_ids}")

    for bid in bucket3_ids:
        adjudicator = "Samarth" if bid in b3["Samarth"] else "Dhruv"
        if cycle1[adjudicator][bid]["Correctness"] != "Correct":
            errors.append(f"{bid}: bucket-3 adjudicator {adjudicator} did not mark it Correct in Cycle 1")
        row = bucket3_rows.get(bid, {})
        if row.get("Decision") not in VALID_B3_DECISIONS:
            errors.append(f"{bid}: invalid/missing bucket-3 decision {row.get('Decision')!r}")
        if row.get("Decision") == "Neither - write new" and not norm(row.get(NEW_TEXT_COL)):
            errors.append(f"{bid}: 'Neither' chosen but no corrected text given")
    for bid in bucket4_ids:
        found_in = "Samarth" if bid in b4["Samarth"] else ("Dhruv" if bid in b4["Dhruv"] else None)
        if found_in != assignment[bid]["adjudicator"]:
            errors.append(f"{bid}: expected adjudicator {assignment[bid]['adjudicator']}, found in {found_in}'s sheet")
        row = bucket4_rows.get(bid, {})
        if row.get("Decision") not in VALID_B4_DECISIONS:
            errors.append(f"{bid}: invalid/missing bucket-4 decision {row.get('Decision')!r}")
        if row.get("Decision") == "Neither - write new" and not norm(row.get(NEW_TEXT_COL)):
            errors.append(f"{bid}: 'Neither' chosen but no corrected text given")
        a = assignment[bid]
        for col, author in (("Version A", a["version_a_author"]), ("Version B", a["version_b_author"])):
            if norm(row.get(col)) != norm(cycle1[author][bid]["Corrected version"]):
                errors.append(f"{bid}: {col} no longer matches {author}'s Cycle 1 fix")

    if errors:
        print("VALIDATION ERRORS:")
        for e in errors:
            print(" -", e)
        raise SystemExit("Aborting -- fix the above before resolving.")
    print(f"Validation clean: Cycle 1 buckets {dict(sorted(Counter(buckets.values()).items()))} match the saved "
          f"classification; Cycle 2 bucket 3 {len(bucket3_ids)}/{len(bucket3_ids)}, "
          f"bucket 4 {len(bucket4_ids)}/{len(bucket4_ids)} decided.")

    # --- Resolve final text per item ---
    final_rows = []
    stats = {"bucket3": Counter(), "bucket4": Counter(), "resolution": Counter()}
    for bid in sorted(buckets, key=id_key):
        s_row, d_row = cycle1["Samarth"][bid], cycle1["Dhruv"][bid]
        pre_review = d_row["Translation"]
        entry = {
            "base_id": bid,
            "language": "gu",
            "bucket": buckets[bid],
            "english_source": d_row["English Source"],  # canonical copy, see docstring (multiple_154)
            "pre_review_translation": pre_review,
            "cycle1_samarth_correctness": s_row["Correctness"],
            "cycle1_dhruv_correctness": d_row["Correctness"],
        }
        b = buckets[bid]
        if bid in prefer_dhruv:
            entry["final_text"] = prefer_dhruv[bid]["final_text"]
            entry["resolution"] = "both_correct_prefer_dhruv_better_translation"
        elif b == 1:
            entry["final_text"] = pre_review
            entry["resolution"] = "both_correct"
        elif b == 2:
            entry["final_text"] = norm(d_row["Corrected version"])
            entry["resolution"] = "both_incorrect_identical_fix"
        elif b == 3:
            row = bucket3_rows[bid]
            adjudicator = "Samarth" if bid in b3["Samarth"] else "Dhruv"
            other = "Dhruv" if adjudicator == "Samarth" else "Samarth"
            dec = row["Decision"]
            stats["bucket3"][dec] += 1
            if dec == "Original stands":
                entry["final_text"] = pre_review
            elif dec == "Accept fix":
                entry["final_text"] = norm(cycle1[other][bid]["Corrected version"])
            else:
                entry["final_text"] = norm(row[NEW_TEXT_COL])
            entry["resolution"] = "cycle2_bucket3"
            entry["cycle2_adjudicator"] = adjudicator
            entry["cycle2_decision"] = dec
        else:
            row = bucket4_rows[bid]
            a = assignment[bid]
            dec = row["Decision"]
            stats["bucket4"][dec] += 1
            if dec == "Version A":
                entry["final_text"], chosen = norm(row["Version A"]), a["version_a_author"]
            elif dec == "Version B":
                entry["final_text"], chosen = norm(row["Version B"]), a["version_b_author"]
            else:
                entry["final_text"], chosen = norm(row[NEW_TEXT_COL]), None
            entry["resolution"] = "cycle2_bucket4"
            entry["cycle2_adjudicator"] = a["adjudicator"]
            entry["cycle2_decision"] = dec
            entry["cycle2_chosen_fix_author"] = chosen
            entry["cycle2_adjudicator_picked_own_fix"] = (chosen == a["adjudicator"]) if chosen else None
        if norm(row.get("Notes") if b in (3, 4) else None):
            entry["cycle2_notes"] = norm(row["Notes"])
        if not entry["final_text"]:
            raise SystemExit(f"{bid}: resolved to empty text -- aborting")
        stats["resolution"][entry["resolution"]] += 1
        final_rows.append(entry)

    by_id = {e["base_id"]: e for e in final_rows}
    for target, source in HARMONIZE_DUPLICATES.items():
        t, src = by_id[target], by_id[source]
        if norm(t["english_source"]) != norm(src["english_source"]):
            raise SystemExit(f"{target}/{source}: English queries differ -- harmonization not allowed")
        if t["final_text"] != src["final_text"]:
            t["text_before_harmonization"] = t["final_text"]
            t["final_text"] = src["final_text"]
            t["harmonized_with"] = source
            t["harmonization_reason"] = ("identical English query; user decision 2026-10-20 to use the same "
                                         "reviewed Gujarati text as " + source)
            print(f"Harmonized {target} -> text of {source}")
    for a, b in [(108, 195), (109, 196), (110, 197), (111, 198)]:
        if by_id[f"multiple_{a}"]["final_text"] != by_id[f"multiple_{b}"]["final_text"]:
            raise SystemExit(f"multiple_{a}/multiple_{b}: identical English query but different Gujarati text")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "gujarati_final_resolved.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for entry in final_rows:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"Wrote {out_path} ({len(final_rows)}/200 rows)")

    snapshot = {f"bucket{n}_{r.lower()}": rows[r] for n, rows in ((3, b3), (4, b4)) for r in REVIEWERS}
    with open(OUT_DIR / "gujarati_cycle2_decisions.json", "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)
    print(f"Wrote {OUT_DIR / 'gujarati_cycle2_decisions.json'}")

    print("\nResolution categories:", dict(stats["resolution"]))
    print("Bucket 3 decisions:", dict(stats["bucket3"]))
    print("Bucket 4 decisions:", dict(stats["bucket4"]))
    changed_from_mt = sum(1 for e in final_rows if norm(e["final_text"]) != norm(e["pre_review_translation"]))
    print(f"Final text differs from raw IndicTrans2 output for {changed_from_mt}/200 items "
          f"({changed_from_mt / 2:.1f}%).")


if __name__ == "__main__":
    main()
