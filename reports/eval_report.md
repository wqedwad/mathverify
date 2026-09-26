# Değerlendirme raporu (Phase 1, deterministik katmanlar)

Toplam öğe: **280** · anahtar sızma testi: **GEÇTİ** · ortalama süre/öğe: 158 ms

## Ana metrikler

| Görünüm | n | Pozitif precision | Negatif precision | Kapsama | Sayımlar |
|---|---|---|---|---|---|
| Cevap düzeyi (A+B+C) | 238 | 1.000 | 1.000 | 1.000 | tp=154 fp=0 tn=84 fn=0 unk=0 |
| Çözüm düzeyi (A+B+C+D) | 280 | 0.994 | 1.000 | 1.000 | tp=154 fp=1 tn=125 fn=0 unk=0 |
| F1-TYT kapısı (TYT sözel+cebir) | 87 | 0.980 | 1.000 | 1.000 | tp=50 fp=1 tn=36 fn=0 unk=0 |
| F1-AYT kapısı (AYT analiz+trig+analitik) | 94 | 1.000 | 1.000 | 1.000 | tp=50 fp=0 tn=44 fn=0 unk=0 |
| F2 kapısı (TYT sentetik geometri) | 20 | 1.000 | 1.000 | 1.000 | tp=11 fp=0 tn=9 fn=0 unk=0 |
| F2 tümü (geometri+olasılık+diziler+lineer cebir) | 87 | 1.000 | 1.000 | 1.000 | tp=47 fp=0 tn=40 fn=0 unk=0 |

- **B hücresi false rejection:** 0.000 (kapsama 1.000)
- **D hücresi tespit oranı:** 0.976 · D yanlış onay: 0.024
- **Adım lokalizasyonu:** 74/120 lokalize, tam eşleşme 1.000
- **Adversaryal (çöp önek/sonek):** 0 saldırı, 0 karar değişti, saldırı başarısı n/a
- **Restructuring (yol b) sadıklığı:** 280/280 = 1.000 (cevap bulunamayan: 0)
  - bunun 260'i yalnız **şık harfi** eşleştiği için sayıldı; matematik hiç karşılaştırılmadı
  - **cevabın kendisi karşılaştırılan öğe: 20**, sadık: 20 = 1.000
- **L5 (metamorfik) uygulanabilirlik tavanı:** 21/280 = 0.075 · D hücresinde 3/42. L5 D hücresini yakalamak için var; bu tavan model çağrısı gerektirmeden ölçülür ve bütçeyle değişmez.

## Hücre bazında

| Hücre | n | Pos. prec. | Neg. prec. | Kapsama | Sayımlar |
|---|---|---|---|---|---|
| A | 84 | 1.000 | n/a | 1.000 | tp=84 fp=0 tn=0 fn=0 unk=0 |
| B | 70 | 1.000 | n/a | 1.000 | tp=70 fp=0 tn=0 fn=0 unk=0 |
| C | 84 | n/a | 1.000 | 1.000 | tp=0 fp=0 tn=84 fn=0 unk=0 |
| D | 42 | 0.000 | 1.000 | 1.000 | tp=0 fp=1 tn=41 fn=0 unk=0 |

## Seviye bazında

| Seviye | n | Pos. prec. | Neg. prec. | Kapsama | Sayımlar |
|---|---|---|---|---|---|
| AYT | 114 | 1.000 | 1.000 | 1.000 | tp=61 fp=0 tn=53 fn=0 unk=0 |
| TYT | 127 | 0.986 | 1.000 | 1.000 | tp=72 fp=1 tn=54 fn=0 unk=0 |
| UNI | 39 | 1.000 | 1.000 | 1.000 | tp=21 fp=0 tn=18 fn=0 unk=0 |

## Konu bazında

| Konu | n | Pos. prec. | Neg. prec. | Kapsama | Sayımlar |
|---|---|---|---|---|---|
| analitik geometri | 22 | 1.000 | 1.000 | 1.000 | tp=11 fp=0 tn=11 fn=0 unk=0 |
| denklem | 19 | 1.000 | 1.000 | 1.000 | tp=11 fp=0 tn=8 fn=0 unk=0 |
| diziler | 20 | 1.000 | 1.000 | 1.000 | tp=11 fp=0 tn=9 fn=0 unk=0 |
| eşitsizlik | 6 | 1.000 | 1.000 | 1.000 | tp=4 fp=0 tn=2 fn=0 unk=0 |
| fonksiyonlar | 14 | 1.000 | 1.000 | 1.000 | tp=8 fp=0 tn=6 fn=0 unk=0 |
| geometri | 20 | 1.000 | 1.000 | 1.000 | tp=11 fp=0 tn=9 fn=0 unk=0 |
| integral | 21 | 1.000 | 1.000 | 1.000 | tp=10 fp=0 tn=11 fn=0 unk=0 |
| limit | 14 | 1.000 | 1.000 | 1.000 | tp=9 fp=0 tn=5 fn=0 unk=0 |
| lineer cebir | 27 | 1.000 | 1.000 | 1.000 | tp=14 fp=0 tn=13 fn=0 unk=0 |
| olasılık | 20 | 1.000 | 1.000 | 1.000 | tp=11 fp=0 tn=9 fn=0 unk=0 |
| polinom | 11 | 1.000 | 1.000 | 1.000 | tp=6 fp=0 tn=5 fn=0 unk=0 |
| problemler | 21 | 0.923 | 1.000 | 1.000 | tp=12 fp=1 tn=8 fn=0 unk=0 |
| reel analiz | 12 | 1.000 | 1.000 | 1.000 | tp=7 fp=0 tn=5 fn=0 unk=0 |
| sayılar | 16 | 1.000 | 1.000 | 1.000 | tp=9 fp=0 tn=7 fn=0 unk=0 |
| trigonometri | 21 | 1.000 | 1.000 | 1.000 | tp=10 fp=0 tn=11 fn=0 unk=0 |
| türev | 16 | 1.000 | 1.000 | 1.000 | tp=10 fp=0 tn=6 fn=0 unk=0 |

## Hatalı kararlar

- Yanlış onay (FP): ['tyt-prob-018']
- Yanlış red (FN): yok

## UNKNOWN öğeler (0)


