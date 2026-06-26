import argparse
import json
import re
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_DATASET_PATH = PROJECT_ROOT / "data" / "processed" / "synthetic_v01.jsonl"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "exports" / "evaluations"


REQUIRED_PREDICTION_COLUMNS = {
    "id",
    "predicted_numeric_answer",
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
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON at line {line_number}: {error}") from error

    return examples


def get_numeric_examples(examples: list[dict]) -> list[dict]:
    numeric_examples = []

    for example in examples:
        if example.get("numeric_answer") is None:
            continue

        if example.get("answer_type") not in {"numeric", "numeric_with_label"}:
            continue

        numeric_examples.append(example)

    return numeric_examples


def load_predictions(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Prediction file not found: {path}")

    predictions = pd.read_csv(path)

    missing_columns = REQUIRED_PREDICTION_COLUMNS - set(predictions.columns)

    if missing_columns:
        raise ValueError(
            f"Prediction file is missing required columns: {sorted(missing_columns)}"
        )

    if predictions["id"].duplicated().any():
        duplicate_ids = predictions.loc[predictions["id"].duplicated(), "id"].head(10).tolist()
        raise ValueError(f"Prediction file contains duplicate ids. Examples: {duplicate_ids}")

    return predictions

def safe_float(value) -> float | None:
    if value is None:
        return None

    if pd.isna(value):
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()

    if not text:
        return None

    text = text.replace("%", "")
    text = text.replace("−", "-")
    text = text.replace("–", "-")
    text = text.replace("—", "-")

    match = re.search(r"-?\d[\d\.,]*", text)

    if not match:
        return None

    number_text = match.group(0)

    has_dot = "." in number_text
    has_comma = "," in number_text

    if has_dot and has_comma:
        last_dot = number_text.rfind(".")
        last_comma = number_text.rfind(",")

        if last_comma > last_dot:
            # Turkish/European style: 1.234,5 -> 1234.5
            number_text = number_text.replace(".", "")
            number_text = number_text.replace(",", ".")
        else:
            # US style: 1,234.5 -> 1234.5
            number_text = number_text.replace(",", "")

    elif has_comma:
        parts = number_text.split(",")

        if len(parts[-1]) == 3 and len(parts) > 1:
            # 1,234 or 1,234,567
            number_text = number_text.replace(",", "")
        else:
            # 12,5
            number_text = number_text.replace(",", ".")

    elif has_dot:
        parts = number_text.split(".")

        if len(parts[-1]) == 3 and len(parts) > 1:
            # 1.234 or 1.234.567
            number_text = number_text.replace(".", "")

    try:
        return float(number_text)
    except ValueError:
        return None


def is_exact_match(gold: float, predicted: float) -> bool:
    return abs(float(gold) - float(predicted)) < 1e-9


def is_within_tolerance(example: dict, predicted: float) -> bool:
    gold = float(example["numeric_answer"])
    predicted = float(predicted)

    absolute_error = abs(predicted - gold)

    if example["question_type"] == "percentage_change":
        # Percentage-change questions use ±2 percentage points.
        return absolute_error <= 2.0

    # For large values, use 2% relative tolerance.
    # For very small values, allow absolute tolerance of 1.
    relative_error = absolute_error / max(abs(gold), 1.0)

    return relative_error <= 0.02 or absolute_error <= 1.0


def summarize_group(details: pd.DataFrame, group_column: str) -> dict:
    summary = {}

    for group_value, group_df in details.groupby(group_column):
        summary[str(group_value)] = {
            "count": int(len(group_df)),
            "missing_predictions": int(group_df["missing_prediction"].sum()),
            "invalid_predictions": int(group_df["invalid_prediction"].sum()),
            "exact_accuracy": float(group_df["exact_match"].mean()),
            "tolerance_accuracy": float(group_df["within_tolerance"].mean()),
            "mean_absolute_error": safe_metric(group_df["absolute_error"].dropna().mean()),
            "median_absolute_error": safe_metric(group_df["absolute_error"].dropna().median()),
        }

    return summary


def safe_metric(value) -> float | None:
    if pd.isna(value):
        return None

    return float(value)


def evaluate_predictions(
    examples: list[dict],
    predictions: pd.DataFrame,
    prediction_name: str,
) -> tuple[dict, pd.DataFrame]:
    prediction_map = {}

    for _, row in predictions.iterrows():
        prediction_map[row["id"]] = row

    dataset_ids = {example["id"] for example in examples}
    prediction_ids = set(predictions["id"].tolist())

    extra_prediction_ids = sorted(prediction_ids - dataset_ids)
    missing_prediction_ids = sorted(dataset_ids - prediction_ids)

    detail_rows = []

    for example in examples:
        example_id = example["id"]
        gold = float(example["numeric_answer"])

        prediction_row = prediction_map.get(example_id)

        if prediction_row is None:
            predicted = None
            prediction_text = None
            missing_prediction = True
            invalid_prediction = False
            exact_match = False
            within_tolerance = False
            absolute_error = None
            relative_error = None

        else:
            predicted = safe_float(prediction_row["predicted_numeric_answer"])
            prediction_text = prediction_row.get("prediction_text", "")

            missing_prediction = False
            invalid_prediction = predicted is None

            if invalid_prediction:
                exact_match = False
                within_tolerance = False
                absolute_error = None
                relative_error = None
            else:
                absolute_error = abs(predicted - gold)
                relative_error = absolute_error / max(abs(gold), 1.0)
                exact_match = is_exact_match(gold, predicted)
                within_tolerance = is_within_tolerance(example, predicted)

        detail_rows.append(
            {
                "prediction_name": prediction_name,
                "id": example_id,
                "domain": example["domain"],
                "input_format": example["input_format"],
                "chart_type": example["chart_type"],
                "question_type": example["question_type"],
                "difficulty": example["difficulty"],
                "split": example["split"],
                "unit": example["unit"],
                "question": example["question"],
                "gold_answer": example["answer"],
                "gold_numeric_answer": gold,
                "predicted_numeric_answer": predicted,
                "prediction_text": prediction_text,
                "missing_prediction": missing_prediction,
                "invalid_prediction": invalid_prediction,
                "exact_match": exact_match,
                "within_tolerance": within_tolerance,
                "absolute_error": absolute_error,
                "relative_error": relative_error,
            }
        )

    details = pd.DataFrame(detail_rows)

    report = {
        "prediction_name": prediction_name,
        "total_numeric_examples": int(len(details)),
        "provided_predictions": int(len(predictions)),
        "missing_predictions": int(details["missing_prediction"].sum()),
        "invalid_predictions": int(details["invalid_prediction"].sum()),
        "extra_predictions": int(len(extra_prediction_ids)),
        "exact_accuracy": float(details["exact_match"].mean()),
        "tolerance_accuracy": float(details["within_tolerance"].mean()),
        "mean_absolute_error": safe_metric(details["absolute_error"].dropna().mean()),
        "median_absolute_error": safe_metric(details["absolute_error"].dropna().median()),
        "by_question_type": summarize_group(details, "question_type"),
        "by_input_format": summarize_group(details, "input_format"),
        "by_domain": summarize_group(details, "domain"),
        "extra_prediction_ids_sample": extra_prediction_ids[:20],
        "missing_prediction_ids_sample": missing_prediction_ids[:20],
    }

    return report, details


def make_markdown_report(report: dict) -> str:
    lines = []

    lines.append(f"# Evaluation Report: {report['prediction_name']}")
    lines.append("")
    lines.append("## Overall Results")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Evaluation split | {report.get('evaluation_split', 'all')} |")
    lines.append(f"| Total numeric examples | {report['total_numeric_examples']} |")
    lines.append(f"| Provided predictions | {report['provided_predictions']} |")
    lines.append(f"| Missing predictions | {report['missing_predictions']} |")
    lines.append(f"| Invalid predictions | {report['invalid_predictions']} |")
    lines.append(f"| Extra predictions | {report['extra_predictions']} |")
    lines.append(f"| Exact accuracy | {report['exact_accuracy']:.2%} |")
    lines.append(f"| Tolerance accuracy | {report['tolerance_accuracy']:.2%} |")

    if report["mean_absolute_error"] is not None:
        lines.append(f"| Mean absolute error | {report['mean_absolute_error']:.4f} |")

    if report["median_absolute_error"] is not None:
        lines.append(f"| Median absolute error | {report['median_absolute_error']:.4f} |")

    lines.append("")
    lines.append("## Results by Question Type")
    lines.append("")
    lines.append("| Question type | Count | Exact accuracy | Tolerance accuracy | Mean absolute error |")
    lines.append("|---|---:|---:|---:|---:|")

    for key, value in report["by_question_type"].items():
        mae = value["mean_absolute_error"]
        mae_text = "" if mae is None else f"{mae:.4f}"
        lines.append(
            f"| {key} | {value['count']} | {value['exact_accuracy']:.2%} | "
            f"{value['tolerance_accuracy']:.2%} | {mae_text} |"
        )

    lines.append("")
    lines.append("## Results by Input Format")
    lines.append("")
    lines.append("| Input format | Count | Exact accuracy | Tolerance accuracy |")
    lines.append("|---|---:|---:|---:|")

    for key, value in report["by_input_format"].items():
        lines.append(
            f"| {key} | {value['count']} | {value['exact_accuracy']:.2%} | "
            f"{value['tolerance_accuracy']:.2%} |"
        )

    lines.append("")
    lines.append("## Results by Domain")
    lines.append("")
    lines.append("| Domain | Count | Exact accuracy | Tolerance accuracy |")
    lines.append("|---|---:|---:|---:|")

    for key, value in report["by_domain"].items():
        lines.append(
            f"| {key} | {value['count']} | {value['exact_accuracy']:.2%} | "
            f"{value['tolerance_accuracy']:.2%} |"
        )

    if report["extra_prediction_ids_sample"]:
        lines.append("")
        lines.append("## Extra Prediction IDs Sample")
        lines.append("")
        for item in report["extra_prediction_ids_sample"]:
            lines.append(f"- `{item}`")

    if report["missing_prediction_ids_sample"]:
        lines.append("")
        lines.append("## Missing Prediction IDs Sample")
        lines.append("")
        for item in report["missing_prediction_ids_sample"]:
            lines.append(f"- `{item}`")

    lines.append("")

    return "\n".join(lines)


def save_json(data: dict, path: Path) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate numeric prediction CSV files against TR-DataAnalystBench synthetic_v01."
    )

    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET_PATH,
        help="Path to the dataset JSONL file.",
    )

    parser.add_argument(
        "--predictions",
        type=Path,
        required=True,
        help="Path to prediction CSV file. Required columns: id,predicted_numeric_answer.",
    )

    parser.add_argument(
        "--prediction-name",
        type=str,
        default=None,
        help="Name of this prediction run. Defaults to prediction file stem.",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where evaluation outputs will be saved.",
    )
    parser.add_argument(
    "--split",
    type=str,
    choices=["all", "train", "validation", "test"],
    default="all",
    help="Dataset split to evaluate. Use 'all' to evaluate all numeric examples.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    dataset_path = args.dataset
    predictions_path = args.predictions
    output_dir = args.output_dir

    prediction_name = args.prediction_name or predictions_path.stem

    output_dir.mkdir(parents=True, exist_ok=True)

    examples = load_jsonl(dataset_path)
    numeric_examples_all = get_numeric_examples(examples)
    if args.split == "all":
        numeric_examples = numeric_examples_all
    else:
        numeric_examples = [
            example for example in numeric_examples_all
            if example.get("split") == args.split
    ]
    predictions = load_predictions(predictions_path)

    # When evaluating a specific split, ignore predictions from other splits.
    # This allows users to pass either a full prediction file or a split-specific file.
    evaluation_ids = {example["id"] for example in numeric_examples}
    predictions = predictions[predictions["id"].isin(evaluation_ids)].copy()


    report, details = evaluate_predictions(
        examples=numeric_examples,
        predictions=predictions,
        prediction_name=prediction_name,
    )
    report["evaluation_split"] = args.split

    details_path = output_dir / f"{prediction_name}_details.csv"
    report_json_path = output_dir / f"{prediction_name}_report.json"
    report_md_path = output_dir / f"{prediction_name}_report.md"

    details.to_csv(details_path, index=False, encoding="utf-8-sig")
    save_json(report, report_json_path)
    report_md_path.write_text(make_markdown_report(report), encoding="utf-8")

    print("Prediction file evaluation completed successfully.")
    print(f"Prediction name: {prediction_name}")
    print(f"Dataset: {dataset_path}")
    print(f"Predictions: {predictions_path}")
    print(f"Evaluation split: {args.split}")
    print()
    print("Overall results:")
    print(f"  Total numeric examples: {report['total_numeric_examples']}")
    print(f"  Provided predictions: {report['provided_predictions']}")
    print(f"  Missing predictions: {report['missing_predictions']}")
    print(f"  Invalid predictions: {report['invalid_predictions']}")
    print(f"  Extra predictions: {report['extra_predictions']}")
    print(f"  Exact accuracy: {report['exact_accuracy']:.2%}")
    print(f"  Tolerance accuracy: {report['tolerance_accuracy']:.2%}")
    print()
    print(f"Details CSV: {details_path}")
    print(f"Report JSON: {report_json_path}")
    print(f"Report Markdown: {report_md_path}")


if __name__ == "__main__":
    main()