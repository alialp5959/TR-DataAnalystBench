"""Build a dense ~50-question hard-chart probe over just 3 charts.

So a model can be tested in only 3 chats (one image + ~17 questions each), this
packs many verifiable questions onto each of 3 cluttered, off-gridline,
two-series charts from chart_hard_v01. Output is standard-schema JSONL
(split=test) so scripts/25 and 26 build the bulk prompt and score it.
"""

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "data" / "processed" / "chart_hard_v01.jsonl"
OUT = PROJECT_ROOT / "data" / "processed" / "chart_hard_probe50.jsonl"

VAL_TOL = {"numeric_tolerance": 0.05, "numeric_abs_tolerance": 0.0}
DIFF_TOL = {"numeric_tolerance": 0.08, "numeric_abs_tolerance": 0.0}
EXACT = {"numeric_tolerance": 0.0, "numeric_abs_tolerance": 0.0}


def load(path):
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def fmt(v):
    return f"{int(round(v)):,}".replace(",", ".")


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


def thr_between(vals, pos):
    sv = sorted(set(vals))
    i = min(max(1, pos), len(sv) - 1)
    prev_v, mid_v = sv[i - 1], sv[i]
    import math
    mag = 10 ** (math.floor(math.log10(max(mid_v, 1))) - 1)
    cand = int(round(((prev_v + mid_v) / 2) / mag) * mag)
    if prev_v < cand < mid_v and cand not in vals:
        return cand
    return (prev_v + mid_v) / 2


EID = 0


def make(src, qtype, q, ans_num, tol, calc, trend_class=None):
    global EID
    EID += 1
    e = {
        "id": f"trdab_chp50_{EID:03d}",
        "dataset_version": "chart_hard_probe50",
        "language": "tr",
        "domain": src["domain"],
        "source_name": "chart_hard_probe50",
        "data_type": "table_chart",
        "input_format": "chart_only",
        "chart_type": "line",
        "chart_path": src["chart_path"],
        "question_type": qtype,
        "difficulty": "hard",
        "table": src["table"],
        "target_column": src["target_column"],
        "unit": src["unit"],
        "split": "test",
        "question": q,
        "answer": (f"~{fmt(ans_num)}" if ans_num is not None else trend_class),
        "calculation": calc,
        "expected_reasoning": "Doğru seri seçilip grafikten dikkatle okunmalıdır.",
    }
    if trend_class is not None:
        e.update({"answer_type": "text", "numeric_answer": None, "trend_class": trend_class})
    else:
        e.update({"answer_type": "numeric", "numeric_answer": ans_num, **tol})
    return e


