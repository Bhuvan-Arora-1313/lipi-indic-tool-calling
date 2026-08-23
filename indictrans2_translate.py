"""
indictrans2_translate.py

Translates the "question" field of a BFCL test file into Hindi or Tamil
using IndicTrans2 (AI4Bharat) -- a neural machine translation model
purpose-built for Indian languages, as opposed to a general-purpose LLM.

Unlike an LLM, this model cannot "helpfully" add content, solve the
problem, or otherwise generate anything not conditioned on the source
sentence -- it can only map source tokens to target tokens. That
structurally rules out the kind of bug we saw from the LLM translator
(adding a worked solution to a math question).

Runs entirely locally/offline once the model is downloaded -- no API
key needed, no per-call cost. Uses the distilled 200M model, which is
much lighter than the full 1B model and reasonable to run on a CPU
(no GPU needed, though it'll be slower without one).

ONE-TIME SETUP (run inside your activated bfcl_env):
    pip install IndicTransToolkit

USAGE (run from inside berkeley-function-call-leaderboard):
    # Quick preview on 5 examples first (also downloads the model on
    # this first run -- a few hundred MB, one-time, then it's cached)
    python indictrans2_translate.py --input bfcl_eval/data/BFCL_v4_simple_python.json --lang hi --limit 5

    # Full run
    python indictrans2_translate.py --input bfcl_eval/data/BFCL_v4_simple_python.json --lang hi
    python indictrans2_translate.py --input bfcl_eval/data/BFCL_v4_simple_python.json --lang ta

Output goes to a new file with "_indictrans2" in the name, so it never
overwrites your LLM-based translations -- you'll end up with both,
which is exactly what you want for comparing the two.
"""

import argparse
import json
import os
import sys
import traceback
from pathlib import Path

import torch
from dotenv import load_dotenv
from IndicTransToolkit import IndicProcessor
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

load_dotenv()

MODEL_NAME = "ai4bharat/indictrans2-en-indic-dist-200M"  # distilled -- feasible on CPU

# IndicTrans2 uses FLORES-200 style language codes
LANG_CODES = {"hi": "hin_Deva", "ta": "tam_Taml"}
LANG_NAMES = {"hi": "Hindi", "ta": "Tamil"}
SRC_LANG = "eng_Latn"


def load_model():
    print(f"Loading {MODEL_NAME}...")
    print("(first run downloads the model -- a few hundred MB, cached after that)")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        print("\nWARNING: No HF_TOKEN found in .env. This model is gated and needs one.")
        print("See the setup steps for creating a Hugging Face token and adding it to .env.\n")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True, token=hf_token)
    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME, trust_remote_code=True, token=hf_token).to(device)
    model.eval()
    ip = IndicProcessor(inference=True)
    print(f"Model loaded (running on {device}).")
    return tokenizer, model, ip, device


def translate_batch(texts, tokenizer, model, ip, tgt_lang_code, device, num_beams=1):
    batch = ip.preprocess_batch(texts, src_lang=SRC_LANG, tgt_lang=tgt_lang_code)
    inputs = tokenizer(
        batch, truncation=True, padding="longest", return_tensors="pt", return_attention_mask=True
    ).to(device)

    with torch.no_grad():
        generated_tokens = model.generate(
            **inputs,
            use_cache=False,
            min_length=0,
            max_length=256,
            num_beams=num_beams,
            num_return_sequences=1,
        )

    decoded = tokenizer.batch_decode(generated_tokens, skip_special_tokens=True, clean_up_tokenization_spaces=True)
    translations = ip.postprocess_batch(decoded, lang=tgt_lang_code)
    return translations


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--lang", required=True, choices=["hi", "ta"])
    parser.add_argument("--limit", type=int, default=None, help="Only translate the first N examples (for a quick preview)")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--num-beams", type=int, default=1, help="1 = greedy decoding (default, works around a cache bug); higher = beam search")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path.with_name(
        input_path.stem + f"_{args.lang}_indictrans2" + input_path.suffix
    )

    examples = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                examples.append(json.loads(line))

    if args.limit:
        examples = examples[: args.limit]

    try:
        tokenizer, model, ip, device = load_model()
    except Exception as e:
        print(f"\nERROR loading model: {e}")
        print("Paste this error back to Claude for help debugging before trying again.")
        sys.exit(1)

    tgt_lang_code = LANG_CODES[args.lang]
    print(f"\nTranslating {len(examples)} examples into {LANG_NAMES[args.lang]}...")

    with open(output_path, "w", encoding="utf-8") as out_f:
        for i in range(0, len(examples), args.batch_size):
            batch = examples[i : i + args.batch_size]
            texts = [ex["question"][0][0]["content"] for ex in batch]

            try:
                translations = translate_batch(texts, tokenizer, model, ip, tgt_lang_code, device, num_beams=args.num_beams)
            except Exception as e:
                print(f"\nERROR translating batch starting at index {i}:")
                traceback.print_exc()
                print(f"\nThe texts in this batch were: {texts}")
                print("Paste all of the above back to Claude. Partial output up to this point has been saved.")
                sys.exit(1)

            for ex, translated_text in zip(batch, translations):
                original_text = ex["question"][0][0]["content"]
                new_ex = json.loads(json.dumps(ex))
                new_ex["question"][0][0]["content"] = translated_text
                new_ex["question_en"] = original_text
                out_f.write(json.dumps(new_ex, ensure_ascii=False) + "\n")
                print(f"  {ex['id']}")
                print(f"     EN: {original_text}")
                print(f"     {args.lang.upper()}: {translated_text}")

            out_f.flush()
            print(f"  [{min(i + args.batch_size, len(examples))}/{len(examples)}] done\n")

    print(f"Done. Wrote translations to {output_path}")


if __name__ == "__main__":
    main()
