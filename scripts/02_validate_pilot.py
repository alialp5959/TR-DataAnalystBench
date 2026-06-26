import json
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = PROJECT_ROOT / "data" / "processed" / "pilot.jsonl"


REQUIRED_FIELDS = [
    "id",
    "language",
    "domain",
    "source_name",
    "data_type",
    "chart_type",
    "chart_path",
    "question_type",
    "difficulty",
    "table",
    "question",
    "answer",
    "numeric_answer",
    "calculation",
    "expected_reasoning",
    "unit",
    "split",
]


ALLOWED_QUESTION_TYPES = {
    "value_lookup",
    "max_min",
    "comparison",
    "percentage_change",
    "trend_summary",
}


ALLOWED_SPLITS = {
    "train",
    "validation",
    "test",
}


ALLOWED_DIFFICULTIES = {
    "easy",
    "medium",
    "hard",
}


def load_jsonl(path: Path) -> list[dict]:
    examples = []

    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                examples.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON at line {line_number}: {e}") from e

    return examples


def validate_required_fields(example: dict, index: int) -> list[str]:
    errors = []

    for field in REQUIRED_FIELDS:
        if field not in example:
            errors.append(f"Example {index}: missing field '{field}'")

    return errors


def validate_table(example: dict, index: int) -> list[str]:
    errors = []

    table = example.get("table")

    if not isinstance(table, dict):
        return [f"Example {index}: table must be a dictionary"]

    columns = table.get("columns")
    rows = table.get("rows")

    if not isinstance(columns, list) or len(columns) < 2:
        errors.append(f"Example {index}: table.columns must be a list with at least 2 columns")

    if not isinstance(rows, list) or len(rows) == 0:
        errors.append(f"Example {index}: table.rows must be a non-empty list")
        return errors

    for row_idx, row in enumerate(rows):
        if not isinstance(row, list):
            errors.append(f"Example {index}: row {row_idx} must be a list")
            continue

        if columns and len(row) != len(columns):
            errors.append(
                f"Example {index}: row {row_idx} has {len(row)} values but table has {len(columns)} columns"
            )

    return errors


def validate_chart_path(example: dict, index: int) -> list[str]:
    chart_path = example.get("chart_path")

    if not chart_path:
        return [f"Example {index}: chart_path is empty"]

    full_chart_path = PROJECT_ROOT / chart_path

    if not full_chart_path.exists():
        return [f"Example {index}: chart file does not exist: {chart_path}"]

    return []


def validate_values(example: dict, index: int) -> list[str]:
    errors = []

    if example.get("language") != "tr":
        errors.append(f"Example {index}: language should be 'tr'")

    if example.get("question_type") not in ALLOWED_QUESTION_TYPES:
        errors.append(f"Example {index}: invalid question_type '{example.get('question_type')}'")

    if example.get("split") not in ALLOWED_SPLITS:
        errors.append(f"Example {index}: invalid split '{example.get('split')}'")

    if example.get("difficulty") not in ALLOWED_DIFFICULTIES:
        errors.append(f"Example {index}: invalid difficulty '{example.get('difficulty')}'")

    if not str(example.get("question", "")).strip():
        errors.append(f"Example {index}: question is empty")

    if not str(example.get("answer", "")).strip():
        errors.append(f"Example {index}: answer is empty")

    if not str(example.get("calculation", "")).strip():
        errors.append(f"Example {index}: calculation is empty")

    if "kişitir" in str(example.get("answer", "")):
        errors.append(f"Example {index}: suspicious Turkish typo found: 'kişitir'")

    return errors


def main() -> None:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATASET_PATH}")

    examples = load_jsonl(DATASET_PATH)

    errors = []

    ids = []
    question_types = Counter()
    splits = Counter()
    domains = Counter()
    difficulties = Counter()

    for index, example in enumerate(examples, start=1):
        errors.extend(validate_required_fields(example, index))

        if all(field in example for field in REQUIRED_FIELDS):
            errors.extend(validate_table(example, index))
            errors.extend(validate_chart_path(example, index))
            errors.extend(validate_values(example, index))

        ids.append(example.get("id"))
        question_types[example.get("question_type")] += 1
        splits[example.get("split")] += 1
        domains[example.get("domain")] += 1
        difficulties[example.get("difficulty")] += 1

    duplicate_ids = [item for item, count in Counter(ids).items() if count > 1]
    if duplicate_ids:
        errors.append(f"Duplicate IDs found: {duplicate_ids}")

    print("=" * 60)
    print("TR-DataAnalystBench Pilot Validation")
    print("=" * 60)

    print(f"Total examples: {len(examples)}")
    print(f"Unique IDs: {len(set(ids))}")

    print("\nQuestion type distribution:")
    for key, value in sorted(question_types.items()):
        print(f"  {key}: {value}")

    print("\nSplit distribution:")
    for key, value in sorted(splits.items()):
        print(f"  {key}: {value}")

    print("\nDomain distribution:")
    for key, value in sorted(domains.items()):
        print(f"  {key}: {value}")

    print("\nDifficulty distribution:")
    for key, value in sorted(difficulties.items()):
        print(f"  {key}: {value}")

    if errors:
        print("\nValidation failed.")
        print(f"Number of errors: {len(errors)}")
        for error in errors[:30]:
            print(f"  - {error}")

        if len(errors) > 30:
            print(f"  ... and {len(errors) - 30} more errors")

        raise SystemExit(1)

    print("\nValidation passed. No issues found.")


if __name__ == "__main__":
    main()