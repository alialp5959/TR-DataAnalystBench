# Manual evaluation worksheet — real_pilot (test)

14 questions. For each one, open a **fresh** chat, paste the prompt (upload the chart image when one is referenced), then write the model's answer into `real_pilot_test_manual_template.csv` (`predicted_numeric_answer` for numbers / trend word / `veri yok`).
When done, score it:

```bash
python scripts/08_evaluate_predictions_file.py --dataset data/processed/real_pilot.jsonl --predictions data/exports/real_pilot_test_manual_template.csv --split test
```

---

## 1. `trdab_real_000095`  (chart_only · value_lookup)

```
Aşağıdaki Türkçe veri analizi sorusunu cevapla.
Cevap olarak sadece sayısal değeri yaz. Birim/yıl/açıklama yazma. Örnek: 12345
Eğer soru verilen veriden cevaplanamıyorsa (istenen yıl veya veri yoksa) cevap olarak sadece 'veri yok' yaz.

Grafik (bu görseli sohbete yükle): charts/real_pilot/chart_015_co2_line.png

Soru:
Türkiye'de 2013 yılında fosil yakıt CO2 salımı kaçtır?
```

## 2. `trdab_real_000096`  (table_and_chart · comparison)

```
Aşağıdaki Türkçe veri analizi sorusunu cevapla.
Cevap olarak sadece sayısal değeri yaz. Birim/yıl/açıklama yazma. Örnek: 12345
Eğer soru verilen veriden cevaplanamıyorsa (istenen yıl veya veri yoksa) cevap olarak sadece 'veri yok' yaz.

Tablo:
| Yıl | fosil yakıt CO2 salımı |
|---|---|
| 2009 | 76365 |
| 2010 | 80153 |
| 2011 | 87159 |
| 2012 | 88807 |
| 2013 | 87951 |
| 2014 | 93678 |

Grafik (bu görseli sohbete yükle): charts/real_pilot/chart_015_co2_line.png

Soru:
Türkiye'de 2014 yılındaki fosil yakıt CO2 salımı, 2009 yılına göre kaç bin ton karbon farklıdır?
```

## 3. `trdab_real_000097`  (table_only · average)

```
Aşağıdaki Türkçe veri analizi sorusunu cevapla.
Cevap olarak sadece sayısal değeri yaz. Birim/yıl/açıklama yazma. Örnek: 12345
Eğer soru verilen veriden cevaplanamıyorsa (istenen yıl veya veri yoksa) cevap olarak sadece 'veri yok' yaz.

Tablo:
| Yıl | fosil yakıt CO2 salımı |
|---|---|
| 2009 | 76365 |
| 2010 | 80153 |
| 2011 | 87159 |
| 2012 | 88807 |
| 2013 | 87951 |
| 2014 | 93678 |

Soru:
Türkiye'de 2009-2014 arasında fosil yakıt CO2 salımı ortalaması yaklaşık kaçtır?
```

## 4. `trdab_real_000098`  (chart_only · nth_highest)

```
Aşağıdaki Türkçe veri analizi sorusunu cevapla.
Cevap olarak sadece sayısal değeri yaz. Birim/yıl/açıklama yazma. Örnek: 12345
Eğer soru verilen veriden cevaplanamıyorsa (istenen yıl veya veri yoksa) cevap olarak sadece 'veri yok' yaz.

Grafik (bu görseli sohbete yükle): charts/real_pilot/chart_015_co2_line.png

Soru:
Türkiye'de fosil yakıt CO2 salımı açısından en yüksek 2. değer kaçtır?
```

## 5. `trdab_real_000099`  (table_and_chart · percentage_change)

