import json
import random
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


RANDOM_SEED = 42
random.seed(RANDOM_SEED)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
EXPORTS_DIR = PROJECT_ROOT / "data" / "exports"
CHART_DIR = PROJECT_ROOT / "charts" / "pilot"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
CHART_DIR.mkdir(parents=True, exist_ok=True)


DATASET_PATH = PROCESSED_DIR / "pilot.jsonl"
PREVIEW_PATH = EXPORTS_DIR / "pilot_preview.csv"


TOPICS = [
    {
        "domain": "transportation",
        "metric": "yolcu sayısı",
        "unit": "kişi",
        "base": 1_200_000,
        "step": 120_000,
    },
    {
        "domain": "economy",
        "metric": "ihracat değeri",
        "unit": "milyon dolar",
        "base": 180,
        "step": 18,
    },
    {
        "domain": "education",
        "metric": "öğrenci sayısı",
        "unit": "öğrenci",
        "base": 25_000,
        "step": 1_200,
    },
    {
        "domain": "tourism",
        "metric": "ziyaretçi sayısı",
        "unit": "kişi",
        "base": 600_000,
        "step": 75_000,
    },
    {
        "domain": "energy",
        "metric": "elektrik tüketimi",
        "unit": "MWh",
        "base": 90_000,
        "step": 4_500,
    },
    {
        "domain": "health",
        "metric": "hastane başvuru sayısı",
        "unit": "başvuru",
        "base": 310_000,
        "step": 22_000,
    },
    {
        "domain": "environment",
        "metric": "geri dönüştürülen atık miktarı",
        "unit": "ton",
        "base": 8_000,
        "step": 650,
    },
    {
        "domain": "sports",
        "metric": "spor tesisi kullanım sayısı",
        "unit": "kullanım",
        "base": 45_000,
        "step": 3_500,
    },
    {
        "domain": "municipality",
        "metric": "belediye hizmet başvurusu",
        "unit": "başvuru",
        "base": 70_000,
        "step": 5_000,
    },
    {
        "domain": "agriculture",
        "metric": "üretim miktarı",
        "unit": "ton",
        "base": 150_000,
        "step": 9_000,
    },
]


def format_number_tr(value: float) -> str:
    """
    Turkish-style readable number formatting.
    1200000 -> 1.200.000
    33.3 -> 33,3
    """
    if isinstance(value, float) and not value.is_integer():
        return f"{value:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{int(round(value)):,}".replace(",", ".")


