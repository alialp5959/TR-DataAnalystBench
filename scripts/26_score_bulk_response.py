"""Score a pasted bulk model response (see scripts/25_create_bulk_prompt.py).

Parses lines of the form `N) answer` from the model's reply, maps them back to
the question ids (same order the bulk prompt used), writes a predictions CSV,
and runs the standard evaluator on the chosen split.

Usage:
    python scripts/26_score_bulk_response.py \
        --dataset data/processed/reasoning_v01.jsonl --split test \
        --response path/to/model_reply.txt --name gpt
"""

import argparse
import csv
import json
import re
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPORTS_DIR = PROJECT_ROOT / "data" / "exports"


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--split", type=str, default="test")
    parser.add_argument("--response", type=Path, required=True)
    parser.add_argument("--name", type=str, default="manual_model")
    args = parser.parse_args()

    examples = load_jsonl(args.dataset)
    items = [e for e in examples if e.get("split") == args.split]
    if not items:
        raise SystemExit("No items for this split.")

    text = args.response.read_text(encoding="utf-8")
    answers = {}
    for line in text.splitlines():
        m = re.match(r"\s*(\d+)\s*[\)\.\-:]\s*(.+?)\s*$", line)
        if m:
            answers[int(m.group(1))] = m.group(2).strip()

    predictions_path = EXPORTS_DIR / f"{args.name}_{args.split}_bulk_predictions.csv"
    with predictions_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "predicted_numeric_answer", "prediction_text"])
        for i, e in enumerate(items, start=1):
            a = answers.get(i, "")
            w.writerow([e["id"], a, a])

    parsed = len(answers)
    print(f"Parsed {parsed}/{len(items)} answers -> {predictions_path}\n")

    cmd = [
        sys.executable, str(PROJECT_ROOT / "scripts" / "08_evaluate_predictions_file.py"),
        "--dataset", str(args.dataset),
        "--predictions", str(predictions_path),
        "--prediction-name", args.name,
        "--split", args.split,
    ]
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
