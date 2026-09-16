# Log

*Chronological record of actions taken, commands run, and decisions made.
Append-only. For current high-level status, see `PROGRESS.md`.*

---

## 2026-08-23

**Diagnosed the `fix_number_matching.py` regression (pilot project, now archived).**
- Ran `check_regression.py` (new script) comparing `simple_python_hi` vs
  `simple_python_hi_numfix` score files: 17 regressions, 0 improvements
  out of 400 examples (55.25% vs. 59.50% baseline).
- Root-caused by hand-tracing `simple_python_hi_3`: `extract_numbers_from_text`
  used `.strip("-.")`, which strips from both ends of the string, silently
  deleting genuine leading minus signs (e.g. `-3` -> `3`).
- Found two more bugs: digits embedded in identifiers (e.g. `B1004`) getting
  extracted as real quantities; and the core assumption -- that every correct
  output number must appear literally as digits in the source text -- is false
  whenever the correct value requires a derived transformation (percent to
  decimal, unit conversion, AM/PM to 24hr, degrees, etc.). 13 of 17
  regressions were this category.
- Patched the two implementation bugs in `fix_number_matching.py`. Re-ran:
  56.50% (12 regressions remain, all in the "derived value" category, still
  0 improvements -- confirms the deeper design issue is real, not fixed by
  the patch).
- Verified via a specific case (`hi_42`, LC circuit resonant frequency) that
  the *original* Hindi model output was already correct (matched the English
  answer exactly, correct unit conversion mH->H) -- the regression was
  100% self-inflicted by the fix script, not a pre-existing language weakness
  or evaluator strictness. Confirms the evaluator itself is not the problem
  here; the repair strategy's core assumption is.

**Received `Indic_ToolCalling_Project_Plan.md` -- new project plan, supersedes prior pilot scope.**
5 languages (Hindi/Marathi/Bengali/Tamil/Santali-Bodo), 8 models (GPT-5,
Gemini 2.5, DeepSeek V3.2, Qwen3, Llama, Sarvam-105B/30B/M), full MLCL grid +
Romanization axis, 8-category taxonomy, `BFCL_v4_multiple.json` base dataset,
Exp 0-5 sequence.

**Set up git + GitHub, restructured the repo.**
- Found `bfcl_env` (referenced in old notes) doesn't exist as a conda env --
  it's a plain virtualenv at `BFCL-eval/bfcl_env`, Python 3.11.9, all deps
  already present. Use this going forward, not `base` conda.
- User set up SSH key (`~/.ssh/id_ed25519`) and registered it with GitHub
  (`Bhuvan-Arora-1313`); confirmed working via `ssh -T git@github.com`.
- `git init` at `berkeley-function-call-leaderboard/` (chosen repo root --
  this is where all actual project content lives; `gorilla/` has its own
  separate `.git` as the upstream BFCL clone, and `bfcl_env/` is the
  virtualenv, neither committed).
- `.gitignore` created first (excludes `.env`, caches, `.DS_Store`,
  `.file_locks/`, `bfcl_eval.egg-info/`) -- confirmed `.env` (API keys) never
  got staged.
- Commit 1 (`dcb8c5f`): full snapshot of the pilot as a safety net.
- Created `archive/pilot-hindi-tamil-simple-python` branch at that commit.
- Commit 2 (`ada326e`) on `main`: removed all pilot-specific files (scripts,
  translated data under `bfcl_eval/data/`, results, scores,
  `research_notes.md`), restored `bfcl_eval/constants/category_mapping.py`
  to clean upstream (removed 21 pilot-added category entries), added
  `Indic_ToolCalling_Project_Plan.md`, `PROJECT_MANIFEST.md`, and skeleton
  folders (`data/`, `translation/`, `experiments/`, `analysis/`, `results/`,
  each with a README).
- Removed 4 stray accidental empty folders at the `BFCL-eval/` top level
  (`cd`, `clone`, `git`, `https:` -- leftover from a mistyped command).
- Added remote `origin` = `git@github.com:Bhuvan-Arora-1313/Indic-tool-calling-agentic-ai.git`,
  pushed both `main` and the archive branch.

**Started Exp 0 (tool-calling smoke test) investigation.**
- Checked BFCL's existing model support against the 8-model roster: Gemini
  2.5 Flash, DeepSeek V3.2, and Qwen3 (cloud) all already have handlers +
  matching API keys in `.env`. GPT-5 has no plain entry (only
  gpt-5.2/mini/nano) and its config looks tuned for direct OpenAI API rather
  than OpenRouter. Llama's built-in handler (`LlamaHandler`) expects local
  GPU serving, not viable here -- plan is to register a separate
  OpenRouter-routed entry instead. Sarvam has no handler and no API key at
  all -- confirmed not on OpenRouter (user has a separate Sarvam key
  elsewhere, not yet in `.env`).
- Clarified for the user how BFCL's model registry works: it's a
  name -> handler mapping, not a hard restriction. Any model reachable via
  OpenRouter can reuse the existing OpenAI-compatible handler with just a
  new registry entry (no new code). A genuinely new handler is only needed
  for a provider with its own distinct API format (Sarvam's situation).

**Plan change: add Qwen3-8B running locally via Ollama, as the first pipeline test.**
- Confirmed Ollama installed (v0.32.7) and running, serving an
  OpenAI-compatible API at `localhost:11434/v1` (verified via `curl`).
  `qwen3:30b` already pulled; `qwen3:8b` is not.
- Found BFCL already has `QwenFCHandler`
  (`bfcl_eval/model_handler/local_inference/qwen_fc.py`), built exactly for
  self-hosted Qwen via an OpenAI-compatible local server, and its base class
  (`OSSHandler`) already reads `LOCAL_SERVER_ENDPOINT`/`LOCAL_SERVER_PORT`
  (or `REMOTE_OPENAI_BASE_URL`/`REMOTE_OPENAI_API_KEY`) to point at exactly
  such a server. No new handler code needed -- just a new registry entry
  pointing the existing handler at Ollama's endpoint, plus pulling the
  `qwen3:8b` model.

**Generated PARA/SYNO perturbation data.**
- Confirmed via research (WebSearch + WebFetch on arXiv 2601.05366) that
  MLCL's own data/code release is an anonymized peer-review link
  (`anonymous.4open.science/...`) that returns 403 -- not usable, and
  wouldn't cover our 5 languages regardless (MLCL only tested Hindi among
  Indic languages). Confirmed MLCL used the *full* `BFCL_v4_multiple.json`
  subset with no further downsampling -- same as us (200 examples is all
  there is, not an arbitrary cut). [Corrected 2026-08-24: this was first
  reported as 199 due to a `wc -l` miscount -- the file has no trailing
  newline after its last entry, so `wc -l` undercounts by one. Verified
  properly (parsing actual JSON entries): 200. The generation script was
  never affected, since JSONL parsing doesn't depend on trailing newlines
  -- only the verbal report to the user was wrong, now corrected.]
  Retrieved MLCL's exact PARA (Appendix A.8) and SYNO (Appendix A.9,
  including its worked few-shot example) prompts verbatim, for
  methodological comparability. User independently confirmed both prompts
  matched what they'd found themselves.
