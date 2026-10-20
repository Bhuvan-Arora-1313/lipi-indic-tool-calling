"""
translate_indictrans2.py

Produces the FT (fully translated) condition via IndicTrans2 (AI4Bharat) --
a dedicated NMT model, not an LLM. Runs entirely locally/offline once the
model weights are cached (needs HF_TOKEN once, for the gated download).

Input: data/perturbations/en_multiple_perturbations.jsonl (the canonical
English source -- NO/PARA/SYNO rows for all 199 base queries).
Output: data/translations/multiple_translations.jsonl -- raw, immutable
per the data provenance policy in PROJECT_MANIFEST.md. One row per
(base_id, language, composition, perturbation_type).

PAR (partially translated, English parameter values preserved) is NOT
handled here -- IndicTrans2 has no mechanism to selectively preserve
spans, and MLCL's own PAR construction is LLM-instruction-based, not NMT.
See LOG.md (2026-08-24) for that decision.

USAGE (run from inside berkeley-function-call-leaderboard):
    # Quick preview first (also downloads the model on first run --
    # a few hundred MB, one-time, then cached)
    python translation/translate_indictrans2.py --lang hi --limit 5
    python translation/translate_indictrans2.py --lang ta --limit 5

    # Full run (all NO rows by default; add --perturbation-types to widen)
    python translation/translate_indictrans2.py --lang hi
    python translation/translate_indictrans2.py --lang ta
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import torch
from dotenv import load_dotenv
from IndicTransToolkit import IndicProcessor
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

load_dotenv()

MODEL_NAME = "ai4bharat/indictrans2-en-indic-dist-200M"

# IndicTrans2 uses FLORES-200 style language codes. Full 5-language set
# from the project plan, plus Gujarati (added 2026-08-24 at the user's
# request -- not one of the original 5 plan languages, noted here for
# traceability). Confirmed via AI4Bharat's language list that all of
# these (including both Santali and Bodo) are natively supported.
LANG_CODES = {
    "hi": "hin_Deva",
    "ta": "tam_Taml",
    "mr": "mar_Deva",
    "bn": "ben_Beng",
    "sat": "sat_Olck",
    "brx": "brx_Deva",
    "gu": "guj_Gujr",
}
LANG_NAMES = {"hi": "Hindi", "ta": "Tamil", "mr": "Marathi", "bn": "Bengali", "sat": "Santali", "brx": "Bodo", "gu": "Gujarati"}
SRC_LANG = "eng_Latn"

SOURCE_PATH = Path("data/perturbations/en_multiple_perturbations.jsonl")
# PARA/SYNO English text goes through Cycle 1/2 human review (see
# translation/resolve_cycle2_parasyno.py) -- roughly a dozen items were
# corrected there. Translate the reviewed/corrected text, not the stale
# pre-review version still sitting in SOURCE_PATH.
PARASYNO_RESOLVED_PATH = Path("data/reviews/parasyno_final_resolved.jsonl")
OUTPUT_PATH = Path("data/translations/multiple_translations.jsonl")


def get_device():
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def load_model(device):
    print(f"Loading {MODEL_NAME}...")
    print("(first run downloads the model -- a few hundred MB, cached after that)")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME, trust_remote_code=True).to(device)
    model.eval()
    ip = IndicProcessor(inference=True)
    print(f"Model loaded (running on {device}).")
    return tokenizer, model, ip


def translate_batch(texts, tokenizer, model, ip, tgt_lang_code, device):
    batch = ip.preprocess_batch(texts, src_lang=SRC_LANG, tgt_lang=tgt_lang_code)
    inputs = tokenizer(
        batch, truncation=True, padding="longest", return_tensors="pt", return_attention_mask=True
    ).to(device)
    with torch.no_grad():
        generated_tokens = model.generate(
            **inputs, use_cache=False, min_length=0, max_length=256, num_beams=1, num_return_sequences=1,
        )
    decoded = tokenizer.batch_decode(generated_tokens, skip_special_tokens=True, clean_up_tokenization_spaces=True)
    return ip.postprocess_batch(decoded, lang=tgt_lang_code)


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
    """NO comes from the original generator output (never reviewed at the
    English level). PARA/SYNO comes from the Cycle 2 resolved file, since
    that's the reviewed/corrected English text -- see PARASYNO_RESOLVED_PATH."""
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", required=True, choices=list(LANG_CODES.keys()))
    parser.add_argument("--perturbation-types", nargs="+", default=["NO"],
                         choices=["NO", "PARA", "SYNO"],
                         help="Which English source rows to translate (default: NO only).")
    parser.add_argument("--limit", type=int, default=None, help="Only translate the first N examples (for a quick preview).")
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()

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

    device = get_device()
    tokenizer, model, ip = load_model(device)
    tgt_lang_code = LANG_CODES[args.lang]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    n_done = 0
    with open(OUTPUT_PATH, "a", encoding="utf-8") as out_f:
        for i in range(0, len(todo), args.batch_size):
            batch = todo[i: i + args.batch_size]
            texts = [e["text"] for e in batch]
            translations = translate_batch(texts, tokenizer, model, ip, tgt_lang_code, device)
            for src_entry, translated_text in zip(batch, translations):
                out_f.write(json.dumps({
                    "base_id": src_entry["base_id"],
                    "language": args.lang,
                    "composition": "FT",
                    "perturbation_type": src_entry["perturbation_type"],
                    "text": translated_text,
                    "source_text": src_entry["text"],
                    "model": MODEL_NAME,
                    "method": "indictrans2_local",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "review_status": "pending",
                    "review_notes": "",
                }, ensure_ascii=False) + "\n")
            out_f.flush()
            n_done += len(batch)
            print(f"  [{n_done}/{len(todo)}] done")

    print(f"\nDone. Translated {n_done} rows into {LANG_NAMES[args.lang]}.")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
