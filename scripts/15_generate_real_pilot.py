"""Generate the real_pilot dataset from cached real open data.

Reads the locally cached, redistributable World Bank indicators for Türkiye
(see scripts/14_fetch_real_sources.py) and builds verified Turkish data-analysis
questions on top of the *real* numbers. Gold answers are computed with Python,
exactly as in the synthetic tiers, so this stays fully auto-scorable.

The schema matches synthetic_v02, so the version-agnostic evaluator
(08_evaluate_predictions_file.py) scores it without changes.
"""

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCES_DIR = PROJECT_ROOT / "data" / "sources_real"
PROVENANCE_PATH = SOURCES_DIR / "provenance.json"

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
EXPORTS_DIR = PROJECT_ROOT / "data" / "exports"
CHART_DIR = PROJECT_ROOT / "charts" / "real_pilot"

for directory in (PROCESSED_DIR, EXPORTS_DIR, CHART_DIR):
    directory.mkdir(parents=True, exist_ok=True)

DATASET_PATH = PROCESSED_DIR / "real_pilot.jsonl"
PREVIEW_PATH = EXPORTS_DIR / "real_pilot_preview.csv"
STATS_PATH = EXPORTS_DIR / "real_pilot_stats.json"

DATASET_VERSION = "real_pilot"
WINDOW_SIZE = 6

# Plausible-but-absent metric per domain, for unanswerable questions.
ABSENT_METRIC = {
    "demografi": "işsizlik oranı",
    "ekonomi": "cari açık",
}

# Rate-style indicators: skip percentage_change (a percent change of a percent
# rate is confusing) and treat them accordingly.
RATE_METRICS = {"enflasyon oranı"}

INPUT_FORMATS = ["table_only", "chart_only", "table_and_chart"]


def format_number_tr(value: float) -> str:
    if isinstance(value, float) and not float(value).is_integer():
        return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{int(round(value)):,}".replace(",", ".")


def load_source_rows(name: str) -> list[tuple[int, float]]:
    rows = []
    with (SOURCES_DIR / f"{name}.csv").open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for record in reader:
            year = int(record["Year"])
            raw = record["Value"]
            value = int(raw) if raw.lstrip("-").isdigit() else float(raw)
            rows.append((year, value))
    rows.sort(key=lambda r: r[0])
    return rows


def make_windows(rows: list[tuple[int, float]], count: int = 3) -> list[list[tuple[int, float]]]:
    """Take `count` non-overlapping recent windows of WINDOW_SIZE years."""
    windows = []
    end = len(rows)
    for _ in range(count):
        start = end - WINDOW_SIZE
        if start < 0:
            break
        windows.append(rows[start:end])
        end = start
    return list(reversed(windows))


# Minimum net change (relative to the start value) to call a direction on a
# non-monotonic series; below this, a noisy/flat series is "mixed" (dalgalı).
TREND_NET_CHANGE_THRESHOLD = 0.05


def detect_trend(values: list[float]) -> str:
    increases = sum(1 for a, b in zip(values, values[1:]) if b > a)
    decreases = sum(1 for a, b in zip(values, values[1:]) if b < a)

    if decreases == 0 and increases > 0:
        return "increasing"
    if increases == 0 and decreases > 0:
        return "decreasing"

    net = values[-1] - values[0]
    net_ratio = abs(net) / max(abs(values[0]), 1)

    if net_ratio >= TREND_NET_CHANGE_THRESHOLD:
        if net > 0 and increases > decreases:
            return "increasing"
        if net < 0 and decreases > increases:
            return "decreasing"

    return "mixed"


def generate_chart(window, source, chart_type, output_path):
    years = [r[0] for r in window]
    values = [r[1] for r in window]
    plt.figure(figsize=(8, 4.8))
    if chart_type == "line":
        plt.plot(years, values, marker="o")
        for y, v in zip(years, values):
            plt.annotate(format_number_tr(v), (y, v), textcoords="offset points",
                         xytext=(0, 8), ha="center", fontsize=8)
    else:
        bars = plt.bar(years, values)
        for bar, v in zip(bars, values):
            plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                     format_number_tr(v), ha="center", va="bottom", fontsize=8)
    plt.title(f"{source['metric']} - {COUNTRY} ({years[0]}-{years[-1]})")
    plt.xlabel("Yıl")
    plt.ylabel(f"{source['metric']} ({source['unit']})")
    plt.grid(True, alpha=0.3, axis="y")
    plt.margins(y=0.18)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


COUNTRY = "Türkiye"


