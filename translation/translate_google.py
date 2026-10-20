"""
translate_google.py

Produces the second FT (fully translated) candidate, via the Google Cloud
Translation API (Basic/v2) -- the counterpart to translate_indictrans2.py.
Reviewers will be shown BOTH candidates per item and pick whichever they
judge correct (see translation/generate_review_sheets_dual.py, TODO).

Needs GOOGLE_TRANSLATE_API_KEY in .env, with the Cloud Translation API
enabled and unrestricted (or explicitly allowed) on that key's project,
and billing linked to the project (required even to use the free
500,000-chars/month tier). Confirmed working live 2026-09-19.

Input: same as translate_indictrans2.py -- NO from
data/perturbations/en_multiple_perturbations.jsonl, PARA/SYNO from the
Cycle 2 resolved English (data/reviews/parasyno_final_resolved.jsonl),
since that's the reviewed/corrected text, not the stale pre-review
version.
Output: data/translations/multiple_translations_google.jsonl -- separate
file from IndicTrans2's output (different producer, same schema shape)
so neither can silently clobber the other; joined only at review-sheet
build time.

USAGE (run from inside berkeley-function-call-leaderboard):
    # Quick preview first
    python translation/translate_google.py --lang hi --limit 5

    # Full run (PARA/SYNO by default, since that's what NO already has
    # human-reviewed IndicTrans2-only translations for)
    python translation/translate_google.py --lang hi
    python translation/translate_google.py --lang ta
    python translation/translate_google.py --lang gu
"""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv
import os

load_dotenv()

API_URL = "https://translation.googleapis.com/language/translate/v2"
MODEL_NAME = "google_cloud_translate_v2_basic"

# Google Cloud Translation uses plain ISO 639-1 codes -- no FLORES-style
# script suffix needed (unlike IndicTrans2). Santali/Bodo are NOT
# supported by this API (confirmed against Google's supported-languages
# list 2026-09-19) -- omitted here, not silently mapped to something else.
LANG_CODES = {"hi": "hi", "ta": "ta", "mr": "mr", "bn": "bn", "gu": "gu"}
LANG_NAMES = {"hi": "Hindi", "ta": "Tamil", "mr": "Marathi", "bn": "Bengali", "gu": "Gujarati"}

SOURCE_PATH = Path("data/perturbations/en_multiple_perturbations.jsonl")
PARASYNO_RESOLVED_PATH = Path("data/reviews/parasyno_final_resolved.jsonl")
OUTPUT_PATH = Path("data/translations/multiple_translations_google.jsonl")

BATCH_SIZE = 20  # Translate v2 accepts multiple `q` values per request
MAX_RETRIES = 3


def load_jsonl(path):
    if not path.exists():
        return []
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def load_source_rows(perturbation_types):
    rows = []
    if "NO" in perturbation_types:
        rows.extend(e for e in load_jsonl(SOURCE_PATH) if e["perturbation_type"] == "NO")
    para_syno_types = [pt for pt in perturbation_types if pt in ("PARA", "SYNO")]
    if para_syno_types:
        resolved = load_jsonl(PARASYNO_RESOLVED_PATH)
        if not resolved:
            print(f"ERROR: {PARASYNO_RESOLVED_PATH} not found or empty. Run resolve_cycle2_parasyno.py first.")
        rows.extend(
            {"base_id": e["base_id"], "perturbation_type": e["perturbation_type"], "text": e["final_text"]}
            for e in resolved if e["perturbation_type"] in para_syno_types
        )
    return rows


def translate_batch(texts, target_lang, api_key):
    for attempt in range(1, MAX_RETRIES + 1):
        resp = requests.post(
            API_URL,
            params={"key": api_key},
            json={"q": texts, "target": target_lang, "source": "en", "format": "text"},
            timeout=30,
        )
        if resp.status_code == 200:
            return [t["translatedText"] for t in resp.json()["data"]["translations"]]
        if resp.status_code in (429, 500, 502, 503) and attempt < MAX_RETRIES:
            wait = 2 ** attempt
            print(f"  [retry {attempt}/{MAX_RETRIES}] HTTP {resp.status_code}, waiting {wait}s...")
            time.sleep(wait)
            continue
        raise RuntimeError(f"Translation API error {resp.status_code}: {resp.text}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", required=True, choices=list(LANG_CODES.keys()))
    parser.add_argument("--perturbation-types", nargs="+", default=["PARA", "SYNO"],
                         choices=["NO", "PARA", "SYNO"],
                         help="Which English source rows to translate (default: PARA+SYNO).")
    parser.add_argument("--limit", type=int, default=None, help="Only translate the first N examples (for a quick preview).")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    args = parser.parse_args()

    api_key = os.environ.get("GOOGLE_TRANSLATE_API_KEY")
    if not api_key:
        print("ERROR: GOOGLE_TRANSLATE_API_KEY not set in .env")
        return

    source_entries = load_source_rows(args.perturbation_types)
    if not source_entries:
        print(f"ERROR: no source rows found for perturbation types {args.perturbation_types}. "
              f"Check {SOURCE_PATH} (for NO) / {PARASYNO_RESOLVED_PATH} (for PARA/SYNO) exist.")
        return
    if args.limit:
        source_entries = source_entries[: args.limit]

    existing = load_jsonl(OUTPUT_PATH)
    already_done = {
        (e["base_id"], e["language"], e["composition"], e["perturbation_type"]) for e in existing
    }
    todo = [
        e for e in source_entries
        if (e["base_id"], args.lang, "FT", e["perturbation_type"]) not in already_done
    ]
    print(f"{len(source_entries)} source rows selected, {len(todo)} need translation "
          f"({len(source_entries) - len(todo)} already present).")
    if not todo:
        print("Nothing to do.")
        return

    total_chars = sum(len(e["text"]) for e in todo)
    print(f"Estimated {total_chars} characters to translate into {LANG_NAMES[args.lang]} "
          f"(well within the 500K/month free tier).")

    tgt_lang_code = LANG_CODES[args.lang]
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    n_done = 0
    with open(OUTPUT_PATH, "a", encoding="utf-8") as out_f:
        for i in range(0, len(todo), args.batch_size):
            batch = todo[i: i + args.batch_size]
            texts = [e["text"] for e in batch]
            translations = translate_batch(texts, tgt_lang_code, api_key)
            for src_entry, translated_text in zip(batch, translations):
                out_f.write(json.dumps({
                    "base_id": src_entry["base_id"],
                    "language": args.lang,
                    "composition": "FT",
                    "perturbation_type": src_entry["perturbation_type"],
                    "text": translated_text,
                    "source_text": src_entry["text"],
                    "model": MODEL_NAME,
                    "method": "google_translate_api",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "review_status": "pending",
                    "review_notes": "",
                }, ensure_ascii=False) + "\n")
            out_f.flush()
            n_done += len(batch)
            print(f"  [{n_done}/{len(todo)}] done")
            if i == 0:
                for src_entry, translated_text in zip(batch[:2], translations[:2]):
                    print(f"    sample -- EN: {src_entry['text'][:70]}")
                    print(f"              {LANG_NAMES[args.lang]}: {translated_text[:70]}")

    print(f"\nDone. Translated {n_done} rows into {LANG_NAMES[args.lang]}.")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
