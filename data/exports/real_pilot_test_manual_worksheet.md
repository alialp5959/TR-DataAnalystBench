# Manual evaluation worksheet — real_pilot (test)

12 questions. For each one, open a **fresh** chat, paste the prompt (upload the chart image when one is referenced), then write the model's answer into `real_pilot_test_manual_template.csv` (`predicted_numeric_answer` for numbers / trend word / `veri yok`).
When done, score it:

```bash
python scripts/08_evaluate_predictions_file.py --dataset data/processed/real_pilot.jsonl --predictions data/exports/real_pilot_test_manual_template.csv --split test
```

---

## 1. `trdab_real_000049`  (table_only · value_lookup)

```
Aşağıdaki Türkçe veri analizi sorusunu cevapla.
Cevap olarak sadece sayısal değeri yaz. Birim/yıl/açıklama yazma. Örnek: 12345
Eğer soru verilen veriden cevaplanamıyorsa (istenen yıl veya veri yoksa) cevap olarak sadece 'veri yok' yaz.

Tablo:
| Yıl | enflasyon oranı |
|---|---|
| 2013 | 7.49 |
| 2014 | 8.85 |
| 2015 | 7.67 |
| 2016 | 7.78 |
| 2017 | 11.14 |
| 2018 | 16.33 |

Soru:
Türkiye'de 2017 yılında enflasyon oranı kaçtır?
```

## 2. `trdab_real_000050`  (chart_only · comparison)

```
Aşağıdaki Türkçe veri analizi sorusunu cevapla.
Cevap olarak sadece sayısal değeri yaz. Birim/yıl/açıklama yazma. Örnek: 12345
Eğer soru verilen veriden cevaplanamıyorsa (istenen yıl veya veri yoksa) cevap olarak sadece 'veri yok' yaz.

Grafik (bu görseli sohbete yükle): charts/real_pilot/chart_008_inflation_bar.png

Soru:
Türkiye'de 2018 yılındaki enflasyon oranı, 2013 yılına göre kaç yüzde farklıdır?
```

## 3. `trdab_real_000051`  (table_and_chart · average)

```
Aşağıdaki Türkçe veri analizi sorusunu cevapla.
Cevap olarak sadece sayısal değeri yaz. Birim/yıl/açıklama yazma. Örnek: 12345
Eğer soru verilen veriden cevaplanamıyorsa (istenen yıl veya veri yoksa) cevap olarak sadece 'veri yok' yaz.

Tablo:
| Yıl | enflasyon oranı |
|---|---|
| 2013 | 7.49 |
| 2014 | 8.85 |
| 2015 | 7.67 |
| 2016 | 7.78 |
| 2017 | 11.14 |
| 2018 | 16.33 |

Grafik (bu görseli sohbete yükle): charts/real_pilot/chart_008_inflation_bar.png

Soru:
Türkiye'de 2013-2018 arasında enflasyon oranı ortalaması yaklaşık kaçtır?
```

## 4. `trdab_real_000052`  (table_only · nth_highest)

```
Aşağıdaki Türkçe veri analizi sorusunu cevapla.
Cevap olarak sadece sayısal değeri yaz. Birim/yıl/açıklama yazma. Örnek: 12345
Eğer soru verilen veriden cevaplanamıyorsa (istenen yıl veya veri yoksa) cevap olarak sadece 'veri yok' yaz.

Tablo:
| Yıl | enflasyon oranı |
|---|---|
| 2013 | 7.49 |
| 2014 | 8.85 |
| 2015 | 7.67 |
| 2016 | 7.78 |
| 2017 | 11.14 |
| 2018 | 16.33 |

Soru:
Türkiye'de enflasyon oranı açısından en yüksek 2. değer kaçtır?
```

## 5. `trdab_real_000053`  (chart_only · trend_summary)

```
Aşağıdaki Türkçe veri analizi sorusunu cevapla.
Cevap olarak sadece eğilimi tek kelimeyle yaz: artış, azalış veya dalgalı.
Eğer soru verilen veriden cevaplanamıyorsa (istenen yıl veya veri yoksa) cevap olarak sadece 'veri yok' yaz.

Grafik (bu görseli sohbete yükle): charts/real_pilot/chart_008_inflation_bar.png

Soru:
Türkiye'de enflasyon oranı için genel eğilim nedir? Cevabı tek kelimeyle ver: artış, azalış veya dalgalı.
```

## 6. `trdab_real_000054`  (table_and_chart · unanswerable)

```
Aşağıdaki Türkçe veri analizi sorusunu cevapla.
Cevap olarak sadece sayısal değeri yaz. Birim/yıl/açıklama yazma. Örnek: 12345
Eğer soru verilen veriden cevaplanamıyorsa (istenen yıl veya veri yoksa) cevap olarak sadece 'veri yok' yaz.

Tablo:
| Yıl | enflasyon oranı |
|---|---|
| 2013 | 7.49 |
| 2014 | 8.85 |
| 2015 | 7.67 |
| 2016 | 7.78 |
| 2017 | 11.14 |
| 2018 | 16.33 |

Grafik (bu görseli sohbete yükle): charts/real_pilot/chart_008_inflation_bar.png

Soru:
Türkiye'de 2018 yılında cari açık kaçtır?
```

