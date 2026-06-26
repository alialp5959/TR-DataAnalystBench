import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATASET_PATH = PROJECT_ROOT / "data" / "processed" / "pilot.jsonl"
EXPORTS_DIR = PROJECT_ROOT / "data" / "exports"
DOCS_DIR = PROJECT_ROOT / "docs"

REPORT_PATH = DOCS_DIR / "pilot_report.md"
ANALYSIS_CSV_PATH = EXPORTS_DIR / "pilot_analysis.csv"


def load_jsonl(path: Path) -> list[dict]:
    examples = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            examples.append(json.loads(line))

    return examples


def flatten_for_dataframe(examples: list[dict]) -> pd.DataFrame:
    rows = []

    for example in examples:
        table = example["table"]

        rows.append(
            {
                "id": example["id"],
                "domain": example["domain"],
                "source_name": example["source_name"],
                "data_type": example["data_type"],
                "chart_type": example["chart_type"],
                "question_type": example["question_type"],
                "difficulty": example["difficulty"],
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


def make_example_markdown(example: dict) -> str:
    table = example["table"]

    table_lines = []
    table_lines.append("| " + " | ".join(table["columns"]) + " |")
    table_lines.append("|" + "|".join(["---"] * len(table["columns"])) + "|")

    for row in table["rows"]:
        table_lines.append("| " + " | ".join(str(x) for x in row) + " |")

    markdown_table = "\n".join(table_lines)

    return f"""
### {example["id"]}

**Domain:** `{example["domain"]}`  
**Question type:** `{example["question_type"]}`  
**Difficulty:** `{example["difficulty"]}`  
**Split:** `{example["split"]}`  
**Chart:** `{example["chart_path"]}`

**Question:**  
{example["question"]}

**Gold answer:**  
{example["answer"]}

**Calculation:**  
`{example["calculation"]}`

**Table:**

{markdown_table}
""".strip()


def main() -> None:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATASET_PATH}")

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    examples = load_jsonl(DATASET_PATH)
    df = flatten_for_dataframe(examples)

    df.to_csv(ANALYSIS_CSV_PATH, index=False, encoding="utf-8-sig")

    question_type_counts = df["question_type"].value_counts().sort_index()
    domain_counts = df["domain"].value_counts().sort_index()
    split_counts = df["split"].value_counts().sort_index()
    difficulty_counts = df["difficulty"].value_counts().sort_index()

    total_examples = len(df)
    unique_domains = df["domain"].nunique()
    unique_question_types = df["question_type"].nunique()
    unique_charts = df["chart_path"].nunique()
    numeric_answer_count = df["numeric_answer"].notna().sum()
    non_numeric_answer_count = df["numeric_answer"].isna().sum()

    sample_examples = "\n\n".join(
        make_example_markdown(example) for example in examples[:8]
    )

    report = f"""# TR-DataAnalystBench Pilot Report

This report summarizes the first pilot version of TR-DataAnalystBench.

## Overview

TR-DataAnalystBench is a Turkish table and chart reasoning benchmark designed to evaluate whether language models can correctly analyze structured data.

The pilot dataset is synthetic and is used to validate the dataset schema, generation pipeline, chart generation, and quality-control scripts before moving to real open-data sources.

## Pilot Summary

| Metric | Value |
|---|---:|
| Total examples | {total_examples} |
| Unique domains | {unique_domains} |
| Unique question types | {unique_question_types} |
| Unique chart images | {unique_charts} |
| Numeric-answer examples | {numeric_answer_count} |
| Non-numeric summary examples | {non_numeric_answer_count} |

## Question Type Distribution

{make_markdown_table(question_type_counts, "Question type")}

## Domain Distribution

{make_markdown_table(domain_counts, "Domain")}

## Split Distribution

{make_markdown_table(split_counts, "Split")}

## Difficulty Distribution

{make_markdown_table(difficulty_counts, "Difficulty")}

## Current Task Types

The pilot currently includes five task types:

1. `value_lookup`: directly reading a value from a table.
2. `max_min`: identifying the maximum value and its corresponding year.
3. `comparison`: calculating the difference between two years.
4. `percentage_change`: calculating percentage change between two years.
5. `trend_summary`: producing a short factual trend interpretation.

## Quality Control

The pilot dataset has passed the validation script:

`python scripts/02_validate_pilot.py`

The validation checks:

- Required fields
- Unique IDs
- Valid question types
- Valid split labels
- Valid difficulty labels
- Table structure
- Chart file existence
- Empty question/answer/calculation fields
- Suspicious known Turkish typos

## Sample Examples

{sample_examples}

## Next Steps

The next development steps are:

1. Improve wording quality in generated Turkish answers.
2. Add more question templates.
3. Add chart-only and table-plus-chart variants.
4. Move from synthetic pilot tables to real open-data sources.
5. Add automatic scoring for numeric answers.
6. Prepare a public Hugging Face dataset card.
"""

    REPORT_PATH.write_text(report, encoding="utf-8")

    print("Pilot analysis completed successfully.")
    print(f"Total examples: {total_examples}")
    print(f"Analysis CSV: {ANALYSIS_CSV_PATH}")
    print(f"Pilot report: {REPORT_PATH}")


if __name__ == "__main__":
    main()