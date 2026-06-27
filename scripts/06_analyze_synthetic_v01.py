import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATASET_PATH = PROJECT_ROOT / "data" / "processed" / "synthetic_v01.jsonl"
STATS_PATH = PROJECT_ROOT / "data" / "exports" / "synthetic_v01_stats.json"

EXPORTS_DIR = PROJECT_ROOT / "data" / "exports"
DOCS_DIR = PROJECT_ROOT / "docs"

ANALYSIS_CSV_PATH = EXPORTS_DIR / "synthetic_v01_analysis.csv"
REPORT_PATH = DOCS_DIR / "synthetic_v01_report.md"


def load_jsonl(path: Path) -> list[dict]:
    examples = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            examples.append(json.loads(line))

    return examples


def load_stats(path: Path) -> dict:
    if not path.exists():
        return {}

    return json.loads(path.read_text(encoding="utf-8"))


def flatten_examples(examples: list[dict]) -> pd.DataFrame:
    rows = []

    for example in examples:
        table = example["table"]

        rows.append(
            {
                "id": example["id"],
                "dataset_version": example["dataset_version"],
                "domain": example["domain"],
                "source_name": example["source_name"],
                "input_format": example["input_format"],
                "chart_type": example["chart_type"],
                "question_type": example["question_type"],
                "difficulty": example["difficulty"],
                "answer_type": example["answer_type"],
                "question": example["question"],
                "answer": example["answer"],
                "numeric_answer": example["numeric_answer"],
                "unit": example["unit"],
                "split": example["split"],
                "chart_path": example["chart_path"],
                "table_num_rows": len(table["rows"]),
                "table_columns": ", ".join(table["columns"]),
            }
        )

    return pd.DataFrame(rows)


def make_markdown_table(series: pd.Series, column_name: str) -> str:
    lines = [
        f"| {column_name} | Count |",
        "|---|---:|",
    ]

    for key, value in series.items():
        lines.append(f"| {key} | {value} |")

    return "\n".join(lines)


def make_sample_table_markdown(example: dict) -> str:
    table = example["table"]

    lines = []
    lines.append("| " + " | ".join(table["columns"]) + " |")
    lines.append("|" + "|".join(["---"] * len(table["columns"])) + "|")

    for row in table["rows"]:
        lines.append("| " + " | ".join(str(value) for value in row) + " |")

    return "\n".join(lines)


def make_sample_examples_section(examples: list[dict], limit: int = 10) -> str:
    selected = examples[:limit]
    sections = []

    for example in selected:
        table_markdown = make_sample_table_markdown(example)

        section = f"""
### {example["id"]}

| Field | Value |
|---|---|
| Domain | `{example["domain"]}` |
| Input format | `{example["input_format"]}` |
| Chart type | `{example["chart_type"]}` |
| Question type | `{example["question_type"]}` |
| Difficulty | `{example["difficulty"]}` |
| Split | `{example["split"]}` |
| Chart path | `{example["chart_path"]}` |

**Question:**  
{example["question"]}

**Gold answer:**  
{example["answer"]}

**Calculation:**  
{example["calculation"]}

**Expected reasoning:**  
{example["expected_reasoning"]}

**Table:**

{table_markdown}
"""
        sections.append(section.strip())

    return "\n\n".join(sections)