## 7. `trdab_real_000055`  (table_only · value_lookup)

```
Aşağıdaki Türkçe veri analizi sorusunu cevapla.
Cevap olarak sadece sayısal değeri yaz. Birim/yıl/açıklama yazma. Örnek: 12345
Eğer soru verilen veriden cevaplanamıyorsa (istenen yıl veya veri yoksa) cevap olarak sadece 'veri yok' yaz.

Tablo:
| Yıl | enflasyon oranı |
|---|---|
| 2019 | 15.18 |
| 2020 | 12.28 |
| 2021 | 19.6 |
| 2022 | 72.31 |
| 2023 | 53.86 |
| 2024 | 58.51 |

Soru:
Türkiye'de 2023 yılında enflasyon oranı kaçtır?
```

## 8. `trdab_real_000056`  (chart_only · comparison)

```
Aşağıdaki Türkçe veri analizi sorusunu cevapla.
Cevap olarak sadece sayısal değeri yaz. Birim/yıl/açıklama yazma. Örnek: 12345
Eğer soru verilen veriden cevaplanamıyorsa (istenen yıl veya veri yoksa) cevap olarak sadece 'veri yok' yaz.

Grafik (bu görseli sohbete yükle): charts/real_pilot/chart_009_inflation_line.png

Soru:
Türkiye'de 2024 yılındaki enflasyon oranı, 2019 yılına göre kaç yüzde farklıdır?
```

## 9. `trdab_real_000057`  (table_and_chart · average)

```
Aşağıdaki Türkçe veri analizi sorusunu cevapla.
Cevap olarak sadece sayısal değeri yaz. Birim/yıl/açıklama yazma. Örnek: 12345
Eğer soru verilen veriden cevaplanamıyorsa (istenen yıl veya veri yoksa) cevap olarak sadece 'veri yok' yaz.

Tablo:
| Yıl | enflasyon oranı |
|---|---|
| 2019 | 15.18 |
| 2020 | 12.28 |
| 2021 | 19.6 |
| 2022 | 72.31 |
| 2023 | 53.86 |
| 2024 | 58.51 |

Grafik (bu görseli sohbete yükle): charts/real_pilot/chart_009_inflation_line.png

Soru:
Türkiye'de 2019-2024 arasında enflasyon oranı ortalaması yaklaşık kaçtır?
```

## 10. `trdab_real_000058`  (table_only · nth_highest)

```
Aşağıdaki Türkçe veri analizi sorusunu cevapla.
Cevap olarak sadece sayısal değeri yaz. Birim/yıl/açıklama yazma. Örnek: 12345
Eğer soru verilen veriden cevaplanamıyorsa (istenen yıl veya veri yoksa) cevap olarak sadece 'veri yok' yaz.

Tablo:
| Yıl | enflasyon oranı |
|---|---|
| 2019 | 15.18 |
| 2020 | 12.28 |
| 2021 | 19.6 |
| 2022 | 72.31 |
| 2023 | 53.86 |
| 2024 | 58.51 |

Soru:
Türkiye'de enflasyon oranı açısından en yüksek 2. değer kaçtır?
```

## 11. `trdab_real_000059`  (chart_only · trend_summary)

```
Aşağıdaki Türkçe veri analizi sorusunu cevapla.
Cevap olarak sadece eğilimi tek kelimeyle yaz: artış, azalış veya dalgalı.
Eğer soru verilen veriden cevaplanamıyorsa (istenen yıl veya veri yoksa) cevap olarak sadece 'veri yok' yaz.

Grafik (bu görseli sohbete yükle): charts/real_pilot/chart_009_inflation_line.png

Soru:
Türkiye'de enflasyon oranı için genel eğilim nedir? Cevabı tek kelimeyle ver: artış, azalış veya dalgalı.
```

## 12. `trdab_real_000060`  (table_and_chart · unanswerable)

```
Aşağıdaki Türkçe veri analizi sorusunu cevapla.
Cevap olarak sadece sayısal değeri yaz. Birim/yıl/açıklama yazma. Örnek: 12345
Eğer soru verilen veriden cevaplanamıyorsa (istenen yıl veya veri yoksa) cevap olarak sadece 'veri yok' yaz.

Tablo:
| Yıl | enflasyon oranı |
|---|---|
| 2019 | 15.18 |
| 2020 | 12.28 |
| 2021 | 19.6 |
| 2022 | 72.31 |
| 2023 | 53.86 |
| 2024 | 58.51 |

Grafik (bu görseli sohbete yükle): charts/real_pilot/chart_009_inflation_line.png

Soru:
Türkiye'de 2024 yılında cari açık kaçtır?
```
