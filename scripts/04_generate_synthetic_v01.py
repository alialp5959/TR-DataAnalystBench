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
CHART_DIR = PROJECT_ROOT / "charts" / "synthetic_v01"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
CHART_DIR.mkdir(parents=True, exist_ok=True)


DATASET_PATH = PROCESSED_DIR / "synthetic_v01.jsonl"
PREVIEW_PATH = EXPORTS_DIR / "synthetic_v01_preview.csv"
STATS_PATH = EXPORTS_DIR / "synthetic_v01_stats.json"


DATASET_VERSION = "synthetic_v01"


TOPICS = [
    {
        "domain": "transportation",
        "metric": "yolcu sayısı",
        "unit": "kişi",
        "base": 1_200_000,
        "step": 110_000,
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
        "step": 1_100,
    },
    {
        "domain": "tourism",
        "metric": "ziyaretçi sayısı",
        "unit": "kişi",
        "base": 600_000,
        "step": 70_000,
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
        "step": 20_000,
    },
    {
        "domain": "environment",
        "metric": "geri dönüştürülen atık miktarı",
        "unit": "ton",
        "base": 8_000,
        "step": 600,
    },
    {
        "domain": "sports",
        "metric": "spor tesisi kullanım sayısı",
        "unit": "kullanım",
        "base": 45_000,
        "step": 3_200,
    },
    {
        "domain": "municipality",
        "metric": "belediye hizmet başvurusu",
        "unit": "başvuru",
        "base": 70_000,
        "step": 4_800,
    },
    {
        "domain": "agriculture",
        "metric": "üretim miktarı",
        "unit": "ton",
        "base": 150_000,
        "step": 8_500,
    },
]


QUESTION_BUILDERS = [
    "value_lookup",
    "max_min",
    "comparison",
    "percentage_change",
    "trend_summary",
]


INPUT_FORMATS = [
    "table_only",
    "chart_only",
    "table_and_chart",
]


CHART_TYPES = [
    "line",
    "bar",
]


TREND_MODES = [
    "increasing",
    "decreasing",
    "mixed",
]


def format_number_tr(value: float) -> str:
    """
    Turkish-style number formatting.

    Examples:
    1200000 -> 1.200.000
    33.3 -> 33,3
    """
    if isinstance(value, float) and not value.is_integer():
        return f"{value:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")

    return f"{int(round(value)):,}".replace(",", ".")


def format_percent_tr(value: float) -> str:
    return format_number_tr(round(abs(value), 1))


def choose_split(index: int, total: int) -> str:
    train_cutoff = int(total * 0.8)
    validation_cutoff = int(total * 0.9)

    if index < train_cutoff:
        return "train"

    if index < validation_cutoff:
        return "validation"

    return "test"


