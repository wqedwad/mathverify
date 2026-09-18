# Değerlendirme raporu (Phase 1, deterministik katmanlar)

Toplam öğe: **260** · anahtar sızma testi: **GEÇTİ** · ortalama süre/öğe: 139 ms

## Ana metrikler

| Görünüm | n | Pozitif precision | Negatif precision | Kapsama | Sayımlar |
|---|---|---|---|---|---|
| Cevap düzeyi (A+B+C) | 221 | 1.000 | 1.000 | 1.000 | tp=143 fp=0 tn=78 fn=0 unk=0 |
| Çözüm düzeyi (A+B+C+D) | 260 | 0.993 | 1.000 | 1.000 | tp=143 fp=1 tn=116 fn=0 unk=0 |
| F1-TYT kapısı (TYT sözel+cebir) | 67 | 0.975 | 1.000 | 1.000 | tp=39 fp=1 tn=27 fn=0 unk=0 |
| F1-AYT kapısı (AYT analiz+trig+analitik) | 94 | 1.000 | 1.000 | 1.000 | tp=50 fp=0 tn=44 fn=0 unk=0 |
| F2 kapısı (TYT sentetik geometri) | 20 | 1.000 | 1.000 | 1.000 | tp=11 fp=0 tn=9 fn=0 unk=0 |
| F2 tümü (geometri+olasılık+diziler+lineer cebir) | 87 | 1.000 | 1.000 | 1.000 | tp=47 fp=0 tn=40 fn=0 unk=0 |

- **B hücresi false rejection:** 0.000 (kapsama 1.000)
- **D hücresi tespit oranı:** 0.974 · D yanlış onay: 0.026
- **Adım lokalizasyonu:** 70/117 lokalize, tam eşleşme 1.000
- **Adversaryal (çöp önek/sonek):** 0 saldırı, 0 karar değişti, saldırı başarısı n/a
- **Restructuring (yol b) sadıklığı:** 260/260 = 1.000 (cevap bulunamayan: 0)

## Hücre bazında

| Hücre | n | Pos. prec. | Neg. prec. | Kapsama | Sayımlar |
|---|---|---|---|---|---|
| A | 78 | 1.000 | n/a | 1.000 | tp=78 fp=0 tn=0 fn=0 unk=0 |
| B | 65 | 1.000 | n/a | 1.000 | tp=65 fp=0 tn=0 fn=0 unk=0 |
| C | 78 | n/a | 1.000 | 1.000 | tp=0 fp=0 tn=78 fn=0 unk=0 |
| D | 39 | 0.000 | 1.000 | 1.000 | tp=0 fp=1 tn=38 fn=0 unk=0 |

## Seviye bazında

| Seviye | n | Pos. prec. | Neg. prec. | Kapsama | Sayımlar |
|---|---|---|---|---|---|
| AYT | 114 | 1.000 | 1.000 | 1.000 | tp=61 fp=0 tn=53 fn=0 unk=0 |
| TYT | 107 | 0.984 | 1.000 | 1.000 | tp=61 fp=1 tn=45 fn=0 unk=0 |
| UNI | 39 | 1.000 | 1.000 | 1.000 | tp=21 fp=0 tn=18 fn=0 unk=0 |

## Konu bazında

| Konu | n | Pos. prec. | Neg. prec. | Kapsama | Sayımlar |
|---|---|---|---|---|---|
| analitik geometri | 22 | 1.000 | 1.000 | 1.000 | tp=11 fp=0 tn=11 fn=0 unk=0 |
| denklem | 14 | 1.000 | 1.000 | 1.000 | tp=8 fp=0 tn=6 fn=0 unk=0 |
| diziler | 20 | 1.000 | 1.000 | 1.000 | tp=11 fp=0 tn=9 fn=0 unk=0 |
| eşitsizlik | 6 | 1.000 | 1.000 | 1.000 | tp=4 fp=0 tn=2 fn=0 unk=0 |
| fonksiyonlar | 5 | 1.000 | 1.000 | 1.000 | tp=3 fp=0 tn=2 fn=0 unk=0 |
| geometri | 20 | 1.000 | 1.000 | 1.000 | tp=11 fp=0 tn=9 fn=0 unk=0 |
| integral | 21 | 1.000 | 1.000 | 1.000 | tp=10 fp=0 tn=11 fn=0 unk=0 |
| limit | 14 | 1.000 | 1.000 | 1.000 | tp=9 fp=0 tn=5 fn=0 unk=0 |
| lineer cebir | 27 | 1.000 | 1.000 | 1.000 | tp=14 fp=0 tn=13 fn=0 unk=0 |
| olasılık | 20 | 1.000 | 1.000 | 1.000 | tp=11 fp=0 tn=9 fn=0 unk=0 |
| polinom | 5 | 1.000 | 1.000 | 1.000 | tp=3 fp=0 tn=2 fn=0 unk=0 |
| problemler | 21 | 0.923 | 1.000 | 1.000 | tp=12 fp=1 tn=8 fn=0 unk=0 |
| reel analiz | 12 | 1.000 | 1.000 | 1.000 | tp=7 fp=0 tn=5 fn=0 unk=0 |
| sayılar | 16 | 1.000 | 1.000 | 1.000 | tp=9 fp=0 tn=7 fn=0 unk=0 |
| trigonometri | 21 | 1.000 | 1.000 | 1.000 | tp=10 fp=0 tn=11 fn=0 unk=0 |
| türev | 16 | 1.000 | 1.000 | 1.000 | tp=10 fp=0 tn=6 fn=0 unk=0 |

## Hatalı kararlar

- Yanlış onay (FP): ['tyt-prob-018']
- Yanlış red (FN): yok

## UNKNOWN öğeler (0)


