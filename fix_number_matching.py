"""
fix_number_matching.py

Your original idea, turned into a real repair strategy: for each
example, extract the numbers from the model's tool-call output and the
numbers from the ORIGINAL native-language question (not the ground
truth -- this works with information available in a real deployment).
Any output number that doesn't trace back to a question number is
suspicious.

Resolution:
  - If there's exactly ONE suspicious output number and exactly ONE
    unmatched question number, swap deterministically -- no ambiguity,
    no API call needed.
  - If there are multiple candidates on either side, ask a small, narrow
    LLM call to match them (not to re-translate or re-solve anything,
    just "which candidate number belongs to which parameter").
  - If there's no unmatched question number to substitute, leave the
    output alone -- nothing to correct it with.

Works on any existing result set (NT, PT, PRE, POST, or combinations),
no new `bfcl generate` call needed -- same reuse pattern as POST and
the type-cast fix.

USAGE (run from inside berkeley-function-call-leaderboard):
    python fix_number_matching.py --source-category simple_python_hi
    python fix_number_matching.py --source-category simple_python_hi_pre
"""

import argparse
import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

RESULT_DIR_TEMPLATE = "result/{model}/non_live"

DEVANAGARI_DIGITS = "०१२३४५६७८९"
DEVANAGARI_TO_WESTERN = {d: str(i) for i, d in enumerate(DEVANAGARI_DIGITS)}
TAMIL_DIGITS = "௦௧௨௩௪௫௬௭௮௯"
TAMIL_TO_WESTERN = {d: str(i) for i, d in enumerate(TAMIL_DIGITS)}

NUMBER_PATTERN = re.compile(r"-?\d[\d,]*\.?\d*")


def normalize_digits(text):
    out = []
    for c in text:
        out.append(DEVANAGARI_TO_WESTERN.get(c, TAMIL_TO_WESTERN.get(c, c)))
    return "".join(out)


def extract_numbers_from_text(text):
    normalized = normalize_digits(text)
    numbers = []
    for m in NUMBER_PATTERN.finditer(normalized):
        start = m.start()
        # Skip digit runs glued to a preceding letter (e.g. the "1004" in
        # "B1004" is an identifier, not a quantity). A letter *after* the
        # number is fine and common ("50mH", "100uF" are value+unit pairs).
        if start > 0 and normalized[start - 1].isalpha():
            continue
        # Only strip a trailing "." (sentence-final punctuation caught by
        # the regex's optional decimal point) -- NOT a leading "-", which
        # would destroy a genuine negative sign. str.strip() trims both
        # ends, so it must not be used here.
        cleaned = m.group().replace(",", "").rstrip(".")
        if not cleaned or cleaned == "-":
            continue
        try:
            numbers.append(float(cleaned) if "." in cleaned else int(cleaned))
        except ValueError:
            continue
    return numbers


def extract_numbers_from_value(value):
    """Pull numeric leaf values out of a (possibly nested) parameter value."""
    numbers = []
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        numbers.append(value)
    elif isinstance(value, str):
        numbers.extend(extract_numbers_from_text(value))
    elif isinstance(value, list):
        for v in value:
            numbers.extend(extract_numbers_from_value(v))
    elif isinstance(value, dict):
        for v in value.values():
            numbers.extend(extract_numbers_from_value(v))
    return numbers


def numbers_equal(a, b):
    try:
        return float(a) == float(b)
    except (ValueError, TypeError):
        return False


def normalize_func_name(name):
    return name.replace(".", "_")


def find_flat_numeric_params(params, prefix=()):
    """Walks a params dict, returning [(path, value), ...] for every
    numeric leaf value (path is a tuple of keys/indices to get back there)."""
    found = []
    if isinstance(params, dict):
        for k, v in params.items():
            found.extend(find_flat_numeric_params(v, prefix + (k,)))
    elif isinstance(params, list):
        for i, v in enumerate(params):
            found.extend(find_flat_numeric_params(v, prefix + (i,)))
    elif isinstance(params, (int, float)) and not isinstance(params, bool):
        found.append((prefix, params))
    return found


def set_by_path(params, path, new_value):
    obj = params
    for key in path[:-1]:
        obj = obj[key]
    obj[path[-1]] = new_value


