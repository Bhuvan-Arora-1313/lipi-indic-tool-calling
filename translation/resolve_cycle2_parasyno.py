"""
resolve_cycle2_parasyno.py

Reads the completed Cycle 2 English PARA/SYNO adjudication files
(Anshul's Bucket 3 tab, Jayant's Bucket 3 tab), validates them against
the Cycle 1 classification this project generated
(`generate_cycle2_parasyno.py`), and produces the final resolved text for
every (base_id, perturbation_type) pair -- merging bucket 1/2 (resolved
after Cycle 1) and the one auto-resolved bucket-4 item with the bucket-3
adjudication decisions.

Two items keep the special handling from generate_cycle2_parasyno.py,
carried over unchanged here (see that script's docstring for the
original reasoning, confirmed with the user 2026-09-16):
  - multiple_3 (PARA): Cycle 2 offered only "Original stands" / "Neither"
    (no "Accept fix", since the other reviewer gave no fix to accept).
  - multiple_72 (SYNO): auto-resolved directly to Jayant's fix, no Cycle 2
    row at all -- read back here from parasyno_cycle1_classification.json
    rather than re-derived, so the resolution logic lives in one place.

Raw Cycle 1 and Cycle 2 reviewer files are read-only here, never
modified.

USAGE (run from inside berkeley-function-call-leaderboard):
    python translation/resolve_cycle2_parasyno.py
"""

import json
from pathlib import Path

import openpyxl

CYCLE1_DIR = Path("reviewer annotated file downloaded from google sheets")
CYCLE1_FILES = {
    "Jayant": (CYCLE1_DIR / "English_PARA_SYNO_Jayant_Kapoor.xlsx", "English PARA-SYNO Jayant"),
    "Anshul": (CYCLE1_DIR / "English_PARA_SYNO_Anshul_Gupta.xlsx", "English PARA-SYNO Anshul"),
}
CYCLE2_FILES = {
    "Anshul": CYCLE1_DIR / "English_PARA_SYNO_Cycle_2_Anshul_Gupta.xlsx",
    "Jayant": CYCLE1_DIR / "English_PARA_SYNO_Cycle_2_Jayant_Kapoor.xlsx",
}
REVIEWERS = list(CYCLE1_FILES.keys())

CLASSIFICATION_PATH = Path("data/reviews/parasyno_cycle1_classification.json")
OUT_DIR = Path("data/reviews")

CYCLE1_HEADER = ["base_id", "Perturbation type", "English Source", "Perturbed text", "Automated check", "Correctness",
                 "Number/Value Issue", "Wrong Word/Mistranslation", "Grammar Error", "Meaning Changed",
                 "Missing Content", "Added Content", "Script/Formatting", "Invalid Swap", "Other",
                 "Corrected version", "Notes"]
B3_HEADER = ["base_id", "Perturbation type", "English Source", "Original Perturbed text (you marked this Correct)",
             "Other reviewer's proposed fix", "Other reviewer's reasoning",
             "Decision", "Corrected version (only if 'Neither')", "Notes"]

NO_FIX_GIVEN_BUCKET3 = {("multiple_3", "PARA")}
VALID_B3_DECISIONS_NORMAL = {"Original stands", "Accept fix", "Neither - write new"}
VALID_B3_DECISIONS_NO_FIX = {"Original stands", "Neither - write new"}


def norm(s):
    return "" if s is None else s.rstrip()


def key_str(key):
    return f"{key[0]}|{key[1]}"


def unkey_str(s):
    base_id, ptype = s.split("|")
    return (base_id, ptype)


def load_cycle1_file(path, sheet_name):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[sheet_name]
    rows = {}
    last_base_id, last_source = None, None
    for r in range(2, ws.max_row + 1):
        values = [ws.cell(row=r, column=c).value for c in range(1, len(CYCLE1_HEADER) + 1)]
        row = dict(zip(CYCLE1_HEADER, values))
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
        rows[(row["base_id"], row["Perturbation type"])] = row
    return rows


def load_b3_sheet(path, sheet_name):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[sheet_name]
    rows = {}
    for r in range(2, ws.max_row + 1):
        values = [ws.cell(row=r, column=c).value for c in range(1, len(B3_HEADER) + 1)]
        row = dict(zip(B3_HEADER, values))
        if row["base_id"] and row["Perturbation type"]:
            rows[(row["base_id"], row["Perturbation type"])] = row
    return rows


