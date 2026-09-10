# translation/

Translation, Romanization, and QA pipeline scripts for producing the
5-language dataset from the English BFCL source.

Covers: query translation (PAR/FT), Romanization (native script -> Latin
script via a transliteration tool per Section 5 of
`Indic_ToolCalling_Project_Plan.md`), and QA (back-translation + judge model,
extending the approach validated in the archived pilot -- see the
`archive/pilot-hindi-tamil-simple-python` branch for that prior version).

## Scripts

- `generate_perturbations.py` -- generates PARA/SYNO English perturbations
  of the 200 `BFCL_v4_multiple.json` base queries via `google/gemini-3.7-flash`
  (OpenRouter), using MLCL's verbatim prompts. Writes to
  `data/perturbations/en_multiple_perturbations.jsonl` (raw, immutable --
  see the data provenance policy in `PROJECT_MANIFEST.md`).
- `check_perturbation_number_drift.py` -- read-only QA pass over that file;
  order-independent number-set check (source vs. perturbed text), flags
  genuine drops/additions/substitutions, not reordering. Writes to a
  separate `..._qa.jsonl` file, never touches the raw data.