def llm_match(client, model, question_text, func_name, suspicious, candidates):
    """Narrow LLM call: just match suspicious param values to the right
    candidate number from the question. Not translation, not solving."""
    prompt = (
        f"Question: {question_text}\n\n"
        f"A function call to '{func_name}' has these parameter values that don't match any number "
        f"explicitly stated in the question: {suspicious}\n\n"
        f"These numbers ARE stated in the question but aren't used anywhere in the call: {candidates}\n\n"
        "For each suspicious value, decide which candidate number (if any) it should actually be. "
        'Respond with ONLY a JSON object mapping each suspicious value (as a string key) to its correct '
        'replacement number, e.g. {"70": 50}. If a suspicious value has no good match among the candidates, omit it.'
    )
    resp = client.chat.completions.create(
        model=model,
        temperature=0,
        max_tokens=150,
        messages=[
            {"role": "system", "content": "You match numbers to their correct parameter. Respond with only the JSON object, nothing else."},
            {"role": "user", "content": prompt},
        ],
    )
    text = resp.choices[0].message.content.strip()
    try:
        return {float(k): v for k, v in json.loads(text).items()}
    except (json.JSONDecodeError, ValueError, TypeError):
        return {}


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
    return f"{prefix}_numfix_{num}"


def get_source_text(question_entry, lang):
    """PRE-built files save the true original under question_hi/question_ta;
    everything else has the native-language text directly in question."""
    for key in (f"question_{lang}", "question_hi", "question_ta"):
        if key in question_entry:
            return question_entry[key]
    return question_entry["question"][0][0]["content"]


def fix_entry(client, model, result_entry, question_entry, lang):
    source_text = get_source_text(question_entry, lang)
    source_numbers = extract_numbers_from_text(source_text)

    result_field = result_entry["result"]
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

            numeric_leaves = find_flat_numeric_params(args)
            unmatched_output = [(path, val) for path, val in numeric_leaves
                                 if not any(numbers_equal(val, s) for s in source_numbers)]
            used_source = set()
            for _, val in numeric_leaves:
                for i, s in enumerate(source_numbers):
                    if numbers_equal(val, s):
                        used_source.add(i)
                        break
            unmatched_source = [s for i, s in enumerate(source_numbers) if i not in used_source]

            if unmatched_output and unmatched_source:
                if len(unmatched_output) == 1 and len(unmatched_source) == 1:
                    path, old_val = unmatched_output[0]
                    set_by_path(args, path, unmatched_source[0])
                    n_fixed += 1
                else:
                    suspicious_vals = [val for _, val in unmatched_output]
                    mapping = llm_match(client, model, source_text, func_name, suspicious_vals, unmatched_source)
                    for path, old_val in unmatched_output:
                        if float(old_val) in mapping:
                            set_by_path(args, path, mapping[float(old_val)])
                            n_fixed += 1

            new_call[func_name] = json.dumps(args, ensure_ascii=False)
        new_result.append(new_call)

    return new_result, n_fixed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-category", required=True)
    parser.add_argument("--lang", required=True, choices=["hi", "ta"])
    parser.add_argument("--model", default="gpt-4o-mini-2024-07-18-FC")
    args = parser.parse_args()

    out_category = f"{args.source_category}_numfix"

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

    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found. Run this from the berkeley-function-call-leaderboard folder.")
        return
    translate_model = args.model[:-3] if args.model.endswith("-FC") else args.model
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=30.0, max_retries=2)

    questions = load_jsonl(source_questions_path)
    questions_by_id = {q["id"]: q for q in questions}
    results = load_jsonl(source_result_path)

    print(f"Applying number-match fix to '{args.source_category}' -> '{out_category}', {len(results)} entries...")

    total_fixed = 0
    n_entries_changed = 0
    new_results = []
    for entry in results:
        question_entry = questions_by_id.get(entry["id"])
        if question_entry is None:
            new_results.append({"id": remap_id(entry["id"]), "result": entry["result"]})
            continue

        new_result_field, n_fixed = fix_entry(client, translate_model, entry, question_entry, args.lang)
        if n_fixed:
            total_fixed += n_fixed
            n_entries_changed += 1
            print(f"  {entry['id']}: fixed {n_fixed} value(s)")

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

    print(f"\nDone. Fixed {total_fixed} value(s) across {n_entries_changed} entries.")
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
