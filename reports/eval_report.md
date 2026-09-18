# Değerlendirme raporu (Phase 1, deterministik katmanlar)

Toplam öğe: **180** · anahtar sızma testi: **GEÇTİ** · ortalama süre/öğe: 376 ms

## Ana metrikler

| Görünüm | n | Pozitif precision | Negatif precision | Kapsama | Sayımlar |
|---|---|---|---|---|---|
| Cevap düzeyi (A+B+C) | 153 | 1.000 | 1.000 | 1.000 | tp=99 fp=0 tn=54 fn=0 unk=0 |
| Çözüm düzeyi (A+B+C+D) | 180 | 0.990 | 1.000 | 1.000 | tp=99 fp=1 tn=80 fn=0 unk=0 |
| F1-TYT kapısı (TYT sözel+cebir) | 67 | 0.975 | 1.000 | 1.000 | tp=39 fp=1 tn=27 fn=0 unk=0 |
| F1-AYT kapısı (AYT analiz+trig+analitik) | 94 | 1.000 | 1.000 | 1.000 | tp=50 fp=0 tn=44 fn=0 unk=0 |

- **B hücresi false rejection:** 0.000 (kapsama 1.000)
- **D hücresi tespit oranı:** 0.963 · D yanlış onay: 0.037
- **Adım lokalizasyonu:** 56/81 lokalize, tam eşleşme 1.000
- **Adversaryal (çöp önek/sonek):** 520 saldırı, 0 karar değişti, saldırı başarısı 0.000
- **Restructuring (yol b) sadıklığı:** 180/180 = 1.000 (cevap bulunamayan: 0)

## Hücre bazında

| Hücre | n | Pos. prec. | Neg. prec. | Kapsama | Sayımlar |
|---|---|---|---|---|---|
| A | 54 | 1.000 | n/a | 1.000 | tp=54 fp=0 tn=0 fn=0 unk=0 |
| B | 45 | 1.000 | n/a | 1.000 | tp=45 fp=0 tn=0 fn=0 unk=0 |
| C | 54 | n/a | 1.000 | 1.000 | tp=0 fp=0 tn=54 fn=0 unk=0 |
| D | 27 | 0.000 | 1.000 | 1.000 | tp=0 fp=1 tn=26 fn=0 unk=0 |

## Seviye bazında

| Seviye | n | Pos. prec. | Neg. prec. | Kapsama | Sayımlar |
|---|---|---|---|---|---|
| AYT | 94 | 1.000 | 1.000 | 1.000 | tp=50 fp=0 tn=44 fn=0 unk=0 |
| TYT | 67 | 0.975 | 1.000 | 1.000 | tp=39 fp=1 tn=27 fn=0 unk=0 |
| UNI | 19 | 1.000 | 1.000 | 1.000 | tp=10 fp=0 tn=9 fn=0 unk=0 |

## Konu bazında

| Konu | n | Pos. prec. | Neg. prec. | Kapsama | Sayımlar |
|---|---|---|---|---|---|
| analitik geometri | 22 | 1.000 | 1.000 | 1.000 | tp=11 fp=0 tn=11 fn=0 unk=0 |
| denklem | 14 | 1.000 | 1.000 | 1.000 | tp=8 fp=0 tn=6 fn=0 unk=0 |
| eşitsizlik | 6 | 1.000 | 1.000 | 1.000 | tp=4 fp=0 tn=2 fn=0 unk=0 |
| fonksiyonlar | 5 | 1.000 | 1.000 | 1.000 | tp=3 fp=0 tn=2 fn=0 unk=0 |
| integral | 21 | 1.000 | 1.000 | 1.000 | tp=10 fp=0 tn=11 fn=0 unk=0 |
| limit | 14 | 1.000 | 1.000 | 1.000 | tp=9 fp=0 tn=5 fn=0 unk=0 |
| lineer cebir | 7 | 1.000 | 1.000 | 1.000 | tp=3 fp=0 tn=4 fn=0 unk=0 |
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


