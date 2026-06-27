import json
import random
from pathlib import Path

import pandas as pd


RANDOM_SEED = 42
random.seed(RANDOM_SEED)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATASET_PATH = PROJECT_ROOT / "data" / "processed" / "synthetic_v01.jsonl"

EXPORTS_DIR = PROJECT_ROOT / "data" / "exports"
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

ORACLE_PREDICTIONS_PATH = EXPORTS_DIR / "synthetic_v01_oracle_predictions.csv"
NOISY_PREDICTIONS_PATH = EXPORTS_DIR / "synthetic_v01_noisy_baseline_predictions.csv"

SCORING_DETAILS_PATH = EXPORTS_DIR / "synthetic_v01_scoring_details.csv"
SCORING_REPORT_PATH = EXPORTS_DIR / "synthetic_v01_scoring_report.json"


def load_jsonl(path: Path) -> list[dict]:
    examples = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            examples.append(json.loads(line))

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


# Makine-okunur trend sınıfı -> Türkçe tek kelime (oracle/noisy üretimi için).
TREND_CLASS_TO_WORD = {
    "increasing": "artış",
    "decreasing": "azalış",
    "mixed": "dalgalı",
}

TREND_WORDS = list(TREND_CLASS_TO_WORD.values())


def normalize_trend_label(text) -> str | None:
    if text is None:
        return None

    text = str(text).strip().lower()

    if not text:
        return None

    if any(k in text for k in ["dalgal", "karış", "karis", "mixed"]):
        return "mixed"

    if any(k in text for k in ["azal", "düş", "dus", "decreas"]):
        return "decreasing"

    if any(k in text for k in ["art", "yüksel", "yuksel", "increas"]):
        return "increasing"

    return None


def create_oracle_predictions(examples: list[dict]) -> pd.DataFrame:
    rows = []

    for example in examples:
        gold = example["numeric_answer"]

        rows.append(
            {
                "id": example["id"],
                "predicted_numeric_answer": gold,
                "prediction_text": str(gold),
                "prediction_source": "oracle",
            }
        )

    return pd.DataFrame(rows)


def perturb_numeric_answer(example: dict) -> float:
    gold = float(example["numeric_answer"])
    question_type = example["question_type"]

    # Bazı soru tipleri daha kolay, bazıları daha zor gibi davranıyoruz.
    correct_probability_by_type = {
        "value_lookup": 0.85,
        "max_min": 0.80,
        "comparison": 0.65,
        "percentage_change": 0.55,
    }

    correct_probability = correct_probability_by_type.get(question_type, 0.65)

    # Bazen doğru cevabı aynen döndür.
    if random.random() < correct_probability:
        return gold

    # Yanlış cevap üret.
    if question_type == "percentage_change":
        # Percentage change için hata yüzde puanı cinsinden olsun.
        error = random.choice([-1, 1]) * random.uniform(2.5, 12.0)
        return round(gold + error, 1)

    # Diğer numeric tasklarda oransal hata üret.
    relative_error = random.choice([-1, 1]) * random.uniform(0.03, 0.15)
    predicted = gold * (1 + relative_error)

    return round(predicted)


def create_noisy_baseline_predictions(examples: list[dict]) -> pd.DataFrame:
    rows = []

    for example in examples:
        predicted = perturb_numeric_answer(example)

        rows.append(
            {
                "id": example["id"],
                "predicted_numeric_answer": predicted,
                "prediction_text": str(predicted),
                "prediction_source": "noisy_baseline",
            }
        )

    return pd.DataFrame(rows)


def create_oracle_trend_predictions(examples: list[dict]) -> pd.DataFrame:
    rows = []

    for example in examples:
        word = TREND_CLASS_TO_WORD[example["trend_class"]]

        rows.append(
            {
                "id": example["id"],
                "predicted_numeric_answer": "",
                "prediction_text": word,
                "prediction_source": "oracle",
            }
        )

    return pd.DataFrame(rows)


