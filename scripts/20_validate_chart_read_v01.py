"""Validate the chart_read_v01 tier (recomputes every gold answer)."""

import json
import re
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = PROJECT_ROOT / "data" / "processed" / "chart_read_v01.jsonl"

REQUIRED = [
    "id", "dataset_version", "language", "domain", "input_format", "chart_type",
    "chart_path", "question_type", "difficulty", "table", "target_column", "unit",
    "split", "question", "answer", "answer_type", "numeric_answer", "calculation",
]
QUESTION_TYPES = {"max_min_year", "compare_years", "count_above", "value_estimate", "trend_summary"}
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


def validate(e, i):
    errs = []
    for f in REQUIRED:
        if f not in e:
            errs.append(f"{i}: missing '{f}'")
    if errs:
        return errs

    if e["input_format"] != "chart_only":
        errs.append(f"{i}: chart_read must be chart_only (label-free)")
    if e["question_type"] not in QUESTION_TYPES:
        errs.append(f"{i}: bad question_type {e['question_type']}")
    if not (PROJECT_ROOT / e["chart_path"]).exists():
        errs.append(f"{i}: chart missing")

    rows = e["table"]["rows"]
    years = [r[0] for r in rows]
    values = [r[1] for r in rows]
    qt = e["question_type"]
    g = e["numeric_answer"]

    if qt == "trend_summary":
        if e["answer_type"] != "text" or e.get("trend_class") != detect_trend(values):
            errs.append(f"{i}: trend mismatch")
        return errs

    # all numeric tasks must declare explicit tolerances
    if "numeric_tolerance" not in e or "numeric_abs_tolerance" not in e:
        errs.append(f"{i}: numeric task must set numeric_tolerance/abs_tolerance")

    if qt == "max_min_year":
        want_max = "en yüksek" in e["question"]
        target = max(rows, key=lambda r: r[1]) if want_max else min(rows, key=lambda r: r[1])
        if g != target[0]:
            errs.append(f"{i}: max_min_year gold {g} != {target[0]}")
    elif qt == "compare_years":
        yy = [int(x) for x in re.findall(r"\b(20\d\d)\b", e["question"])]
        if len(yy) >= 2:
            va = values[years.index(yy[0])]
            vb = values[years.index(yy[1])]
            higher = yy[0] if va > vb else yy[1]
            if g != higher:
                errs.append(f"{i}: compare_years gold {g} != {higher}")
        else:
            errs.append(f"{i}: compare_years could not parse two years")
    elif qt == "count_above":
        m = re.search(r">\s*(\d+(?:\.\d+)?)\s*->", e["calculation"])
        if not m:
            errs.append(f"{i}: count_above threshold not parseable")
        else:
            thr = float(m.group(1))
            if g != sum(1 for v in values if v > thr):
                errs.append(f"{i}: count_above gold mismatch")
    elif qt == "value_estimate":
        if g not in values:
            errs.append(f"{i}: value_estimate gold not a real value")
        if abs(e.get("numeric_tolerance", 0) - 0.08) > 1e-9:
            errs.append(f"{i}: value_estimate tolerance should be 0.08")

    return errs


def main():
    if not DATASET_PATH.exists():
        raise FileNotFoundError(DATASET_PATH)
    examples = load(DATASET_PATH)
    errors = []
    for i, e in enumerate(examples, 1):
        errors.extend(validate(e, i))

    print("=" * 60)
    print("chart_read_v01 validation")
    print("=" * 60)
    print(f"Total: {len(examples)}")
    print(f"  question_type: {dict(Counter(e.get('question_type') for e in examples))}")
    print(f"  split: {dict(Counter(e.get('split') for e in examples))}")
    if any(e.get("input_format") != "chart_only" for e in examples):
        errors.append("not all chart_only")

    if errors:
        print(f"\nFAILED ({len(errors)}):")
        for err in errors[:40]:
            print("  -", err)
        raise SystemExit(1)
    print("\nValidation passed. No issues found.")


if __name__ == "__main__":
    main()