def make_table(topic: dict, table_id: int) -> dict:
    years = list(range(2020, 2025))
    rows = []

    for i, year in enumerate(years):
        noise = random.randint(-topic["step"] // 3, topic["step"] // 3)
        value = topic["base"] + i * topic["step"] + noise

        # Negatif değer oluşmasını engelleyelim.
        value = max(value, 1)

        rows.append([year, int(value)])

    table = {
        "columns": ["Yıl", topic["metric"].title()],
        "rows": rows,
    }

    chart_path = CHART_DIR / f"table_{table_id:03d}.png"
    generate_chart(table, topic, chart_path)

    return {
        "table": table,
        "chart_path": str(chart_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
    }


def generate_chart(table: dict, topic: dict, output_path: Path) -> None:
    years = [row[0] for row in table["rows"]]
    values = [row[1] for row in table["rows"]]

    plt.figure(figsize=(7, 4))
    plt.plot(years, values, marker="o")
    plt.title(f"{topic['metric'].title()} (2020-2024)")
    plt.xlabel("Yıl")
    plt.ylabel(f"{topic['metric'].title()} ({topic['unit']})")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def build_value_lookup(example_id: int, topic: dict, table_info: dict, split: str) -> dict:
    rows = table_info["table"]["rows"]
    year, value = random.choice(rows)

    return {
        "id": f"trdab_pilot_{example_id:05d}",
        "language": "tr",
        "domain": topic["domain"],
        "source_name": "synthetic_pilot",
        "data_type": "table",
        "chart_type": "line",
        "chart_path": table_info["chart_path"],
        "question_type": "value_lookup",
        "difficulty": "easy",
        "table": table_info["table"],
        "question": f"{year} yılında {topic['metric']} kaçtır?",
        "answer": f"{year} yılında {topic['metric']} {format_number_tr(value)} {topic['unit']} olarak verilmiştir.",
        "numeric_answer": value,
        "calculation": f"{year} satırındaki değer okunur: {value}",
        "expected_reasoning": "Tabloda ilgili yıl satırı bulunup karşılık gelen değer okunmalıdır.",
        "unit": topic["unit"],
        "split": split,
    }


def build_max_min(example_id: int, topic: dict, table_info: dict, split: str) -> dict:
    rows = table_info["table"]["rows"]
    max_year, max_value = max(rows, key=lambda row: row[1])

    return {
        "id": f"trdab_pilot_{example_id:05d}",
        "language": "tr",
        "domain": topic["domain"],
        "source_name": "synthetic_pilot",
        "data_type": "table",
        "chart_type": "line",
        "chart_path": table_info["chart_path"],
        "question_type": "max_min",
        "difficulty": "easy",
        "table": table_info["table"],
        "question": f"Tabloda {topic['metric']} en yüksek hangi yıldadır?",
        "answer": f"{topic['metric'].capitalize()} en yüksek {max_year} yılındadır. Bu yıldaki değer {format_number_tr(max_value)} {topic['unit']} olarak verilmiştir.",
        "numeric_answer": max_value,
        "calculation": f"Maksimum değer: {max_value}, yıl: {max_year}",
        "expected_reasoning": "Tüm yıllardaki değerler karşılaştırılıp en yüksek değer seçilmelidir.",
        "unit": topic["unit"],
        "split": split,
    }


def build_comparison(example_id: int, topic: dict, table_info: dict, split: str) -> dict:
    rows = table_info["table"]["rows"]
    first = rows[1]
    second = rows[-1]

    year_a, value_a = first
    year_b, value_b = second
    diff = value_b - value_a

    direction = "fazladır" if diff >= 0 else "azdır"

    return {
        "id": f"trdab_pilot_{example_id:05d}",
        "language": "tr",
        "domain": topic["domain"],
        "source_name": "synthetic_pilot",
        "data_type": "table",
        "chart_type": "line",
        "chart_path": table_info["chart_path"],
        "question_type": "comparison",
        "difficulty": "medium",
        "table": table_info["table"],
        "question": f"{year_b} yılındaki {topic['metric']}, {year_a} yılına göre kaç {topic['unit']} farklıdır?",
        "answer": f"{year_b} yılındaki {topic['metric']}, {year_a} yılına göre {format_number_tr(abs(diff))} {topic['unit']} {direction}.",
        "numeric_answer": diff,
        "calculation": f"{value_b} - {value_a} = {diff}",
        "expected_reasoning": "İki yılın değerleri bulunup son yıldan önceki yıl çıkarılmalıdır.",
        "unit": topic["unit"],
        "split": split,
    }


def build_percentage_change(example_id: int, topic: dict, table_info: dict, split: str) -> dict:
    rows = table_info["table"]["rows"]
    start_year, start_value = rows[0]
    end_year, end_value = rows[-1]

    pct_change = ((end_value - start_value) / start_value) * 100
    pct_rounded = round(pct_change, 1)

    direction = "artmıştır" if pct_change >= 0 else "azalmıştır"

    return {
        "id": f"trdab_pilot_{example_id:05d}",
        "language": "tr",
        "domain": topic["domain"],
        "source_name": "synthetic_pilot",
        "data_type": "table",
        "chart_type": "line",
        "chart_path": table_info["chart_path"],
        "question_type": "percentage_change",
        "difficulty": "medium",
        "table": table_info["table"],
        "question": f"{start_year}'den {end_year}'e {topic['metric']} yaklaşık yüzde kaç değişmiştir?",
        "answer": f"{start_year}'den {end_year}'e {topic['metric']} yaklaşık %{format_number_tr(abs(pct_rounded))} {direction}.",
        "numeric_answer": pct_rounded,
        "calculation": f"(({end_value} - {start_value}) / {start_value}) * 100 = {pct_rounded}",
        "expected_reasoning": "İlk ve son yıl değerleri karşılaştırılıp yüzde değişim formülü uygulanmalıdır.",
        "unit": "percent",
        "split": split,
    }


def build_trend_summary(example_id: int, topic: dict, table_info: dict, split: str) -> dict:
    rows = table_info["table"]["rows"]
    start_year, start_value = rows[0]
    end_year, end_value = rows[-1]

    if end_value > start_value:
        trend = "artış eğilimi"
        answer = (
            f"Tablo genel olarak {topic['metric']} için artış eğilimi göstermektedir. "
            f"{start_year} yılında {format_number_tr(start_value)} {topic['unit']} olan değer, "
            f"{end_year} yılında {format_number_tr(end_value)} {topic['unit']} seviyesine çıkmıştır."
        )
    elif end_value < start_value:
        trend = "azalış eğilimi"
        answer = (
            f"Tablo genel olarak {topic['metric']} için azalış eğilimi göstermektedir. "
            f"{start_year} yılında {format_number_tr(start_value)} {topic['unit']} olan değer, "
            f"{end_year} yılında {format_number_tr(end_value)} {topic['unit']} seviyesine düşmüştür."
        )
    else:
        trend = "yatay eğilim"
        answer = (
            f"Tablo genel olarak {topic['metric']} için yatay bir eğilim göstermektedir. "
            f"{start_year} ve {end_year} değerleri birbirine yakındır."
        )

    return {
        "id": f"trdab_pilot_{example_id:05d}",
        "language": "tr",
        "domain": topic["domain"],
        "source_name": "synthetic_pilot",
        "data_type": "table",
        "chart_type": "line",
        "chart_path": table_info["chart_path"],
        "question_type": "trend_summary",
        "difficulty": "medium",
        "table": table_info["table"],
        "question": f"Bu tabloya göre {topic['metric']} için genel eğilim nedir?",
        "answer": answer,
        "numeric_answer": None,
        "calculation": f"Başlangıç değeri: {start_value}, bitiş değeri: {end_value}, trend: {trend}",
        "expected_reasoning": "Başlangıç ve bitiş değerleri ile ara yıllardaki genel yön incelenmelidir.",
        "unit": topic["unit"],
        "split": split,
    }


def assign_split(index: int) -> str:
    # 50 örnekte yaklaşık 40 train, 5 validation, 5 test.
    if index < 40:
        return "train"
    if index < 45:
        return "validation"
    return "test"


def main() -> None:
    examples = []
    example_id = 1

    builders = [
        build_value_lookup,
        build_max_min,
        build_comparison,
        build_percentage_change,
        build_trend_summary,
    ]

    for table_id, topic in enumerate(TOPICS, start=1):
        table_info = make_table(topic, table_id)

        for builder in builders:
            split = assign_split(len(examples))
            example = builder(example_id, topic, table_info, split)
            examples.append(example)
            example_id += 1

    with DATASET_PATH.open("w", encoding="utf-8") as f:
        for example in examples:
            f.write(json.dumps(example, ensure_ascii=False) + "\n")

    preview_rows = []
    for ex in examples:
        preview_rows.append(
            {
                "id": ex["id"],
                "domain": ex["domain"],
                "question_type": ex["question_type"],
                "difficulty": ex["difficulty"],
                "question": ex["question"],
                "answer": ex["answer"],
                "numeric_answer": ex["numeric_answer"],
                "split": ex["split"],
                "chart_path": ex["chart_path"],
            }
        )

    pd.DataFrame(preview_rows).to_csv(PREVIEW_PATH, index=False, encoding="utf-8-sig")

    print("Pilot dataset generated successfully.")
    print(f"Number of examples: {len(examples)}")
    print(f"JSONL path: {DATASET_PATH}")
    print(f"Preview CSV path: {PREVIEW_PATH}")
    print(f"Charts directory: {CHART_DIR}")


if __name__ == "__main__":
    main()