def create_noisy_trend_predictions(examples: list[dict]) -> pd.DataFrame:
    rows = []

    for example in examples:
        gold_word = TREND_CLASS_TO_WORD[example["trend_class"]]

        if random.random() < 0.7:
            word = gold_word
        else:
            other_words = [w for w in TREND_WORDS if w != gold_word]
            word = random.choice(other_words)

        rows.append(
            {
                "id": example["id"],
                "predicted_numeric_answer": "",
                "prediction_text": word,
                "prediction_source": "noisy_baseline",
            }
        )

    return pd.DataFrame(rows)


def evaluate_trend(examples: list[dict], predictions: pd.DataFrame, prediction_name: str) -> tuple[dict, int]:
    prediction_map = {row["id"]: row for _, row in predictions.iterrows()}

    correct = 0

    for example in examples:
        prediction_row = prediction_map.get(example["id"])

        if prediction_row is None:
            continue

        predicted_label = normalize_trend_label(prediction_row.get("prediction_text"))

        if predicted_label == example["trend_class"]:
            correct += 1

    total = len(examples)
    accuracy = correct / total if total else 0.0

    report = {
        "prediction_name": prediction_name,
        "total_trend_examples": total,
        "label_accuracy": accuracy,
    }

    return report, correct


def is_exact_match(gold: float, predicted: float) -> bool:
    return abs(float(gold) - float(predicted)) < 1e-9


def is_within_tolerance(example: dict, predicted: float) -> bool:
    gold = float(example["numeric_answer"])
    predicted = float(predicted)

    absolute_error = abs(predicted - gold)

    if example["question_type"] == "percentage_change":
        # Yüzde değişim sorularında ±2 yüzde puanı tolerans.
        return absolute_error <= 2.0

    # Büyük sayılarda %2 tolerans.
    # Küçük sayılarda ise absolute tolerance en az 1 olsun.
    relative_error = absolute_error / max(abs(gold), 1.0)

    return relative_error <= 0.02 or absolute_error <= 1.0


def safe_float(value) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except ValueError:
        return None
    except TypeError:
        return None


def evaluate_predictions(
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
        gold = float(example["numeric_answer"])

        prediction_row = prediction_map.get(example_id)

        if prediction_row is None:
            predicted = None
            missing = True
            exact = False
            within_tolerance = False
            absolute_error = None
            relative_error = None
        else:
            predicted = safe_float(prediction_row["predicted_numeric_answer"])
            missing = predicted is None

            if missing:
                exact = False
                within_tolerance = False
                absolute_error = None
                relative_error = None
            else:
                absolute_error = abs(predicted - gold)
                relative_error = absolute_error / max(abs(gold), 1.0)
                exact = is_exact_match(gold, predicted)
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
                "gold_numeric_answer": gold,
                "predicted_numeric_answer": predicted,
                "missing_prediction": missing,
                "exact_match": exact,
                "within_tolerance": within_tolerance,
                "absolute_error": absolute_error,
                "relative_error": relative_error,
            }
        )

    details = pd.DataFrame(detail_rows)

    report = {
        "prediction_name": prediction_name,
        "total_examples": int(len(details)),
        "missing_predictions": int(details["missing_prediction"].sum()),
        "exact_accuracy": float(details["exact_match"].mean()),
        "tolerance_accuracy": float(details["within_tolerance"].mean()),
        "mean_absolute_error": float(details["absolute_error"].dropna().mean()),
        "median_absolute_error": float(details["absolute_error"].dropna().median()),
        "by_question_type": summarize_group(details, "question_type"),
        "by_input_format": summarize_group(details, "input_format"),
        "by_domain": summarize_group(details, "domain"),
    }

    return report, details


def summarize_group(details: pd.DataFrame, group_column: str) -> dict:
    summary = {}

    for group_value, group_df in details.groupby(group_column):
        summary[str(group_value)] = {
            "count": int(len(group_df)),
            "exact_accuracy": float(group_df["exact_match"].mean()),
            "tolerance_accuracy": float(group_df["within_tolerance"].mean()),
            "mean_absolute_error": float(group_df["absolute_error"].dropna().mean()),
        }

    return summary


