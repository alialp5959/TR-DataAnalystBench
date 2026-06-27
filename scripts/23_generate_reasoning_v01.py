"""Generate reasoning_v01: a hard, multi-step numerical-reasoning tier.

These tasks require multiple computation steps that strong models frequently
get wrong, while staying exactly Python-verifiable. Every example is
`table_only` (a multi-series table is always provided), so the tier isolates
*reasoning* rather than table/chart reading.

Tasks:
  - cagr                    : compound annual growth rate of a series
  - fastest_change_year     : the year with the largest year-over-year increase
  - longest_increase_streak : length of the longest run of consecutive increases
  - conditional_average     : mean of the years whose value exceeds a threshold
  - share_of_total          : a year's value as a percentage of the total
  - ratio                   : ratio between the two series in a given year

Per-example tolerances are written into the data and honored by the evaluator:
exact tasks (year / streak length) require an exact match; the rest use a
small relative/absolute tolerance.
"""

import json
import random
from pathlib import Path


RANDOM_SEED = 4242
random.seed(RANDOM_SEED)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
EXPORTS_DIR = PROJECT_ROOT / "data" / "exports"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

DATASET_PATH = PROCESSED_DIR / "reasoning_v01.jsonl"
PREVIEW_PATH = EXPORTS_DIR / "reasoning_v01_preview.csv"
STATS_PATH = EXPORTS_DIR / "reasoning_v01_stats.json"

DATASET_VERSION = "reasoning_v01"

TOPICS = [
    {"domain": "transportation", "a": ("yolcu sayısı", "kişi", 1_200_000, 95_000), "b": ("sefer sayısı", "sefer", 42_000, 2_600)},
    {"domain": "economy", "a": ("ihracat değeri", "milyon dolar", 180, 16), "b": ("ithalat değeri", "milyon dolar", 210, 14)},
    {"domain": "education", "a": ("öğrenci sayısı", "öğrenci", 25_000, 1_100), "b": ("öğretmen sayısı", "öğretmen", 1_700, 70)},
    {"domain": "tourism", "a": ("ziyaretçi sayısı", "kişi", 600_000, 55_000), "b": ("konaklama sayısı", "gece", 1_400_000, 90_000)},
    {"domain": "energy", "a": ("elektrik tüketimi", "MWh", 90_000, 4_200), "b": ("doğal gaz tüketimi", "m3", 320_000, 12_000)},
    {"domain": "health", "a": ("hastane başvurusu", "başvuru", 310_000, 18_000), "b": ("ameliyat sayısı", "ameliyat", 24_000, 1_300)},
    {"domain": "environment", "a": ("geri dönüşüm", "ton", 8_000, 560), "b": ("toplam atık", "ton", 41_000, 1_900)},
    {"domain": "sports", "a": ("tesis kullanımı", "kullanım", 45_000, 3_000), "b": ("lisanslı sporcu", "sporcu", 12_000, 800)},
    {"domain": "municipality", "a": ("hizmet başvurusu", "başvuru", 70_000, 4_500), "b": ("çözülen başvuru", "başvuru", 61_000, 4_100)},
    {"domain": "agriculture", "a": ("üretim miktarı", "ton", 150_000, 7_800), "b": ("ekili alan", "hektar", 38_000, 1_500)},
]

EXACT = {"numeric_tolerance": 0.0, "numeric_abs_tolerance": 0.0}


def format_number_tr(value):
    if isinstance(value, float) and not float(value).is_integer():
        return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{int(round(value)):,}".replace(",", ".")


