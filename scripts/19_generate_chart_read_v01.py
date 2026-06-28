"""Generate the chart_read_v01 tier: genuine (label-free) chart reading.

Unlike the other tiers, these charts carry NO printed data labels — the model
must read values from the axes and gridlines, so this measures real chart
reading rather than label OCR. All examples are chart_only.

Tasks are chosen so that most are robustly scorable even without precise value
reading:
  - max_min_year  : which year holds the maximum / minimum (answer: a year) — exact
  - compare_years : which of two years is higher (answer: a year) — exact
  - count_above   : how many years exceed a round threshold (answer: a count) — exact
  - trend         : artış / azalış / dalgalı (categorical) — exact
  - value_estimate: approximate value in a given year — scored with an estimation
                    tolerance (±8%), since exact reading off gridlines is not possible

Per-example tolerances are written into the data and honored by the evaluator
(scripts/08_evaluate_predictions_file.py).
"""

import json
import random
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


RANDOM_SEED = 20260627
random.seed(RANDOM_SEED)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
EXPORTS_DIR = PROJECT_ROOT / "data" / "exports"
CHART_DIR = PROJECT_ROOT / "charts" / "chart_read_v01"
for d in (PROCESSED_DIR, EXPORTS_DIR, CHART_DIR):
    d.mkdir(parents=True, exist_ok=True)

DATASET_PATH = PROCESSED_DIR / "chart_read_v01.jsonl"
PREVIEW_PATH = EXPORTS_DIR / "chart_read_v01_preview.csv"
STATS_PATH = EXPORTS_DIR / "chart_read_v01_stats.json"

DATASET_VERSION = "chart_read_v01"
ESTIMATE_TOLERANCE = 0.08  # ±8% relative tolerance for reading a value off gridlines

TOPICS = [
    {"domain": "transportation", "metric": "yolcu sayısı", "unit": "kişi", "base": 1_200_000, "step": 110_000},
    {"domain": "economy", "metric": "ihracat değeri", "unit": "milyon dolar", "base": 180, "step": 18},
    {"domain": "education", "metric": "öğrenci sayısı", "unit": "öğrenci", "base": 25_000, "step": 1_100},
    {"domain": "tourism", "metric": "ziyaretçi sayısı", "unit": "kişi", "base": 600_000, "step": 70_000},
    {"domain": "energy", "metric": "elektrik tüketimi", "unit": "MWh", "base": 90_000, "step": 4_500},
    {"domain": "health", "metric": "hastane başvuru sayısı", "unit": "başvuru", "base": 310_000, "step": 20_000},
    {"domain": "environment", "metric": "geri dönüştürülen atık", "unit": "ton", "base": 8_000, "step": 600},
    {"domain": "sports", "metric": "spor tesisi kullanımı", "unit": "kullanım", "base": 45_000, "step": 3_200},
    {"domain": "municipality", "metric": "belediye hizmet başvurusu", "unit": "başvuru", "base": 70_000, "step": 4_800},
    {"domain": "agriculture", "metric": "üretim miktarı", "unit": "ton", "base": 150_000, "step": 8_500},
]

CHART_TYPES = ["line", "bar"]
TREND_MODES = ["increasing", "decreasing", "mixed"]
TREND_NET_CHANGE_THRESHOLD = 0.05


def format_number_tr(value: float) -> str:
    if isinstance(value, float) and not float(value).is_integer():
        return f"{value:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{int(round(value)):,}".replace(",", ".")


def detect_trend(values):
    inc = sum(1 for a, b in zip(values, values[1:]) if b > a)
    dec = sum(1 for a, b in zip(values, values[1:]) if b < a)
    if dec == 0 and inc > 0:
        return "increasing"
    if inc == 0 and dec > 0:
        return "decreasing"
    net = values[-1] - values[0]
    ratio = abs(net) / max(abs(values[0]), 1)
    if ratio >= TREND_NET_CHANGE_THRESHOLD:
        if net > 0 and inc > dec:
            return "increasing"
        if net < 0 and dec > inc:
            return "decreasing"
    return "mixed"


def nice_round(value: float) -> int:
    """Round to ~2 significant figures so the value sits near a gridline."""
    if value <= 0:
        return 1
    import math
    magnitude = 10 ** (math.floor(math.log10(abs(value))) - 1)
    return int(round(value / magnitude) * magnitude)


