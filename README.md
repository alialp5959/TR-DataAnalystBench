# TR-DataAnalystBench

**A Turkish table & chart reasoning benchmark for language models — with Python-verified gold answers and an automatic evaluator.**

![validate](https://github.com/alialp5959/TR-DataAnalystBench/actions/workflows/validate.yml/badge.svg)
&nbsp;![license](https://img.shields.io/badge/code-MIT-blue)
&nbsp;![data](https://img.shields.io/badge/data-CC--BY--4.0-green)
&nbsp;![language](https://img.shields.io/badge/language-Turkish-red)

Can a Turkish-capable LLM actually *do data analysis* — read a value from a
table, pull a number off a chart, find the maximum, compute an average or a
percentage change, summarize a trend, and **say "I can't" when the data doesn't
contain the answer**? TR-DataAnalystBench measures exactly that.

Gold answers are **computed and verified with Python**, not guessed by a model,
so the benchmark is reproducible and auditable. A single evaluator scores three
kinds of answer — numeric (with tolerance), categorical (trend), and abstention.

## Highlights

- **968 examples** across **four tiers** of increasing realism and difficulty.
- **Genuine chart reading:** a label-free tier where values must be read off the axes/gridlines, not OCR'd from printed labels.
- **Hallucination test:** `unanswerable` questions where inventing a number is penalized.
- **Real-data tier** built from licensed Türkiye open data (World Bank, CDIAC) with full provenance.
- **Automatic evaluator** with task-aware tolerances + **oracle/noisy baselines** + a **free, no-API manual evaluation kit**.
- **CI** revalidates every gold answer on each push.

## The benchmark suite

| Tier | Examples | Tasks | Domains | Focus |
|---|---:|---:|---:|---|
| `synthetic_v01` | 300 | 5 | 10 | Easy/medium baseline (single-series tables) |
| `synthetic_v02` | 320 | 8 | 10 | Harder & discriminative (multi-series, distractors, unanswerable, `hard`) |
| `real_pilot` | 108 | 7 | 3 | **Real Türkiye open data** (population, GDP, inflation, CO₂) |
| `chart_read_v01` | 240 | 5 | 10 | **Label-free chart reading** (estimate from axes/gridlines, not OCR) |
| **Total** | **968** | | | |

## Baselines

| System | Tier | Accuracy | Notes |
|---|---|---:|---|
| Oracle (gold) | all | 100% | scoring sanity check |
| Noisy baseline | synthetic_v01 | ~72% | programmatic reference |
| Noisy baseline | synthetic_v02 | ~66% | abstention ~45% (catches hallucination) |
| ChatGPT (manual, 12-item) | real_pilot | ~92% | by-hand run; perfect on numeric & abstention |

> The ChatGPT figure is a small, manually collected illustration — reproduce or
> extend it with the no-API kit (`scripts/16_create_manual_kit.py`).

## Use on Hugging Face

Build a self-contained, uploadable dataset folder (one config per tier, three
splits each, charts included):

```bash
python scripts/18_build_release.py
huggingface-cli upload <user>/TR-DataAnalystBench release . --repo-type dataset
```

The dataset card is in [`docs/hf_dataset_card.md`](docs/hf_dataset_card.md).
Code is MIT-licensed; the datasets are CC-BY-4.0 (see [`LICENSE`](LICENSE) and
[`CITATION.cff`](CITATION.cff)).

## Motivation

Many models are fluent in Turkish yet still fail at numerical reasoning, table
understanding, and chart interpretation. TR-DataAnalystBench isolates those
abilities with verifiable gold answers and a transparent scoring contract. The
repository also keeps the earlier 50-example `pilot` (scripts `01`–`03`) for
reference.

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

## Dataset: synthetic_v02 (harder tier)

`synthetic_v02` keeps the same schema and scoring contract as v01 but is designed to be discriminative rather than saturated.

| Property | Value |
| --- | ---: |
| Total examples | 320 |
| Task types | 8 |
| Difficulty | 40 easy / 160 medium / 120 hard |
| Tables | multi-series (Year + two metrics) |

What makes it harder:

* **Multi-series tables** — every table has two metric columns, so the model must select the correct series; the other column is a distractor.
* **Multi-step tasks** — in addition to `value_lookup`, `comparison`, and `percentage_change`, it adds:
  * `average` — mean of a series across all years
  * `nth_highest` — the 2nd/3rd highest value of a series
  * `cross_series_diff` — difference between the two series in a given year
* **Unanswerable questions** (`unanswerable`) — ask about a year or metric not present in the data. The gold answer is an abstention (`veri yok`); a model that invents a number is marked wrong. This directly measures hallucination resistance. Every prompt carries a global "if it can't be answered, say `veri yok`" instruction, so unanswerable items are indistinguishable from answerable ones.
* **Trend** (`trend_summary`) — categorical, as in v01.

Scoring kinds: numeric (tolerance), trend (categorical label), and abstention. The evaluator reports overall accuracy plus per-kind accuracy.

```bash
python scripts/11_generate_synthetic_v02.py     # dataset + multi-series charts
python scripts/12_validate_synthetic_v02.py     # schema + recomputed-gold checks
python scripts/13_create_v02_eval_assets.py     # prompt packs, template, baselines

# sanity check: oracle scores 100% across all 320 examples
python scripts/08_evaluate_predictions_file.py \
    --dataset data/processed/synthetic_v02.jsonl \
    --predictions data/exports/synthetic_v02_oracle_predictions.csv \
    --prediction-name v02_oracle
```

## Dataset: real_pilot (real Türkiye open data)

A **real-data** tier built from redistributable open data for Türkiye, so the questions are grounded in real figures rather than synthetic ones.

* **108 examples** from 4 indicators across 3 domains: population (demografi), GDP and consumer inflation (ekonomi), and fossil-fuel CO₂ emissions (çevre).
* Sources are GitHub-hosted World Bank / CDIAC datasets (via the datahub `datasets` mirrors). Licenses: ODC-PDDL-1.0 and CC-BY-4.0 (redistributable). Provenance and license per source are in `data/sources_real/provenance.json`, and the raw snapshots are committed for reproducibility.
* Gold answers are computed with Python from the real numbers, so the tier stays fully auto-scorable with the same evaluator. Each example carries `source_name`, `source_url`, and `license` for transparency.

```bash
python scripts/14_fetch_real_sources.py     # cache real sources + provenance (needs network)
python scripts/15_generate_real_pilot.py    # build real_pilot from the cache
python scripts/17_validate_real_pilot.py    # schema + recomputed-gold + license checks
python scripts/08_evaluate_predictions_file.py \
    --dataset data/processed/real_pilot.jsonl \
    --predictions data/exports/real_pilot_oracle_predictions.csv --prediction-name real_pilot_oracle
```

It is designed to scale by adding indicators to the source list in `scripts/14_fetch_real_sources.py` (any GitHub-hosted, redistributable dataset with yearly Türkiye values).

## Free manual model evaluation

You do not need an API to get a first real model score. `scripts/16_create_manual_kit.py` produces a paste-friendly worksheet plus an empty prediction template for any split:

```bash
python scripts/16_create_manual_kit.py --dataset data/processed/real_pilot.jsonl --split test
```

Paste each prompt into a fresh chat (upload the chart image when one is referenced), write the model's answer into the template CSV, then score it with `scripts/08_evaluate_predictions_file.py`.

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
│   ├── 10_create_prompt_pack.py
│   ├── 11_generate_synthetic_v02.py        # harder tier: dataset + multi-series charts
│   ├── 12_validate_synthetic_v02.py        # schema + recomputed-gold validation
│   ├── 13_create_v02_eval_assets.py        # v02 prompt packs / template / baselines
│   ├── 14_fetch_real_sources.py            # cache real open data + provenance
│   ├── 15_generate_real_pilot.py           # real-data tier from cached sources
│   ├── 16_create_manual_kit.py             # paste-friendly kit for free manual eval
│   ├── 17_validate_real_pilot.py           # real-data schema + recomputed-gold checks
│   ├── 18_build_release.py                 # assemble a Hugging Face-uploadable release/
│   ├── 19_generate_chart_read_v01.py       # label-free chart-reading tier
│   └── 20_validate_chart_read_v01.py       # chart-reading schema + recomputed-gold checks
├── requirements.txt
└── README.md
```

The evaluator `08_evaluate_predictions_file.py` is version-agnostic: pass
`--dataset data/processed/synthetic_v02.jsonl` to score v02.

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
* [x] Harder `synthetic_v02` tier: multi-series tables, distractor columns, multi-step tasks (average / nth-highest / cross-series), unanswerable (abstention) questions, real `hard` labels

* [x] First real-data tier (`real_pilot`) from licensed Türkiye open data, with provenance
* [x] Free manual evaluation kit (no API required)

Planned next:

1. Scale the real-data tier: more indicators/domains and more examples (target ~1000+ with ≥100 per important cell for statistically stable subgroup numbers).
2. Label-free chart variants (read values from gridlines, scored with estimation tolerance) for genuine chart-reading rather than label OCR.
3. A real multimodal evaluation harness that passes chart images to a model.
4. Baseline model evaluations and a public comparison table.
5. Prepare a Hugging Face dataset release and a public benchmark card.

## Project Goal

The goal is not just a dataset, but a reproducible Turkish benchmark for evaluating the data-analysis abilities of language models: dataset generation, gold verification, chart generation, quality control, evaluation scripts, documentation, and baseline comparisons.

## License

License will be decided before the public dataset release.
</content>
</invoke>
