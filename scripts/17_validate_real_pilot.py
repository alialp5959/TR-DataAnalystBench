"""Validate the real_pilot dataset.

Recomputes the gold answer for every task directly from the table (so a
generator bug is caught), checks the schema, and verifies that each example
carries source/license provenance.
"""

import json
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = PROJECT_ROOT / "data" / "processed" / "real_pilot.jsonl"

ALLOWED_QUESTION_TYPES = {
    "value_lookup", "comparison", "percentage_change",
    "average", "nth_highest", "trend_summary", "unanswerable",
}
ALLOWED_ANSWER_TYPES = {"numeric", "numeric_with_label", "text", "abstention"}
ALLOWED_SPLITS = {"train", "validation", "test"}

REQUIRED_FIELDS = [
    "id", "dataset_version", "language", "domain", "source_name", "source_url",
    "license", "country", "input_format", "chart_type", "chart_path",
    "question_type", "difficulty", "table", "target_column", "unit", "split",
    "question", "answer", "answer_type", "numeric_answer", "calculation",
]

TREND_NET_CHANGE_THRESHOLD = 0.05


def load_jsonl(path: Path) -> list[dict]:
    out = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def detect_trend(values):
    inc = sum(1 for a, b in zip(values, values[1:]) if b > a)
    dec = sum(1 for a, b in zip(values, values[1:]) if b < a)
    if dec == 0 and inc > 0:
        return "increasing"
    if inc == 0 and dec > 0:
        return "decreasing"
    net = values[-1] - values[0]
    ratio = abs(net) / max(abs(values[0]), 1)
    if ratio >= TREND_NET_CHANGE_THRESHOLD:
        if net > 0 and inc > dec:
            return "increasing"
        if net < 0 and dec > inc:
            return "decreasing"
    return "mixed"


def approx(a, b):
    return abs(a - b) <= max(abs(b) * 0.01, 1.0)


def validate(example, index):
    errors = []
    for field in REQUIRED_FIELDS:
        if field not in example:
            errors.append(f"{index}: missing '{field}'")
    if errors:
        return errors

    if example["question_type"] not in ALLOWED_QUESTION_TYPES:
        errors.append(f"{index}: bad question_type")
    if example["answer_type"] not in ALLOWED_ANSWER_TYPES:
        errors.append(f"{index}: bad answer_type")
    if example["split"] not in ALLOWED_SPLITS:
        errors.append(f"{index}: bad split")
    if not str(example.get("license", "")).strip() or example["license"] == "unknown":
        errors.append(f"{index}: missing/unknown license")
    if not str(example.get("source_url", "")).strip():
        errors.append(f"{index}: missing source_url")

    chart = PROJECT_ROOT / example["chart_path"]
    if not chart.exists():
        errors.append(f"{index}: chart missing {example['chart_path']}")

    values = [row[1] for row in example["table"]["rows"]]
    qt = example["question_type"]
    gold = example.get("numeric_answer")

    if qt == "unanswerable":
        if example["answer_type"] != "abstention" or gold is not None:
            errors.append(f"{index}: unanswerable must be abstention with null numeric_answer")
        return errors

    if qt == "trend_summary":
        if example.get("trend_class") != detect_trend(values):
            errors.append(f"{index}: trend_class != recomputed ({example.get('trend_class')} vs {detect_trend(values)})")
        return errors

    if not isinstance(gold, (int, float)):
        errors.append(f"{index}: {qt} needs numeric gold")
        return errors

    if qt == "value_lookup" and gold not in values:
        errors.append(f"{index}: value_lookup gold not in column")
    elif qt == "comparison" and round(abs(values[-1] - values[0]), 2) != round(gold, 2):
        errors.append(f"{index}: comparison gold mismatch")
    elif qt == "average" and not approx(sum(values) / len(values), gold):
        errors.append(f"{index}: average gold mismatch")
    elif qt == "nth_highest" and sorted(values, reverse=True)[1] != gold:
        errors.append(f"{index}: nth_highest gold mismatch")
    elif qt == "percentage_change":
        exp = round(((values[-1] - values[0]) / values[0]) * 100, 1)
        if exp != gold:
            errors.append(f"{index}: percentage_change gold mismatch ({gold} vs {exp})")

    return errors


def main():
    if not DATASET_PATH.exists():
        raise FileNotFoundError(DATASET_PATH)

    examples = load_jsonl(DATASET_PATH)
    errors = []
    for i, example in enumerate(examples, start=1):
        errors.extend(validate(example, i))

    ids = [e["id"] for e in examples]
    if len(ids) != len(set(ids)):
        errors.append("duplicate ids found")

    print("=" * 60)
    print("real_pilot validation")
    print("=" * 60)
    print(f"Total examples: {len(examples)}")
    for key in ["domain", "source_name", "question_type", "answer_type", "split"]:
        print(f"  {key}: {dict(Counter(e.get(key) for e in examples))}")
    print(f"  licenses: {dict(Counter(e.get('license') for e in examples))}")

    if errors:
        print(f"\nValidation FAILED ({len(errors)} errors):")
        for error in errors[:40]:
            print(f"  - {error}")
        raise SystemExit(1)

    print("\nValidation passed. No issues found.")


if __name__ == "__main__":
    main()