def build_for_chart(src):
    cols = src["table"]["columns"]
    rows = src["table"]["rows"]
    a_name, b_name = cols[1], cols[2]
    years = [r[0] for r in rows]
    A = [r[1] for r in rows]
    B = [r[2] for r in rows]
    unit = src["unit"]
    rows_a = list(zip(years, A))
    out = []

    def Q(s):
        return f"Grafiğe göre {s} Cevap olarak sadece {'eğilimi (artış/azalış/dalgalı)' if False else 'sayıyı/yılı'} yaz."

    # value estimates on A (3 interior years) and B (2 years)
    for idx in (3, 6, 9):
        out.append(make(src, "value_estimate",
                        f"Grafiğe göre {years[idx]} yılında {a_name} yaklaşık kaçtır? Cevap olarak sadece sayıyı yaz.",
                        A[idx], VAL_TOL, f"{a_name} {years[idx]} = {A[idx]}"))
    for idx in (4, 8):
        out.append(make(src, "value_estimate",
                        f"Grafiğe göre {years[idx]} yılında {b_name} yaklaşık kaçtır? Cevap olarak sadece sayıyı yaz.",
                        B[idx], VAL_TOL, f"{b_name} {years[idx]} = {B[idx]}"))

    # range (max-min) of A
    rng = max(A) - min(A)
    out.append(make(src, "range",
                    f"Grafiğe göre {a_name} en yüksek ve en düşük yıllar arasındaki fark yaklaşık kaçtır? Cevap olarak sadece sayıyı yaz.",
                    rng, DIFF_TOL, f"max-min A = {rng}"))

    # ranking
    ordered = sorted(rows_a, key=lambda r: r[1], reverse=True)
    out.append(make(src, "max_year",
                    f"Grafiğe göre {a_name} en yüksek değerine hangi yılda ulaşmıştır? Cevap olarak sadece yılı yaz.",
                    ordered[0][0], EXACT, f"max {ordered[0]}"))
    out.append(make(src, "second_highest_year",
                    f"Grafiğe göre {a_name} en yüksek 2. değerine hangi yılda ulaşmıştır? Cevap olarak sadece yılı yaz.",
                    ordered[1][0], EXACT, f"2nd {ordered[1]}"))
    out.append(make(src, "third_highest_year",
                    f"Grafiğe göre {a_name} en yüksek 3. değerine hangi yılda ulaşmıştır? Cevap olarak sadece yılı yaz.",
                    ordered[2][0], EXACT, f"3rd {ordered[2]}"))
    out.append(make(src, "min_year",
                    f"Grafiğe göre {a_name} en düşük değerine hangi yılda ulaşmıştır? Cevap olarak sadece yılı yaz.",
                    min(rows_a, key=lambda r: r[1])[0], EXACT, "min A"))

    # counts (A two thresholds, B one)
    t1 = thr_between(A, len(set(A)) // 2)
    out.append(make(src, "count_above",
                    f"Grafiğe göre kaç yılda {a_name} {fmt(t1)} {unit} değerinin üzerindedir? Cevap olarak sadece sayıyı yaz.",
                    sum(1 for v in A if v > t1), EXACT, f"A > {t1} -> {sum(1 for v in A if v > t1)}"))
    t2 = thr_between(A, int(len(set(A)) * 0.72))
    out.append(make(src, "count_above",
                    f"Grafiğe göre kaç yılda {a_name} {fmt(t2)} {unit} değerinin üzerindedir? Cevap olarak sadece sayıyı yaz.",
                    sum(1 for v in A if v > t2), EXACT, f"A > {t2} -> {sum(1 for v in A if v > t2)}"))
    tb = thr_between(B, len(set(B)) // 2)
    out.append(make(src, "count_above",
                    f"Grafiğe göre kaç yılda {b_name} {fmt(tb)} {unit} değerinin üzerindedir? Cevap olarak sadece sayıyı yaz.",
                    sum(1 for v in B if v > tb), EXACT, f"B > {tb} -> {sum(1 for v in B if v > tb)}"))

    # closest pair on A
    best = None
    for i in range(len(rows_a)):
        for j in range(i + 1, len(rows_a)):
            if rows_a[i][1] == rows_a[j][1]:
                continue
            d = abs(rows_a[i][1] - rows_a[j][1])
            if best is None or d < best[0]:
                best = (d, rows_a[i], rows_a[j])
    (ya, va), (yb, vb) = best[1], best[2]
    out.append(make(src, "closest_compare",
                    f"Grafiğe göre {ya} ve {yb} yıllarından hangisinde {a_name} daha yüksektir? Cevap olarak sadece yılı yaz.",
                    ya if va > vb else yb, EXACT, f"{ya}:{va} vs {yb}:{vb}"))

    # cross-series closest / furthest year
    gaps = [(y, abs(a - b)) for y, a, b in zip(years, A, B)]
    out.append(make(src, "cross_closest_year",
                    f"Grafiğe göre {a_name} ile {b_name} hangi yılda birbirine en yakındır? Cevap olarak sadece yılı yaz.",
                    min(gaps, key=lambda g: g[1])[0], EXACT, "min|A-B|"))
    out.append(make(src, "cross_furthest_year",
                    f"Grafiğe göre {a_name} ile {b_name} hangi yılda birbirinden en uzaktır? Cevap olarak sadece yılı yaz.",
                    max(gaps, key=lambda g: g[1])[0], EXACT, "max|A-B|"))

    # trend of A
    tc = detect_trend(A)
    out.append(make(src, "trend_summary",
                    f"Grafiğe göre {a_name} için genel eğilim nedir? Cevabı tek kelimeyle ver: artış, azalış veya dalgalı.",
                    None, None, f"{tc}", trend_class=tc))

    return out


def main():
    records = load(SRC)
    by_chart = {}
    for r in records:
        by_chart.setdefault(r["chart_path"], r)
    charts = list(by_chart.values())

    # pick 3 charts from distinct domains for variety
    seen_domains, picked = set(), []
    for c in charts:
        if c["domain"] not in seen_domains:
            picked.append(c)
            seen_domains.add(c["domain"])
        if len(picked) == 3:
            break

    out = []
    for src in picked:
        out.extend(build_for_chart(src))

    with OUT.open("w", encoding="utf-8") as f:
        for e in out:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    from collections import Counter
    print(f"Probe written: {OUT}")
    print(f"Questions: {len(out)}  Charts: {len(picked)}  (~{len(out)//len(picked)} per chart)")
    print(f"Domains: {[c['domain'] for c in picked]}")
    print(f"Distribution: {dict(Counter(e['question_type'] for e in out))}")


if __name__ == "__main__":
    main()
