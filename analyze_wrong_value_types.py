"""
analyze_wrong_value_types.py

For every failure classified as "Wrong Value (English)" by
error_taxonomy.py's logic, determines whether the mismatch is
specifically about a NUMBER (the model's numeric parameter value
doesn't match any accepted numeric ground-truth value) versus
something else entirely (wrong entity/string, wrong category, wrong
date format, etc.).

This tells us the real ceiling for a deterministic "extract numbers
from both versions, compare, correct" repair strategy before spending
time building it -- no new API calls, just a deeper read of data you
already have in your score files.

USAGE (run from inside berkeley-function-call-leaderboard):
    python analyze_wrong_value_types.py --model gpt-4o-mini-2024-07-18-FC --categories simple_python_hi simple_python_ta simple_python_hi_pt simple_python_hi_pre simple_python_hi_post simple_python_hi_pt_post simple_python_ta_pt simple_python_ta_pre simple_python_ta_post simple_python_ta_pt_post
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
    decoded = entry.get("model_result_decoded")
    if decoded is not None and contains_non_english(decoded):
        return "Language Mismatch"
    return "Wrong Value (English)"


def is_number(x):
    if isinstance(x, bool):
        return False
    return isinstance(x, (int, float))


def strict_match(model_value, av):
    """Exact match including type -- what BFCL's strict nested-type checker
    effectively requires for typed parameters."""
    if isinstance(model_value, list) and isinstance(av, list):
        if len(model_value) != len(av):
            return False
        return all(strict_match(a, b) for a, b in zip(model_value, av))
    if type(model_value) != type(av):
        return False
    return model_value == av


def loose_match(model_value, av):
    """Numeric-equality match that ignores int vs. float type differences."""
    if isinstance(model_value, list) and isinstance(av, list):
        if len(model_value) != len(av):
            return False
        return all(loose_match(a, b) for a, b in zip(model_value, av))
    if is_number(model_value) and is_number(av):
        try:
            return float(model_value) == float(av)
        except (ValueError, TypeError):
            return False
    return model_value == av


def values_match(model_value, accepted_values):
    return any(strict_match(model_value, av) for av in accepted_values)


def normalize_func_name(name):
    return name.replace(".", "_")


def get_model_params(model_call, func_name):
    if func_name in model_call:
        return model_call[func_name]
    target = normalize_func_name(func_name)
    for k, v in model_call.items():
        if normalize_func_name(k) == target:
            return v
    return None


def is_type_only_diff(model_value, accepted_values):
    """True if model_value doesn't strictly match any accepted value, but
    does match loosely (i.e. the only difference is int vs. float type) --
    a pure type-casting issue, not a real value error."""
    return any(loose_match(model_value, av) for av in accepted_values)


def classify_wrong_value_entry(entry):
    """Returns 'number', 'non_number', 'type_only', 'both', or 'unclear'."""
    decoded = entry.get("model_result_decoded")
    ground_truth = entry.get("possible_answer")

    if not decoded or not ground_truth or not isinstance(decoded, list) or not isinstance(ground_truth, list):
        return "unclear"

    try:
        model_call = decoded[0]
        gt_variant = ground_truth[0]
    except (IndexError, TypeError):
        return "unclear"

    if not isinstance(model_call, dict) or not isinstance(gt_variant, dict):
        return "unclear"

    has_number_mismatch = False
    has_non_number_mismatch = False
    has_type_only_mismatch = False

    for func_name, gt_params in gt_variant.items():
        model_params = get_model_params(model_call, func_name)
        if not isinstance(model_params, dict) or not isinstance(gt_params, dict):
            continue
        for param_name, accepted_values in gt_params.items():
            if not isinstance(accepted_values, list):
                continue
            model_value = model_params.get(param_name)
            if model_value is None:
                continue
            if not values_match(model_value, accepted_values):
                if is_type_only_diff(model_value, accepted_values):
                    has_type_only_mismatch = True
                    continue
                model_is_num = is_number(model_value)
                any_accepted_is_num = any(is_number(av) for av in accepted_values)
                if model_is_num or any_accepted_is_num:
                    has_number_mismatch = True
                else:
                    has_non_number_mismatch = True

    if has_number_mismatch and has_non_number_mismatch:
        return "both"
    if has_number_mismatch:
        return "number"
    if has_non_number_mismatch:
        return "non_number"
    if has_type_only_mismatch:
        return "type_only"
    return "unclear"


def load_score_file(path):
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            if i == 0 and "accuracy" in data:
                continue
            entries.append(data)
    return entries


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--categories", nargs="+", required=True)
    parser.add_argument("--output", default="wrong_value_breakdown.csv")
    parser.add_argument("--debug-category", default=None, help="Print raw data for a few 'unclear' entries in this category, to diagnose why they weren't classified")
    parser.add_argument("--debug-count", type=int, default=3)
    args = parser.parse_args()

    score_dir = Path(SCORE_DIR_TEMPLATE.format(model=args.model))

    labels = ["number", "non_number", "type_only", "both", "unclear"]
    table = {}

    for cat in args.categories:
        score_path = score_dir / f"BFCL_v4_{cat}_score.json"
        if not score_path.exists():
            print(f"  SKIP {cat}: {score_path} not found")
            continue

        entries = load_score_file(score_path)
        counts = {label: 0 for label in labels}
        total_wrong_value = 0

        for entry in entries:
            if classify(entry) != "Wrong Value (English)":
                continue
            total_wrong_value += 1
            counts[classify_wrong_value_entry(entry)] += 1

        table[cat] = (counts, total_wrong_value)

        if args.debug_category == cat:
            print(f"\n--- DEBUG: 'unclear' entries in {cat} ---")
            shown = 0
            for entry in entries:
                if classify(entry) != "Wrong Value (English)":
                    continue
                if classify_wrong_value_entry(entry) != "unclear":
                    continue
                print(f"\n  id: {entry.get('id')}")
                print(f"  error_type: {entry.get('error_type')}")
                print(f"  error: {entry.get('error')}")
                print(f"  model_result_decoded: {entry.get('model_result_decoded')}")
                print(f"  possible_answer: {entry.get('possible_answer')}")
                shown += 1
                if shown >= args.debug_count:
                    break

    col_width = 14
    print(f"\n{'Category':<28}" + "".join(f"{l:<{col_width}}" for l in labels) + "Total Wrong-Value")
    for cat, (counts, total) in table.items():
        row = f"{cat:<28}"
        for label in labels:
            n = counts[label]
            pct = 100 * n / total if total else 0
            row += f"{f'{n} ({pct:.0f}%)':<{col_width}}"
        row += str(total)
        print(row)

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["category", "total_wrong_value"] + labels)
        for cat, (counts, total) in table.items():
            writer.writerow([cat, total] + [counts[label] for label in labels])

    print(f"\nSaved to {args.output}")
    print("\n'number' + 'both' = failures where fixing the numeral would help.")
    print("'non_number' = failures a numeral-repair strategy cannot touch.")


if __name__ == "__main__":
    main()
