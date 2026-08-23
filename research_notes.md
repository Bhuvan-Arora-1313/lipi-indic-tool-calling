# Research Notes — Fixing Parameter-Value Failures in Tool Calling for Indian Languages

*Living document. Last updated: Aug 19, 2026. Keep adding to this as you go — ask Claude to update it after any session with new results or decisions.*

---

## 1. Novelty & Positioning (for Introduction / Related Work)

**Correction to the original proposal's framing:** the claim "first study to include a Dravidian language" is too broad and should be tightened. VoiceAgentBench (speech-based, includes Tamil/Telugu/Malayalam) and IndicDB (Text-to-SQL, includes Tamil/Telugu) both already cover Dravidian languages in some form.

**The accurate, defensible novelty claim:** first study of the *parameter-value-language-mismatch* failure mode specifically, in the *text-based executable tool-calling* setting, at *numeral/date/entity granularity*, for a Dravidian language. Neither VoiceAgentBench (different modality — speech/ASR) nor IndicDB (different task — SQL generation, fixed grammar) isolates this specific mechanism or granularity.

**Additional related work found beyond the original proposal table** (searched during the project, not in the original literature review):
- **Ticket-Bench** (Sept 2025) — multilingual function-calling benchmark, European languages only, no Indic coverage. Useful methodologically (regionalizes entities per language) but not a direct comparator.
- **MAPS** (Multilingual Benchmark for Agent Performance and Security) — includes Hindi, no Dravidian language. Broad cross-lingual gap + security angle, not parameter-level diagnosis.
- **GAIA-v2-LILT** (~April 2026) — Hindi only, no Dravidian. Key finding: ~20 points of "multilingual gap" in prior benchmarks can be translation artifact rather than real model limitation once translations are carefully audited. **Relevant caution for our own E2 methodology** — motivates the back-translation QA pipeline we built (Section 3).
- **OmnilingualGAIA2** (Meta Superintelligence Labs, Aug 9 2026 — very recent). Ten languages confirmed via direct inspection of their Figure 2 column labels: eng, spa, deu, fra, ita, por, **ind (Indonesian, not India)**, tur, cmn, jpn, hin. **No Dravidian language** — confirms our novelty claim holds even against the newest, best-resourced comparator. Their "Execution" panel (closest analogue to our task) shows Hindi dropping 15–46 points depending on model — corroborating evidence our motivation section can cite as an independent, very recent confirmation the problem is real.

---

## 2. Methodology Decisions & Rationale

### Translation approach
Used an LLM (GPT-4o via OpenRouter) rather than a dedicated MT system (Google Translate, IndicTrans2) as the primary translator. Rationale: avoided heavy dependency setup, and gave fine-grained prompt control over realistic numeral/date conventions. **Tradeoff to state explicitly in Limitations**: a dedicated MT system structurally cannot hallucinate/add content (no "reasoning" capacity), which an LLM can and did (see Section 3). Precedent: IndicDB also used an LLM (Gemini) as its "primary conversion engine," so this is not an unusual choice for this literature. Our own predecessor BFCL-Hi used Google Translate + human verification instead — worth citing as the alternative path not taken.

### Numeral convention — a real Hindi/Tamil asymmetry (relevant to RQ3)
Confirmed via multiple independent sources: Tamil's traditional numeral glyphs (௦–௯) are essentially obsolete in contemporary usage — "in contemporary usage, Tamil largely employs Arabic numerals for all practical purposes, including in education, governance, and daily life." Devanagari numerals, by contrast, remain in active use in Hindi. **Implication:** the numeral-mismatch failure mechanism this whole project studies applies less structurally to Tamil than to Hindi — a lower Tamil "numeral mismatch" rate would not necessarily mean better model handling, it could mean the mechanism barely applies to begin with. State this explicitly when interpreting the Hindi-vs-Tamil comparison (RQ3).

### Currency localization — open methodological decision, not yet finalized
Found the translator sometimes silently converts USD → INR during translation (8 instances flagged in QA). This is a genuine problem distinct from language ability: if the ground truth expects a specific numeric value tied to USD, and the translated query says the same number in INR, the "correct" tool call is arguably no longer the same question. **Decision needed**: keep original currency units regardless of naturalness (current default going forward), and document this as a deliberate choice.