def main():
    cycle1 = {}
    for reviewer, (path, sheet) in CYCLE1_FILES.items():
        cycle1[reviewer] = load_cycle1_file(path, sheet)
        print(f"Loaded {reviewer}: {len(cycle1[reviewer])} rows from {path.name}")

    with open(CLASSIFICATION_PATH, encoding="utf-8") as f:
        classification = json.load(f)
    buckets = {unkey_str(k): v for k, v in classification["buckets"].items()}
    auto_resolved_bucket4 = {unkey_str(k): v for k, v in classification["manual_handling"]["auto_resolve_bucket4"].items()}

    anshul_b3 = load_b3_sheet(CYCLE2_FILES["Anshul"], "Bucket 3 - Asymmetric")
    jayant_b3 = load_b3_sheet(CYCLE2_FILES["Jayant"], "Bucket 3 - Asymmetric")
    bucket3_rows = {**anshul_b3, **jayant_b3}

    bucket3_keys = sorted([k for k, v in buckets.items() if v == 3], key=lambda k: (int(k[0].split("_")[1]), k[1]))
    bucket4_keys = sorted([k for k, v in buckets.items() if v == 4], key=lambda k: (int(k[0].split("_")[1]), k[1]))

    # --- Validate ---
    errors = []
    if set(bucket3_rows.keys()) != set(bucket3_keys):
        errors.append(f"Bucket 3 key mismatch: sheets have {set(bucket3_rows.keys())}, expected {set(bucket3_keys)}")
    if set(bucket4_keys) != set(auto_resolved_bucket4.keys()):
        errors.append(f"Bucket 4 key mismatch: expected all auto-resolved but classification has "
                       f"{set(bucket4_keys)} vs auto-resolved {set(auto_resolved_bucket4.keys())}")
    for key in bucket3_keys:
        row = bucket3_rows.get(key, {})
        dec = row.get("Decision")
        valid = VALID_B3_DECISIONS_NO_FIX if key in NO_FIX_GIVEN_BUCKET3 else VALID_B3_DECISIONS_NORMAL
        if dec not in valid:
            errors.append(f"{key}: invalid/missing bucket-3 decision {dec!r} (valid: {valid})")
        if dec == "Neither - write new" and not row.get("Corrected version (only if 'Neither')"):
            errors.append(f"{key}: 'Neither' chosen but no Corrected version given")

    if errors:
        print("VALIDATION ERRORS:")
        for e in errors:
            print(" -", e)
        raise SystemExit("Aborting -- fix the above before resolving.")
    print(f"Cycle 2 validation: bucket-3 ({len(bucket3_keys)}) clean, bucket-4 ({len(bucket4_keys)}) all auto-resolved.")

    # --- Resolve final text per item ---
    final_rows = []
    resolution_stats = {"bucket3": {}}
    all_keys = sorted(buckets.keys(), key=lambda k: (int(k[0].split("_")[1]), k[1]))
    for key in all_keys:
        b = buckets[key]
        j_row, a_row = cycle1["Jayant"][key], cycle1["Anshul"][key]
        english_source = j_row["English Source"]
        pre_review_text = j_row["Perturbed text"]

        entry = {
            "base_id": key[0],
            "perturbation_type": key[1],
            "language": "en",
            "bucket": b,
            "english_source": english_source,
            "pre_review_perturbed_text": pre_review_text,
            "cycle1_jayant_correctness": j_row["Correctness"],
            "cycle1_anshul_correctness": a_row["Correctness"],
        }

        if b == 1:
            entry["final_text"] = pre_review_text
            entry["resolution"] = "both_correct"
        elif b == 2:
            entry["final_text"] = norm(j_row["Corrected version"])
            entry["resolution"] = "both_incorrect_identical_fix"
        elif b == 3:
            row = bucket3_rows[key]
            adjudicator = "Jayant" if key in jayant_b3 else "Anshul"
            dec = row["Decision"]
            resolution_stats["bucket3"][dec] = resolution_stats["bucket3"].get(dec, 0) + 1
            if dec == "Original stands":
                entry["final_text"] = pre_review_text
            elif dec == "Accept fix":
                other = "Anshul" if adjudicator == "Jayant" else "Jayant"
                entry["final_text"] = norm(cycle1[other][key]["Corrected version"])
            else:
                entry["final_text"] = norm(row["Corrected version (only if 'Neither')"])
            entry["cycle2_adjudicator"] = adjudicator
            entry["cycle2_decision"] = dec
            entry["no_fix_was_given"] = key in NO_FIX_GIVEN_BUCKET3
        else:  # bucket 4, all auto-resolved
            info = auto_resolved_bucket4[key]
            entry["final_text"] = info["final_text"]
            entry["resolution"] = "auto_resolved_no_competing_fix"
            entry["resolved_from"] = info["resolved_by"]

        final_rows.append(entry)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "parasyno_final_resolved.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for entry in final_rows:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"Wrote {out_path} ({len(final_rows)} rows)")

    decisions_snapshot = {
        "bucket3_anshul": {key_str(k): v for k, v in anshul_b3.items()},
        "bucket3_jayant": {key_str(k): v for k, v in jayant_b3.items()},
    }
    with open(OUT_DIR / "parasyno_cycle2_decisions.json", "w", encoding="utf-8") as f:
        json.dump(decisions_snapshot, f, ensure_ascii=False, indent=2)
    print(f"Wrote {OUT_DIR / 'parasyno_cycle2_decisions.json'}")

    print("\nBucket 3 resolution breakdown:", resolution_stats["bucket3"])


if __name__ == "__main__":
    main()
