# TR-DataAnalystBench

TR-DataAnalystBench is a Turkish table and chart reasoning benchmark for evaluating whether language models can correctly analyze structured data.

The benchmark focuses on realistic data analysis tasks such as reading tables, interpreting charts, comparing values, calculating percentage changes, and producing short factual trend summaries.

## Motivation

Many language models can generate fluent Turkish text, but they may still fail at numerical reasoning, table understanding, chart interpretation, and factual data analysis.

TR-DataAnalystBench aims to provide a reproducible Turkish benchmark for evaluating these abilities. The long-term goal is a dataset and evaluation pipeline that can test Turkish-capable LLMs and multimodal models on data-analyst style tasks.

## Current Status

The current benchmark version is **`synthetic_v01`**: a fully synthetic, programmatically verified dataset of **300 examples**. Gold answers are computed with Python (not guessed by a language model), which makes the benchmark reproducible and auditable.

The repository also keeps the earlier 50-example `pilot` (scripts `01`–`03`) for reference.

### What's in the pipeline

* Synthetic table + chart generation
* Turkish question generation across 5 task types
* Python-verified gold answers
* Schema/consistency validation
* Automatic scoring for **all 300 examples** (240 numeric + 60 trend)
* An external evaluator that scores a prediction CSV
* Prompt packs and prediction templates for running a model
* Oracle and noisy baselines as a scoring sanity check

## Dataset: synthetic_v01

| Property | Value |
| --- | ---: |
| Total examples | 300 |
| Numeric examples (auto-scored, tolerance) | 240 |
| Trend examples (auto-scored, categorical) | 60 |
| Domains | 10 |
| Task types | 5 |
| Input formats | 3 |
| Unique charts | 60 |

### Domains

transportation, economy, education, tourism, energy, health, environment, sports, municipality, agriculture

### Task types

| Task type | Answer | Scoring |
| --- | --- | --- |
| `value_lookup` | a single value | numeric, ±2% tolerance |
| `max_min` | the max/min value | numeric, ±2% tolerance |
| `comparison` | absolute difference between two years | numeric, ±2% tolerance |
| `percentage_change` | **signed** percent change (positive = increase, negative = decrease) | numeric, ±2 percentage points |
| `trend_summary` | trend as one word (`artış` / `azalış` / `dalgalı`) | categorical label match |

> **Note on `percentage_change`:** the gold answer is *signed*. The question explicitly asks for a positive value for an increase and a negative value for a decrease, so the evaluator measures direction as well as magnitude.

> **Note on `trend_summary`:** these were previously free text and unscored. They are now framed as a 3-class categorization (`increasing` / `decreasing` / `mixed`, stored in `trend_class`) so the full benchmark is automatically scorable.

### Input formats

| Format | Model is given |
| --- | --- |
| `table_only` | the table (no chart) |
| `chart_only` | only the chart image (no table — prevents table leakage) |
| `table_and_chart` | both |

### Splits

| Split | Count |
| --- | ---: |
| train | 240 |
| validation | 30 |
| test | 30 |

Splits are table-disjoint: the 5 questions sharing a table/chart never cross a split boundary.

## Repository Structure

```text
TR-DataAnalystBench/
├── charts/
│   ├── pilot/
│   └── synthetic_v01/
├── data/
│   ├── exports/            # previews, stats, prompt packs, templates, evaluations
│   └── processed/
│       ├── pilot.jsonl
│       └── synthetic_v01.jsonl
├── docs/
│   ├── pilot_report.md
│   └── synthetic_v01_report.md
├── scripts/
│   ├── 01_generate_synthetic_pilot.py
│   ├── 02_validate_pilot.py
│   ├── 03_analyze_pilot.py
│   ├── 04_generate_synthetic_v01.py
│   ├── 05_validate_synthetic_v01.py
│   ├── 06_analyze_synthetic_v01.py
│   ├── 07_score_numeric_answers.py        # oracle / noisy baselines (full benchmark)
│   ├── 08_evaluate_predictions_file.py     # external evaluator (numeric + trend)
│   ├── 09_create_prediction_templates.py
│   └── 10_create_prompt_pack.py
├── requirements.txt
└── README.md
```

## Setup

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\activate
# Linux/macOS:        source .venv/bin/activate
pip install -r requirements.txt
```

## Reproduce the benchmark

Run the synthetic_v01 pipeline in order:

```bash
python scripts/04_generate_synthetic_v01.py     # dataset + charts + stats
python scripts/05_validate_synthetic_v01.py     # schema / consistency checks
python scripts/06_analyze_synthetic_v01.py      # docs/synthetic_v01_report.md
python scripts/07_score_numeric_answers.py      # oracle / noisy baselines
python scripts/09_create_prediction_templates.py
python scripts/10_create_prompt_pack.py
```

The generator uses a fixed random seed, so the dataset is deterministic.

## Evaluate a model

1. Build prompts for the model with `scripts/10_create_prompt_pack.py`. Use the
   `*_full` packs to cover the whole benchmark (numeric + trend), or the
   `*_numeric` packs for numeric-only.
2. Collect the model's answers into a CSV with at least the columns:
   * `id`
   * `predicted_numeric_answer` (for numeric tasks)
   * `prediction_text` (used for `trend_summary`; should contain `artış`, `azalış`, or `dalgalı`)

   A ready-to-fill template is produced by `scripts/09_create_prediction_templates.py`
   (`synthetic_v01_prediction_template_all_full.csv`).
3. Score it:

```bash
python scripts/08_evaluate_predictions_file.py \
    --predictions path/to/predictions.csv \
    --prediction-name my_model \
    --split test
```

This writes a details CSV, a JSON report, and a Markdown report under
`data/exports/evaluations/`, including overall accuracy, numeric tolerance
accuracy, and trend label accuracy, broken down by question type, input format,
and domain.

### Sanity check

Running the evaluator on the generated oracle predictions yields 100% overall
accuracy, confirming the scoring pipeline is correct:

```bash
python scripts/08_evaluate_predictions_file.py \
    --predictions data/exports/synthetic_v01_oracle_predictions.csv \
    --prediction-name oracle_full
```

## Roadmap

Done so far:

* [x] Synthetic table + chart generation
* [x] Python-verified gold answers
* [x] Chart-only inputs without table leakage
* [x] Automatic numeric scoring with tolerance
* [x] Automatic scoring for trend (categorical) answers — full benchmark is now scorable
* [x] Signed percentage-change so direction is evaluated
* [x] External prediction-file evaluator

Planned next:

1. Increase difficulty and discrimination (label-free chart variants, multi-series
   tables, distractor columns, harder templates) so the benchmark separates models.
2. Add a real multimodal evaluation harness that passes chart images to a model.
3. Run baseline model evaluations and publish a comparison table.
4. Move from synthetic tables to real Turkish open-data sources (e.g. TÜİK).
5. Prepare a Hugging Face dataset release and a public benchmark card.

## Project Goal

The goal is not just a dataset, but a reproducible Turkish benchmark for evaluating the data-analysis abilities of language models: dataset generation, gold verification, chart generation, quality control, evaluation scripts, documentation, and baseline comparisons.

## License

License will be decided before the public dataset release.
</content>
</invoke>
