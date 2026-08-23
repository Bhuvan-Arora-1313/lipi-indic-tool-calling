"""
fix_flagged.py

Re-translates specific flagged examples using a strengthened prompt that
explicitly targets the failure patterns found during QA review: changed
numbers, garbled proper nouns, hallucinated/added content, loose synonym
substitution for precision-sensitive terms, and silent currency
conversion.

Automatically backs up the original translated file before touching it,
updates it in place with the fixed translations, and writes an audit
log of every change -- useful as methods-section material documenting
your manual correction pass (mirrors what IndicDB reports as "Phase 3:
targeted error correction").

USAGE (run from inside berkeley-function-call-leaderboard):
    python fix_flagged.py --ids-file flagged_ids.csv

flagged_ids.csv format (one row per example to fix):
    id,lang,reason
    simple_python_2,hi,hallucination - added computed answer
    ...

The "reason" column is just for your own record-keeping / the audit log
-- it isn't used to change how the fix is done.

Requires the main translated files to already exist at:
    bfcl_eval/data/BFCL_v4_simple_python_hi.json
    bfcl_eval/data/BFCL_v4_simple_python_ta.json
(i.e. wherever translate_bfcl.py wrote them -- pass --hi-file / --ta-file
if yours are somewhere else).
"""

import argparse
import csv
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

LANG_NAMES = {"hi": "Hindi", "ta": "Tamil"}

NUMERAL_GUIDANCE = {
    "hi": "Translate numbers into natural Hindi numeral words or Devanagari digits, the way a real user would type them (not English/Arabic digits), and use native magnitude words (e.g. lakh, crore) where they would naturally appear.",
    "ta": "Write numbers using ordinary Arabic digits (0-9), the way real Tamil speakers actually type numbers today -- traditional Tamil numeral glyphs are essentially obsolete in everyday use. Still use native magnitude words (e.g. lakh, crore) where they would naturally appear.",
}

STRICT_SYSTEM_PROMPT_TEMPLATE = """You are correcting a previous translation that was flagged for a specific error during quality review. Translate the user's message into natural, fluent {lang_name}, exactly as a native speaker would type it to a voice assistant or chatbot -- but follow these rules with extra care, since a previous attempt on this exact sentence violated one of them:

1. NEVER change any number, date, quantity, or specific value. If the original says 50, the translation must correspond to exactly 50 -- not 70, not any other number. Copy every numeric value with total precision.
2. NEVER add content, opinions, extra detail, or a computed answer that wasn't in the original. Translate only what is asked -- do not solve the problem, elaborate, or embellish, even if the answer seems obvious to you.
3. For proper nouns (brand names, game names, person names, place names) that don't have a standard {lang_name} form, transliterate them phonetically and carefully, preserving the sound. Do NOT substitute a native word that merely sounds similar or is unrelated -- e.g. the board game "Catan" must stay recognizable as "Catan" transliterated into {lang_name} script, never replaced with an unrelated native word.
4. For precise technical terms, use the most accurate {lang_name} equivalent, not a loose everyday synonym -- e.g. preserve the distinction between velocity (has direction) and speed, or mass and weight, if the original text makes that distinction.
5. Keep currency units exactly as in the original. If the original says dollars, the translation must still refer to dollars -- do not convert to rupees or any other currency.
6. {numeral_guidance}

Do not translate into English. Do not explain your translation or note what you fixed. Output ONLY the translated sentence -- no quotes, no notes, no extra text."""


import zlib


def looks_degenerate(text, source_text):
    """Same validated check used elsewhere in the project: genuine
    repetition-loop garbage compresses extremely well (ratio ~0.02-0.1),
    normal text does not (ratio ~0.8-1.1 for short sentences)."""
    if not text:
        return True
    if len(text) > max(300, len(source_text) * 5):
        return True
    if len(text) > 50:
        compressed_len = len(zlib.compress(text.encode("utf-8")))
        original_len = len(text.encode("utf-8"))
        if compressed_len / original_len < 0.5:
            return True
    return False


