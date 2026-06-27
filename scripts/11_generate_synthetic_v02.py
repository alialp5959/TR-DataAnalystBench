"""Generate the synthetic_v02 dataset.

synthetic_v02 raises difficulty over v01 while staying fully Python-verified
and auto-scorable:

* Multi-series tables (Year + two metrics) so the model must select the right
  series; the unasked series acts as a distractor.
* Harder, multi-step numeric tasks: average, nth-highest, cross-series
  difference (in addition to value_lookup / comparison / percentage_change).
* Categorical trend questions (as in v01).
* Unanswerable questions (abstention) that ask about a year or metric not
  present in the data, to test hallucination resistance.
* Real `hard` difficulty labels.
"""

import json
import random
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


RANDOM_SEED = 1234
random.seed(RANDOM_SEED)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
EXPORTS_DIR = PROJECT_ROOT / "data" / "exports"
CHART_DIR = PROJECT_ROOT / "charts" / "synthetic_v02"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
CHART_DIR.mkdir(parents=True, exist_ok=True)


DATASET_PATH = PROCESSED_DIR / "synthetic_v02.jsonl"
PREVIEW_PATH = EXPORTS_DIR / "synthetic_v02_preview.csv"
STATS_PATH = EXPORTS_DIR / "synthetic_v02_stats.json"


DATASET_VERSION = "synthetic_v02"


# Each topic has two metric series with data, plus one absent metric name that
# is never put in the table (used to build "unanswerable" questions).
TOPICS = [
    {
        "domain": "transportation",
        "series": [
            {"metric": "yolcu sayısı", "unit": "kişi", "base": 1_200_000, "step": 95_000},
            {"metric": "sefer sayısı", "unit": "sefer", "base": 42_000, "step": 2_600},
        ],
        "absent_metric": "bilet geliri",
    },
    {
        "domain": "economy",
        "series": [
            {"metric": "ihracat değeri", "unit": "milyon dolar", "base": 180, "step": 16},
            {"metric": "ithalat değeri", "unit": "milyon dolar", "base": 210, "step": 14},
        ],
        "absent_metric": "enflasyon oranı",
    },
    {
        "domain": "education",
        "series": [
            {"metric": "öğrenci sayısı", "unit": "öğrenci", "base": 25_000, "step": 1_100},
            {"metric": "öğretmen sayısı", "unit": "öğretmen", "base": 1_700, "step": 70},
        ],
        "absent_metric": "okul sayısı",
    },
    {
        "domain": "tourism",
        "series": [
            {"metric": "ziyaretçi sayısı", "unit": "kişi", "base": 600_000, "step": 55_000},
            {"metric": "konaklama sayısı", "unit": "gece", "base": 1_400_000, "step": 90_000},
        ],
        "absent_metric": "ortalama harcama",
    },
    {
        "domain": "energy",
        "series": [
            {"metric": "elektrik tüketimi", "unit": "MWh", "base": 90_000, "step": 4_200},
            {"metric": "doğal gaz tüketimi", "unit": "m3", "base": 320_000, "step": 12_000},
        ],
        "absent_metric": "yenilenebilir üretim",
    },
    {
        "domain": "health",
        "series": [
            {"metric": "hastane başvuru sayısı", "unit": "başvuru", "base": 310_000, "step": 18_000},
            {"metric": "ameliyat sayısı", "unit": "ameliyat", "base": 24_000, "step": 1_300},
        ],
        "absent_metric": "yatak sayısı",
    },
    {
        "domain": "environment",
        "series": [
            {"metric": "geri dönüştürülen atık miktarı", "unit": "ton", "base": 8_000, "step": 560},
            {"metric": "toplam atık miktarı", "unit": "ton", "base": 41_000, "step": 1_900},
        ],
        "absent_metric": "karbon salımı",
    },
    {
        "domain": "sports",
        "series": [
            {"metric": "spor tesisi kullanım sayısı", "unit": "kullanım", "base": 45_000, "step": 3_000},
            {"metric": "lisanslı sporcu sayısı", "unit": "sporcu", "base": 12_000, "step": 800},
        ],
        "absent_metric": "müsabaka sayısı",
    },
    {
        "domain": "municipality",
        "series": [
            {"metric": "belediye hizmet başvurusu", "unit": "başvuru", "base": 70_000, "step": 4_500},
            {"metric": "çözülen başvuru sayısı", "unit": "başvuru", "base": 61_000, "step": 4_100},
        ],
        "absent_metric": "personel sayısı",
    },
    {
        "domain": "agriculture",
        "series": [
            {"metric": "üretim miktarı", "unit": "ton", "base": 150_000, "step": 7_800},
            {"metric": "ekili alan", "unit": "hektar", "base": 38_000, "step": 1_500},
        ],
        "absent_metric": "su tüketimi",
    },
]


