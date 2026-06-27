"""Create evaluation assets for synthetic_v02.

Produces, under data/exports/:
* prompt packs (all + test) the model answers from
* a prediction template to fill in
* oracle and noisy baseline prediction CSVs (a sanity check for the scorer)

Every prompt carries a global abstention instruction so that "unanswerable"
questions are fair and indistinguishable from normal questions in the prompt.
"""

import csv
import json
import random
from pathlib import Path


RANDOM_SEED = 7
random.seed(RANDOM_SEED)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATASET_PATH = PROJECT_ROOT / "data" / "processed" / "synthetic_v02.jsonl"
EXPORTS_DIR = PROJECT_ROOT / "data" / "exports"

PROMPT_ALL_JSONL = EXPORTS_DIR / "synthetic_v02_prompt_pack_all.jsonl"
PROMPT_TEST_JSONL = EXPORTS_DIR / "synthetic_v02_prompt_pack_test.jsonl"
PROMPT_ALL_CSV = EXPORTS_DIR / "synthetic_v02_prompt_pack_all.csv"
PROMPT_TEST_CSV = EXPORTS_DIR / "synthetic_v02_prompt_pack_test.csv"

TEMPLATE_ALL_CSV = EXPORTS_DIR / "synthetic_v02_prediction_template_all.csv"
TEMPLATE_TEST_CSV = EXPORTS_DIR / "synthetic_v02_prediction_template_test.csv"

ORACLE_CSV = EXPORTS_DIR / "synthetic_v02_oracle_predictions.csv"
NOISY_CSV = EXPORTS_DIR / "synthetic_v02_noisy_baseline_predictions.csv"


ABSTENTION_NOTE = (
    "Eğer soru verilen veriden cevaplanamıyorsa (istenen yıl veya veri tabloda/grafikte yoksa) "
    "cevap olarak sadece 'veri yok' yaz."
)

TREND_WORD = {"increasing": "artış", "decreasing": "azalış", "mixed": "dalgalı"}


def load_jsonl(path: Path) -> list[dict]:
    examples = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                examples.append(json.loads(line))
    return examples


def table_to_markdown(table: dict) -> str:
    columns = table["columns"]
    lines = ["| " + " | ".join(str(c) for c in columns) + " |",
             "|" + "|".join(["---"] * len(columns)) + "|"]
    for row in table["rows"]:
        lines.append("| " + " | ".join(str(v) for v in row) + " |")
    return "\n".join(lines)


def get_output_instruction(example: dict) -> str:
    # NOTE: "unanswerable" must use the same instruction as a normal numeric
    # question, otherwise the prompt would reveal that it is unanswerable.
    if example["question_type"] == "trend_summary":
        return "Cevap olarak sadece eğilimi tek kelimeyle yaz: artış, azalış veya dalgalı."

    if example["question_type"] == "percentage_change":
        return (
            "Cevap olarak sadece sayısal yüzde değişim değerini yaz. "
            "Artış için pozitif, azalış için negatif değer ver. Örnek: 8.8 veya -8.8"
        )

    return "Cevap olarak sadece sayısal değeri yaz. Birim, yıl veya açıklama yazma. Örnek: 12345"


def build_prompt(example: dict) -> tuple[str, str, str]:
    input_format = example["input_format"]
    question = example["question"]

    parts = [
        "Aşağıdaki Türkçe veri analizi sorusunu cevapla.",
        get_output_instruction(example),
        ABSTENTION_NOTE,
        "",
    ]

    table_markdown = ""
    chart_path = ""

    if input_format == "table_only":
        table_markdown = table_to_markdown(example["table"])
        parts += ["Girdi türü: sadece tablo", "", "Tablo:", table_markdown, "", "Soru:", question]
    elif input_format == "chart_only":
        chart_path = example["chart_path"]
        parts += ["Girdi türü: sadece grafik", "", "Grafik dosyası:", chart_path, "",
                  "Soru:", question, "", "Not: Bu örnekte tablo verilmemiştir. Cevabı grafik görselinden çıkar."]
    elif input_format == "table_and_chart":
        table_markdown = table_to_markdown(example["table"])
        chart_path = example["chart_path"]
        parts += ["Girdi türü: tablo ve grafik", "", "Tablo:", table_markdown, "",
                  "Grafik dosyası:", chart_path, "", "Soru:", question]
    else:
        raise ValueError(f"Unsupported input_format: {input_format}")

    return "\n".join(parts), table_markdown, chart_path


def create_prompt_rows(examples: list[dict]) -> list[dict]:
    rows = []
    for example in examples:
        prompt, table_markdown, chart_path = build_prompt(example)
        rows.append({
            "id": example["id"],
            "dataset_version": example["dataset_version"],
            "split": example["split"],
            "domain": example["domain"],
            "input_format": example["input_format"],
            "chart_type": example["chart_type"],
            "chart_path": chart_path,
            "question_type": example["question_type"],
            "difficulty": example["difficulty"],
            "unit": example["unit"],
            "question": example["question"],
            "table_markdown": table_markdown,
            "prompt": prompt,
        })
    return rows


