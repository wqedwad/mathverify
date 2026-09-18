# mathverify — AI matematik çözümü doğrulama aracı (Faz 1)

Üç değerli (CORRECT / INCORRECT / UNKNOWN), **tamamen deterministik** doğrulayıcı. Girdi:
yapısal problem IR'ı + bir AI'ın (veya dış kaynağın) çözümü. Çıktı: karar, güven, ilk hatalı
adım, kanıt zinciri ve sürüm damgası (handoff §1 sözleşmesi birebir).

Handoff: `fable-handoff-matematik-dogrulama_1.md` · Kararlar: [DECISIONS.md](DECISIONS.md) ·
§6 ölçümleri: [docs/E1-E10-measurement.md](docs/E1-E10-measurement.md) · Çözücü formatı:
[docs/SOLVER_FORMAT.md](docs/SOLVER_FORMAT.md) · Son rapor: [reports/eval_report.md](reports/eval_report.md)

## Faz 1 sonuç özeti (180 öğelik §9 seti, 18 Eylül 2026)

| Metrik | Değer | Hedef |
|---|---|---|
| Pozitif precision (cevap düzeyi, A+B+C) | **1.000** | ≥ 0.98 |
| Negatif precision (cevap düzeyi) | **1.000** | ≥ 0.98 |
| Kapsama (UNKNOWN olmayan) | **1.000** | ≥ 0.85 |
| Pozitif precision (çözüm düzeyi, A+B+C+D) | 0.990 (1 FP) | — |
| F1-TYT kapısı (67 öğe) pos/neg precision | 0.975 / 1.000 | ≥ 0.98 |
| F1-AYT kapısı (94 öğe) pos/neg precision | 1.000 / 1.000 | ≥ 0.98 |
| B hücresi (kanonik olmayan doğru) false rejection | **0.000** | < 0.10 |
| D hücresi (doğru cevap, geçersiz adım) tespit | 0.963 (26/27) | ayrı raporlanır |
| İlk hatalı adım lokalizasyonu (tam eşleşme) | 1.000 (56/81 lokalize) | — |
| Adversaryal çöp önek/sonek (520 saldırı) | **0 karar değişti** | < %2 |
| Anahtar sızma testi (D2) | GEÇTİ | zorunlu |
| Yol (b) deterministik cevap çıkarma sadıklığı | 180/180 | ölçülür |
| Ortalama süre / öğe | ~0.4 s (adımlar dahil) | — |

Tek açık: `tyt-prob-018` — cevabı doğru, ara adımı **doğru ama gerekçesiz** ("iki denklemi
çıkarınca a − b = 2"). Deterministik reddedici yalnız somut karşı örnekle çürütür; bu sınıf
F4'teki kritik modelin işidir. F1-TYT kapısındaki 0.975 bu tek öğeden gelir; cevap düzeyinde 1.000.

## Kurulum ve çalıştırma

```bash
uv venv --python 3.14 .venv
uv pip install --python .venv/Scripts/python.exe -e . pytest pytest-timeout hypothesis
```

```bash
.venv/Scripts/python.exe -m pytest tests -q            # §6 E1–E10 sözleşmeleri + birim testleri (184 test; bellek sınırı testi platforma göre atlanır)
```

```bash
.venv/Scripts/python.exe evalset/build/build_all.py    # 180 öğelik seti üret (evalset/items/*.json)
```

```bash
.venv/Scripts/python.exe -m harness.run_eval           # precision/kapsama/hücre raporu -> reports/
```

```bash
.venv/Scripts/python.exe scripts/verify_cli.py --item evalset/items/tyt-prob-001.json
```

Sürümler sabittir: SymPy 1.14.0, mpmath 1.3.0, z3-solver 5.1.0, math-verify 0.9.0. Windows'ta
`PYTHONUTF8=1` ile çalıştırın.

## Mimari (Faz 1'de var olanlar)

```
problem_ir + solution  ──►  L0 normalize (parse, TR sözlük, sınıflandırıcı)
                            L1 IR (task.kind router anahtarı; gold alanı yapısal olarak yasak)
                            L3 certify/  algebra · wordproblem(z3) · domain · counting · calculus
                                         · limits · extremum · trig · geometry      [hard, primary]
                            L6 steps/    deterministik adım reddedici (yalnız çürütür)   [hard, veto]
                            mc.consistency · sanity                                     [hard, veto]
                            L8 fuse/     veto + noisy-OR + abstain eşiği (D6)
                       ──►  VerificationResult(verdict, confidence, first_bad_step, layers, trace, versions)
```

* `equiv/`: ortak karşılaştırma motoru — sembolik (yalnız pozitif kanıt) → nümerik göreli
  tolerans + hassasiyet merdiveni → alan-farkında rastgele nokta (alan IR'dan gelir, E4) →
  küme/aralık normalizasyonu; Math-Verify ikinci görüş.
* `sandbox/`: her CAS/z3 çağrısı kalıcı worker süreçte, sert timeout, bellek bekçisi,
  `PYTHONHASHSEED=0`.
* `intake/`: yol (a) yapısal yükleyici, yol (b) deterministik nihai-cevap çıkarıcı.
* `harness/`: anahtarları tutan değerlendirme koşucusu; sızma ve adversaryal testler dahil.

## §6 ölçümleri

E1–E10'un tamamı bu makinede yeniden üretildi (`scripts/probe_e1_e10.py`). Ek bulgular —
`is_subset`'in hash-tohumu bağımlılığı, Math-Verify'ın Windows'ta süreç açması, `lambdify`'ın
karmaşık sabitleri 15 basamağa düşürmesi, Gauss–Legendre'in uç tekilliklerde çökmesi, Float
örneklemenin özdeşlikleri "çürütmesi", SymPy varsayımının kısıtı yutması, görünmez karakter
enjeksiyonu — [docs/E1-E10-measurement.md](docs/E1-E10-measurement.md) içinde.

## Kapsam dışı (bilinçli) ve sonraki fazlar

* **LLM katmanı yok** (§11/1): L4 çapraz-aile yeniden çözüm, L5 metamorfik, L6 kritik +
  meta-doğrulama, L7 Lean, L0/L1 doğal dil → IR çıkarımı ve yol (b) LLM restructuring F3–F6.
  Faz 1'de IR ve yapısal çözüm doğrudan verilir; harness'teki IR'lar elle yazıldı.
* `router.DEFERRED_KINDS`: proof, synthetic_geometry, probability, series, linalg → UNKNOWN + bayrak.
* Sentetik geometri (TYT'nin en riskli bloğu) için nümerik realizasyon motoru F2.
* Kalibre Naive-Bayes ağırlıkları ve abstain eğrisi F6; şimdilik veto + noisy-OR + sabit eşik.
* Değerlendirme seti sentetiktir ve **dağıtılmaz** (§9 telif uyarısı); `provenance` zorunlu.

## Dizin

```
src/mathverify/   types · ir · solution · versions · normalize/ · sandbox/ · equiv/ · certify/ · steps/ · fuse/ · intake/ · router · verifier
tests/            test_e01..e10 (§6 sözleşmeleri) · sandbox · leakage · equiv · intake · fusion · e2e · evalset integrity
evalset/build/    konu başına öğe üreticileri (A/B elle, C adlandırılmış mutasyon, D elle)
evalset/items/    180 JSON öğe (üretilir)
harness/          loader · metrics · run_eval
docs/             SOLVER_FORMAT · E1-E10-measurement
scripts/          probe_e1_e10 · verify_cli · diag_sandbox
reports/          eval_report.md · eval_results.json (üretilir)
```
