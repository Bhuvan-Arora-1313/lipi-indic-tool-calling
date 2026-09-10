# data/

Per-language, per-condition question sets and ground truth for the 5-language
grid (Hindi, Marathi, Bengali, Tamil, Santali/Bodo), derived from
`bfcl_eval/data/BFCL_v4_multiple.json`.

Holds the outputs of the NT/PAR/FT x NO/PARA/SYNO grid (Section 5/7/8 of
`Indic_ToolCalling_Project_Plan.md`) and the Romanized variants (Exp 3),
before they're registered as BFCL test categories and copied into
`bfcl_eval/data/`.

## perturbations/

English-only PARA/SYNO perturbations of the 200 `BFCL_v4_multiple.json`
base queries (see `translation/README.md` for the generation script).
Raw data is immutable once written -- see the data provenance policy in
`PROJECT_MANIFEST.md` for how QA findings and any future corrections are
layered on top without ever overwriting it.

- `en_multiple_perturbations.jsonl` -- raw generation output. 600 rows
  (200 each of NO/PARA/SYNO).
- `en_multiple_perturbations_qa.jsonl` -- automated number-drift QA
  findings, one row per PARA/SYNO entry, referencing back to it by
  `base_id` + `perturbation_type`.
