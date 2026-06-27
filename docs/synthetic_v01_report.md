# TR-DataAnalystBench Synthetic v0.1 Report

This report summarizes the synthetic v0.1 version of TR-DataAnalystBench.

## Overview

TR-DataAnalystBench is a Turkish table and chart reasoning benchmark designed to evaluate whether language models can correctly analyze structured data.

The synthetic v0.1 dataset expands the initial 50-example pilot into a 300-example benchmark with more input formats and chart variants.

## Summary

| Metric | Value |
|---|---:|
| Total examples | 300 |
| Unique IDs | 300 |
| Unique domains | 10 |
| Unique question types | 5 |
| Unique chart images | 60 |
| Numeric-answer examples | 240 |
| Text-answer examples | 60 |

## Dataset Files

| File | Description |
|---|---|
| `data/processed/synthetic_v01.jsonl` | Main JSONL dataset |
| `data/exports/synthetic_v01_preview.csv` | Lightweight preview CSV |
| `data/exports/synthetic_v01_stats.json` | Dataset statistics |
| `data/exports/synthetic_v01_analysis.csv` | Flattened analysis CSV |
| `charts/synthetic_v01/` | Generated chart images |

## Domain Distribution

| Domain | Count |
|---|---:|
| agriculture | 30 |
| economy | 30 |
| education | 30 |
| energy | 30 |
| environment | 30 |
| health | 30 |
| municipality | 30 |
| sports | 30 |
| tourism | 30 |
| transportation | 30 |

## Input Format Distribution

| Input format | Count |
|---|---:|
| chart_only | 100 |
| table_and_chart | 100 |
| table_only | 100 |

## Chart Type Distribution

| Chart type | Count |
|---|---:|
| bar | 160 |
| line | 140 |

## Question Type Distribution

| Question type | Count |
|---|---:|
| comparison | 60 |
| max_min | 60 |
| percentage_change | 60 |
| trend_summary | 60 |
| value_lookup | 60 |

## Difficulty Distribution

| Difficulty | Count |
|---|---:|
| easy | 120 |
| medium | 180 |

## Split Distribution

| Split | Count |
|---|---:|
| test | 30 |
| train | 240 |
| validation | 30 |

## Answer Type Distribution

| Answer type | Count |
|---|---:|
| numeric | 180 |
| numeric_with_label | 60 |
| text | 60 |

## Current Task Types

The synthetic v0.1 dataset includes five task types:

1. `value_lookup`: directly reading a value from a table or chart.
2. `max_min`: identifying the maximum or minimum value and its corresponding year.
3. `comparison`: calculating the absolute difference between two selected years.
4. `percentage_change`: calculating percentage change between two selected years.
5. `trend_summary`: producing a short factual trend interpretation.

## Input Formats

The dataset includes three input formats:

1. `table_only`: the model should answer using the table.
2. `chart_only`: the model should answer using the chart image.
3. `table_and_chart`: the model can use both the table and chart.

## Quality Control

The synthetic v0.1 dataset passed the validation script:

`python scripts/05_validate_synthetic_v01.py`

The validation checks:

- Required fields
- Unique IDs
- Valid dataset version
- Valid input formats
- Valid chart types
- Valid question types
- Valid split labels
- Valid difficulty labels
- Valid answer types
- Table structure
- Chart file existence
- Numeric answer consistency
- Signed percentage-change direction consistency
- Trend class consistency (increasing / decreasing / mixed)
- Known suspicious Turkish typos
- Expected dataset size and distribution

## Scoring

All 300 examples are automatically scorable:

- 240 numeric examples (`value_lookup`, `max_min`, `comparison`, `percentage_change`) are scored with tolerance. `percentage_change` gold answers are signed, so direction is evaluated.
- 60 `trend_summary` examples are scored as a 3-class categorization (`increasing` / `decreasing` / `mixed`) via the `trend_class` field.

Use `scripts/08_evaluate_predictions_file.py` to score a prediction CSV. Running it on the generated oracle predictions yields 100% overall accuracy.

## Stats JSON

The stats file contains the following top-level keys:

`dataset_version`, `total_examples`, `unique_charts`, `domain_distribution`, `input_format_distribution`, `chart_type_distribution`, `question_type_distribution`, `difficulty_distribution`, `split_distribution`, `answer_type_distribution`

## Sample Examples

### trdab_v01_000001

| Field | Value |
|---|---|
| Domain | `transportation` |
| Input format | `table_only` |
| Chart type | `line` |
| Question type | `value_lookup` |
| Difficulty | `easy` |
| Split | `train` |
| Chart path | `charts/synthetic_v01/chart_001_line.png` |

**Question:**  
2024 yılında yolcu sayısı kaçtır?

**Gold answer:**  
2024 yılında yolcu sayısı 1.616.768 kişi olarak verilmiştir.

**Calculation:**  
2024 satırındaki değer okunur: 1616768

**Expected reasoning:**  
İlgili yıl bulunup o yıla karşılık gelen değer okunmalıdır.

**Table:**

