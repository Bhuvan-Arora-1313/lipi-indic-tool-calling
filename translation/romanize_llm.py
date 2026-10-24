"""
romanize_llm.py

Builds the Romanized condition (FT-Rom): the human-verified FT translation of
each query rewritten in everyday Latin-script typing (e.g. "ganit", not
"gaṇita"), with the same words in the same language. This is transliteration,
not translation, so no word is replaced by its English equivalent.

Input:  data/reviews/{hindi,tamil,gujarati}_final_resolved.jsonl (final FT text)
Output: data/romanized/multiple_romanized.jsonl (append-only, resumable)

Automatic checks recorded per row:
- native_script_left: characters of the source script still present
- numbers_match: same multiset of numbers as the source

USAGE (run from inside berkeley-function-call-leaderboard):
    python translation/romanize_llm.py hi --limit 20
"""

import argparse
import json
import os
import re
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

MODEL = "google/gemini-3.7-flash"
LANGS = {
    "hi": ("Hindi", "data/reviews/hindi_final_resolved.jsonl", r"[ऀ-ॿ]"),
    "gu": ("Gujarati", "data/reviews/gujarati_final_resolved.jsonl", r"[઀-૿]"),
    "ta": ("Tamil", "data/reviews/tamil_final_resolved.jsonl", r"[஀-௿]"),
}
OUT_PATH = Path("data/romanized/multiple_romanized.jsonl")

SYSTEM_PROMPT = (
    "You convert {lang} text written in its native script into Romanized {lang}: the same {lang} words "
    "written in Latin letters, the way people casually type {lang} on a phone keyboard (no diacritics, "
    "common everyday spellings).\n"
    "RULES:\n"
    "1. Transliterate only. Do NOT translate any {lang} word into English or change word choice or order.\n"
    "2. Keep every number, symbol, unit, punctuation mark, quote and bracket exactly as given.\n"
    "3. Keep any text already in Latin script (English words, names, codes, variable names) unchanged.\n"
    "4. Output ONLY the Romanized text, with no explanation."
)
NUM_RE = re.compile(r"\d+(?:[.,]\d+)*")


def load_jsonl(path):
    if not Path(path).exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("lang", choices=LANGS)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    name, gold_path, script_re = LANGS[args.lang]

    load_dotenv()
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL"),
                    timeout=60.0, max_retries=2)

    gold = sorted(load_jsonl(gold_path), key=lambda e: int(e["base_id"].rsplit("_", 1)[-1]))
    if args.limit:
        gold = gold[: args.limit]
    done = {(e["base_id"], e["language"]) for e in load_jsonl(OUT_PATH)}
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    n_new = 0
    with open(OUT_PATH, "a", encoding="utf-8") as out:
        for e in gold:
            if (e["base_id"], args.lang) in done:
                continue
            resp = client.chat.completions.create(
                model=MODEL,
                temperature=0,
                messages=[{"role": "system", "content": SYSTEM_PROMPT.format(lang=name)},
                          {"role": "user", "content": e["final_text"]}],
            )
            text = resp.choices[0].message.content.strip()
            row = {
                "base_id": e["base_id"],
                "language": args.lang,
                "composition": "FT-Rom",
                "perturbation_type": "NO",
                "source_text": e["final_text"],
                "text": text,
                "model": MODEL,
                "native_script_left": len(re.findall(script_re, text)),
                "numbers_match": Counter(NUM_RE.findall(text)) == Counter(NUM_RE.findall(e["final_text"])),
            }
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()
            n_new += 1
    rows = [r for r in load_jsonl(OUT_PATH) if r["language"] == args.lang]
    print(f"{name}: {n_new} new, {len(rows)} total | native script left in {sum(r['native_script_left'] > 0 for r in rows)} "
          f"| number mismatch in {sum(not r['numbers_match'] for r in rows)}")


if __name__ == "__main__":
    main()
