import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATASET_PATH = PROJECT_ROOT / "data" / "processed" / "synthetic_v01.jsonl"
EXPORTS_DIR = PROJECT_ROOT / "data" / "exports"

ALL_TEMPLATE_PATH = EXPORTS_DIR / "synthetic_v01_prediction_template_all_numeric.csv"
TEST_TEMPLATE_PATH = EXPORTS_DIR / "synthetic_v01_prediction_template_test_numeric.csv"


def load_jsonl(path: Path) -> list[dict]:
    examples = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            examples.append(json.loads(line))

    return examples


def is_numeric_example(example: dict) -> bool:
    if example.get("numeric_answer") is None:
        return False

    if example.get("answer_type") not in {"numeric", "numeric_with_label"}:
        return False

    return True


def table_to_compact_json(table: dict) -> str:
    return json.dumps(table, ensure_ascii=False)


def create_template_rows(examples: list[dict]) -> list[dict]:
    rows = []

    for example in examples:
        if not is_numeric_example(example):
            continue

        rows.append(
            {
                "id": example["id"],
                "dataset_version": example["dataset_version"],
                "split": example["split"],
                "domain": example["domain"],
                "input_format": example["input_format"],
                "chart_type": example["chart_type"],
                "chart_path": example["chart_path"],
                "question_type": example["question_type"],
                "difficulty": example["difficulty"],
                "question": example["question"],
                "table": table_to_compact_json(example["table"]),
                "unit": example["unit"],
                "predicted_numeric_answer": "",
                "prediction_text": "",
            }
        )

    return rows


def main() -> None:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATASET_PATH}")

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    examples = load_jsonl(DATASET_PATH)

    all_rows = create_template_rows(examples)
    test_rows = [row for row in all_rows if row["split"] == "test"]

    all_df = pd.DataFrame(all_rows)
    test_df = pd.DataFrame(test_rows)

    all_df.to_csv(ALL_TEMPLATE_PATH, index=False, encoding="utf-8-sig")
    test_df.to_csv(TEST_TEMPLATE_PATH, index=False, encoding="utf-8-sig")

    print("Prediction templates created successfully.")
    print(f"All numeric template rows: {len(all_df)}")
    print(f"Test numeric template rows: {len(test_df)}")
    print(f"All numeric template: {ALL_TEMPLATE_PATH}")
    print(f"Test numeric template: {TEST_TEMPLATE_PATH}")


if __name__ == "__main__":
    main()