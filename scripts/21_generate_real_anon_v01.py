"""Generate real_anon_v01: a contamination-controlled real-data tier.

Real benchmarks built on well-known public figures (Türkiye's population, GDP,
...) risk measuring *recall* instead of *table reading*: a strong model may
"know" that Türkiye's 2011 population was ~74.2M without reading the table.

This tier keeps the **real structure** of the data (authentic year-to-year
variability, real trends and relationships) while removing the anchors a model
could use to recall a specific value:

  - the country is dropped and absolute years are replaced by period indices
    (1..N), so questions reference "3. dönem", "ilk dönem", "son dönem", etc.;
  - each series is rescaled by a random per-table factor, which breaks
    exact-magnitude recall but preserves shape, ordering, ratios and percentage
    changes (so every task stays well-defined and Python-verifiable).

Gold answers are recomputed from the rescaled values, so the tier is fully
auto-scorable with the same evaluator and schema family as the other tiers.
"""

import csv
import json
import math
import random
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


RANDOM_SEED = 99
random.seed(RANDOM_SEED)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCES_DIR = PROJECT_ROOT / "data" / "sources_real"
PROVENANCE_PATH = SOURCES_DIR / "provenance.json"

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
EXPORTS_DIR = PROJECT_ROOT / "data" / "exports"
CHART_DIR = PROJECT_ROOT / "charts" / "real_anon_v01"
for d in (PROCESSED_DIR, EXPORTS_DIR, CHART_DIR):
    d.mkdir(parents=True, exist_ok=True)

DATASET_PATH = PROCESSED_DIR / "real_anon_v01.jsonl"
PREVIEW_PATH = EXPORTS_DIR / "real_anon_v01_preview.csv"
STATS_PATH = EXPORTS_DIR / "real_anon_v01_stats.json"

DATASET_VERSION = "real_anon_v01"
WINDOW_SIZE = 6
TREND_NET_CHANGE_THRESHOLD = 0.05

RATE_METRICS = {"tüketici enflasyon oranı", "enflasyon oranı"}
ABSENT_METRIC = {
    "demografi": "işsizlik oranı",
    "ekonomi": "cari açık",
    "çevre": "orman alanı",
}
INPUT_FORMATS = ["table_only", "chart_only", "table_and_chart"]


def format_number_tr(value):
    if isinstance(value, float) and not float(value).is_integer():
        return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{int(round(value)):,}".replace(",", ".")


def load_source_rows(name):
    rows = []
    with (SOURCES_DIR / f"{name}.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            raw = r["Value"]
            rows.append((int(r["Year"]), int(raw) if raw.lstrip("-").isdigit() else float(raw)))
    rows.sort(key=lambda x: x[0])
    return rows


def make_windows(rows, count):
    windows, end = [], len(rows)
    for _ in range(count):
        start = end - WINDOW_SIZE
        if start < 0:
            break
        windows.append(rows[start:end])
        end = start
    return list(reversed(windows))


def nice_round(value):
    if value <= 0:
        return 1
    mag = 10 ** (math.floor(math.log10(abs(value))) - 1)
    return int(round(value / mag) * mag)


def rescale(values, is_rate, scale):
    out = []
    for v in values:
        s = v * scale
        out.append(round(s, 1) if is_rate else nice_round(s))
    return out


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


def generate_chart(periods, values, metric, unit, chart_type, path):
    plt.figure(figsize=(8, 4.8))
    if chart_type == "line":
        plt.plot(periods, values, marker="o")
        for p, v in zip(periods, values):
            plt.annotate(format_number_tr(v), (p, v), textcoords="offset points",
                         xytext=(0, 8), ha="center", fontsize=8)
    else:
        bars = plt.bar(periods, values)
        for bar, v in zip(bars, values):
            plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                     format_number_tr(v), ha="center", va="bottom", fontsize=8)
    plt.title(f"{metric} (dönemsel)")
    plt.xlabel("Dönem")
    plt.ylabel(f"{metric} ({unit})")
    plt.xticks(periods)
    plt.grid(True, alpha=0.3, axis="y")
    plt.margins(y=0.18)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()


EID = 0


