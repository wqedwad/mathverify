# mathverify — AI matematik çözümü doğrulama aracı

Üç değerli (CORRECT / INCORRECT / UNKNOWN) doğrulayıcı: bir matematik sorusu ve bir AI'ın
ürettiği çözüm verildiğinde, çözümün geçerli olup olmadığına **kanıtla** karar verir, cevabı
kendisi üretip karşılaştırarak değil. Cevap anahtarı doğrulama hattına hiç girmez.

Handoff: `fable-handoff-matematik-dogrulama_1.md` · Kararlar: [DECISIONS.md](DECISIONS.md)
Mimari: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · Çözücü formatı: [docs/SOLVER_FORMAT.md](docs/SOLVER_FORMAT.md)
§6 ölçümleri: [docs/E1-E10-measurement.md](docs/E1-E10-measurement.md) · LLM katmanları: [docs/LLM_LAYERS.md](docs/LLM_LAYERS.md)
Lean kurulumu: [docs/LEAN_SETUP.md](docs/LEAN_SETUP.md) · Raporlar: [reports/](reports/)

## Durum (19 Eylül 2026)

| Faz | Durum |
|---|---|
| F0 §6 sözleşmeleri, IR, sandbox, §9 seti, iki intake yolu | **tamam** |
| F1-TYT / F1-AYT sertifikaları | **tamam** |
| F2 sentetik geometri, kombinatorik, seriler, lineer cebir | **tamam** |
| F3 LLM ön yüzü, L4 çapraz aile, L5 metamorfik | **kod tamam, ölçüm yarım** (Anthropic kredisi bitti) |
| F4 kritik + meta-doğrulama | **kod tamam, hiç koşmadı** (ölçüm hattı hazır, kredi bekliyor) |
| F5 Lean 4 + Mathlib | **tamam ve ölçüldü** (model gerektirmeyen yolla) |
| F6 adversaryal sertleştirme + kalibrasyon | **tamam ve ölçüldü** |

## Ölçülen sonuçlar

Deterministik hat, 260 öğelik değerlendirme seti ([reports/eval_report.md](reports/eval_report.md)):

| Metrik | Değer | Hedef |
|---|---|---|
| Pozitif precision (cevap düzeyi) | **1.000** | ≥ 0.98 |
| Negatif precision (cevap düzeyi) | **1.000** | ≥ 0.98 |
| Kapsama | **1.000** | ≥ 0.85 |
| Pozitif precision (çözüm düzeyi) | 0.993 (1 FP) | — |
| B hücresi yanlış red | **0.000** | < 0.10 |
| D hücresi tespit | 0.974 (38/39) | ayrı raporlanır |
| Adım lokalizasyonu (tam eşleşme) | 1.000 | — |
| Anahtar sızma testi | geçti | zorunlu |
| Ortalama süre / öğe | ~0.14 s | — |

Formal katman, modelsiz ([reports/lean_report.md](reports/lean_report.md)):

| Metrik | Değer | Hedef |
|---|---|---|
| Lean ifadesi üretilebilen öğe | 156 / 260 (%60.0) | — |
| Denetimden geçmiş formal sertifika | **107** (%41.2) | — |
| Yanlış cevaplı öğede kanıt | **0** | 0 |
| Süre / öğe | ~0.26 s | — |

Adversaryal sertleştirme ([reports/adversarial_report.md](reports/adversarial_report.md)):

| Metrik | Değer | Hedef |
|---|---|---|
| Saldırı sayısı | 6009 | — |
| **Saldırı başarısı** | **%0.000** | < %2 |
| Anlamı koruyan saldırıda karar değişimi | 0 | 0 |
| Anlamı değiştiren saldırıda yanlış onay | 0 | 0 |

F3 (tam otomatik hat) kısmi ölçümü, kredinin yettiği 64 öğede
([reports/f3_report.md](reports/f3_report.md)): IR kabul oranı 64/64, görev türü elle yazılanla
aynı 64/64, çıkarılan IR ile elle yazılan IR'ın kararı aynı 63/64, precision 1.000/1.000.
Kalan 154 öğe `Your credit balance is too low` ile düştü.

