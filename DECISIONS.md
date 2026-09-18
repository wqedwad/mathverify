# DECISIONS.md — kilitli kararlar ve Faz 1 uygulama kararları

Tarih: 18 Eylül 2026. Handoff: `fable-handoff-matematik-dogrulama_1.md`.

## 1. Ürün sahibi tarafından kilitlenmiş kararlar (§2) — yeniden sorulmadı

| # | Karar | Uygulamadaki karşılığı |
|---|---|---|
| D1 | Çözüm kaynağı: hem uygulamanın kendi çözücüsü hem dış çözüm | `intake/structured.py` (yol a, yapısal format `docs/SOLVER_FORMAT.md`) ve `intake/restructure.py` (yol b). Faz 1'de yol b yalnızca deterministik nihai-cevap çıkarıcıdır; sadıklığı harness'te ölçülür (`restructure_fidelity`). LLM ile yeniden yapılandırma F3'e ertelendi ve `restructure_llm` bilinçli olarak `NotImplementedError` fırlatır. |
| D2 | Doğrulayıcı anahtarı görmez | `ProblemIR` şemasında `gold_answer` alanı yoktur; `ir.py` içindeki `FORBIDDEN_KEYS` listesi (gold_answer, answer_key, expected, correct_option, cell, solution_is_correct, first_bad_step, …) IR'ın ve çözümün **her seviyesinde** özyinelemeli taranır ve `LeakageError` fırlatılır. Harness (`harness/loader.py`) etiketleri ayrı bir yapıda tutar. Sızma testi: `tests/test_ir_leakage.py` + `harness/run_eval.py` (her öğe doğru ve kasıtlı yanlış anahtarla iki kez koşar; verdict ve confidence birebir aynı olmalı). |
| D3 | Süre sınırı yok; erken çıkış yalnız kesin kararda | Faz 1'de tüm katmanlar ucuz; router'daki tüm sertifikalar koşturulur, katman atlanmaz. CAS çağrıları için 8 s sert timeout (askıya karşı, hız için değil). |
| D4 | Tamamen API, yerel GPU yok | Faz 1'de model yok. Lean (F5) için konteyner planı README'de. |
| D5 | TYT + AYT + üniversite; ispat dahil | Değerlendirme setinde TYT/AYT/UNI seviyeleri var. İspat türü (`task.kind = proof`) router'da **ertelenmiş** olarak tanımlı: doğrulayıcı `UNKNOWN` + `unsupported_task_kind` bayrağı döndürür, asla tahmin etmez. |
| D6 | Yanlış onay > yanlış red | Füzyon eşikleri: CORRECT için ≥ 0.90, INCORRECT için ≥ 0.90; `ir_incomplete`, `ir_inconsistent`, `contradiction`, `parse_error` bayrakları CORRECT'i engeller; adım reddi ve sertifika çelişkisi UNKNOWN'a iter. |

## 2. Faz 1 kapsam kararı

Handoff §0/§10: yalnızca **F0 + F1-TYT + F1-AYT**, LLM katmanı yok (§11/1). Uygulanan katmanlar: L0 (deterministik normalizasyon), L1 (yapısal IR girdisi), L3 sertifikaları, L6'nın **yalnız deterministik** kısmı (adım reddedici), L8 kural tabanlı füzyon. L2 "anahtarla eşdeğerlik" katmanı D2 gereği bağımsız bir katman olarak **yoktur**; `equiv/` her sertifikanın kullandığı ortak karşılaştırma motorudur. L4/L5/L6-kritik/L7 yok.

## 3. Ek uygulama kararları (handoff'ta açık bırakılanlar)