def base_example(source, table, chart_type, chart_path, qtype, difficulty, split, fmt):
    global EID
    EID += 1
    return {
        "id": f"trdab_ranon_{EID:06d}",
        "dataset_version": DATASET_VERSION,
        "language": "tr",
        "domain": source["domain"],
        "source_name": source["name"],
        "source_url": source["url"],
        "license": source["license"].get("name", "unknown") if isinstance(source["license"], dict) else str(source["license"]),
        "anonymized": True,
        "data_type": "table_chart",
        "input_format": fmt,
        "chart_type": chart_type,
        "chart_path": chart_path,
        "question_type": qtype,
        "difficulty": difficulty,
        "table": table,
        "target_column": source["metric"],
        "unit": source["unit"],
        "split": split,
    }


def build(source, periods, values, chart_type, chart_path, split, fmt_state):
    metric, unit = source["metric"], source["unit"]
    is_rate = metric in RATE_METRICS
    table = {"columns": ["Dönem", metric], "rows": [[p, v] for p, v in zip(periods, values)]}
    out = []

    def fmt():
        f = INPUT_FORMATS[fmt_state[0] % 3]
        fmt_state[0] += 1
        return f

    def add(qtype, diff, upd):
        ex = base_example(source, table, chart_type, chart_path, qtype, diff, split, fmt())
        ex.update(upd)
        out.append(ex)

    n = len(periods)

    p = periods[n // 2]
    v = values[n // 2]
    add("value_lookup", "easy", {
        "question": f"{p}. dönemde {metric} kaçtır?",
        "answer": f"{p}. dönemde {metric} {format_number_tr(v)} {unit}.",
        "answer_type": "numeric", "numeric_answer": v,
        "calculation": f"{p}. dönem değeri: {v}",
        "expected_reasoning": "İlgili döneme karşılık gelen değer okunmalıdır."})

    diff = abs(values[-1] - values[0])
    add("comparison", "medium", {
        "question": f"Son dönem ({periods[-1]}.) ile ilk dönem ({periods[0]}.) arasındaki {metric} farkı kaç {unit}dır?",
        "answer": f"Fark {format_number_tr(diff)} {unit}.",
        "answer_type": "numeric", "numeric_answer": round(diff, 2) if isinstance(diff, float) else diff,
        "calculation": f"|{values[-1]} - {values[0]}| = {diff}",
        "expected_reasoning": "İlk ve son dönem değerleri arasındaki mutlak fark hesaplanmalıdır."})

    mean_v = round(sum(values) / len(values), 2)
    add("average", "hard", {
        "question": f"Tüm dönemler boyunca {metric} ortalaması yaklaşık kaçtır?",
        "answer": f"Ortalama yaklaşık {format_number_tr(mean_v)} {unit}.",
        "answer_type": "numeric", "numeric_answer": mean_v,
        "calculation": f"ortalama({values}) = {mean_v}",
        "expected_reasoning": "Tüm dönem değerleri toplanıp dönem sayısına bölünmelidir."})

    ordered = sorted(zip(periods, values), key=lambda r: r[1], reverse=True)
    sp, sv = ordered[1]
    add("nth_highest", "hard", {
        "question": f"{metric} açısından en yüksek 2. değer kaçtır?",
        "answer": f"En yüksek 2. değer {format_number_tr(sv)} {unit} ({sp}. dönem).",
        "answer_type": "numeric_with_label", "numeric_answer": sv,
        "calculation": f"sıralı, 2.: {sv} ({sp}. dönem)",
        "expected_reasoning": "Değerler sıralanıp ikinci en yüksek alınmalıdır."})

    if not is_rate:
        pct = round(((values[-1] - values[0]) / values[0]) * 100, 1)
        direction = "artmıştır" if pct > 0 else ("azalmıştır" if pct < 0 else "değişmemiştir")
        add("percentage_change", "medium", {
            "question": f"İlk dönemden son döneme {metric} yaklaşık yüzde kaç değişmiştir? Artış için pozitif, azalış için negatif değer ver.",
            "answer": f"{metric} yaklaşık %{format_number_tr(abs(pct))} {direction}.",
            "answer_type": "numeric", "numeric_answer": pct, "unit": "percent",
            "calculation": f"(({values[-1]} - {values[0]}) / {values[0]}) * 100 = {pct}",
            "expected_reasoning": "Yüzde değişim yön dahil hesaplanmalıdır."})

    tclass = detect_trend(values)
    word = {"increasing": "artış", "decreasing": "azalış", "mixed": "dalgalı"}[tclass]
    add("trend_summary", "medium", {
        "question": f"{metric} için genel eğilim nedir? Cevabı tek kelimeyle ver: artış, azalış veya dalgalı.",
        "answer": f"{metric} genel olarak {word} eğilimi göstermektedir.",
        "answer_type": "text", "numeric_answer": None, "trend_class": tclass,
        "calculation": f"başlangıç {values[0]}, bitiş {values[-1]}, eğilim {tclass}",
        "expected_reasoning": "Dönemler arası değişim yönleri birlikte incelenmelidir."})

    absent = ABSENT_METRIC.get(source["domain"], "bilinmeyen gösterge")
    if random.random() < 0.5:
        q = f"{periods[-1] + random.choice([3, 5, 8])}. dönemde {metric} kaçtır?"
        reason = "istenen dönem veride bulunmamaktadır"
    else:
        q = f"{random.choice(periods)}. dönemde {absent} kaçtır?"
        reason = f"{absent} veride bulunmamaktadır"
    add("unanswerable", "hard", {
        "target_column": None,
        "question": q,
        "answer": f"Bu soru verilen veriden cevaplanamaz çünkü {reason}.",
        "answer_type": "abstention", "numeric_answer": None,
        "calculation": f"İstenen veri mevcut değil: {reason}.",
        "expected_reasoning": "İstenen veri yoksa cevap verilemeyeceği belirtilmelidir."})

    return out


def main():
    if not PROVENANCE_PATH.exists():
        raise FileNotFoundError("Run scripts/14_fetch_real_sources.py first.")
    provenance = json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))

    table_specs = []
    for source in provenance["sources"]:
        rows = load_source_rows(source["name"])
        for window in make_windows(rows, count=4):
            table_specs.append((source, window))

    total = len(table_specs)
    examples = []
    fmt_state = [0]
    for idx, (source, window) in enumerate(table_specs):
        is_rate = source["metric"] in RATE_METRICS
        scale = random.uniform(0.7, 1.3)
        values = rescale([v for _, v in window], is_rate, scale)
        periods = list(range(1, len(window) + 1))
        chart_type = "line" if idx % 2 == 0 else "bar"
        chart_path_abs = CHART_DIR / f"chart_{idx + 1:03d}_{source['name']}_{chart_type}.png"
        generate_chart(periods, values, source["metric"], source["unit"], chart_type, chart_path_abs)
        chart_path = str(chart_path_abs.relative_to(PROJECT_ROOT)).replace("\\", "/")
        split = ("test" if idx >= int(total * 0.9)
                 else "validation" if idx >= int(total * 0.8) else "train")
        examples.extend(build(source, periods, values, chart_type, chart_path, split, fmt_state))

    with DATASET_PATH.open("w", encoding="utf-8") as f:
        for e in examples:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    pd.DataFrame([{
        "id": e["id"], "domain": e["domain"], "question_type": e["question_type"],
        "input_format": e["input_format"], "question": e["question"], "answer": e["answer"],
        "numeric_answer": e["numeric_answer"], "split": e["split"], "license": e["license"],
    } for e in examples]).to_csv(PREVIEW_PATH, index=False, encoding="utf-8-sig")

    from collections import Counter
    STATS_PATH.write_text(json.dumps({
        "dataset_version": DATASET_VERSION,
        "anonymized": True,
        "note": "Real series, country/years removed and per-series rescaled to control memorization leakage.",
        "total_examples": len(examples),
        "question_type_distribution": dict(Counter(e["question_type"] for e in examples)),
        "split_distribution": dict(Counter(e["split"] for e in examples)),
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print("real_anon_v01 generated.")
    print(f"Tables: {total}  Examples: {len(examples)}")
    print(f"Distribution: {dict(Counter(e['question_type'] for e in examples))}")


if __name__ == "__main__":
    main()
