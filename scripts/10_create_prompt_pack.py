import csv
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATASET_PATH = PROJECT_ROOT / "data" / "processed" / "synthetic_v01.jsonl"
EXPORTS_DIR = PROJECT_ROOT / "data" / "exports"

ALL_JSONL_PATH = EXPORTS_DIR / "synthetic_v01_prompt_pack_all_numeric.jsonl"
TEST_JSONL_PATH = EXPORTS_DIR / "synthetic_v01_prompt_pack_test_numeric.jsonl"

ALL_CSV_PATH = EXPORTS_DIR / "synthetic_v01_prompt_pack_all_numeric.csv"
TEST_CSV_PATH = EXPORTS_DIR / "synthetic_v01_prompt_pack_test_numeric.csv"

# Full packs cover every scorable example (numeric + trend), so a model can
# answer the whole benchmark from a single file.
ALL_FULL_JSONL_PATH = EXPORTS_DIR / "synthetic_v01_prompt_pack_all_full.jsonl"
TEST_FULL_JSONL_PATH = EXPORTS_DIR / "synthetic_v01_prompt_pack_test_full.jsonl"

ALL_FULL_CSV_PATH = EXPORTS_DIR / "synthetic_v01_prompt_pack_all_full.csv"
TEST_FULL_CSV_PATH = EXPORTS_DIR / "synthetic_v01_prompt_pack_test_full.csv"


def load_jsonl(path: Path) -> list[dict]:
    examples = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                examples.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON at line {line_number}: {error}") from error

    return examples


def is_numeric_example(example: dict) -> bool:
    if example.get("numeric_answer") is None:
        return False

    if example.get("answer_type") not in {"numeric", "numeric_with_label"}:
        return False

    return True


def is_trend_example(example: dict) -> bool:
    return example.get("question_type") == "trend_summary"


def is_scorable_example(example: dict) -> bool:
    return is_numeric_example(example) or is_trend_example(example)


def table_to_markdown(table: dict) -> str:
    columns = table["columns"]
    rows = table["rows"]

    lines = []
    lines.append("| " + " | ".join(str(column) for column in columns) + " |")
    lines.append("|" + "|".join(["---"] * len(columns)) + "|")

    for row in rows:
        lines.append("| " + " | ".join(str(value) for value in row) + " |")

    return "\n".join(lines)


def get_output_instruction(example: dict) -> str:
    if example["question_type"] == "trend_summary":
        return (
            "Cevap olarak sadece eğilimi tek kelimeyle yaz: artış, azalış veya dalgalı. "
            "Açıklama, sayı veya ekstra metin yazma."
        )

    if example["question_type"] == "percentage_change":
        return (
            "Cevap olarak sadece sayısal yüzde değişim değerini yaz. "
            "Artış için pozitif, azalış için negatif değer ver. "
            "Yüzde işareti, birim, açıklama veya ekstra metin yazma. "
            "Örnek cevap formatı: 8.8 veya -8.8"
        )

    return (
        "Cevap olarak sadece sayısal değeri yaz. "
        "Birim, yıl, açıklama veya ekstra metin yazma. "
        "Örnek cevap formatı: 12345"
    )


def build_prompt(example: dict) -> tuple[str, str, str]:
    input_format = example["input_format"]
    question = example["question"]

    table_markdown = ""
    chart_path = ""

    prompt_parts = [
        "Aşağıdaki Türkçe veri analizi sorusunu cevapla.",
        get_output_instruction(example),
        "",
    ]

    if input_format == "table_only":
        table_markdown = table_to_markdown(example["table"])

        prompt_parts.extend(
            [
                "Girdi türü: sadece tablo",
                "",
                "Tablo:",
                table_markdown,
                "",
                "Soru:",
                question,
            ]
        )

    elif input_format == "chart_only":
        chart_path = example["chart_path"]

        prompt_parts.extend(
            [
                "Girdi türü: sadece grafik",
                "",
                "Grafik dosyası:",
                chart_path,
                "",
                "Soru:",
                question,
                "",
                "Not: Bu örnekte tablo verilmemiştir. Cevabı grafik görselinden çıkar.",
            ]
        )

    elif input_format == "table_and_chart":
        table_markdown = table_to_markdown(example["table"])
        chart_path = example["chart_path"]

        prompt_parts.extend(
            [
                "Girdi türü: tablo ve grafik",
                "",
                "Tablo:",
                table_markdown,
                "",
                "Grafik dosyası:",
                chart_path,
                "",
                "Soru:",
                question,
            ]
        )

    else:
        raise ValueError(f"Unsupported input_format: {input_format}")

    prompt = "\n".join(prompt_parts)

    return prompt, table_markdown, chart_path