- Designed a data provenance policy (now in `PROJECT_MANIFEST.md`): raw
  generation / QA findings / corrections as three separate, append-only
  layers, never merged in place -- so any data point's raw-vs-corrected
  status stays traceable, per the user's explicit requirement for paper
  accountability.
- Built `translation/generate_perturbations.py`: calls
  `google/gemini-3.7-flash` via OpenRouter, separate calls for PARA and
  SYNO (user's choice over a combined single-call approach), writes to
  `data/perturbations/en_multiple_perturbations.jsonl`. Idempotent (skips
  already-generated (base_id, perturbation_type) pairs on rerun).
- Smoke-tested on 3 queries first. Found `multiple_0`'s PARA reordered a
  triangle's side-length numbers (5,4,3 -> 3,4,5) -- investigated with the
  user and correctly walked back an overstated initial concern: pure
  reordering is normal, expected paraphrase behavior and harmless for a
  symmetric function like this one. The real risk category is numbers
  being dropped/added/substituted (a genuine meaning change), not
  reordering.
- Ran the full batch: 197 remaining queries (3 already done) x 2 types =
  394 calls, 0 errors. Total dataset: 600 rows (200 NO + 200 PARA + 200
  SYNO).
- Built `translation/check_perturbation_number_drift.py`: order-independent
  number-SET comparison (source vs. perturbed text), read-only against the
  raw file, writes findings to a separate `..._qa.jsonl` file per the
  provenance policy. Result: 1/400 flagged, investigated by hand and found
  to be the checker's own false positive (`multiple_64`: source text has
  "June01" with no space, which the identifier-glue guard -- built to skip
  digits inside IDs like "B1004" -- treats differently than the correctly
  space-separated "June 01" in the PARA output; same date, no real drift).
  **0 genuine issues found across all 400 rows.**
- Actual cost: $0.4734 (400 calls, 57,280 input / 241,018 output tokens).
  Corrected an earlier pre-run estimate of $0.06-0.11 that didn't account
  for Gemini 3.7 Flash's apparent internal-reasoning tokens being billed
  as completion tokens (~6x more output tokens than guessed). Reported the
  correction rather than letting the earlier estimate stand.

**Executed the Qwen3-8B-via-Ollama plan; pipeline confirmed working end-to-end.**
- Corrected an earlier mistake: had reported Gemini/DeepSeek/Qwen(cloud) as
  "ready" based only on the *existence* of their `.env` variable names --
  actually checking values showed `DEEPSEEK_API_KEY`/`QWEN_API_KEY` are
  literal placeholders (`sk-XXXXXX`) and `GOOGLE_API_KEY` is empty. None are
  actually usable yet.
- `ollama pull qwen3:8b` (5.2 GB, ~2.5 min).
- Found BFCL already had a local-inference `Qwen/Qwen3-8B-FC` entry using
  `QwenFCHandler`, but its `model_name` is HuggingFace-style
  (`Qwen/Qwen3-8B`) -- checked `base_oss_handler.py` and confirmed the API
  request sends this exact string as the `model=` field, which would 404
  against Ollama (Ollama calls it `qwen3:8b`). `--local-model-path` can't
  fix this either -- it requires a real local HF-format directory
  (`config.json`/`tokenizer_config.json`), which Ollama doesn't provide.
  Added a separate registry entry, `qwen3-8b-ollama-FC`, with
  `model_name="qwen3:8b"` to match Ollama's naming (in
  `bfcl_eval/constants/model_config.py` and `supported_models.py`).
- Set `REMOTE_OPENAI_BASE_URL=http://localhost:11434/v1` in `.env`. First
  run failed with `HFValidationError` -- the handler also loads a tokenizer
  from HF Hub keyed on `model_name`, and `"qwen3:8b"` isn't a valid HF repo
  ID (colon not allowed). Fixed by setting
  `REMOTE_OPENAI_TOKENIZER_PATH=Qwen/Qwen3-8B` (the real HF repo), which the
  handler uses for tokenizer loading independent of the API's `model=`
  field.