```
Aşağıdaki Türkçe veri analizi sorusunu cevapla.
Cevap olarak sadece sayısal yüzde değişim değerini yaz. Artış için pozitif, azalış için negatif. Örnek: 8.8 veya -8.8
Eğer soru verilen veriden cevaplanamıyorsa (istenen yıl veya veri yoksa) cevap olarak sadece 'veri yok' yaz.

Tablo:
| Yıl | fosil yakıt CO2 salımı |
|---|---|
| 2009 | 76365 |
| 2010 | 80153 |
| 2011 | 87159 |
| 2012 | 88807 |
| 2013 | 87951 |
| 2014 | 93678 |

Grafik (bu görseli sohbete yükle): charts/real_pilot/chart_015_co2_line.png

Soru:
Türkiye'de 2009 ile 2014 arasında fosil yakıt CO2 salımı yaklaşık yüzde kaç değişmiştir? Artış için pozitif, azalış için negatif değer ver.
```

## 6. `trdab_real_000100`  (table_only · trend_summary)

```
Aşağıdaki Türkçe veri analizi sorusunu cevapla.
Cevap olarak sadece eğilimi tek kelimeyle yaz: artış, azalış veya dalgalı.
Eğer soru verilen veriden cevaplanamıyorsa (istenen yıl veya veri yoksa) cevap olarak sadece 'veri yok' yaz.

Tablo:
| Yıl | fosil yakıt CO2 salımı |
|---|---|
| 2009 | 76365 |
| 2010 | 80153 |
| 2011 | 87159 |
| 2012 | 88807 |
| 2013 | 87951 |
| 2014 | 93678 |

Soru:
Türkiye'de fosil yakıt CO2 salımı için genel eğilim nedir? Cevabı tek kelimeyle ver: artış, azalış veya dalgalı.
```

## 7. `trdab_real_000101`  (chart_only · unanswerable)

```
Aşağıdaki Türkçe veri analizi sorusunu cevapla.
Cevap olarak sadece sayısal değeri yaz. Birim/yıl/açıklama yazma. Örnek: 12345
Eğer soru verilen veriden cevaplanamıyorsa (istenen yıl veya veri yoksa) cevap olarak sadece 'veri yok' yaz.

Grafik (bu görseli sohbete yükle): charts/real_pilot/chart_015_co2_line.png

Soru:
Türkiye'de 2014 yılında orman alanı kaçtır?
```

## 8. `trdab_real_000102`  (table_and_chart · value_lookup)

```
Aşağıdaki Türkçe veri analizi sorusunu cevapla.
Cevap olarak sadece sayısal değeri yaz. Birim/yıl/açıklama yazma. Örnek: 12345
Eğer soru verilen veriden cevaplanamıyorsa (istenen yıl veya veri yoksa) cevap olarak sadece 'veri yok' yaz.

Tablo:
| Yıl | fosil yakıt CO2 salımı |
|---|---|
| 2015 | 95116 |
| 2016 | 101512 |
| 2017 | 112707 |
| 2018 | 110376 |
| 2019 | 106372 |
| 2020 | 107313 |

Grafik (bu görseli sohbete yükle): charts/real_pilot/chart_016_co2_bar.png

Soru:
Türkiye'de 2019 yılında fosil yakıt CO2 salımı kaçtır?
```

## 9. `trdab_real_000103`  (table_only · comparison)

```
Aşağıdaki Türkçe veri analizi sorusunu cevapla.
Cevap olarak sadece sayısal değeri yaz. Birim/yıl/açıklama yazma. Örnek: 12345
Eğer soru verilen veriden cevaplanamıyorsa (istenen yıl veya veri yoksa) cevap olarak sadece 'veri yok' yaz.

Tablo:
| Yıl | fosil yakıt CO2 salımı |
|---|---|
| 2015 | 95116 |
| 2016 | 101512 |
| 2017 | 112707 |
| 2018 | 110376 |
| 2019 | 106372 |
| 2020 | 107313 |

Soru:
Türkiye'de 2020 yılındaki fosil yakıt CO2 salımı, 2015 yılına göre kaç bin ton karbon farklıdır?
```

## 10. `trdab_real_000104`  (chart_only · average)

