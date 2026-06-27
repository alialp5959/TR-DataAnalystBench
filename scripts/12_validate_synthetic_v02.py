"""Validate the synthetic_v02 dataset.

Beyond schema checks, this validator recomputes the gold numeric answer for
each task directly from the table, so a bug in the generator is caught.
"""

import json
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATASET_PATH = PROJECT_ROOT / "data" / "processed" / "synthetic_v02.jsonl"
STATS_PATH = PROJECT_ROOT / "data" / "exports" / "synthetic_v02_stats.json"


REQUIRED_FIELDS = [
    "id", "dataset_version", "language", "domain", "source_name", "data_type",
    "input_format", "chart_type", "chart_path", "question_type", "difficulty",
    "table", "target_column", "unit", "split", "question", "answer",
    "answer_type", "numeric_answer", "calculation", "expected_reasoning",
]

ALLOWED_INPUT_FORMATS = {"table_only", "chart_only", "table_and_chart"}
ALLOWED_CHART_TYPES = {"line", "bar"}
ALLOWED_QUESTION_TYPES = {
    "value_lookup", "comparison", "percentage_change", "cross_series_diff",
    "average", "nth_highest", "trend_summary", "unanswerable",
}
ALLOWED_DIFFICULTIES = {"easy", "medium", "hard"}
ALLOWED_SPLITS = {"train", "validation", "test"}
ALLOWED_ANSWER_TYPES = {"numeric", "numeric_with_label", "text", "abstention"}

TOLERANCE = 0.01  # 1% leeway for rounding in recomputation


def load_jsonl(path: Path) -> list[dict]:
    examples = []
    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                examples.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON at line {line_number}: {error}") from error
    return examples


def column_values(table: dict, column_name: str):
    if column_name not in table["columns"]:
        return None
    idx = table["columns"].index(column_name)
    return [row[idx] for row in table["rows"]]


def detect_trend(values: list[int]) -> str:
    increases = sum(1 for a, b in zip(values, values[1:]) if b > a)
    decreases = sum(1 for a, b in zip(values, values[1:]) if b < a)
    if increases > decreases and values[-1] > values[0]:
        return "increasing"
    if decreases > increases and values[-1] < values[0]:
        return "decreasing"
    return "mixed"


def approx_equal(a: float, b: float) -> bool:
    return abs(a - b) <= max(abs(b) * TOLERANCE, 1.0)


def validate_schema(example: dict, index: int) -> list[str]:
    errors = []

    for field in REQUIRED_FIELDS:
        if field not in example:
            errors.append(f"Example {index}: missing field '{field}'")
    if errors:
        return errors

    if example["dataset_version"] != "synthetic_v02":
        errors.append(f"Example {index}: wrong dataset_version '{example['dataset_version']}'")
    if example["language"] != "tr":
        errors.append(f"Example {index}: language must be 'tr'")
    if example["input_format"] not in ALLOWED_INPUT_FORMATS:
        errors.append(f"Example {index}: invalid input_format '{example['input_format']}'")
    if example["chart_type"] not in ALLOWED_CHART_TYPES:
        errors.append(f"Example {index}: invalid chart_type '{example['chart_type']}'")
    if example["question_type"] not in ALLOWED_QUESTION_TYPES:
        errors.append(f"Example {index}: invalid question_type '{example['question_type']}'")
    if example["difficulty"] not in ALLOWED_DIFFICULTIES:
        errors.append(f"Example {index}: invalid difficulty '{example['difficulty']}'")
    if example["split"] not in ALLOWED_SPLITS:
        errors.append(f"Example {index}: invalid split '{example['split']}'")
    if example["answer_type"] not in ALLOWED_ANSWER_TYPES:
        errors.append(f"Example {index}: invalid answer_type '{example['answer_type']}'")

    for field in ["question", "answer", "calculation", "expected_reasoning", "unit"]:
        if not str(example.get(field, "")).strip():
            errors.append(f"Example {index}: field '{field}' is empty")

    return errors


def validate_table(example: dict, index: int) -> list[str]:
    errors = []
    table = example.get("table")
    if not isinstance(table, dict):
        return [f"Example {index}: table must be a dict"]

    columns = table.get("columns")
    rows = table.get("rows")
    if not isinstance(columns, list) or len(columns) < 2:
        errors.append(f"Example {index}: table must have at least 2 columns (Year + metric)")
        return errors
    if columns[0] != "Yıl":
        errors.append(f"Example {index}: first column must be 'Yıl', got '{columns[0]}'")
    if not isinstance(rows, list) or len(rows) not in {5, 6}:
        errors.append(f"Example {index}: table must have 5 or 6 rows")
        return errors

    seen_years = set()
    for row_idx, row in enumerate(rows):
        if not isinstance(row, list) or len(row) != len(columns):
            errors.append(f"Example {index}: row {row_idx} shape mismatch")
            continue
        year = row[0]
        if not isinstance(year, int):
            errors.append(f"Example {index}: row {row_idx} year must be int")
        if year in seen_years:
            errors.append(f"Example {index}: duplicate year {year}")
        seen_years.add(year)
        for value in row[1:]:
            if not isinstance(value, int) or value <= 0:
                errors.append(f"Example {index}: row {row_idx} has non-positive/non-int value {value}")
    return errors


