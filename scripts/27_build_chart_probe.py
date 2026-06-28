"""Build a curated 16-question "critical" chart-reading probe.

Selects label-free charts from chart_read_v01 and writes a balanced, deliberately
hard probe set aimed at discriminating strong vision models:
  - 5 value_estimate : choose the year whose value sits farthest from a gridline
  - 4 count_above    : count points above a round threshold line
  - 3 compare_years  : the TWO CLOSEST years (visually hard to tell apart)
  - 2 max_min_year   : which year is the extreme
  - 2 trend_summary  : overall shape

Output is a standard-schema JSONL (split=test), so scripts/25 and 26 build the
bulk prompt / charts manifest and score it unchanged.
"""

import json
import math
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "data" / "processed" / "chart_read_v01.jsonl"
OUT = PROJECT_ROOT / "data" / "processed" / "chart_read_probe16.jsonl"

ESTIMATE_TOL = 0.08
EXACT = {"numeric_tolerance": 0.0, "numeric_abs_tolerance": 0.0}


def load(path):
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def fmt(value):
    if isinstance(value, float) and not float(value).is_integer():
        return f"{value:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{int(round(value)):,}".replace(",", ".")


def nice_round(value):
    if value <= 0:
        return 1
    mag = 10 ** (math.floor(math.log10(abs(value))) - 1)
    return int(round(value / mag) * mag)


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


# --- per-task constructors (recompute gold from the chart's table) ---

def hardest_estimate_year(rows):
    vals = [v for _, v in rows]
    lo, hi = min(vals), max(vals)
    step = max((hi - lo) / 5, 1)
    # year whose value is farthest from a gridline multiple
    best = max(rows, key=lambda r: abs((r[1] - lo) / step - round((r[1] - lo) / step)))
    return best


