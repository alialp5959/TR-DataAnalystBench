"""Validate chart_hard_v01 (recompute every gold answer from the table)."""

import json
import re
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = PROJECT_ROOT / "data" / "processed" / "chart_hard_v01.jsonl"

QUESTION_TYPES = {
    "value_estimate", "second_highest_year", "count_above",
    "closest_compare", "cross_closest_year", "trend_summary",
}
REQUIRED = [
    "id", "dataset_version", "language", "domain", "input_format", "chart_type",
    "chart_path", "question_type", "difficulty", "table", "target_column", "unit",
    "split", "question", "answer", "answer_type", "numeric_answer", "calculation",
]


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
    if abs(net) / max(abs(values[0]), 1) >= 0.05:
        if net > 0 and inc > dec:
            return "increasing"
        if net < 0 and dec > inc:
            return "decreasing"
    return "mixed"


def validate(e, i):
    errs = []
    for f in REQUIRED:
        if f not in e:
            errs.append(f"{i}: missing '{f}'")
    if errs:
        return errs

    if e["input_format"] != "chart_only":
        errs.append(f"{i}: must be chart_only")
    if e["question_type"] not in QUESTION_TYPES:
        errs.append(f"{i}: bad question_type")
    if not (PROJECT_ROOT / e["chart_path"]).exists():
        errs.append(f"{i}: chart missing")

    rows = e["table"]["rows"]
    years = [r[0] for r in rows]
    a = [r[1] for r in rows]
    b = [r[2] for r in rows]
    rows_a = list(zip(years, a))
    qt = e["question_type"]
    g = e["numeric_answer"]

    if qt == "trend_summary":
        if e["answer_type"] != "text" or e.get("trend_class") != detect_trend(a):
            errs.append(f"{i}: trend mismatch")
        return errs

    if "numeric_tolerance" not in e or "numeric_abs_tolerance" not in e:
        errs.append(f"{i}: numeric task must set tolerances")

    if qt == "value_estimate":
        if g not in a:
            errs.append(f"{i}: value_estimate gold not a real value")
        if abs(e.get("numeric_tolerance", 0) - 0.05) > 1e-9:
            errs.append(f"{i}: value_estimate tolerance should be 0.05")
    elif qt == "second_highest_year":
        exp = sorted(rows_a, key=lambda r: r[1], reverse=True)[1][0]
        if g != exp:
            errs.append(f"{i}: second_highest_year {g} != {exp}")
    elif qt == "count_above":
        m = re.search(r">\s*(\d+(?:\.\d+)?)\s*->", e["calculation"])
        if not m:
            errs.append(f"{i}: threshold unparseable")
        elif g != sum(1 for v in a if v > float(m.group(1))):
            errs.append(f"{i}: count_above mismatch")
    elif qt == "closest_compare":
        yy = [int(x) for x in re.findall(r"\b(\d{4})\b", e["question"])]
        if len(yy) >= 2:
            va, vb = a[years.index(yy[0])], a[years.index(yy[1])]
            exp = yy[0] if va > vb else yy[1]
            if g != exp:
                errs.append(f"{i}: closest_compare {g} != {exp}")
        else:
            errs.append(f"{i}: closest_compare years unparseable")
    elif qt == "cross_closest_year":
        exp = min(zip(years, a, b), key=lambda r: abs(r[1] - r[2]))[0]
        if g != exp:
            errs.append(f"{i}: cross_closest_year {g} != {exp}")

    return errs


def main():
    if not DATASET_PATH.exists():
        raise FileNotFoundError(DATASET_PATH)
    examples = load(DATASET_PATH)
    errors = []
    for i, e in enumerate(examples, 1):
        errors.extend(validate(e, i))

    print("=" * 60)
    print("chart_hard_v01 validation")
    print("=" * 60)
    print(f"Total: {len(examples)}")
    print(f"  question_type: {dict(Counter(e.get('question_type') for e in examples))}")
    print(f"  split: {dict(Counter(e.get('split') for e in examples))}")

    if errors:
        print(f"\nFAILED ({len(errors)}):")
        for err in errors[:40]:
            print("  -", err)
        raise SystemExit(1)
    print("\nValidation passed. No issues found.")


if __name__ == "__main__":
    main()