def validate_no_leakage(rows: list[dict]) -> list[str]:
    errors = []
    forbidden = {"answer", "numeric_answer", "calculation", "expected_reasoning", "trend_class", "target_column"}
    for row in rows:
        leaked = forbidden.intersection(row.keys())
        if leaked:
            errors.append(f"{row['id']}: leaked gold fields {sorted(leaked)}")
        if row["input_format"] == "chart_only" and row["table_markdown"].strip():
            errors.append(f"{row['id']}: chart_only row contains table_markdown")
        # the prompt must not hint that a question is unanswerable
        if "cevaplanamaz" in row["prompt"].lower() and "cevaplanamıyorsa" not in row["prompt"].lower():
            errors.append(f"{row['id']}: prompt leaks unanswerability")
    return errors


def template_rows(examples: list[dict]) -> list[dict]:
    rows = []
    for example in examples:
        rows.append({
            "id": example["id"],
            "split": example["split"],
            "question_type": example["question_type"],
            "input_format": example["input_format"],
            "question": example["question"],
            "predicted_numeric_answer": "",
            "prediction_text": "",
        })
    return rows


def oracle_rows(examples: list[dict]) -> list[dict]:
    rows = []
    for example in examples:
        answer_type = example["answer_type"]
        if answer_type in {"numeric", "numeric_with_label"}:
            value = example["numeric_answer"]
            rows.append({"id": example["id"], "predicted_numeric_answer": value, "prediction_text": str(value)})
        elif answer_type == "text":  # trend
            word = TREND_WORD[example["trend_class"]]
            rows.append({"id": example["id"], "predicted_numeric_answer": "", "prediction_text": word})
        elif answer_type == "abstention":
            rows.append({"id": example["id"], "predicted_numeric_answer": "", "prediction_text": "veri yok"})
    return rows


def noisy_rows(examples: list[dict]) -> list[dict]:
    rows = []
    for example in examples:
        answer_type = example["answer_type"]
        if answer_type in {"numeric", "numeric_with_label"}:
            gold = float(example["numeric_answer"])
            if example["question_type"] == "percentage_change":
                pred = round(gold + random.choice([-1, 1]) * random.uniform(0, 8), 1) if random.random() > 0.6 else gold
            else:
                pred = round(gold * (1 + random.choice([-1, 1]) * random.uniform(0, 0.12))) if random.random() > 0.6 else gold
            rows.append({"id": example["id"], "predicted_numeric_answer": pred, "prediction_text": str(pred)})
        elif answer_type == "text":
            word = TREND_WORD[example["trend_class"]]
            if random.random() < 0.3:
                word = random.choice([w for w in TREND_WORD.values() if w != word])
            rows.append({"id": example["id"], "predicted_numeric_answer": "", "prediction_text": word})
        elif answer_type == "abstention":
            # A weak model often hallucinates a number instead of abstaining.
            if random.random() < 0.5:
                rows.append({"id": example["id"], "predicted_numeric_answer": random.randint(1000, 900000), "prediction_text": ""})
            else:
                rows.append({"id": example["id"], "predicted_numeric_answer": "", "prediction_text": "veri yok"})
    return rows


def save_jsonl(rows: list[dict], path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def save_csv(rows: list[dict], path: Path) -> None:
    if not rows:
        raise ValueError(f"No rows to write for {path}")
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATASET_PATH}")

    examples = load_jsonl(DATASET_PATH)
    test_examples = [e for e in examples if e["split"] == "test"]

    prompt_all = create_prompt_rows(examples)
    prompt_test = create_prompt_rows(test_examples)

    errors = validate_no_leakage(prompt_all)
    if errors:
        print("Prompt pack leakage validation failed:")
        for error in errors[:40]:
            print(f"  - {error}")
        raise SystemExit(1)

    save_jsonl(prompt_all, PROMPT_ALL_JSONL)
    save_jsonl(prompt_test, PROMPT_TEST_JSONL)
    save_csv(prompt_all, PROMPT_ALL_CSV)
    save_csv(prompt_test, PROMPT_TEST_CSV)

    save_csv(template_rows(examples), TEMPLATE_ALL_CSV)
    save_csv(template_rows(test_examples), TEMPLATE_TEST_CSV)

    save_csv(oracle_rows(examples), ORACLE_CSV)
    save_csv(noisy_rows(examples), NOISY_CSV)

    print("Synthetic v0.2 evaluation assets created successfully.")
    print(f"Prompt pack rows (all): {len(prompt_all)}  (test): {len(prompt_test)}")
    print(f"Prompt pack: {PROMPT_ALL_CSV}")
    print(f"Prediction template: {TEMPLATE_ALL_CSV}")
    print(f"Oracle predictions: {ORACLE_CSV}")
    print(f"Noisy predictions: {NOISY_CSV}")


if __name__ == "__main__":
    main()
