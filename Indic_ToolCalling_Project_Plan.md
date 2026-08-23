# Multilingual Tool-Calling Robustness for Indic Languages
## Project Plan & Reference Document

*Extending MLCL ("Lost in Execution", arXiv 2601.05366) to the Indic language space.*

---

## 1. What this paper is

We study whether large language models fail at tool calling when the user writes in an Indic language. MLCL showed that non-English queries fail primarily through **parameter value language mismatch** — the model understands the intent and picks the right tool, but copies a user-language word into a parameter value that the execution interface expects in English, making the call non-executable.

We extend this to Indic languages with a design that answers questions MLCL's setup could not: we **disentangle script, language family, and resource level** (which MLCL's Chinese/Hindi/Igbo set varied all at once), we add **Romanized input** as a real-world mode MLCL never tested, and we evaluate **Indic-native models (Sarvam)** to test whether Indic-specialized training escapes the failure.

---

## 2. Contributions (the three things that make this novel)

1. **A controlled Indic language design** that isolates resource level, script, and language family as independent variables — enabling causal-style comparisons MLCL's confounded language set could not make.
2. **A Romanization axis** — comparing native-script vs Latin-script (transliterated) input, the dominant real-world way Indic users type, which MLCL held fixed at native script.
3. **Evaluation of Indic-native tool-calling models (Sarvam family)** — testing whether from-scratch Indic training, a custom Indic tokenizer, and code-mixed pretraining prevent the parameter-value-language-mismatch failure.

---

## 3. Languages (5)

| Language | Family | Script | Resource | Purpose in the design |
|---|---|---|---|---|
| **Hindi** | Indo-Aryan | Devanagari | Very high | Anchor for direct comparison with MLCL |
| **Marathi** | Indo-Aryan | Devanagari | Mid | **Hindi vs Marathi = RESOURCE axis** (script + family held constant) |
| **Bengali** | Indo-Aryan | Bengali | High | **Hindi vs Bengali = SCRIPT axis** (family + resource held roughly constant) |
| **Tamil** | Dravidian | Tamil | Mid–high | **FAMILY axis** — a second family, agglutinative morphology |
| **Santali** (or Bodo) | Munda (or Indo-Aryan) | Ol Chiki (or Devanagari) | Extremely low | Low-resource stress case (the "Igbo role") |

**Why these five:** the Indic space lets us change one factor at a time. Hindi–Marathi isolates resource level; Hindi–Bengali isolates script; Tamil tests generalization to a different family; Santali/Bodo is the low-resource extreme, chosen low-but-not-hopeless so the tool-calling signal isn't drowned by pure comprehension failure. Five is the minimum set that delivers all three controlled contrasts plus the extreme; more would inflate native-speaker verification (the real bottleneck) without adding a new scientific comparison.

---

## 4. Models (8)

| Category | Models | Why |
|---|---|---|
| Frontier proprietary | **GPT-5**, **Gemini 2.5** | GPT-5 for comparability with MLCL; Gemini is the strongest model on Indic in IndicParam, so essential for an Indic paper |
| Open general multilingual | **DeepSeek V3.2**, **Qwen3** (one size), **Llama** (current) | Reproducibility and comparability; DeepSeek featured in MLCL, Qwen was strong on low-resource in MLCL |
| **Indic-native** | **Sarvam-105B**, **Sarvam-30B**, **Sarvam-M** | The specialization contrast — confirmed native tool-calling support |

**Why the Sarvam family is the model contribution.** The general models establish the baseline pattern; Sarvam is the specialized contrast group that tests whether Indic training fixes the failure. The three variants give internal structure to that test:

- **Sarvam-105B** — trained from scratch on Indic (custom Indic tokenizer, code-mixed pretraining)
- **Sarvam-30B** — smaller sibling → a **scale** comparison within Indic-native
- **Sarvam-M** — post-trained on a Western base (Mistral) → a **specialization-type** comparison (from-scratch vs post-hoc)

One Indic-native family is sufficient: the paper's claim is about whether the *failure mode* survives Indic specialization, not about any single vendor. Conclusions are scoped to "the Sarvam family"; other Indic-native models are future work.

---

## 5. Conditions / axes

### Inherited from MLCL (for comparability)

- **Query Language Composition:** NT (English) / PAR (context translated, English parameter preserved) / FT (fully translated).
- **Semantic Perturbation:** NO (none) / PARA (paraphrase) / SYNO (synonym substitution).

This 3×3 grid is kept verbatim so results are directly comparable to MLCL.

### New axis — Romanization

For a translated query, we also produce a **Romanized** version: the same Indic-language words written in Latin script (e.g., Hindi *"aaj New York ka mausam batao"* — every content word is Hindi, just in Latin letters). This is transliteration, not code-mixing — the language stays 100% Indic, only the script changes.

- **Why it matters:** Romanized input is how a large share of Indic users actually type, and MLCL only ever tested native script.
- **How we produce it cheaply:** mechanical transliteration via an established tool (AI4Bharat **IndicXlit** or comparable), plus a light native-speaker spot-check for naturalness. No new ground-truth authoring — the target tool call is inherited from the English source.

---

## 6. Error taxonomy (reused from MLCL, unchanged)

Severity-ordered, language-agnostic, enables direct comparison. Most to least severe:

1. Syntax Error
2. Function-Level Error
3. Language Mismatch + Wrong Value
4. Language Mismatch + Relevant but Incorrect
5. Language Mismatch + Same Meaning *(the core parameter-value-language-mismatch signal)*
6. Wrong Value (English, semantically wrong)
7. Relevant but Incorrect (English)
8. Exactly Same Meaning (English, correct but fails strict string match)

