import json
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATASET_PATH = PROJECT_ROOT / "data" / "processed" / "synthetic_v01.jsonl"
STATS_PATH = PROJECT_ROOT / "data" / "exports" / "synthetic_v01_stats.json"


REQUIRED_FIELDS = [
    "id",
    "dataset_version",
    "language",
    "domain",
    "source_name",
    "data_type",
    "input_format",
    "chart_type",
    "chart_path",
    "question_type",
    "difficulty",
    "table",
    "target_column",
    "unit",
    "split",
    "question",
    "answer",
    "answer_type",
    "numeric_answer",
    "calculation",
    "expected_reasoning",
]


ALLOWED_DATASET_VERSIONS = {
    "synthetic_v01",
}


ALLOWED_LANGUAGES = {
    "tr",
}


ALLOWED_DATA_TYPES = {
    "table_chart",
}


ALLOWED_INPUT_FORMATS = {
    "table_only",
    "chart_only",
    "table_and_chart",
}


ALLOWED_CHART_TYPES = {
    "line",
    "bar",
}


ALLOWED_QUESTION_TYPES = {
    "value_lookup",
    "max_min",
    "comparison",
    "percentage_change",
    "trend_summary",
}


ALLOWED_DIFFICULTIES = {
    "easy",
    "medium",
    "hard",
}


ALLOWED_SPLITS = {
    "train",
    "validation",
    "test",
}


ALLOWED_ANSWER_TYPES = {
    "numeric",
    "numeric_with_label",
    "text",
}


SUSPICIOUS_TURKISH_TYPOS = [
    "kişitir",
    "öğrencitir",
    "tontir",
    "başvurutir",
    "kullanımtir",
    "MWhdir",
]


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


def validate_required_fields(example: dict, index: int) -> list[str]:
    errors = []

    for field in REQUIRED_FIELDS:
        if field not in example:
            errors.append(f"Example {index}: missing field '{field}'")

    return errors


def validate_basic_values(example: dict, index: int) -> list[str]:
    errors = []

    if example.get("dataset_version") not in ALLOWED_DATASET_VERSIONS:
        errors.append(f"Example {index}: invalid dataset_version '{example.get('dataset_version')}'")

    if example.get("language") not in ALLOWED_LANGUAGES:
        errors.append(f"Example {index}: invalid language '{example.get('language')}'")

    if example.get("data_type") not in ALLOWED_DATA_TYPES:
        errors.append(f"Example {index}: invalid data_type '{example.get('data_type')}'")

    if example.get("input_format") not in ALLOWED_INPUT_FORMATS:
        errors.append(f"Example {index}: invalid input_format '{example.get('input_format')}'")

    if example.get("chart_type") not in ALLOWED_CHART_TYPES:
        errors.append(f"Example {index}: invalid chart_type '{example.get('chart_type')}'")

    if example.get("question_type") not in ALLOWED_QUESTION_TYPES:
        errors.append(f"Example {index}: invalid question_type '{example.get('question_type')}'")

    if example.get("difficulty") not in ALLOWED_DIFFICULTIES:
        errors.append(f"Example {index}: invalid difficulty '{example.get('difficulty')}'")

    if example.get("split") not in ALLOWED_SPLITS:
        errors.append(f"Example {index}: invalid split '{example.get('split')}'")

    if example.get("answer_type") not in ALLOWED_ANSWER_TYPES:
        errors.append(f"Example {index}: invalid answer_type '{example.get('answer_type')}'")

    return errors


def validate_text_fields(example: dict, index: int) -> list[str]:
    errors = []

    text_fields = [
        "domain",
        "source_name",
        "chart_path",
        "target_column",
        "unit",
        "question",
        "answer",
        "calculation",
        "expected_reasoning",
    ]

    for field in text_fields:
        value = example.get(field)

        if value is None:
            errors.append(f"Example {index}: field '{field}' is None")
            continue

        if not str(value).strip():
            errors.append(f"Example {index}: field '{field}' is empty")

    answer = str(example.get("answer", ""))

    for typo in SUSPICIOUS_TURKISH_TYPOS:
        if typo in answer:
            errors.append(f"Example {index}: suspicious Turkish typo found: '{typo}'")

    return errors