| Yıl | yolcu sayısı |
|---|---|
| 2020 | 1199382 |
| 2021 | 1305432 |
| 2022 | 1412590 |
| 2023 | 1511623 |
| 2024 | 1616768 |

### trdab_v01_000002

| Field | Value |
|---|---|
| Domain | `transportation` |
| Input format | `chart_only` |
| Chart type | `line` |
| Question type | `max_min` |
| Difficulty | `easy` |
| Split | `train` |
| Chart path | `charts/synthetic_v01/chart_001_line.png` |

**Question:**  
Verilen verideki en düşük yolcu sayısı kaçtır?

**Gold answer:**  
En düşük yolcu sayısı 1.199.382 kişi olarak verilmiştir. Bu değer 2020 yılında görülmüştür.

**Calculation:**  
Minimum değer: 1199382, yıl: 2020

**Expected reasoning:**  
Tüm yıllardaki değerler karşılaştırılıp istenen en yüksek veya en düşük değer seçilmelidir.

**Table:**

| Yıl | yolcu sayısı |
|---|---|
| 2020 | 1199382 |
| 2021 | 1305432 |
| 2022 | 1412590 |
| 2023 | 1511623 |
| 2024 | 1616768 |

### trdab_v01_000003

| Field | Value |
|---|---|
| Domain | `transportation` |
| Input format | `table_and_chart` |
| Chart type | `line` |
| Question type | `comparison` |
| Difficulty | `medium` |
| Split | `train` |
| Chart path | `charts/synthetic_v01/chart_001_line.png` |

**Question:**  
2024 yılındaki yolcu sayısı, 2020 yılına göre kaç kişi farklıdır?

**Gold answer:**  
2024 yılındaki yolcu sayısı, 2020 yılına göre 417.386 kişi fazladır.

**Calculation:**  
|1616768 - 1199382| = 417386

**Expected reasoning:**  
İki yılın değerleri bulunup aralarındaki mutlak fark hesaplanmalıdır.

**Table:**

| Yıl | yolcu sayısı |
|---|---|
| 2020 | 1199382 |
| 2021 | 1305432 |
| 2022 | 1412590 |
| 2023 | 1511623 |
| 2024 | 1616768 |

### trdab_v01_000004

| Field | Value |
|---|---|
| Domain | `transportation` |
| Input format | `table_only` |
| Chart type | `line` |
| Question type | `percentage_change` |
| Difficulty | `medium` |
| Split | `train` |
| Chart path | `charts/synthetic_v01/chart_001_line.png` |

**Question:**  
2020 ile 2021 arasında yolcu sayısı yaklaşık yüzde kaç değişmiştir? Artış için pozitif, azalış için negatif değer ver.

**Gold answer:**  
2020 ile 2021 arasında yolcu sayısı yaklaşık %8,8 artmıştır.

**Calculation:**  
((1305432 - 1199382) / 1199382) * 100 = 8.8

**Expected reasoning:**  
Başlangıç ve bitiş yıllarındaki değerler bulunup yüzde değişim (yön dahil) hesaplanmalıdır.

**Table:**

| Yıl | yolcu sayısı |
|---|---|
| 2020 | 1199382 |
| 2021 | 1305432 |
| 2022 | 1412590 |
| 2023 | 1511623 |
| 2024 | 1616768 |

### trdab_v01_000005

| Field | Value |
|---|---|
| Domain | `transportation` |
| Input format | `chart_only` |
| Chart type | `line` |
| Question type | `trend_summary` |
| Difficulty | `medium` |
| Split | `train` |
| Chart path | `charts/synthetic_v01/chart_001_line.png` |

**Question:**  
Verilen veriye göre yolcu sayısı için genel eğilim nedir? Cevabı tek kelimeyle ver: artış, azalış veya dalgalı.

**Gold answer:**  
Verilen veri genel olarak yolcu sayısı için artış eğilimi göstermektedir. 2020 yılında 1.199.382 kişi olan değer, 2024 yılında 1.616.768 kişi seviyesine yükselmiştir.

**Calculation:**  
Başlangıç değeri: 1199382, bitiş değeri: 1616768, tespit edilen eğilim: artış eğilimi

**Expected reasoning:**  
Başlangıç, bitiş ve ara yıllardaki değişim yönleri birlikte incelenmelidir.

**Table:**

| Yıl | yolcu sayısı |
|---|---|
| 2020 | 1199382 |
| 2021 | 1305432 |
| 2022 | 1412590 |
| 2023 | 1511623 |
| 2024 | 1616768 |

### trdab_v01_000006

| Field | Value |
|---|---|
| Domain | `economy` |
| Input format | `table_and_chart` |
| Chart type | `bar` |
| Question type | `value_lookup` |
| Difficulty | `easy` |
| Split | `train` |
| Chart path | `charts/synthetic_v01/chart_002_bar.png` |

**Question:**  
2018 yılında ihracat değeri kaçtır?

**Gold answer:**  
2018 yılında ihracat değeri 211 milyon dolar olarak verilmiştir.

