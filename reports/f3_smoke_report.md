# F3 raporu — tam otomatik hat (soru metni → IR → sertifikalar → L4/L5)

Öğe: **10** (örnekler hariç) · L4 açık · L5 açık

## IR çıkarımı (L0/L1)

- Kabul (round-trip iki aile ≥ 9): **10/10 = 1.000**
- Reddedilme nedenleri: yok
- Tur sayısı dağılımı (1 = onarım yok): {1: 10}
- Ortalama round-trip puanı: anthropic: 9.50, meta: 9.90
- Görev türü elle yazılanla aynı: 10/10
- **Karar uyumu (çıkarılan IR vs elle IR, kabul edilenlerde): 10/10 = 1.000**

## Otomatik hattın kararları (etiketlere karşı)

| Görünüm | n | Pozitif precision | Negatif precision | Kapsama | Sayımlar |
|---|---|---|---|---|---|
| Cevap düzeyi (A+B+C) | 8 | 1.000 | 1.000 | 1.000 | tp=6 fp=0 tn=2 fn=0 unk=0 |
| Çözüm düzeyi (A+B+C+D) | 10 | 1.000 | 1.000 | 1.000 | tp=6 fp=0 tn=4 fn=0 unk=0 |

- B hücresi false rejection: n/a · D tespit: 1.000
- UNKNOWN kaynakları: yok

## L4 / L5 sinyalleri

- Bayraklar: ir_extracted: 10, l4_agree: 8, l4_disagree_certified: 2, l5_method_ok: 3, roundtrip_borderline: 6
- L4 yeniden çözücünün kendi çözümünün deterministik kararı: {'CORRECT': 10}
- L5 uygulanabilen öğe: 3; başarısız yöntem (≥2/3): 0; D hücresinde yakalanan: 0/1

## Yol (b): serbest metin → LLM yeniden yapılandırma (elle IR ile)

- Öğe: 10 · doğru karar: 10 · UNKNOWN: 0 · yanlış karar: 0
- D hücresi tespiti (yeniden yapılandırılmış adımlarla): 2/2
- Cevap çapraz kontrolü uyuşmazlığı: 0
- Nota indirgenen adımı olan öğe: 1

## Maliyet / süre

- Toplam maliyet: **$2.12** · öğe başına $0.212
- Ortalama süre/öğe: 39.3 s · toplam LLM çağrısı: 49

## Hatalı / UNKNOWN öğeler