def create_prompt_pack_rows(examples: list[dict], predicate=is_numeric_example) -> list[dict]:
    rows = []

    for example in examples:
        if not predicate(example):
            continue

        prompt, table_markdown, chart_path = build_prompt(example)

        rows.append(
            {
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
            }
        )

    return rows


def save_jsonl(rows: list[dict], path: Path) -> None:
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def save_csv(rows: list[dict], path: Path) -> None:
    if not rows:
        raise ValueError("Cannot save empty prompt pack.")

    fieldnames = list(rows[0].keys())

    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def validate_no_gold_leakage(rows: list[dict]) -> list[str]:
    errors = []

    forbidden_fields = {
        "answer",
        "numeric_answer",
        "gold_answer",
        "gold_numeric_answer",
        "calculation",
        "expected_reasoning",
    }

    for row in rows:
        example_id = row["id"]

        leaked_fields = forbidden_fields.intersection(row.keys())
        if leaked_fields:
            errors.append(f"{example_id}: forbidden gold fields found: {sorted(leaked_fields)}")

        if row["input_format"] == "chart_only":
            if row["table_markdown"].strip():
                errors.append(f"{example_id}: chart_only row contains table_markdown")

            if "| Yıl |" in row["prompt"]:
                errors.append(f"{example_id}: chart_only prompt appears to contain a table")

        if row["input_format"] == "table_only":
            if row["chart_path"].strip():
                errors.append(f"{example_id}: table_only row contains chart_path")

            if "Grafik dosyası:" in row["prompt"]:
                errors.append(f"{example_id}: table_only prompt appears to contain chart information")

    return errors


def main() -> None:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATASET_PATH}")

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    examples = load_jsonl(DATASET_PATH)

    all_rows = create_prompt_pack_rows(examples, predicate=is_numeric_example)
    test_rows = [row for row in all_rows if row["split"] == "test"]

    all_full_rows = create_prompt_pack_rows(examples, predicate=is_scorable_example)
    test_full_rows = [row for row in all_full_rows if row["split"] == "test"]

    errors = validate_no_gold_leakage(all_rows) + validate_no_gold_leakage(all_full_rows)

    if errors:
        print("Prompt pack validation failed.")
        print(f"Number of errors: {len(errors)}")

        for error in errors[:40]:
            print(f"  - {error}")

        if len(errors) > 40:
            print(f"  ... and {len(errors) - 40} more errors")

        raise SystemExit(1)

    save_jsonl(all_rows, ALL_JSONL_PATH)
    save_jsonl(test_rows, TEST_JSONL_PATH)

    save_csv(all_rows, ALL_CSV_PATH)
    save_csv(test_rows, TEST_CSV_PATH)

    save_jsonl(all_full_rows, ALL_FULL_JSONL_PATH)
    save_jsonl(test_full_rows, TEST_FULL_JSONL_PATH)

    save_csv(all_full_rows, ALL_FULL_CSV_PATH)
    save_csv(test_full_rows, TEST_FULL_CSV_PATH)

    input_format_counts = {}
    question_type_counts = {}

    for row in all_rows:
        input_format_counts[row["input_format"]] = input_format_counts.get(row["input_format"], 0) + 1
        question_type_counts[row["question_type"]] = question_type_counts.get(row["question_type"], 0) + 1

    print("Prompt packs created successfully.")
    print(f"All numeric prompt rows: {len(all_rows)}")
    print(f"Test numeric prompt rows: {len(test_rows)}")
    print(f"All full prompt rows (numeric + trend): {len(all_full_rows)}")
    print(f"Test full prompt rows (numeric + trend): {len(test_full_rows)}")

    print("\nInput format distribution:")
    for key in sorted(input_format_counts):
        print(f"  {key}: {input_format_counts[key]}")

    print("\nQuestion type distribution:")
    for key in sorted(question_type_counts):
        print(f"  {key}: {question_type_counts[key]}")

    print(f"\nAll JSONL prompt pack: {ALL_JSONL_PATH}")
    print(f"Test JSONL prompt pack: {TEST_JSONL_PATH}")
    print(f"All CSV prompt pack: {ALL_CSV_PATH}")
    print(f"Test CSV prompt pack: {TEST_CSV_PATH}")
    print(f"All full JSONL prompt pack: {ALL_FULL_JSONL_PATH}")
    print(f"Test full JSONL prompt pack: {TEST_FULL_JSONL_PATH}")
    print(f"All full CSV prompt pack: {ALL_FULL_CSV_PATH}")
    print(f"Test full CSV prompt pack: {TEST_FULL_CSV_PATH}")


if __name__ == "__main__":
    main()