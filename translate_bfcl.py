"""
translate_bfcl.py

Translates the natural-language "question" field of a BFCL test file into
Hindi or Tamil using an LLM via OpenRouter, while leaving "id" and
"function" (the tool schema) untouched -- so only the language of the
user's query changes, nothing about what the model is asked to call.

Each output example keeps the original English text under "question_en"
so you (or a native-speaker reviewer) can spot-check translations later.

USAGE (run from inside the berkeley-function-call-leaderboard folder,
with your bfcl_env activated, so it picks up the same .env you already
set up for BFCL + OpenRouter):

    # Quick preview on just 5 examples first (recommended before a full run)
    python translate_bfcl.py --input bfcl_eval/data/BFCL_v4_simple_python.json --lang hi --limit 5

    # Full run once you're happy with the preview
    python translate_bfcl.py --input bfcl_eval/data/BFCL_v4_simple_python.json --lang hi
    python translate_bfcl.py --input bfcl_eval/data/BFCL_v4_simple_python.json --lang ta

If it crashes or you Ctrl+C partway through, just re-run the exact same
command -- it skips examples already translated and continues from where
it stopped.
"""

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

LANG_NAMES = {"hi": "Hindi", "ta": "Tamil"}

SYSTEM_PROMPT_TEMPLATE = """You are helping build a research dataset. Translate the user's message into natural, fluent {lang_name}, the way a native {lang_name} speaker in India would actually type it when talking to a voice assistant or chatbot on their phone.

Rules:
- Translate numbers into natural {lang_name} numeral words or native-script digits, the way a real user would type them (not English/Arabic digits), and use native magnitude words (e.g. lakh, crore) where they would naturally appear.
- Translate dates and units naturally into {lang_name} conventions.
- Keep proper nouns (names of people, places, brands) transliterated naturally into {lang_name} script.
- CRITICAL: Do NOT solve the problem, compute any answer, or add any information not present in the original sentence -- even if the answer seems obvious to you. Your only job is translation. If the original asks a question or gives an instruction, the translation must also just ask that question or give that instruction, with nothing added.
- Do not translate into English. Do not explain your translation. Output ONLY the translated sentence -- no quotes, no notes, no extra text, no worked solutions."""


def translate(client, model, text, lang_code):
    lang_name = LANG_NAMES[lang_code]
    resp = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE.format(lang_name=lang_name)},
            {"role": "user", "content": text},
        ],
    )
    return resp.choices[0].message.content.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to a BFCL .json test file")
    parser.add_argument("--lang", required=True, choices=["hi", "ta"], help="hi (Hindi) or ta (Tamil)")
    parser.add_argument("--model", default="openai/gpt-4o", help="OpenRouter model ID used to translate")
    parser.add_argument("--limit", type=int, default=None, help="Only translate the first N examples (for a quick preview)")
    parser.add_argument("--output", default=None, help="Output path (default: <input>_<lang>.json next to input)")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path.with_name(
        input_path.stem + f"_{args.lang}" + input_path.suffix
    )

    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found. Make sure you're running this from the")
        print("berkeley-function-call-leaderboard folder, where your .env file lives.")
        sys.exit(1)

    client = OpenAI(api_key=api_key, base_url=base_url)

    examples = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                examples.append(json.loads(line))

    if args.limit:
        examples = examples[: args.limit]

    done_ids = set()
    if output_path.exists():
        with open(output_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    done_ids.add(json.loads(line)["id"])
        if done_ids:
            print(f"Found {len(done_ids)} already-translated examples in {output_path}, resuming...")

    remaining = [ex for ex in examples if ex["id"] not in done_ids]
    print(f"Translating {len(remaining)} of {len(examples)} examples into {LANG_NAMES[args.lang]} using {args.model}...")

    with open(output_path, "a", encoding="utf-8") as out_f:
        for i, ex in enumerate(remaining):
            try:
                original_text = ex["question"][0][0]["content"]
                translated_text = translate(client, args.model, original_text, args.lang)

                new_ex = json.loads(json.dumps(ex))  # deep copy
                new_ex["question"][0][0]["content"] = translated_text
                new_ex["question_en"] = original_text  # keep original for review

                out_f.write(json.dumps(new_ex, ensure_ascii=False) + "\n")
                out_f.flush()

                print(f"  [{i + 1}/{len(remaining)}] {ex['id']}")
                print(f"     EN: {original_text}")
                print(f"     {args.lang.upper()}: {translated_text}")

            except Exception as e:
                print(f"\n  ERROR on id {ex.get('id')}: {e}")
                print("  Stopping here. Re-run this exact same command to resume.")
                sys.exit(1)

    print(f"\nDone. Wrote {len(remaining)} translations to {output_path}")


if __name__ == "__main__":
    main()