def main() -> None:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATASET_PATH}")

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    examples = load_jsonl(DATASET_PATH)
    stats = load_stats(STATS_PATH)

    df = flatten_examples(examples)
    df.to_csv(ANALYSIS_CSV_PATH, index=False, encoding="utf-8-sig")

    total_examples = len(df)
    unique_ids = df["id"].nunique()
    unique_domains = df["domain"].nunique()
    unique_charts = df["chart_path"].nunique()
    unique_question_types = df["question_type"].nunique()

    numeric_examples = df["numeric_answer"].notna().sum()
    text_examples = df["numeric_answer"].isna().sum()

    domain_counts = df["domain"].value_counts().sort_index()
    input_format_counts = df["input_format"].value_counts().sort_index()
    chart_type_counts = df["chart_type"].value_counts().sort_index()
    question_type_counts = df["question_type"].value_counts().sort_index()
    difficulty_counts = df["difficulty"].value_counts().sort_index()
    split_counts = df["split"].value_counts().sort_index()
    answer_type_counts = df["answer_type"].value_counts().sort_index()

    report = f"""# TR-DataAnalystBench Synthetic v0.1 Report

This report summarizes the synthetic v0.1 version of TR-DataAnalystBench.

## Overview

TR-DataAnalystBench is a Turkish table and chart reasoning benchmark designed to evaluate whether language models can correctly analyze structured data.

The synthetic v0.1 dataset expands the initial 50-example pilot into a 300-example benchmark with more input formats and chart variants.

## Summary

| Metric | Value |
|---|---:|
| Total examples | {total_examples} |
| Unique IDs | {unique_ids} |
| Unique domains | {unique_domains} |
| Unique question types | {unique_question_types} |
| Unique chart images | {unique_charts} |
| Numeric-answer examples | {numeric_examples} |
| Text-answer examples | {text_examples} |

## Dataset Files

| File | Description |
|---|---|
| `data/processed/synthetic_v01.jsonl` | Main JSONL dataset |
| `data/exports/synthetic_v01_preview.csv` | Lightweight preview CSV |
| `data/exports/synthetic_v01_stats.json` | Dataset statistics |
| `data/exports/synthetic_v01_analysis.csv` | Flattened analysis CSV |
| `charts/synthetic_v01/` | Generated chart images |

## Domain Distribution

{make_markdown_table(domain_counts, "Domain")}

## Input Format Distribution

{make_markdown_table(input_format_counts, "Input format")}

## Chart Type Distribution

{make_markdown_table(chart_type_counts, "Chart type")}

## Question Type Distribution

{make_markdown_table(question_type_counts, "Question type")}

## Difficulty Distribution

{make_markdown_table(difficulty_counts, "Difficulty")}

## Split Distribution

{make_markdown_table(split_counts, "Split")}

## Answer Type Distribution

{make_markdown_table(answer_type_counts, "Answer type")}

## Current Task Types

The synthetic v0.1 dataset includes five task types:

1. `value_lookup`: directly reading a value from a table or chart.
2. `max_min`: identifying the maximum or minimum value and its corresponding year.
3. `comparison`: calculating the absolute difference between two selected years.
4. `percentage_change`: calculating percentage change between two selected years.
5. `trend_summary`: producing a short factual trend interpretation.

## Input Formats

The dataset includes three input formats:

1. `table_only`: the model should answer using the table.
2. `chart_only`: the model should answer using the chart image.
3. `table_and_chart`: the model can use both the table and chart.

## Quality Control

The synthetic v0.1 dataset passed the validation script:

`python scripts/05_validate_synthetic_v01.py`

The validation checks:

- Required fields
- Unique IDs
- Valid dataset version
- Valid input formats
- Valid chart types
- Valid question types
- Valid split labels
- Valid difficulty labels
- Valid answer types
- Table structure
- Chart file existence
- Numeric answer consistency
- Signed percentage-change direction consistency
- Trend class consistency (increasing / decreasing / mixed)
- Known suspicious Turkish typos
- Expected dataset size and distribution

## Scoring

All 300 examples are automatically scorable:

- 240 numeric examples (`value_lookup`, `max_min`, `comparison`, `percentage_change`) are scored with tolerance. `percentage_change` gold answers are signed, so direction is evaluated.
- 60 `trend_summary` examples are scored as a 3-class categorization (`increasing` / `decreasing` / `mixed`) via the `trend_class` field.

Use `scripts/08_evaluate_predictions_file.py` to score a prediction CSV. Running it on the generated oracle predictions yields 100% overall accuracy.

## Stats JSON

The stats file contains the following top-level keys:

{", ".join(f"`{key}`" for key in stats.keys()) if stats else "Stats file was not found."}

## Sample Examples

{make_sample_examples_section(examples, limit=10)}

## Notes

This is still a synthetic dataset. It is useful for validating the benchmark schema, generation pipeline, chart generation, and quality-control process.

The next major step is to move from synthetic tables to real open-data sources.

## Next Steps

1. Increase difficulty and discrimination (label-free chart variants, multi-series tables, distractor columns, harder templates).
2. Add a multimodal evaluation harness that passes chart images to a model.
3. Add baseline model evaluation and a comparison table.
4. Move from synthetic tables to real Turkish open-data sources.
5. Prepare a Hugging Face dataset release.
"""

    REPORT_PATH.write_text(report, encoding="utf-8")

    print("Synthetic v0.1 analysis completed successfully.")
    print(f"Total examples: {total_examples}")
    print(f"Unique charts: {unique_charts}")
    print(f"Analysis CSV: {ANALYSIS_CSV_PATH}")
    print(f"Report path: {REPORT_PATH}")


if __name__ == "__main__":
    main()