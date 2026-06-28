"""Generate chart_hard_v01: a deliberately discriminative chart-reading tier.

Earlier manual runs showed frontier models score ~100% on the simpler tiers,
including label-free charts with round, gridline-aligned values. This tier is
built to actually separate strong models, while staying fair (a careful human
can answer) and exactly Python-verifiable:

  - values are NOT rounded -> points fall between gridlines (real interpolation);
  - two overlapping series of similar magnitude cross each other -> the model
    must track the correct line;
  - 12 years -> many points to scan/count;
  - questions include close comparisons and cross-series scanning.

Tasks (all chart_only, label-free):
  - value_estimate     : a series value at a year, scored with a tight ±5% band
  - second_highest_year: the year of the 2nd highest point (exact)
  - count_above        : how many years exceed a round level (exact)
  - closest_compare    : which of the two CLOSEST years is higher (exact)
  - cross_closest_year : the year where the two series are closest (exact)
  - trend              : trend of the target series among a distractor (exact)
"""

import json
import random
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


RANDOM_SEED = 20260628
random.seed(RANDOM_SEED)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
EXPORTS_DIR = PROJECT_ROOT / "data" / "exports"
CHART_DIR = PROJECT_ROOT / "charts" / "chart_hard_v01"
for d in (PROCESSED_DIR, EXPORTS_DIR, CHART_DIR):
    d.mkdir(parents=True, exist_ok=True)

DATASET_PATH = PROCESSED_DIR / "chart_hard_v01.jsonl"
PREVIEW_PATH = EXPORTS_DIR / "chart_hard_v01_preview.csv"
STATS_PATH = EXPORTS_DIR / "chart_hard_v01_stats.json"

DATASET_VERSION = "chart_hard_v01"
ESTIMATE_TOL = 0.05
EXACT = {"numeric_tolerance": 0.0, "numeric_abs_tolerance": 0.0}
N_YEARS = 12

# Two series of comparable magnitude so their lines cross and clutter each other.
TOPICS = [
    {"domain": "transportation", "a": ("iç hat yolcu", "kişi"), "b": ("dış hat yolcu", "kişi"), "base": 1_200_000, "step": 60_000},
    {"domain": "economy", "a": ("ihracat değeri", "milyon dolar"), "b": ("ithalat değeri", "milyon dolar"), "base": 190, "step": 11},
    {"domain": "education", "a": ("kız öğrenci sayısı", "öğrenci"), "b": ("erkek öğrenci sayısı", "öğrenci"), "base": 24_000, "step": 1_200},
    {"domain": "tourism", "a": ("yerli ziyaretçi", "kişi"), "b": ("yabancı ziyaretçi", "kişi"), "base": 620_000, "step": 35_000},
    {"domain": "energy", "a": ("gündüz tüketimi", "MWh"), "b": ("gece tüketimi", "MWh"), "base": 88_000, "step": 4_000},
    {"domain": "health", "a": ("acil başvuru", "başvuru"), "b": ("poliklinik başvuru", "başvuru"), "base": 300_000, "step": 14_000},
    {"domain": "environment", "a": ("geri dönüşüm", "ton"), "b": ("kompost", "ton"), "base": 8_200, "step": 420},
    {"domain": "sports", "a": ("amatör lisans", "sporcu"), "b": ("yıldız lisans", "sporcu"), "base": 13_000, "step": 700},
    {"domain": "municipality", "a": ("açılan başvuru", "başvuru"), "b": ("çözülen başvuru", "başvuru"), "base": 70_000, "step": 3_600},
    {"domain": "agriculture", "a": ("buğday üretimi", "ton"), "b": ("arpa üretimi", "ton"), "base": 150_000, "step": 6_500},
]


