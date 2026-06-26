# TR-DataAnalystBench

TR-DataAnalystBench is a Turkish table and chart reasoning benchmark for evaluating whether language models can correctly analyze structured data.

The benchmark focuses on realistic data analysis tasks such as reading tables, interpreting charts, comparing values, calculating percentage changes, and producing short factual summaries.

## Motivation

Many language models can generate fluent Turkish text, but they may still fail at numerical reasoning, table understanding, chart interpretation, and factual data analysis.

TR-DataAnalystBench aims to provide a reproducible Turkish benchmark for evaluating these abilities.

The long-term goal is to build a dataset and evaluation pipeline that can be used to test Turkish-capable LLMs and multimodal models on data analyst style tasks.

## Current Status

This repository currently contains the first synthetic pilot version of the benchmark.

The pilot includes:

* Synthetic table generation
* Turkish question generation
* Python-verified gold answers
* Chart image generation
* Dataset validation
* Pilot analysis report

## Pilot Dataset

The current pilot dataset contains 50 examples across 10 domains and 5 question types.

### Domains

* transportation
* economy
* education
* tourism
* energy
* health
* environment
* sports
* municipality
* agriculture

### Question Types

* value_lookup
* max_min
* comparison
* percentage_change
* trend_summary

### Splits

| Split      | Count |
| ---------- | ----: |
| train      |    40 |
| validation |     5 |
| test       |     5 |

## Repository Structure

```text
TR-DataAnalystBench/
│
├── charts/
│   └── pilot/
│
├── data/
│   ├── exports/
│   │   ├── pilot_analysis.csv
│   │   └── pilot_preview.csv
│   │
│   └── processed/
│       └── pilot.jsonl
│
├── docs/
│   └── pilot_report.md
│
├── scripts/
│   ├── 01_generate_synthetic_pilot.py
│   ├── 02_validate_pilot.py
│   └── 03_analyze_pilot.py
│
├── requirements.txt
└── README.md
```

## Example

Example question:

```text
2021 yılında yolcu sayısı kaçtır?
```

Example answer:

```text
2021 yılında yolcu sayısı 1.283.278 kişi olarak verilmiştir.
```

The gold answers are generated and verified with Python calculations instead of being guessed by a language model.

## Setup

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```bash
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Generate the Pilot Dataset

Run:

```bash
python scripts/01_generate_synthetic_pilot.py
```

This creates:

```text
data/processed/pilot.jsonl
data/exports/pilot_preview.csv
charts/pilot/*.png
```

## Validate the Pilot Dataset

Run:

```bash
python scripts/02_validate_pilot.py
```

The validation script checks:

* Required fields
* Unique IDs
* Valid question types
* Valid split labels
* Valid difficulty labels
* Table structure
* Chart file existence
* Empty question, answer, and calculation fields
* Known suspicious Turkish typos

## Generate the Pilot Report

Run:

```bash
python scripts/03_analyze_pilot.py
```

This creates:

```text
docs/pilot_report.md
data/exports/pilot_analysis.csv
```

## Roadmap

Planned next steps:

1. Improve Turkish wording quality in generated answers.
2. Add more question templates.
3. Add chart-only and table-plus-chart variants.
4. Move from synthetic pilot tables to real open-data sources.
5. Add automatic scoring for numeric answers.
6. Add baseline model evaluation.
7. Publish the dataset on Hugging Face.
8. Create a public benchmark card and model comparison table.

## Project Goal

The final goal is not just to create a dataset, but to build a reproducible Turkish benchmark for evaluating data analysis abilities of language models.

This includes:

* Dataset generation
* Gold answer verification
* Chart generation
* Quality control
* Evaluation scripts
* Documentation
* Baseline model comparisons

## License

License will be decided before the public dataset release.