## Bilinen tek açık

`tyt-prob-018`: cevabı doğru, ara adımı **doğru ama gerekçesiz**. "İki denklemi çıkarınca
a − b = 2" deniyor; ifade doğru, gerekçe yanlış. Deterministik reddedici yalnız somut karşı
örnekle çürütür, bu adım öncüllerden çıkarılabilir olduğu için çürütülemez.

Bu açığın F4 kritiğiyle kapanacağını varsaymayın: **kod bugünkü hâliyle kapatamaz**. L6'daki
deterministik çapraz kontrol, kritiğin işaretlediği adım deterministik olarak *doğrulanmışsa*
raporu iptal ediyor. Sertifika adımın **iddiasının doğru** olduğunu kanıtlar; kritiğin şikâyeti
ise iddianın yanlışlığı değil, **öncüllerden çıkmaması**. Çapraz kontrol bu ikisini ayırmıyor,
dolayısıyla kritik doğru adımı işaretlese bile iptal ediliyor. Bu davranış
`test_a_true_but_unjustified_step_is_still_overruled_by_its_certificate` ile teste bağlandı.

Kuralı daraltmak, gerekçesiz suçlamanın sertifikayı ezmesine kapı açar; handoff'un en çok
uyardığı hata biçimi bu. Hangisinin doğru olduğu precision/recall ödünleşmesidir ve handoff
yalnız ölçümle karara bağlanmasına izin veriyor. Bu yüzden temkinli okuma varsayılan kaldı;
F4 taraması koştuğunda `reports/f3_report.md` içindeki "Sertifikanın iptal ettiği kritik
raporu" satırı kararı sayıyla verecek.

## Kurulum

```bash
uv venv --python 3.14 .venv
uv pip install --python .venv/Scripts/python.exe -e . pytest pytest-timeout hypothesis anthropic python-dotenv
```

LLM katmanları için `.env` (git tarafından yok sayılır):

```
ANTHROPIC_API_KEY=...
META_MODEL_API_KEY=...
```

Lean için [docs/LEAN_SETUP.md](docs/LEAN_SETUP.md).

## Çalıştırma

```bash
.venv/Scripts/python.exe scripts/check.py --full
```

Tek komutta bütün kapılar: testler, deterministik değerlendirme, Lean taraması, adversaryal
tarama, kalibrasyon. Kapı düşerse çıkış kodu 1.

Tek tek:

```bash
.venv/Scripts/python.exe -m pytest tests -q
```

```bash
.venv/Scripts/python.exe evalset/build/build_all.py
```

```bash
.venv/Scripts/python.exe -m harness.run_eval
```

```bash
.venv/Scripts/python.exe -m harness.run_lean --timeout 45
```

```bash
.venv/Scripts/python.exe -m harness.adversarial
```

```bash
.venv/Scripts/python.exe -m harness.run_f3 --workers 6 --pathb
```

F3 koşusu L4, L5 ve L6'yı birlikte ölçer; `--no-l4` / `--no-l5` / `--no-l6` ile tek tek
kapatılır. F4 kritiğinin sayıları raporun "L6 kritik + meta-doğrulama (F4)" bölümünde çıkar.
`--max-cost 20` verilirse toplam harcama o dolar değerine ulaştığında tarama kendini durdurur;
gözetimsiz bir koşunun bakiyeyi boşaltmasına karşı. Sağlayıcı faturalama hatası verirse koşu
zaten ilk hatada durur.

Tek bir öğeyi doğrulamak:

```bash
.venv/Scripts/python.exe scripts/verify_cli.py --item evalset/items/tyt-geo-001.json
```

`--lean` eklenirse formal katman da koşar. Model gerektirmez, yalnız yerel Lean/Mathlib ister,
ve yalnız pozitif kanıt üretir: sertifika ekleyebilir, hiçbir kararı ters çeviremez.

Sürümler sabittir: SymPy 1.14.0, mpmath 1.3.0, z3-solver 5.1.0, math-verify 0.9.0,
Lean 4.34.0 + Mathlib. Windows'ta `PYTHONUTF8=1` ile çalıştırın.

