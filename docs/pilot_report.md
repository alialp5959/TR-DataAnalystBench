# TR-DataAnalystBench Pilot Report

This report summarizes the first pilot version of TR-DataAnalystBench.

## Overview

TR-DataAnalystBench is a Turkish table and chart reasoning benchmark designed to evaluate whether language models can correctly analyze structured data.

The pilot dataset is synthetic and is used to validate the dataset schema, generation pipeline, chart generation, and quality-control scripts before moving to real open-data sources.

## Pilot Summary

| Metric | Value |
|---|---:|
| Total examples | 50 |
| Unique domains | 10 |
| Unique question types | 5 |
| Unique chart images | 10 |
| Numeric-answer examples | 40 |
| Non-numeric summary examples | 10 |

## Question Type Distribution

| Question type | Count |
|---|---:|
| comparison | 10 |
| max_min | 10 |
| percentage_change | 10 |
| trend_summary | 10 |
| value_lookup | 10 |

## Domain Distribution

| Domain | Count |
|---|---:|
| agriculture | 5 |
| economy | 5 |
| education | 5 |
| energy | 5 |
| environment | 5 |
| health | 5 |
| municipality | 5 |
| sports | 5 |
| tourism | 5 |
| transportation | 5 |

## Split Distribution

| Split | Count |
|---|---:|
| test | 5 |
| train | 40 |
| validation | 5 |

## Difficulty Distribution

| Difficulty | Count |
|---|---:|
| easy | 20 |
| medium | 30 |

## Current Task Types

The pilot currently includes five task types:

1. `value_lookup`: directly reading a value from a table.
2. `max_min`: identifying the maximum value and its corresponding year.
3. `comparison`: calculating the difference between two years.
4. `percentage_change`: calculating percentage change between two years.
5. `trend_summary`: producing a short factual trend interpretation.

## Quality Control

The pilot dataset has passed the validation script:

`python scripts/02_validate_pilot.py`

The validation checks:

- Required fields
- Unique IDs
- Valid question types
- Valid split labels
- Valid difficulty labels
- Table structure
- Chart file existence
- Empty question/answer/calculation fields
- Suspicious known Turkish typos

## Sample Examples

### trdab_pilot_00001

**Domain:** `transportation`  
**Question type:** `value_lookup`  
**Difficulty:** `easy`  
**Split:** `train`  
**Chart:** `charts/pilot/table_001.png`

**Question:**  
2021 yılında yolcu sayısı kaçtır?

**Gold answer:**  
2021 yılında yolcu sayısı 1.283.278 kişi olarak verilmiştir.

**Calculation:**  
`2021 satırındaki değer okunur: 1283278`

**Table:**

| Yıl | Yolcu Sayısı |
|---|---|
| 2020 | 1174592 |
| 2021 | 1283278 |
| 2022 | 1436048 |
| 2023 | 1552098 |
| 2024 | 1669256 |

### trdab_pilot_00002

**Domain:** `transportation`  
**Question type:** `max_min`  
**Difficulty:** `easy`  
**Split:** `train`  
**Chart:** `charts/pilot/table_001.png`

**Question:**  
Tabloda yolcu sayısı en yüksek hangi yıldadır?

**Gold answer:**  
Yolcu sayısı en yüksek 2024 yılındadır. Bu yıldaki değer 1.669.256 kişi olarak verilmiştir.

**Calculation:**  
`Maksimum değer: 1669256, yıl: 2024`

**Table:**

| Yıl | Yolcu Sayısı |
|---|---|
| 2020 | 1174592 |
| 2021 | 1283278 |
| 2022 | 1436048 |
| 2023 | 1552098 |
| 2024 | 1669256 |

### trdab_pilot_00003

**Domain:** `transportation`  
**Question type:** `comparison`  
**Difficulty:** `medium`  
**Split:** `train`  
**Chart:** `charts/pilot/table_001.png`

**Question:**  
2024 yılındaki yolcu sayısı, 2021 yılına göre kaç kişi farklıdır?

**Gold answer:**  
2024 yılındaki yolcu sayısı, 2021 yılına göre 385.978 kişi fazladır.

**Calculation:**  
`1669256 - 1283278 = 385978`

**Table:**