```
Aşağıdaki Türkçe veri analizi sorusunu cevapla.
Cevap olarak sadece sayısal değeri yaz. Birim/yıl/açıklama yazma. Örnek: 12345
Eğer soru verilen veriden cevaplanamıyorsa (istenen yıl veya veri yoksa) cevap olarak sadece 'veri yok' yaz.

Grafik (bu görseli sohbete yükle): charts/real_pilot/chart_016_co2_bar.png

Soru:
Türkiye'de 2015-2020 arasında fosil yakıt CO2 salımı ortalaması yaklaşık kaçtır?
```

## 11. `trdab_real_000105`  (table_and_chart · nth_highest)

```
Aşağıdaki Türkçe veri analizi sorusunu cevapla.
Cevap olarak sadece sayısal değeri yaz. Birim/yıl/açıklama yazma. Örnek: 12345
Eğer soru verilen veriden cevaplanamıyorsa (istenen yıl veya veri yoksa) cevap olarak sadece 'veri yok' yaz.

Tablo:
| Yıl | fosil yakıt CO2 salımı |
|---|---|
| 2015 | 95116 |
| 2016 | 101512 |
| 2017 | 112707 |
| 2018 | 110376 |
| 2019 | 106372 |
| 2020 | 107313 |

Grafik (bu görseli sohbete yükle): charts/real_pilot/chart_016_co2_bar.png

Soru:
Türkiye'de fosil yakıt CO2 salımı açısından en yüksek 2. değer kaçtır?
```

## 12. `trdab_real_000106`  (table_only · percentage_change)

```
Aşağıdaki Türkçe veri analizi sorusunu cevapla.
Cevap olarak sadece sayısal yüzde değişim değerini yaz. Artış için pozitif, azalış için negatif. Örnek: 8.8 veya -8.8
Eğer soru verilen veriden cevaplanamıyorsa (istenen yıl veya veri yoksa) cevap olarak sadece 'veri yok' yaz.

Tablo:
| Yıl | fosil yakıt CO2 salımı |
|---|---|
| 2015 | 95116 |
| 2016 | 101512 |
| 2017 | 112707 |
| 2018 | 110376 |
| 2019 | 106372 |
| 2020 | 107313 |

Soru:
Türkiye'de 2015 ile 2020 arasında fosil yakıt CO2 salımı yaklaşık yüzde kaç değişmiştir? Artış için pozitif, azalış için negatif değer ver.
```

## 13. `trdab_real_000107`  (chart_only · trend_summary)

```
Aşağıdaki Türkçe veri analizi sorusunu cevapla.
Cevap olarak sadece eğilimi tek kelimeyle yaz: artış, azalış veya dalgalı.
Eğer soru verilen veriden cevaplanamıyorsa (istenen yıl veya veri yoksa) cevap olarak sadece 'veri yok' yaz.

Grafik (bu görseli sohbete yükle): charts/real_pilot/chart_016_co2_bar.png

Soru:
Türkiye'de fosil yakıt CO2 salımı için genel eğilim nedir? Cevabı tek kelimeyle ver: artış, azalış veya dalgalı.
```

## 14. `trdab_real_000108`  (table_and_chart · unanswerable)

```
Aşağıdaki Türkçe veri analizi sorusunu cevapla.
Cevap olarak sadece sayısal değeri yaz. Birim/yıl/açıklama yazma. Örnek: 12345
Eğer soru verilen veriden cevaplanamıyorsa (istenen yıl veya veri yoksa) cevap olarak sadece 'veri yok' yaz.

Tablo:
| Yıl | fosil yakıt CO2 salımı |
|---|---|
| 2015 | 95116 |
| 2016 | 101512 |
| 2017 | 112707 |
| 2018 | 110376 |
| 2019 | 106372 |
| 2020 | 107313 |

Grafik (bu görseli sohbete yükle): charts/real_pilot/chart_016_co2_bar.png

Soru:
Türkiye'de 2020 yılında orman alanı kaçtır?
```
