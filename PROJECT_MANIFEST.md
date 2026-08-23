# Project Manifest

What every file and folder in this repo is for. Keep this up to date as the
project evolves -- when you add, remove, or repurpose something, update the
entry here in the same change.

## Project-specific

| Path | Purpose |
|---|---|
| `Indic_ToolCalling_Project_Plan.md` | The governing project plan: languages, models, conditions, error taxonomy, experiment sequence (Exp 0-5). Read this first. |
| `PROJECT_MANIFEST.md` | This file. |
| `data/` | Per-language, per-condition question sets and ground truth (see `data/README.md`). |
| `translation/` | Translation, Romanization, and QA pipeline scripts (see `translation/README.md`). |
| `experiments/` | Exp 0-5 driver scripts (see `experiments/README.md`). |
| `analysis/` | Error taxonomy classification and result analysis (see `analysis/README.md`). |
| `results/` | Generation/evaluation outputs organized per experiment (see `results/README.md`). |

## BFCL harness (vendored dependency, not our code)

| Path | Purpose |
|---|---|
| `bfcl_eval/` | The BFCL v4 evaluation harness itself -- model handlers, AST-based correctness checker, base English datasets (including `bfcl_eval/data/BFCL_v4_multiple.json`, our source dataset per Section 7 of the plan), and the `bfcl generate`/`bfcl evaluate` CLI. Treated as infrastructure we run on top of, not project output -- avoid editing it directly except to register new test categories (`bfcl_eval/constants/category_mapping.py`) or add a model handler (e.g. for Sarvam, under `bfcl_eval/model_handler/`). |
| `openfunctions_evaluation.py`, `pyproject.toml`, `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `LOG_GUIDE.md`, `SUPPORTED_MODELS.md`, `TEST_CATEGORIES.md`, `architecture_diagram.png` | Upstream BFCL project files, unmodified. |
| `.gitignore` | Excludes `.env` (API keys), Python caches, `.DS_Store`, `.file_locks/` (BFCL runtime lock files), and `bfcl_eval.egg-info/` (build artifact). |

## History

The first commit on `main` was a full snapshot of an earlier pilot project
(Hindi/Tamil only, `simple_python` category, single model gpt-4o-mini,
MLCL's PT/PRE/POST baselines). That work is preserved in full on the
`archive/pilot-hindi-tamil-simple-python` branch, including a validated
deterministic type-casting fix and a documented negative result (a
number-matching repair strategy that was found to regress accuracy and was
diagnosed in detail) -- both worth referencing when designing Exp 5. `main`
was then cleaned to the structure above for the 5-language, 8-model project
described in `Indic_ToolCalling_Project_Plan.md`.