**Calculation:**  
2018 satırındaki değer okunur: 211

**Expected reasoning:**  
İlgili yıl bulunup o yıla karşılık gelen değer okunmalıdır.

**Table:**

| Yıl | ihracat değeri |
|---|---|
| 2018 | 211 |
| 2019 | 153 |
| 2020 | 172 |
| 2021 | 158 |
| 2022 | 179 |

### trdab_v01_000007

| Field | Value |
|---|---|
| Domain | `economy` |
| Input format | `table_only` |
| Chart type | `bar` |
| Question type | `max_min` |
| Difficulty | `easy` |
| Split | `train` |
| Chart path | `charts/synthetic_v01/chart_002_bar.png` |

**Question:**  
Verilen verideki en yüksek ihracat değeri kaçtır?

**Gold answer:**  
En yüksek ihracat değeri 211 milyon dolar olarak verilmiştir. Bu değer 2018 yılında görülmüştür.

**Calculation:**  
Maksimum değer: 211, yıl: 2018

**Expected reasoning:**  
Tüm yıllardaki değerler karşılaştırılıp istenen en yüksek veya en düşük değer seçilmelidir.

**Table:**

| Yıl | ihracat değeri |
|---|---|
| 2018 | 211 |
| 2019 | 153 |
| 2020 | 172 |
| 2021 | 158 |
| 2022 | 179 |

### trdab_v01_000008

| Field | Value |
|---|---|
| Domain | `economy` |
| Input format | `chart_only` |
| Chart type | `bar` |
| Question type | `comparison` |
| Difficulty | `medium` |
| Split | `train` |
| Chart path | `charts/synthetic_v01/chart_002_bar.png` |

**Question:**  
2018 yılındaki ihracat değeri, 2021 yılına göre kaç milyon dolar farklıdır?

**Gold answer:**  
2018 yılındaki ihracat değeri, 2021 yılına göre 53 milyon dolar fazladır.

**Calculation:**  
|211 - 158| = 53

**Expected reasoning:**  
İki yılın değerleri bulunup aralarındaki mutlak fark hesaplanmalıdır.

**Table:**

| Yıl | ihracat değeri |
|---|---|
| 2018 | 211 |
| 2019 | 153 |
| 2020 | 172 |
| 2021 | 158 |
| 2022 | 179 |

### trdab_v01_000009

| Field | Value |
|---|---|
| Domain | `economy` |
| Input format | `table_and_chart` |
| Chart type | `bar` |
| Question type | `percentage_change` |
| Difficulty | `medium` |
| Split | `train` |
| Chart path | `charts/synthetic_v01/chart_002_bar.png` |

**Question:**  
2020 ile 2022 arasında ihracat değeri yaklaşık yüzde kaç değişmiştir? Artış için pozitif, azalış için negatif değer ver.

**Gold answer:**  
2020 ile 2022 arasında ihracat değeri yaklaşık %4,1 artmıştır.

**Calculation:**  
((179 - 172) / 172) * 100 = 4.1

**Expected reasoning:**  
Başlangıç ve bitiş yıllarındaki değerler bulunup yüzde değişim (yön dahil) hesaplanmalıdır.

**Table:**

| Yıl | ihracat değeri |
|---|---|
| 2018 | 211 |
| 2019 | 153 |
| 2020 | 172 |
| 2021 | 158 |
| 2022 | 179 |

### trdab_v01_000010

| Field | Value |
|---|---|
| Domain | `economy` |
| Input format | `table_only` |
| Chart type | `bar` |
| Question type | `trend_summary` |
| Difficulty | `medium` |
| Split | `train` |
| Chart path | `charts/synthetic_v01/chart_002_bar.png` |

**Question:**  
Verilen veriye göre ihracat değeri için genel eğilim nedir? Cevabı tek kelimeyle ver: artış, azalış veya dalgalı.

**Gold answer:**  
Verilen veri ihracat değeri için dalgalı bir eğilim göstermektedir. Yıllar arasında hem artış hem de azalış görüldüğü için tek yönlü güçlü bir eğilim yoktur.

**Calculation:**  
Başlangıç değeri: 211, bitiş değeri: 179, tespit edilen eğilim: dalgalı eğilim

**Expected reasoning:**  
Başlangıç, bitiş ve ara yıllardaki değişim yönleri birlikte incelenmelidir.

**Table:**

| Yıl | ihracat değeri |
|---|---|
| 2018 | 211 |
| 2019 | 153 |
| 2020 | 172 |
| 2021 | 158 |
| 2022 | 179 |

## Notes

This is still a synthetic dataset. It is useful for validating the benchmark schema, generation pipeline, chart generation, and quality-control process.

The next major step is to move from synthetic tables to real open-data sources.

## Next Steps

1. Increase difficulty and discrimination (label-free chart variants, multi-series tables, distractor columns, harder templates).
2. Add a multimodal evaluation harness that passes chart images to a model.
3. Add baseline model evaluation and a comparison table.
4. Move from synthetic tables to real Turkish open-data sources.
5. Prepare a Hugging Face dataset release.