def round_threshold(vals):
    sv = sorted(set(vals))
    i = max(1, len(sv) // 2)
    prev_v, mid_v = sv[i - 1], sv[i]
    cand = nice_round((prev_v + mid_v) / 2)
    if prev_v < cand < mid_v and cand not in vals:
        return cand
    return (prev_v + mid_v) / 2


def closest_pair(rows):
    best = None
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            if rows[i][1] == rows[j][1]:
                continue
            d = abs(rows[i][1] - rows[j][1])
            if best is None or d < best[0]:
                best = (d, rows[i], rows[j])
    return best[1], best[2]


EID = 0


def rec(src, qtype, difficulty):
    global EID
    EID += 1
    return {
        "id": f"trdab_crprobe_{EID:03d}",
        "dataset_version": "chart_read_probe16",
        "language": "tr",
        "domain": src["domain"],
        "source_name": "chart_read_probe16",
        "data_type": "table_chart",
        "input_format": "chart_only",
        "chart_type": src["chart_type"],
        "chart_path": src["chart_path"],
        "question_type": qtype,
        "difficulty": difficulty,
        "table": src["table"],
        "target_column": src["target_column"],
        "unit": src["unit"],
        "split": "test",
    }


def build_value_estimate(src):
    rows = src["table"]["rows"]
    y, v = hardest_estimate_year(rows)
    e = rec(src, "value_estimate", "hard")
    e.update({"question": f"Grafiğe göre {y} yılında {src['target_column']} yaklaşık kaçtır? Cevap olarak sadece sayıyı yaz.",
              "answer": f"{y} yılında yaklaşık {fmt(v)} {src['unit']}.",
              "answer_type": "numeric", "numeric_answer": v,
              "numeric_tolerance": ESTIMATE_TOL, "numeric_abs_tolerance": 0.0,
              "calculation": f"{y} -> ~{v} (±%8)", "expected_reasoning": "Yükseklik gridline'lardan tahmin edilmelidir."})
    return e


def build_count_above(src):
    rows = src["table"]["rows"]
    vals = [v for _, v in rows]
    thr = round_threshold(vals)
    cnt = sum(1 for v in vals if v > thr)
    e = rec(src, "count_above", "hard")
    e.update({"question": f"Grafiğe göre kaç yılda {src['target_column']} {fmt(thr)} {src['unit']} değerinin üzerindedir? Cevap olarak sadece sayıyı yaz.",
              "answer": f"{cnt} yıl.", **EXACT,
              "answer_type": "numeric", "numeric_answer": cnt,
              "calculation": f"{vals} > {thr} -> {cnt}", "expected_reasoning": "Eşik çizgisinin üstündeki yıllar sayılmalıdır."})
    return e


def build_compare(src):
    rows = src["table"]["rows"]
    (ya, va), (yb, vb) = closest_pair(rows)
    higher = ya if va > vb else yb
    e = rec(src, "compare_years", "hard")
    e.update({"question": f"Grafiğe göre {ya} ve {yb} yıllarından hangisinde {src['target_column']} daha yüksektir? Cevap olarak sadece yılı yaz.",
              "answer": f"{higher} yılında daha yüksektir.", **EXACT,
              "answer_type": "numeric", "numeric_answer": higher,
              "calculation": f"{ya}:{va} vs {yb}:{vb} -> {higher}", "expected_reasoning": "En yakın iki yılın yükseklikleri dikkatle karşılaştırılmalıdır."})
    return e


def build_max_min(src, want_max):
    rows = src["table"]["rows"]
    y, v = (max if want_max else min)(rows, key=lambda r: r[1])
    word = "en yüksek" if want_max else "en düşük"
    e = rec(src, "max_min_year", "medium")
    e.update({"question": f"Grafiğe göre {word} {src['target_column']} hangi yılda görülmüştür? Cevap olarak sadece yılı yaz.",
              "answer": f"{y} yılında.", **EXACT,
              "answer_type": "numeric", "numeric_answer": y,
              "calculation": f"{word}: {v} ({y})", "expected_reasoning": "Grafikteki uç nokta bulunup yılı okunmalıdır."})
    return e


def build_trend(src):
    rows = src["table"]["rows"]
    vals = [v for _, v in rows]
    tclass = detect_trend(vals)
    word = {"increasing": "artış", "decreasing": "azalış", "mixed": "dalgalı"}[tclass]
    e = rec(src, "trend_summary", "medium")
    e.update({"question": f"Grafiğe göre {src['target_column']} için genel eğilim nedir? Cevabı tek kelimeyle ver: artış, azalış veya dalgalı.",
              "answer": f"{word} eğilimi.", "answer_type": "text", "numeric_answer": None, "trend_class": tclass,
              "calculation": f"{vals} -> {tclass}", "expected_reasoning": "Grafiğin genel şekli değerlendirilmelidir."})
    return e


def main():
    records = load(SRC)
    # one representative record per chart (each chart appears 6x); keep the table+meta
    by_chart = {}
    for r in records:
        by_chart.setdefault(r["chart_path"], r)
    charts = list(by_chart.values())

    # spread across domains/chart types: pick 8 evenly
    idxs = [round(k * (len(charts) - 1) / 7) for k in range(8)]
    picked = [charts[i] for i in idxs]

    # (chart, [task specs]) to hit the target distribution
    plan = [
        (0, [("ve",), ("ca",)]),
        (1, [("ve",), ("cmp",)]),
        (2, [("ve",), ("max",)]),
        (3, [("ve",), ("trend",)]),
        (4, [("ve",), ("ca",)]),
        (5, [("ca",), ("cmp",)]),
        (6, [("ca",), ("min",)]),
        (7, [("cmp",), ("trend",)]),
    ]
    build = {
        "ve": build_value_estimate, "ca": build_count_above, "cmp": build_compare,
        "max": lambda s: build_max_min(s, True), "min": lambda s: build_max_min(s, False),
        "trend": build_trend,
    }

    out = []
    for ci, specs in plan:
        for (t,) in specs:
            out.append(build[t](picked[ci]))

    with OUT.open("w", encoding="utf-8") as f:
        for e in out:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    from collections import Counter
    print(f"Probe set written: {OUT}")
    print(f"Questions: {len(out)}  Charts used: {len(set(e['chart_path'] for e in out))}")
    print(f"Distribution: {dict(Counter(e['question_type'] for e in out))}")


if __name__ == "__main__":
    main()