def create_values(topic, num_years, mode):
    base, step = topic["base"], topic["step"]
    values = []
    for i in range(num_years):
        noise = random.randint(-step // 3, step // 3)
        if mode == "increasing":
            v = base + i * step + noise
        elif mode == "decreasing":
            v = base + (num_years - i) * step + noise
        else:
            v = base + (1 if i % 2 == 0 else -1) * random.randint(0, step * 2) + i * random.randint(-step // 4, step // 4) + noise
        values.append(nice_round(max(v, 1)))
    return values


def generate_chart(years, values, topic, chart_type, path):
    plt.figure(figsize=(8, 4.8))
    if chart_type == "line":
        plt.plot(years, values, marker="o")
    else:
        plt.bar(years, values)
    plt.title(f"{topic['metric']} ({years[0]}-{years[-1]})")
    plt.xlabel("Yıl")
    plt.ylabel(f"{topic['metric']} ({topic['unit']})")
    plt.xticks(years)
    # Clear major gridlines so values can be read off the axis without printed
    # data labels. (Minor gridlines are intentionally avoided: with large value
    # ranges they explode the number of drawn lines and stall savefig.)
    ax = plt.gca()
    ax.yaxis.set_major_locator(plt.MaxNLocator(nbins=8))
    plt.grid(True, which="major", axis="both", alpha=0.4)
    plt.margins(y=0.15)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()


def base_example(eid, topic, table, chart_type, chart_path, qtype, difficulty, split):
    return {
        "id": f"trdab_cr_{eid:06d}",
        "dataset_version": DATASET_VERSION,
        "language": "tr",
        "domain": topic["domain"],
        "source_name": "chart_read_v01",
        "data_type": "table_chart",
        "input_format": "chart_only",
        "chart_type": chart_type,
        "chart_path": chart_path,
        "question_type": qtype,
        "difficulty": difficulty,
        "table": table,
        "target_column": topic["metric"],
        "unit": topic["unit"],
        "split": split,
    }


EXACT = {"numeric_tolerance": 0.0, "numeric_abs_tolerance": 0.0}


def build_table_examples(eid, topic, window, chart_type, chart_path, split):
    metric, unit = topic["metric"], topic["unit"]
    years = [y for y, _ in window]
    values = [v for _, v in window]
    table = {"columns": ["Yıl", metric], "rows": [[y, v] for y, v in window]}
    examples = []

    def add(qtype, difficulty, updates):
        nonlocal eid
        ex = base_example(eid, topic, table, chart_type, chart_path, qtype, difficulty, split)
        ex.update(updates)
        examples.append(ex)
        eid += 1

    # max year
    my, mv = max(window, key=lambda r: r[1])
    add("max_min_year", "medium", {**EXACT,
        "question": f"Grafiğe göre en yüksek {metric} hangi yılda görülmüştür? Cevap olarak sadece yılı yaz.",
        "answer": f"En yüksek {metric} {my} yılında görülmüştür.",
        "answer_type": "numeric", "numeric_answer": my,
        "calculation": f"max değer {mv}, yıl {my}",
        "expected_reasoning": "Grafikteki en yüksek nokta/çubuk bulunup yılı okunmalıdır."})

    # min year
    ny, nv = min(window, key=lambda r: r[1])
    add("max_min_year", "medium", {**EXACT,
        "question": f"Grafiğe göre en düşük {metric} hangi yılda görülmüştür? Cevap olarak sadece yılı yaz.",
        "answer": f"En düşük {metric} {ny} yılında görülmüştür.",
        "answer_type": "numeric", "numeric_answer": ny,
        "calculation": f"min değer {nv}, yıl {ny}",
        "expected_reasoning": "Grafikteki en düşük nokta/çubuk bulunup yılı okunmalıdır."})

    # compare two years (readable difference)
    pair = None
    for _ in range(20):
        a, b = random.sample(window, 2)
        if abs(a[1] - b[1]) >= 0.06 * max(values):
            pair = (a, b)
            break
    if pair is None:
        pair = (max(window, key=lambda r: r[1]), min(window, key=lambda r: r[1]))
    (ya, va), (yb, vb) = pair
    higher = ya if va > vb else yb
    add("compare_years", "medium", {**EXACT,
        "question": f"Grafiğe göre {ya} ve {yb} yıllarından hangisinde {metric} daha yüksektir? Cevap olarak sadece yılı yaz.",
        "answer": f"{metric} {higher} yılında daha yüksektir.",
        "answer_type": "numeric", "numeric_answer": higher,
        "calculation": f"{ya}:{va} vs {yb}:{vb} -> {higher}",
        "expected_reasoning": "İki yılın yükseklikleri karşılaştırılmalıdır."})

    # Count above a threshold placed strictly between two adjacent distinct
    # values near the median, so it never equals a data point (and the loop
    # cannot get stuck). Prefer a "nice" round number inside that gap.
    sv = sorted(set(values))
    mid_i = max(1, len(sv) // 2)
    prev_v, mid_v = sv[mid_i - 1], sv[mid_i]
    candidate = nice_round((prev_v + mid_v) / 2)
    if prev_v < candidate < mid_v and candidate not in values:
        threshold = candidate
    else:
        threshold = (prev_v + mid_v) / 2  # half-integer midpoint, never equals a value
    count = sum(1 for v in values if v > threshold)
    add("count_above", "hard", {**EXACT,
        "question": f"Grafiğe göre kaç yılda {metric} {format_number_tr(threshold)} {unit} değerinin üzerindedir? Cevap olarak sadece sayıyı yaz.",
        "answer": f"{count} yılda {metric} {format_number_tr(threshold)} {unit} değerinin üzerindedir.",
        "answer_type": "numeric", "numeric_answer": count,
        "calculation": f"{values} > {threshold} -> {count}",
        "expected_reasoning": "Eşik çizgisinin üstünde kalan yıllar sayılmalıdır."})

    # value estimate (estimation tolerance)
    ey, ev = random.choice(window)
    add("value_estimate", "hard", {
        "question": f"Grafiğe göre {ey} yılında {metric} yaklaşık kaçtır? Cevap olarak sadece sayıyı yaz.",
        "answer": f"{ey} yılında {metric} yaklaşık {format_number_tr(ev)} {unit}.",
        "answer_type": "numeric", "numeric_answer": ev,
        "numeric_tolerance": ESTIMATE_TOLERANCE,
        "numeric_abs_tolerance": 0.0,
        "calculation": f"{ey} değeri ~{ev} (±%{int(ESTIMATE_TOLERANCE*100)})",
        "expected_reasoning": "Noktanın/çubuğun yüksekliği eksen ve gridline'lardan tahmin edilmelidir."})

    # trend
    tclass = detect_trend(values)
    word = {"increasing": "artış", "decreasing": "azalış", "mixed": "dalgalı"}[tclass]
    add("trend_summary", "medium", {
        "question": f"Grafiğe göre {metric} için genel eğilim nedir? Cevabı tek kelimeyle ver: artış, azalış veya dalgalı.",
        "answer": f"{metric} genel olarak {word} eğilimi göstermektedir.",
        "answer_type": "text", "numeric_answer": None, "trend_class": tclass,
        "calculation": f"başlangıç {values[0]}, bitiş {values[-1]}, eğilim {tclass}",
        "expected_reasoning": "Grafiğin genel şekli (yükseliş/iniş/dalgalanma) değerlendirilmelidir."})

    return examples, eid


def main():
    total_tables = 40
    examples = []
    eid = 1
    for t in range(total_tables):
        topic = TOPICS[t % len(TOPICS)]
        start_year = random.choice([2017, 2018, 2019])
        num_years = random.choice([6, 7])
        years = list(range(start_year, start_year + num_years))
        mode = random.choice(TREND_MODES)
        values = create_values(topic, num_years, mode)
        window = list(zip(years, values))
        chart_type = CHART_TYPES[t % 2]
        chart_path_abs = CHART_DIR / f"chart_{t+1:03d}_{chart_type}.png"
        generate_chart(years, values, topic, chart_type, chart_path_abs)
        chart_path = str(chart_path_abs.relative_to(PROJECT_ROOT)).replace("\\", "/")
        split = ("test" if t >= int(total_tables * 0.9)
                 else "validation" if t >= int(total_tables * 0.8) else "train")
        batch, eid = build_table_examples(eid, topic, window, chart_type, chart_path, split)
        examples.extend(batch)

    with DATASET_PATH.open("w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    pd.DataFrame([{
        "id": e["id"], "domain": e["domain"], "question_type": e["question_type"],
        "difficulty": e["difficulty"], "question": e["question"], "answer": e["answer"],
        "numeric_answer": e["numeric_answer"], "split": e["split"], "chart_path": e["chart_path"],
    } for e in examples]).to_csv(PREVIEW_PATH, index=False, encoding="utf-8-sig")

    from collections import Counter
    stats = {
        "dataset_version": DATASET_VERSION,
        "total_examples": len(examples),
        "unique_charts": len(set(e["chart_path"] for e in examples)),
        "all_chart_only_label_free": True,
        "question_type_distribution": dict(Counter(e["question_type"] for e in examples)),
        "difficulty_distribution": dict(Counter(e["difficulty"] for e in examples)),
        "split_distribution": dict(Counter(e["split"] for e in examples)),
    }
    STATS_PATH.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    print("chart_read_v01 generated.")
    print(f"Tables: {total_tables}  Examples: {len(examples)}")
    print(f"Distribution: {stats['question_type_distribution']}")


if __name__ == "__main__":
    main()