Reporting follows MLCL: **error composition and severity**, not aggregate accuracy alone.

---

## 7. Base dataset & protocol

- **Base dataset:** BFCL V4, `BFCL_v4_multiple.json` subset — single-turn queries with multiple candidate functions. Same subset MLCL used.
- **Ground truth:** inherited from the English source; translated and Romanized queries are meaning-preserving surface rewrites, so the target tool call never changes.
- **Verification:** native-speaker check of semantic equivalence for translated conditions; light naturalness spot-check on Romanized output.
- **Evaluation:** BFCL-style exact matching of function name, parameter keys, and parameter values, extended with MLCL's separation of semantic correctness from language conformity.
- **Query count:** fix a modest per-condition N (~200, in line with MLCL's figures).

---

## 8. Experiment plan

| # | Experiment | Scope | Purpose |
|---|---|---|---|
| **Exp 0** | Tool-calling smoke test | ~12 English BFCL schemas × all 8 models (esp. Sarvam) | Confirm every model — especially Sarvam — emits valid parseable tool calls in our harness. Gates the mechanics before any large run. |
| **Exp 1** | Replication anchor | Hindi through the exact MLCL grid | Confirm our pipeline reproduces MLCL's Hindi results before extending. Establishes validity. |
| **Exp 2** | Core robustness | Full grid (NT/PAR/FT × NO/PARA/SYNO) × 5 languages × 8 models, 8-category taxonomy | Does parameter-value-language-mismatch reproduce across Indic? Does Hindi-vs-Marathi confirm resource drives error composition? Does Hindi-vs-Bengali reveal a script effect? |
| **Exp 3** | Romanization axis | Native-script vs Romanized FT, across languages and models | Does input script change the copying behavior? Headline novelty. |
| **Exp 4** | Indic-native specialization | Analytical slice of Exp 2–3 by model type (Sarvam vs general; within Sarvam: scale and from-scratch vs post-trained) | Does Indic training escape the failure? |
| **Exp 5** | Mitigation | PT / PRE / POST on a representative subset (few models × languages), **plus** a transliteration/script-normalization mitigation | Can inference-time strategies recover performance? Does Sarvam's native training make them redundant? |

### Design principle: both outcomes are results

Exp 4 has no failure branch. If Sarvam **still shows** the mismatch, that is the *strongest* finding — even a from-scratch Indic model with a custom tokenizer and code-mixed training copies Indic tokens into English-only parameters, so the failure is structural to the language–execution interface, not a training-data gap (confirming MLCL's thesis in the hardest test case). If Sarvam **avoids** it, that shows the failure is trainable-away and quantifies how much specialization buys. Either way the measurement is the contribution. The only genuine kill-switch is Exp 0 failing (Sarvam can't tool-call at all) — and even that would be a reportable finding.

### Feasibility guardrails

- Run the full grid on all 8 models, but restrict the *extra* axes (Romanization in full, mitigation) to the subset of models/languages where they are most informative, as MLCL restricted mitigation to a few representative models.
- The binding constraint is native-speaker verification time, not compute. Budget human effort first; secure verifiers for all 5 languages before scaling data generation.

---

## 9. Limitations to state in the paper

- **Organic code-mixing (Hinglish/Tanglish) is future work.** We study native-script and Romanized input as the two dominant real-world modes; faithful organic code-mix construction requires large-scale native-speaker elicitation, which we leave to future work.
- **Transliteration quality** — Romanized queries are tool-generated with a native-speaker spot-check; we validate the transliteration sample. (With code-mixing out of scope, the Romanization axis carries the real-world-input story, so this check matters.)
- **One Indic-native family** — conclusions are scoped to the Sarvam family; generalization to other Indic-native models is future work.
- **Language coverage** — 5 languages chosen for controlled contrasts, not exhaustive coverage of Indic families/scripts.
- **Single-turn only** — inherited from the BFCL `multiple` subset.
- **English-only execution assumption** — follows MLCL and current tool-calling convention; we study behavior under this convention, not advocate for it.

---

## 10. One-line framing for the introduction

> "MLCL and its Arabic counterpart establish parameter-value-language-mismatch for typologically unrelated languages, but their language choices confound script, family, and resource. We use the internal structure of the Indic language space to disentangle these factors, introduce Romanized input as a dominant real-world mode prior work omits, and test whether Indic-native models (Sarvam) escape the failure — finding [result]."

---

## 11. Quick-reference decision table

| Decision | Choice |
|---|---|
| Languages | Hindi, Marathi, Bengali, Tamil, Santali/Bodo |
| Controlled contrasts | Hindi–Marathi (resource), Hindi–Bengali (script), Tamil (family), Santali (low-resource) |
| General models | GPT-5, Gemini 2.5, DeepSeek V3.2, Qwen3, Llama |
| Indic-native models | Sarvam-105B, Sarvam-30B, Sarvam-M |
| Inherited grid | NT/PAR/FT × NO/PARA/SYNO |
| New axis | Romanization (native vs Latin script), via IndicXlit + spot-check |
| Error taxonomy | MLCL's 8-category severity scheme |
| Base data | BFCL_v4_multiple.json (single-turn) |
| Experiments | Exp 0 smoke test → Exp 1 replication → Exp 2 core → Exp 3 Romanization → Exp 4 specialization → Exp 5 mitigation |
| Future work | Organic code-mixing; additional Indic-native model families |