def translate_strict(client, model, text, lang_code):
    lang_name = LANG_NAMES[lang_code]

    def call(temperature):
        resp = client.chat.completions.create(
            model=model,
            temperature=temperature,
            max_tokens=150,
            messages=[
                {"role": "system", "content": STRICT_SYSTEM_PROMPT_TEMPLATE.format(
                    lang_name=lang_name, numeral_guidance=NUMERAL_GUIDANCE[lang_code]
                )},
                {"role": "user", "content": text},
            ],
        )
        return resp.choices[0].message.content.strip()

    result = call(temperature=0)
    if looks_degenerate(result, text):
        result = call(temperature=0.3)
        if looks_degenerate(result, text):
            raise RuntimeError(f"Degenerate/repetitive output persisted after retry for: {text[:80]}...")
    return result


def load_jsonl(path):
    examples = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                examples.append(json.loads(line))
    return examples


def save_jsonl(path, examples):
    with open(path, "w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids-file", required=True, help="CSV with columns: id,lang,reason")
    parser.add_argument("--hi-file", default="bfcl_eval/data/BFCL_v4_simple_python_hi.json")
    parser.add_argument("--ta-file", default="bfcl_eval/data/BFCL_v4_simple_python_ta.json")
    parser.add_argument("--model", default="openai/gpt-4o")
    parser.add_argument("--audit-log", default=None, help="Where to write the change log (default: fix_audit_<timestamp>.csv)")
    args = parser.parse_args()

    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found. Run this from the berkeley-function-call-leaderboard folder.")
        sys.exit(1)
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=30.0, max_retries=2)

    # Read the list of IDs to fix, grouped by language
    to_fix = {"hi": [], "ta": []}
    with open(args.ids_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lang = row["lang"].strip()
            if lang not in to_fix:
                print(f"  WARNING: unknown lang '{lang}' for id {row['id']}, skipping")
                continue
            to_fix[lang].append((row["id"].strip(), row.get("reason", "")))

    audit_log_path = args.audit_log or f"fix_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    audit_rows = []

    for lang, file_path_arg in [("hi", args.hi_file), ("ta", args.ta_file)]:
        ids_for_lang = to_fix[lang]
        if not ids_for_lang:
            continue

        file_path = Path(file_path_arg)
        if not file_path.exists():
            print(f"  SKIP {lang}: {file_path} not found")
            continue

        # Back up the original before touching it
        backup_path = file_path.with_suffix(file_path.suffix + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        shutil.copy2(file_path, backup_path)
        print(f"Backed up {file_path} -> {backup_path}")

        examples = load_jsonl(file_path)
        by_id = {ex["id"]: ex for ex in examples}

        print(f"\nFixing {len(ids_for_lang)} {LANG_NAMES[lang]} examples...")
        for ex_id, reason in ids_for_lang:
            if ex_id not in by_id:
                print(f"  WARNING: {ex_id} not found in {file_path}, skipping")
                continue

            ex = by_id[ex_id]
            original_en = ex.get("question_en", ex["question"][0][0]["content"])
            old_translation = ex["question"][0][0]["content"]

            try:
                new_translation = translate_strict(client, args.model, original_en, lang)
            except Exception as e:
                print(f"  ERROR fixing {ex_id}: {e}")
                continue

            ex["question"][0][0]["content"] = new_translation

            print(f"\n  {ex_id} ({reason})")
            print(f"     EN:  {original_en}")
            print(f"     OLD: {old_translation}")
            print(f"     NEW: {new_translation}")

            audit_rows.append([ex_id, lang, reason, original_en, old_translation, new_translation])

        save_jsonl(file_path, examples)
        print(f"\nSaved updated {file_path}")

    if audit_rows:
        with open(audit_log_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "lang", "reason_flagged", "original_en", "old_translation", "new_translation"])
            writer.writerows(audit_rows)
        print(f"\nAudit log written to {audit_log_path}")
        print("Keep this -- it's a ready-made table for your methods section documenting the correction pass.")
    else:
        print("\nNo rows were fixed.")


if __name__ == "__main__":
    main()
