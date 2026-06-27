---
license: cc-by-4.0
language:
- tr
pretty_name: TR-DataAnalystBench
size_categories:
- n<1K
task_categories:
- question-answering
- table-question-answering
tags:
- turkish
- data-analysis
- tables
- charts
- reasoning
- benchmark
- evaluation
configs:
- config_name: synthetic_v01
  data_files:
  - split: train
    path: data/synthetic_v01/train.jsonl
  - split: validation
    path: data/synthetic_v01/validation.jsonl
  - split: test
    path: data/synthetic_v01/test.jsonl
- config_name: synthetic_v02
  data_files:
  - split: train
    path: data/synthetic_v02/train.jsonl
  - split: validation
    path: data/synthetic_v02/validation.jsonl
  - split: test
    path: data/synthetic_v02/test.jsonl
- config_name: real_pilot
  data_files:
  - split: train
    path: data/real_pilot/train.jsonl
  - split: validation
    path: data/real_pilot/validation.jsonl
  - split: test
    path: data/real_pilot/test.jsonl
---

# TR-DataAnalystBench

A Turkish-language benchmark for evaluating whether language models can perform
**data-analyst style reasoning over tables and charts**: reading a value,
finding the maximum/minimum, comparing two years, computing an average or a
(signed) percentage change, ranking, summarizing a trend, and — importantly —
**abstaining when the data does not contain the answer**.

Gold answers are computed and verified with Python (not produced by a language
model), so the benchmark is reproducible and auditable. An automatic evaluator
scores numeric (tolerance), categorical (trend), and abstention tasks.

## Why this benchmark

Many models are fluent in Turkish yet still fail at numerical reasoning, table
understanding, and chart interpretation. TR-DataAnalystBench isolates those
abilities with verifiable gold answers and a transparent scoring contract.

## The suite (728 examples, three tiers)

| Tier | Examples | Tasks | What it targets |
|---|---:|---:|---|
| `synthetic_v01` | 300 | 5 | Easy/medium baseline: single-series tables, basic lookups/compare/percentage |
| `synthetic_v02` | 320 | 8 | Harder & discriminative: multi-series tables, distractor columns, average / nth-highest / cross-series, unanswerable questions, real `hard` labels |
| `real_pilot` | 108 | 7 | **Real Türkiye open data** (population, GDP, consumer inflation, CO₂) with verified gold |

Splits are table-disjoint (the questions sharing a table/chart never cross a
split boundary).

## Task types

| Task | Answer | Scoring |
|---|---|---|
| `value_lookup` | a value | numeric, ±2% tolerance |
| `max_min` / `nth_highest` | an extreme / ranked value | numeric |
| `comparison` | absolute difference between two years | numeric |
| `cross_series_diff` | difference between two series in a year | numeric |
| `average` | mean of a series | numeric |
| `percentage_change` | **signed** percent change | numeric, ±2 percentage points |
| `trend_summary` | `artış` / `azalış` / `dalgalı` | categorical label match |
| `unanswerable` | abstention (`veri yok`) | correct iff the model declines |

Input formats: `table_only`, `chart_only` (chart image, no table — prevents
table leakage), and `table_and_chart`.

## Data fields

Each example is a JSON object with, among others:

- `id`, `dataset_version`, `language` (`tr`), `domain`, `split`
- `question_type`, `difficulty`, `input_format`, `chart_type`, `chart_path`
- `table`: `{ "columns": [...], "rows": [[...], ...] }`
- `question`, `answer` (human-readable gold)
- `answer_type`: `numeric` | `numeric_with_label` | `text` (trend) | `abstention`
- `numeric_answer` (or `null`), `trend_class` (for trends), `target_column`, `unit`
- `calculation` (how the gold was derived)
- `real_pilot` only: `source_name`, `source_url`, `license`, `country`

## How to evaluate a model

1. Build prompts from the dataset (a prompt for each example; for `chart_only`
   the model is given the chart image, not the table).
2. Collect answers into a CSV with columns `id`, `predicted_numeric_answer`,
   and `prediction_text` (used for trend words and `veri yok`).
3. Score with the repository's evaluator:

```bash
python scripts/08_evaluate_predictions_file.py \
    --dataset data/processed/real_pilot.jsonl \
    --predictions your_predictions.csv --split test
```

The evaluator reports overall accuracy plus per-kind accuracy (numeric
tolerance, trend label, abstention) broken down by task, input format, and
domain. Running it on the provided oracle predictions yields 100%, confirming
the scoring pipeline.

## Baselines

| System | Tier | Accuracy | Notes |
|---|---|---:|---|
| Oracle (gold) | all | 100% | scoring sanity check |
| Noisy baseline | synthetic_v01 | ~72% | programmatic perturbation reference |
| Noisy baseline | synthetic_v02 | ~66% | abstention ~45% (catches hallucination) |
| ChatGPT (manual, 12-item sample) | real_pilot | ~92% | by-hand run; perfect on numeric & abstention, missed one borderline trend |

The ChatGPT number is a small, manually collected illustration, not a full
leaderboard entry. The repository includes a free **manual evaluation kit**
(`scripts/16_create_manual_kit.py`) so anyone can reproduce/extend it without
an API.

## Limitations

- The synthetic tiers are templated; charts carry printed data labels, so
  `chart_only` partly measures label OCR rather than pure visual estimation.
- `real_pilot` is a proof-of-concept (108 examples, 4 indicators); it is meant
  to grow.
- With a few hundred examples, overall rankings are stable but fine-grained
  per-subgroup numbers carry meaningful confidence intervals.
- Trends are labeled by a deterministic rule (monotonic, or net change ≥5% with
  a dominant direction, else `dalgalı`); some borderline series are debatable.

## Licensing and provenance

- Datasets: **CC-BY-4.0**. `real_pilot` is derived from World Bank Open Data and
  CDIAC emissions data (ODC-PDDL-1.0 / CC-BY-4.0); per-source provenance and
  licenses are in `data/sources_real/provenance.json`. Synthetic tiers are
  original work.
- Code: MIT (see `LICENSE`).

## Citation

```bibtex
@misc{harac2026trdataanalystbench,
  title        = {TR-DataAnalystBench: A Turkish Table and Chart Reasoning Benchmark},
  author       = {Hara\c{c}, Ali Alp},
  year         = {2026},
  howpublished = {\url{https://github.com/alialp5959/TR-DataAnalystBench}}
}
```