def make_series(base, step, n, mode):
    vals = []
    for i in range(n):
        noise = random.randint(-step // 3, step // 3)
        if mode == "increasing":
            v = base + i * step + noise
        elif mode == "decreasing":
            v = base + (n - i) * step + noise
        else:
            v = base + (1 if i % 2 == 0 else -1) * random.randint(0, step * 2) + i * random.randint(-step // 4, step // 4) + noise
        vals.append(max(int(v), 1))
    return vals


EID = 0


def base_example(topic, table, metric, unit, qtype, split):
    global EID
    EID += 1
    return {
        "id": f"trdab_reason_{EID:06d}",
        "dataset_version": DATASET_VERSION,
        "language": "tr",
        "domain": topic["domain"],
        "source_name": "reasoning_v01",
        "data_type": "table",
        "input_format": "table_only",
        "chart_type": None,
        "chart_path": None,
        "question_type": qtype,
        "difficulty": "hard",
        "table": table,
        "target_column": metric,
        "unit": unit,
        "split": split,
    }


def build(topic, years, a_vals, b_vals, split):
    a_metric, a_unit = topic["a"][0], topic["a"][1]
    b_metric = topic["b"][0]
    table = {"columns": ["Yıl", a_metric, b_metric],
             "rows": [[y, a, b] for y, a, b in zip(years, a_vals, b_vals)]}
    out = []

    def add(qtype, upd):
        ex = base_example(topic, table, a_metric, a_unit, qtype, split)
        ex.update(upd)
        out.append(ex)

    n = len(years)

    # CAGR of series A
    cagr = (((a_vals[-1] / a_vals[0]) ** (1 / (n - 1))) - 1) * 100
    cagr_r = round(cagr, 1)
    add("cagr", {**{"numeric_tolerance": 0.05, "numeric_abs_tolerance": 0.5},
        "question": (f"{a_metric} için {years[0]}-{years[-1]} arasındaki bileşik yıllık büyüme oranı (CAGR) "
                     f"yaklaşık yüzde kaçtır? Artış için pozitif, azalış için negatif değer ver."),
        "answer": f"CAGR yaklaşık %{format_number_tr(abs(cagr_r))}.",
        "answer_type": "numeric", "numeric_answer": cagr_r, "unit": "percent",
        "calculation": f"(({a_vals[-1]}/{a_vals[0]})^(1/{n-1}) - 1)*100 = {cagr_r}",
        "expected_reasoning": "Bileşik büyüme: (son/ilk)^(1/yıl sayısı) - 1."})

    # fastest year-over-year change. If the series never increases, asking for
    # the biggest "increase" would be ill-posed, so we ask for the biggest
    # decrease instead — keeping a well-defined year answer.
    deltas = [(years[i], a_vals[i] - a_vals[i - 1]) for i in range(1, n)]
    max_d = max(deltas, key=lambda d: d[1])
    if max_d[1] > 0:
        direction, fast_year = "artmıştır", max_d[0]
        verb = "artış"
    else:
        min_d = min(deltas, key=lambda d: d[1])
        direction, fast_year = "azalmıştır", min_d[0]
        verb = "azalış"
    add("fastest_change_year", {**EXACT,
        "question": f"{a_metric} bir önceki yıla göre en çok hangi yılda {direction}? Cevap olarak sadece yılı yaz.",
        "answer": f"En büyük yıllık {verb} {fast_year} yılında olmuştur.",
        "answer_type": "numeric", "numeric_answer": fast_year,
        "calculation": f"yıllık farklar {deltas}, en büyük {verb} yılı {fast_year}",
        "expected_reasoning": "Ardışık yıl farkları hesaplanıp istenen yönde en büyük değişimin yılı seçilmelidir."})

    # longest streak of consecutive increases (in steps)
    best = cur = 0
    for i in range(1, n):
        cur = cur + 1 if a_vals[i] > a_vals[i - 1] else 0
        best = max(best, cur)
    add("longest_increase_streak", {**EXACT,
        "question": (f"{a_metric} bir önceki yıla göre art arda en fazla kaç kez artmıştır "
                     f"(en uzun kesintisiz artış serisi)? Cevap olarak sadece sayıyı yaz."),
        "answer": f"En uzun kesintisiz artış serisi {best} yıldır.",
        "answer_type": "numeric", "numeric_answer": best,
        "calculation": f"ardışık artış serileri içinde en uzunu {best}",
        "expected_reasoning": "Ardışık yıl-yıl artışların en uzun kesintisiz serisi sayılmalıdır."})

    # conditional average: mean of A over years where A > threshold
    lo, hi = min(a_vals), max(a_vals)
    sa = sorted(a_vals)
    threshold = sa[max(1, n // 3)]  # ensures several values above it
    above = [v for v in a_vals if v > threshold]
    if len(above) < 2:
        above = sorted(a_vals)[-2:]
        threshold = sorted(a_vals)[-3] if n >= 3 else min(a_vals)
        above = [v for v in a_vals if v > threshold]
    cond_avg = round(sum(above) / len(above), 1)
    add("conditional_average", {**{"numeric_tolerance": 0.02, "numeric_abs_tolerance": 1.0},
        "question": (f"{a_metric} değerinin {format_number_tr(threshold)} {a_unit} değerinden büyük olduğu "
                     f"yıllardaki ortalama {a_metric} kaçtır?"),
        "answer": f"Bu yıllardaki ortalama yaklaşık {format_number_tr(cond_avg)} {a_unit}.",
        "answer_type": "numeric", "numeric_answer": cond_avg,
        "calculation": f">{threshold} olanlar {above}, ortalama {cond_avg}",
        "expected_reasoning": "Önce eşiği aşan yıllar seçilip yalnızca onların ortalaması alınmalıdır."})

    # share of total
    total = sum(a_vals)
    sy_idx = random.randrange(n)
    share = round(a_vals[sy_idx] / total * 100, 1)
    add("share_of_total", {**{"numeric_tolerance": 0.0, "numeric_abs_tolerance": 1.0},
        "question": (f"Tüm yılların toplam {a_metric} değeri içinde {years[sy_idx]} yılının payı "
                     f"yaklaşık yüzde kaçtır?"),
        "answer": f"{years[sy_idx]} yılının payı yaklaşık %{format_number_tr(share)}.",
        "answer_type": "numeric", "numeric_answer": share, "unit": "percent",
        "calculation": f"{a_vals[sy_idx]} / {total} * 100 = {share}",
        "expected_reasoning": "İlgili yılın değeri tüm yılların toplamına bölünüp 100 ile çarpılmalıdır."})

    # ratio of the two series in a year
    ry_idx = random.randrange(n)
    ratio = round(a_vals[ry_idx] / b_vals[ry_idx], 2)
    add("ratio", {**{"numeric_tolerance": 0.05, "numeric_abs_tolerance": 0.05},
        "question": f"{years[ry_idx]} yılında {a_metric}, {b_metric}'nin yaklaşık kaç katıdır?",
        "answer": f"{years[ry_idx]} yılında {a_metric}, {b_metric}'nin yaklaşık {format_number_tr(ratio)} katıdır.",
        "answer_type": "numeric", "numeric_answer": ratio,
        "calculation": f"{a_vals[ry_idx]} / {b_vals[ry_idx]} = {ratio}",
        "expected_reasoning": "Aynı yıldaki iki serinin değerleri bölünmelidir."})

    return out


def main():
    total_tables = 30
    examples = []
    for t in range(total_tables):
        topic = TOPICS[t % len(TOPICS)]
        start_year = random.choice([2016, 2017, 2018])
        n = random.choice([6, 7])
        years = list(range(start_year, start_year + n))
        a_vals = make_series(topic["a"][2], topic["a"][3], n, random.choice(["increasing", "decreasing", "mixed"]))
        b_vals = make_series(topic["b"][2], topic["b"][3], n, random.choice(["increasing", "decreasing", "mixed"]))
        split = ("test" if t >= int(total_tables * 0.9)
                 else "validation" if t >= int(total_tables * 0.8) else "train")
        examples.extend(build(topic, years, a_vals, b_vals, split))

    with DATASET_PATH.open("w", encoding="utf-8") as f:
        for e in examples:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    import csv
    with PREVIEW_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "domain", "question_type", "question", "answer", "numeric_answer", "split"])
        for e in examples:
            w.writerow([e["id"], e["domain"], e["question_type"], e["question"], e["answer"], e["numeric_answer"], e["split"]])

    from collections import Counter
    STATS_PATH.write_text(json.dumps({
        "dataset_version": DATASET_VERSION,
        "total_examples": len(examples),
        "all_table_only": True,
        "question_type_distribution": dict(Counter(e["question_type"] for e in examples)),
        "split_distribution": dict(Counter(e["split"] for e in examples)),
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print("reasoning_v01 generated.")
    print(f"Tables: {total_tables}  Examples: {len(examples)}")
    print(f"Distribution: {dict(Counter(e['question_type'] for e in examples))}")


if __name__ == "__main__":
    main()