def create_values(topic: dict, num_years: int, trend_mode: str) -> list[int]:
    values = []

    base = topic["base"]
    step = topic["step"]

    for i in range(num_years):
        noise = random.randint(-max(1, step // 3), max(1, step // 3))

        if trend_mode == "increasing":
            value = base + i * step + noise

        elif trend_mode == "decreasing":
            value = base + (num_years - i) * step + noise

        else:
            direction = 1 if i % 2 == 0 else -1
            value = (
                base
                + direction * random.randint(0, step * 2)
                + i * random.randint(-step // 4, step // 4)
                + noise
            )

        value = max(int(value), 1)
        values.append(value)

    return values


def create_table(topic: dict, table_id: int) -> dict:
    start_year = random.choice([2018, 2019, 2020])
    num_years = random.choice([5, 6])
    years = list(range(start_year, start_year + num_years))

    trend_mode = random.choice(TREND_MODES)
    values = create_values(topic, num_years, trend_mode)

    rows = [[year, value] for year, value in zip(years, values)]

    table = {
        "columns": ["Yıl", topic["metric"]],
        "rows": rows,
    }

    chart_type = random.choice(CHART_TYPES)
    chart_path = CHART_DIR / f"chart_{table_id:03d}_{chart_type}.png"

    generate_chart(
        table=table,
        topic=topic,
        chart_type=chart_type,
        output_path=chart_path,
    )

    return {
        "table": table,
        "chart_type": chart_type,
        "chart_path": str(chart_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "trend_mode": trend_mode,
    }


def generate_chart(table: dict, topic: dict, chart_type: str, output_path: Path) -> None:
    years = [row[0] for row in table["rows"]]
    values = [row[1] for row in table["rows"]]

    plt.figure(figsize=(8, 4.8))

    if chart_type == "line":
        plt.plot(years, values, marker="o")

        for year, value in zip(years, values):
            plt.annotate(
                format_number_tr(value),
                (year, value),
                textcoords="offset points",
                xytext=(0, 8),
                ha="center",
                fontsize=8,
            )

    elif chart_type == "bar":
        bars = plt.bar(years, values)

        for bar, value in zip(bars, values):
            plt.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                format_number_tr(value),
                ha="center",
                va="bottom",
                fontsize=8,
            )

    else:
        raise ValueError(f"Unsupported chart type: {chart_type}")

    plt.title(f"{topic['metric']} ({years[0]}-{years[-1]})")
    plt.xlabel("Yıl")
    plt.ylabel(f"{topic['metric']} ({topic['unit']})")
    plt.grid(True, alpha=0.3, axis="y")
    plt.margins(y=0.18)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def base_example(
    example_id: int,
    topic: dict,
    table_info: dict,
    question_type: str,
    difficulty: str,
    split: str,
    input_format: str,
) -> dict:
    return {
        "id": f"trdab_v01_{example_id:06d}",
        "dataset_version": DATASET_VERSION,
        "language": "tr",
        "domain": topic["domain"],
        "source_name": "synthetic_v01",
        "data_type": "table_chart",
        "input_format": input_format,
        "chart_type": table_info["chart_type"],
        "chart_path": table_info["chart_path"],
        "question_type": question_type,
        "difficulty": difficulty,
        "table": table_info["table"],
        "target_column": topic["metric"],
        "unit": topic["unit"],
        "split": split,
    }


def build_value_lookup(
    example_id: int,
    topic: dict,
    table_info: dict,
    split: str,
    input_format: str,
) -> dict:
    rows = table_info["table"]["rows"]
    year, value = random.choice(rows)

    example = base_example(
        example_id=example_id,
        topic=topic,
        table_info=table_info,
        question_type="value_lookup",
        difficulty="easy",
        split=split,
        input_format=input_format,
    )

    example.update(
        {
            "question": f"{year} yılında {topic['metric']} kaçtır?",
            "answer": f"{year} yılında {topic['metric']} {format_number_tr(value)} {topic['unit']} olarak verilmiştir.",
            "answer_type": "numeric",
            "numeric_answer": value,
            "calculation": f"{year} satırındaki değer okunur: {value}",
            "expected_reasoning": "İlgili yıl bulunup o yıla karşılık gelen değer okunmalıdır.",
        }
    )

    return example


def build_max_min(
    example_id: int,
    topic: dict,
    table_info: dict,
    split: str,
    input_format: str,
) -> dict:
    rows = table_info["table"]["rows"]
    ask_max = random.choice([True, False])

    if ask_max:
        selected_year, selected_value = max(rows, key=lambda row: row[1])
        question = f"Verilen verideki en yüksek {topic['metric']} kaçtır?"
        answer = (
            f"En yüksek {topic['metric']} {format_number_tr(selected_value)} "
            f"{topic['unit']} olarak verilmiştir. Bu değer {selected_year} yılında görülmüştür."
        )
        calculation = f"Maksimum değer: {selected_value}, yıl: {selected_year}"
    else:
        selected_year, selected_value = min(rows, key=lambda row: row[1])
        question = f"Verilen verideki en düşük {topic['metric']} kaçtır?"
        answer = (
            f"En düşük {topic['metric']} {format_number_tr(selected_value)} "
            f"{topic['unit']} olarak verilmiştir. Bu değer {selected_year} yılında görülmüştür."
        )
        calculation = f"Minimum değer: {selected_value}, yıl: {selected_year}"

    example = base_example(
        example_id=example_id,
        topic=topic,
        table_info=table_info,
        question_type="max_min",
        difficulty="easy",
        split=split,
        input_format=input_format,
    )

    example.update(
        {
            "question": question,
            "answer": answer,
            "answer_type": "numeric_with_label",
            "numeric_answer": selected_value,
            "calculation": calculation,
            "expected_reasoning": "Tüm yıllardaki değerler karşılaştırılıp istenen en yüksek veya en düşük değer seçilmelidir.",
        }
    )

    return example


def build_comparison(
    example_id: int,
    topic: dict,
    table_info: dict,
    split: str,
    input_format: str,
) -> dict:
    rows = table_info["table"]["rows"]

    row_a, row_b = random.sample(rows, 2)
    year_a, value_a = row_a
    year_b, value_b = row_b

    diff = value_b - value_a
    abs_diff = abs(diff)

    if diff > 0:
        direction = "fazladır"
    elif diff < 0:
        direction = "azdır"
    else:
        direction = "aynıdır"

    example = base_example(
        example_id=example_id,
        topic=topic,
        table_info=table_info,
        question_type="comparison",
        difficulty="medium",
        split=split,
        input_format=input_format,
    )

    example.update(
        {
            "question": f"{year_b} yılındaki {topic['metric']}, {year_a} yılına göre kaç {topic['unit']} farklıdır?",
            "answer": f"{year_b} yılındaki {topic['metric']}, {year_a} yılına göre {format_number_tr(abs_diff)} {topic['unit']} {direction}.",
            "answer_type": "numeric",
            "numeric_answer": abs_diff,
            "calculation": f"|{value_b} - {value_a}| = {abs_diff}",
            "expected_reasoning": "İki yılın değerleri bulunup aralarındaki mutlak fark hesaplanmalıdır.",
        }
    )

    return example


def build_percentage_change(
    example_id: int,
    topic: dict,
    table_info: dict,
    split: str,
    input_format: str,
) -> dict:
    rows = table_info["table"]["rows"]

    sorted_rows = sorted(random.sample(rows, 2), key=lambda row: row[0])
    start_year, start_value = sorted_rows[0]
    end_year, end_value = sorted_rows[1]

    pct_change = ((end_value - start_value) / start_value) * 100
    pct_rounded = round(pct_change, 1)
    pct_magnitude = abs(pct_rounded)

    if pct_change > 0:
        direction = "artmıştır"
    elif pct_change < 0:
        direction = "azalmıştır"
    else:
        direction = "değişmemiştir"

    example = base_example(
        example_id=example_id,
        topic=topic,
        table_info=table_info,
        question_type="percentage_change",
        difficulty="medium",
        split=split,
        input_format=input_format,
    )

    example.update(
        {
            # Soru yön bilgisini de istiyor: artış pozitif, azalış negatif.
            "question": (
                f"{start_year} ile {end_year} arasında {topic['metric']} yaklaşık yüzde kaç "
                f"değişmiştir? Artış için pozitif, azalış için negatif değer ver."
            ),
            "answer": f"{start_year} ile {end_year} arasında {topic['metric']} yaklaşık %{format_percent_tr(pct_magnitude)} {direction}.",
            "answer_type": "numeric",
            # Gold işaretli (signed) tutulur ki yön de ölçülebilsin.
            "numeric_answer": pct_rounded,
            "calculation": f"(({end_value} - {start_value}) / {start_value}) * 100 = {pct_rounded}",
            "expected_reasoning": "Başlangıç ve bitiş yıllarındaki değerler bulunup yüzde değişim (yön dahil) hesaplanmalıdır.",
            "unit": "percent",
        }
    )

    return example


def detect_trend(rows: list[list[int]]) -> str:
    values = [row[1] for row in rows]

    increases = 0
    decreases = 0

    for previous, current in zip(values, values[1:]):
        if current > previous:
            increases += 1
        elif current < previous:
            decreases += 1

    if increases > decreases and values[-1] > values[0]:
        return "artış eğilimi"

    if decreases > increases and values[-1] < values[0]:
        return "azalış eğilimi"

    return "dalgalı eğilim"


def build_trend_summary(
    example_id: int,
    topic: dict,
    table_info: dict,
    split: str,
    input_format: str,
) -> dict:
    rows = table_info["table"]["rows"]
    start_year, start_value = rows[0]
    end_year, end_value = rows[-1]

    trend = detect_trend(rows)

    # Otomatik (kategorik) skorlama için makine-okunur sınıf etiketi.
    trend_class_map = {
        "artış eğilimi": "increasing",
        "azalış eğilimi": "decreasing",
        "dalgalı eğilim": "mixed",
    }
    trend_class = trend_class_map[trend]

    if trend == "artış eğilimi":
        answer = (
            f"Verilen veri genel olarak {topic['metric']} için artış eğilimi göstermektedir. "
            f"{start_year} yılında {format_number_tr(start_value)} {topic['unit']} olan değer, "
            f"{end_year} yılında {format_number_tr(end_value)} {topic['unit']} seviyesine yükselmiştir."
        )
    elif trend == "azalış eğilimi":
        answer = (
            f"Verilen veri genel olarak {topic['metric']} için azalış eğilimi göstermektedir. "
            f"{start_year} yılında {format_number_tr(start_value)} {topic['unit']} olan değer, "
            f"{end_year} yılında {format_number_tr(end_value)} {topic['unit']} seviyesine düşmüştür."
        )
    else:
        answer = (
            f"Verilen veri {topic['metric']} için dalgalı bir eğilim göstermektedir. "
            f"Yıllar arasında hem artış hem de azalış görüldüğü için tek yönlü güçlü bir eğilim yoktur."
        )

    example = base_example(
        example_id=example_id,
        topic=topic,
        table_info=table_info,
        question_type="trend_summary",
        difficulty="medium",
        split=split,
        input_format=input_format,
    )

    example.update(
        {
            "question": (
                f"Verilen veriye göre {topic['metric']} için genel eğilim nedir? "
                f"Cevabı tek kelimeyle ver: artış, azalış veya dalgalı."
            ),
            "answer": answer,
            "answer_type": "text",
            "numeric_answer": None,
            "trend_class": trend_class,
            "calculation": f"Başlangıç değeri: {start_value}, bitiş değeri: {end_value}, tespit edilen eğilim: {trend}",
            "expected_reasoning": "Başlangıç, bitiş ve ara yıllardaki değişim yönleri birlikte incelenmelidir.",
        }
    )

    return example


def build_example(
    example_id: int,
    question_type: str,
    topic: dict,
    table_info: dict,
    split: str,
    input_format: str,
) -> dict:
    if question_type == "value_lookup":
        return build_value_lookup(example_id, topic, table_info, split, input_format)

    if question_type == "max_min":
        return build_max_min(example_id, topic, table_info, split, input_format)

    if question_type == "comparison":
        return build_comparison(example_id, topic, table_info, split, input_format)

    if question_type == "percentage_change":
        return build_percentage_change(example_id, topic, table_info, split, input_format)

    if question_type == "trend_summary":
        return build_trend_summary(example_id, topic, table_info, split, input_format)

    raise ValueError(f"Unsupported question type: {question_type}")


def save_jsonl(examples: list[dict], path: Path) -> None:
    with path.open("w", encoding="utf-8") as file:
        for example in examples:
            file.write(json.dumps(example, ensure_ascii=False) + "\n")


def save_preview_csv(examples: list[dict], path: Path) -> None:
    preview_rows = []

    for example in examples:
        preview_rows.append(
            {
                "id": example["id"],
                "dataset_version": example["dataset_version"],
                "domain": example["domain"],
                "input_format": example["input_format"],
                "chart_type": example["chart_type"],
                "question_type": example["question_type"],
                "difficulty": example["difficulty"],
                "question": example["question"],
                "answer": example["answer"],
                "numeric_answer": example["numeric_answer"],
                "unit": example["unit"],
                "split": example["split"],
                "chart_path": example["chart_path"],
            }
        )

    pd.DataFrame(preview_rows).to_csv(path, index=False, encoding="utf-8-sig")


def save_stats(examples: list[dict], path: Path) -> None:
    df = pd.DataFrame(
        [
            {
                "domain": example["domain"],
                "input_format": example["input_format"],
                "chart_type": example["chart_type"],
                "question_type": example["question_type"],
                "difficulty": example["difficulty"],
                "split": example["split"],
                "answer_type": example["answer_type"],
            }
            for example in examples
        ]
    )

    stats = {
        "dataset_version": DATASET_VERSION,
        "total_examples": len(examples),
        "unique_charts": len(set(example["chart_path"] for example in examples)),
        "domain_distribution": df["domain"].value_counts().sort_index().to_dict(),
        "input_format_distribution": df["input_format"].value_counts().sort_index().to_dict(),
        "chart_type_distribution": df["chart_type"].value_counts().sort_index().to_dict(),
        "question_type_distribution": df["question_type"].value_counts().sort_index().to_dict(),
        "difficulty_distribution": df["difficulty"].value_counts().sort_index().to_dict(),
        "split_distribution": df["split"].value_counts().sort_index().to_dict(),
        "answer_type_distribution": df["answer_type"].value_counts().sort_index().to_dict(),
    }

    path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    examples = []

    total_tables = 60
    total_examples = total_tables * len(QUESTION_BUILDERS)

    example_id = 1

    for table_id in range(1, total_tables + 1):
        topic = TOPICS[(table_id - 1) % len(TOPICS)]
        table_info = create_table(topic, table_id)

        for question_type in QUESTION_BUILDERS:
            split = choose_split(len(examples), total_examples)
            input_format = INPUT_FORMATS[(example_id - 1) % len(INPUT_FORMATS)]

            example = build_example(
                example_id=example_id,
                question_type=question_type,
                topic=topic,
                table_info=table_info,
                split=split,
                input_format=input_format,
            )

            examples.append(example)
            example_id += 1

    save_jsonl(examples, DATASET_PATH)
    save_preview_csv(examples, PREVIEW_PATH)
    save_stats(examples, STATS_PATH)

    print("Synthetic v0.1 dataset generated successfully.")
    print(f"Dataset version: {DATASET_VERSION}")
    print(f"Number of examples: {len(examples)}")
    print(f"Number of unique charts: {len(set(example['chart_path'] for example in examples))}")
    print(f"JSONL path: {DATASET_PATH}")
    print(f"Preview CSV path: {PREVIEW_PATH}")
    print(f"Stats path: {STATS_PATH}")
    print(f"Charts directory: {CHART_DIR}")


if __name__ == "__main__":
    main()