# (question_type, difficulty, scoring kind)
TASKS = [
    ("value_lookup", "easy", "numeric"),
    ("comparison", "medium", "numeric"),
    ("percentage_change", "medium", "numeric"),
    ("cross_series_diff", "medium", "numeric"),
    ("average", "hard", "numeric"),
    ("nth_highest", "hard", "numeric"),
    ("trend_summary", "medium", "trend"),
    ("unanswerable", "hard", "abstention"),
]


INPUT_FORMATS = ["table_only", "chart_only", "table_and_chart"]
CHART_TYPES = ["line", "bar"]
TREND_MODES = ["increasing", "decreasing", "mixed"]


def format_number_tr(value: float) -> str:
    if isinstance(value, float) and not value.is_integer():
        return f"{value:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")

    return f"{int(round(value)):,}".replace(",", ".")


def format_percent_tr(value: float) -> str:
    return format_number_tr(round(abs(value), 1))


def ordinal_tr(n: int) -> str:
    words = {1: "en yüksek", 2: "en yüksek 2.", 3: "en yüksek 3."}
    return words[n]


def create_series_values(spec: dict, num_years: int, trend_mode: str) -> list[int]:
    values = []
    base = spec["base"]
    step = spec["step"]

    for i in range(num_years):
        noise = random.randint(-max(1, step // 3), max(1, step // 3))

        if trend_mode == "increasing":
            value = base + i * step + noise
        elif trend_mode == "decreasing":
            value = base + (num_years - i) * step + noise
        else:
            direction = 1 if i % 2 == 0 else -1
            value = base + direction * random.randint(0, step * 2) + i * random.randint(-step // 4, step // 4) + noise

        values.append(max(int(value), 1))

    return values


def create_table(topic: dict, table_id: int) -> dict:
    start_year = random.choice([2017, 2018, 2019, 2020])
    num_years = random.choice([5, 6])
    years = list(range(start_year, start_year + num_years))

    series_values = []
    for spec in topic["series"]:
        trend_mode = random.choice(TREND_MODES)
        series_values.append(create_series_values(spec, num_years, trend_mode))

    columns = ["Yıl"] + [spec["metric"] for spec in topic["series"]]
    rows = []
    for idx, year in enumerate(years):
        row = [year] + [series_values[s][idx] for s in range(len(topic["series"]))]
        rows.append(row)

    table = {"columns": columns, "rows": rows}

    chart_type = random.choice(CHART_TYPES)
    chart_path = CHART_DIR / f"chart_{table_id:03d}_{chart_type}.png"
    generate_chart(table, topic, chart_type, chart_path)

    return {
        "table": table,
        "chart_type": chart_type,
        "chart_path": str(chart_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "years": years,
    }


def generate_chart(table: dict, topic: dict, chart_type: str, output_path: Path) -> None:
    years = [row[0] for row in table["rows"]]
    metrics = table["columns"][1:]
    series = [[row[i + 1] for row in table["rows"]] for i in range(len(metrics))]

    plt.figure(figsize=(9, 5.0))

    if chart_type == "line":
        for metric, values in zip(metrics, series):
            plt.plot(years, values, marker="o", label=metric)
            for year, value in zip(years, values):
                plt.annotate(
                    format_number_tr(value),
                    (year, value),
                    textcoords="offset points",
                    xytext=(0, 8),
                    ha="center",
                    fontsize=7,
                )
    else:
        num_series = len(metrics)
        width = 0.8 / num_series
        for s_idx, (metric, values) in enumerate(zip(metrics, series)):
            offsets = [y + (s_idx - (num_series - 1) / 2) * width for y in range(len(years))]
            bars = plt.bar(offsets, values, width=width, label=metric)
            for bar, value in zip(bars, values):
                plt.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height(),
                    format_number_tr(value),
                    ha="center",
                    va="bottom",
                    fontsize=6,
                )
        plt.xticks(range(len(years)), years)

    plt.title(f"{topic['domain']} ({years[0]}-{years[-1]})")
    plt.xlabel("Yıl")
    plt.ylabel("Değer")
    plt.legend(fontsize=8)
    plt.grid(True, alpha=0.3, axis="y")
    plt.margins(y=0.20)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


# Minimum net change (relative to the start value) to call a direction on a
# non-monotonic series; below this, a noisy/flat series is "dalgalı".
TREND_NET_CHANGE_THRESHOLD = 0.05


def detect_trend(values: list[int]) -> str:
    increases = sum(1 for a, b in zip(values, values[1:]) if b > a)
    decreases = sum(1 for a, b in zip(values, values[1:]) if b < a)

    if decreases == 0 and increases > 0:
        return "artış eğilimi"
    if increases == 0 and decreases > 0:
        return "azalış eğilimi"

    net = values[-1] - values[0]
    net_ratio = abs(net) / max(abs(values[0]), 1)

    if net_ratio >= TREND_NET_CHANGE_THRESHOLD:
        if net > 0 and increases > decreases:
            return "artış eğilimi"
        if net < 0 and decreases > increases:
            return "azalış eğilimi"

    return "dalgalı eğilim"


def base_example(example_id, topic, table_info, question_type, difficulty, split, input_format):
    return {
        "id": f"trdab_v02_{example_id:06d}",
        "dataset_version": DATASET_VERSION,
        "language": "tr",
        "domain": topic["domain"],
        "source_name": "synthetic_v02",
        "data_type": "table_chart",
        "input_format": input_format,
        "chart_type": table_info["chart_type"],
        "chart_path": table_info["chart_path"],
        "question_type": question_type,
        "difficulty": difficulty,
        "table": table_info["table"],
        "split": split,
    }


def series_column(table: dict, series_index: int) -> tuple[str, list[int]]:
    metric = table["columns"][series_index + 1]
    values = [row[series_index + 1] for row in table["rows"]]
    return metric, values


def build_value_lookup(eid, topic, table_info, difficulty, split, input_format):
    table = table_info["table"]
    s_idx = random.randrange(len(topic["series"]))
    metric, values = series_column(table, s_idx)
    unit = topic["series"][s_idx]["unit"]
    row = random.choice(table["rows"])
    year = row[0]
    value = row[s_idx + 1]

    ex = base_example(eid, topic, table_info, "value_lookup", difficulty, split, input_format)
    ex.update({
        "target_column": metric,
        "unit": unit,
        "question": f"{year} yılında {metric} kaçtır?",
        "answer": f"{year} yılında {metric} {format_number_tr(value)} {unit} olarak verilmiştir.",
        "answer_type": "numeric",
        "numeric_answer": value,
        "calculation": f"{metric}: {year} satırındaki değer okunur: {value}",
        "expected_reasoning": "Doğru seri (kolon) ve yıl seçilip ilgili değer okunmalıdır.",
    })
    return ex


def build_comparison(eid, topic, table_info, difficulty, split, input_format):
    table = table_info["table"]
    s_idx = random.randrange(len(topic["series"]))
    metric, values = series_column(table, s_idx)
    unit = topic["series"][s_idx]["unit"]
    rows = table["rows"]
    row_a, row_b = random.sample(rows, 2)
    year_a, year_b = row_a[0], row_b[0]
    value_a, value_b = row_a[s_idx + 1], row_b[s_idx + 1]
    diff = value_b - value_a
    abs_diff = abs(diff)
    direction = "fazladır" if diff > 0 else ("azdır" if diff < 0 else "aynıdır")

    ex = base_example(eid, topic, table_info, "comparison", difficulty, split, input_format)
    ex.update({
        "target_column": metric,
        "unit": unit,
        "question": f"{year_b} yılındaki {metric}, {year_a} yılına göre kaç {unit} farklıdır?",
        "answer": f"{year_b} yılındaki {metric}, {year_a} yılına göre {format_number_tr(abs_diff)} {unit} {direction}.",
        "answer_type": "numeric",
        "numeric_answer": abs_diff,
        "calculation": f"|{value_b} - {value_a}| = {abs_diff}",
        "expected_reasoning": "Doğru seri seçilip iki yılın değerleri arasındaki mutlak fark hesaplanmalıdır.",
    })
    return ex


def build_percentage_change(eid, topic, table_info, difficulty, split, input_format):
    table = table_info["table"]
    s_idx = random.randrange(len(topic["series"]))
    metric, values = series_column(table, s_idx)
    rows = table["rows"]
    pair = sorted(random.sample(rows, 2), key=lambda r: r[0])
    start_year, end_year = pair[0][0], pair[1][0]
    start_value, end_value = pair[0][s_idx + 1], pair[1][s_idx + 1]
    pct = round(((end_value - start_value) / start_value) * 100, 1)
    direction = "artmıştır" if pct > 0 else ("azalmıştır" if pct < 0 else "değişmemiştir")

    ex = base_example(eid, topic, table_info, "percentage_change", difficulty, split, input_format)
    ex.update({
        "target_column": metric,
        "unit": "percent",
        "question": (
            f"{start_year} ile {end_year} arasında {metric} yaklaşık yüzde kaç değişmiştir? "
            f"Artış için pozitif, azalış için negatif değer ver."
        ),
        "answer": f"{start_year} ile {end_year} arasında {metric} yaklaşık %{format_percent_tr(abs(pct))} {direction}.",
        "answer_type": "numeric",
        "numeric_answer": pct,
        "calculation": f"(({end_value} - {start_value}) / {start_value}) * 100 = {pct}",
        "expected_reasoning": "Doğru seri seçilip yüzde değişim (yön dahil) hesaplanmalıdır.",
    })
    return ex


def build_cross_series_diff(eid, topic, table_info, difficulty, split, input_format):
    table = table_info["table"]
    metric_a = table["columns"][1]
    metric_b = table["columns"][2]
    unit = topic["series"][0]["unit"]
    row = random.choice(table["rows"])
    year = row[0]
    value_a, value_b = row[1], row[2]
    abs_diff = abs(value_a - value_b)
    bigger = metric_a if value_a >= value_b else metric_b

    ex = base_example(eid, topic, table_info, "cross_series_diff", difficulty, split, input_format)
    ex.update({
        "target_column": f"{metric_a} - {metric_b}",
        "unit": unit,
        "question": f"{year} yılında {metric_a} ile {metric_b} arasındaki fark kaçtır?",
        "answer": (
            f"{year} yılında {metric_a} ile {metric_b} arasındaki fark {format_number_tr(abs_diff)} "
            f"{unit} olarak hesaplanır ({bigger} daha yüksektir)."
        ),
        "answer_type": "numeric",
        "numeric_answer": abs_diff,
        "calculation": f"|{value_a} - {value_b}| = {abs_diff}",
        "expected_reasoning": "Aynı yıldaki iki serinin değerleri okunup mutlak farkları alınmalıdır.",
    })
    return ex


def build_average(eid, topic, table_info, difficulty, split, input_format):
    table = table_info["table"]
    s_idx = random.randrange(len(topic["series"]))
    metric, values = series_column(table, s_idx)
    unit = topic["series"][s_idx]["unit"]
    mean_value = round(sum(values) / len(values), 1)

    ex = base_example(eid, topic, table_info, "average", difficulty, split, input_format)
    ex.update({
        "target_column": metric,
        "unit": unit,
        "question": f"Tüm yıllar boyunca {metric} ortalaması yaklaşık kaçtır?",
        "answer": f"Tüm yıllar boyunca {metric} ortalaması yaklaşık {format_number_tr(mean_value)} {unit} olarak hesaplanır.",
        "answer_type": "numeric",
        "numeric_answer": mean_value,
        "calculation": f"({' + '.join(str(v) for v in values)}) / {len(values)} = {mean_value}",
        "expected_reasoning": "Doğru serinin tüm yıl değerleri toplanıp yıl sayısına bölünmelidir.",
    })
    return ex


def build_nth_highest(eid, topic, table_info, difficulty, split, input_format):
    table = table_info["table"]
    s_idx = random.randrange(len(topic["series"]))
    metric, values = series_column(table, s_idx)
    unit = topic["series"][s_idx]["unit"]
    n = random.choice([2, 3])
    sorted_rows = sorted(table["rows"], key=lambda r: r[s_idx + 1], reverse=True)
    selected_row = sorted_rows[n - 1]
    selected_value = selected_row[s_idx + 1]
    selected_year = selected_row[0]

    ex = base_example(eid, topic, table_info, "nth_highest", difficulty, split, input_format)
    ex.update({
        "target_column": metric,
        "unit": unit,
        "question": f"{metric} açısından {ordinal_tr(n)} değer kaçtır?",
        "answer": (
            f"{metric} açısından {ordinal_tr(n)} değer {format_number_tr(selected_value)} {unit} olup "
            f"{selected_year} yılında görülmüştür."
        ),
        "answer_type": "numeric_with_label",
        "numeric_answer": selected_value,
        "calculation": f"{metric} değerleri büyükten küçüğe sıralanır, {n}. değer: {selected_value} ({selected_year})",
        "expected_reasoning": "Seçilen serinin değerleri sıralanıp istenen sıradaki değer bulunmalıdır.",
    })
    return ex


def build_trend_summary(eid, topic, table_info, difficulty, split, input_format):
    table = table_info["table"]
    s_idx = random.randrange(len(topic["series"]))
    metric, values = series_column(table, s_idx)
    unit = topic["series"][s_idx]["unit"]
    start_year, end_year = table["rows"][0][0], table["rows"][-1][0]
    start_value, end_value = values[0], values[-1]
    trend = detect_trend(values)
    trend_class = {"artış eğilimi": "increasing", "azalış eğilimi": "decreasing", "dalgalı eğilim": "mixed"}[trend]

    if trend_class == "increasing":
        answer = (
            f"{metric} genel olarak artış eğilimi göstermektedir. {start_year} yılında "
            f"{format_number_tr(start_value)} {unit} olan değer, {end_year} yılında {format_number_tr(end_value)} {unit} olmuştur."
        )
    elif trend_class == "decreasing":
        answer = (
            f"{metric} genel olarak azalış eğilimi göstermektedir. {start_year} yılında "
            f"{format_number_tr(start_value)} {unit} olan değer, {end_year} yılında {format_number_tr(end_value)} {unit} olmuştur."
        )
    else:
        answer = f"{metric} dalgalı bir eğilim göstermektedir; yıllar arasında hem artış hem azalış görülmektedir."

    ex = base_example(eid, topic, table_info, "trend_summary", difficulty, split, input_format)
    ex.update({
        "target_column": metric,
        "unit": unit,
        "question": f"Verilen veriye göre {metric} için genel eğilim nedir? Cevabı tek kelimeyle ver: artış, azalış veya dalgalı.",
        "answer": answer,
        "answer_type": "text",
        "numeric_answer": None,
        "trend_class": trend_class,
        "calculation": f"{metric}: başlangıç {start_value}, bitiş {end_value}, eğilim: {trend}",
        "expected_reasoning": "Seçilen serinin başlangıç, bitiş ve ara değişimleri birlikte incelenmelidir.",
    })
    return ex


def build_unanswerable(eid, topic, table_info, difficulty, split, input_format):
    table = table_info["table"]
    years = table_info["years"]
    s_idx = random.randrange(len(topic["series"]))
    metric, _ = series_column(table, s_idx)
    unit = topic["series"][s_idx]["unit"]

    variant = random.choice(["missing_year", "missing_metric"])

    if variant == "missing_year":
        missing_year = years[-1] + random.choice([3, 4, 5, 7, 10])
        question = f"{missing_year} yılında {metric} kaçtır?"
        reason = f"{missing_year} yılı verilen veride bulunmamaktadır"
    else:
        absent_metric = topic["absent_metric"]
        year = random.choice(years)
        question = f"{year} yılında {absent_metric} kaçtır?"
        reason = f"{absent_metric} verilen tabloda/grafikte bulunmamaktadır"

    ex = base_example(eid, topic, table_info, "unanswerable", difficulty, split, input_format)
    ex.update({
        "target_column": None,
        "unit": unit,
        "question": question,
        "answer": f"Bu soru verilen veriden cevaplanamaz çünkü {reason}.",
        "answer_type": "abstention",
        "numeric_answer": None,
        "calculation": f"İstenen veri mevcut değil: {reason}.",
        "expected_reasoning": "Soruda istenen veri tabloda/grafikte yoksa cevap verilemeyeceği belirtilmelidir.",
    })
    return ex


BUILDERS = {
    "value_lookup": build_value_lookup,
    "comparison": build_comparison,
    "percentage_change": build_percentage_change,
    "cross_series_diff": build_cross_series_diff,
    "average": build_average,
    "nth_highest": build_nth_highest,
    "trend_summary": build_trend_summary,
    "unanswerable": build_unanswerable,
}


def save_jsonl(examples, path):
    with path.open("w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")


def save_preview_csv(examples, path):
    rows = []
    for ex in examples:
        rows.append({
            "id": ex["id"],
            "domain": ex["domain"],
            "input_format": ex["input_format"],
            "chart_type": ex["chart_type"],
            "question_type": ex["question_type"],
            "difficulty": ex["difficulty"],
            "answer_type": ex["answer_type"],
            "question": ex["question"],
            "answer": ex["answer"],
            "numeric_answer": ex["numeric_answer"],
            "unit": ex["unit"],
            "split": ex["split"],
            "chart_path": ex["chart_path"],
        })
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


def save_stats(examples, path):
    df = pd.DataFrame([
        {
            "domain": ex["domain"],
            "input_format": ex["input_format"],
            "chart_type": ex["chart_type"],
            "question_type": ex["question_type"],
            "difficulty": ex["difficulty"],
            "split": ex["split"],
            "answer_type": ex["answer_type"],
        }
        for ex in examples
    ])

    stats = {
        "dataset_version": DATASET_VERSION,
        "total_examples": len(examples),
        "unique_charts": len(set(ex["chart_path"] for ex in examples)),
        "domain_distribution": df["domain"].value_counts().sort_index().to_dict(),
        "input_format_distribution": df["input_format"].value_counts().sort_index().to_dict(),
        "chart_type_distribution": df["chart_type"].value_counts().sort_index().to_dict(),
        "question_type_distribution": df["question_type"].value_counts().sort_index().to_dict(),
        "difficulty_distribution": df["difficulty"].value_counts().sort_index().to_dict(),
        "split_distribution": df["split"].value_counts().sort_index().to_dict(),
        "answer_type_distribution": df["answer_type"].value_counts().sort_index().to_dict(),
    }
    path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")


def table_split(table_index: int, total_tables: int) -> str:
    train_cutoff = int(total_tables * 0.8)
    validation_cutoff = int(total_tables * 0.9)
    if table_index < train_cutoff:
        return "train"
    if table_index < validation_cutoff:
        return "validation"
    return "test"


def main() -> None:
    examples = []
    total_tables = 40
    example_id = 1
    input_format_counter = 0

    for table_idx in range(total_tables):
        topic = TOPICS[table_idx % len(TOPICS)]
        table_info = create_table(topic, table_idx + 1)
        split = table_split(table_idx, total_tables)

        for question_type, difficulty, _kind in TASKS:
            input_format = INPUT_FORMATS[input_format_counter % len(INPUT_FORMATS)]
            input_format_counter += 1

            example = BUILDERS[question_type](
                example_id, topic, table_info, difficulty, split, input_format
            )
            examples.append(example)
            example_id += 1

    save_jsonl(examples, DATASET_PATH)
    save_preview_csv(examples, PREVIEW_PATH)
    save_stats(examples, STATS_PATH)

    print("Synthetic v0.2 dataset generated successfully.")
    print(f"Number of examples: {len(examples)}")
    print(f"Unique charts: {len(set(ex['chart_path'] for ex in examples))}")
    print(f"JSONL path: {DATASET_PATH}")
    print(f"Preview CSV path: {PREVIEW_PATH}")
    print(f"Stats path: {STATS_PATH}")
    print(f"Charts directory: {CHART_DIR}")


if __name__ == "__main__":
    main()