def base_example(eid, source, table, chart_type, chart_path, qtype, difficulty, split, input_format):
    return {
        "id": f"trdab_real_{eid:06d}",
        "dataset_version": DATASET_VERSION,
        "language": "tr",
        "domain": source["domain"],
        "source_name": source["name"],
        "source_url": source["url"],
        "license": source["license"].get("name", "unknown") if isinstance(source["license"], dict) else str(source["license"]),
        "country": COUNTRY,
        "data_type": "table_chart",
        "input_format": input_format,
        "chart_type": chart_type,
        "chart_path": chart_path,
        "question_type": qtype,
        "difficulty": difficulty,
        "table": table,
        "target_column": source["metric"],
        "unit": source["unit"],
        "split": split,
    }


def build_tasks(eid_start, source, window, chart_type, chart_path, split, fmt_cycle):
    metric = source["metric"]
    unit = source["unit"]
    is_rate = metric in RATE_METRICS
    years = [r[0] for r in window]
    values = [r[1] for r in window]
    table = {"columns": ["Yıl", metric], "rows": [[y, v] for y, v in window]}

    examples = []
    eid = eid_start

    def fmt():
        nonlocal fmt_cycle
        f = INPUT_FORMATS[fmt_cycle % 3]
        fmt_cycle += 1
        return f

    def add(qtype, difficulty, updates):
        nonlocal eid
        ex = base_example(eid, source, table, chart_type, chart_path, qtype, difficulty, split, fmt())
        ex.update(updates)
        examples.append(ex)
        eid += 1

    # value_lookup
    y, v = window[-2]
    add("value_lookup", "easy", {
        "question": f"{COUNTRY}'de {y} yılında {metric} kaçtır?",
        "answer": f"{COUNTRY}'de {y} yılında {metric} {format_number_tr(v)} {unit} olarak gerçekleşmiştir.",
        "answer_type": "numeric", "numeric_answer": v,
        "calculation": f"{y} satırındaki değer: {v}",
        "expected_reasoning": "İlgili yıla karşılık gelen değer okunmalıdır.",
    })

    # comparison (absolute difference)
    diff = abs(values[-1] - values[0])
    add("comparison", "medium", {
        "question": f"{COUNTRY}'de {years[-1]} yılındaki {metric}, {years[0]} yılına göre kaç {unit} farklıdır?",
        "answer": f"{years[-1]} ile {years[0]} arasındaki {metric} farkı {format_number_tr(diff)} {unit}.",
        "answer_type": "numeric", "numeric_answer": round(diff, 2) if isinstance(diff, float) else diff,
        "calculation": f"|{values[-1]} - {values[0]}| = {diff}",
        "expected_reasoning": "İki yılın değerleri arasındaki mutlak fark hesaplanmalıdır.",
    })

    # average
    mean_value = round(sum(values) / len(values), 2)
    add("average", "hard", {
        "question": f"{COUNTRY}'de {years[0]}-{years[-1]} arasında {metric} ortalaması yaklaşık kaçtır?",
        "answer": f"{years[0]}-{years[-1]} arasında ortalama {metric} yaklaşık {format_number_tr(mean_value)} {unit}.",
        "answer_type": "numeric", "numeric_answer": mean_value,
        "calculation": f"ortalama({values}) = {mean_value}",
        "expected_reasoning": "Tüm yıl değerleri toplanıp yıl sayısına bölünmelidir.",
    })

    # nth_highest (2nd highest)
    ordered = sorted(window, key=lambda r: r[1], reverse=True)
    second = ordered[1]
    add("nth_highest", "hard", {
        "question": f"{COUNTRY}'de {metric} açısından en yüksek 2. değer kaçtır?",
        "answer": f"{metric} açısından en yüksek 2. değer {format_number_tr(second[1])} {unit} olup {second[0]} yılındadır.",
        "answer_type": "numeric_with_label", "numeric_answer": second[1],
        "calculation": f"değerler sıralanır, 2. en yüksek: {second[1]} ({second[0]})",
        "expected_reasoning": "Değerler büyükten küçüğe sıralanıp ikinci değer alınmalıdır.",
    })

    # percentage_change (only for level metrics, signed)
    if not is_rate:
        start_v, end_v = values[0], values[-1]
        pct = round(((end_v - start_v) / start_v) * 100, 1)
        direction = "artmıştır" if pct > 0 else ("azalmıştır" if pct < 0 else "değişmemiştir")
        add("percentage_change", "medium", {
            "question": (
                f"{COUNTRY}'de {years[0]} ile {years[-1]} arasında {metric} yaklaşık yüzde kaç değişmiştir? "
                f"Artış için pozitif, azalış için negatif değer ver."
            ),
            "answer": f"{years[0]}-{years[-1]} arasında {metric} yaklaşık %{format_number_tr(abs(pct))} {direction}.",
            "answer_type": "numeric", "numeric_answer": pct, "unit": "percent",
            "calculation": f"(({end_v} - {start_v}) / {start_v}) * 100 = {pct}",
            "expected_reasoning": "Yüzde değişim yön dahil hesaplanmalıdır.",
        })

    # trend_summary
    tclass = detect_trend(values)
    word = {"increasing": "artış", "decreasing": "azalış", "mixed": "dalgalı"}[tclass]
    add("trend_summary", "medium", {
        "question": f"{COUNTRY}'de {metric} için genel eğilim nedir? Cevabı tek kelimeyle ver: artış, azalış veya dalgalı.",
        "answer": f"{metric} {years[0]}-{years[-1]} arasında genel olarak {word} eğilimi göstermektedir.",
        "answer_type": "text", "numeric_answer": None, "trend_class": tclass,
        "calculation": f"başlangıç {values[0]}, bitiş {values[-1]}, eğilim: {tclass}",
        "expected_reasoning": "Başlangıç, bitiş ve ara değişimler birlikte incelenmelidir.",
    })

    # unanswerable (absent metric)
    absent = ABSENT_METRIC.get(source["domain"], "bilinmeyen gösterge")
    add("unanswerable", "hard", {
        "target_column": None,
        "question": f"{COUNTRY}'de {years[-1]} yılında {absent} kaçtır?",
        "answer": f"Bu soru verilen veriden cevaplanamaz çünkü {absent} tabloda/grafikte bulunmamaktadır.",
        "answer_type": "abstention", "numeric_answer": None,
        "calculation": f"İstenen veri mevcut değil: {absent}.",
        "expected_reasoning": "İstenen veri yoksa cevap verilemeyeceği belirtilmelidir.",
    })

    return examples, eid, fmt_cycle