- `bfcl generate --model qwen3-8b-ollama-FC --test-category multiple --run-ids
  --skip-server-setup` needed a fixed-path id file at
  `test_case_ids_to_generate.json` (repo root) -- the canonical smoke-test
  list lives at `experiments/exp0_smoke_test_ids.json` (12 ids from
  `multiple`, BFCL's own numbering `multiple_0`..`multiple_11`), copied to
  the required location to run.
- Ran successfully: 12/12 generated in ~2m25s. `bfcl evaluate --partial-eval`
  (needed since only 12 of 200 `multiple` entries were generated): **91.67%
  (11/12)**. The 1 failure (`multiple_7`) is `multiple_function_checker:wrong_count`
  -- a genuine model error (wrong function selected), not a parsing/mechanics
  failure. Confirms the pipeline works end-to-end for this model: Ollama
  serving, tokenizer loading, generation, and BFCL's evaluator all correctly
  wired together.

## 2026-08-24

**Translated NO (baseline) English queries into Hindi and Tamil via IndicTrans2 (FT condition).**
- Decision: PAR (partially translated) cannot be built with IndicTrans2 --
  confirmed via the paper that MLCL's own PAR construction is an LLM
  instruction ("translate, keep these ground-truth keywords in English"),
  not something a pure NMT model has any mechanism for. Deferred; FT
  proceeds with IndicTrans2 as planned.
- Found and reused prior working code on the archive branch
  (`indictrans2_translate.py`) -- `IndicTransToolkit` and a real `HF_TOKEN`
  were already present, saving setup time. Rebuilt as
  `translation/translate_indictrans2.py`: fixed the old script's device
  detection (only checked CUDA, would've silently run on CPU on this Mac)
  to also use MPS (Apple GPU) -- confirmed working ("running on mps").
  Verified via WebSearch that all 5 plan languages, including both Santali
  (sat_Olck) and Bodo (brx_Deva), are natively supported by IndicTrans2.
- Smoke-tested 5 examples first. Numbers/order all correct, but found a
  real fidelity issue: source "10 m/s^2" (acceleration) translated to
  Hindi lost the "^2", reading as a plain speed unit. Verified the source
  literally contains "m/s^2" (not a misread). Agreed with the user this
  needs its own automated checker later (analogous to the perturbation
  number-drift check, but for unit/exponent markers, not just numbers) --
  not yet built.
- Ran full batches: 200 Hindi + 200 Tamil = 400 rows in
  `data/translations/multiple_translations.jsonl`.
- **Correction**: earlier reports of "199 base queries" / "597 perturbation
  rows" were wrong -- caused by `wc -l` undercounting by 1 because
  `BFCL_v4_multiple.json` has no trailing newline after its last line.
  Verified properly (parsing actual JSON entries): 200 base queries, 600
  perturbation rows. The actual pipeline runs were never affected (JSONL
  parsing doesn't depend on trailing newlines) -- only the verbal reports
  to the user were wrong. Corrected in PROGRESS.md, LOG.md, and both
  affected READMEs.

**Set up Label Studio for human review, replacing a planned plain-CSV export.**
- User's call, and a better fit than CSV given the project's scale
  (multiple languages, recurring review rounds): purpose-built review UI,
  proper script rendering for non-Latin scripts, structured JSON export
  that fits the provenance-layer design, built-in multi-annotator support.
- Installed into `label_studio_env`, a separate venv from `bfcl_env` --
  NOT a redundant precaution: the first attempt (installing directly into
  `bfcl_env`) pulled in `numpy 2.4.6`, conflicting with BFCL's pinned
  `numpy==1.26.4` and risking silent breakage of the harness. Caught before
  causing damage (checked `bfcl_eval`/`ast_checker` imports still worked,
  but didn't trust that alone given numpy 2.x's real behavioral changes),
  uninstalled, restored the pin, moved the install to its own venv instead.
- First venv attempt used the `miniconda3` base Python (3.14) --
  `django-environ` (a Label Studio dependency) doesn't support 3.14 yet
  (`pkgutil.find_loader` removed in 3.12). Recreated the venv with Python
  3.11 (same version `bfcl_env` already uses successfully) -- worked.
- `label-studio --version` unexpectedly launched the full server and
  opened a browser (not just a version string) -- user signed up through
  it themselves at `localhost:8080`.
- Built the review flow per the user's exact design: source + target text
  shown, Correct/Incorrect choice; if Incorrect, a multi-select issue-type
  checklist (number/unit wrong, wrong word choice, grammar, meaning
  changed, missing/added content, script issue, not-a-valid-perturbation,
  other), a corrected-text box, and a notes box -- all conditionally shown
  only when Incorrect is picked, via Label Studio's `visibleWhen`.
- To set this up without requiring the user to click through the UI:
  pulled an API auth token directly from the local SQLite DB via Django
  shell (`manage.py shell`, `Token.objects.get_or_create`), rather than
  needing their account password. Stored in `.env` as
  `LABEL_STUDIO_API_TOKEN`.
- Hit a real auth error: "legacy token authentication has been disabled
  for this organization" -- this Label Studio version defaults new
  organizations to JWT-only auth. Fixed by flipping
  `org.jwt.legacy_api_tokens_enabled = True` directly on the existing
  organization via Django shell (simpler and more reliable than trying to
  set an env var that only applies at org-creation time and restart).
- Hit a wrong API endpoint (`/api/projects/{id}/tasks` -> 404); the
  correct one is `/api/tasks?project={id}`, response shaped as
  `{"tasks": [...]}` not a bare list. Fixed in
  `translation/setup_label_studio.py`.
- Ran successfully: created 3 projects (idempotent, safe to rerun as more
  languages/data are added) -- **PARA-SYNO Review (English)** (400 tasks),
  **Hindi Translation Review** (200 tasks), **Tamil Translation Review**
  (200 tasks).
- Not yet done: assigning specific verifiers to specific language
  projects (user's explicit requirement -- different people per language),
  and building the review-import script for when completed reviews come
  back (must land in a separate file per the provenance policy, never
  merged into the raw translation/perturbation data).

**Discussed review sampling depth.** For PARA/SYNO: agreed a 10% human
sample is defensible, given 0/400 automated number-drift flags from a
capable model and no claim in MLCL's own paper of 100% review either. For
translations: held off committing to a percentage until the
unit/exponent-marker checker (above) gives a real automated baseline,
given the one already-observed real issue (`m/s^2`).

**Discussed and dropped a custom-built review UI.** User initially
reacted to Label Studio's default UI as too generic/dated and asked about
a fully custom app. Walked through the real tradeoff: a custom tool isn't
a legitimacy problem for the paper (methodology matters, not tool choice),
but IS a real reliability risk (a hand-rolled persistence layer has more
chance of silently losing or corrupting real reviewer work than a mature,
tested tool, and reviewer time is expensive to redo unlike API cost).
Offered a middle path (custom frontend on Label Studio's backend) but user
decided to stay sober and keep Label Studio as-is, unmodified -- they
won't be doing the reviewing themselves, so visual polish matters less
than reliability.

**Built `translation/check_translation_fidelity.py`, then fixed it through
three rounds of false positives before trusting its output.** Initial run:
60/400 (15%) flagged -- suspiciously high next to the perturbation
checker's 0.2%. Investigated each pattern by hand rather than trusting the
raw flag count:
- `%` markers: false positive. "10%" -> "10 प्रतिशत" (correctly spelled
  out as the word "percent"), fully correct, not a drop. Removed `%` from
  the MARKERS list entirely.
- List-comma merging: false positive. Hindi/Tamil output often omits the
  space after a comma in a list ("3,4 और 5" for "3, 4, and 5") -- the
  NUMBER_PATTERN's `[\d,]*` (built to correctly parse thousands
  separators like "3,400") was merging separate list items into one wrong
  number. Fixed: a comma only counts as a grouping separator when followed
  by exactly 3 digits then a non-digit/end; otherwise the match is split
  back into separate numbers (not just truncated -- an earlier draft of
  this fix discarded the second half instead of recovering it, caught and
  corrected before running).
- Decimal-point-space: false positive. IndicTrans2's detokenizer inserts a
  space after some decimal points ("0.95" -> "0. 95", value unchanged).
  Fixed: NUMBER_PATTERN now tolerates one optional space after the decimal
  point; the cleanup step strips it before parsing. Documented as a known
  limitation (small over-merge risk on genuine sentence-boundary digits,
  low risk given this dataset is single-sentence queries).
- Identifier-glue guard too aggressive: false positive. The guard (built
  to stop "1004" being extracted from "B1004") was checking
  `.isalpha()`, which is Unicode-aware and also true for Devanagari/Tamil
  letters -- so a number written glued to a preceding Indic word with no
  space (normal, correct writing in these scripts, e.g. "और-25" =
  "and-25") was being wrongly skipped, producing a false "missing" number.
  Fixed: guard now requires the preceding character to be alpha AND ascii
  (Latin-only), which still catches "B1004" but no longer misfires on
  Devanagari/Tamil.
- All four fixes verified against synthetic test cases before rerunning on
  real data.

**Final, trusted result: 27/400 (6.8%) flagged**, down from the initial
60. Hand-verified 2 as genuinely real:
1. `^` (exponent) systematically dropped -- confirmed on 3 independent
   examples (`m/s^2`, `3x^2`, `m^3`), no compensating word ever appears.
2. A real value corruption on `multiple_106`: source `0.01` Coulombs,
   both the independently-generated Hindi AND Tamil translations produced
   `0.1` -- a 10x magnitude error, silent (no formatting trace, unlike the
   `^` case), confirmed real specifically because it recurred identically
   across two separate language generations.
The remaining ~25 flagged rows were NOT individually hand-verified
(diminishing returns) -- left for human review.

**Decided against building any auto-corrected candidates**, even for the
confirmed `^` pattern. Discussed a masking/re-translate approach, but the
user's call was simpler and safer: just surface the detector's exact
finding to the reviewer as an upfront warning (what was flagged, and why),
propose no fix at all, and let the human handle correction entirely. Cited
reasoning: avoids risking a repeat of the archived pilot's
`fix_number_matching.py` regression, where auto-substituting based on a
source/target mismatch caused more harm than it fixed.

**Rebuilt all three Label Studio projects with QA warnings included.**
Updated `translation/setup_label_studio.py`: added a `qa_warning` field to
every task (joined from the QA JSONL files by base_id +
perturbation_type [+ language for translations]), rendered as a yellow
warning banner above the source/target text via a new
`format_qa_warning()` function -- states exactly what the checker found in
plain language, proposes nothing. Added `delete_project_if_exists()` and a
`reset=True` path, since the original 3 projects (created before the
checker was fixed) needed to be fully replaced, not patched -- per the
user's explicit call to delete old and rebuild once the check was done.
Ran successfully: projects 1/2/3 deleted, recreated as 4/5/6 with the same
task counts (400/200/200). Spot-verified via the API that `multiple_106`
(hi) now carries the correct warning text end-to-end.

**User caught a real UX problem: clean rows showed a reassuring "No
issues detected" badge.** Risk: automation bias -- a checker-approved
badge on every clean row would train reviewers to trust it and skim
rather than read closely, defeating the point of human review. Fixed by
switching the field from a static-styled `View`+`Text` (which always
rendered *something*) to a `HyperText` field whose entire content --
including whether the warning box exists at all -- is generated in
Python. `format_qa_warning()` now returns an empty string for a clean
row (renders nothing) and a full styled HTML div only when there's an
actual flag. Rebuilt all three projects again (ids 7/8/9, replacing
4/5/6) -- safe to do, since no reviewer had submitted any work yet.
Spot-verified via the API: `multiple_2` (clean) -> `''`, `multiple_106`
(flagged) -> full warning HTML.

**User reported the empty-string fix broke the UI**: clean rows showed a
grey box stuck loading forever instead of nothing. Root cause (best
understanding, can't inspect the compiled frontend JS directly): the
`HyperText` field appears not to treat a bare empty string as "nothing to
render" -- likely hits a "waiting for content" state instead. Fixed by
never returning a literal `""`; `format_qa_warning()` now returns
`'<div style="display:none;"></div>'` for clean rows -- valid, non-empty
HTML that resolves instantly and takes up no visible space, sidestepping
whatever edge case empty-string triggered. Rebuilt all three projects
again (ids 10/11/12, replacing 7/8/9). Verified via the API that both the
empty-marker div and the real warning HTML are present correctly; actual
browser-rendering confirmation still pending from the user.

**User reported a second problem**: even `display:none` content still
left visible reserved space, shifting the real content (source/target
text) toward the middle of the screen -- suggesting Label Studio's own
wrapper around a HyperText field reserves layout space independent of
its inner content. Researched properly this time instead of guessing
again: fetched Label Studio's own documentation for the `View` tag and
confirmed `visibleWhen` supports exactly four modes
(`region-selected`/`choice-selected`/`no-region-selected`/`choice-
unselected`), all driven by an annotator's in-session action -- there is
no documented mechanism to hide an element based on task data. Also
checked the "predictions" pre-fill mechanism as a possible workaround
(pre-select a hidden Choices value at import time to drive
`visibleWhen`); Label Studio's own docs are ambiguous about whether a
prediction counts as "selected" on initial load without the reviewer
manually accepting it first, and this can't be resolved by reading docs
alone without a real browser to test in. Reported this honestly to the
user rather than attempting a third unverified guess.

**User separately questioned whether a composed plain-language warning
sentence (not just HTML) also violates data integrity** -- correctly
identified that a derived/formatted summary is still not the same as raw
structured data, even without markup. Clarified the actual distinction:
the canonical QA files (`*_qa.jsonl`) are and remain the clean,
structured, reusable dataset of record; Label Studio's own task store is
a separate, disposable, regenerated-from-source working copy that exists
only to drive the review UI, not a second copy of the dataset.

**User then gave the actual working solution directly**, cutting through
several rounds of failed attempts:
1. Accept HTML living in Label Studio's task data specifically (not the
   canonical files) -- confirmed with the user this is genuinely
   low-risk given the data flow above, conditional on one firm rule: the
   future review-import script must only extract the reviewer's own
   annotation output (their choice, corrected text, notes), never a raw
   dump of `task.data` -- noted explicitly so it isn't forgotten when
   that script gets built.
2. Move the warning box to appear AFTER the source/target text (not
   before), so real content is never pushed down by it.
3. Always render the same box, same shape/size, in both states --
   yellow and readable when flagged, white-on-white (present but
   invisible) when clean -- rather than trying to make it disappear
   entirely. This sidesteps the loading-state bug (content is never
   empty) and the layout-shift bug (size is always consistent) at the
   same time, without needing any of the unavailable data-driven
   visibility mechanisms.
Implemented in `format_qa_warning()` and `build_labeling_config()`,
rebuilt all three projects again (ids 13/14/15, replacing 10/11/12).
Verified via the API: `multiple_2` (clean) -> white box with `&nbsp;`,
`multiple_106` (flagged) -> yellow box with the real finding, both same
padding/border/margin shape. Actual browser confirmation still pending.

**User confirmed the fix works in the browser.**

**Added Gujarati** (user's request -- not one of the original 5 plan
languages, noted here for traceability). Added `gu: guj_Gujr` to
`translate_indictrans2.py`'s language table (confirmed supported by
AI4Bharat same as the others), smoke-tested 5 examples (same known
patterns as before -- correct number order, same `^2`-drop bug recurring
predictably, nothing new), ran the full 200. Re-ran
`check_translation_fidelity.py` across all 600 rows (hi+ta+gu): 41
flagged (6.8%), same rate as before, no new surprises. Added a Gujarati
project to `setup_label_studio.py` without touching the existing
Hindi/Tamil/PARA-SYNO projects (`reset=False` by default now that they're
correctly built) -- hit one bug along the way: `get_existing_task_keys`'s
pagination 404s on an exact-multiple-of-page-size task count (an empty
next page returns 404, not an empty list) -- fixed by treating 404 as
"no more pages."

**Added a static reviewer-guidelines panel to every project**, per the
user's request: the issue-type checklist only helps *after* a reviewer
has already decided something's wrong, it doesn't tell them what to
actively look for while reading. Added `TRANSLATION_GUIDELINES` (4
points: numbers/values preserved, meaning preserved, units/symbols/
exponents conveyed, natural word choice/grammar) and
`PERTURBATION_GUIDELINES` (same 4, plus 2 more specific to SYNO being a
word-for-word swap and PARA preserving exact meaning). Baked directly
into each project's `label_config` XML (not per-task data, since it's
identical on every page) as a static styled panel above the source text.
Required rebuilding all 4 projects (a label_config change is project-
wide, unlike adding new task data) -- ids 17/18/19/20. Verified via the
API that the guidelines HTML is present and correctly escaped in the
stored config.

**Tried Cloudflare Tunnel again per a suggestion from the user's friend
(via Gemini), given university firewall context.** Suggestion assumed
`--protocol http2` forces the connection onto port 443 (the port the
university's captive-portal network allows). Tested directly rather than
assuming either way: still failed, and the actual log line showed why --
`dial tcp 198.41.200.73:7844: i/o timeout` -- cloudflared's edge
connection uses port 7844 regardless of the `--protocol` flag; that flag
only changes the tunnel's data framing, not the port dialed. Also
confirmed `api.cloudflare.com:443` (regular HTTPS) reaches fine from this
network -- only the tunnel-specific edge servers are blocked, suggesting
a deliberate, targeted block on tunnel traffic rather than an accidental
port restriction. Concluded further tunnel attempts weren't worth it and
moved to real hosting.

**Chose Render (free web service) + Neon (free Postgres) for hosting,
after ruling out Vercel** (serverless-only, no persistent process or
filesystem -- fundamentally the wrong model for a stateful Django app
like Label Studio, not just a worse fit) **and after the user explicitly
ruled out any paid option.** Externalizing the database to Neon was the
key design choice: it means Render's known free-tier problem (ephemeral
disk wiped on restart) can't lose real data, since the data was never
going to live there -- confirmed this is architecturally sufficient
specifically because none of our tasks reference uploaded media files,
only structured text fields.

**Set up the Render deployment via its REST API** (base
`https://api.render.com/v1`, Bearer auth): fetched the workspace
`ownerId` first (`tea-d3p1gs3ipnbc739khblg`), confirmed
`heartexlabs/label-studio:latest` as the official Docker image (port
8080 by default) via WebSearch, created the web service (`srv-
da5tb0u417fc738kf490`, region `singapore` to match Neon's `ap-
southeast-1`), set env vars for the Postgres connection
(`DJANGO_DB=postgresql`, `POSTGRE_USER/PASSWORD/NAME/HOST/PORT` --
confirmed these exact names by reading Label Studio's own
`core/settings/base.py` + `label_studio.py` rather than guessing; also
confirmed no `DATABASE_URL`-style single-connection-string option exists,
so SSL isn't explicitly configured -- relying on psycopg2's default
`sslmode=prefer`, which should negotiate SSL successfully against Neon
without needing explicit config) plus `LABEL_STUDIO_HOST` (for correct
asset/link URLs) and `PORT`.

**Hit a real crash-restart loop on first deploy.** Diagnosed
systematically rather than guessing at a fix immediately:
1. First hypothesis: memory (Render free tier is 512MB). Checked
   Render's metrics API directly -- memory peaked at ~388MB across the
   observed window, under the limit. Ruled out.
2. Read the actual logs closely: `"Port scan timeout reached, no open
   ports detected"` appeared at 05:30:01, but the app didn't actually
   finish starting (Django's dev server logged as up) until 05:31:30 --
   90 seconds *after* Render had already given up and presumably queued
   a restart. The container briefly went live afterward, served a few
   real requests successfully, then restarted again ~4 seconds later.
3. Realized a self-inflicted contributing factor: triggered an extra
   manual redeploy via the API while the first auto-triggered deploy
   (from service creation) was likely still starting, causing at least
   one avoidable restart on top of the timeout issue.
4. Fix: stopped interfering entirely and just watched, on the reasoning
   that a fresh-database first-time migration is the slowest possible
   run, and subsequent attempts should be faster once the schema exists.
   Built a Monitor script polling deploy status, confirmed "live" state
   held stable for 60+ seconds (not just another brief flash) before
   treating it as actually fixed.

**Solved authentication for the Render instance without shell access.**
The local instance's token came from `manage.py shell` (`Token.objects.
get_or_create`), not available on a hosted container. Instead: signed up
a real account via `POST /user/signup/` (scraped the CSRF token from the
signup page's HTML first), confirmed Django's session-cookie auth (with
an `X-CSRFToken` header) works for both reads AND writes by testing a
throwaway probe project (created, confirmed, deleted). Added a `--target
{local,render}` flag to `setup_label_studio.py` and a `session(target)`
function that either uses the existing token flow (local) or logs in
with real credentials and sets the CSRF header as a session default
(render) -- no changes needed to any of the individual API call sites,
since `requests.Session` applies default headers automatically.

**Ran the full setup against Render**: all 4 projects recreated (ids
2/3/4/5 on the new instance), 1000 tasks total, verified matching the
local instance exactly (200 Hindi tasks, 14 flagged). Confirmed the
instance stable and publicly reachable at
https://indic-tool-calling-label-studio.onrender.com. Credentials stored
in `.env` (`RENDER_LS_EMAIL`/`RENDER_LS_PASSWORD`), along with
`RENDER_API_KEY` and `NEON_DATABASE_URL`.

**User tried logging in via a real browser and hit a second real bug**:
"CSRF verification failed. Request aborted." (403), screenshotted.
Diagnosed correctly on the first attempt this time: checked Label
Studio's own settings source and confirmed `CSRF_TRUSTED_ORIGINS`
defaults to an empty list, not auto-derived from `LABEL_STUDIO_HOST` --
and confirmed no `SECURE_PROXY_SSL_HEADER` handling exists either
(Render terminates TLS at its proxy, so without this Django may not
know the original request was HTTPS). My earlier curl-based login (used
while building `setup_label_studio.py`'s session auth) had worked
despite this, because it never sent an `Origin` header -- only a real
browser triggers Django's stricter Origin-based CSRF check. Reproduced
the exact failure with curl by adding an `Origin` header to confirm the
diagnosis before fixing anything.
Fix: added `CSRF_TRUSTED_ORIGINS=https://indic-tool-calling-label-studio.onrender.com`
via the Render env-vars API. Learned from the earlier crash-loop episode
that env var changes don't restart the running process by themselves --
confirmed this directly (repeated the Origin-header curl test right after
setting the var, still failed) before concluding a redeploy was actually
needed, rather than assuming either way. Triggered exactly one redeploy
(nothing else was mid-deploy this time, so no double-deploy risk),
watched it reach a stable live state the same way as before, then
re-tested the Origin-header login: 302 (success), no CSRF error.
Confirmed all 4 projects and their tasks survived the redeploy completely
unaffected -- the first real, practical validation that externalizing
the database to Neon actually protects data through a real restart, not
just a theoretical argument.

**Designed the two-reviewer Cycle 1 / Cycle 2 methodology** (extensive
back-and-forth, several real corrections along the way -- see full
detail in the conversation; summarized concisely in PROGRESS.md under
"Review methodology" to avoid duplicating it here). Key corrections made
during design, not just the final answer:
- Verified (didn't assume) that Label Studio Community edition has no
  per-project access restriction -- confirmed via research that any
  signed-up user can see every project. Accepted as a trust-based
  tradeoff rather than a blocker.
- Verified (didn't assume) that Label Studio doesn't cleanly hide one
  annotator's submitted answer from another within a shared project when
  overlap is used -- confirmed via a real reported concern on Label
  Studio's own community forum. This is *why* the two-separate-project-
  copies-per-reviewer design exists at all, not a stylistic choice.
- User caught a real gap in my first Cycle 2 design: a binary choice
  (original vs. other's fix; A's version vs. B's version) can't produce
  an answer that's neither -- added a third "neither, write a new final
  version" option to both conflict-resolution flows after being asked
  directly "are you sure this will be a clean merge" and actually
  checking rather than reassuring.
- User specified the bucket-2 "exact match" rule precisely: character-
  for-character, only trailing whitespace ignored, no other
  normalization -- explicitly rejecting fuzzy matching given how many
  false positives fuzzy/lenient matching has already caused this session
  (comma-merge, decimal-space, identifier-glue bugs).

**Created named per-reviewer projects, replacing the generic ones.**
Roster: Rohan + Dhayanidhi (Tamil, two independent full copies each --
the two-reviewer design above), Dhruv Kunvarani (Gujarati, one), Jayant
Kapoor (Hindi, one). Extended `setup_translation_review()` with an
optional `reviewer_name` parameter -- when given, produces a project
titled "{Language} Translation Review — {name}" instead of the generic
title, so each reviewer's project is unambiguous. Deleted the old
generic-named Hindi/Tamil/Gujarati projects on the Render instance and
recreated as named ones (ids 6/7/8/9); left PARA-SYNO (id 2) untouched,
no reviewer named for it in this request. Verified final project list
via the API matches exactly what was requested.

## 2026-09-07

**Checked completed Cycle 1 Tamil review files and built Cycle 2 for
Tamil**, following the methodology designed 2026-08-24 above. Reviewers
switched from Label Studio to Google Sheets .xlsx templates between
these two log entries (Render's free tier could not support real
simultaneous multi-reviewer load -- Render and Neon were subsequently
torn down); this is the first time the Sheets-based Cycle 1 -> Cycle 2
pipeline has actually been run on real reviewer data.

Read the two downloaded Cycle 1 files (`Tamil_review_Dhayanidhi.xlsx`,
`Tamil_review_Rohan.xlsx`, in `reviewer annotated file downloaded from
google sheets/`) and verified before doing anything else: both match
the expected template schema (16 columns), both reviewers completed all
200/200 rows with no missing or duplicate `base_id`s and no empty
Correctness values, and English Source / pre-review Translation text is
identical between the two files for every row (confirms neither drifted
from the canonical template). Every "Incorrect" row in both files has a
non-empty Corrected version and at least one issue-type checkbox
checked. One data anomaly found and accepted rather than silently
patched: `multiple_1` -- Rohan marked Correctness = Correct but also
checked "Script/Formatting" and filled in a Corrected version fixing a
colon-rendering glitch. Left as-is; it still classifies correctly into
bucket 3 off the Correctness field, and Rohan will see Dhayanidhi's fix
for it like any other bucket-3 item during Cycle 2.

Classified all 200 items with the strict exact-match rule (only
trailing whitespace trimmed, no fuzzy matching): bucket 1 (both
Correct) 126, bucket 2 (both Incorrect, identical fix) 58 -- both
resolved, no Cycle 2 needed. Bucket 3 (asymmetric) 8 items, all eight
with Dhayanidhi saying Incorrect and Rohan saying Correct, so Rohan is
the adjudicator for all eight per the "whoever said Correct" rule --
not a coincidence to randomize, just how the rule resolved here. Bucket
4 (both Incorrect, different fixes) 8 items, split 4/4 between the two
reviewers by a fixed-seed (42) balanced random assignment, with A/B
version-order per item also randomized by the same seeded RNG so the
adjudicator sees blinded "Version A"/"Version B" labels, not reviewer
names.

Wrote `translation/generate_cycle2_tamil.py` to do this end to end:
loads both raw Cycle 1 files read-only (never modified), classifies,
assigns bucket-4 adjudicators/blinding, and writes two new per-
adjudicator Cycle 2 .xlsx files (`data/review_sheets/cycle2/
Tamil_Cycle2_Rohan.xlsx` -- 8 bucket-3 rows + his 4 bucket-4 rows in
separate tabs; `Tamil_Cycle2_Dhayanidhi.xlsx` -- her 4 bucket-4 rows).
Same styling/dropdown conventions as `generate_review_sheets.py`
(readonly fill, header fill, wrap text, list-based data validation).
Decision dropdowns: bucket 3 tab = "Original stands / Accept fix /
Neither - write new"; bucket 4 tab = "Version A / Version B / Neither -
write new" (the third "neither" option in both, per the 2026-08-24 gap
fix). Verified after generation: correct row counts per tab, dropdown
data validation present and scoped to the right ranges, readonly fills
applied to context columns only, and blinding actually holds (checked
that Dhayanidhi's own fix shows correctly as Version A/B on her own
sheet without her name attached).

Also wrote the classification and the bucket-4 assignment as their own
derived files, separate from the raw reviewer files, per the data
provenance policy: `data/reviews/tamil_cycle1_classification.json`
(bucket per base_id, matching rule used, source file paths) and
`data/reviews/tamil_cycle2_bucket4_assignment.json` (adjudicator +
version-A/B authorship per bucket-4 item -- kept out of the Sheets the
reviewers see, needed later to interpret their Cycle 2 decisions).

Not yet done: uploading the two new .xlsx files to Google Sheets
(same manual upload/rename step as Cycle 1), and the same Cycle 1 ->
Cycle 2 pass for Hindi (Jayant Kapoor, Anshul) and PARA/SYNO (Jayant
Kapoor, Anshul) once each pair finishes Cycle 1 -- only Tamil was
requested this round.

**Checked completed Tamil Cycle 2 files and resolved the final Tamil
translation set.** Both reviewers returned their Cycle 2 adjudication
workbooks (`Tamil_review_cycle_2_Rohan.xlsx` -- Bucket 3 + Bucket 4 tabs
added onto a duplicate of his Cycle 1 sheet; `Tamil_review_cycle_2_
Dhayanidhi.xlsx` -- Bucket 4 tab only). Validated before trusting either:
all 20 expected items present in exactly the sheet the fixed-seed
assignment predicted (no id landed in the wrong reviewer's file), every
Decision a valid option for its tab, and the one "Neither - write new"
row (`multiple_37`) had a Corrected version actually filled in.

Wrote `translation/resolve_cycle2_tamil.py`: re-derives the same 4-bucket
classification from the raw Cycle 1 files, cross-checks the Cycle 2
decisions against the saved `tamil_cycle2_bucket4_assignment.json`
(catches an id showing up in the wrong adjudicator's sheet, an invalid
decision value, or a missing write-new correction -- would abort rather
than silently resolve), then merges Cycle 1 (buckets 1/2, already
resolved) with Cycle 2 (buckets 3/4) into one final per-item text. Ran
clean, no validation errors. Output: `data/reviews/tamil_final_
resolved.jsonl` (200 rows, one per base_id, each carrying both
reviewers' Cycle 1 verdicts, bucket, and -- for bucket 3/4 -- the
adjudicator and decision that produced the final text) and `data/
reviews/tamil_cycle2_decisions.json` (raw Cycle 2 decision rows, kept as
their own snapshot layer). Raw Cycle 1 and Cycle 2 reviewer files
untouched throughout, per the provenance policy.

**Recorded reviewer behavior during Cycle 2 adjudication**, per user
request -- not just the resolved text but how the two reviewers actually
behaved when confronted with disagreement. Written up in `data/reviews/
tamil_cycle2_reviewer_behavior.md`: bucket 3 (Rohan reversed his own
"Correct" call 5/8 times, held it 3/8); bucket 4 (adjudicators picked
the *other* reviewer's blinded fix 6/7 times when choosing A/B, their
own only once; the one "write new" case genuinely synthesized both
proposed fixes rather than picking one). Reading: no evidence of
self-favoring or rubber-stamping bias in either reviewer, in either
direction -- both signals lean toward genuine reconsideration. Small
sample (n=8 and n=7), flagged as descriptive, not a statistically
powered claim; worth rechecking once Hindi/PARA-SYNO Cycle 2 data
exists.

**Checked completed Hindi Cycle 1 files (Jayant Kapoor, Anshul Gupta)
and built Cycle 2 for Hindi.** Structural audit clean same as Tamil
(200/200 rows each, no missing/duplicate ids, identical source text
between files). Found something the Tamil audit's one-off anomaly
didn't prepare for: Anshul marked **every single row "Correct"**
(200/200 in the Correctness dropdown), but 10 of those rows also had an
issue checkbox ticked, a Corrected version filled in, and (for most) a
real linguistic note explaining an actual problem -- not a one-off, a
systematic pattern. Reported this to the user with the concrete stakes
before doing anything else: under a literal reading of the Correctness
field, 4 of the 10 (`multiple_122, 125, 134, 170`) would land in bucket
1 (both Correct -> resolved, no Cycle 2) and Anshul's actual catches
(a dropped "felony" qualifier, a dropped "assume equal variance", a
grammatical meaning-flip, etc.) would be silently lost; the other 6
overlap with items Jayant already flagged Incorrect so they'd land in
bucket 3 regardless, just with less useful classification.

User confirmed the root cause directly rather than leaving it to
guesswork: Anshul misread the Correctness field as "is my correction
below correct" rather than "is the original translation correct" --
so any row where he wrote a Corrected version means he considered the
*original* Incorrect, regardless of what the dropdown says. Applied
this as a targeted, documented reinterpretation -- Anshul-only, not a
general rule -- for bucket classification purposes: a non-empty
Corrected version overrides his Correctness cell to Incorrect. His raw
Correctness column is untouched in the source file and in loaded data;
the override is recorded explicitly (`anshul_correctness_reinterpreted:
true` + a full explanatory note) in the classification output so it's
traceable, not a silent correction.

Wrote `translation/generate_cycle2_hindi.py` (same structure as the
Tamil version, with the reinterpretation as an explicit, commented
special case). Reclassifying with the override changed the picture
substantially from a literal read: bucket 1 (both Correct) 186, bucket
2 (both Incorrect, identical fix) 1 (`multiple_150`), bucket 3
(asymmetric) 8 -- split 4/4 between Jayant and Anshul as adjudicator
(not a coincidence of the random assignment; bucket 3's adjudicator
rule is deterministic per item), bucket 4 (different fixes) 5, split
3/2 between Jayant/Anshul by the same fixed-seed (42) balanced random
assignment used for Tamil. Wrote `data/review_sheets/cycle2/
Hindi_Cycle2_Jayant.xlsx` (4 bucket-3 + 3 bucket-4) and `Hindi_Cycle2_
Anshul.xlsx` (4 bucket-3 + 2 bucket-4), not yet uploaded to Google
Sheets. Classification + bucket-4 assignment saved to `data/reviews/
hindi_cycle1_classification.json` and `hindi_cycle2_bucket4_assignment.
json`. Verified row assignment in both generated sheets matches the
computed bucket-3/bucket-4-by-adjudicator lists exactly.

## 2026-09-16

**Checked completed English PARA/SYNO Cycle 1 files (Jayant Kapoor,
Anshul Gupta) and built Cycle 2.** Structural audit hit a new, real bug on
the first pass: naive loading reported only 201 rows per reviewer (should
be 400) with almost every row showing as PARA and only one SYNO --
`build_perturbation_sheet` (generate_review_sheets.py) merges the
base_id and English Source cells across each PARA+SYNO pair, and
openpyxl only returns a value on the top-left cell of a merged range, so
every SYNO row's base_id/English Source read as None and collapsed onto
a single dict key. Fixed by forward-filling those two columns from the
last non-empty value seen; re-verified afterward (400/400 rows, keys
match between reviewers, source text identical, no empty Correctness).

Classified with the composite (base_id, perturbation_type) key (PARA and
SYNO reviewed independently per base_id): bucket 1 (both Correct) 392,
bucket 2 (identical fix) 1, bucket 3 (asymmetric) 6, bucket 4 (different
fixes) 1. Found a new kind of anomaly, not seen in Tamil/Hindi: two items
where a reviewer marked "Incorrect" with literally nothing else filled in
(no fix, no issue-type checkbox, no notes) -- `multiple_3` (PARA, Jayant)
and `multiple_72` (SYNO, Anshul's side of a bucket-4 pair). Reported to
the user with a concrete proposal before writing anything; confirmed:
`multiple_3` still gets a Cycle 2 row but with only two decision options
(no "Accept fix", nothing to accept) -- "Original stands" / "Neither -
write new"; `multiple_72` skips Cycle 2 entirely and is auto-resolved to
Jayant's fix directly, since Anshul's blank side isn't a competing
alternative to weigh against it, just an omission.

Wrote `translation/generate_cycle2_parasyno.py`. Per-row decision-list
support added to the sheet styling (a single row can get a different
dropdown than the rest of its column) specifically for the multiple_3
case. Wrote `data/review_sheets/cycle2/ParaSyno_Cycle2_Jayant.xlsx` (3
bucket-3 items) and `ParaSyno_Cycle2_Anshul.xlsx` (3 bucket-3 items,
including the 2-option row), not yet uploaded to Google Sheets.
Classification + the auto-resolved bucket-4 item saved to `data/reviews/
parasyno_cycle1_classification.json`. Verified after generation: correct
row assignment per adjudicator, and the multiple_3 row's dropdown is
genuinely 2-option while every other row stayed 3-option.
