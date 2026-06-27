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


def get_trend_examples(examples: list[dict]) -> list[dict]:
    return [
        example
        for example in examples
        if example.get("question_type") == "trend_summary"
        and example.get("trend_class") is not None
    ]


def normalize_trend_label(value) -> str | None:
    """Map a free-text trend prediction to one of: increasing / decreasing / mixed."""
    if value is None:
        return None

    if pd.isna(value):
        return None

    text = str(value).strip().lower()

    if not text:
        return None

    # "dalgalı / karışık / değişken" -> mixed (check first; it is the catch-all class).
    if any(keyword in text for keyword in ["dalgal", "karış", "karis", "değişken", "degisken", "istikrarsız", "mixed", "fluctuat"]):
        return "mixed"

    # "azalış / düşüş / azalma" -> decreasing (check before increasing to avoid 'art' clashes).
    if any(keyword in text for keyword in ["azal", "düş", "dus", "decreas", "decline", "gerile"]):
        return "decreasing"

    # "artış / yükseliş / artma" -> increasing.
    if any(keyword in text for keyword in ["art", "yüksel", "yuksel", "increas", "rising", "yukar"]):
        return "increasing"

    return None


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
                "answer_kind": "numeric",
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
                # Unified correctness flag (numeric uses tolerance accuracy).
                "correct": within_tolerance,
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


def get_trend_prediction_value(prediction_row) -> object:
    """Trend predictions are textual; prefer prediction_text, fall back to the numeric column."""
    text = prediction_row.get("prediction_text", None)

    if text is not None and not pd.isna(text) and str(text).strip():
        return text

    return prediction_row.get("predicted_numeric_answer", None)


def evaluate_trend_predictions(
    examples: list[dict],
    predictions: pd.DataFrame,
    prediction_name: str,
) -> tuple[dict, pd.DataFrame]:
    prediction_map = {}

    for _, row in predictions.iterrows():
        prediction_map[row["id"]] = row

    detail_rows = []

    for example in examples:
        example_id = example["id"]
        gold_label = example["trend_class"]

        prediction_row = prediction_map.get(example_id)

        if prediction_row is None:
            predicted_label = None
            prediction_value = None
            missing_prediction = True
            invalid_prediction = False
            label_match = False
        else:
            prediction_value = get_trend_prediction_value(prediction_row)
            predicted_label = normalize_trend_label(prediction_value)

            missing_prediction = False
            invalid_prediction = predicted_label is None
            label_match = (predicted_label == gold_label)

        detail_rows.append(
            {
                "prediction_name": prediction_name,
                "answer_kind": "trend",
                "id": example_id,
                "domain": example["domain"],
                "input_format": example["input_format"],
                "chart_type": example["chart_type"],
                "question_type": example["question_type"],
                "difficulty": example["difficulty"],
                "split": example["split"],
                "question": example["question"],
                "gold_answer": example["answer"],
                "gold_label": gold_label,
                "prediction_text": None if prediction_value is None else str(prediction_value),
                "predicted_label": predicted_label,
                "missing_prediction": missing_prediction,
                "invalid_prediction": invalid_prediction,
                "correct": label_match,
            }
        )

    details = pd.DataFrame(detail_rows)

    report = {
        "prediction_name": prediction_name,
        "total_trend_examples": int(len(details)),
        "missing_predictions": int(details["missing_prediction"].sum()) if len(details) else 0,
        "invalid_predictions": int(details["invalid_prediction"].sum()) if len(details) else 0,
        "label_accuracy": float(details["correct"].mean()) if len(details) else 0.0,
        "by_input_format": summarize_trend_group(details, "input_format"),
        "by_domain": summarize_trend_group(details, "domain"),
    }

    return report, details


def summarize_trend_group(details: pd.DataFrame, group_column: str) -> dict:
    summary = {}

    if len(details) == 0:
        return summary

    for group_value, group_df in details.groupby(group_column):
        summary[str(group_value)] = {
            "count": int(len(group_df)),
            "missing_predictions": int(group_df["missing_prediction"].sum()),
            "invalid_predictions": int(group_df["invalid_prediction"].sum()),
            "label_accuracy": float(group_df["correct"].mean()),
        }

    return summary