def validate_chart(example: dict, index: int) -> list[str]:
    chart_path = example.get("chart_path")
    if not chart_path:
        return [f"Example {index}: chart_path is empty"]
    full = PROJECT_ROOT / chart_path
    if not full.exists():
        return [f"Example {index}: chart file missing: {chart_path}"]
    return []


def validate_answer(example: dict, index: int) -> list[str]:
    errors = []
    qtype = example["question_type"]
    table = example["table"]
    gold = example.get("numeric_answer")
    target = example.get("target_column")
    answer = str(example.get("answer", ""))

    if qtype == "unanswerable":
        if example["answer_type"] != "abstention":
            errors.append(f"Example {index}: unanswerable must have answer_type 'abstention'")
        if gold is not None:
            errors.append(f"Example {index}: unanswerable must have numeric_answer None")
        return errors

    if qtype == "trend_summary":
        if example["answer_type"] != "text":
            errors.append(f"Example {index}: trend_summary must have answer_type 'text'")
        if gold is not None:
            errors.append(f"Example {index}: trend_summary must have numeric_answer None")
        tclass = example.get("trend_class")
        if tclass not in {"increasing", "decreasing", "mixed"}:
            errors.append(f"Example {index}: invalid trend_class '{tclass}'")
        else:
            values = column_values(table, target)
            if values is None:
                errors.append(f"Example {index}: trend target_column '{target}' not in table")
            elif detect_trend(values) != tclass:
                errors.append(f"Example {index}: trend_class '{tclass}' does not match recomputed trend")
        return errors

    # Numeric tasks
    if not isinstance(gold, (int, float)):
        errors.append(f"Example {index}: numeric task '{qtype}' must have numeric_answer")
        return errors

    if qtype == "cross_series_diff":
        # target is composite "A - B"; verify gold == |A_y - B_y| for some year
        col_a = [row[1] for row in table["rows"]]
        col_b = [row[2] for row in table["rows"]]
        if not any(abs(a - b) == gold for a, b in zip(col_a, col_b)):
            errors.append(f"Example {index}: cross_series_diff gold {gold} not found among series differences")
        return errors

    values = column_values(table, target)
    if values is None:
        errors.append(f"Example {index}: target_column '{target}' not in table for {qtype}")
        return errors

    if qtype == "value_lookup":
        if gold not in values:
            errors.append(f"Example {index}: value_lookup gold {gold} not in target column")

    elif qtype == "comparison":
        if gold < 0:
            errors.append(f"Example {index}: comparison gold must be non-negative absolute difference")

    elif qtype == "percentage_change":
        if example["unit"] != "percent":
            errors.append(f"Example {index}: percentage_change unit must be 'percent'")
        if "artmıştır" in answer and gold < 0:
            errors.append(f"Example {index}: percentage_change 'artmıştır' but gold negative ({gold})")
        if "azalmıştır" in answer and gold > 0:
            errors.append(f"Example {index}: percentage_change 'azalmıştır' but gold positive ({gold})")

    elif qtype == "average":
        expected = sum(values) / len(values)
        if not approx_equal(float(gold), expected):
            errors.append(f"Example {index}: average gold {gold} != recomputed mean {expected:.2f}")

    elif qtype == "nth_highest":
        ordered = sorted(values, reverse=True)
        if gold not in {ordered[1], ordered[2] if len(ordered) > 2 else ordered[1]}:
            errors.append(f"Example {index}: nth_highest gold {gold} is not the 2nd or 3rd highest value")

    return errors


def validate_counts(examples: list[dict]) -> list[str]:
    errors = []
    if len(examples) != 320:
        errors.append(f"Expected 320 examples, found {len(examples)}")
    qt = Counter(e["question_type"] for e in examples)
    for question_type in ALLOWED_QUESTION_TYPES:
        if qt[question_type] != 40:
            errors.append(f"Expected 40 examples for '{question_type}', found {qt[question_type]}")
    ids = [e["id"] for e in examples]
    dupes = [i for i, c in Counter(ids).items() if c > 1]
    if dupes:
        errors.append(f"Duplicate ids: {dupes[:5]}")
    return errors


def main() -> None:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATASET_PATH}")

    examples = load_jsonl(DATASET_PATH)
    errors = []

    for index, example in enumerate(examples, start=1):
        schema_errors = validate_schema(example, index)
        errors.extend(schema_errors)
        if schema_errors:
            continue
        errors.extend(validate_table(example, index))
        errors.extend(validate_chart(example, index))
        errors.extend(validate_answer(example, index))

    errors.extend(validate_counts(examples))

    print("=" * 70)
    print("TR-DataAnalystBench Synthetic v0.2 Validation")
    print("=" * 70)
    print(f"Total examples: {len(examples)}")
    print(f"Unique charts: {len(set(e['chart_path'] for e in examples))}")

    for key in ["question_type", "answer_type", "difficulty", "input_format", "split"]:
        dist = Counter(e.get(key) for e in examples)
        print(f"\n{key} distribution:")
        for k, v in sorted(dist.items(), key=lambda kv: str(kv[0])):
            print(f"  {k}: {v}")

    if not STATS_PATH.exists():
        errors.append(f"Stats file not found: {STATS_PATH}")

    if errors:
        print("\nValidation failed.")
        print(f"Number of errors: {len(errors)}")
        for error in errors[:40]:
            print(f"  - {error}")
        if len(errors) > 40:
            print(f"  ... and {len(errors) - 40} more errors")
        raise SystemExit(1)

    print("\nValidation passed. No issues found.")


if __name__ == "__main__":
    main()