def save_json(data: dict, path: Path) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATASET_PATH}")

    examples = load_jsonl(DATASET_PATH)
    numeric_examples = get_numeric_examples(examples)
    trend_examples = get_trend_examples(examples)

    # Oracle/noisy predictions cover the full benchmark (numeric + trend).
    oracle_predictions = pd.concat(
        [create_oracle_predictions(numeric_examples), create_oracle_trend_predictions(trend_examples)],
        ignore_index=True,
    )
    noisy_predictions = pd.concat(
        [create_noisy_baseline_predictions(numeric_examples), create_noisy_trend_predictions(trend_examples)],
        ignore_index=True,
    )

    oracle_predictions.to_csv(ORACLE_PREDICTIONS_PATH, index=False, encoding="utf-8-sig")
    noisy_predictions.to_csv(NOISY_PREDICTIONS_PATH, index=False, encoding="utf-8-sig")

    oracle_report, oracle_details = evaluate_predictions(
        examples=numeric_examples,
        predictions=oracle_predictions,
        prediction_name="oracle",
    )

    noisy_report, noisy_details = evaluate_predictions(
        examples=numeric_examples,
        predictions=noisy_predictions,
        prediction_name="noisy_baseline",
    )

    oracle_trend_report, oracle_trend_correct = evaluate_trend(
        trend_examples, oracle_predictions, "oracle"
    )
    noisy_trend_report, noisy_trend_correct = evaluate_trend(
        trend_examples, noisy_predictions, "noisy_baseline"
    )

    all_details = pd.concat([oracle_details, noisy_details], ignore_index=True)
    all_details.to_csv(SCORING_DETAILS_PATH, index=False, encoding="utf-8-sig")

    total_scorable = len(numeric_examples) + len(trend_examples)

    def overall_accuracy(numeric_report: dict, trend_correct: int) -> float:
        numeric_correct = numeric_report["tolerance_accuracy"] * len(numeric_examples)
        return (numeric_correct + trend_correct) / total_scorable if total_scorable else 0.0

    full_report = {
        "dataset_path": str(DATASET_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "total_dataset_examples": len(examples),
        "total_numeric_examples": len(numeric_examples),
        "total_trend_examples": len(trend_examples),
        "total_scorable_examples": total_scorable,
        "reports": {
            "oracle": {
                "numeric": oracle_report,
                "trend": oracle_trend_report,
                "overall_accuracy": overall_accuracy(oracle_report, oracle_trend_correct),
            },
            "noisy_baseline": {
                "numeric": noisy_report,
                "trend": noisy_trend_report,
                "overall_accuracy": overall_accuracy(noisy_report, noisy_trend_correct),
            },
        },
        "output_files": {
            "oracle_predictions": str(ORACLE_PREDICTIONS_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "noisy_predictions": str(NOISY_PREDICTIONS_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "scoring_details": str(SCORING_DETAILS_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "scoring_report": str(SCORING_REPORT_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        },
    }

    save_json(full_report, SCORING_REPORT_PATH)

    print("Benchmark scoring completed successfully.")
    print(f"Total dataset examples: {len(examples)}")
    print(f"Numeric examples scored: {len(numeric_examples)}")
    print(f"Trend examples scored: {len(trend_examples)}")
    print(f"Total scorable examples: {total_scorable}")
    print()
    print("Oracle results:")
    print(f"  Numeric tolerance accuracy: {oracle_report['tolerance_accuracy']:.2%}")
    print(f"  Trend label accuracy: {oracle_trend_report['label_accuracy']:.2%}")
    print(f"  Overall accuracy: {overall_accuracy(oracle_report, oracle_trend_correct):.2%}")
    print()
    print("Noisy baseline results:")
    print(f"  Numeric tolerance accuracy: {noisy_report['tolerance_accuracy']:.2%}")
    print(f"  Trend label accuracy: {noisy_trend_report['label_accuracy']:.2%}")
    print(f"  Overall accuracy: {overall_accuracy(noisy_report, noisy_trend_correct):.2%}")
    print()
    print(f"Oracle predictions: {ORACLE_PREDICTIONS_PATH}")
    print(f"Noisy predictions: {NOISY_PREDICTIONS_PATH}")
    print(f"Scoring details: {SCORING_DETAILS_PATH}")
    print(f"Scoring report: {SCORING_REPORT_PATH}")


if __name__ == "__main__":
    main()