## Katmanlar

`docs/ARCHITECTURE.md` tam yetki tablosunu ve gerekçeleri içerir. Özet:

* **certify/** (13 modül) iddiayı sınar: cebir (yabancı kök guard'ı), z3 sözel problem ve
  teklik, tanım kümesi, sayım (Sturm), analiz (kırılma noktalı tanh-sinh), limit (iki yönlü),
  ekstremum (iki taraflı), trigonometri (periyoda indirgeme), analitik geometri, sentetik
  geometri (nümerik realizasyon), kombinatorik (tüketici sayım), seriler, lineer cebir.
* **steps/** adımları yalnız somut karşı örnekle çürütür — kanıtlayamadığı adımı cezalandırmaz
  ([10]: aksi hâlde kanonik olmayan doğru çözümlerde %75-85 yanlış red).
* **formal/** Lean ifadesini IR'dan deterministik şablonla üretir, önce taktik merdiveni dener,
  ve hiçbir ispatı `sorry` / aksiyom / vakumluk / kullanılmayan hipotez denetiminden geçmeden
  kabul etmez. Analiz kalemlerinde SymPy yalnız **öneriyor** (ilkel fonksiyon, ekstremum tanık
  noktası); türev ispatı ifade ağacından terim terim derleniyor ve türevin değerini Lean kendisi
  çıkarıyor. Saymalarda teorem Lean'in kendi tanımları üzerinden kuruluyor (`Equiv.Perm`,
  `powersetCard`, `↪`), bizim formülümüz üzerinden değil. Çeviremediği ya da sadakat riski
  taşıyan sınıflarda (olasılık olay yüklemleri, limitler, sentetik geometri) ifade üretmez.
* **resolve/**, **meta/**, **critic/** çapraz aile LLM sinyalleridir: kararı yalnız daha
  temkinli yapabilirler.
* **fuse/** sert veto + noisy-OR + abstain; kalibrasyon opsiyoneldir (aşağıya bakın).

## Kalibrasyon: ölçüm neden kapalı tutmayı söyledi

`harness/calibrate.py` her sinyalin (katman + verdict + bayrak) güvenilirliğini eğitim
bölmesinde ölçüp log-odds ağırlıkları üretir, eşikleri doğrulama bölmesinden seçer ve tutulan
test bölmesinde raporlar ([reports/calibration_report.md](reports/calibration_report.md)).
Ölçüm: tam sette kalibre model kapsamadan 13 öğe götürüyor (1.000 → 0.950) ve tek FP'yi
kaldırmıyor — çünkü o öğe tam olarak doğru bir öğenin sinyallerini yayıyor, hiçbir ağırlık
onu ayıramaz. Bu yüzden varsayılan **kapalı**; `MATHVERIFY_CALIBRATION=on` ile açılır.
Altyapı duruyor çünkü asıl gerekeceği yer yumuşak LLM sinyalleridir ([7]: naif ortalama
kalibre birleşimden 17.1 puan geride).

## Dizin

```
src/mathverify/   types · ir · solution · versions · normalize/ · sandbox/ · equiv/ · certify/ ·
                  steps/ · fuse/ · intake/ · llm/ · extract/ · resolve/ · meta/ · critic/ ·
                  formal/ · router · verifier · pipeline
tests/            §6 sözleşmeleri (E1–E10) · F2 · F3 (çevrimdışı, senaryolu istemci) · F5 · F6 ·
                  sandbox · sızma · equiv · intake · füzyon · uçtan uca · set bütünlüğü
evalset/build/    konu başına öğe üreticileri (A/B elle, C adlandırılmış mutasyon, D elle)
evalset/items/    260 JSON öğe (üretilir)
harness/          run_eval · run_lean · run_f3 · adversarial · calibrate · metrics · loader
docs/             ARCHITECTURE · SOLVER_FORMAT · LLM_LAYERS · LEAN_SETUP · E1-E10-measurement
scripts/          check · verify_cli · probe_e1_e10 · smoke_* · lean_* · setup_lean*
reports/          üretilmiş raporlar
```
