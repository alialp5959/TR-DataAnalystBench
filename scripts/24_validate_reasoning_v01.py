"""Validate reasoning_v01 (recompute every gold answer from the table)."""

import json
import re
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = PROJECT_ROOT / "data" / "processed" / "reasoning_v01.jsonl"

QUESTION_TYPES = {
    "cagr", "fastest_change_year", "longest_increase_streak",
    "conditional_average", "share_of_total", "ratio",
}
REQUIRED = [
    "id", "dataset_version", "language", "domain", "input_format", "question_type",
    "difficulty", "table", "target_column", "unit", "split", "question", "answer",
    "answer_type", "numeric_answer", "numeric_tolerance", "numeric_abs_tolerance",
    "calculation",
]


def load(path):
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def longest_streak(vals):
    best = cur = 0
    for i in range(1, len(vals)):
        cur = cur + 1 if vals[i] > vals[i - 1] else 0
        best = max(best, cur)
    return best


def approx(a, b, rel=0.01, ab=1.0):
    return abs(a - b) <= max(abs(b) * rel, ab)


def validate(e, i):
    errs = []
    for f in REQUIRED:
        if f not in e:
            errs.append(f"{i}: missing '{f}'")
    if errs:
        return errs

    if e["question_type"] not in QUESTION_TYPES:
        errs.append(f"{i}: bad question_type")
    if e["input_format"] != "table_only":
        errs.append(f"{i}: reasoning_v01 must be table_only")

    rows = e["table"]["rows"]
    years = [r[0] for r in rows]
    a = [r[1] for r in rows]
    b = [r[2] for r in rows] if len(e["table"]["columns"]) > 2 else None
    n = len(years)
    qt = e["question_type"]
    g = e["numeric_answer"]

    if qt == "cagr":
        exp = round((((a[-1] / a[0]) ** (1 / (n - 1))) - 1) * 100, 1)
        if exp != g:
            errs.append(f"{i}: cagr {g} != {exp}")
    elif qt == "fastest_change_year":
        deltas = [(years[k], a[k] - a[k - 1]) for k in range(1, n)]
        exp = max(deltas, key=lambda d: d[1])[0]
        if exp != g:
            errs.append(f"{i}: fastest_change_year {g} != {exp}")
    elif qt == "longest_increase_streak":
        if longest_streak(a) != g:
            errs.append(f"{i}: streak {g} != {longest_streak(a)}")
    elif qt == "conditional_average":
        m = re.search(r">\s*(\d+)\s*olanlar", e["calculation"])
        if not m:
            errs.append(f"{i}: threshold unparseable")
        else:
            thr = int(m.group(1))
            above = [v for v in a if v > thr]
            exp = round(sum(above) / len(above), 1)
            if not approx(g, exp):
                errs.append(f"{i}: conditional_average {g} != {exp}")
    elif qt == "share_of_total":
        m = re.search(r"\b(20\d\d)\b", e["question"])
        if not m:
            errs.append(f"{i}: share year unparseable")
        else:
            yr = int(m.group(1))
            exp = round(a[years.index(yr)] / sum(a) * 100, 1)
            if abs(g - exp) > 0.11:
                errs.append(f"{i}: share_of_total {g} != {exp}")
    elif qt == "ratio":
        m = re.search(r"\b(20\d\d)\b", e["question"])
        if not m or b is None:
            errs.append(f"{i}: ratio year/series unparseable")
        else:
            yr = int(m.group(1))
            exp = round(a[years.index(yr)] / b[years.index(yr)], 2)
            if abs(g - exp) > 0.02:
                errs.append(f"{i}: ratio {g} != {exp}")

    return errs


def main():
    if not DATASET_PATH.exists():
        raise FileNotFoundError(DATASET_PATH)
    examples = load(DATASET_PATH)
    errors = []
    for i, e in enumerate(examples, 1):
        errors.extend(validate(e, i))

    print("=" * 60)
    print("reasoning_v01 validation")
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
