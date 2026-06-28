"""Validate real_anon_v01: recompute every gold answer and verify anonymization."""

import json
import re
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = PROJECT_ROOT / "data" / "processed" / "real_anon_v01.jsonl"

QUESTION_TYPES = {
    "value_lookup", "comparison", "percentage_change",
    "average", "nth_highest", "trend_summary", "unanswerable",
}
REQUIRED = [
    "id", "dataset_version", "language", "domain", "source_name", "license",
    "anonymized", "input_format", "chart_type", "chart_path", "question_type",
    "difficulty", "table", "target_column", "unit", "split", "question",
    "answer", "answer_type", "numeric_answer", "calculation",
]
TREND_NET_CHANGE_THRESHOLD = 0.05


def load(path):
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def detect_trend(values):
    inc = sum(1 for a, b in zip(values, values[1:]) if b > a)
    dec = sum(1 for a, b in zip(values, values[1:]) if b < a)
    if dec == 0 and inc > 0:
        return "increasing"
    if inc == 0 and dec > 0:
        return "decreasing"
    net = values[-1] - values[0]
    if abs(net) / max(abs(values[0]), 1) >= TREND_NET_CHANGE_THRESHOLD:
        if net > 0 and inc > dec:
            return "increasing"
        if net < 0 and dec > inc:
            return "decreasing"
    return "mixed"


def approx(a, b):
    return abs(a - b) <= max(abs(b) * 0.01, 1.0)


def validate(e, i):
    errs = []
    for f in REQUIRED:
        if f not in e:
            errs.append(f"{i}: missing '{f}'")
    if errs:
        return errs

    if e["question_type"] not in QUESTION_TYPES:
        errs.append(f"{i}: bad question_type")
    if e.get("anonymized") is not True:
        errs.append(f"{i}: anonymized flag must be true")
    if e["table"]["columns"][0] != "Dönem":
        errs.append(f"{i}: first column must be 'Dönem' (no absolute years)")
    if not (PROJECT_ROOT / e["chart_path"]).exists():
        errs.append(f"{i}: chart missing")

    # Anonymization leak check: questions/answers must not reveal country or year.
    blob = (e["question"] + " " + e["answer"]).lower()
    if "türkiye" in blob or "turkiye" in blob:
        errs.append(f"{i}: leaks country name")
    if re.search(r"\b(19|20)\d\d\b", blob):
        errs.append(f"{i}: leaks an absolute year")

    values = [row[1] for row in e["table"]["rows"]]
    qt = e["question_type"]
    g = e["numeric_answer"]

    if qt == "unanswerable":
        if e["answer_type"] != "abstention" or g is not None:
            errs.append(f"{i}: unanswerable must be abstention/null")
        return errs
    if qt == "trend_summary":
        if e["answer_type"] != "text" or e.get("trend_class") != detect_trend(values):
            errs.append(f"{i}: trend mismatch")
        return errs

    if not isinstance(g, (int, float)):
        errs.append(f"{i}: numeric gold missing")
        return errs

    if qt == "value_lookup" and g not in values:
        errs.append(f"{i}: value_lookup gold not in column")
    elif qt == "comparison" and round(abs(values[-1] - values[0]), 2) != round(g, 2):
        errs.append(f"{i}: comparison mismatch")
    elif qt == "average" and not approx(sum(values) / len(values), g):
        errs.append(f"{i}: average mismatch")
    elif qt == "nth_highest" and sorted(values, reverse=True)[1] != g:
        errs.append(f"{i}: nth_highest mismatch")
    elif qt == "percentage_change":
        exp = round(((values[-1] - values[0]) / values[0]) * 100, 1)
        if exp != g:
            errs.append(f"{i}: percentage_change mismatch ({g} vs {exp})")
    return errs


def main():
    if not DATASET_PATH.exists():
        raise FileNotFoundError(DATASET_PATH)
    examples = load(DATASET_PATH)
    errors = []
    for i, e in enumerate(examples, 1):
        errors.extend(validate(e, i))

    print("=" * 60)
    print("real_anon_v01 validation")
    print("=" * 60)
    print(f"Total: {len(examples)}")
    print(f"  question_type: {dict(Counter(e.get('question_type') for e in examples))}")
    print(f"  split: {dict(Counter(e.get('split') for e in examples))}")

    if errors:
        print(f"\nFAILED ({len(errors)}):")
        for err in errors[:40]:
            print("  -", err)
        raise SystemExit(1)
    print("\nValidation passed. No issues found (incl. anonymization).")


if __name__ == "__main__":
    main()
