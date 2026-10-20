# Progress

*Living status doc. High-level: where the project stands right now, what's
done, what's blocked, what's next. For a detailed chronological record of
every action taken, see `LOG.md`.*

---

## Current phase

*(Updated 2026-09-29.)* Past Exp 0. Two parts are finished:
- **Hindi and Tamil translations:** gold-reviewed for the NO condition.
- **English PARA/SYNO:** gold-reviewed.

Two model sets have been run:
- **14 open-weights models** across all 5 conditions (EN / HI / TA / PARA
  / SYNO).
- **8 OpenRouter/Sarvam models** on EN / TA only.

Four things are pending:
- Gujarati Cycle 2.
- Review of the Indic PARA/SYNO translations.
- Llama-3.3-70B.
- PAR and Romanization (not started). The language scope is
  final: EN + HI/GU/TA (2026-09-29).

The Exp 0 model table below is historical: it's from before the
OpenRouter route existed.

## Model readiness (Exp 0)

| Model | Status | Notes |
|---|---|---|
| Qwen3-8B (local, via Ollama) | ✅ Smoke test passed | `qwen3-8b-ollama-FC` registered, running against Ollama (`localhost:11434/v1`). 12/12 `multiple`-category schemas generated valid, BFCL-parseable tool calls; 11/12 (91.67%) also correct. The 1 failure was a genuine model error ("Wrong number of functions"), not a mechanics/parsing failure -- pipeline confirmed working end-to-end (generate + evaluate). First model to clear Exp 0. |
| Gemini 2.5 Flash | ❌ Not actually ready | Correction: `GOOGLE_API_KEY` in `.env` is empty. Handler exists, key does not. |
| DeepSeek V3.2 | ❌ Not actually ready | Correction: `DEEPSEEK_API_KEY` in `.env` is a literal placeholder (`sk-XXXXXX`), not a real key. |
| Qwen3 (cloud) | ❌ Not actually ready | Correction: `QWEN_API_KEY` in `.env` is a literal placeholder (`sk-XXXXXX`), not a real key. |
| GPT-5 | ⚠️ Needs verification | No plain "GPT-5" in BFCL's list, only gpt-5.2/mini/nano. Existing entry's model-name format looks tuned for direct OpenAI API, not OpenRouter -- needs an empirical check or a new OpenRouter-routed registry entry. |
| Llama | ⚠️ Needs rerouting | BFCL's built-in `LlamaHandler` expects local GPU serving (impractical here). Plan: register a new entry via OpenRouter instead, same pattern as the pilot's gpt-4o-mini-FC. |
| Sarvam-105B / 30B / M | ❌ Blocked | Not in BFCL at all -- no handler, no API key in `.env`. Needs: an API key from Sarvam's platform (user to obtain), and confirmation of whether its API is OpenAI-compatible (no new code needed) or bespoke (new handler needed). |

## Repo state

- `main` branch: clean project structure for the 5-language/8-model project.
- `archive/pilot-hindi-tamil-simple-python` branch: full prior pilot (Hindi/Tamil, simple_python, gpt-4o-mini, MLCL PT/PRE/POST replication) -- preserved, not deleted.
- Both pushed to `github.com/Bhuvan-Arora-1313/Indic-tool-calling-agentic-ai`.

## Perturbation data (PARA/SYNO)

