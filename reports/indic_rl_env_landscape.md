# Indic datasets as RL environments: landscape (checked 2026-10-24)

**Question:** which Indic datasets could become RL environments (benchmark + training) that nobody has built yet?

## Main finding

AI4Bharat + NVIDIA released 16 translated benchmarks (Indic-LLM-Eval-Suite, Sept–Oct 2026).
- All 16 are **evaluation-only**.
- Each has fewer than 250 downloads on Hugging Face.
- No RL environment, training use or paper exists for any of them (the report is still "coming soon").
- Only exception: a third-party blog post says IndicIFEval (an older AI4Bharat benchmark, Feb 2026) was turned into a Prime RL environment, `indic-ifeval`. Treat that one as taken.

## Candidates

| Dataset | Task | Reward checkable automatically? | Size | Licence | Fit as RL env |
|---|---|---|---|---|---|
| **LIPI (ours)** | Tool calling | Yes: AST match, plus a penalty for Indic text in English-only arguments | 200 per condition | ours | **Strong.** Test set only; training data must come from a larger translated tool set |
| **IndicDB** (Dhruv Kumar's group, arXiv 2604.13686) | Text-to-SQL, 7 language variants | Yes: run the SQL and compare results | 15,617 tasks | n/a | **Strongest.** In-house, large enough to train on, execution-verified |
| indic-swe-bench | Fix GitHub issues (issue text translated, code English) | Yes: repo tests | 500 × 14 languages | Apache-2.0 | Possible but heavy: a Docker image per task, long agent runs. Test set only; training needs translated SWE-Gym / SWE-smith tasks |
| indic-gsm8k, indic-math-500, indic-frontier-math | Maths | Yes: final answer | 1.3k / 500 / small | Apache-2.0 | Easy, but crowded: maths RLVR is common in English |
| indic-aime-2026 | Maths | Yes | 30-ish | CC-BY-NC-SA | Too small, non-commercial |
| indic-jee-bench | JEE maths/physics/chem | Yes (MCQ / numeric) | ? | MIT | Good: India-specific, verifiable |
| indic-humaneval, indic-mbpp | Code | Yes: unit tests | 164 / ~500 | Apache-2.0 | Easy, small |
| MILU-1.5, indic-mmlu-pro, indic-gpqa, indic-arc, indic-hle | Multiple choice | Yes, but guessable | various | various | Weak: MCQ rewards invite guessing |
| indic-arena-hard-v2, indic-alpaca-eval, indic-biggenbench | Open chat | No: needs an LLM judge | various | some NC | Weak |
| IndicIFEval | Instruction following | Yes: rule checkers | 14 languages | — | Already done by someone (Prime RL) |

## Caveats

1. **Test sets must not be trained on.** All AI4Bharat sets are benchmarks. An environment should *evaluate* on them and *train* on separate data (translated training sets), or the benchmark becomes contaminated.
2. **Novelty must come from a question, not from wrapping a dataset.** Good questions: does training in one script or language transfer to others (Romanized, Gujarati, Tamil)? Does issue language change patch success (SWE)? Does argument-language reward fix value copying (LIPI)?
3. Prior RL work on the copying failure: Chauhan et al. 2026 (European languages only).

## Recommendation

1. Build **one multi-task Indic agent environment** with verifiable rewards: LIPI (tool calling) + IndicDB (SQL). Optionally add indic-swe-bench as a hard eval-only split.
2. Core experiment: cross-language and cross-script transfer of RL training.

## Sources

- https://huggingface.co/datasets/ai4bharat/indic-swe-bench
- https://ai4bharat.github.io/indic-llm-eval-suite-blog/
- https://arxiv.org/abs/2604.13686 (IndicDB)
- https://arxiv.org/html/2602.22125v1 (IndicIFEval)
- https://x.com/adityapuranik99/article/2031876535767220476 (indic-ifeval Prime RL env, third-party)
- Hugging Face API for licences and downloads (checked 2026-10-24)