1. **IR'a `task` alanı eklendi.** §5'teki `unknown_of_interest` + `operators` router için yeterince belirleyici değil; `task.kind` router anahtarıdır (`router.py`), §5 alanları korunur. Faz 1 türleri: `solve_equation, solve_inequality, evaluate, simplify_expression, count_roots, count_integers, count_solutions, domain_of, limit, antiderivative, definite_integral, derivative, tangent_line, extremum (max/min/argmax/argmin/local_*), trig_solve, equation_of`.
2. **Verdict semantiği.** CORRECT = iddia edilen cevap doğru **ve** hiçbir adım reddedilmedi. INCORRECT = cevap deterministik olarak çürütüldü **veya** bir adım somut karşı örnekle reddedildi. UNKNOWN = diğer her durum. D hücresi (doğru cevap, geçersiz adım) çözüm düzeyinde *geçersiz* sayılır; harness hem cevap düzeyi (A+B+C) hem çözüm düzeyi (A+B+C+D) metriklerini ayrı raporlar.
3. **Adım reddedici yalnız çürütür.** Bir adım ancak öncülleri sağlayan, alan içinde ve iddiayı sağlamayan somut bir nokta bulununca reddedilir. Doğrulanamayan adım cezalandırılmaz ([10] şablon duyarlılığı riski yapısal olarak kapatıldı). Öncül havuzu = IR verileri + önceki tüm `eq` iddiaları (alt-atıf cezalandırılmaz) + aynı durum dalındaki `case` varsayımları. Tanımlayıcı iddialar (öncüllerin kısıtlamadığı yeni sembol içeren, özdeşlik biçiminde olmayan) atlanır. Bilinen sınır: **doğru ama gerekçesiz** adımlar (örn. `tyt-prob-018`) yakalanamaz; bu F4'teki kritik modelin işi.
4. **Füzyon = veto + noisy-OR.** Katman çıktıları ortalanmaz; bağımsız sert sertifikalar noisy-OR ile birleşir (kalibre Naive-Bayes ağırlıkları F6). Yalnız `primary=True` sertifikalar CORRECT'i temellendirebilir; `mc.consistency`, `sanity`, `steps.refute` yalnız veto edebilir.
5. **Sandbox = süreç izolasyonu, güvenlik sandbox'ı değil.** Faz 1 model üretimi kod çalıştırmaz; ifadeler beyaz-listeli tokenizer ile ayrıştırılıp SymPy ile değerlendirilir. Her CAS/z3 çağrısı kalıcı worker süreçte, sert timeout'la; timeout'ta worker öldürülüp yeniden başlatılır. Bellek sınırı: POSIX'te RLIMIT_AS, Windows'ta Job Object; ikisi de yoksa bekçi iş parçacığı (`watchdog`). gVisor/Firecracker F3'te model kodu geldiğinde şart.
6. **Determinizm.** Worker süreçlerinde `PYTHONHASHSEED=0` sabitlenir (ölçüm: `is_subset` sonucu hash tohumuna bağlı — `docs/E1-E10-measurement.md`). Rastgele nokta testleri sabit seed ile; sürümler her `VerificationResult.versions`'a yazılır.
7. **Math-Verify** ikinci görüş olarak sandbox içinde ve kendi timeout'u kapalı çağrılır (Windows'ta her çağrıda süreç açıyordu; ölçüldü).
8. **Nümerik karşılaştırma** hiçbir yerde sabit 1e-12 kullanmaz: göreli tolerans + hassasiyet merdiveni (30/50/80 basamak), Float girdilerin kendi hassasiyeti taban alınır, integral için tolerans nümerik hata kestiriminden türetilir.
9. **Değerlendirme seti tamamen sentetiktir** (`provenance: sentetik`), ÖSYM metni içermez, dağıtılmaz. 180 öğe, hücreler tam olarak %30/%25/%30/%15. C hücresi adlandırılmış mutasyonlarla (`mutation` alanı), B ve D elle yazıldı.
10. **Türkçe sayı biçimi** normalize edilir (ondalık virgül, binlik nokta). IR dizgileri kanonik (nokta ondalık, `*` açık) yazılır; derece (`°`), yüzde (`%`), unicode operatörler ön-temizlemede çevrilir.
11. **Ertelenen türler** (`router.DEFERRED_KINDS`): proof (F5), synthetic_geometry/probability/series/linalg (F2). Bu türlerde doğrulayıcı UNKNOWN döndürür ve bayrak koyar.

## 4. Kabul kapılarına karşı durum (Faz 1 sonu, 180 öğe)

`reports/eval_report.md` üretilmiş sayılardır; özet README'de. F1-TYT kapısı çözüm düzeyinde pozitif precision 0.975 (< 0.98) — tek FP, deterministik olarak çürütülemeyen "doğru ama gerekçesiz adım" sınıfındaki `tyt-prob-018`; cevap düzeyinde 1.000. Bu açık, F4 (kritik model) kapsamındadır ve gizlenmemiştir.