def validate_table(example: dict, index: int) -> list[str]:
    errors = []

    table = example.get("table")

    if not isinstance(table, dict):
        return [f"Example {index}: table must be a dictionary"]

    columns = table.get("columns")
    rows = table.get("rows")

    if not isinstance(columns, list):
        errors.append(f"Example {index}: table.columns must be a list")
        return errors

    if len(columns) != 2:
        errors.append(f"Example {index}: table must have exactly 2 columns")

    if not isinstance(rows, list):
        errors.append(f"Example {index}: table.rows must be a list")
        return errors

    if len(rows) not in {5, 6}:
        errors.append(f"Example {index}: table must have 5 or 6 rows, got {len(rows)}")

    target_column = example.get("target_column")
    if target_column not in columns:
        errors.append(f"Example {index}: target_column '{target_column}' not found in table columns")

    seen_years = set()

    for row_idx, row in enumerate(rows):
        if not isinstance(row, list):
            errors.append(f"Example {index}: row {row_idx} must be a list")
            continue

        if len(row) != len(columns):
            errors.append(
                f"Example {index}: row {row_idx} has {len(row)} values but table has {len(columns)} columns"
            )
            continue

        year = row[0]
        value = row[1]

        if not isinstance(year, int):
            errors.append(f"Example {index}: row {row_idx} year must be int, got {type(year).__name__}")

        if year in seen_years:
            errors.append(f"Example {index}: duplicate year found: {year}")

        seen_years.add(year)

        if not isinstance(value, int):
            errors.append(f"Example {index}: row {row_idx} value must be int, got {type(value).__name__}")

        if isinstance(value, int) and value <= 0:
            errors.append(f"Example {index}: row {row_idx} value must be positive, got {value}")

    return errors


def validate_chart_path(example: dict, index: int) -> list[str]:
    chart_path = example.get("chart_path")

    if not chart_path:
        return [f"Example {index}: chart_path is empty"]

    full_chart_path = PROJECT_ROOT / chart_path

    if not full_chart_path.exists():
        return [f"Example {index}: chart file does not exist: {chart_path}"]

    if full_chart_path.suffix.lower() != ".png":
        return [f"Example {index}: chart file must be .png: {chart_path}"]

    return []


def validate_answer_consistency(example: dict, index: int) -> list[str]:
    errors = []

    question_type = example.get("question_type")
    answer_type = example.get("answer_type")
    numeric_answer = example.get("numeric_answer")
    question = str(example.get("question", ""))

    if question_type == "trend_summary":
        if answer_type != "text":
            errors.append(f"Example {index}: trend_summary should have answer_type 'text'")

        if numeric_answer is not None:
            errors.append(f"Example {index}: trend_summary should have numeric_answer None")

        trend_class = example.get("trend_class")
        allowed_trend_classes = {"increasing", "decreasing", "mixed"}

        if trend_class not in allowed_trend_classes:
            errors.append(
                f"Example {index}: trend_summary should have trend_class in {sorted(allowed_trend_classes)}, "
                f"got '{trend_class}'"
            )
        else:
            answer = str(example.get("answer", ""))
            if trend_class == "increasing" and "artış" not in answer:
                errors.append(f"Example {index}: trend_class 'increasing' but answer text does not mention 'artış'")
            if trend_class == "decreasing" and "azalış" not in answer:
                errors.append(f"Example {index}: trend_class 'decreasing' but answer text does not mention 'azalış'")
            if trend_class == "mixed" and "dalgalı" not in answer:
                errors.append(f"Example {index}: trend_class 'mixed' but answer text does not mention 'dalgalı'")

        return errors

    if answer_type not in {"numeric", "numeric_with_label"}:
        errors.append(f"Example {index}: {question_type} should have numeric or numeric_with_label answer_type")

    if numeric_answer is None:
        errors.append(f"Example {index}: {question_type} should have a numeric_answer")
        return errors

    if not isinstance(numeric_answer, (int, float)):
        errors.append(f"Example {index}: numeric_answer should be int or float")
        return errors

    rows = example.get("table", {}).get("rows", [])

    if question_type == "max_min":
        values = [row[1] for row in rows if isinstance(row, list) and len(row) >= 2]

        if not values:
            errors.append(f"Example {index}: max_min cannot be checked because table values are missing")
        else:
            if "hangi yıldadır" in question:
                errors.append(
                    f"Example {index}: max_min question asks for a year, but numeric scoring expects a value"
                )

            if "en yüksek" in question:
                expected_value = max(values)
                if numeric_answer != expected_value:
                    errors.append(
                        f"Example {index}: max_min numeric_answer should be max value {expected_value}, got {numeric_answer}"
                    )

            elif "en düşük" in question:
                expected_value = min(values)
                if numeric_answer != expected_value:
                    errors.append(
                        f"Example {index}: max_min numeric_answer should be min value {expected_value}, got {numeric_answer}"
                    )

            else:
                errors.append(f"Example {index}: max_min question should mention 'en yüksek' or 'en düşük'")

    if question_type == "comparison":
        if numeric_answer < 0:
            errors.append(
                f"Example {index}: comparison numeric_answer should be an absolute difference, got {numeric_answer}"
            )

    if question_type == "percentage_change":
        if example.get("unit") != "percent":
            errors.append(f"Example {index}: percentage_change should have unit 'percent'")

        # Gold artık işaretli (signed): yön, cevap metnindeki ifadeyle tutarlı olmalı.
        answer = str(example.get("answer", ""))

        if "artmıştır" in answer and numeric_answer < 0:
            errors.append(
                f"Example {index}: percentage_change says 'artmıştır' but numeric_answer is negative ({numeric_answer})"
            )

        if "azalmıştır" in answer and numeric_answer > 0:
            errors.append(
                f"Example {index}: percentage_change says 'azalmıştır' but numeric_answer is positive ({numeric_answer})"
            )

        if "değişmemiştir" in answer and numeric_answer != 0:
            errors.append(
                f"Example {index}: percentage_change says 'değişmemiştir' but numeric_answer is not zero ({numeric_answer})"
            )

    return errors