def make_series(base, step, mode):
    vals = []
    for i in range(N_YEARS):
        noise = random.randint(-step, step)  # large noise -> off-gridline, jagged
        if mode == "increasing":
            v = base + i * step + noise
        elif mode == "decreasing":
            v = base + (N_YEARS - i) * step + noise
        else:
            v = base + (1 if i % 2 == 0 else -1) * random.randint(0, int(step * 1.5)) + i * random.randint(-step // 3, step // 3) + noise
        vals.append(max(int(v), 1))
    return vals


def detect_trend(values):
    inc = sum(1 for a, b in zip(values, values[1:]) if b > a)
    dec = sum(1 for a, b in zip(values, values[1:]) if b < a)
    if dec == 0 and inc > 0:
        return "increasing"
    if inc == 0 and dec > 0:
        return "decreasing"
    net = values[-1] - values[0]
    if abs(net) / max(abs(values[0]), 1) >= 0.05:
        if net > 0 and inc > dec:
            return "increasing"
        if net < 0 and dec > inc:
            return "decreasing"
    return "mixed"


def fmt(value):
    return f"{int(round(value)):,}".replace(",", ".")


def generate_chart(years, a_vals, b_vals, a_name, b_name, unit, path):
    plt.figure(figsize=(10, 5.2))
    plt.plot(years, a_vals, marker="o", label=a_name)
    plt.plot(years, b_vals, marker="s", label=b_name)
    plt.title(f"{a_name} ve {b_name} ({years[0]}-{years[-1]})")
    plt.xlabel("Yıl")
    plt.ylabel(unit)
    plt.xticks(years, rotation=45)
    plt.gca().yaxis.set_major_locator(plt.MaxNLocator(nbins=11))
    plt.grid(True, which="major", axis="both", alpha=0.4)
    plt.legend()
    plt.margins(y=0.1)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()


def round_threshold(vals):
    sv = sorted(set(vals))
    i = max(1, len(sv) // 2)
    prev_v, mid_v = sv[i - 1], sv[i]
    # a clean round number near the median, strictly inside a gap when possible
    import math
    mag = 10 ** (math.floor(math.log10(max(mid_v, 1))) - 1)
    cand = int(round(((prev_v + mid_v) / 2) / mag) * mag)
    if prev_v < cand < mid_v and cand not in vals:
        return cand
    return (prev_v + mid_v) / 2


EID = 0


def rec(topic, table, a_name, unit, chart_type, chart_path, qtype, split):
    global EID
    EID += 1
    return {
        "id": f"trdab_chard_{EID:06d}",
        "dataset_version": DATASET_VERSION,
        "language": "tr",
        "domain": topic["domain"],
        "source_name": DATASET_VERSION,
        "data_type": "table_chart",
        "input_format": "chart_only",
        "chart_type": chart_type,
        "chart_path": chart_path,
        "question_type": qtype,
        "difficulty": "hard",
        "table": table,
        "target_column": a_name,
        "unit": unit,
        "split": split,
    }


def build(topic, years, a_vals, b_vals, chart_path, split):
    a_name, unit = topic["a"]
    b_name = topic["b"][0]
    table = {"columns": ["Yıl", a_name, b_name],
             "rows": [[y, a, b] for y, a, b in zip(years, a_vals, b_vals)]}
    rows_a = list(zip(years, a_vals))
    out = []

    def add(qtype, upd):
        e = rec(topic, table, a_name, unit, "line", chart_path, qtype, split)
        e.update(upd)
        out.append(e)

    # value_estimate (interior, off-gridline year), tight tolerance
    interior = rows_a[2:-2] or rows_a
    y, v = random.choice(interior)
    add("value_estimate", {
        "question": f"Grafiğe göre {y} yılında {a_name} yaklaşık kaçtır? Cevap olarak sadece sayıyı yaz.",
        "answer": f"{y} yılında yaklaşık {fmt(v)} {unit}.",
        "answer_type": "numeric", "numeric_answer": v,
        "numeric_tolerance": ESTIMATE_TOL, "numeric_abs_tolerance": 0.0,
        "calculation": f"{a_name} {y} = {v} (±%5)",
        "expected_reasoning": "Doğru seri (etiket) seçilip ilgili noktanın yüksekliği gridline'lardan tahmin edilmelidir."})

    # second highest year of A
    ordered = sorted(rows_a, key=lambda r: r[1], reverse=True)
    add("second_highest_year", {**EXACT,
        "question": f"Grafiğe göre {a_name} en yüksek 2. değerine hangi yılda ulaşmıştır? Cevap olarak sadece yılı yaz.",
        "answer": f"{ordered[1][0]} yılında.",
        "answer_type": "numeric", "numeric_answer": ordered[1][0],
        "calculation": f"sıralı {ordered[:3]}, 2.: {ordered[1]}",
        "expected_reasoning": "Doğru serinin en yüksek ikinci noktası bulunmalıdır."})

    # count above a round threshold (12 points, close calls)
    thr = round_threshold(a_vals)
    cnt = sum(1 for v in a_vals if v > thr)
    add("count_above", {**EXACT,
        "question": f"Grafiğe göre kaç yılda {a_name} {fmt(thr)} {unit} değerinin üzerindedir? Cevap olarak sadece sayıyı yaz.",
        "answer": f"{cnt} yıl.",
        "answer_type": "numeric", "numeric_answer": cnt,
        "calculation": f"{a_vals} > {thr} -> {cnt}",
        "expected_reasoning": "Eşik çizgisinin üstündeki noktalar sayılmalıdır."})

    # closest comparison (two nearest-valued years of A)
    best = None
    for i in range(len(rows_a)):
        for j in range(i + 1, len(rows_a)):
            if rows_a[i][1] == rows_a[j][1]:
                continue
            d = abs(rows_a[i][1] - rows_a[j][1])
            if best is None or d < best[0]:
                best = (d, rows_a[i], rows_a[j])
    (ya, va), (yb, vb) = best[1], best[2]
    higher = ya if va > vb else yb
    add("closest_compare", {**EXACT,
        "question": f"Grafiğe göre {ya} ve {yb} yıllarından hangisinde {a_name} daha yüksektir? Cevap olarak sadece yılı yaz.",
        "answer": f"{higher} yılında.",
        "answer_type": "numeric", "numeric_answer": higher,
        "calculation": f"{ya}:{va} vs {yb}:{vb} -> {higher}",
        "expected_reasoning": "Değerleri çok yakın iki yıl dikkatle ayırt edilmelidir."})

    # year where the two series are closest
    gaps = [(y, abs(a - b)) for y, a, b in zip(years, a_vals, b_vals)]
    cross_year = min(gaps, key=lambda g: g[1])[0]
    add("cross_closest_year", {**EXACT,
        "question": f"Grafiğe göre {a_name} ile {b_name} hangi yılda birbirine en yakındır? Cevap olarak sadece yılı yaz.",
        "answer": f"{cross_year} yılında en yakındırlar.",
        "answer_type": "numeric", "numeric_answer": cross_year,
        "calculation": f"yıllık |A-B| min -> {cross_year}",
        "expected_reasoning": "İki çizginin en çok yaklaştığı (en yakın olduğu) yıl bulunmalıdır."})

    # trend of A among the distractor B
    tclass = detect_trend(a_vals)
    word = {"increasing": "artış", "decreasing": "azalış", "mixed": "dalgalı"}[tclass]
    add("trend_summary", {
        "question": f"Grafiğe göre {a_name} için genel eğilim nedir? Cevabı tek kelimeyle ver: artış, azalış veya dalgalı.",
        "answer": f"{a_name} {word} eğilimi göstermektedir.",
        "answer_type": "text", "numeric_answer": None, "trend_class": tclass,
        "calculation": f"{a_vals} -> {tclass}",
        "expected_reasoning": "Doğru serinin genel şekli (diğer seriyle karıştırmadan) değerlendirilmelidir."})

    return out


def main():
    total_tables = 30
    examples = []
    for t in range(total_tables):
        topic = TOPICS[t % len(TOPICS)]
        start = random.choice([2010, 2011, 2012, 2013])
        years = list(range(start, start + N_YEARS))
        a_vals = make_series(topic["base"], topic["step"], random.choice(["increasing", "decreasing", "mixed"]))
        b_vals = make_series(int(topic["base"] * random.uniform(0.85, 1.15)), topic["step"], random.choice(["increasing", "decreasing", "mixed"]))
        chart_path_abs = CHART_DIR / f"chart_{t + 1:03d}.png"
        generate_chart(years, a_vals, b_vals, topic["a"][0], topic["b"][0], topic["a"][1], chart_path_abs)
        chart_path = str(chart_path_abs.relative_to(PROJECT_ROOT)).replace("\\", "/")
        split = ("test" if t >= int(total_tables * 0.9)
                 else "validation" if t >= int(total_tables * 0.8) else "train")
        examples.extend(build(topic, years, a_vals, b_vals, chart_path, split))

    with DATASET_PATH.open("w", encoding="utf-8") as f:
        for e in examples:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    pd.DataFrame([{
        "id": e["id"], "domain": e["domain"], "question_type": e["question_type"],
        "question": e["question"], "numeric_answer": e["numeric_answer"], "split": e["split"],
    } for e in examples]).to_csv(PREVIEW_PATH, index=False, encoding="utf-8-sig")

    from collections import Counter
    STATS_PATH.write_text(json.dumps({
        "dataset_version": DATASET_VERSION,
        "total_examples": len(examples),
        "all_chart_only_label_free": True,
        "series_per_chart": 2,
        "years_per_chart": N_YEARS,
        "question_type_distribution": dict(Counter(e["question_type"] for e in examples)),
        "split_distribution": dict(Counter(e["split"] for e in examples)),
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print("chart_hard_v01 generated.")
    print(f"Tables: {total_tables}  Examples: {len(examples)}")
    print(f"Distribution: {dict(Counter(e['question_type'] for e in examples))}")


if __name__ == "__main__":
    main()
