# LIPI: Tool Calling in Indian Languages

LIPI tests whether open-source LLM agents can call tools when the user writes in Hindi, Gujarati or Tamil instead of English.

We took the 200 questions in the `multiple` category of the [Berkeley Function Calling Leaderboard (BFCL)](https://gorilla.cs.berkeley.edu/leaderboard.html) v4, where each question comes with several tools to choose from. We translated them into Hindi, Gujarati and Tamil with machine translation, and two native speakers checked every question over two review rounds. The tools, the expected answers and BFCL's grader are unchanged. Only the language of the user's question changes.

**Result:** across 14 open-source models (0.5B to 32B), average accuracy falls from **87%** in English to **54%** in Hindi, **53%** in Gujarati and **48%** in Tamil. Every model does worse in every Indian language.

## Results

Percentage of the 200 questions each model answered correctly (right tool, every argument right). Models are ranked by their total across the three Indian languages.

| # | Model | English | Hindi | Gujarati | Tamil |
|---|---|---:|---:|---:|---:|
| 1 | Gemma 3 12B | 94.0 | 77.0 | 81.5 | 82.5 |
| 2 | Qwen3 8B | 96.0 | 77.5 | 78.5 | 82.5 |
| 3 | Qwen3 32B | 96.5 | 75.0 | 82.0 | 79.5 |
| 4 | Gemma 3 27B | 92.5 | 66.5 | 76.0 | 72.0 |
| 5 | Qwen3 1.7B | 92.5 | 74.5 | 69.0 | 60.0 |
| 6 | Gemma 3 4B | 87.5 | 59.0 | 62.0 | 64.5 |
| 7 | Hammer 2.1 7B | 92.5 | 66.0 | 63.5 | 44.0 |
| 8 | Falcon3 10B | 92.5 | 64.0 | 56.5 | 42.0 |
| 9 | Llama 3.2 3B | 92.5 | 40.5 | 47.0 | 41.5 |
| 10 | Falcon3 7B | 89.0 | 52.0 | 40.5 | 33.5 |
| 11 | Llama 3.1 8B | 53.5 | 28.0 | 38.5 | 36.0 |
| 12 | Hammer 2.1 1.5B | 92.0 | 41.5 | 32.5 | 25.0 |
| 13 | Hammer 2.1 0.5B | 80.5 | 16.5 | 8.0 | 8.0 |
| 14 | Falcon3 3B | 68.5 | 13.5 | 6.5 | 7.5 |
| | **Average of 14** | **87.1** | **53.7** | **53.0** | **48.5** |

Per-model outputs are in `result/` and BFCL scores are in `score/`.

## What's in this repo

| Path | Contents |
|---|---|
| `bfcl_eval/data/BFCL_v4_multiple_{hi,gu,ta}.json` | The translated question sets, registered as BFCL test categories `multiple_hi`, `multiple_gu`, `multiple_ta` |
| `bfcl_eval/data/possible_answer/` | Ground truth (identical to English BFCL) |
| `data/translations/` | Raw machine translations |
| `data/review_sheets/`, `data/human_review/` | Blank review templates and the native-speaker review sheets for both rounds |
| `data/reviews/` | Review decisions, final resolved translations and error-taxonomy outputs |
| `data/perturbations/` | English paraphrase (`multiple_para`) and synonym-swap (`multiple_syno`) control sets |
| `translation/` | Scripts for translation, review-sheet generation, resolving reviews, building test categories and error analysis |
| `result/`, `score/` | Model outputs and scores for every model and language |

## Running the evaluation

This repo is a fork of BFCL, so setup and the CLI are the same as upstream. See [BFCL_README.md](BFCL_README.md) for installation and backend options.

```bash
pip install -e .

# generate answers for English plus the three Indian languages
bfcl generate --model Qwen/Qwen3-8B-FC \
  --test-category multiple,multiple_hi,multiple_gu,multiple_ta \
  --backend vllm --num-gpus 1

# score them
bfcl evaluate --model Qwen/Qwen3-8B-FC \
  --test-category multiple,multiple_hi,multiple_gu,multiple_ta
```

## Team

- Bhuvan Arora: test sets, experiments and analysis
- Dhayanidhi Purushothaman and S Rohan: Tamil review
- Jayant Kapoor and Anshul Gupta: Hindi and English review
- Dhruv Kunvarani and Samarth Patel: Gujarati review
- Prof. Dhruv Kumar (BITS Pilani): faculty advisor

## Acknowledgements

Built on the [Berkeley Function Calling Leaderboard](https://github.com/ShishirPatil/gorilla/tree/main/berkeley-function-call-leaderboard) (Patil et al., ICML 2025). Upstream BFCL code keeps its original license.
