# mathverify — AI matematik çözümü doğrulama aracı (Faz 1 + F2)

Üç değerli (CORRECT / INCORRECT / UNKNOWN), **tamamen deterministik** doğrulayıcı. Girdi:
yapısal problem IR'ı + bir AI'ın (veya dış kaynağın) çözümü. Çıktı: karar, güven, ilk hatalı
adım, kanıt zinciri ve sürüm damgası (handoff §1 sözleşmesi birebir).

Handoff: `fable-handoff-matematik-dogrulama_1.md` · Kararlar: [DECISIONS.md](DECISIONS.md) ·
§6 ölçümleri: [docs/E1-E10-measurement.md](docs/E1-E10-measurement.md) · Çözücü formatı:
[docs/SOLVER_FORMAT.md](docs/SOLVER_FORMAT.md) · Son rapor: [reports/eval_report.md](reports/eval_report.md)

## Durum (18 Eylül 2026)

| Faz | Durum |
|---|---|
| F0 (§6 testleri, IR, sandbox, §9 seti, iki intake yolu) | **tamam** |
| F1-TYT (equiv + cebir/sözel/alan/sayım) | **tamam** — kapı: 0.975 / 1.000 (tek FP: gerekçesiz-ama-doğru adım) |
| F1-AYT (analiz/limit/ekstremum/trig + analitik) | **tamam** — kapı: 1.000 / 1.000 |
| F2 (sentetik geometri nümerik realizasyon, kombinatorik/olasılık, seriler, lineer cebir) | **tamam** — kapı: 1.000 / 1.000, kapsama 1.000 |
| F3 (çapraz-aile LLM yeniden çözüm, metamorfik, doğal dil → IR, yol b LLM restructuring) | bekliyor — iki model ailesi için API erişimi gerekir |
| F4 (adım grafiği + kritik + meta-doğrulama) | bekliyor |
| F5 (Lean 4 / Kimina + sadıklık + aksiyom denetimi) | bekliyor — Docker/Mathlib cache altyapısı gerekir |
| F6 (kalibre füzyon, adversaryal sertleştirme, distilasyon) | bekliyor |

## Ölçülen sonuç (260 öğelik §9 seti, hücreler tam olarak %30/%25/%30/%15)

| Metrik | Değer | Hedef |
|---|---|---|
| Pozitif precision (cevap düzeyi, A+B+C) | **1.000** | ≥ 0.98 |
| Negatif precision (cevap düzeyi) | **1.000** | ≥ 0.98 |
| Kapsama (UNKNOWN olmayan) | **1.000** | ≥ 0.85 |
| Pozitif precision (çözüm düzeyi, A+B+C+D) | 0.993 (1 FP) | — |
| F1-TYT kapısı (67 öğe) pos/neg precision | 0.975 / 1.000 | ≥ 0.98 |
| F1-AYT kapısı (94 öğe) pos/neg precision | 1.000 / 1.000 | ≥ 0.98 |
| F2 kapısı, TYT sentetik geometri (20 öğe) precision / kapsama | 1.000 / 1.000 | ≥ 0.98 / ≥ 0.60 |
| F2 tümü (87 öğe: geometri, olasılık, diziler, lineer cebir) | 1.000 / 1.000 | — |
| B hücresi (kanonik olmayan doğru) false rejection | **0.000** | < 0.10 |
| D hücresi (doğru cevap, geçersiz adım) tespit | 0.974 (38/39) | ayrı raporlanır |
| İlk hatalı adım lokalizasyonu (tam eşleşme) | 1.000 (70/117 lokalize) | — |
| Adversaryal çöp önek/sonek/görünmez karakter (784 saldırı) | **0 karar değişti** | < %2 |
| Anahtar sızma testi (D2) | GEÇTİ | zorunlu |
| Yol (b) deterministik cevap çıkarma sadıklığı | 260/260 | ölçülür |
| Ortalama süre / öğe | ~0.3 s (adım denetimi dahil) | — |