| Yıl | Yolcu Sayısı |
|---|---|
| 2020 | 1174592 |
| 2021 | 1283278 |
| 2022 | 1436048 |
| 2023 | 1552098 |
| 2024 | 1669256 |

### trdab_pilot_00004

**Domain:** `transportation`  
**Question type:** `percentage_change`  
**Difficulty:** `medium`  
**Split:** `train`  
**Chart:** `charts/pilot/table_001.png`

**Question:**  
2020'den 2024'e yolcu sayısı yaklaşık yüzde kaç değişmiştir?

**Gold answer:**  
2020'den 2024'e yolcu sayısı yaklaşık %42,1 artmıştır.

**Calculation:**  
`((1669256 - 1174592) / 1174592) * 100 = 42.1`

**Table:**

| Yıl | Yolcu Sayısı |
|---|---|
| 2020 | 1174592 |
| 2021 | 1283278 |
| 2022 | 1436048 |
| 2023 | 1552098 |
| 2024 | 1669256 |

### trdab_pilot_00005

**Domain:** `transportation`  
**Question type:** `trend_summary`  
**Difficulty:** `medium`  
**Split:** `train`  
**Chart:** `charts/pilot/table_001.png`

**Question:**  
Bu tabloya göre yolcu sayısı için genel eğilim nedir?

**Gold answer:**  
Tablo genel olarak yolcu sayısı için artış eğilimi göstermektedir. 2020 yılında 1.174.592 kişi olan değer, 2024 yılında 1.669.256 kişi seviyesine çıkmıştır.

**Calculation:**  
`Başlangıç değeri: 1174592, bitiş değeri: 1669256, trend: artış eğilimi`

**Table:**

| Yıl | Yolcu Sayısı |
|---|---|
| 2020 | 1174592 |
| 2021 | 1283278 |
| 2022 | 1436048 |
| 2023 | 1552098 |
| 2024 | 1669256 |

### trdab_pilot_00006

**Domain:** `economy`  
**Question type:** `value_lookup`  
**Difficulty:** `easy`  
**Split:** `train`  
**Chart:** `charts/pilot/table_002.png`

**Question:**  
2020 yılında ihracat değeri kaçtır?

**Gold answer:**  
2020 yılında ihracat değeri 185 milyon dolar olarak verilmiştir.

**Calculation:**  
`2020 satırındaki değer okunur: 185`

**Table:**

| Yıl | Ihracat Değeri |
|---|---|
| 2020 | 185 |
| 2021 | 193 |
| 2022 | 220 |
| 2023 | 239 |
| 2024 | 254 |

### trdab_pilot_00007

**Domain:** `economy`  
**Question type:** `max_min`  
**Difficulty:** `easy`  
**Split:** `train`  
**Chart:** `charts/pilot/table_002.png`

**Question:**  
Tabloda ihracat değeri en yüksek hangi yıldadır?

**Gold answer:**  
Ihracat değeri en yüksek 2024 yılındadır. Bu yıldaki değer 254 milyon dolar olarak verilmiştir.

**Calculation:**  
`Maksimum değer: 254, yıl: 2024`

**Table:**

| Yıl | Ihracat Değeri |
|---|---|
| 2020 | 185 |
| 2021 | 193 |
| 2022 | 220 |
| 2023 | 239 |
| 2024 | 254 |

### trdab_pilot_00008

**Domain:** `economy`  
**Question type:** `comparison`  
**Difficulty:** `medium`  
**Split:** `train`  
**Chart:** `charts/pilot/table_002.png`

**Question:**  
2024 yılındaki ihracat değeri, 2021 yılına göre kaç milyon dolar farklıdır?

**Gold answer:**  
2024 yılındaki ihracat değeri, 2021 yılına göre 61 milyon dolar fazladır.

**Calculation:**  
`254 - 193 = 61`

**Table:**

| Yıl | Ihracat Değeri |
|---|---|
| 2020 | 185 |
| 2021 | 193 |
| 2022 | 220 |
| 2023 | 239 |
| 2024 | 254 |

## Next Steps

The next development steps are:

1. Improve wording quality in generated Turkish answers.
2. Add more question templates.
3. Add chart-only and table-plus-chart variants.
4. Move from synthetic pilot tables to real open-data sources.
5. Add automatic scoring for numeric answers.
6. Prepare a public Hugging Face dataset card.