def make_markdown_report(combined: dict) -> str:
    overall = combined["overall"]
    numeric = combined["numeric"]
    trend = combined["trend"]

    lines = []

    lines.append(f"# Evaluation Report: {combined['prediction_name']}")
    lines.append("")
    lines.append("## Overall Benchmark Results")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Evaluation split | {combined.get('evaluation_split', 'all')} |")
    lines.append(f"| Total scorable examples | {overall['total_scorable_examples']} |")
    lines.append(f"| Numeric examples | {overall['numeric_examples']} |")
    lines.append(f"| Trend examples | {overall['trend_examples']} |")
    lines.append(f"| Correct | {overall['correct']} |")
    lines.append(f"| Overall accuracy | {overall['accuracy']:.2%} |")
    lines.append("")
    lines.append(
        "_Overall accuracy combines numeric tolerance accuracy and trend label accuracy "
        "over every scorable example._"
    )

    if numeric["total_numeric_examples"] > 0:
        lines.append("")
        lines.append("## Numeric Results")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|---|---:|")
        lines.append(f"| Total numeric examples | {numeric['total_numeric_examples']} |")
        lines.append(f"| Provided predictions | {numeric['provided_predictions']} |")
        lines.append(f"| Missing predictions | {numeric['missing_predictions']} |")
        lines.append(f"| Invalid predictions | {numeric['invalid_predictions']} |")
        lines.append(f"| Extra predictions | {numeric['extra_predictions']} |")
        lines.append(f"| Exact accuracy | {numeric['exact_accuracy']:.2%} |")
        lines.append(f"| Tolerance accuracy | {numeric['tolerance_accuracy']:.2%} |")

        if numeric["mean_absolute_error"] is not None:
            lines.append(f"| Mean absolute error | {numeric['mean_absolute_error']:.4f} |")

        if numeric["median_absolute_error"] is not None:
            lines.append(f"| Median absolute error | {numeric['median_absolute_error']:.4f} |")

        lines.append("")
        lines.append("### Numeric Results by Question Type")
        lines.append("")
        lines.append("| Question type | Count | Exact accuracy | Tolerance accuracy | Mean absolute error |")
        lines.append("|---|---:|---:|---:|---:|")

        for key, value in numeric["by_question_type"].items():
            mae = value["mean_absolute_error"]
            mae_text = "" if mae is None else f"{mae:.4f}"
            lines.append(
                f"| {key} | {value['count']} | {value['exact_accuracy']:.2%} | "
                f"{value['tolerance_accuracy']:.2%} | {mae_text} |"
            )

        lines.append("")
        lines.append("### Numeric Results by Input Format")
        lines.append("")
        lines.append("| Input format | Count | Exact accuracy | Tolerance accuracy |")
        lines.append("|---|---:|---:|---:|")

        for key, value in numeric["by_input_format"].items():
            lines.append(
                f"| {key} | {value['count']} | {value['exact_accuracy']:.2%} | "
                f"{value['tolerance_accuracy']:.2%} |"
            )

        lines.append("")
        lines.append("### Numeric Results by Domain")
        lines.append("")
        lines.append("| Domain | Count | Exact accuracy | Tolerance accuracy |")
        lines.append("|---|---:|---:|---:|")

        for key, value in numeric["by_domain"].items():
            lines.append(
                f"| {key} | {value['count']} | {value['exact_accuracy']:.2%} | "
                f"{value['tolerance_accuracy']:.2%} |"
            )

    if trend["total_trend_examples"] > 0:
        lines.append("")
        lines.append("## Trend (Categorical) Results")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|---|---:|")
        lines.append(f"| Total trend examples | {trend['total_trend_examples']} |")
        lines.append(f"| Missing predictions | {trend['missing_predictions']} |")
        lines.append(f"| Invalid predictions | {trend['invalid_predictions']} |")
        lines.append(f"| Label accuracy | {trend['label_accuracy']:.2%} |")

        lines.append("")
        lines.append("### Trend Results by Input Format")
        lines.append("")
        lines.append("| Input format | Count | Label accuracy |")
        lines.append("|---|---:|---:|")

        for key, value in trend["by_input_format"].items():
            lines.append(f"| {key} | {value['count']} | {value['label_accuracy']:.2%} |")

        lines.append("")
        lines.append("### Trend Results by Domain")
        lines.append("")
        lines.append("| Domain | Count | Label accuracy |")
        lines.append("|---|---:|---:|")

        for key, value in trend["by_domain"].items():
            lines.append(f"| {key} | {value['count']} | {value['label_accuracy']:.2%} |")

    if numeric["extra_prediction_ids_sample"]:
        lines.append("")
        lines.append("## Extra Prediction IDs Sample")
        lines.append("")
        for item in numeric["extra_prediction_ids_sample"]:
            lines.append(f"- `{item}`")

    if numeric["missing_prediction_ids_sample"]:
        lines.append("")
        lines.append("## Missing Numeric Prediction IDs Sample")
        lines.append("")
        for item in numeric["missing_prediction_ids_sample"]:
            lines.append(f"- `{item}`")

    lines.append("")

    return "\n".join(lines)