def validate_expected_counts(examples: list[dict]) -> list[str]:
    errors = []

    total = len(examples)

    if total != 300:
        errors.append(f"Expected 300 examples, found {total}")

    unique_charts = len(set(example.get("chart_path") for example in examples))

    if unique_charts != 60:
        errors.append(f"Expected 60 unique chart paths, found {unique_charts}")

    question_type_counts = Counter(example.get("question_type") for example in examples)
    for question_type in ALLOWED_QUESTION_TYPES:
        if question_type_counts[question_type] != 60:
            errors.append(
                f"Expected 60 examples for question_type '{question_type}', found {question_type_counts[question_type]}"
            )

    input_format_counts = Counter(example.get("input_format") for example in examples)
    for input_format in ALLOWED_INPUT_FORMATS:
        if input_format_counts[input_format] != 100:
            errors.append(
                f"Expected 100 examples for input_format '{input_format}', found {input_format_counts[input_format]}"
            )

    split_counts = Counter(example.get("split") for example in examples)

    expected_split_counts = {
        "train": 240,
        "validation": 30,
        "test": 30,
    }

    for split, expected_count in expected_split_counts.items():
        if split_counts[split] != expected_count:
            errors.append(f"Expected {expected_count} examples for split '{split}', found {split_counts[split]}")

    return errors


def print_distribution(title: str, counter: Counter) -> None:
    print(f"\n{title}:")
    for key, value in sorted(counter.items()):
        print(f"  {key}: {value}")


def main() -> None:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATASET_PATH}")

    examples = load_jsonl(DATASET_PATH)
    errors = []

    ids = []
    domains = Counter()
    input_formats = Counter()
    chart_types = Counter()
    question_types = Counter()
    difficulties = Counter()
    splits = Counter()
    answer_types = Counter()

    for index, example in enumerate(examples, start=1):
        errors.extend(validate_required_fields(example, index))

        if all(field in example for field in REQUIRED_FIELDS):
            errors.extend(validate_basic_values(example, index))
            errors.extend(validate_text_fields(example, index))
            errors.extend(validate_table(example, index))
            errors.extend(validate_chart_path(example, index))
            errors.extend(validate_answer_consistency(example, index))

        ids.append(example.get("id"))
        domains[example.get("domain")] += 1
        input_formats[example.get("input_format")] += 1
        chart_types[example.get("chart_type")] += 1
        question_types[example.get("question_type")] += 1
        difficulties[example.get("difficulty")] += 1
        splits[example.get("split")] += 1
        answer_types[example.get("answer_type")] += 1

    duplicate_ids = [item for item, count in Counter(ids).items() if count > 1]
    if duplicate_ids:
        errors.append(f"Duplicate IDs found: {duplicate_ids[:10]}")

    errors.extend(validate_expected_counts(examples))

    print("=" * 70)
    print("TR-DataAnalystBench Synthetic v0.1 Validation")
    print("=" * 70)

    print(f"Total examples: {len(examples)}")
    print(f"Unique IDs: {len(set(ids))}")
    print(f"Unique charts: {len(set(example.get('chart_path') for example in examples))}")

    print_distribution("Domain distribution", domains)
    print_distribution("Input format distribution", input_formats)
    print_distribution("Chart type distribution", chart_types)
    print_distribution("Question type distribution", question_types)
    print_distribution("Difficulty distribution", difficulties)
    print_distribution("Split distribution", splits)
    print_distribution("Answer type distribution", answer_types)

    if STATS_PATH.exists():
        print(f"\nStats file found: {STATS_PATH}")
    else:
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