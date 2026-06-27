"""Create a manual testing kit for free, by-hand model evaluation.

Lets you evaluate any model (e.g. a free ChatGPT / Claude / Gemini chat) without
an API: it writes a paste-friendly Markdown worksheet (one prompt per question,
plus the chart image to upload for chart inputs) and an empty prediction
template CSV. Paste each prompt into a fresh chat, copy the answer into the
template, then score with scripts/08_evaluate_predictions_file.py.

Usage:
    python scripts/16_create_manual_kit.py --dataset data/processed/real_pilot.jsonl --split test
"""

import argparse
import csv
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPORTS_DIR = PROJECT_ROOT / "data" / "exports"

ABSTENTION_NOTE = (
    "Eğer soru verilen veriden cevaplanamıyorsa (istenen yıl veya veri yoksa) "
    "cevap olarak sadece 'veri yok' yaz."
)


def load_jsonl(path: Path) -> list[dict]:
    examples = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                examples.append(json.loads(line))
    return examples


def table_to_markdown(table: dict) -> str:
    cols = table["columns"]
    lines = ["| " + " | ".join(str(c) for c in cols) + " |",
             "|" + "|".join(["---"] * len(cols)) + "|"]
    for row in table["rows"]:
        lines.append("| " + " | ".join(str(v) for v in row) + " |")
    return "\n".join(lines)


def output_instruction(example: dict) -> str:
    if example["question_type"] == "trend_summary":
        return "Cevap olarak sadece eğilimi tek kelimeyle yaz: artış, azalış veya dalgalı."
    if example["question_type"] == "percentage_change":
        return ("Cevap olarak sadece sayısal yüzde değişim değerini yaz. "
                "Artış için pozitif, azalış için negatif. Örnek: 8.8 veya -8.8")
    return "Cevap olarak sadece sayısal değeri yaz. Birim/yıl/açıklama yazma. Örnek: 12345"


def build_prompt_block(example: dict) -> str:
    fmt = example["input_format"]
    lines = ["Aşağıdaki Türkçe veri analizi sorusunu cevapla.",
             output_instruction(example), ABSTENTION_NOTE, ""]
    if fmt in ("table_only", "table_and_chart"):
        lines += ["Tablo:", table_to_markdown(example["table"]), ""]
    if fmt in ("chart_only", "table_and_chart"):
        lines += [f"Grafik (bu görseli sohbete yükle): {example['chart_path']}", ""]
    lines += ["Soru:", example["question"]]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a manual (by-hand) evaluation kit.")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--split", type=str, default="test",
                        choices=["all", "train", "validation", "test"])
    args = parser.parse_args()

    examples = load_jsonl(args.dataset)
    if args.split != "all":
        examples = [e for e in examples if e.get("split") == args.split]

    if not examples:
        raise SystemExit(f"No examples for split '{args.split}' in {args.dataset}")

    version = examples[0].get("dataset_version", args.dataset.stem)
    stem = f"{version}_{args.split}_manual"
    worksheet_path = EXPORTS_DIR / f"{stem}_worksheet.md"
    template_path = EXPORTS_DIR / f"{stem}_template.csv"

    lines = [
        f"# Manual evaluation worksheet — {version} ({args.split})",
        "",
        f"{len(examples)} questions. For each one, open a **fresh** chat, paste the prompt "
        "(upload the chart image when one is referenced), then write the model's answer into "
        f"`{template_path.name}` (`predicted_numeric_answer` for numbers / trend word / `veri yok`).",
        "When done, score it:",
        "",
        "```bash",
        f"python scripts/08_evaluate_predictions_file.py --dataset {args.dataset} "
        f"--predictions data/exports/{template_path.name} --split {args.split}",
        "```",
        "",
        "---",
        "",
    ]

    for i, example in enumerate(examples, start=1):
        lines.append(f"## {i}. `{example['id']}`  ({example['input_format']} · {example['question_type']})")
        lines.append("")
        lines.append("```")
        lines.append(build_prompt_block(example))
        lines.append("```")
        lines.append("")

    worksheet_path.write_text("\n".join(lines), encoding="utf-8")

    with template_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "input_format", "question_type", "predicted_numeric_answer", "prediction_text"])
        for example in examples:
            writer.writerow([example["id"], example["input_format"], example["question_type"], "", ""])

    print("Manual kit created.")
    print(f"Worksheet: {worksheet_path}")
    print(f"Template:  {template_path}")
    print(f"Questions: {len(examples)}")


if __name__ == "__main__":
    main()