def save_json(data: dict, path: Path) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate prediction CSV files against TR-DataAnalystBench synthetic_v01. "
            "Scores numeric examples (tolerance) and trend examples (categorical label)."
        )
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
    help="Dataset split to evaluate. Use 'all' to evaluate all scorable examples.",
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
    trend_examples_all = get_trend_examples(examples)

    if args.split == "all":
        numeric_examples = numeric_examples_all
        trend_examples = trend_examples_all
    else:
        numeric_examples = [e for e in numeric_examples_all if e.get("split") == args.split]
        trend_examples = [e for e in trend_examples_all if e.get("split") == args.split]

    predictions = load_predictions(predictions_path)

    # When evaluating a specific split, ignore predictions from other splits.
    # Each evaluator only sees the prediction rows relevant to its own example ids.
    numeric_ids = {example["id"] for example in numeric_examples}
    trend_ids = {example["id"] for example in trend_examples}

    numeric_predictions = predictions[predictions["id"].isin(numeric_ids)].copy()
    trend_predictions = predictions[predictions["id"].isin(trend_ids)].copy()

    numeric_report, numeric_details = evaluate_predictions(
        examples=numeric_examples,
        predictions=numeric_predictions,
        prediction_name=prediction_name,
    )

    trend_report, trend_details = evaluate_trend_predictions(
        examples=trend_examples,
        predictions=trend_predictions,
        prediction_name=prediction_name,
    )

    correct_numeric = int(numeric_details["correct"].sum()) if len(numeric_details) else 0
    correct_trend = int(trend_details["correct"].sum()) if len(trend_details) else 0
    total_scorable = len(numeric_examples) + len(trend_examples)
    total_correct = correct_numeric + correct_trend

    combined = {
        "prediction_name": prediction_name,
        "evaluation_split": args.split,
        "overall": {
            "total_scorable_examples": total_scorable,
            "numeric_examples": len(numeric_examples),
            "trend_examples": len(trend_examples),
            "correct": total_correct,
            "accuracy": (total_correct / total_scorable) if total_scorable else 0.0,
        },
        "numeric": numeric_report,
        "trend": trend_report,
    }

    # Unified per-example details (numeric + trend) sharing a 'correct' column.
    details = pd.concat([numeric_details, trend_details], ignore_index=True)

    details_path = output_dir / f"{prediction_name}_details.csv"
    report_json_path = output_dir / f"{prediction_name}_report.json"
    report_md_path = output_dir / f"{prediction_name}_report.md"

    details.to_csv(details_path, index=False, encoding="utf-8-sig")
    save_json(combined, report_json_path)
    report_md_path.write_text(make_markdown_report(combined), encoding="utf-8")

    overall = combined["overall"]

    print("Prediction file evaluation completed successfully.")
    print(f"Prediction name: {prediction_name}")
    print(f"Dataset: {dataset_path}")
    print(f"Predictions: {predictions_path}")
    print(f"Evaluation split: {args.split}")
    print()
    print("Overall benchmark results:")
    print(f"  Total scorable examples: {overall['total_scorable_examples']}")
    print(f"  Numeric examples: {overall['numeric_examples']}")
    print(f"  Trend examples: {overall['trend_examples']}")
    print(f"  Overall accuracy: {overall['accuracy']:.2%}")
    print()
    print("Numeric:")
    print(f"  Exact accuracy: {numeric_report['exact_accuracy']:.2%}")
    print(f"  Tolerance accuracy: {numeric_report['tolerance_accuracy']:.2%}")
    print(f"  Missing: {numeric_report['missing_predictions']}  Invalid: {numeric_report['invalid_predictions']}")
    print()
    print("Trend (categorical):")
    print(f"  Label accuracy: {trend_report['label_accuracy']:.2%}")
    print(f"  Missing: {trend_report['missing_predictions']}  Invalid: {trend_report['invalid_predictions']}")
    print()
    print(f"Details CSV: {details_path}")
    print(f"Report JSON: {report_json_path}")
    print(f"Report Markdown: {report_md_path}")


if __name__ == "__main__":
    main()