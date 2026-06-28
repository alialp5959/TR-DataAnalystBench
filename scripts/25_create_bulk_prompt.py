"""Create a single bulk prompt for fast manual evaluation of text-only tiers.

For tiers/splits whose items are all `table_only` (no images needed), this packs
every question into ONE prompt with a strict output format, so a model can be
evaluated in a single paste instead of one chat per question. Pair the pasted
response with scripts/26_score_bulk_response.py to score it automatically.

Usage:
    python scripts/25_create_bulk_prompt.py --dataset data/processed/reasoning_v01.jsonl --split test
"""

import argparse
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPORTS_DIR = PROJECT_ROOT / "data" / "exports"


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def table_md(table: dict) -> str:
    cols = table["columns"]
    lines = ["| " + " | ".join(str(c) for c in cols) + " |"]
    for row in table["rows"]:
        lines.append("| " + " | ".join(str(v) for v in row) + " |")
    return "\n".join(lines)


HEADER = """Aşağıda numaralandırılmış Türkçe veri analizi soruları var. Her birini, ilgili tabloyu ve/veya grafiği kullanarak cevapla. Grafikli sorularda ilgili GÖRSEL numarası belirtilmiştir; o görselden değerleri eksen ve gridline'lardan oku (grafiklerde sayı yazılı değildir).

ÇOK ÖNEMLİ — ÇIKTI FORMATI:
- Her soru için TEK satır dön: `numara) cevap`
- Cevap SADECE sayısal değer olsun (gerekiyorsa ondalık). Birim, yıl etiketi, açıklama YAZMA.
- Yüzde/oran sorularında artış için pozitif, azalış için negatif değer ver.
- Eğilim sorusu varsa cevap tek kelime olsun: artış, azalış veya dalgalı.
- Soru verilen veriden cevaplanamıyorsa sadece: veri yok
- Başka hiçbir şey yazma; sadece `numara) cevap` satırlarını dön.

SORULAR:
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--split", type=str, default="test")
    args = parser.parse_args()

    examples = load_jsonl(args.dataset)
    items = [e for e in examples if e.get("split") == args.split]
    if not items:
        raise SystemExit(f"No items in split '{args.split}'.")

    # Assign a stable "GÖRSEL-N" label to each unique chart referenced.
    chart_labels = {}
    for e in items:
        cp = e.get("chart_path")
        if cp and e.get("input_format") in ("chart_only", "table_and_chart") and cp not in chart_labels:
            chart_labels[cp] = f"GÖRSEL-{len(chart_labels) + 1}"

    version = items[0].get("dataset_version", args.dataset.stem)
    stem = f"{version}_{args.split}_bulk"
    prompt_path = EXPORTS_DIR / f"{stem}_prompt.txt"
    ids_path = EXPORTS_DIR / f"{stem}_ids.json"
    charts_path = EXPORTS_DIR / f"{stem}_charts.json"

    blocks = [HEADER]
    for i, e in enumerate(items, start=1):
        parts = [f"\n--- Soru {i} ---"]
        if e.get("input_format") in ("table_only", "table_and_chart"):
            parts.append(f"Tablo:\n{table_md(e['table'])}")
        if e.get("input_format") in ("chart_only", "table_and_chart"):
            parts.append(f"Görsel: {chart_labels[e['chart_path']]}")
        parts.append(f"Soru: {e['question']}")
        blocks.append("\n".join(parts))

    prompt_path.write_text("\n".join(blocks) + "\n", encoding="utf-8")
    ids_path.write_text(json.dumps([e["id"] for e in items], ensure_ascii=False), encoding="utf-8")
    # label -> chart_path, so the operator knows which images to attach
    charts_path.write_text(json.dumps({v: k for k, v in chart_labels.items()}, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Bulk prompt created.")
    print(f"Questions: {len(items)}  Charts to attach: {len(chart_labels)}")
    print(f"Prompt: {prompt_path}")
    print(f"Id order: {ids_path}")
    if chart_labels:
        print(f"Charts manifest: {charts_path}")
        for label, cp in sorted({v: k for k, v in chart_labels.items()}.items()):
            print(f"  {label} -> {cp}")


if __name__ == "__main__":
    main()
