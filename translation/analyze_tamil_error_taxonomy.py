"""
analyze_tamil_error_taxonomy.py

Breaks down the Qwen3-32B Tamil ("multiple_ta") failures from the just-run
experiment using the MLCL 8-category error taxonomy (severity order), rather
than just the aggregate pass/fail accuracy BFCL's own `evaluate` reports.

This is pure analysis over data we already have (score/result files from the
2026-09-10 Qwen3-32B run) -- no new GPU run needed.

Method, and its honest limits:
  - Bucket 1 (Syntax Error) / Bucket 2 (Function-Level Error): read directly
    off BFCL's own error_type field (decoder-failure / wrong function name or
    count) -- these are unambiguous, no judgment call needed.
  - For every remaining value-level failure (error_type starting
    "value_error:"), we check whether the model's actual output value for
    that parameter contains Tamil-script characters (Unicode block
    U+0B80-U+0BFF) where the expected answer is English/numeric. That split
    (language-mismatch present vs. not) is mechanical and reliable.
  - We do NOT attempt the finer MLCL sub-split within language-mismatch
    (same-meaning vs. relevant-but-wrong vs. wrong-value) or within the
    English-value-error bucket (wrong-value vs. relevant-but-incorrect vs.
    correct-but-fails-strict-match) -- those require semantic judgment
    (e.g. back-translating the Tamil value and comparing meaning) that this
    pass does not do. Flagged in the output, not silently collapsed.
  - We DO add one extra, cheap, high-value signal beyond the taxonomy: for
    every Tamil failure, whether the identical underlying question (by
    original_id) succeeded in English. That tells us directly whether the
    failure is language-specific or a task the model can't do regardless of
    language.

USAGE (run from inside berkeley-function-call-leaderboard, after pulling the
score/ and result/ files down from the cluster):
    python translation/analyze_tamil_error_taxonomy.py
"""

import json
import re
from collections import Counter
from pathlib import Path

TAMIL_SCORE_PATH = Path("score/Qwen_Qwen3-32B-FC/non_live/BFCL_v4_multiple_ta_score.json")
ENGLISH_SCORE_PATH = Path("score/Qwen_Qwen3-32B-FC/non_live/BFCL_v4_multiple_score.json")
TAMIL_PROMPT_PATH = Path("bfcl_eval/data/BFCL_v4_multiple_ta.json")

TAMIL_SCRIPT_RE = re.compile(r"[஀-௿]")

FUNCTION_LEVEL_ERROR_TYPES = {
    "multiple_function_checker:wrong_count",
    "simple_function_checker:wrong_func_name",
    "parallel_function_checker:wrong_count",
}
SYNTAX_ERROR_TYPES = {
    "ast_decoder:decoder_failed",
    "ast_decoder:decoder_wrong_output_type",
}


def load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def contains_tamil_script(value) -> bool:
    if isinstance(value, str):
        return bool(TAMIL_SCRIPT_RE.search(value))
    if isinstance(value, (list, tuple)):
        return any(contains_tamil_script(v) for v in value)
    if isinstance(value, dict):
        return any(contains_tamil_script(k) or contains_tamil_script(v) for k, v in value.items())
    return False


def has_language_mismatch(entry) -> bool:
    """Does any value in the model's actual output contain Tamil script?"""
    decoded = entry.get("model_result_decoded")
    if not decoded:
        return False
    for call in decoded:
        for func_name, args in call.items():
            if contains_tamil_script(args):
                return True
    return False


def main():
    tamil_scores = load_jsonl(TAMIL_SCORE_PATH)
    english_scores = load_jsonl(ENGLISH_SCORE_PATH)
    tamil_prompts = {e["id"]: e for e in load_jsonl(TAMIL_PROMPT_PATH)}

    tamil_summary, tamil_failures = tamil_scores[0], tamil_scores[1:]
    english_summary = english_scores[0]
    # English score file's failure entries -> which original_ids failed in English
    english_failed_ids = {e["id"] for e in english_scores[1:]}

    print(f"Tamil accuracy: {tamil_summary['accuracy']:.1%} ({tamil_summary['correct_count']}/{tamil_summary['total_count']})")
    print(f"English accuracy: {english_summary['accuracy']:.1%} ({english_summary['correct_count']}/{english_summary['total_count']})")
    print(f"Tamil failures to classify: {len(tamil_failures)}")
    print()

    buckets = Counter()
    bucket_items = {}
    lang_specific_count = 0  # Tamil failed AND English succeeded on the same question

    for entry in tamil_failures:
        error_type = entry["error_type"]
        original_id = tamil_prompts[entry["id"]]["original_id"]
        english_also_failed = original_id in english_failed_ids

        if error_type in SYNTAX_ERROR_TYPES:
            bucket = "1_syntax_error"
        elif error_type in FUNCTION_LEVEL_ERROR_TYPES:
            bucket = "2_function_level_error"
        elif error_type.startswith("value_error"):
            bucket = "language_mismatch" if has_language_mismatch(entry) else "wrong_value_english"
        else:
            bucket = f"unclassified:{error_type}"

        buckets[bucket] += 1
        bucket_items.setdefault(bucket, []).append(entry["id"])

        if not english_also_failed:
            lang_specific_count += 1

    print("=== Bucket breakdown (of the 41 Tamil failures) ===")
    for bucket, count in buckets.most_common():
        pct_of_failures = count / len(tamil_failures) * 100
        pct_of_total = count / tamil_summary["total_count"] * 100
        print(f"  {bucket}: {count} ({pct_of_failures:.1f}% of failures, {pct_of_total:.1f}% of all 200)")

    print()
    print(f"=== Language-specificity check (paired with English on the same question) ===")
    print(f"  Tamil failed AND English succeeded on the same question: {lang_specific_count}/{len(tamil_failures)} "
          f"({lang_specific_count/len(tamil_failures)*100:.1f}% of Tamil failures)")
    print(f"  Tamil failed AND English ALSO failed (not language-specific): {len(tamil_failures) - lang_specific_count}/{len(tamil_failures)}")

    print()
    print("=== NOT done in this pass (flagged, not silently skipped) ===")
    print("  - No semantic sub-split within 'language_mismatch' (same-meaning vs. relevant-but-wrong vs. wrong-value)")
    print("  - No semantic sub-split within 'wrong_value_english' (wrong-value vs. relevant-but-incorrect vs. correct-but-strict-match-failure)")
    print("  These need per-item judgment (e.g. back-translation), not yet built.")

    out = {
        "model": "Qwen/Qwen3-32B-FC",
        "tamil_accuracy": tamil_summary["accuracy"],
        "english_accuracy": english_summary["accuracy"],
        "bucket_counts": dict(buckets),
        "bucket_items": bucket_items,
        "language_specific_failure_count": lang_specific_count,
        "total_tamil_failures": len(tamil_failures),
        "not_yet_done": [
            "semantic sub-split within language_mismatch (same-meaning / relevant-but-wrong / wrong-value)",
            "semantic sub-split within wrong_value_english (wrong-value / relevant-but-incorrect / correct-but-strict-match-failure)",
        ],
    }
    out_path = Path("data/reviews/qwen32b_tamil_error_taxonomy.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
