# Project Manifest

What every file and folder in this repo is for. Keep this up to date as the
project evolves -- when you add, remove, or repurpose something, update the
entry here in the same change.

## Project-specific

| Path | Purpose |
|---|---|
| `Indic_ToolCalling_Project_Plan.md` | The governing project plan: languages, models, conditions, error taxonomy, experiment sequence (Exp 0-5). Read this first. |
| `PROJECT_MANIFEST.md` | This file. |
| `PROGRESS.md` | Living status doc -- current phase, model/experiment readiness, next steps. Check this for "where are we right now." |
| `LOG.md` | Append-only chronological record of actions taken, commands run, bugs found, decisions made. Check this for "what happened and why." |
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

## Data provenance policy

Applies to every generated dataset in this project (perturbations,
translations, Romanization, model outputs -- not just one file). The goal:
for any single data point, always be able to answer "is this exactly what
the model produced, or did we touch it, and if so how and why" -- required
for the paper to honestly report what's raw vs. corrected.

Three separate, append-only layers, never merged in place:

1. **Raw generation** -- exactly what the model produced. Written once,
   never edited after the fact. If regenerated, that's a new row/run, not
   an overwrite of the old one.
2. **QA findings** -- a separate file recording what an automated or human
   check found, referencing back to the raw row by id. Never modifies the
   raw file.
3. **Corrections** -- created only if a flagged row is actually fixed.
   Lives in its own file: original text, corrected text, who/what corrected
   it, why, when. Not an in-place overwrite of the raw or QA files.

Anything actually fed into an experiment (a `bfcl_eval/data/BFCL_v4_*.json`
category file) is a derived export built by joining these three layers at
export time -- never hand-edited, always regeneratable, always traceable
back to which layer each value came from.

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
