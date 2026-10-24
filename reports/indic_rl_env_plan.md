# Indic agent RL environment: concrete plan and novelty check (2026-10-24)

## 1. Novelty check (web search, 2026-10-24)

| Area | Prior work | Status |
|---|---|---|
| RL for English text-to-SQL (multi-turn, execution feedback, step rewards) | SkyRL-SQL; SQL-Trail (ACL 2026); MTIR-SQL (arXiv 2510.25510); Progress-SQL (arXiv 2606.06825); Reasoning-SQL (arXiv 2503.23157) | **Crowded.** The RL method itself is not our contribution |
| Multilingual RL text-to-SQL | Contrastive rewards on MultiSpider, 7 languages, single-turn (arXiv 2510.13827) | One paper. **No Indic, no multi-turn** |
| Indic text-to-SQL | IndicDB (PI's group, arXiv 2604.13686): 15,617 tasks; EN, Hinglish, HI, BN, TA, TE, MR; about 9% drop EN -> Indic; prompting only | **No RL / training** |
| RL against argument-language copying in tool calling | Chauhan et al. 2026 (European, Latin-script languages only) | No Indic, no script study |
| Cross-language / cross-script transfer of agentic RL | Only RL-for-translation work (low-resource MT) | **Nothing found for agents or tools** |
| Indic RL environments | indic-ifeval (third-party Prime RL env, instruction following) | Only one, not agentic |

**Gap:** no RL environment, and no study, for Indic **agents** (SQL, tools), and no work on whether RL training transfers across Indic languages and scripts (native vs Romanized / Hinglish).

## 2. What we build

**IndicAgentGym** (working name), with two verifiable, multi-turn environments:

1. **SQL environment (IndicDB).**
   - Tools: `list_tables`, `describe_table`, `run_sql` (returns rows or an error), `submit`.
   - Step rewards:
     - query runs without error: +0.1;
     - touches the correct tables and joins: +0.2;
     - submitted result equals the gold result: +1;
     - SQL error or empty / looping turns: small negative;
     - turn budget enforced.
   - Train/test split **by database**: held-out databases are never seen in training.
2. **Tool-calling environment (LIPI / BFCL multiple).**
   - Single call, AST-checked.
   - Rewards: right function, right argument names, right values.
   - **Language-conformance penalty:** Indic text in an English-only argument is penalised.
   - Conditions: native script, Romanized, partly translated.
   - LIPI's human-verified 200 per condition = **eval only**. Training tasks come from a larger translated tool set, or a train split of BFCL-style tasks.

## 3. Research questions (what makes it publishable)

- **RQ1 Transfer.** Train on {English, Hindi native, Hinglish/Romanized}, test on all of {EN, HI, GU/BN/MR, TA/TE, Romanized}. Does RL in one language or script transfer, and does it reach the Dravidian family?
- **RQ2 Step vs outcome rewards.** Do step rewards help more in Indic languages, where outcome rewards are sparse?
- **RQ3 Copying fix.** Does the language-conformance reward remove argument copying without hurting understanding? Compare with prompting and SFT.
- **RQ4 Script.** Is Romanized input easier or harder to learn from than native script?

## 4. Steps

| Week | Work |
|---|---|
| 1 | Get IndicDB databases and splits from the PI's group. Fix the database-level train/test split. Finish the Romanized LIPI conditions. |
| 1–2 | Build both environments (verifiers / OpenEnv-style API). Unit-test the rewards against gold queries and calls. |
| 2–3 | Baselines: prompting and SFT on 3 small models (e.g. Qwen3-4B/8B, Gemma3-4B). |
| 3–5 | GRPO runs for the RQ1 transfer matrix, then the RQ2/RQ3 ablations (Sharanga H200s). |
| 6 | Analysis and paper. |

## 5. Usefulness and risks

- **Useful:** Indian government data portals (NDAP) and Indic voice/chat agents need exactly this. There is no public Indic agent training environment today.
- **Venues:** ACL/EMNLP main if the RQ1–RQ3 findings are clear; NeurIPS Datasets & Benchmarks for the environment itself.
- **Risks:**
  - Compute for multi-turn GRPO.
  - IndicDB data access (internal, PI's group).
  - "Just another RL-for-SQL" criticism. Answer it by putting the transfer and script findings first.
  - AI4Bharat may release similar work. Move fast.

## Sources

- https://arxiv.org/abs/2604.13686 (IndicDB)
- https://arxiv.org/pdf/2510.13827 (multilingual contrastive-reward GRPO text-to-SQL)
- https://novasky-ai.notion.site/skyrl-sql (SkyRL-SQL)
- https://preview.aclanthology.org/ingest-acl/2026.acl-long.1677/ (SQL-Trail)
- https://arxiv.org/html/2510.25510v1 (MTIR-SQL)
- https://arxiv.org/pdf/2606.06825 (Progress-SQL)
- https://arxiv.org/pdf/2503.23157 (Reasoning-SQL)
- https://arxiv.org/abs/2608.11715 (Chauhan et al.)
