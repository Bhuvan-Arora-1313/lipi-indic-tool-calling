"""
fix_type_casting.py

Deterministically fixes int-vs-float type mismatches in an existing
result set. Reads each function's OWN parameter schema -- which the
model already saw in its prompt, not the ground truth -- and casts any
integer values the model output to float wherever the schema specifies
type "float" (including inside arrays), leaving everything else
untouched. This is a legitimate, deployable repair: it only uses
information the model already had access to.

Works on any category you've already generated (NT, PT, PRE, POST, or
any combination) -- no new `bfcl generate` call needed, same pattern as
apply_post.py. Produces a new "<source-category>_typefix" category.

USAGE (run from inside berkeley-function-call-leaderboard):
    python fix_type_casting.py --source-category simple_python_hi
    python fix_type_casting.py --source-category simple_python_hi_pt
"""

import argparse
import json
from pathlib import Path

RESULT_DIR_TEMPLATE = "result/{model}/non_live"


def load_jsonl(path):
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def save_jsonl(path, entries):
    with open(path, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def remap_id(old_id):
    prefix, num = old_id.rsplit("_", 1)
    return f"{prefix}_typefix_{num}"


def normalize_func_name(name):
    return name.replace(".", "_")


def build_param_schema_map(question_entry):
    """Returns {normalized_func_name: {param_name: type_schema_dict}}."""
    schema_map = {}
    for func in question_entry.get("function", []):
        params = func.get("parameters", {}).get("properties", {})
        schema_map[normalize_func_name(func["name"])] = params
    return schema_map


def cast_value(value, schema):
    """Recursively casts ints to floats wherever the schema says 'float'."""
    if schema is None:
        return value, False
    schema_type = schema.get("type")

    if schema_type == "float" and isinstance(value, int) and not isinstance(value, bool):
        return float(value), True

    if schema_type == "array" and isinstance(value, list):
        item_schema = schema.get("items", {})
        changed = False
        new_list = []
        for item in value:
            new_item, item_changed = cast_value(item, item_schema)
            new_list.append(new_item)
            changed = changed or item_changed
        return new_list, changed

    return value, False


def fix_entry_result(result_field, schema_map):
    if not isinstance(result_field, list):
        return result_field, 0

    n_fixed = 0
    new_result = []
    for call in result_field:
        new_call = {}
        for func_name, args_json_str in call.items():
            try:
                args = json.loads(args_json_str)
            except (json.JSONDecodeError, TypeError):
                new_call[func_name] = args_json_str
                continue

            param_schemas = schema_map.get(normalize_func_name(func_name), {})
            for param_name, value in args.items():
                param_schema = param_schemas.get(param_name)
                new_value, changed = cast_value(value, param_schema)
                if changed:
                    args[param_name] = new_value
                    n_fixed += 1

            new_call[func_name] = json.dumps(args, ensure_ascii=False)
        new_result.append(new_call)

    return new_result, n_fixed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-category", required=True)
    parser.add_argument("--model", default="gpt-4o-mini-2024-07-18-FC")
    args = parser.parse_args()

    out_category = f"{args.source_category}_typefix"

    result_dir = Path(RESULT_DIR_TEMPLATE.format(model=args.model))
    source_result_path = result_dir / f"BFCL_v4_{args.source_category}_result.json"
    out_result_path = result_dir / f"BFCL_v4_{out_category}_result.json"

    source_questions_path = Path(f"bfcl_eval/data/BFCL_v4_{args.source_category}.json")
    source_answers_path = Path(f"bfcl_eval/data/possible_answer/BFCL_v4_{args.source_category}.json")
    out_questions_path = Path(f"bfcl_eval/data/BFCL_v4_{out_category}.json")
    out_answers_path = Path(f"bfcl_eval/data/possible_answer/BFCL_v4_{out_category}.json")

    for p, label in [(source_result_path, "result file"), (source_questions_path, "question file"), (source_answers_path, "ground truth file")]:
        if not p.exists():
            print(f"ERROR: {label} not found at {p}")
            return

    questions = load_jsonl(source_questions_path)
    questions_by_id = {q["id"]: q for q in questions}
    results = load_jsonl(source_result_path)

    print(f"Applying type-cast fix to '{args.source_category}' -> '{out_category}', {len(results)} entries...")

    total_fixed_values = 0
    n_entries_changed = 0
    new_results = []
    for entry in results:
        question_entry = questions_by_id.get(entry["id"])
        if question_entry is None:
            new_results.append({"id": remap_id(entry["id"]), "result": entry["result"]})
            continue

        schema_map = build_param_schema_map(question_entry)
        new_result_field, n_fixed = fix_entry_result(entry["result"], schema_map)

        if n_fixed:
            total_fixed_values += n_fixed
            n_entries_changed += 1
            print(f"  {entry['id']}: cast {n_fixed} value(s) to float")

        new_results.append({"id": remap_id(entry["id"]), "result": new_result_field})

    save_jsonl(out_result_path, new_results)

    for source_path, out_path in [(source_answers_path, out_answers_path), (source_questions_path, out_questions_path)]:
        entries = load_jsonl(source_path)
        remapped = []
        for entry in entries:
            new_entry = json.loads(json.dumps(entry))
            new_entry["id"] = remap_id(entry["id"])
            remapped.append(new_entry)
        save_jsonl(out_path, remapped)

    print(f"\nDone. Fixed {total_fixed_values} value(s) across {n_entries_changed} entries.")
    print(f"Wrote {out_result_path}")
    print(f"Wrote {out_answers_path}")
    print(f"Wrote {out_questions_path}")
    print()
    print("Next steps:")
    print(f"  python register_category.py {out_category}")
    print(f"  bfcl evaluate --model {args.model} --test-category {out_category}")
    print("  (no `bfcl generate` needed -- the result file already exists)")


if __name__ == "__main__":
    main()
