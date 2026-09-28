# Gerçek çözücü ölçümü (K4): `meta` ailesi

Model(ler): `muse-spark-1.3` (278) · öğe 280 · çözüm üretilen 278 · çözümsüz 2 · harcama $5.62

Doğrulama yalnız deterministik (sertifikalar, adım reddedici, füzyon; LLM katmanı yok), öğenin el yazısı IR'ıyla. Cevap etiketi kararın ardından harness'ta: SymPy çözücünün cevabını anahtara eşit (`right`) ya da farklı (`wrong`) kanıtlarsa; kanıtlayamazsa `undecided`. Çözüm düzeyinde etiket yok.

| Ölçüt | Değer |
|---|---|
| **Yanlış onay** (CORRECT, cevap yanlış) | 0 |
| Pozitif precision (cevap düzeyi) | 1.000 |
| Negatif precision (cevap düzeyi; alt sınır, aşağıya bkz.) | 0.000 |
| Kapsama (CORRECT/INCORRECT kararı) | 1.000 |
| Yanlış cevabı INCORRECT bulma oranı | n/a |
| Çözücünün cevap doğruluğu (etiketlenenlerde) | 1.000 |

## Karar × cevap etiketi

| Karar | right | wrong | undecided |
|---|---|---|---|
| CORRECT | 274 | 0 | 0 |
| INCORRECT | 4 | 0 | 0 |

## Yanlış onaylar

yok

## Doğru cevapta INCORRECT (elle okunacak)

Reddedilen adım gerçekten yanlış olabilir (doğru cevaba yanlış adımla varan çözüm INCORRECT'tir) ya da reddedici yanılıyor olabilir.

- `tyt-say-004`: ilk kötü adım 3, bayraklar ['step_refuted']
- `tyt-say-009`: ilk kötü adım 3, bayraklar ['step_refuted']
- `tyt-say-012`: ilk kötü adım 3, bayraklar ['step_refuted']
- `tyt-say-016`: ilk kötü adım 3, bayraklar ['step_refuted']

## Cevabı etiketlenemeyenler

yok

## Çözüm üretilemeyenler

- `tyt-esf-007`: llm: meta API failed after retries: connection: stream ended without usage after 0 characters
- `tyt-esf-014`: llm: meta API error HTTP 504: {"error":{"code":null,"message":"request timed out","param":null,"type":"server_error"}}

Süre: 1343 s · `--effort xhigh` · `--workers 6`