### QA pipeline: back-translation + LLM judge
Built to catch translation errors before treating translated data as ground truth for evaluation. Two-stage: (1) back-translate Hindi/Tamil → English using a **different model family** (Claude Sonnet) than the forward translator (GPT-4o), specifically so a shared blind spot doesn't cancel out invisibly; (2) a judge model (gpt-4o-mini) compares back-translation against the original English and flags MISMATCH with a stated reason.

**Important self-correction to note in the paper**: the back-translation QA pipeline itself has a nonzero false-positive rate. On manual review, at least one flagged "entity garbling" case (Tamil #339, "poker" flagged as mistranslated to "Bhogar") turned out to be a misreading introduced during the *back-translation* step, not a real forward-translation error — the actual Tamil text correctly said "போக்கர்" (poker) all along. This is itself a citable methodological finding: **QA pipelines built from LLM judges need their own spot-checking, not blind trust of stated reasons.**

---

## 3. QA Findings — Error Taxonomy (for Methods / Error Analysis section)

Back-translation check flag rates on `simple_python` (n=400 each): **Hindi 40/400 (10%)**, **Tamil 72/400 (18%)**. Both above IndicDB's own ~8% flag rate; Tamil notably higher (possibly reflecting Tamil being lower-resource for the back-translation/judge models too, not necessarily the forward translator — worth noting as an open question, not a settled fact).

Categories identified via manual triage of all 112 flagged rows (mirrors IndicDB's own error taxonomy structure):

| Category | Examples found | Notes |
|---|---|---|
| Hallucination / added content | Hindi #2, #105; Tamil #34, #130, #222, #295, #311 | Model appends a computed answer or extra detail not in the source query. Fixed via strengthened prompt forbidding this explicitly — reduced but did not fully eliminate (~7/800 still slipped through). |
| Numeric value changed | Hindi #132 (equity amount); Tamil #160 (case number), #219 (neuron count), #223 (group size 50→70) | Most serious category — directly corrupts ground truth. #223 was the clearest, most serious single bug found (50 became "seventy" / எழுபது). |
| Entity/proper-noun garbling | Tamil #330 ("Catan"→"Kattaan") | Matches IndicDB's #1 error category, "Lexical Entity Divergence" (~31% of their flagged errors) — direct corroboration of a published finding in our own data. |
| Systematic term mistranslation | "Vegan" → "vegetarian" (Hindi #77, #80, #356; Tamil #35) — 4 independent instances | Too consistent to be random; likely reflects "vegan" lacking as standard a native-language equivalent as "vegetarian" in Hindi/Tamil. |
| Currency silently localized | 8 instances, mostly Hindi | See Section 2 — open methodological question, not just a translation bug. |
| Near-synonym drift (likely false alarms) | predict/estimate, odds/probability, ranking/standings, etc. — largest bucket | Back-translation naturally introduces paraphrase drift; judge is often being pedantic about exact wording rather than catching real errors. |

**Fix regression worth noting**: the first automated fix pass (strengthened prompt, re-translation) correctly fixed the numeric and hallucination bugs above, but introduced a new side effect — 3 Hindi examples lost their Devanagari numeral convention (reverted to Western digits) because the stricter "precision" instructions apparently crowded out the numeral-script instruction. Fixed with **deterministic code** (not another LLM call) — a Python Indian-number-grouping formatter, verified correct (e.g. $10,000,000 → "१,००,००,०००" / 1 crore). **Worth stating as a design principle**: numeral/currency formatting is better handled by deterministic post-processing than by relying on an LLM to get lakh/crore grouping right during free-form translation — this is arguably a preview of the E4 "value-slot-targeted repair" idea from the original proposal, just applied to dataset construction rather than model output.

---

## 4. Results So Far

**Model**: gpt-4o-mini-2024-07-18-FC, via OpenRouter. **Category**: `simple_python` (BFCL v4, n=400).

| Setting | Accuracy | Gap vs. English |
|---|---|---|
| English (NT baseline) | 91.25% | — |
| Hindi (NT, no mitigation) | 59.50% | −31.75 pts (40.5% relative failure rate) |
| Tamil (NT, no mitigation) | 67.25% | −24.00 pts (32.75% relative failure rate) |
| Hindi + PT (MLCL baseline, replicated) | 81.50% | −9.75 pts — recovers 69.3% of the English–Hindi gap |
| Hindi + POST (MLCL baseline, replicated) | 82.00% | −9.25 pts — recovers 70.9% of the English–Hindi gap |
| Hindi + PRE (MLCL baseline, replicated) | 85.00% | −6.25 pts — recovers 80.3% of the English–Hindi gap |

**Full E3 replication set complete.** Ranking (PRE > POST > PT) matches MLCL's own qualitative finding closely — they describe PRE as generally strongest due to full query context, and PT as weakest with inconsistent compliance. Our absolute recovery percentages are higher across the board than what they reported for the models they tested (GPT-5 family, DeepSeek, Llama 3.1, Qwen 3, Granite 4 — none of which is gpt-4o-mini), but the *ordering* replicates cleanly. Also consistent with their core claim: even the best strategy (PRE) leaves a real 6.25-point residual gap — none of these lightweight fixes fully closes it.

**Implementation notes for Methods**: PT and PRE required new `bfcl generate` runs (~400 fresh API calls each). POST did not — since MLCL's POST strategy is itself defined as a post-processing step on already-generated output, POST was implemented by re-using the existing Hindi (NT) generation results and translating only the individual non-English parameter values found in them (using a simple non-ASCII-character heuristic to skip values already in English, minimizing translation calls to only what's needed).

### Error taxonomy breakdown (for Error Analysis / RQ3 section)

Built by reusing BFCL's own AST-checker `error_type` field rather than re-implementing parsing logic — BFCL already records exactly why each example failed. Mapped onto a simplified version of MLCL's severity-ordered taxonomy: Syntax Error → Function-Level Error → Language Mismatch (generated value contains non-English characters) → Wrong Value (English, but still incorrect).

| Category | Syntax Error | Function-Level Error | Language Mismatch | Wrong Value (English) | Total failures |
|---|---|---|---|---|---|
| English (simple_python) | 0 (0.0%) | 13 (3.2%) | 1 (0.2%) | 21 (5.2%) | 35/400 |
| Hindi NT | 0 (0.0%) | 15 (3.8%) | 121 (30.2%) | 26 (6.5%) | 162/400 |
| Tamil NT | 0 (0.0%) | 16 (4.0%) | 82 (20.5%) | 33 (8.2%) | 131/400 |
| Hindi + PT | 0 (0.0%) | 17 (4.2%) | 11 (2.8%) | 46 (11.5%) | 74/400 |
| Hindi + PRE | 2 (0.5%) | 16 (4.0%) | 2 (0.5%) | 40 (10.0%) | 60/400 |
| Hindi + POST | 0 (0.0%) | 16 (4.0%) | 6 (1.5%) | 50 (12.5%) | 72/400 |

**Finding 1 — Tamil-numeral hypothesis confirmed.** Language Mismatch: Hindi 30.2% vs. Tamil 20.5%, a ~10-point gap that plausibly explains most of Tamil's higher raw accuracy — not better general handling of Tamil, but structurally less opportunity for the specific numeral-mismatch mechanism to fire, consistent with Tamil's numerals being largely obsolete in real usage (Section 2). **Nuance worth keeping**: Tamil's Wrong-Value-English rate is *higher* than Hindi's (8.2% vs 6.5%) — some failures that would show up as script-mismatch in a language with an active native numeral system show up in Tamil as genuine comprehension error instead. Nice small-scale echo of MLCL's own finding about Igbo (their low-resource language): less language-mismatch, more real semantic error underneath — worth citing that parallel directly.

**Finding 2 — all three mitigation strategies show the identical failure-mode shift.** Each crushes Language Mismatch (Hindi's 30.2% down to 2.8% / 0.5% / 1.5% for PT/PRE/POST respectively) but Wrong-Value-English rises sharply in exchange (6.5% up to 11.5% / 10.0% / 12.5%). This is a clean numerical replication of MLCL's own stated finding: *"Translation introduces semantic drift and surface-form normalization, replacing language mismatch with new execution-level errors."* Not just citing their claim — demonstrating it independently.

**Finding 3 — Function-Level Error is flat across every condition (3.2%–4.2%, English included).** Tool selection and intent understanding don't degrade under translation or under any mitigation strategy, in any of the six conditions tested. Directly reproduces MLCL's headline claim that failures occur "despite correct intent understanding and tool selection" — arguably the cleanest, most consistent piece of evidence in the whole dataset so far.

**Cross-check**: total-failures column (162/74/60/72 for NT/PT/PRE/POST) ranks in exactly the same order as the accuracy table above (PRE best, POST and PT close, NT worst) — internal consistency confirmed between the two analyses.

### Tamil strategy comparison (mirrors Hindi E3 replication)

| Setting | Accuracy | Gap vs. English | % of gap recovered |
|---|---|---|---|
| Tamil (NT, no mitigation) | 67.25% | −24.00 pts | — |
| Tamil + PRE | 78.75% | −12.50 pts | 47.9% |
| Tamil + POST | 79.75% | −11.50 pts | 52.1% |
| Tamil + PT | 82.00% | −9.25 pts | 61.5% |
| Tamil + PT+POST | 82.25% | −9.00 pts | 62.5% |

**Finding 5 — the Hindi strategy ranking fully reverses for Tamil.**
- Hindi: PRE (80.3%) > PT+POST (72.4%) > POST (70.9%) > PT (69.3%)
- Tamil: **PT+POST (62.5%) > PT (61.5%) > POST (52.1%) > PRE (47.9%)**

PT and PRE essentially swap from best to worst between languages, with POST consistently in the middle for both. The combination (PT+POST) is the single best strategy for *both* languages, but the margin differs sharply: for Hindi, PRE alone still beats the combination (85.00% vs 82.50%); for Tamil, nothing beats the combination, not even PRE. **Practical implication worth stating in Discussion**: if you don't know in advance which language you're deploying for, PT+POST is the safer universal choice — PRE is the single best strategy, but only if you already know you're dealing with Hindi specifically.

Plausible mechanism, **confirmed by the full error taxonomy re-run** (see below) — PRE's weakness for Tamil is specifically translation-induced semantic drift, not comprehension failure.

### Full error taxonomy across all ten categories (both languages, all strategies)

| Category | Syntax Error | Function-Level Error | Language Mismatch | Wrong Value (English) | Total failures |
|---|---|---|---|---|---|
| English | 0 (0.0%) | 13 (3.2%) | 1 (0.2%) | 21 (5.2%) | 35/400 |
| Hindi NT | 0 (0.0%) | 15 (3.8%) | 121 (30.2%) | 26 (6.5%) | 162/400 |
| Tamil NT | 0 (0.0%) | 16 (4.0%) | 82 (20.5%) | 33 (8.2%) | 131/400 |
| Hindi + PT | 0 (0.0%) | 17 (4.2%) | 11 (2.8%) | 46 (11.5%) | 74/400 |
| Hindi + PRE | 2 (0.5%) | 16 (4.0%) | 2 (0.5%) | 40 (10.0%) | 60/400 |
| Hindi + POST | 0 (0.0%) | 16 (4.0%) | 6 (1.5%) | 50 (12.5%) | 72/400 |
| Hindi + PT+POST | 0 (0.0%) | 17 (4.2%) | 4 (1.0%) | 49 (12.2%) | 70/400 |
| Tamil + PT | 0 (0.0%) | 19 (4.8%) | 8 (2.0%) | 45 (11.2%) | 72/400 |
| Tamil + PRE | 3 (0.8%) | 20 (5.0%) | 2 (0.5%) | **60 (15.0%)** | 85/400 |
| Tamil + POST | 0 (0.0%) | 16 (4.0%) | 6 (1.5%) | 59 (14.8%) | 81/400 |
| Tamil + PT+POST | 0 (0.0%) | 19 (4.8%) | 3 (0.8%) | 49 (12.2%) | 71/400 |

**Finding 6 — CONFIRMED: Tamil PRE's weakness is translation-induced semantic drift, not comprehension failure.** Tamil PRE nearly eliminates Language Mismatch (82→2, matching Hindi's reduction almost exactly) but has the single **highest Wrong-Value-English rate of any condition across both languages (15.0%)**. This directly confirms the hypothesized mechanism: PRE routes the entire query through a Tamil→English translation step, and for this model, that translation step itself introduces enough semantic drift to make the (now fully English) query harder to answer correctly — independent of any language-mismatch mechanism. PT never takes this hit because it doesn't translate the query at all; it instructs the model while it still reads the original Tamil directly. This is why PT beats PRE for Tamil while the opposite holds for Hindi: it's specifically about the trustworthiness of a full Tamil→English translation versus a Hindi→English one for gpt-4o-mini.

**Finding 7 — PRE is the only strategy that introduces syntax errors, in either language.** Hindi PRE: 2 syntax errors; Tamil PRE: 3. Every other strategy (PT, POST, PT+POST) shows zero syntax errors in both languages. Small absolute counts, but a clean, consistent pattern: routing through a full query translation occasionally disrupts the model's structured tool-call formatting in a way that instructing-in-place (PT) or post-hoc correction (POST) never does — a small additional cost of PRE worth noting alongside its semantic-drift weakness.

### E4 candidate 1: deterministic type-casting fix (complete)

Before designing a full numeral-matching repair strategy, ran `analyze_wrong_value_types.py` on all Wrong-Value failures to find what fraction were genuinely number/value mismatches versus a completely separate, purely mechanical failure mode: the model outputs an integer where the function's own schema specifies `float` (e.g. `interval: [1, 3]` instead of `[1.0, 3.0]`). This is legitimate to fix deterministically — the type requirement comes from the function schema the model already had in its prompt, not from peeking at the ground truth.

Built `fix_type_casting.py`: reads each function's own parameter schema, recursively casts any int values to float wherever the schema requires it (including inside arrays), leaves everything else untouched. Applied on top of existing result sets, no new `bfcl generate` calls needed (same reuse pattern as POST).

| Condition | Before | After type-cast | Gain |
|---|---|---|---|
| Hindi NT | 59.50% | 60.50% | +1.00 |
| Hindi PT | 81.50% | 82.50% | +1.00 |
| Hindi PRE | 85.00% | 86.00% | +1.00 |
| Hindi POST | 82.00% | 83.00% | +1.00 |
| Hindi PT+POST | 82.50% | 83.50% | +1.00 |
| Tamil NT | 67.25% | 68.25% | +1.00 |
| Tamil PT | 82.00% | 83.00% | +1.00 |
| Tamil PRE | 78.75% | 79.75% | +1.00 |
| Tamil POST | 79.75% | 80.75% | +1.00 |
| Tamil PT+POST | 82.25% | 83.25% | +1.00 |

**Finding 8 — the type-casting fix gives a perfectly consistent +1.00 point gain across all 10 conditions tested (both languages, every strategy including the PT+POST combination), exactly matching the taxonomy's prediction of ~4 type-only failures per 400-example condition.** Free (no API cost, purely deterministic, zero risk of new errors), stacks cleanly with every other strategy tried, and is now the new best result for both languages: **Hindi 86.00% (PRE+typefix), Tamil 83.25% (PT+POST+typefix)**. Worth reporting as a small, fully-explained, perfectly-reproducible contribution in its own right.

### QA methodology note: detecting degenerate translation output (for Methods section)

While building the Tamil and Hindi PRE datasets, gpt-4o-mini occasionally (a handful of cases out of 400 per language) produced two distinct failure modes during back-translation: (a) the same hallucination/added-content bug found earlier in forward translation, and (b) a runaway repetition-loop failure producing walls of repeated characters instead of a translation.

Building an automated detector for (b) took three iterations, worth documenting honestly as a methods note:
1. A same-character run-length check missed alternating-pattern garbage (e.g. "X X X X...") and a length-based check narrowly missed cases just under threshold.
2. A single-character-dominance check fixed that, but produced false positives on legitimate translations containing a few non-ASCII symbols (currency signs, card suits like ♥/♠) — rejecting *correct* translations.
3. **Final approach: compression ratio.** Genuine repetition garbage compresses extremely well (ratio ~0.025 via zlib), while normal English text does not (ratio 0.81–1.09 for short sentences in validation) — a 30x+ margin, not a borderline threshold. This is the version used for the final confirmed numbers in this document.

**Why this is worth including rather than hiding**: it's a concrete demonstration of exactly the QA discipline IndicDB and GAIA-v2-LILT call for (Section 1) — building automated checks, discovering their failure modes, and replacing ad-hoc thresholds with a statistically validated method. Final verification: both Hindi and Tamil PRE datasets were re-scanned with the same final compression-ratio detector and confirmed clean (0 flagged entries), and both languages' accuracy numbers were reconfirmed unchanged from their pre-fix values (85.00% / 78.75%) — meaning the underlying data was never actually corrupted, only difficult for earlier detector versions to automatically clear.

### Late-discovered base-file corruption (2 IDs, bounded and documented)

While testing a source-vs-translation number-drift detector (Section on E4 candidates below), found 2 examples (`simple_python_ta_128`, `simple_python_ta_135`) in the **base** Tamil file (`BFCL_v4_simple_python_ta.json`) containing the same repetition-garbage bug as the PRE-stage failures — meaning these 2 corrupted questions were the actual input to every Tamil experiment run so far (NT, PT, PRE, POST, and all combinations/typefix variants), not just PRE. These slipped past the original 72-example back-translation QA review (Section 3), landing in the "MATCH" bucket that wasn't manually re-checked.

**Methodology**: ran the compression-ratio detector across the base Tamil file, which flagged 95 candidates (a high false-positive rate, since the detector's threshold was calibrated on English text and doesn't transfer cleanly to Tamil/Devanagari script compression behavior — noted as a limitation of the automated check itself). Manually reviewed all 95 flagged candidates and confirmed only 2 were genuine corruption; the remaining 93 were normal, correctly-formed Tamil sentences. **This is the same automated-flag-then-human-verify pattern IndicDB uses for its own QA (Section 3)** — worth stating plainly in the methods section: automated detection followed by manual verification and targeted correction of confirmed cases, not blind trust of the detector's raw output.

**Correction method for the 2 confirmed cases**: both (`simple_python_ta_128`, `simple_python_ta_135`) repeatedly triggered the repetition-loop failure via the API — at both temperature 0 and a temperature-0.3 retry — so rather than continue spending API credits against a repeatable dead end, both were corrected with direct manual translation instead of another automated attempt.

**An observed pattern worth flagging, not yet explained**: both persistently-failing examples are finance/dollar-amount questions (dividend-per-share, stock ROI), and this is at least the third time in this project that finance content with dollar figures has triggered this specific failure mode (the earlier NPV and equity examples had the same pattern). Not conclusive on its own, but consistent across multiple independent instances — worth a line in Limitations as an observed quirk of gpt-4o-mini with this content type, without overclaiming a specific mechanism.

**Decision: fixed the base file for future work, did not cascade-regenerate existing results.** Rationale: a garbled question is very unlikely to be answerable correctly under any condition, so these 2/400 (0.5%) examples almost certainly already register as failures across every category regardless of mitigation strategy — meaning the practical effect on reported accuracy numbers is bounded at well under 1 percentage point and likely zero. None of the paper's actual findings (the Hindi/Tamil strategy-ranking reversal, the semantic-drift pattern, the type-casting result) depend on these 2 specific examples. Cascading a full regenerate across 8+ Tamil categories for a sub-1-point, likely-zero effect was judged not worth the cost — noted here explicitly as a considered decision, not an oversight.

### Strategy combination: PT+POST

Tested the one mechanistically sensible combination (PT reduces mismatch upfront via system-prompt instruction; POST catches whatever slips through afterward). PT+PRE and PRE+POST were not tested — not mechanistically sensible, since PRE removes all non-English content before the other two strategies would have anything left to act on.

| Setting | Accuracy | Gap vs. English | % of gap recovered |
|---|---|---|---|
| Hindi + PT | 81.50% | −9.75 pts | 69.3% |
| Hindi + POST | 82.00% | −9.25 pts | 70.9% |
| Hindi + PT+POST | 82.50% | −8.75 pts | 72.4% |
| Hindi + PRE | 85.00% | −6.25 pts | 80.3% |

**Finding 4 — combining strategies gives a small, real improvement, but doesn't beat PRE alone.** PT+POST (82.50%) only marginally exceeds either strategy individually, and remains 2.5 points below PRE. Explained directly by the taxonomy table: PT had already reduced Language Mismatch to just 11/400 failures, leaving POST little room to add value on top. **Implication worth stating explicitly in Discussion**: *where* in the pipeline an intervention happens matters more than how many interventions are stacked — normalizing the input before generation (PRE) outperforms any combination of instructing-and-correcting strategies applied around the edges of generation. This is a genuine, citable finding about strategy design, not just a numeric footnote.

Implementation note: like standalone POST, PT+POST required no new `bfcl generate` call — built by applying the same POST translation step on top of the existing PT result file (`apply_post.py --source-category simple_python_hi_pt`), reusing the same generalized script used for standalone POST.

**Sanity check**: our raw Hindi failure rate (40.5%) falls within MLCL's own reported range for Hindi (roughly 25–50% depending on model) — good signal the pipeline is measuring something real.

**Notable divergence from MLCL worth writing up**: MLCL characterized PT as their *weakest and least consistent* strategy across GPT-5, DeepSeek, Llama, Qwen, and Granite — models frequently ignored the instruction. Our result is the opposite: a strong, clean recovery for gpt-4o-mini (a model MLCL never tested). Possible explanations to explore before finalizing: (a) genuine model-family difference in instruction-following, (b) our Hindi data went through more QA (back-translation + manual fixes) than MLCL's, giving the instruction less noisy input to work against, (c) delivery mechanism differs — we used BFCL's native system-prompt-merging behavior; MLCL built a custom harness.

**Tamil scoring higher than Hindi (RQ3)**: plausibly explained by the numeral-convention asymmetry in Section 2 — Tamil's test set may simply contain less of the specific failure mechanism this project targets, not necessarily reflect better model handling of Tamil. **Not yet verified** — next step is to break down failures by category (numeral/date/entity) per language to test this directly rather than leaving it as a plausible story.

---

## 5. Technical / Reproducibility Notes

- **BFCL bug found and worked around**: `bfcl generate`/`evaluate` route result files by parsing each entry's `id` field (e.g. `simple_python_0` → category `simple_python`), *not* by the `--test-category` CLI argument. Translated files that reuse the original English IDs will silently collide and overwrite each other's results. Fix: IDs must be renamed to embed the new category name (e.g. `simple_python_hi_0`) in both the question file and its matching ground-truth file.
- **New category registration**: BFCL only accepts `--test-category` names from a hardcoded list (`NON_LIVE_CATEGORY` in `bfcl_eval/constants/category_mapping.py`). New categories must be added there.
- **PT implementation**: delivered via BFCL's built-in system-prompt-merging behavior (a system-role message as the first entry in a question's message list gets automatically merged with BFCL's own default system prompt) — this is a documented pattern already used in BFCL's own `live_*` data files, not a workaround. Avoided editing any shared BFCL source files for this.
- **Translation cost**: full 400-example translation ≈ $0.30–0.50 per language with GPT-4o; back-translation QA check ≈ $1 total for both languages; each generate/evaluate run on gpt-4o-mini ≈ a few cents.

---

## 6. Open Questions / Next Steps

- [ ] Verify the Hindi-vs-Tamil numeral-mechanism story (Section 4) with an actual per-category error breakdown, not just the aggregate accuracy gap.
- [ ] Finalize the currency-localization decision (Section 2) and re-check whether any currently-passing examples are secretly benefiting from unintended localization.
- [ ] Native-speaker confirmation still needed for: Tamil #311 ("கூடலேபந்து" for basketball — possibly a non-standard neologism) and #330 (whether "கடான்" is a better transliteration of "Catan" than the original).
- [x] Build PT, PRE, and POST baselines to complete the E3 MLCL replication set — all three done (Section 4).
- [x] Run the error taxonomy across all six conditions (Section 4) — Tamil-numeral hypothesis confirmed, semantic-drift pattern replicated across all three strategies, function-level-error stability confirmed.
- [x] Test PT+POST combination for both languages — done (Section 4).
- [x] Run the full error taxonomy across all ten categories (both languages, all strategies + combination) — Tamil-numeral hypothesis confirmed, semantic-drift pattern replicated across all strategies, function-level-error stability confirmed, PRE's Tamil-specific weakness mechanistically confirmed as translation-induced semantic drift (not comprehension failure), PRE's unique syntax-error cost identified.
- [ ] Design a novel repair strategy targeted specifically at the Wrong-Value-English problem — this is now the clearly evidenced open problem across every condition tested (NT, PT, PRE, POST, PT+POST, both languages): none of MLCL's strategies fix semantic correctness once a value is in English, and PRE actively makes it worse for Tamil specifically. This is a sharper, evidence-backed E4 target than the original proposal's numeral/date/entity-repair framing, which was aimed at language-mismatch — a problem these baselines already handle reasonably well.
- [ ] Extend error_taxonomy.py with the finer Wrong/Related/Same-Meaning sub-classification (needs an LLM judge per failure) if reviewers want MLCL's full 8-category granularity rather than the simplified 4-category version used here.

### E4 candidate 2: number-matching repair strategy (in progress — unexpected regression, unresolved)

**The idea** (user's own proposal, refined together): at the point where the model produces its tool call, extract the numbers from that output and compare them against the numbers in the *original native-language question* (not the ground truth — this needs to work with information available in a real deployment, not an answer key). Any output number that doesn't trace back to a question number is suspicious. Resolution logic:
- If exactly one suspicious output number and exactly one unmatched question number exist, swap deterministically (free, no API call).
- If multiple candidates exist on either side, ask a narrow, cheap LLM call to match them (not to re-translate or re-solve — just "which candidate number belongs to which parameter").
- If no unmatched question number exists to substitute, leave the value alone.

**Built `fix_number_matching.py`** implementing this. Handles Devanagari and Tamil digit normalization, walks nested parameter structures for numeric leaves, applies the deterministic/LLM-assisted resolution above. Operates on an existing result set (no new `bfcl generate` call needed, same reuse pattern as POST and the type-cast fix). Unit-tested successfully against two known real cases before running on real data: correctly auto-fixed the group-size 70→50 bug (unambiguous case) and correctly parsed Devanagari-grouped currency figures.

**Result on raw Hindi (`simple_python_hi` → `simple_python_hi_numfix`): 55.25%.**

**This is a real regression, not just "no improvement"** — worse than both the 59.50% NT baseline and the 60.50% post-typefix baseline. The fix is actively breaking previously-correct answers, not just failing to help. This needs to be understood before the strategy is used further or reported.

**Diagnosis was in progress when this session ended** — `check_regression.py` was being built to directly compare before/after score files and identify exactly which specific examples flipped from correct to incorrect, which will pinpoint the actual bug rather than guessing.

**Leading hypothesis for the bug, not yet confirmed**: the core assumption — that every correct numeric parameter value must literally appear as a digit sequence somewhere in the source question text — is likely too strict. Plausible false-positive triggers:
- Numbers expressed as words in the source ("half," "a dozen") that a correct model output as digits (0.5, 12) — these would never match any digit found by regex in the source text, get wrongly flagged as "suspicious," and risk being overwritten with an unrelated candidate number from elsewhere in the same question.
- Percentages: a question stating "5%" could be correctly represented by the model as either `5` or `0.05` depending on the function's convention — if the model correctly uses `0.05`, this wouldn't match the source's extracted `5`, triggering a false "fix" attempt.
- Possible bugs in the deterministic swap logic itself when a source number legitimately appears more than once, or in the LLM-matching prompt/response-parsing for the ambiguous-case branch.

**Next steps when resuming**: build and run `check_regression.py` (comparing `simple_python_hi` vs `simple_python_hi_numfix` score files) to get the actual list of regressed examples, inspect several by hand to confirm or replace the hypothesis above, patch `fix_number_matching.py` accordingly, and re-test on raw Hindi before trying Tamil or stacking on PT/PRE/POST. Do not roll this strategy out further or report its results until the regression is understood and fixed.
- [ ] Extend error_taxonomy.py with the finer Wrong/Related/Same-Meaning sub-classification (needs an LLM judge per failure, not just the free deterministic pass done so far) if reviewers want MLCL's full 8-category granularity rather than the simplified 4-category version used here.
- [ ] Keep the weekly literature check going (OmnilingualGAIA2 was found only 9 days after publication) — re-verify the novelty claim in Section 1 stays accurate closer to submission.
