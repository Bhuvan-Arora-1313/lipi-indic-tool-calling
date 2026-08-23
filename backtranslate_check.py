"""
backtranslate_check.py

Automated quality-screening pass for translated BFCL queries, using
back-translation: translate the Hindi/Tamil text back into English with
a DIFFERENT model than the one used for the forward translation, then
ask a judge model whether the back-translation still means the same
thing as the original English query.

This mirrors the QA approach used in IndicDB and similar papers: flag
suspicious examples automatically so a human reviewer can focus their
limited time on the ones that actually need a second look, instead of
reading all 400 by hand.

USAGE (run from inside berkeley-function-call-leaderboard, same .env
you already set up for BFCL + OpenRouter):

    python backtranslate_check.py --input bfcl_eval/data/BFCL_v4_simple_python_hi.json --lang hi
    python backtranslate_check.py --input bfcl_eval/data/BFCL_v4_simple_python_ta.json --lang ta

Produces a CSV: <input>_review.csv -- one row per example with the
original English, the forward translation, the back-translation, and
a MATCH/MISMATCH verdict with a short reason. Open it in Excel/Numbers
and filter to MISMATCH rows to see just what needs a closer look.

Requires the input file to have been made by translate_bfcl.py (it
needs the "question_en" field that script saves alongside each
translation).
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

LANG_NAMES = {"hi": "Hindi", "ta": "Tamil"}


def back_translate(client, model, text, lang_code):
    lang_name = LANG_NAMES[lang_code]
    resp = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": (
                    f"Translate the following {lang_name} sentence into natural English. "
                    "Output ONLY the English translation, nothing else -- no quotes, no notes."
                ),
            },
            {"role": "user", "content": text},
        ],
    )
    return resp.choices[0].message.content.strip()


def judge_equivalence(client, model, original_en, back_translated_en):
    resp = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are checking translation quality for a research dataset. "
                    "You will see two English sentences. SENTENCE A is the original. "
                    "SENTENCE B came from translating A into another language and back "
                    "into English. Decide whether B asks for exactly the same thing as A, "
                    "with nothing added, removed, or changed -- extra solved answers, "
                    "flipped meanings (e.g. ascending vs descending), or changed numbers "
                    "all count as a mismatch, even if B reads as fluent English.\n\n"
                    "Respond in EXACTLY this format and nothing else:\n"
                    "VERDICT: MATCH or MISMATCH\n"
                    "REASON: <one short sentence>"
                ),
            },
            {
                "role": "user",
                "content": f"SENTENCE A: {original_en}\nSENTENCE B: {back_translated_en}",
            },
        ],
    )
    text = resp.choices[0].message.content.strip()
    verdict = "MISMATCH"  # safe default if parsing fails -- gets flagged for human review
    reason = text
    for line in text.splitlines():
        if line.upper().startswith("VERDICT:"):
            verdict = line.split(":", 1)[1].strip().upper()
        elif line.upper().startswith("REASON:"):
            reason = line.split(":", 1)[1].strip()
    return verdict, reason


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="A translated BFCL file made by translate_bfcl.py")
    parser.add_argument("--lang", required=True, choices=["hi", "ta"])
    parser.add_argument(
        "--backtranslate-model",
        default="~anthropic/claude-sonnet-latest",
        help="Model used for the back-translation step (kept different from the forward-translation model on purpose)",
    )
    parser.add_argument("--judge-model", default="openai/gpt-4o-mini", help="Model used to judge meaning preservation")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output", default=None, help="Output CSV path (default: <input>_review.csv)")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path.with_name(input_path.stem + "_review.csv")

    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found. Run this from the berkeley-function-call-leaderboard folder.")
        sys.exit(1)

    client = OpenAI(api_key=api_key, base_url=base_url, timeout=30.0, max_retries=2)

    examples = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                examples.append(json.loads(line))

    if args.limit:
        examples = examples[: args.limit]

    print(f"Checking {len(examples)} examples from {input_path}...")
    print(f"Back-translating with {args.backtranslate_model}, judging with {args.judge_model}\n")

    done_ids = set()
    file_exists = output_path.exists()
    if file_exists:
        with open(output_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)  # skip header
            for row in reader:
                if row:
                    done_ids.add(row[0])
        if done_ids:
            print(f"Found {len(done_ids)} already-checked examples in {output_path}, resuming...\n")

    n_flagged = 0
    n_skipped = 0
    write_header = not file_exists
    with open(output_path, "a", newline="", encoding="utf-8") as csv_f:
        writer = csv.writer(csv_f)
        if write_header:
            writer.writerow(["id", "original_en", "forward_translation", "back_translation", "verdict", "reason"])

        for i, ex in enumerate(examples):
            if ex["id"] in done_ids:
                continue

            original_en = ex.get("question_en")
            if not original_en:
                print(f"  SKIP {ex['id']}: no question_en field (was this file made with translate_bfcl.py?)")
                n_skipped += 1
                continue

            try:
                forward_translation = ex["question"][0][0]["content"]
                back_translation = back_translate(client, args.backtranslate_model, forward_translation, args.lang)
                verdict, reason = judge_equivalence(client, args.judge_model, original_en, back_translation)

                writer.writerow([ex["id"], original_en, forward_translation, back_translation, verdict, reason])
                csv_f.flush()

                flag = "  <-- FLAGGED" if verdict != "MATCH" else ""
                if flag:
                    n_flagged += 1
                print(f"  [{i + 1}/{len(examples)}] {ex['id']}: {verdict}{flag}")

            except Exception as e:
                print(f"  ERROR on id {ex.get('id')}: {e}")

    print(f"\nDone. {n_flagged} of {len(examples) - n_skipped} checked examples flagged for review.")
    print(f"Full results in {output_path}")
    print("Open it in Excel/Numbers/Google Sheets and filter the 'verdict' column to MISMATCH to review just those.")


if __name__ == "__main__":
    main()