Tek açık: `tyt-prob-018` — cevabı doğru, ara adımı **doğru ama gerekçesiz** ("iki denklemi
çıkarınca a − b = 2"). Deterministik reddedici yalnız somut karşı örnekle çürütür; bu sınıf
F4'teki kritik modelin işidir. F1-TYT kapısındaki 0.975 bu tek öğeden gelir; cevap düzeyinde 1.000.

## Kurulum ve çalıştırma

```bash
uv venv --python 3.14 .venv
uv pip install --python .venv/Scripts/python.exe -e . pytest pytest-timeout hypothesis
```

```bash
.venv/Scripts/python.exe -m pytest tests -q            # §6 E1–E10 sözleşmeleri + F2 sözleşmeleri + birim testleri (209 test)
```

```bash
.venv/Scripts/python.exe evalset/build/build_all.py    # 260 öğelik seti üret (evalset/items/*.json)
```

```bash
.venv/Scripts/python.exe -m harness.run_eval           # precision/kapsama/hücre raporu + sızma + adversaryal -> reports/
```

```bash
.venv/Scripts/python.exe scripts/verify_cli.py --item evalset/items/tyt-geo-001.json
```

Sürümler sabittir: SymPy 1.14.0, mpmath 1.3.0, z3-solver 5.1.0, math-verify 0.9.0. Windows'ta
`PYTHONUTF8=1` ile çalıştırın.

## Mimari (var olanlar)

```
problem_ir + solution  ──►  L0 normalize (parse, TR sözlük, sınıflandırıcı)
                            L1 IR (task.kind router anahtarı; gold alanı yapısal olarak yasak)
                            L3 certify/  algebra · wordproblem(z3) · domain · counting · calculus · limits
                                         · extremum · trig · geometry (analitik)
                                         · geometry_numeric (F2) · combinatorics (F2) · series (F2) · linalg (F2)
                            L6 steps/    deterministik adım reddedici (yalnız çürütür)   [hard, veto]
                            mc.consistency · sanity                                     [hard, veto]
                            L8 fuse/     veto + noisy-OR + abstain eşiği (D6)
                       ──►  VerificationResult(verdict, confidence, first_bad_step, layers, trace, versions)
```

* `equiv/`: ortak karşılaştırma motoru — sembolik (yalnız pozitif kanıt) → nümerik göreli
  tolerans + hassasiyet merdiveni → alan-farkında rastgele nokta (alan IR'dan gelir, E4) →
  küme/aralık normalizasyonu → matris/vektör eleman bazında; Math-Verify ikinci görüş.
* `certify/geometry_numeric.py`: sentetik geometri; kısıtları sağlayan çok sayıda rastgele
  konfigürasyon Levenberg–Marquardt ile 25+ basamak hassasiyetle üretilir, hedef tüm
  konfigürasyonlarda aynıysa ve iddiaya eşitse sertifika; farklıysa IR eksik → UNKNOWN.
* `certify/combinatorics.py`: örnek uzay yapısal (permütasyon/kombinasyon/dizi/çarpım),
  olay beyaz-listeli AST ile; ≤ 3·10⁶ tüketici sayım, üstünde Monte Carlo **yalnız çürütür**.
* `certify/series.py`: rekürans iterasyonu, kapalı form (sembolik, yoksa 20 terim kesin),
  seri toplamı (sembolik + `nsum` nümerik uzlaşması).
* `certify/linalg.py`: ters (M·C = I), özvektör (M v = λ v, herhangi sıfırdan farklı kat),
  sistem (A x = b + det ≠ 0), özdeğer kümesi/çoklu kümesi, matris ifadesi.
* `sandbox/`: her CAS/z3 çağrısı kalıcı worker süreçte, sert timeout, bellek bekçisi,
  `PYTHONHASHSEED=0`.
* `intake/`: yol (a) yapısal yükleyici, yol (b) deterministik nihai-cevap çıkarıcı
  (`answer_shape` ile "(a, b)" nokta/aralık ayrımı).
* `harness/`: anahtarları tutan değerlendirme koşucusu; sızma ve adversaryal testler dahil.

## §6 ölçümleri ve ek bulgular

E1–E10'un tamamı bu makinede yeniden üretildi (`scripts/probe_e1_e10.py`). Ek bulgular —
`is_subset`'in hash-tohumu bağımlılığı, Math-Verify'ın Windows'ta süreç açması, `lambdify`'ın
karmaşık sabitleri 15 basamağa düşürmesi, Gauss–Legendre'in uç tekilliklerde çökmesi, Float
örneklemenin özdeşlikleri "çürütmesi", SymPy varsayımının kısıtı yutması, görünmez karakter
enjeksiyonu — [docs/E1-E10-measurement.md](docs/E1-E10-measurement.md) içinde.

## Kapsam dışı (bilinçli) ve sonraki fazlar

* **LLM katmanı yok** (§11/1): L4/L5/L6-kritik/L7 ve doğal dil → IR çıkarımı F3–F6'da.
  Bugün IR ve yapısal çözüm doğrudan verilir; setteki IR'lar elle yazıldı.
* `router.DEFERRED_KINDS`: proof (F5), ode, solid_geometry (3-B realizasyon) → UNKNOWN + bayrak.
  Formül tabanlı katı cisim soruları `evaluate` ile doğrulanır.
* Kalibre Naive-Bayes ağırlıkları ve abstain eğrisi F6; şimdilik veto + noisy-OR + sabit eşik.
* Değerlendirme seti sentetiktir ve **dağıtılmaz** (§9 telif uyarısı); `provenance` zorunlu.

## Dizin

```
src/mathverify/   types · ir · solution · versions · normalize/ · sandbox/ · equiv/ · certify/ · steps/ · fuse/ · intake/ · router · verifier
tests/            test_e01..e10 (§6) · test_f2_* · sandbox · leakage · equiv · intake · fusion · e2e · evalset integrity
evalset/build/    konu başına öğe üreticileri (A/B elle, C adlandırılmış mutasyon, D elle)
evalset/items/    260 JSON öğe (üretilir)
harness/          loader · metrics · run_eval
docs/             SOLVER_FORMAT · E1-E10-measurement
scripts/          probe_e1_e10 · verify_cli · smoke_f2 · diag_sandbox
reports/          eval_report.md · eval_results.json (üretilir)
```
