"""
error_taxonomy.py

Classifies every FAILING example across your BFCL score files into
MLCL's error taxonomy (their Appendix A.2 / Figure 3), reusing BFCL's
own AST-checker error_type field rather than re-implementing any
parsing or comparison logic -- BFCL's score files already record
exactly why each example failed, including the model's actual decoded
output, which is what we need to tell "wrong value in English" apart
from "wrong value because it's still in Hindi/Tamil".

Mapping used (BFCL error_type -> MLCL category):
    ast_decoder:*                          -> Syntax Error
    simple_function_checker:wrong_func_name
    simple_function_checker:missing_required
    simple_function_checker:unexpected_param
    simple_function_checker:wrong_count     -> Function-Level Error
    value_error:* / type_error:* / other    -> Language Mismatch
                                                (if the model's actual
                                                output contains non-English
                                                characters)
                                             -> Wrong Value
                                                (if the output is already
                                                in English but still scored
                                                incorrect)

This gives the top two tiers of MLCL's severity ordering plus the
language-mismatch vs. wrong-value split -- the split that matters most
for this project. MLCL further subdivides each of those into
Wrong/Related/Same-Meaning using semantic judgment; that finer split
isn't included here since it needs an LLM judge call per failure --
ask Claude to extend this script if you want that level of detail.

USAGE (run from inside berkeley-function-call-leaderboard, after you've
run `bfcl evaluate` for each category you want included):
    python error_taxonomy.py --model gpt-4o-mini-2024-07-18-FC --categories simple_python simple_python_hi simple_python_ta simple_python_hi_pt simple_python_hi_pre simple_python_hi_post
"""

import argparse
import csv
import json
from pathlib import Path

SCORE_DIR_TEMPLATE = "score/{model}/non_live"

FUNCTION_LEVEL_ERRORS = {
    "simple_function_checker:wrong_func_name",
    "simple_function_checker:missing_required",
    "simple_function_checker:unexpected_param",
    "simple_function_checker:wrong_count",
    "simple_function_checker:missing_optional",
    "simple_function_checker:unclear",
}


def is_syntax_error(error_type):
    return error_type.startswith("ast_decoder:")


def is_function_level_error(error_type):
    return error_type in FUNCTION_LEVEL_ERRORS


def extract_all_strings(obj):
    """Recursively pull every string value out of a nested dict/list structure."""
    strings = []
    if isinstance(obj, str):
        strings.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            strings.extend(extract_all_strings(v))
    elif isinstance(obj, list):
        for v in obj:
            strings.extend(extract_all_strings(v))
    return strings


def contains_non_english(model_result_decoded):
    strings = extract_all_strings(model_result_decoded)
    return any(any(ord(c) > 127 for c in s) for s in strings)


def classify(entry):
    error_type = entry.get("error_type", "unknown")

    if is_syntax_error(error_type):
        return "Syntax Error"
    if is_function_level_error(error_type):
        return "Function-Level Error"

    # Remaining: value_error:*, type_error:*, or anything else -- split by
    # whether the model's actual output contains non-English characters.
    decoded = entry.get("model_result_decoded")
    if decoded is not None and contains_non_english(decoded):
        return "Language Mismatch"
    return "Wrong Value (English)"


def load_score_file(path):
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            if i == 0 and "accuracy" in data:
                continue  # skip header line
            entries.append(data)
    return entries


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--categories", nargs="+", required=True)
    parser.add_argument("--output", default="error_taxonomy_breakdown.csv")
    args = parser.parse_args()

    score_dir = Path(SCORE_DIR_TEMPLATE.format(model=args.model))

    categories = ["Syntax Error", "Function-Level Error", "Language Mismatch", "Wrong Value (English)"]
    table = {}  # category_name -> {taxonomy_bucket: count}
    totals = {}  # category_name -> total examples in the file

    for cat in args.categories:
        score_path = score_dir / f"BFCL_v4_{cat}_score.json"
        if not score_path.exists():
            print(f"  SKIP {cat}: {score_path} not found (did you run bfcl evaluate for it?)")
            continue

        entries = load_score_file(score_path)
        counts = {c: 0 for c in categories}
        for entry in entries:
            bucket = classify(entry)
            counts[bucket] += 1

        table[cat] = counts

        # Figure out total count from the header line
        with open(score_path, "r", encoding="utf-8") as f:
            header = json.loads(f.readline())
        totals[cat] = header.get("total_count", len(entries))

    # Print a readable table
    col_width = 24
    print(f"\n{'Category':<28}" + "".join(f"{c:<{col_width}}" for c in categories) + "Total failures")
    for cat, counts in table.items():
        row = f"{cat:<28}"
        for c in categories:
            n = counts[c]
            pct = 100 * n / totals[cat] if totals[cat] else 0
            row += f"{f'{n} ({pct:.1f}%)':<{col_width}}"
        row += f"{sum(counts.values())}/{totals[cat]}"
        print(row)

    # Save as CSV too
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["category", "total_examples"] + categories)
        for cat, counts in table.items():
            writer.writerow([cat, totals[cat]] + [counts[c] for c in categories])

    print(f"\nSaved to {args.output}")


if __name__ == "__main__":
    main()