def split_for_table(index: int, total: int) -> str:
    if index >= total - 2:
        return "test"
    if index == total - 3:
        return "validation"
    return "train"


def save_jsonl(examples, path):
    with path.open("w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")


def save_preview(examples, path):
    pd.DataFrame([{
        "id": e["id"], "domain": e["domain"], "source_name": e["source_name"],
        "input_format": e["input_format"], "question_type": e["question_type"],
        "difficulty": e["difficulty"], "question": e["question"], "answer": e["answer"],
        "numeric_answer": e["numeric_answer"], "unit": e["unit"], "split": e["split"],
        "license": e["license"],
    } for e in examples]).to_csv(path, index=False, encoding="utf-8-sig")


def save_stats(examples, path, provenance):
    from collections import Counter
    stats = {
        "dataset_version": DATASET_VERSION,
        "country": COUNTRY,
        "total_examples": len(examples),
        "unique_charts": len(set(e["chart_path"] for e in examples)),
        "sources": [s["name"] for s in provenance["sources"]],
        "licenses": sorted(set(e["license"] for e in examples)),
        "question_type_distribution": dict(Counter(e["question_type"] for e in examples)),
        "answer_type_distribution": dict(Counter(e["answer_type"] for e in examples)),
        "difficulty_distribution": dict(Counter(e["difficulty"] for e in examples)),
        "input_format_distribution": dict(Counter(e["input_format"] for e in examples)),
        "split_distribution": dict(Counter(e["split"] for e in examples)),
    }
    path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    if not PROVENANCE_PATH.exists():
        raise FileNotFoundError("Run scripts/14_fetch_real_sources.py first to cache sources.")

    provenance = json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))

    # Build the table list (source x window) first so we can assign splits by table.
    table_specs = []
    for source in provenance["sources"]:
        rows = load_source_rows(source["name"])
        for window in make_windows(rows, count=3):
            table_specs.append((source, window))

    examples = []
    eid = 1
    fmt_cycle = 0
    total_tables = len(table_specs)

    for table_idx, (source, window) in enumerate(table_specs):
        chart_type = "line" if (table_idx % 2 == 0) else "bar"
        chart_path_abs = CHART_DIR / f"chart_{table_idx + 1:03d}_{source['name']}_{chart_type}.png"
        generate_chart(window, source, chart_type, chart_path_abs)
        chart_path = str(chart_path_abs.relative_to(PROJECT_ROOT)).replace("\\", "/")

        split = split_for_table(table_idx, total_tables)
        batch, eid, fmt_cycle = build_tasks(eid, source, window, chart_type, chart_path, split, fmt_cycle)
        examples.extend(batch)

    save_jsonl(examples, DATASET_PATH)
    save_preview(examples, PREVIEW_PATH)
    save_stats(examples, STATS_PATH, provenance)

    print("real_pilot dataset generated successfully.")
    print(f"Tables: {total_tables}  Examples: {len(examples)}")
    print(f"Sources: {[s['name'] for s in provenance['sources']]}")
    print(f"JSONL: {DATASET_PATH}")


if __name__ == "__main__":
    main()