- Generated for all 200 base queries in `bfcl_eval/data/BFCL_v4_multiple.json` (the full category -- confirmed this is genuinely all of it, not a subset; MLCL's own paper reports using the same full subset with no further downsampling). Note: an earlier report of "199" was a `wc -l` miscount (the file has no trailing newline after its last entry) -- corrected 2026-08-24, the actual pipeline runs were never affected since JSONL parsing doesn't depend on trailing newlines.
- Model: `google/gemini-3.7-flash` via OpenRouter. Prompts verbatim from MLCL (arXiv 2601.05366) Appendix A.8 (PARA) / A.9 (SYNO, incl. the worked few-shot example).
- Script: `translation/generate_perturbations.py`. Idempotent (safe to re-run/resume).
- Output: `data/perturbations/en_multiple_perturbations.jsonl` -- 600 rows (200 NO + 200 PARA + 200 SYNO). Raw and immutable per the data provenance policy above.
- QA: `translation/check_perturbation_number_drift.py` (order-independent number-set check, source vs. perturbed text). Result: **0 genuine issues** across 400 PARA/SYNO rows. 1 row flagged (`multiple_64`, PARA) turned out to be a checker false positive (source text has a formatting quirk, "June01" with no space, that the identifier-glue guard treats differently than the paraphrase's correctly-spaced "June 01") -- investigated and confirmed benign, documented rather than silently dismissed.
- Actual cost: **$0.4734** (400 calls, 57,280 input / 241,018 output tokens). Notably higher than the pre-run estimate (~$0.06-0.11) -- output token usage was ~6x the estimate, likely internal reasoning tokens billed as completion tokens. Still trivial in absolute terms.

## Translation data (FT via IndicTrans2)

- FT (fully translated) condition only -- PAR deferred (see Open decisions below).
- Model: `ai4bharat/indictrans2-en-indic-dist-200M`, run locally (Apple GPU / MPS on this Mac). Script: `translation/translate_indictrans2.py`. Idempotent.
- Hindi and Tamil done for the `NO` (unperturbed) English source: 200 rows each, 400 total, in `data/translations/multiple_translations.jsonl`.
- All 5 target languages confirmed supported by IndicTrans2 (verified via AI4Bharat's language list) -- including both Santali (sat_Olck) and Bodo (brx_Deva), so no coverage gap whichever the plan ultimately picks.
- Fidelity check built and run: `translation/check_translation_fidelity.py` (number-set drift + unit/exponent marker drift). Went through 3 rounds of fixing checker false positives (see LOG.md 2026-08-24) before trusting the numbers: `%` spelled out as a word is not a bug, list items merging across a no-space comma in Indic script is a checker bug (fixed), decimal points followed by a stray space are a checker bug (fixed), and the identifier-glue guard was wrongly skipping numbers glued to Devanagari/Tamil words (fixed -- now Latin-letter-only).
- **Final result after fixes: 27/400 (6.8%) flagged.** 2 confirmed real via hand-verification: (a) `^` (exponent) systematically dropped by IndicTrans2 (`m/s^2`, `3x^2`, `m^3` all lose it, no compensating word), (b) a genuine value corruption on `multiple_106`: source `0.01` -> both Hindi AND Tamil independently produced `0.1` (10x magnitude error). The remaining ~25 flagged rows are NOT individually hand-verified -- left for human review rather than guessed at further.
- Decision (user's call): do not build auto-corrected candidates at all, not even for the confirmed `^` pattern. Instead, surface the QA detector's exact finding to the reviewer as an upfront warning banner, and let them handle correction entirely -- avoids repeating the archived pilot's `fix_number_matching.py` regression (auto-substituting based on mismatches caused more harm than it fixed).

## Human review (Label Studio)

- Runs locally in its own venv (`label_studio_env`, separate from `bfcl_env`) at `http://localhost:8080` -- kept isolated deliberately after an initial install into `bfcl_env` caused a real numpy version conflict with BFCL's own pinned dependencies (reverted cleanly, no lasting damage; see LOG.md 2026-08-24).
- Legacy API token auth had to be manually enabled on the local organization (disabled by default in this version) to allow scripted project/task creation -- token stored in `.env` as `LABEL_STUDIO_API_TOKEN`.
- Review flow (user's design): reviewer sees source + target text, marks Correct/Incorrect. If Incorrect: a multi-select issue-type checklist, a corrected-text box, and a notes box appear.
- Setup script: `translation/setup_label_studio.py` (idempotent for adding new data; pass `reset=True` per-project to delete and fully rebuild, used once already after the fidelity checker was fixed).
- Every task now includes a `qa_warning_html` field, rendered via `HyperText` as an upfront yellow banner above the source/target text -- a plain-language statement of exactly what the automated checker found for that item. Deliberately does NOT propose a correction, per the user's explicit decision -- just warns the reviewer where to look closely, correction is entirely theirs.
- Corrected twice more (both user's catches): (1) a reassuring "No issues detected" badge on clean rows risked automation bias -- tried making it render nothing instead, which (2) caused a real bug: an empty HyperText value got stuck in a perpetual loading state in the UI. Final, working design (user's own call): the box always renders, same shape/size whether flagged or not, positioned below the source/target text (not above, so it doesn't push real content down) -- yellow and readable when flagged, white-on-white (present but invisible) when clean. Explicitly accepted as living only in Label Studio's disposable task store, never in the canonical `data/*.jsonl` files -- on the condition that the future review-import script only pulls the reviewer's own annotation output, never a raw dump of task.data (which would carry this HTML).
- Added a static "Reviewer guidelines" panel to every project (baked into the label_config itself, not per-task data -- it's identical on every page) telling reviewers what to actively check for (numbers/values preserved, meaning preserved, units/symbols/exponents conveyed, natural word choice/grammar; PARA/SYNO project also gets two extra points specific to those perturbation types).
- Added Gujarati (user's request, not one of the original 5 plan languages -- noted for traceability) -- translated via the same IndicTrans2 pipeline, 200 rows, checked for fidelity alongside Hindi/Tamil (600 rows total checked, same ~6.8% flag rate, no new surprises).
- Four projects live locally (ids 17/18/19/20): **PARA-SYNO Review (English)** (400 tasks), **Hindi Translation Review** (200 tasks), **Tamil Translation Review** (200 tasks), **Gujarati Translation Review** (200 tasks). Superseded by the Render deployment below -- local instance can be shut down once verifiers are confirmed working against the hosted one.

## Hosted deployment (Render + Neon)

- **Public URL: https://indic-tool-calling-label-studio.onrender.com** -- reachable from anywhere, no tunnel/VPN needed. Deployed after a university-network firewall made Cloudflare Tunnel unworkable (blocked both QUIC and the HTTP2/443 fallback -- see LOG.md).
- Architecture: Render free web service running `heartexlabs/label-studio:latest` (Docker), database externalized to a free Neon Postgres instance (`DJANGO_DB=postgresql` + `POSTGRE_*` env vars) specifically so Render's free-tier ephemeral disk never holds real data -- a restart can't wipe reviewer work.
- Hit a real crash-restart loop on first deploy: the container took longer to finish its first-time DB migration + startup than Render's port-scan timeout allows, so Render kept concluding the deploy failed and restarting it before it ever finished booting. Resolved by leaving it alone (no more manual redeploys) until a startup attempt completed within the timeout window -- confirmed via Render's metrics API that memory (peaked ~388MB) was NOT the actual cause, despite that being the first hypothesis.
- All 4 projects rebuilt on this instance via `setup_label_studio.py --target render` (added session+CSRF login as an alternative to token auth, since there's no shell/manage.py access on Render to pull a legacy token the way the local instance used) -- same 1000 tasks, verified matching (200 Hindi tasks, 14 flagged, identical to local).
- Login: bhuvanaro123@gmail.com (credentials in `.env` as `RENDER_LS_EMAIL`/`RENDER_LS_PASSWORD`).
- Fixed a second real bug after initial deployment: browser login failed with "CSRF verification failed" (403) -- Label Studio doesn't auto-derive `CSRF_TRUSTED_ORIGINS` from `LABEL_STUDIO_HOST`, needed setting explicitly. Added the env var, redeployed, verified fixed with a browser-equivalent request (Origin header included, which is what actually triggers Django's stricter check -- my original curl-based setup script login had avoided tripping this by not sending an Origin header, so it looked fine until a real browser tried it). Confirmed all 4 projects and their data survived the redeploy untouched -- validates the external-Postgres design actually works as intended under a real restart, not just in theory.
- Reviewer roster (updated 2026-08-25): **Rohan** and **Dhayanidhi** (Tamil, two independent full copies each -- two-reviewer Cycle 1/Cycle 2 design, see "Review methodology" below), **Dhruv Kunvarani** and **Samarth** (Gujarati, now also two-reviewer), **Jayant Kapoor** (Hindi, still single-reviewer). Old generic-named language projects deleted and replaced with per-reviewer named ones; PARA-SYNO left untouched, no reviewer named for it yet. More reviewers/languages can be added later without disturbing existing projects -- verified repeatedly (Gujarati's second reviewer added 2026-08-25 without touching Rohan/Dhayanidhi/Dhruv/Jayant's projects at all).
- Fixed a real self-inflicted bug while adding Samarth: `setup_label_studio.py` had `setup_perturbation_review(s, reset=True)` left over from the 2026-08-24 combined-task rebuild -- caused PARA-SYNO to be needlessly deleted and recreated on every run since, including this one. Harmless so far (no reviewer assigned to it yet, so nothing to lose), but changed to `reset=False` now so a future run can't destroy real progress on it by accident.
- **Jayant Kapoor now also reviews PARA/SYNO (English)**, separate from his Hindi assignment (2026-08-25). Added `reviewer_name` support to `setup_perturbation_review()` (previously only the language function had it), replaced the generic unassigned "PARA-SYNO Review (English)" project with "PARA-SYNO Review (English) — Jayant Kapoor" (id 13, 200 tasks). Hit a transient connection drop mid-import on the first attempt (Render/network blip, not a code bug) -- project was created but ended up with 0 tasks; retried the same idempotent script and it completed cleanly the second time.
- **Anshul added as second reviewer for both Hindi and PARA/SYNO** (2026-08-25) -- Hindi and PARA/SYNO are now both two-reviewer (same design as Tamil/Gujarati). Generalized `PARA_SYNO_REVIEWERS` into a list (was a single hardcoded name) to match the existing per-language pattern. Final roster verified directly via the API: **8 projects total** (ids 6/7/8/9/12/13/14/15), each with 200 tasks, all pre-existing projects confirmed untouched ("already exists / nothing new to import" for every one of them).
- Current full roster: Tamil (Rohan, Dhayanidhi), Gujarati (Dhruv Kunvarani, Samarth), Hindi (Jayant Kapoor, Anshul), PARA/SYNO English (Jayant Kapoor, Anshul).

## Pivot: Google Sheets instead of Label Studio (2026-08-25)

Measured a real concurrency ceiling on Render's free tier (0.1 CPU): 8
simultaneous authenticated requests took 12.7-14.6s each. Since more
worker processes can't exceed a fixed 0.1-core total, this doesn't fix
with tuning -- it needs a paid tier or a different platform for genuine
8-10-person simultaneous use, which the user has as a real requirement.
Switched to Google Sheets instead (user's proposal) -- also solves the
per-reviewer access-isolation problem better than Label Studio's
Community edition did (real per-sheet access control via Google's own
sharing), with zero hosting/concurrency concerns at Google's scale.

- No direct Google Sheets access this session (only Gmail/Calendar
  connected; Drive is available but unauthorized, and wouldn't give
  cell-level control anyway) -- so the workflow is: generate `.xlsx`
  templates locally, user uploads to Google Sheets, duplicates per
  reviewer, renames.
- Built `translation/generate_review_sheets.py`: reuses all the existing
  translation/perturbation/QA data (same source files as the Label
  Studio setup). 4 templates in `data/review_sheets/`: Hindi (200 rows),
  Tamil (200), Gujarati (200), PARA-SYNO (400 -- 2 rows per question,
  PARA+SYNO, shared source/base_id merged across the pair).
- Read-only columns (source, text-under-review, automated-check)
  visually distinguished from editable ones; flagged rows highlighted,
  clean rows left blank (same silence-for-clean principle as Label
  Studio's qa_warning design -- a badge on every row risks automation
  bias). Separate Instructions tab with the review guidelines.
- **Issue type is 9 separate TRUE/FALSE dropdown columns**, one per
  category (Number/Value, Wrong Word/Mistranslation, Grammar, Meaning
  Changed, Missing Content, Added Content, Script/Formatting, Invalid
  Swap, Other) -- not a single free-text or single-select field.
  User caught that free text (the initial version) would lose the
  "select all that apply" capability the original Label Studio design
  had, and made downstream aggregation harder (inconsistent phrasing
  across reviewers vs. clean structured categories).
- Known gap the .xlsx format can't carry: Google Sheets' own "Protect
  ranges" (locking the read-only columns) is Sheets-native, not an Excel
  feature -- needs to be set up manually after each upload.
- **Decided**: Google Sheets fully replaces Label Studio for review.
  Full teardown completed (2026-08-25): all 8 Label Studio projects
  deleted (confirmed 0 remaining), Render service (srv-
  da5tb0u417fc738kf490) fully deleted (confirmed 404 on lookup, not just
  suspended), Neon database wiped (82 tables dropped, schema recreated
  empty -- only had connection-string access, not a Neon account API key,
  so the Neon *project* itself still exists on their free tier and needs
  a manual delete via Neon's console if the user wants it fully gone,
  not just empty). `RENDER_API_KEY`/`RENDER_LS_*`/`NEON_DATABASE_URL` in
  `.env` are now dead credentials, harmless to leave but no longer
  functional. Import script to pull completed Sheets reviews back into
  the canonical data files not yet built.
- Each reviewer needs their own Label Studio account (self-signup at the URL above) and will see all projects technically (Community edition has no per-project access restriction -- verified, not a config gap), but is instructed to only work their own named project. Accepted tradeoff, not yet solved technically. Verified separately: new self-signups automatically join the same organization with full visibility (no invite step needed) -- confirmed with a real throwaway signup, not assumed.
- Published a shareable sign-in guide for reviewers (Artifact, link in conversation) -- steps + a name-to-project lookup table, meant to be sent directly rather than screenshotted.
- **PARA-SYNO project restructured** (2026-08-24): was 400 separate tasks (one per (question, PARA-or-SYNO)); reviewer had no way to tell which type they were looking at from the UI, a real gap. Rebuilt as 200 combined tasks -- English source shown once, PARA and SYNO shown together below it, each independently labeled and independently judged (separate Correct/Incorrect, issue checklist, correction, notes per type -- `correctness_para`/`correctness_syno` etc. as distinct control names, not merged). Confirmed this stays fully compatible with the downstream pipeline: the two judgments remain separable in the stored annotation, decomposing back into the same two-independent-records shape needed later (PARA and SYNO are separate experimental conditions). No reviewer named for this project yet.

## Review methodology (Cycle 1 / Cycle 2, for languages with 2 reviewers)

Full design written up and shared with the user's mentor for review (2026-08-24) -- summary:
- **Cycle 1**: each reviewer independently reviews their *entire* assigned dataset (their own separate project copy, so neither sees the other's answers), marking each item Correct or Incorrect+their own fix.
- **Classification into 4 buckets** once both finish: (1) both Correct -- resolved; (2) both Incorrect with an *exact* matching fix (strict, only trailing whitespace ignored) -- resolved; (3) asymmetric (one Correct, one Incorrect+fix) -- conflict; (4) both Incorrect with *different* fixes -- conflict.
- **Cycle 2** (conflicts only, starts only once both reviewers fully finish Cycle 1): bucket 3's adjudicator is whoever said Correct, shown the other's proposed fix, chooses original/accept fix/neither-write-new. Bucket 4's adjudicator is randomly chosen but balanced ~50/50 across all bucket-4 items (fixed seed for reproducibility), shown both proposed fixes, chooses A/B/neither-write-new. The third "neither" option in both cases was added deliberately after checking for and finding a real gap (binary choice can't produce an answer that's neither of the two flawed options).
- **Tamil Cycle 1 -> Cycle 2 pipeline built and run on real data (2026-09-07)**: `translation/generate_cycle2_tamil.py`. Both Tamil reviewers' downloaded Cycle 1 files (`Tamil_review_Dhayanidhi.xlsx`, `Tamil_review_Rohan.xlsx`) verified complete (200/200 rows each, no missing/duplicate ids, no empty Correctness, matching template schema, identical source text between the two files) before classifying. Results: bucket 1 (both Correct) 126, bucket 2 (both Incorrect, identical fix) 58 -- both resolved, no Cycle 2 needed; bucket 3 (asymmetric) 8, all eight adjudicated by Rohan (he's the one who said Correct in every one of the 8); bucket 4 (different fixes) 8, split 4/4 by fixed-seed (42) balanced random assignment, blinded as Version A/B in the sheet. Cycle 2 .xlsx files written to `data/review_sheets/cycle2/` (`Tamil_Cycle2_Rohan.xlsx` -- 8 bucket-3 + 4 bucket-4 rows in separate tabs; `Tamil_Cycle2_Dhayanidhi.xlsx` -- 4 bucket-4 rows), not yet uploaded to Google Sheets. Classification and the bucket-4 adjudicator/blinding assignment saved as their own derived files in `data/reviews/` (`tamil_cycle1_classification.json`, `tamil_cycle2_bucket4_assignment.json`), separate from the untouched raw Cycle 1 files, per the data provenance policy. One data anomaly noted, not silently fixed: `multiple_1` -- Rohan marked Correct but also flagged Script/Formatting and supplied a fix; still classifies correctly into bucket 3 off the Correctness field. Same pipeline still needs to be run for Hindi (Jayant Kapoor, Anshul) and PARA/SYNO (Jayant Kapoor, Anshul) once each pair finishes Cycle 1, and eventually Gujarati (Dhruv Kunvarani, Samarth) -- not requested yet.
- **Tamil Cycle 2 completed and resolved to final text (2026-09-09)**: both reviewers returned their Cycle 2 workbooks (`Tamil_review_cycle_2_Rohan.xlsx`, `Tamil_review_cycle_2_Dhayanidhi.xlsx`), validated clean against the saved assignment (all 20 items in the right sheet, valid decisions, the one write-new case had its correction filled in). `translation/resolve_cycle2_tamil.py` merges Cycle 1 (buckets 1/2) + Cycle 2 (buckets 3/4) into `data/reviews/tamil_final_resolved.jsonl` (200 rows, fully traceable to both reviewers' verdicts and any Cycle 2 decision); raw Cycle 2 decisions also snapshotted separately in `data/reviews/tamil_cycle2_decisions.json`. Bucket 3 resolution: 5 Accept fix / 3 Original stands. Bucket 4: 4 Version A / 3 Version B / 1 write-new. **Reviewer behavior recorded** (user request) in `data/reviews/tamil_cycle2_reviewer_behavior.md`: Rohan reversed his own "Correct" call 5/8 times in bucket 3; adjudicators picked the blinded *other* reviewer's fix 6/7 times (not their own) in bucket 4; the one write-new case genuinely synthesized both proposed fixes rather than picking one -- no evidence of self-favoring/rubber-stamping bias found, small sample (n=8, n=7), to be rechecked once Hindi/PARA-SYNO Cycle 2 data exists. Tamil is now the first language with a fully resolved, provenance-traceable gold translation set end to end.
- **Hindi Cycle 1 checked, Cycle 2 built (2026-09-09)**: reviewers Jayant Kapoor and Anshul Gupta, 200/200 rows each, structurally clean. Found a systematic issue distinct from Tamil's one-off: Anshul marked Correctness="Correct" on all 200 rows, but had filled in a Corrected version (+ issue checkbox + note) on 10 of them -- 4 of which (`multiple_122, 125, 134, 170`) would have silently resolved as "both Correct, no Cycle 2" under a literal reading, losing real catches (a dropped "felony" qualifier, a dropped "assume equal variance", a grammatical meaning-flip). Reported to the user before proceeding; user confirmed the cause: Anshul misread the Correctness field as "is my correction correct" rather than "is the original correct". Applied as an explicit, documented, Anshul-only reinterpretation for classification purposes (non-empty Corrected version -> effectively Incorrect), raw Correctness column left untouched -- see `data/reviews/hindi_cycle1_classification.json`'s `anshul_correctness_reinterpreted` note for the full traceable record. Reclassified result: bucket 1 (both Correct) 186, bucket 2 (identical fix) 1, bucket 3 (asymmetric) 8 (split 4/4 Jayant/Anshul), bucket 4 (different fixes) 5 (split 3/2 by the same fixed-seed-42 balanced random assignment as Tamil). `translation/generate_cycle2_hindi.py` wrote `data/review_sheets/cycle2/Hindi_Cycle2_Jayant.xlsx` and `Hindi_Cycle2_Anshul.xlsx`, not yet uploaded to Google Sheets. Gujarati (Dhruv Kunvarani, Samarth) Cycle 1 -> Cycle 2 still pending, not requested yet.
- **English PARA/SYNO Cycle 1 checked, Cycle 2 built (2026-09-16)**: reviewers Jayant Kapoor and Anshul Gupta, 400/400 rows each (200 base_ids x PARA+SYNO), keyed by (base_id, perturbation_type) since each gets an independent verdict. Hit a real loader bug first: the sheet template merges the base_id/English Source cells across each PARA+SYNO pair, and openpyxl only returns a value on a merge's top-left cell -- naive reading collapsed every SYNO row onto one key (201 apparent rows instead of 400). Fixed with forward-fill, re-verified clean (400/400, keys match, source text identical, no empty Correctness). Bucket counts: 1 (both Correct) 392, 2 (identical fix) 1, 3 (asymmetric) 6, 4 (different fixes) 1. New anomaly type, not seen before: two items where a reviewer marked "Incorrect" with nothing else filled in at all (no fix, no issue checkbox, no notes) -- `multiple_3` (PARA) and `multiple_72` (SYNO). Reported to the user with a concrete proposal before building anything; confirmed: `multiple_3` gets a Cycle 2 row with only 2 options (no "Accept fix" -- nothing to accept); `multiple_72` skips Cycle 2 entirely, auto-resolved to the one reviewer's actual fix since the other side wasn't a competing alternative, just blank. `translation/generate_cycle2_parasyno.py` wrote `data/review_sheets/cycle2/ParaSyno_Cycle2_Jayant.xlsx` and `ParaSyno_Cycle2_Anshul.xlsx` (3 bucket-3 items each). Classification + the auto-resolved item saved to `data/reviews/parasyno_cycle1_classification.json`. **Cycle 2 returned complete and resolved (2026-09-19)**: `data/reviews/parasyno_final_resolved.jsonl`, 400/400 rows (bucket 3: 2 Accept fix / 4 Original stands).
- **Gujarati Cycle 1 checked, Cycle 2 built (2026-09-19)**: reviewers Samarth Patel and Dhruv Kunvarani, 200/200 rows each. Bucket counts: 1 (both Correct) 134, 2 (identical fix) 1, 3 (asymmetric) 51, 4 (different fixes) 14 -- by far the highest Cycle-2 rate of any language (32.5% vs. 6.5-8% for Hindi/Tamil). New rule (user-confirmed): 6 items where both reviewers said Correct but Dhruv volunteered an unprompted "Better translation" are resolved directly to Dhruv's version, no Cycle 2 needed (`prefer_dhruv_better_translation` in `gujarati_cycle1_classification.json`) -- 3 similar-looking items where Samarth actually disagreed stay in normal bucket 3. `Gujarati_Cycle2_Samarth.xlsx` / `Gujarati_Cycle2_Dhruv.xlsx` uploaded, Cycle 2 not yet returned.
- **Hindi Cycle 2 resolved (2026-09-19)**: `data/reviews/hindi_final_resolved.jsonl`, 200/200 rows (bucket 3: 3 Accept fix / 5 Original stands; bucket 4: 4 Version A / 1 Version B). Hindi is now the second fully-resolved language after Tamil.

## Tamil experiments -- results so far (2026-09-16)

First real experimental results (English NT vs Tamil FT-NO, 200 questions each), all verified with raw-output spot checks before trusting scores, not just summary numbers. Full detail and bug history in LOG.md.

| Model | English | Tamil | Gap | Hosted via |
|---|---|---|---|---|
| Qwen3-32B | 96.5% | 79.5% | 17.0pt | Sharanga (self-hosted) |
| Sarvam-M | 95.5% | 73.5% | 22.0pt | Sharanga (self-hosted) |
| Qwen3.5-9B | 94.0% | 74.0% | 20.0pt | OpenRouter |
| Qwen3.8-27B | 95.5% | 76.5% | 19.0pt | OpenRouter |
| Qwen3.5-122B-A10B | 95.0% | 78.0% | 17.0pt | OpenRouter |
| Gemma4-26B-A4B | 93.0% | 83.5% | 9.5pt | OpenRouter |
| Gemma4-31B | 88.5% | 80.5% | 8.0pt | OpenRouter |
| Llama4-Maverick | 91.5% | 79.5% | 12.0pt | OpenRouter |

**Every model shows a real English-vs-Tamil gap**, ranging 8-22 points. Sarvam-M (Indic-native) has the *largest* gap of any model tested, not the smallest -- Indic-specific training did not shrink the effect here. Gemma4 shows the smallest gap of any model (8-9.5pt) -- worth a closer error-taxonomy look, not yet done. Error-taxonomy breakdown (language-mismatch vs. wrong-value vs. wrong-function, plus a paired English-succeeds-on-same-question check) has only been run for Qwen3-32B so far (`data/reviews/qwen32b_tamil_error_taxonomy.json`; 46%/41%/12% split, 93% of Tamil failures succeed in English on the identical question) -- not yet repeated for the other 7 models.

**Infrastructure built this round**: `bfcl_eval/model_handler/api_inference/openrouter.py` (`OpenRouterHandler`) lets any OpenRouter-hosted model be evaluated with zero per-model prompt-formatting code, since OpenRouter applies each model's own chat template server-side -- this is now the default route for any model too new or too large to self-host, rather than building a bespoke local handler each time (which Sarvam-M needed, and which Qwen3.5/Gemma4 would also have needed if self-hosted, since both changed their tool-calling format from the versions BFCL's existing local handlers target). Always sends `reasoning: {"enabled": false}` -- confirmed necessary, not just a precaution -- matching the project's decided policy of direct/non-reasoning mode for every model.

**Known gaps / not yet done**:
- Gemma4-E4B and Gemma4-12B (2 of the originally-planned 4 Gemma sizes) are not available on OpenRouter at all; would need self-hosting on Sharanga with a new Gemma4 handler (not built).
- Llama4-Scout (the plan's original pick) isn't on OpenRouter; Llama4-Maverick substituted for the OpenRouter route. Scout itself remains available and registered for self-hosting on Sharanga.
- Sarvam-30B/105B, and the OpenRouter-only models (Kimi K2.6, DeepSeek, Mistral Large 3, GLM-4.6 flagship) not yet run.
- Error-taxonomy breakdown only done for Qwen3-32B; not yet repeated for the other 7 models now that they have results.

## 14-model open-weights batch: EN / HI / TA / PARA / SYNO (run 2026-09-19/20, files recovered 2026-09-29)

Full detail and bug history in LOG.md, 2026-09-19/20 (backfilled).
- **Test categories:** `multiple_hi` (from `hindi_final_resolved.jsonl`),
  `multiple_para` and `multiple_syno` (from `parasyno_final_resolved.jsonl`).
- **Where it ran:** 12 small/mid models on bits-gpu; Qwen3-32B and
  Gemma3-27B on Sharanga H200s.
- **Result files:** copied back into local `result/` and `score/` on
  2026-09-29. Every one of the 70 cells was re-read from its score file
  (n=200 each).

| Model | EN | HI | TA | PARA | SYNO |
|---|---|---|---|---|---|
| Qwen3-1.7B | 92.5 | 74.5 | 60.0 | 89.0 | 86.0 |
| Qwen3-8B | 96.0 | 77.5 | 82.5 | 91.5 | 86.5 |
| Qwen3-32B | 96.5 | 75.0 | 79.5 | 91.5 | 90.0 |
| Gemma3-4B | 87.5 | 59.0 | 64.5 | 86.0 | 78.5 |
| Gemma3-12B | 94.0 | 77.0 | 82.5 | 90.0 | 86.5 |
| Gemma3-27B | 92.5 | 66.5 | 72.0 | 89.5 | 87.0 |
| Falcon3-3B | 68.5 | 13.5 | 7.5 | 62.0 | 57.5 |
| Falcon3-7B | 89.0 | 52.0 | 33.5 | 86.0 | 84.5 |
| Falcon3-10B | 92.5 | 64.0 | 42.0 | 89.0 | 84.5 |
| Llama-3.2-3B | 92.5 | 40.5 | 41.5 | 87.0 | 80.0 |
| Llama-3.1-8B | 53.5 | 28.0 | 36.0 | 52.5 | 48.5 |
| Hammer2.1-0.5B | 80.5 | 16.5 | 8.0 | 72.5 | 52.0 |
| Hammer2.1-1.5B | 92.0 | 41.5 | 25.0 | 87.0 | 77.5 |
| Hammer2.1-7B | 92.5 | 66.0 | 44.0 | 88.5 | 75.0 |

- **Translation hurts far more than perturbation.** HI/TA cost 13.5-72.5pt
  vs. EN; PARA/SYNO mostly 0-8pt.
- **SYNO is consistently harder than PARA.**
- **Hindi vs. Tamil splits by family.** Tamil is worse for
  Falcon3/Hammer2.1/Qwen3-1.7B, and slightly better for
  Qwen3-8B/32B, Gemma3 and Llama-3.x.
- **Open issues:**
  - Llama-3.3-70B is not run (blocked on the HF gated-repo access grant).
  - Llama-3.1-8B's 53.5% EN looks like a handler issue; spot-check it
    before trusting.
  - No error taxonomy has been run on any of these yet.

**Sarvam-M caveat:** the Tamil-results table above quotes 95.5 / 73.5, the
post-fix numbers. The only Sarvam-M score files that exist, both local and
on Sharanga, are the pre-fix 79.5 / 62.0 (dated 2026-09-10 09:52, two
minutes before the bracket fix `a8d916d`). Re-run `bfcl evaluate` on the
saved outputs to regenerate the post-fix score files before citing.

## PARA/SYNO dual-source Indic translation + cross-language NO analysis (2026-09-19)

**Translation pipeline**: PARA/SYNO English (400 rows, now Cycle-2-resolved) translated into Hindi, Tamil, Gujarati by two independent sources -- IndicTrans2 (`translate_indictrans2.py`) and Google Cloud Translation API (`translate_google.py`, new). Reviewer sees both candidates per item and judges each independently, rather than being forced to pick one -- if the two reviewers validate different sources as "the" correct one, that's not a special conflict, it just falls out as bucket 3 on each source's own independent 4-bucket classification (same machinery as everywhere else); both ending up validated Correct is a legitimate outcome, final-text tie-break deferred to export time. Real cost: $0 (well under the Cloud Translation free tier). Fixed a staleness bug before running either translator: PARA/SYNO source text now comes from `parasyno_final_resolved.jsonl` (post-review), not the stale pre-review `en_multiple_perturbations.jsonl`.

**Review sheet, 2nd iteration based on user feedback**: original dual-candidate sheet only showed PARA/SYNO; user pointed out a translation-specific failure mode -- a translation model can collapse two genuinely different English sentences (NO vs. PARA) into near-identical target-language text, silently defeating the perturbation even when both are individually "correct" translations. Sheets now show a 3rd grey read-only reference row (NO -- English + already-resolved translation) above each PARA/SYNO pair, plus a new "Same as NO Translation" issue checkbox. Gujarati's NO isn't resolved yet, so its reference row uses the pre-review IndicTrans2 text with an explicit "NOT YET Cycle-2-resolved" marker (auto-detected, needs a re-run once Gujarati's NO resolves). Sheets uploaded for Hindi/Tamil; Gujarati withheld until its own Cycle 2 comes back.

**Cross-language NO analysis** (Hindi/Tamil resolved, Gujarati Cycle-1-only): Hindi's raw IndicTrans2 output needed human correction on only 7.0% of items vs. Tamil's 37.0% and Gujarati's ~32.5% (preliminary) -- a 5x quality gap between Hindi and the other two. The automated number/marker QA checker doesn't see this gap at all (flags ~6.5-7% of rows in all three languages alike), because it only catches a narrow numeric-fidelity failure mode; cross-checked directly and confirmed QA-clean status predicts human-correctness well for Hindi (96.8% clean) but poorly for Tamil (only 66.8% of QA-clean items were actually fine). This gives a plausible explanation for why Tamil showed the largest English-vs-Tamil accuracy gap of any model tested in the experiments above -- the raw MT quality gap is real and visible at the review stage, not just downstream. Reviewer-behavior comparison (Hindi vs. Tamil) shows opposite leans on both bucket 3 (self-reversal rate) and bucket 4 (own- vs. other-fix preference) -- flagged as a small-n (5-13 items) descriptive contrast, not a generalizable pattern; see `hindi_cycle2_reviewer_behavior.md` and `tamil_cycle2_reviewer_behavior.md`. Full detail and tables in LOG.md (2026-09-19).

## Open decisions

- **Language scope (decided 2026-09-29, user):** English + **Hindi, Gujarati,
  Tamil** only. Marathi, Bengali and Santali/Bodo from
  `Indic_ToolCalling_Project_Plan.md` are **dropped**. What the design can
  still separate:
  - Family: Tamil vs. Hindi/Gujarati.
  - Script: Hindi vs. Gujarati (same family, but resource level also
    differs).
  - Script alone: the planned Romanized condition.

  Resource level is no longer isolated and is listed as a limitation.

- **PAR (partially translated) construction method**: deferred. IndicTrans2 (pure NMT) cannot do this -- confirmed MLCL's own PAR construction is LLM-instruction-based (translate the query, keep ground-truth-parameter-value keywords in English), not NMT-based. When resumed, default to matching MLCL's method for comparability unless told otherwise.
- **Review sampling depth**: for PARA/SYNO, a 10% human sample was discussed as reasonable given 0/400 automated number-drift flags with a capable model. For translations, decided to hold off on a percentage until the unit/exponent fidelity checker (above) gives a real automated baseline, given the one already-observed `m/s^2` issue.

## Next steps

- [x] Pull `qwen3:8b` in Ollama, register `qwen3-8b-ollama-FC`, smoke-test end-to-end (generate + evaluate). Passed.
- [ ] Get real API keys for Gemini (`GOOGLE_API_KEY`), DeepSeek (`DEEPSEEK_API_KEY`), Qwen cloud (`QWEN_API_KEY`) -- current `.env` values are empty/placeholders.
- [ ] Verify GPT-5 routing via OpenRouter.
- [ ] Register Llama via OpenRouter.
- [ ] Get Sarvam API access + determine handler approach.
- [ ] Run the same 12-schema smoke test against every other model once reachable, to finish Exp 0.
- [x] Build a unit/exponent-marker fidelity checker for translations -- done as `translation/check_translation_fidelity.py`.
- ~~Assign verifiers to each Label Studio project~~ / ~~Build import_label_studio_reviews.py~~ -- obsolete: Label Studio torn down 2026-08-25; review runs on Google Sheets with per-language `resolve_cycle2_*.py` scripts instead.
- [ ] Decide PAR construction method and build it (LLM-instruction-based, matching MLCL, is the default plan).
- [x] Translate PARA/SYNO English text into Hindi/Tamil/Gujarati (2026-09-19, dual-source IndicTrans2 + Google Translate). (Marathi/Bengali/Santali-Bodo dropped from scope 2026-09-29.)
- [x] Build `multiple_hi`, `multiple_para`, `multiple_syno` test categories and run them (2026-09-19/20) -- 14-model open-weights batch done; results in `result/`/`score/` (recovered from bits-gpu + Sharanga 2026-09-29).
- [ ] Run Llama-3.3-70B (the 15th model) once the HF gated-repo access is granted.
- [ ] Spot-check Llama-3.1-8B raw outputs (53.5% EN is suspiciously low vs. Llama-3.2-3B's 92.5%).
- [ ] Re-run `bfcl evaluate` for Sarvam-M on the saved outputs so the post-fix (95.5/73.5) score files actually exist.
- [ ] Run `multiple_hi`/`multiple_para`/`multiple_syno` for the 2026-09-16 OpenRouter models (Qwen3.5/3.8, Gemma4, Llama4-Maverick) and Sarvam-M -- currently they only have EN/TA.
- [ ] Error-taxonomy breakdown for the 14-model batch (HI and TA).
- [x] Gujarati Cycle 2 returned, validated and resolved (2026-10-20): `gujarati_final_resolved.jsonl`, test category `multiple_gu` built and registered. See LOG.md.
- [x] multiple_195 harmonized to multiple_108's reviewed Gujarati text (user decision 2026-10-20).
- [ ] Run models on `multiple_gu` (all 14 open-weights + OpenRouter batch), copy results back, fill the GU column in the short paper.
- [ ] Update the papers' Gujarati MT-correction figure: preliminary ~32.5% -> final 35.0%.
- [x] Gujarati PARA/SYNO dual-translation review sheet regenerated with the resolved NO reference (2026-10-20): `data/review_sheets/Gujarati_ParaSyno_Translation_review_template.xlsx`. Upload to Google Sheets and duplicate per reviewer.
- [x] Midterm short paper (4-page ACL version with placeholders) built 2026-10-13: `reports/midterm/Indic_ToolCalling_Midterm_Short_Overleaf.zip`. See LOG.md 2026-10-13.
- [ ] Confirm the acknowledgements wording (BITS seed grant / Postman / APPScAI) with the PI before submitting the short paper.
- [x] Reference check for the short paper (2026-10-13): all 24 cited entries verified by script against official records (authors, year, link). See `reports/midterm/citation_check_2026-10-13.md`.
