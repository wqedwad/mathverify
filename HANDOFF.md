# HANDOFF — mathverify

> **Son güncelleme: 23 Eylül 2026.** Bu belge, projeyi hiç görmemiş bir oturumun **yalnız bu dosyayı
> okuyarak** devralabilmesi için yazıldı. Yazılmadan önce `git status`, `git log`, `git diff`
> çalıştırıldı; adı geçen her dosya, fonksiyon ve komut depoda arandı; sayılar `reports/` altındaki
> üretilmiş raporlardan okundu; `check.py --full` bu oturumda yeniden koşturuldu (22/22 kapı,
> 406 test geçti, 1 atlandı; günlük `reports/check_full.log`).
>
> **[DOĞRULANMADI]** işareti şu demek: bilgi önceki (özetlenmiş) bir oturumdan geliyor ve bu oturumda
> yeniden ölçülemedi ya da kontrol edilemedi. İşaretsiz her şey bu oturumda kontrol edildi.

**Durum tek cümlede:** Kodda yarım kalmış bir iş yok. `scripts/check.py --full` 22/22 kapı geçiyor.
Denetimler `denetim-2026-09-20` dalında commit'li (`0f14380`) ama `master`a birleştirilmedi;
23 Eylül ikinci oturumunun işi (bellek sınırı, belge düzeltmeleri, yeni kapı) **commit edilmedi**
(§5.3). İlerlemenin önündeki engeller §12'deki kullanıcı kararları ve Anthropic kredisi; kredili
ölçümler kullanıcı kararıyla lokal iş bitince yapılacak (§7).

**İlk 10 dakika:**

1. Bu belgeyi oku: en az §3 (kararlar), §4 (işe yaramayanlar), §10 (kurallar) ve §11 (tuzaklar).
2. `git status` çalıştır. Bu belgenin yazıldığı andaki commit edilmemiş dosyalar §5.3'te
   listeli. Başka bir değişiklik görürsen, bu belgeden sonra yapılmıştır.
3. `PYTHONUTF8=1 .venv/Scripts/python.exe -m pytest tests -q` çalıştır (Git Bash; PowerShell için
   §9). Beklenen: `406 passed, 1 skipped`, yaklaşık 55 saniye.
4. §7'deki ilk işe geç.

---

## 1. Proje özeti

### Ne yapıyor

Bir matematik sorusu (Türkçe; TYT/AYT biçiminde çoktan seçmeli ya da üniversite düzeyinde açık uçlu)
ve bir AI'ın ürettiği çözüm verildiğinde, çözümün geçerli olup olmadığına **üç değerli** karar verir:
`CORRECT` / `INCORRECT` / `UNKNOWN`. Çıktı bir `VerificationResult`: verdict, güven, ilk hatalı adım,
katman sonuçları, Türkçe karar izi, sürümler ve bayraklar.

İki şey onu sıradan bir "cevabı karşılaştır" aracından ayırır:

1. **Cevap anahtarı doğrulama hattına hiç girmez.** `ProblemIR`'da cevap alanı yoktur.
   `src/mathverify/ir.py` içindeki `FORBIDDEN_KEYS` (gold_answer, answer_key, expected,
   correct_option, cell, …) IR'ın ve çözümün her seviyesinde özyinelemeli taranır; bulunursa
   `LeakageError` fırlatılır. Etiketler yalnız harness'te durur.
2. **Karar üretilerek değil, kanıtlanarak verilir.** Katmanlar çözücünün *iddiasını* sınar;
   cevabı kendileri üretip karşılaştırmazlar. Çekimser kalmak (`UNKNOWN`) bir başarısızlık değil,
   birinci sınıf bir sonuçtur.

### Kim için

Kendi AI çözücüsü olan bir matematik eğitim uygulamasının doğrulama bileşeni olarak tasarlandı.
Girdi iki yoldan gelir (karar D1): uygulamanın kendi çözücüsünün yapısal çıktısı (**yol a**,
`docs/SOLVER_FORMAT.md`) ya da dış bir serbest metin çözüm (**yol b**). Uygulamanın kendisi bu depoda
değil. Adı ne depoda ne şartnamede geçiyor (23 Eylül'de ikisi de tarandı; şartname yalnız
"uygulama soruyu bir AI'a kendisi soruyor" diyor). Adı ve ayrıntıları için kullanıcıya sorulmalı.

Özgün şartname: `C:\Users\kullanici\Downloads\fable-handoff-matematik-dogrulama_1.md` (18 Eylül 2026,
47 KB; dosya yerinde). Numaralı literatür kaynakları (`[5]`, `[10]` gibi) oradaki §13'e aittir.
Kilitli kararlar (D1–D6) oradan gelir ve **yeniden sorulmaz**.

### Temel amaç ve başarı ölçütü

Yanlış onay, yanlış redden daha pahalıdır (D6). "Çalışıyor" demenin tek geçerli kanıtı, §9
değerlendirme setinde **ölçülmüş** precision/recall değeridir. Testlerin geçmesi ya da çıktının
makul görünmesi kanıt sayılmaz.

### Tech stack

| Bileşen | Sürüm | Not |
|---|---|---|
| Python | 3.14.7 (`.venv`) | `pyproject.toml`: `requires-python >=3.12` |
| SymPy | 1.14.0 | sabit |
| mpmath | 1.3.0 | sabit |
| z3-solver | 5.1.0.0 | sabit |
| math-verify | 0.9.0 | yalnız ikinci görüş |
| latex2sympy2-extended | 1.11.0 | LaTeX dalı |
| anthropic / python-dotenv | 1.7.0 / 1.2.3 | `[llm]` ekstrası; beta API yüzeyi kullanıldığı için sabit |
| pytest (≥9), pytest-timeout, hypothesis | — | `[dev]` ekstrası |
| Lean 4 + Mathlib | v4.34.0 | WSL `Ubuntu` içinde; `reports/lean_setup.log` |
| LLM aileleri | `claude-opus-5` (anthropic), `muse-spark-1.3` (meta) | ortam değişkeniyle değiştirilebilir |

Depo yereldir: git uzak deposu, CI ve LICENSE yok. Proje tek makinede duruyor.

---

## 2. Mimari

### Katmanlar ve veri akışı

```
soru (TR) + çözüm
   │
   ├─ L0 normalize/     Türkçe sayı biçimi, derece/yüzde/unicode, beyaz listeli ifade ayrıştırma
   ├─ L1 ir / extract/  ProblemIR. Elle verilir (yol a) ya da LLM ile çıkarılır (F3):
   │                    çıkarım → deterministik doğrulama → iki aileli round-trip → ≤2 onarım
   ├─ intake/           çözüm: yapısal format (yol a) ya da serbest metin (yol b)
   ├─ verifier ön kontrolleri: şık harfinden yük doldurma + kapsam bayrakları, yük temizleyici,
   │                    "iddia bir değer mi" (_claim_not_a_value), mc.consistency, sanity
   ├─ L3 certify/       13 sertifika modülü, iddiayı sınar                   [sert, primary]
   ├─ L6 steps/         deterministik adım reddedici, yalnız karşı örnekle    [sert, veto]
   ├─ L4 resolve/       çapraz aile yeniden çözüm                             [yumuşak]
   ├─ L5 meta/          metamorfik yöntem testi                               [yumuşak]
   ├─ L6' critic/       çapraz aile kritik + meta-doğrulama                   [yumuşak]
   ├─ L7 formal/        Lean 4 + Mathlib, yalnız pozitif kanıt                [sert, primary]
   └─ L8 fuse/          sert veto + noisy-OR + çekimserlik eşikleri (+ kapalı kalibrasyon)
                        → VerificationResult
```

### Katmanların yetkisi

| Katman | Verdict üretebilir mi |
|---|---|
| `certify.*` (primary) | Evet: pass → CORRECT, fail → INCORRECT |
| `formal.lean` (L7) | Yalnız pass (sertifika ekler, hiçbir kararı ters çeviremez) |
| `steps.refute`, `mc.consistency`, `sanity` | Yalnız veto (INCORRECT) |
| `resolve` (L4), `meta` (L5) | Hayır |
| `critic` (L6') | Hayır; yalnız CORRECT'i engelleyebilir |

Kural: bir LLM katmanı kararı yalnız **daha temkinli** yapabilir. `fuse/rules.py` içindeki
`_BLOCK_POSITIVE_FLAGS` bayrakları (ör. `recovered_answer_mismatch`, `malformed_step_claim`,
`claim_is_not_a_value`) CORRECT'i engeller.

### Bileşenler nasıl bağlanıyor

- **Deterministik giriş:** `mathverify.verifier.verify(problem_ir, solution)`. Önce
  `verify_layers()` → `make_ctx()`. Sonra ön kontroller, ardından `router.route(ir)`. Bu çağrı
  `task.kind` değerini `certify.MODULES` içindeki modül adlarına eşler ve her modülün
  `verify(ir, solution, ctx)` fonksiyonu çağrılır. Adımlar varsa `steps.deterministic.check_steps`
  koşar. En son `fuse_layers()` → `fuse.rules.fuse()`.
- **Tam otomatik giriş (LLM):** `mathverify.pipeline.run_pipeline(question_tr, …)`. IR yoksa
  `extract.extract_ir` ile çıkarır. Serbest metni `extract.restructure_llm` ile yapılandırır.
  Deterministik katmanlara L4/L5/L6'yı, `use_l7=True` ise L7'yi (`formal.prove.l7_layer`) ekler ve
  hepsini birlikte füzyona verir.
- **Ortak karşılaştırma primitifi:** `equiv/`. Bütün sertifikalar iki değerin eşitliğini buradan
  sorar; bu yüzden buradaki yanlış bir "eşit" her yere sızar (§3, karar 14).
- **Her CAS/z3 çağrısı** `sandbox/pool.py` içindeki kalıcı worker süreçlerde, sert zaman aşımıyla
  koşar (varsayılan 8 s). Ağır işlemler `sandbox/ops.py` içinde tanımlıdır.
- **LLM istemcileri** `llm/__init__.py` üzerinden alınır: `ROLE_FAMILY`, `client_for_role()`,
  `judge_families()`, `set_client_override()`. Her çağrı `llm/cache.py` içindeki kayıt/tekrar
  önbelleğinden geçer (`llm_cache/`, git'te izleniyor).
- **Lean**, WSL içinde kalıcı bir REPL'dir: `formal/lean_client.py` → `lake env <repl>`.
  `formal/statement.py` IR'dan deterministik şablonla teorem üretir. `formal/prove.py` taktik
  merdivenini dener ve ispatı denetler (sorry, aksiyom, vakum, kullanılmayan hipotez).

### Klasör yapısı (önemli kısımlar)

```
src/mathverify/   63 modül, ~11 650 satır
  normalize/      parse.py (beyaz liste ayrıştırıcı, değer-yalnız ad alanı), turkish.py
  equiv/          __init__ (eşdeğerlik girişi, exact_integer), numeric, random_point, sets, symbolic
  sandbox/        pool.py (süreç havuzu, zaman aşımı, bellek sınırı), ops.py
  certify/        base.py (Ctx) + 13 modül + _z3bridge.py
  steps/          deterministic.py (reddedici)
  fuse/           rules.py
  intake/         structured.py (yol a), restructure.py (yol b, deterministik çıkarıcı)
  extract/        ir_extract, prompts, restructure_llm, roundtrip (F3)
  llm/            base (hata sınıfları), anthropic_client, meta_client, cache, schemas
  resolve/ meta/ critic/   L4 / L5 / L6'
  formal/         statement.py, prove.py, lean_client.py (L7)
  ir.py solution.py types.py router.py verifier.py pipeline.py versions.py
tests/            28 test dosyası + conftest.py + conftest_llm.py (ScriptedClient), 407 test
evalset/build/    17 modül: build_all.py, common.py ve 15 konu üreticisi
evalset/items/    280 JSON öğe (üretilmiş, commit'li)
harness/          run_eval, run_lean, adversarial, soundness_fuzz, calibrate, run_f3, metrics, loader
scripts/          check.py (kapı koşucusu), verify_cli.py, Lean kurulum betikleri, smoke/probe betikleri
docs/             ARCHITECTURE, QUALITY, SOLVER_FORMAT, LLM_LAYERS, LEAN_SETUP, E1-E10-measurement
reports/          üretilmiş .md raporlar (commit'li); *.json raporlar git-ignore'lu
```

### Değerlendirme seti

280 öğe. Hücre oranları A/B/C/D = %30/%25/%30/%15:

| Hücre | Anlamı |
|---|---|
| A | Kanonik doğru çözüm |
| B | Doğru ama kanonik olmayan çözüm |
| C | Yanlış cevap (adlandırılmış mutasyonla üretilir) |
| D | Doğru cevap ama bozuk adım |

Tamamen sentetiktir, ÖSYM metni içermez. Cevap düzeyi metrikleri A+B+C üzerinden, çözüm düzeyi
metrikleri A+B+C+D üzerinden ayrı raporlanır.

---

## 3. Alınan kararlar ve gerekçeleri

Ayrıntılı kayıt `DECISIONS.md` içinde (bölüm sırası 1, 2, 3, 6, 4, 5; madde numaraları 1–30).
Burada her kararın **neden** alındığı ve **hangi alternatifin neden reddedildiği** özetleniyor.

### Kilitli ürün kararları (şartname §2, yeniden sorulmaz)

- **D1:** Hem uygulamanın kendi çözücüsü hem dış çözüm desteklenir.
- **D2:** Doğrulayıcı cevap anahtarını görmez.
- **D3:** Süre sınırı yok. Erken çıkış yalnız kesin kararda yapılır; 8 s zaman aşımı yalnız askıda
  kalmaya karşıdır, hız için değil.
- **D4:** Her şey API üzerinden çalışır, yerel GPU yok.
- **D5:** TYT + AYT + üniversite, ispat dahil. İspat türü ertelendi: `UNKNOWN` + `unsupported_task_kind`.
- **D6:** Yanlış onay, yanlış redden daha kötüdür. CORRECT ve INCORRECT için füzyon eşiği ≥ 0.90.

### Mimari ve doğrulama kararları

1. **Cevap anahtarı yalıtımı yapısaldır** (şemada alan yok + özyinelemeli tarama).
   *Reddedilen:* anahtarı "karşılaştırma için" hatta tutmak. Doğrulayıcıyı anahtar
   eşleştiricisine çevirirdi. *Sızma testi:* her öğe doğru ve kasıtlı yanlış anahtarla iki kez
   koşar; verdict ve güven birebir aynı olmalı. Mutasyon öğenin kendisine, harness
   ayrıştırmasından **önce** uygulanır (§4'e bakın: eski test yerel bir değişkeni değiştiriyordu).

2. **Adım reddedici yalnız somut karşı örnekle çürütür** (DECISIONS §3.3). Doğrulanamayan adım
   cezalandırılmaz. *Neden:* literatür [10], LLM adım doğrulayıcılarının kanonik olmayan doğru
   adımlarda %75–85 yanlış red verdiğini ölçüyor. Bu projede aynı dönüşümlerde ölçülen yanlış
   red 0/184. *Reddedilen:* LLM'i adım yargıcı yapmak ya da "kanıtlanamayanı şüpheli say" kuralı.

3. **Çözücünün kendi sembolüyle yazdığı adım atlanır** (DECISIONS §3.3, 23 Eylül'de
   kesinleştirildi). Örnek: `t² = 4t − 3`, `u = u² − 6`. *Neden:* bir özdeşlik mi, çözülmekte olan
   bir denklem mi olduğu belirsiz. *Reddedilen:* bunları özdeşlik sayıp sınamak; çözülen her
   denklemi "çürütür" ve geçerli çözümleri cezalandırırdı. *Bedel:* bozulmuş adım taramasında
   kaçan 6 adımın 5'i bu sınıftan.

4. **Bozuk adım iddiası atlanmaz, çekimser kalınır** (DECISIONS §25). `u = sqrt(x+4)` iyi biçimli
   matematiktir: `UndeclaredSymbolError`, cezasız atlanır. `a = 20}` matematik değildir:
   `malformed_step_claim` bayrağı CORRECT'i engeller. Ayrım ayrıştırmayla yapılır: bilinmeyen adlar
   `Symbol` (çağrılıyorsa `Function`) kabul edilip metin yeniden ayrıştırılır. *Reddedilen:* her
   ayrıştırılamayanı atlamak. Reddedilmiş bir adıma `}` eklemek INCORRECT'i CORRECT'e çeviriyordu
   (54 saldırı/öğe çifti).

5. **LLM sinyali sert sertifikayı ters çeviremez**, yalnız CORRECT'i engelleyebilir.
   *Reddedilen:* katman çıktılarının ortalaması. Füzyon sert veto + noisy-OR biçimindedir
   (DECISIONS §3.4); yalnız `primary=True` sertifikalar CORRECT'i temellendirir.

6. **İki model ailesi ve zorunlu rol ayrımı** (DECISIONS §17). Bir çözümü üreten aile o çözümü
   yargılayamaz. L4, kritik ve Lean ispatı çözücünün karşıt ailesinden; meta-doğrulayıcı kritiğin
   karşıt ailesinden gelir. `run_f3 --solver-family` verilmezse her kayda
   `solver_family_unknown` bayrağı konur. *Reddedilen:* tek aile. Aynı model kendi hatasını
   görmüyor ([6]).

7. **IR çıkarımı kabul edilmeden kullanılmaz** (DECISIONS §19). Sıra: şema ve ayrıştırma
   doğrulaması → iki aileli round-trip (ikisi de ≥ 9/10) → en fazla 2 onarım turu. Kabul
   edilmezse `UNKNOWN` döner. *Reddedilen:* "en iyi tahmin" IR'ı ile devam etmek.

8. **Lean ifadesi modele yazdırılmaz, IR'dan şablonla üretilir** (DECISIONS §20). *Neden:* [5]'e
   göre otomatik formalizasyonda ifadelerin %89,5'i derleniyor ama yalnız %60,5'i sadık. Yazıcı
   çeviremediği bir şeyi tahmin etmez, `LeanPrintError` fırlatır ve L7 çalışmaz. Modelin tek işi
   ispattır; ispat da `sorry`, aksiyom, vakum ve kullanılmayan hipotez denetimlerinden geçmeden
   kabul edilmez. Tautoloji olan ifadeler `is_trivial` ile reddedilir.

9. **Üreten hesap ile kontrol eden hesap ayrıdır.** SymPy bir ilkel fonksiyon ya da tanık nokta
   *önerebilir*; öneri teoremin ifadesine asla girmez, yalnız taktiğe girer. Yanlış bir öneri
   ispatı düşürür, sertifika üretemez. Türev ispatı ifade ağacından terim terim derlenir
   (`_hasderiv_proof`) ve türevin değerini Lean kendisi çıkarır.

10. **Türev, ilkel ve integral `HasDerivAt` üzerinden kurulur.** *Reddedilen:* `deriv f a = v`.
    Fonksiyon türevlenebilir değilken de doğru çıkar ve yanlış gerekçeyle sertifika üretirdi.

11. **Sayma teoremleri Lean'in kendi tanımlarıyla kurulur**: `Fintype.card (Equiv.Perm (Fin n))`,
    `powersetCard`, `Fin k ↪ Fin n`. *Reddedilen:* `Nat.factorial 5 = 120`. Bu yalnız bizim formül
    seçimimizi onaylar, sayılan nesneyi doğrulamaz.

12. **Lean'in junk değerleri sertifika üretemez** (DECISIONS §26). Mathlib'de `x/0 = 0`,
    `Real.sqrt` negatifte 0, `Real.log 0 = 0`, `Real.tan (π/2) = 0` ve integrallenemeyen fonksiyonun
    integrali 0'dır. Kural `formal/statement.py` içindeki "junk values" bölümünde:
    - Kapalı (değişkensiz) kısmi işlemi yazıcı karara bağlar (`_check_closed_definedness`).
      Tanımsızsa ya da karar verilemezse ifade üretilmez.
    - Açık kısmi işlemleri şablon ele alır. Seçenekler: `evaluate`'te koruma hipotezi
      (`open_guards`), bölgenin tamamında tanımlılık kanıtı (`defined_on`), noktada türevde iç nokta
      (`interior_defined_at`), fonksiyonel türevde boş olmayan tanım kümesi
      (`has_interior_point`), ya da ret.
    - Tanımlılık `certify.domain.definedness_conditions`'tan gelir, yani deterministik katmanla
      aynı tanım kullanılır.

    *Reddedilen:* junk değerleri yalnız denetimlere bırakmak. Aksiyom ve vakum denetimleri bunu
    göremez, çünkü ispatlar junk ifadelerin gerçek ispatlarıdır.

13. **İddia bir değerdir, hesaplama değil** (DECISIONS §28). İddia, `normalize.parse.COMPUTING_OPERATORS`
    (integrate, limit, diff, Sum, simplify, nsimplify, det, dist, …) ve problemin kendi
    fonksiyonları çıkarılmış bir ad alanında okunur (`claim_namespace`, `check_claim_is_value`,
    `Ctx.claim_ns`). `evaluate` görevinde hedefi aynen yazan iddia da cevap sayılmaz
    (`verifier._same_structure`). Karar **çekimserliktir** (`claim_is_not_a_value`), ret değil:
    ortada yanlış bir cevap değil, hiç cevap yok. Kapalı biçimler (`binomial(6, 3)`) geçerlidir.

14. **Sayısal "eşit" kanıt değildir** (DECISIONS §27). Kurallar:
    - Kesin kesirler kesin karşılaştırılır.
    - Tolerans verilmemişse eşitlik hassasiyet merdiveninin (30/50/80 basamak) **her**
      basamağında sağlanmalıdır.
    - Sembolik sıfır testi (`sandbox.ops.zero_test_battery`) yalnız kesin dönüşümlerden oluşur;
      `nsimplify` bir yuvarlamadır.
    - Rastgele noktalarda iki taraf ayrı ayrı değerlendirilip çıkarılmaz; farkın kendisi
      uyarlamalı `evalf` ile değerlendirilir (`equiv.random_point._definite_nonzero_difference`).
    - Math-Verify yalnız ikinci görüştür; tek başına karar verdiği dal kaldırıldı.

    *Neden:* sembolik eşitlik yanlış negatif verebilir ama yanlış pozitif vermez; nümerik
    eşitlikte durum tersidir (TinyV).

15. **İddia karşılaştırılmadan önce yeniden yazılmaz** (DECISIONS §29). Sayılar
    `equiv.exact_integer` ile okunur: tam sayı değilse yanlış bir sayımdır, yuvarlanmaz.
    Hiçbir iddia ya da hesaplanan doğru değer `nsimplify`'dan geçmez. *Reddedilen:* `int()` ve
    "güzel sayıya yakalama".

16. **Kararın kapsamı çıktıya yazılır** (DECISIONS §24). Denetlenebilir adım yoksa verdict korunur
    ama `answer_level_only`, `steps_not_checked` ya da `answer_from_option_letter` bayrağı konur ve
    karar izine `KAPSAM:` satırı eklenir. *Reddedilen:* çekimser kalmak. Yol (b)'nin cevap düzeyi
    kapsamasını yok ederdi.

17. **Yol (b)'de yük kurtarma yalnız küme/aralık literalleri içindir**
    (`payload_source="recovered_text"`). Tavsiye niteliğindedir: şıkla çelişirse
    `recovered_answer_mismatch` ile çekimser kalınır, asla reddedilmez. *Reddedilen:* her
    `<sym> = <token>` biçimini kurtarmak (ölçüm §4'te).

18. **Temizleyici matematiği asla atmaz** (DECISIONS §21). Ayrıştırılamayan yükte yalnız düz yazı
    parçaları atılır. *Reddedilen:* sondaki parçaları kırpmak; `12 + 1` ifadesini `12`ye
    indiriyordu.

19. **Faturalama hatası bir ölçüm değildir** (DECISIONS §23). `LLMCreditError` ve `LLMAuthError`,
    `LLMFatalError` altındadır ve bilerek `LLMError`'ın alt sınıfı **değildir**. Harness yapısal
    `fatal` alanıyla ilk hatada durur. *Reddedilen:* hata metninde "credit" dizgisini aramak
    (§4'e bakın).

20. **Kalibrasyon ölçüldü ve varsayılan olarak kapalı** (DECISIONS §22). Kalibre model kapsamadan
    13 öğe götürdü (1.000 → 0.950) ve tek FP'yi kaldırmadı. Açmak için
    `MATHVERIFY_CALIBRATION=on`; `reports/calibration.json` yoksa `CalibrationUnavailable`
    fırlatılır. Altyapı yumuşak LLM sinyalleri için duruyor.

21. **`tyt-prob-018` açık bırakıldı.** Doğru ama gerekçesiz bir adımı deterministik reddedici
    çürütemez. L6 çapraz kontrolü, sertifikayla doğrulanmış bir adım hakkındaki kritik raporunu
    iptal ediyor. *Reddedilen:* kuralı daraltmak; gerekçesiz bir LLM suçlamasının sertifikayı
    ezmesine kapı açar. Karar F4 ölçümüne bırakıldı. Bugünkü davranış
    `test_a_true_but_unjustified_step_is_still_overruled_by_its_certificate` ile teste bağlı.

22. **Bilerek kapsam dışı (Lean):**
    - Olasılık olay yüklemleri: `Fin 6` ile bir birim kayması teoremi sessizce değiştirir.
    - Limitler: her biçim ayrı bir Mathlib kalıbı ister ve yarısı "limit yoktur"un
      olumsuzlamasını gerektirir.
    - Sentetik geometri.
    - Parçalı ve has olmayan integraller.
    - `domain_of`, `simplify_expression`, `count_solutions`.

23. **Sandbox süreç izolasyonudur, güvenlik sandbox'ı değildir** (DECISIONS §3.5). Model kod
    çalıştırmadığı için yeterli. Model kodu gelirse gVisor/Firecracker şart. Bellek sınırı
    Windows'ta Job Object ile uygulanır ve Windows'ta **atlanamayan bir teste** bağlıdır
    (23 Eylül'e kadar hiç uygulanmıyordu, §6.4).

24. **Determinizm:**
    - Worker'larda `PYTHONHASHSEED=0` (`is_subset` hash tohumuna bağlı değişiyordu).
    - Rastgele noktalarda sabit tohum ve kesin rasyonel örnekleme.
    - LLM için kayıt/tekrar önbelleği (`MATHVERIFY_LLM_CACHE=replay` ağa hiç çıkmaz).
    - Sürümler her sonuca yazılır.

25. **Nümerik integral yalnız tanh-sinh ile yapılır**; tolerans hata kestiriminden türetilir.
    *Reddedilen:* Gauss–Legendre (`∫₀¹ ln x/√x` üzerinde dps 80'de mutlak hata 2.0e-2, göreli
    5e-3; 23 Eylül'de yeniden ölçüldü, eski belgelerdeki "5e-3 hata" göreli hatadır) ve sabit
    1e-12 tolerans.

26. **Doğrulayıcının kendisi metamorfik ve diferansiyel olarak test edilir** (DECISIONS §30,
    `harness/soundness_fuzz.py`). Değerlendirme seti bir sabittir; bu tarama problemin
    üretebileceği cevaplar üzerinde ölçer. Dört sayının sıfır olması `check.py --full` kapısıdır.

27. **Router'da tanımlı her görev türünün sette öğesi olması bir kapıdır.** 20 Eylül'de üç türün
    hiç öğesi yoktu; `evalset/build/tyt_kapsam.py` ile 20 öğe eklendi ve oranlar korundu.

28. **Adversaryal tarama üç yüzeyi ayrı ölçer** (cevap yükü, şık harfi korunarak, adım
    iddiaları) ve üçünün de var olması bir kapıdır. *Neden:* eski tarama tek yüzeydeydi ve her
    saldırıda şık harfini siliyordu, ama çözümlerin çoğu harf taşıyor. Tek yüzeyde %0 başarı,
    ölçülenin dar olduğunu gizler.

29. **`.gitignore` içinde `/build/` ve `/dist/` köke ankrajlı.** *Neden:* ankrajsız `build/`,
    `evalset/build/` klasörünü de yok sayıyordu ve set üreticileri hiç commit edilmemişti.

---

## 4. Denenen ve işe yaramayanlar

Bunlar **tekrar denenmemeli.** Her birinin neden başarısız olduğu yanında yazıyor.

> Aşağıdaki "önce" ölçümleri hataların bulunduğu anki koşulardan geliyor. Çoğu `DECISIONS.md` ve
> `docs/ARCHITECTURE.md` içinde kayıtlı; üçü başka yerde: 94/59 kurtarma ölçümü
> `src/mathverify/intake/restructure.py` yorumunda, Gauss–Legendre `docs/E1-E10-measurement.md`
> içinde, 8/3 kâhin hatası `harness/soundness_fuzz.py` yorumunda.
>
> 23 Eylül'de kütüphane ya da matematik gerçeği olanlar kod geri alınmadan yeniden üretildi ve
> tuttu: `int(7/2) = 3`; `nsimplify` 500000003/3000000000'ı 1/6'ya, −e⁻¹⁰⁰⁰'ü 0'a götürüyor;
> 10³⁰+1 ile 10³⁰'un göreli farkı 1e-30; e^{π√163} 30 basamakta tam sayıya eşit, 50 ve 80'de
> değil; 8/3'ün 30 basamaklı ondalığı 8/3 değil; F3'te 151 kayıt aynı faturalama hatasıyla düşmüş
> ve kırpılmış metin `'message': 'Your` ile bitiyor. "Yerine" sütunundaki mekanizmalar kodda
> duruyor. Kodu geri almadan üretilemeyenler (7/7 iddia, 54 çift, `Bilmiyorum` 0.990, 13 öğe,
> junk 0.995, 245/260, `}` saldırısı) yalnız kayıttan geliyor **[DOĞRULANMADI]**.

### Doğrulama mantığı

| Denenen | Neden başarısız oldu | Yerine |
|---|---|---|
| Sayma iddiasını `int()` ile okumak | `7/2` → 3 → sayısı 3 olan soruda CORRECT | `equiv.exact_integer` |
| İddiayı/doğruyu `nsimplify` ile "güzelleştirmek" | `500000003/3000000000` → 1/6; `−e⁻¹⁰⁰⁰` → 0 | Kesin dönüşümler; `nsimplify` yok |
| Kesin sayıları göreli toleransla karşılaştırmak | `10³⁰+1 == 10³⁰` çıkıyordu | Kesin rasyonel karşılaştırma |
| Nümerik eşitliği tek hassasiyet basamağında kabul etmek | `e^{π√163}` 30 basamakta tam sayıya "eşit" | Her basamakta eşitlik |
| Rastgele noktada iki tarafı ayrı değerlendirip çıkarmak | Çalışma hassasiyetinin altındaki farkı görmüyor | Farkın kendisini uyarlamalı `evalf` ile değerlendirmek |
| Math-Verify'ın tek başına karar vermesi | Belge "ikinci görüş" diyordu, kod karar veriyordu | Yalnız nota yazılıyor |
| İddiayı tam ad alanında okumak | `integrate(log(x), x)`, `f(g(2))`, `gcd(84,120)`: 7 iddianın 7'si CORRECT | Değer-yalnız ad alanı |
| Kayan noktalı örnekleme ile adım çürütmek | Doğru özdeşlikleri "çürütüyordu" | Kesin rasyonel örnekleme |
| `evaluate=True` ile ilişki kurmak | Pozitif sembolde `x > 0` True'ya katlanıyordu | `evaluate=False` ilişkiler + z3'te yan kısıt |
| Her ayrıştırılamayan adımı cezasız atlamak | `}` eklemek reddi iptal ediyordu | `malformed_step_claim` ayrımı |
| Yol (b)'de her `<sym> = <token>` biçimini kurtarmak | 94 kurtarmanın 59'u çözücünün iddiası değildi | Yalnız küme/aralık literalleri: 5/5 doğru |
| Yük temizleyicinin sondaki matematiği atması | `12 + 1` → `12` | Yalnız düz yazı jetonları |
| Yalnız şık harfi veren çözümü sessizce CORRECT saymak | `"Bilmiyorum ama tahminim. Cevap: B"` → CORRECT 0.990, bayraksız | Kapsam bayrakları |
| Kalibrasyonu varsayılan olarak açmak | Kapsamadan 13 öğe götürdü, FP'yi kaldırmadı | Kapalı |
| F4 kritiğinin `tyt-prob-018`'i kapatacağını varsaymak | Çapraz kontrol, sertifikalı adımdaki raporu iptal ediyor | Açık bırakıldı |

### Lean

| Denenen | Neden başarısız oldu |
|---|---|
| `first \| a \| b` alternatiflerini `done` olmadan yazmak | `first` ilk *çalışan* alternatifi seçer; `norm_num at *` ya da `simp` hedefi kapatmadan çalışınca arkadaki doğru alternatif gölgelenir. İspat merdivenlerinde F5'te düzeltilmişti; **vakum sondası 23 Eylül'e kadar eski biçimde kaldı** ve çelişkili hipotezleri kaçırıyordu. |
| Junk değerleri yalnız denetime bırakmak | "tan(π/2) = 0", "√(2−5) = 0", "0/0 = 0", "log 0 = 0" temiz sertifika aldı; ilki `--lean` ile bütün doğrulayıcıdan CORRECT 0.995 çıktı |
| `LEAN_PATH=... exec repl` | `exec` özel bir yerleşik; değişken çocuğa geçmiyor ve Mathlib görünmüyor. Çözüm `lake env <repl>` ve açılışta Mathlib sondası. |
| Bağlamsız matris literali `!![1, 1; 2, 4]` | ℕ olarak elaborate ediliyor (`failed to synthesize CommRing ℕ`); her literale tip ataması yapılmalı |
| `*ᵥ` gösterimi, `Matrix.dotProduct` | Elaborate olmuyor; `Matrix.mulVec` ve kökteki `dotProduct` kullanılmalı |
| Standart trig değerleri için `rw [...]` listesi | Bir lemma ateşlemezse düşüyor; `simp only [...]` kullanılmalı |
| `hasDerivAt_id` | `id ^ 2 * Real.exp` biçimi üretiyor ve eşleşmiyor; `hasDerivAt_id'` kullanılmalı |
| Türevin değerini elle yazmak | SymPy `0^2`'yi sadeleştirip eşleşmeyi bozuyordu; değeri Lean çıkarsın |
| Yan koşulları satır içi `by` bloğunda bırakmak | Ertelenen hedef dışarı sızıyordu; ayrı `have hs0 : (...) ≠ 0 := by ...` satırı gerekiyor |
| CAS'ın hedefi önceden hesaplaması | `gcd(84,120)+lcm(4,6)` → `24 = 24` tautolojisi; artık yapısal ayrıştırma + `is_trivial` |
| Korumalı iff ile çözüm kümesi ifadesi | Kök tanım kümesi dışındaysa iki taraf da yanlış ve iff doğru çıkıyordu; artık her kökün koşulları ve denklemi sağladığı da iddia ediliyor. Aynı açık eşitsizlik uç noktalarında da vardı. |

### Ölçüm ve harness

| Denenen | Neden başarısız oldu |
|---|---|
| Faturalama durdurucusunun `ir_reason` içinde "credit" araması | `str(e)[:120]` kelimeyi bir karakter önce kesiyordu; `except LLMError` sınıfı yutuyordu. 18 Eylül'de 151 öğe boşa gitti ve tarama durmadı. `828fb95`'teki dizgi durdurucusu o koşunun kendi kayıtlarında 0/218 ateşliyor. (Eski belgelerdeki "`aborted: None`" ifadesi dosyayla desteklenmiyor: o koşunun JSON'unda `aborted` anahtarı hiç yok; DECISIONS §23 "Düzeltme (23 Eylül)".) |
| 24 karakterlik sahte hata mesajıyla test | Kırpma sınırının altında kaldığı için hatayı hiç göremedi; test artık sağlayıcının gerçek mesajını kullanıyor |
| Sızma testinde mutasyonu yerel bir değişkene uygulamak | Aynı argümanlarla iki koşu yalnız determinizmi kanıtlar, yalıtımı değil |
| Adversaryal taramanın tek yüzeyde koşması | %0 başarı gösteriyordu ama adım yüzeyindeki açığı (INCORRECT → CORRECT) göremiyordu |
| "Yol (b) sadakati 1.000" tek sayısı | 260 öğenin 245'i yalnız şık harfiyle eşleşiyordu; sayı neredeyse boştu |
| `soundness_fuzz`'ta her kesrin 30 basamaklı ondalığını "eşdeğer" saymak | `8/3` ve `1/6`'nın 30 basamaklı ondalığı gerçekten eşit değil; kâhin hatasıydı. Artık yalnız sonlu ondalıklar üretiliyor (`sp.Float(decimal_str, 30)`). |
| Kaçırılan bozuk adımlar için rapora sabit bir açıklama cümlesi yazmak | Cümle ölçülmüyordu ("`t`, `u`" diyordu, gerçek semboller n, a, t, u, t); kaçan küme değişse de aynı kalırdı. Artık neden adım katmanının kanıtından okunuyor ve açıklanmayan kaçırma bir kapı (23 Eylül). |
| Atlanabilen bellek testi | `test_memory_cap_is_enforced_best_effort` bellek sınırı yokken sessizce atlanıyordu; Faz 1'den 23 Eylül'e kadar hiçbir worker'da sınır yoktu ve kimse fark etmedi. Windows'ta artık atlanamaz. |

### Kapatılmış diğer hatalar (yeniden açılmasın)

- `from mathverify.certify import *` → `ModuleNotFoundError`: `__all__`, router kayıt anahtarlarını
  öznitelik adı sanıyordu.
- `intake.restructure_llm` F3'ten sonra da "ertelendi" diye hata fırlatan ölü koddu.
- Formal katman CLI'dan erişilemiyordu; `verify_cli.py --lean` eklendi.
- F4 bir kez bile koşamazdı: harness kritiği pipeline'a geçirmiyordu. `--no-l6`, kayıt ve rapor
  bölümü eklendi.
- `render_ir` içinde `simplify_expression` ve `count_solutions` şablonları yoktu; round-trip
  yargıcına ham JSON gidiyordu.
- `pipeline` ve `verify_cli`, deterministik geri-düşmeyi `answer_shape` vermeden çağırıyordu
  (DECISIONS §16, "Düzeltme").
- Küme cevaplarında `{` öneki doğru cevabı reddettiriyordu (CORRECT → INCORRECT).
- `Interval.open(...)` Faz 1'den beri kullanılamıyordu; `open(` yasağı onu da yakalıyordu.
- `5π/6` ayrıştırılamıyordu.
- LaTeX dalı beyaz listeyi atlıyordu ve 260 öğenin hiçbiri o dalı tetiklemiyordu. Artık
  `tyt-kap-011` LaTeX iddia taşıyor ve `latex_form` bir saldırı türü.
- `anthropic` ve `python-dotenv` beyan edilmemişti. `MATHVERIFY_CALIBRATION=on` ile kalibrasyon
  dosyası yoksa sessizce hiçbir şey yapmıyordu.
- `solver_family` hiçbir çağırandan verilmiyordu ve `ROLE_FAMILY` hiçbir yerde okunmuyordu.

### Ortam

| Denenen | Neden başarısız oldu |
|---|---|
| Uygulamanın MSIX sanallaştırılmış scratch dizininde pip/uv/venv | Çalışmıyor; proje bu yüzden `C:\Users\kullanici\mathverify` altında |
| Heredoc içinden ters eğik çizgili Python yazmak | `\\boxed` → `\b` gibi çöküşler yanıltıcı sonuç verdi; Write aracıyla gerçek dosya yazılmalı |
| `<stdin>` ya da `-c` ile sandbox kullanan probe | Windows multiprocessing spawn kırılıyor; gerçek dosya ve `if __name__ == "__main__":` gerekli |
| Git kimliği ayarlanmadan commit | `Author identity unknown`; komut başına `git -c user.name=… -c user.email=…` kullanıldı |
| Math-Verify'ı kendi zaman aşımıyla çağırmak | Windows'ta her çağrıda süreç açıyordu; sandbox içinden `timeout_seconds=None` ile çağrılıyor |
| `lambdify` ile karmaşık sabit değerlendirmek | 15 basamağa düşüyordu; yerine `sp.N(expr, dps)` + `as_real_imag` |

---

## 5. Mevcut durum

### 5.1 Tamamlanan ve çalışan

| Faz | Durum |
|---|---|
| F0: §6 sözleşmeleri (E1–E10), IR, sandbox, değerlendirme seti, iki intake yolu | tamam |
| F1-TYT / F1-AYT sertifikaları | tamam |
| F2: sentetik geometri (nümerik realizasyon), kombinatorik/olasılık, seriler, lineer cebir | tamam |
| F3: LLM ön yüzü, L4, L5 | kod tamam; **ölçüm yarım** (218 öğenin 64'ü, sonra kredi bitti) |
| F4: kritik + meta-doğrulama | kod tamam, çevrimdışı testli; **hiç koşmadı** |
| F5: Lean 4 + Mathlib | tamam ve ölçüldü (modelsiz yol) |
| F6: adversaryal sertleştirme + kalibrasyon | tamam ve ölçüldü |
| F7: integral/türev/ilkel/sayma/tekrarlama Lean şablonları | tamam (107 sertifika) |
| 20 Eylül denetimi: 11 boşluk | kapatıldı (DECISIONS §23–25) |
| 23 Eylül denetimi: 4 yanlış-onay sınıfı | kapatıldı (DECISIONS §26–30, `docs/QUALITY.md`) |
| 23 Eylül ikinci oturum: [DOĞRULANMADI] kontrolü, bellek sınırı, belge düzeltmeleri, yeni kapı | tamam, **commit edilmedi** (§5.3) |

Son `check.py --full` sonucu (23 Eylül 2026 13:35, `0f14380` + §5.3'teki commit edilmemiş
değişiklikler; günlük `reports/check_full.log`; toplam ~43 dk, adversaryal 2249 s):

| Kapı | Değer | Hedef |
|---|---|---|
| Birim testleri | 406 geçti, 1 atlandı (`test_f5_lean.py:66`, beklenen) | hepsi geçer |
| Cevap düzeyi pozitif / negatif precision | 1.000 / 1.000 | ≥ 0.98 |
| Kapsama | 1.000 | ≥ 0.85 |
| B hücresi yanlış red | 0.000 | < 0.10 |
| Anahtar sızma testi | geçti | zorunlu |
| Çözüm düzeyi pozitif precision | 0.994 (1 FP: `tyt-prob-018`) | raporlanır |
| D hücresi tespiti | 0.976 (41/42) | raporlanır |
| Yol (b): cevabın kendisi karşılaştırılan öğe | 20/20 | raporlanır |
| L5 uygulanabilirlik tavanı | 21/280 (D'de 3/42) | raporlanır |
| Ölçülmeyen görev türü | yok | yok |
| Lean FP | 0 | 0 |
| Lean sertifika | 107/280 (152 öğede ifade üretiliyor) | raporlanır |
| Lean junk-value sertifikası | 0/12 | 0 |
| Adversaryal saldırı başarısı | %0.000 (21 139 saldırı) | < %2 |
| Saldırı yüzeyleri | cevap, şık, adım | üçü de |
| SymPy üretimli yanlış cevapta yanlış onay | 0/448 | 0 |
| SymPy üretimli eşdeğer cevapta yanlış red | 0/214 | 0 |
| Cevap olmayan iddiada CORRECT | 0/46 | 0 |
| Geçerli adım dönüşümünde yanlış red | 0/184 | 0 |
| Nedeni açıklanmayan kaçırılan bozuk adım (yeni) | 0/6 | 0 |
| Kalibre test precision (poz/neg) | 1.0 / 1.0 | raporlanır |

Kaynaklar: `reports/eval_report.md`, `lean_report.md`, `adversarial_report.md`,
`soundness_report.md`, `calibration_report.md`. Kapı çıktısının tamamı `reports/check_full.log`
içinde (§6.5).

**Süre notu:** Bu koşu öncekinden yavaştı (adversaryal 1245 → 2249 s, değerlendirme 67 → 121 ms/öğe).
Bellek sınırı düzeltmesinden gelmediği ölçüldü: `run_eval` eski ve yeni `pool.py` ile sırayla
dört kez (yeni/eski/yeni/eski) koşturuldu, dördü de 64 s ve 113–114 ms/öğe. Yavaşlık makinenin o
anki durumundan. Hiçbir sonuç dosyasında `MemoryError`, worker ölümü, `cas_error` ya da
`cas_timeout` yok; raporlarda süre dışında değişen satır yok.

### 5.2 Yarım kalan iş

**Kodda yarım kalan bir iş yok.** Son oturumun sırası şöyleydi:

1. 20 Eylül denetimi: "tek eksik API anahtarı mı?" sorusu. Cevap hayırdı; 11 boşluk bulundu ve
   kapatıldı.
2. 23 Eylül: önce literatür tarandı (`docs/QUALITY.md`), sonra doğrulayıcının kendisi test edildi.
   4 yanlış-onay sınıfı bulundu ve kapatıldı.
3. İkisi birlikte `0f14380` olarak commit'lendi (93 dosya, +7235/−320). Kullanıcıya sonuç
   raporu verildi.
4. Bu belge 12 bölümlü yapıya çevrildi, `CLAUDE.md` oluşturuldu ve README'deki eski bölüm
   göndermeleri güncellendi.

O oturumda fark edilip düzeltilmeyen iki şey (bellek sınırı §6.4, kapı günlüğü §6.5) 23 Eylül
ikinci oturumunda kapatıldı. O oturumun sırası:

5. Belgedeki 8 [DOĞRULANMADI] noktası kodla ve ölçümle kontrol edildi. 6'sı doğrulandı ve
   işareti kaldırıldı. Kalanlar: §4'te kod geri alınmadan üretilemeyen "önce" ölçümleri ve
   anahtarların hâlâ geçerli olup olmadığı. İki ifade yanlış çıktı ve "Düzeltme" notuyla
   düzeltildi: `aborted: None` (DECISIONS §23) ve Gauss–Legendre "5e-3 hata", ki göreli hatadır
   (`docs/E1-E10-measurement.md`). README'deki F3 cümlesi de yanlıştı ("64/64", "154 öğe kredi
   hatasıyla"); düzeltildi (§6.6).
6. Bellek sınırı düzeltildi ve atlanamayan teste bağlandı (§6.4).
7. `soundness_fuzz` kaçırma nedenlerini ölçümden yazıyor; yeni kapı (§6.2).
8. `check.py --full` günlüğü kendisi yazıyor (§6.5). 22/22 kapı geçti.

### 5.3 Commit edilmemiş değişiklikler

| Dosya | Durum | Ne işe yarıyor |
|---|---|---|
İki oturumun birikimi; hiçbiri commit'li değil.

| Dosya | Durum | Ne işe yarıyor |
|---|---|---|
| `HANDOFF.md` | değişti | Bu belge: 12 bölümlü yapı; [DOĞRULANMADI] kontrolünün sonuçları, §6.2/§6.4/§6.5/§6.6/§6.8/§6.9 ve §7 güncellendi |
| `CLAUDE.md` | yeni | Kalıcı proje kuralları (§10'un özü) |
| `README.md` | değişti | Bölüm göndermeleri; 22 kapı ve günlük; F3 cümlesi düzeltildi; kaçırma nedeni satırı |
| `DECISIONS.md` | 3 not | §5 bellek sınırı "Düzeltme", §23 `aborted: None` "Düzeltme", §30 kaçırma nedeni "Ek" |
| `docs/E1-E10-measurement.md`, `docs/LLM_LAYERS.md` | düzeltme notu | Gauss–Legendre göreli hata; `aborted: None` |
| `docs/QUALITY.md` | 2 satır | Yeni kapı ve kaçırma nedenlerinin raporlanması |
| `src/mathverify/sandbox/pool.py` | davranış | Tipli ctypes prototipleri (`_win_api`); bellek sınırı artık uygulanıyor |
| `src/mathverify/formal/statement.py` | 1 yorum satırı | "HANDOFF §6" → "HANDOFF §4" (davranış değişikliği yok) |
| `tests/test_sandbox.py` | değişti | Bellek testi Windows'ta atlanamaz; bekçi testi |
| `tests/test_soundness_fuzz.py` | yeni | Kaçırma nedeni sınıflandırıcısının 4 testi |
| `harness/soundness_fuzz.py` | değişti | `ACCEPTED_MISS_REASONS`, `_missed_step_reason`; rapor nedenleri ölçümden yazıyor |
| `harness/run_f3.py` | 1 yorum | `aborted=None` ifadesi düzeltildi |
| `scripts/check.py` | değişti | 22. kapı; `--full` günlüğü kendisi yazıyor |
| `reports/*.md`, `reports/check_full.log` | üretildi | 23 Eylül 13:35 koşusu (sayılar aynı, yalnız süreler ve soundness raporundaki neden satırları değişti) |

Commit yalnız kullanıcı isterse yapılır.

### 5.4 Dal durumu

- `master`: `2744677`'de, yani 20 ve 23 Eylül denetimlerinden önce.
- `denetim-2026-09-20`: `0f14380` (HEAD). İki denetim burada.
- Uzak depo yok. Birleştirme kullanıcı kararı (§12).

Commit geçmişi (eskiden yeniye):

| Commit | Ne |
|---|---|
| `7c222fd` | Faz 1: F0 sözleşmeleri, IR, sandbox, değerlendirme seti, iki intake yolu, F1-TYT/AYT |
| `651f2ec` | README'de kesin test sayısı |
| `d5c8ee8` | F2: sentetik geometri, kombinatorik/olasılık, seriler, lineer cebir |
| `828fb95` | F3–F5: LLM ön yüzü, çapraz aile katmanları, kritik, Lean katmanı (+ `llm_cache/`) |
| `b768e09` | F5: formal kapsam iki katına çıktı, iki şablon sadakat hatası düzeltildi |
| `674b34a` | F6: adversaryal sertleştirme, ölçülmüş kalibrasyon, `check.py` |
| `a94860d` `77cc9d9` `a9d264f` | F7: belirli integral, türev/ilkel, sayma/tekrarlama şablonları (107 sertifika) |
| `abc33d0` `3afda33` | Temizlik ve Lean yeniden ölçümü |
| `53ab97b` | 19 Eylül denetimi: beş boşluk, iki yanlış iddia |
| `2744677` | Önceki HANDOFF.md (`master` burada) |
| `0f14380` | 20 ve 23 Eylül denetimleri (`denetim-2026-09-20`, HEAD) |

Literatür kaynaklarının bağlantıları (ProcessBench, Hard2Verify, Beyond the Answer Key,
Pessimistic Verification, TinyV, Faults in Our Formal Benchmarking, Right Is Not Enough, Robustness
Testing of Intermediate Verifiers, Prover–Verifier Deliberation) `docs/QUALITY.md` içindedir.

---

## 6. Bilinen sorunlar

### 6.1 Deterministik hattın tek yanlış onayı: `tyt-prob-018`

Cevap doğru, ara adım doğru ama gerekçesiz ("iki denklemi çıkarınca a − b = 2"). Çözüm düzeyi
pozitif precision'daki tek FP bu (0.994). Gerekçesi §3 karar 21'de; F4 koşmadan karar verilemez.
Raporun "Sertifikanın iptal ettiği kritik raporu" satırı kararı sayıyla verecek.

### 6.2 Çözücünün kendi sembolüyle yazılmış adımlar denetlenmiyor

Bilerek böyle (§3 karar 3). `reports/soundness_report.md`'ye göre bir tarafı +1 bozulan 46 adımın
40'ı yakalanıyor. Kaçan 6 adımın nedeni artık raporda adım katmanının kendi kanıtından yazılıyor
(23 Eylül'e kadar sabit bir cümleydi):

| Öğe / adım | Neden | Sembol |
|---|---|---|
| `ayt-ana-006` s2 | `undeclared_symbol` | `n` |
| `ayt-diz-008` s1 | `undeclared_symbol` | `a` (dizinin adı, `a(n)`) |
| `ayt-lim-008` s2 | `undeclared_symbol` | `t` |
| `tyt-den-007` s2 | `undeclared_symbol` | `u` |
| `uni-la-002` s1 | `undeclared_symbol` | `t` |
| `tyt-den-003` s2 | `premises_have_no_solution`: öncül `x/(x−3) = 3/(x−3) + 2` çözümsüz, altın cevap `{}` | — |

Bilerek kabul edilen nedenler `harness/soundness_fuzz.py::ACCEPTED_MISS_REASONS` içinde. Başka bir
nedenle kaçırılan bozuk adım `check.py --full`'da "nedeni açıklanmayan kaçırılan bozuk adım"
kapısını düşürür (bugün 0/6).

### 6.3 Adımsız çözümde CORRECT yalnız cevap düzeyindedir

Yol (b)'de çoğu zaman denetlenebilir adım yoktur. Karar `answer_level_only` /
`answer_from_option_letter` bayraklarını ve `KAPSAM:` satırını taşır, ama bayrağa bakmayan bir
tüketici farkı görmez.

### 6.4 Sandbox bellek sınırı hiç uygulanmıyordu — DÜZELTİLDİ (23 Eylül)

`tests/test_sandbox.py::test_memory_cap_is_enforced_best_effort` Faz 1'den beri
`unavailable:AssignProcessToJobObject` ile sessizce atlanıyordu.

**Kök neden (probe ile doğrulandı):** `src/mathverify/sandbox/pool.py` içinde
`ctypes.windll.kernel32` fonksiyonları `restype`/`argtypes` verilmeden çağrılıyordu.
`GetCurrentProcess()`'in 64 bit sözde tutamacı 32 bit'e kırpılıyordu. Sonuç:

- `_apply_mem_limit` → `AssignProcessToJobObject` başarısız. Job Object sınırı yok.
- Yedek `_start_mem_watchdog` → `_rss_bytes()` `None`, çünkü `GetProcessMemoryInfo` aynı
  tutamaçla düşüyordu. Bekçi de başlamıyordu.

Yani worker'ları yalnız zaman aşımı koruyordu.

**Düzeltme:** `pool.py::_win_api()` özel `ctypes.WinDLL("kernel32"/"psapi", use_last_error=True)`
örnekleri ve açık prototipler kullanıyor; hata dizgisine Windows hata kodu ekleniyor.
Ölçüm: 512 MB sınırda 1500 MB'lık ve 2048 MB sınırda 3000 MB'lık ayırma `MemoryError` ile durdu;
sınır altında sympy/mpmath/z3 ısınma importu sorunsuz. Bu makinede süreçler zaten bir Job Object
içinde (`IsProcessInJob` True, muhtemelen masaüstü uygulaması); iç içe job çalışıyor.

**Teste bağlı:** Windows'ta `test_memory_cap_is_enforced_best_effort` artık atlanamaz
(`mem_mode == "job_object"` ve hata `MemoryError` olmalı). Yeni
`test_watchdog_fallback_can_read_process_memory` bekçinin bellek okuyabildiğini sınar. İkisi de
eski `pool.py` ile düşüyor, yenisiyle geçiyor (mutasyon kontrolü yapıldı).

### 6.5 Depodaki kapı günlüğü eskiydi — DÜZELTİLDİ (23 Eylül)

`reports/check_full.log` 19 Eylül'den kalmaydı (`12/12`); 23 Eylül'deki 21/21 çıktısı yalnız o
oturumun geçici görev dosyasındaydı. Artık `check.py --full` günlüğü kendisi yazıyor: başlıkta
tarih, dal, commit ve commit edilmemiş dosya sayısı var, satırlar koşu sırasında yazılıyor.

### 6.6 F3 yarım ölçüldü, F4 hiç koşmadı

`reports/f3_report.md` 18 Eylül'deki yarım koşudan ve eski raporlayıcıdan kalma:

- IR kabulü 64/218.
- 151 öğe `Your credit balance is too low` ile düştü.
- "Yol (b)" bölümü yol (b)'yi ölçmüyor. 218 öğenin 184'ü kredi bittiği için deterministik cevap
  çıkarıcıya düşmüştü (hepsinde `restructure_deterministic_only`), ve adımsız bir öğede D hücresi
  yapısal olarak yakalanamaz. Oradaki "37 yanlış karar, D tespiti 3/39" bu geri-düşmenin
  ölçümüdür.
- Gerçekten yeniden yapılandırılan 34 öğede 32/34 doğru karar, 0 UNKNOWN, D tespiti 3/5. 23 Eylül'de
  `reports/f3_results.json`'dan `run_f3`'ün kendi ayrımıyla (`n_steps > 0`) yeniden hesaplandı;
  LLM çağrısı yapılan öğelerle birebir aynı küme. **2 yanlış kararın ikisi de D hücresinde yanlış
  onay** (`ayt-ana-017`, `ayt-ana-019` → CORRECT), yani pahalı olan hata türü. Sayılar 18 Eylül
  koduna ait; o günden beri iki denetim yapıldı.
- IR kabulü: faturalama hatası almayan 67 öğede 64/67. Reddedilen 3 öğe (`ayt-diz-008`, `-013`,
  `-018`) üç turun sonunda round-trip'te Meta yargıcının puan döndürmediği (`meta: None`) öğeler;
  nedeni kayıtlardan anlaşılmıyor. README'deki eski "64/64" ve "kalan 154 öğe kredi hatasıyla
  düştü" ifadeleri 23 Eylül'de düzeltildi.
- Rapor yeniden koşulunca yeni raporlayıcı iki durumu ayrı yazacak.

### 6.7 Ölçüm hâlâ sentetik

Setin tamamını biz ürettik. Ölçülen 1.000 precision, gerçek bir modelin çözüm dağılımına karşı
değil. Bu açık kodla kapanmaz.

### 6.8 Teknik borç ve küçük tutarsızlıklar

- `DECISIONS.md` bölüm sırası 1, 2, 3, 6, 4, 5 ve madde numaraları bölümler arasında atlıyor.
  §3.9 hâlâ "180 öğe" diyor; bu Faz 1 anlık görüntüsü, güncel sayı 280.
- `harness/run_lean.py` varsayılan `--timeout 60`; `check.py` ve README `45` kullanıyor.
- `scripts/clean_imports.py`, `scripts/diag_sandbox.py`, `scripts/lean_try.py` ve `smoke_*.py`
  tek seferlik geliştirme betikleri. 23 Eylül'de bakıldı: hiçbiri kod, test ya da `check.py`
  tarafından çağrılmıyor (yalnız README'de `smoke_*` diye anılıyor); importlarının hepsi hâlâ
  çözülüyor. `clean_imports.py` pyflakes'e dayanıyor ama pyflakes `pyproject.toml`'da beyan
  edilmemiş. `lean_try.py` §4'te elaborate olmadığı yazılan `Matrix.dotProduct` adaylarını
  içeriyor (tarihî F5 geliştirme betiği). Tutulup tutulmayacakları kullanıcı kararı (§12).
- `certify/counting.py::count_real_roots` kesin olmayan (Float) katsayılı polinomu `nsimplify`
  ile "güzel sayıya" yakalıyor; doğrudan çağrıldığında diskriminantı −4.2e-17 olan
  `x² − 0.6666666666666666x + 0.1111111111111111` için 0 yerine 1 kök sayıyor. 23 Eylül'de uçtan
  uca ölçüldü: doğrulayıcı yolundan **ulaşılamıyor**, çünkü ayrıştırıcı her ondalığı (açık
  `Float(...)` dahil) kesin rasyonele çeviriyor ve iki biçimde de karar doğru (0 kök). Ölü ama
  §3 karar 15'e aykırı bir dal; kaldırılması kullanıcı onayı bekliyor. `sandbox/ops.py`
  `nroots_scan` içindeki `nsimplify(...) if False else ...` de ölü kod.
- Lint ya da biçimlendirici yapılandırılmamış (`pyproject.toml`'da ruff/flake8/black yok).
- CI yok. Kapılar yalnız elle `check.py` ile koşuyor.

### 6.9 Güvenlik

İki API anahtarı yalnız git'in yok saydığı `.env` dosyasında
duruyorlar (`.gitignore:13`). 23 Eylül'de yeniden tarandı, değerler yazdırılmadan: iki anahtarın
değeri, tam ya da 16 karakterlik parça olarak, 14 commit'in (reflog dahil) tam diff'inde, izlenen
dosyalarda (`llm_cache/` dahil) ve 20 erişilemez blob'da **0** kez geçiyor; `sk-ant-` deseni 0;
stash yok. İş bitince ikisinin de yenilenmesi önerilir. Anahtarların hâlâ geçerli olduğu en son
19 Eylül'de görüldü **[DOĞRULANMADI: ağ isteği gerektirir, kontrol edilmedi]**.

---

## 7. Sıradaki adımlar

Eski listenin ilk iki maddesi 23 Eylül'de tamamlandı: sandbox bellek sınırı (§6.4) ve kapı
günlüğü (§6.5).

**Kullanıcı kararı (23 Eylül 2026):** krediye bağlı ölçümler (aşağıda 3–5) ancak bütün lokal iş
bitip program en kaliteli hâline geldikten sonra koşulacak. Bunun iki sonucu var: (a) F3/F4
koşusundan önce kod dondurulur; ölçümden sonraki her kod değişikliği o sayıları yeniden eskitir
(18 Eylül F3 sayıları bugün bu durumda). (b) Bazı kararlar yalnız o ölçümle verilebilir
(`tyt-prob-018` kuralı, §3 karar 21; F4'ün yerini hak edip etmediği); "en kaliteli" lokal durum
bu soruları açık bırakır.

Öncelik sırasıyla:

1. **Kullanıcıya §12'deki soruları sor.** En önemlisi: `denetim-2026-09-20` → `master`
   birleştirmesi ve commit edilmemiş değişikliklerin (§5.3) commit'i.

2. **Lokal kalite işleri (kredi gerektirmez, her biri kullanıcı onayıyla):**
   - `certify/counting.py::count_real_roots` içindeki ölü `nsimplify` dalını kaldır ya da
     kesin olmayan polinomu reddet (§6.8); `ops.py`'deki `if False` ölü kodu.
   - Tek seferlik betikler: tut / sil / `scripts/dev/` altına taşı; tutulursa pyflakes'i `[dev]`e
     ekle (§6.8).
   - `harness/run_lean.py` varsayılan zaman aşımını `check.py` ile hizala (60 → 45) ya da tersini
     belgele.
   - İsteğe bağlı: `domain_of`, `simplify_expression`, `count_solutions` için Lean şablonları.
     Her yeni şablon yanlış cevaplı öğelerde ve junk sondasında da koşturulmalı; FP = 0 ve
     junk = 0 kalmalı.
   - İsteğe bağlı: çözücü sembolü adımları (§6.2). Ancak sağlam bir ayrım bulunursa; örneğin
     yapısal formatta çözücünün sembolü tanımlamasını zorunlu kılmak. Karar verilmedi.
   - Her iş sonunda `check.py --full` bütün kapılardan geçmeli.

3. **Kod dondurulduktan ve anahtarlar yenilendikten sonra F3'ü tamamla.** Önce kalibrasyon
   koşusu: `.venv/Scripts/python.exe -m harness.run_f3 --limit 10 --workers 3 --max-cost 5`.
   Öğe başına gerçek maliyeti ölç; yarım koşuda 0,066 $/öğe ölçülmüştü (`docs/LLM_LAYERS.md`).
   Sonra tam koşu: `.venv/Scripts/python.exe -m harness.run_f3 --workers 6 --pathb --max-cost 40`.
   Kalan 154 öğe için kaba tahmin ~10 $. `llm_cache/` istek hash'iyle anahtarlıdır; istem ya da IR
   metni değiştiyse eski kayıtlar tekrar oynatılmaz ve yeniden ücretlendirilir.

4. **F4'ü ilk kez koştur** (aynı koşuda L6 açık). Kaba tahmin 15–25 $. Raporun "L6 kritik +
   meta-doğrulama (F4)" bölümündeki iki sayı belirleyici: D tespiti ve doğru çözümde yanlış
   suçlama. "Sertifikanın iptal ettiği kritik raporu" satırı `tyt-prob-018` kararını verir
   (§3 karar 21).

5. **Gerçek AI çözücü çıktılarıyla ölç.** `--solver-family anthropic|meta` **mutlaka** verilmeli.
   Kullanıcı bu adımı erteledi.

6. **Uzak depo + CI + LICENSE.** Bunlar sahiplik kararları. Açılırsa CI hızlı modda
   `scripts/check.py` çalıştırmalı; Lean ve `--full` WSL ister.

---

## 8. Kritik dosyalar

| Yol | Açıklama |
|---|---|
| `src/mathverify/verifier.py` | Deterministik giriş: `verify`, `verify_layers`, `fuse_layers`, şık/kapsam bayrakları, `_sanitize_payload`, `_claim_not_a_value`, `_mc_consistency`, `_sanity` |
| `src/mathverify/pipeline.py` | `run_pipeline`: soru metninden karara tam otomatik hat (IR çıkarımı + L4/L5/L6/L7) |
| `src/mathverify/ir.py` | `ProblemIR`, `FORBIDDEN_KEYS`, `LeakageError` |
| `src/mathverify/solution.py` | `Solution`, `ClaimedAnswer`, `Step` |
| `src/mathverify/types.py` | `LayerResult`, `VerificationResult` |
| `src/mathverify/router.py` | `ROUTES` (görev türü → modüller), `DEFERRED_KINDS`, `route` |
| `src/mathverify/normalize/parse.py` | Beyaz listeli ayrıştırıcı; `COMPUTING_OPERATORS`, `claim_namespace`, `check_claim_is_value`, `UndeclaredSymbolError`, `ClaimNotAValue` |
| `src/mathverify/normalize/turkish.py` | Türkçe sayı biçimi ve metin normalizasyonu |
| `src/mathverify/equiv/__init__.py` | Eşdeğerlik motorunun girişi, `exact_integer` |
| `src/mathverify/equiv/numeric.py` | Hassasiyet merdiveni (her basamakta eşitlik) |
| `src/mathverify/equiv/random_point.py` | Rastgele nokta testi, `_definite_nonzero_difference` |
| `src/mathverify/sandbox/pool.py` | Worker havuzu, zaman aşımı, bellek sınırı (`_win_api`: tipli ctypes prototipleri, §6.4) |
| `src/mathverify/sandbox/ops.py` | Sandbox içindeki işlemler, `zero_test_battery` |
| `src/mathverify/certify/base.py` | `Ctx`, `Ctx.claim_ns`, `Ctx.claimed` |
| `src/mathverify/certify/__init__.py` | `MODULES` kaydı (13 sertifika modülü) |
| `src/mathverify/certify/domain.py` | `definedness_conditions`; Lean junk korumaları da bunu kullanır |
| `src/mathverify/steps/deterministic.py` | `check_steps`: yalnız karşı örnekle çürüten adım reddedici |
| `src/mathverify/fuse/rules.py` | `fuse`, `_BLOCK_POSITIVE_FLAGS`, kalibrasyon, `CalibrationUnavailable` |
| `src/mathverify/intake/restructure.py` | Yol (b) deterministik cevap çıkarıcı ve küme/aralık kurtarma |
| `src/mathverify/extract/ir_extract.py` | LLM ile IR çıkarımı + round-trip + onarım |
| `src/mathverify/llm/__init__.py` | Aile/rol eşlemesi, istemci seçimi, `set_client_override` |
| `src/mathverify/llm/base.py` | `LLMError`, `LLMFatalError` (alt sınıfı değil!) |
| `src/mathverify/llm/cache.py` | Kayıt/tekrar önbelleği |
| `src/mathverify/formal/statement.py` | Lean ifade şablonları (`build_statement`, `_t_*`), junk-value korumaları, `vacuity_probe`, `is_trivial` |
| `src/mathverify/formal/prove.py` | Taktik merdiveni, ispat denetimleri, `l7_layer` |
| `src/mathverify/formal/lean_client.py` | WSL içindeki Lean REPL istemcisi |
| `harness/run_eval.py` | Deterministik ölçüm ve sızma testi → `reports/eval_report.md` |
| `harness/run_lean.py` | Lean taraması + 12 `JUNK_PROBES` → `reports/lean_report.md` |
| `harness/adversarial.py` | 3 yüzeyli adversaryal tarama → `reports/adversarial_report.md` |
| `harness/soundness_fuzz.py` | Metamorfik/diferansiyel sağlamlık taraması → `reports/soundness_report.md`; `ACCEPTED_MISS_REASONS`, `_missed_step_reason` |
| `harness/calibrate.py` | Kalibrasyon (train/val/test) |
| `harness/run_f3.py` | LLM'li tam hat ölçümü (F3/F4); `--max-cost`, `--solver-family`, `--pathb` |
| `scripts/check.py` | Bütün kapılar tek komutta; `--full` günlüğü `reports/check_full.log`a kendisi yazar |
| `scripts/verify_cli.py` | Tek öğe ya da serbest metin doğrulama; `--lean` |
| `evalset/build/build_all.py` | 280 öğeyi yeniden üretir |
| `tests/conftest_llm.py` | `ScriptedClient`: F3/F4 testleri ağsız koşar |
| `DECISIONS.md` | Kilitli kararlar ve 30 uygulama kararı |
| `docs/ARCHITECTURE.md` | Yetki tablosu ve tasarım gerekçeleri |
| `docs/QUALITY.md` | Literatür → mekanizma → kapı tablosu |
| `docs/SOLVER_FORMAT.md` | Yol (a) yapısal çözüm formatı ve görev türleri |
| `docs/LLM_LAYERS.md` | Roller, modeller, önbellek, maliyet, hata sınıfları |
| `docs/LEAN_SETUP.md` | WSL + Lean + Mathlib kurulumu |
| `docs/E1-E10-measurement.md` | Şartname §6 davranış sözleşmelerinin ölçümü |

---

## 9. Komutlar ve ortam

Bütün komutlar proje kökünden. Windows'ta **`PYTHONUTF8=1`** gerekir; `check.py` bunu alt süreçlere
kendisi verir. Bu belgedeki `PYTHONUTF8=1 komut` biçimi **Git Bash** içindir. PowerShell'de önce
`$env:PYTHONUTF8 = "1"` çalıştırılır, sonra komut öneksiz yazılır.

### Kurulum

```bash
uv venv --python 3.14 .venv
uv pip install --python .venv/Scripts/python.exe -e ".[llm,dev]"
```

Lean, tek seferlik kurulum (ayrıntı: `docs/LEAN_SETUP.md`):

```bash
wsl -d Ubuntu -- bash /mnt/c/Users/kullanici/mathverify/scripts/setup_lean.sh
wsl -d Ubuntu -- bash /mnt/c/Users/kullanici/mathverify/scripts/setup_lean_repl.sh
wsl -d Ubuntu -- bash /mnt/c/Users/kullanici/mathverify/scripts/lean_status.sh
```

`setup_lean.sh` sonrasında üst düzey `Mathlib.olean` eksikse `scripts/lean_fix.sh` çalıştırılır.
Lean bu makinede kurulu: WSL `Ubuntu` mevcut ve 23 Eylül Lean taraması çalıştı.

### Test ve kapılar

| Komut | Ne yapar | Süre |
|---|---|---|
| `.venv/Scripts/python.exe -m pytest tests -q` | 407 test (406 geçer, 1 atlanır) | ~55 s |
| `.venv/Scripts/python.exe scripts/check.py` | Hızlı: testler + deterministik ölçüm (11 kapı) | ~1.5 dk |
| `.venv/Scripts/python.exe scripts/check.py --full` | + Lean, adversaryal, sağlamlık, kalibrasyon (22 kapı); günlüğü `reports/check_full.log`a yazar | **~25–45 dk** (adversaryal tek başına 21–38 dk, makine yüküne bağlı) |

### Tek tek ölçümler

| Komut | Çıktı |
|---|---|
| `.venv/Scripts/python.exe evalset/build/build_all.py` | 280 öğeyi yeniden üretir |
| `.venv/Scripts/python.exe -m harness.run_eval` | `reports/eval_report.md` |
| `.venv/Scripts/python.exe -m harness.run_lean --timeout 45` | `reports/lean_report.md` |
| `.venv/Scripts/python.exe -m harness.adversarial` | `reports/adversarial_report.md`; `--ids a,b` hedefli tekrar |
| `.venv/Scripts/python.exe -m harness.soundness_fuzz` | `reports/soundness_report.md` |
| `.venv/Scripts/python.exe -m harness.calibrate` | `reports/calibration_report.md` |
| `.venv/Scripts/python.exe -m harness.run_f3 --workers 6 --pathb --max-cost 40` | `reports/f3_report.md`; kredi ister. `--no-l4/--no-l5/--no-l6`, `--limit`, `--ids`, `--solver-family` |

### Tek öğe doğrulama

```bash
.venv/Scripts/python.exe scripts/verify_cli.py --item evalset/items/tyt-prob-001.json --lean
.venv/Scripts/python.exe scripts/verify_cli.py --item evalset/items/tyt-prob-001.json --text "… Cevap: B"
```

Diğer bayraklar: `--ir`, `--solution`, `--json`, `--no-steps`.

### Build ve lint

Ayrı bir build adımı yok; paket `-e` ile kurulu. Lint ya da biçimlendirici **yapılandırılmamış**.

### Ortam değişkenleri (yalnız adlar; değerler `.env` içinde, asla yazılmaz)

| Değişken | Anlamı |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic ailesi (`.env` içinde) |
| `ANTHROPIC_AUTH_TOKEN` | Anthropic için alternatif kimlik bilgisi (kodda okunuyor, `.env`'de yok) |
| `META_MODEL_API_KEY` | Meta Muse Spark ailesi (`.env` içinde) |
| `MATHVERIFY_ANTHROPIC_MODEL` | Varsayılan `claude-opus-5` |
| `MATHVERIFY_META_MODEL` | Varsayılan `muse-spark-1.3` |
| `MATHVERIFY_LLM_CACHE` | `auto` (varsayılan) / `replay` (ağa çıkmaz) / `off` |
| `MATHVERIFY_LLM_CACHE_DIR` | Varsayılan `llm_cache/` |
| `MATHVERIFY_CALIBRATION` | `on` → kalibre füzyon (varsayılan kapalı) |
| `MATHVERIFY_LEAN_PROJECT` | Varsayılan `~/mathverify-lean` (WSL içinde) |
| `MATHVERIFY_LEAN_REPL` | Varsayılan `~/repl/.lake/build/bin/repl` |
| `MATHVERIFY_WSL_DISTRO` | Varsayılan `Ubuntu` |
| `MATHVERIFY_SANDBOX` | `process` (varsayılan) / `inline` (yalnız hata ayıklama) |
| `PYTHONUTF8` | Windows'ta `1` olmalı |
| `PYTHONHASHSEED` | Sandbox worker'larında `0`'a sabitlenir (kod yapar) |

### Harici servisler ve bağımlılıklar

- Anthropic API: F3+ katmanları. **Bakiye bitti.**
- Meta Muse Spark API: ikinci aile.
- WSL Ubuntu + Lean 4 v4.34.0 + Mathlib: L7. Olean cache ~6.7 GB.
- Başka ağ bağımlılığı yok. Deterministik hat tamamen çevrimdışı çalışır.

---

## 10. Kurallar ve tercihler

### Kullanıcının tercihleri

- **Dil:** kullanıcıyla Türkçe konuşulur. Belgeler, raporlar, karar izleri ve commit mesajları
  Türkçe. Kod, tanımlayıcılar ve `src/` içindeki yorumlar İngilizce.
- **Derinlik:** kullanıcı en kaliteli, kapsamlı ve özerk çalışmayı ister. "Emin ol" ya da "tek
  eksik bu mu" gibi sorular harfiyen kastedilir. Cevap, bir önceki cevabın tekrarı değil, yeni ve
  sistematik bir denetim olmalı. Krediye bağlı olmayan bir açık bulunursa aynı turda düzeltilmeli.
- **Dürüstlük:** ölçülmüş sayılar verilir, "testler geçiyor" kanıt sayılmaz. Doğrulanmamış bilgi
  işaretlenir. Önceki bir iddia yanlış çıktıysa bu açıkça söylenir.
- Kilitli kararlar (D1–D6) yeniden sorulmaz.

### Asla yapılmayacaklar

1. Cevap anahtarını ya da anahtar benzeri bir alanı doğrulama hattına sokmak.
2. Bir LLM sinyalinin sert bir sertifikayı ters çevirmesine izin vermek.
3. Bir adımı somut karşı örnek olmadan reddetmek.
4. Lean ifadesini bir modele yazdırmak, ya da bir ispatı sorry/aksiyom/vakum/kullanılmayan
   hipotez denetiminden geçirmeden kabul etmek.
5. `first | …` zincirinde `done` ile kapanmayan bir alternatif yazmak.
6. Bir iddiayı karşılaştırmadan önce yeniden yazmak: `int()`, `nsimplify`, yuvarlama,
   "güzelleştirme" yok.
7. Tek başına nümerik eşitliği kanıt saymak, ya da Math-Verify'ı tek başına karar verdirmek.
8. İddiayı hesaplayan operatörlerin açık olduğu bir ad alanında okumak.
9. `.env`'i, `reports/*.json`'ı ya da herhangi bir anahtarı commit etmek. Anahtar değerlerini
   ekrana, belgeye ya da günlüğe yazmak.
10. Global git ayarını değiştirmek. Kimlik gerekirse komut başına `git -c user.name=… -c user.email=…`
    verilir; önceki commit'lerle aynı kimlik `git log -1 --format='%an <%ae>'` ile görülür.
11. Kullanıcı istemeden commit ya da birleştirme yapmak. Doğrudan `master` üzerinde commit etmek:
    önce dal açılır.
12. Ölçmeden "iyileştirme" iddia etmek.

### Her değişiklikte

- `scripts/check.py --full` 22/22 kalmalı. Hızlı döngüde `scripts/check.py` ve `pytest` yeterli;
  bitirmeden önce `--full` koşturulur.
- Lean tarafında her yeni şablon **yanlış cevaplı öğelerde de** koşturulur. Lean FP = 0 ve
  junk-value sertifikası = 0 kalmalı.
- Her bulgu önce ölçümle bulunur, sonra ölçümle doğrulanır, sonra bir teste ya da kalıcı bir kapıya
  bağlanır.
- Kararlar `DECISIONS.md`'ye, gerekçe ve ölçümle birlikte yazılır. Yanlış çıkan eski ifade
  silinmez; "Düzeltme (tarih)" notuyla düzeltilir.
- Raporlar üretilir, elle yazılmaz.

### Commit biçimi

Başlık `alan: özet` biçiminde ve Türkçe: `denetim:`, `F7:`, `raporlar:`, `temizlik:`,
`HANDOFF.md:`. Gövdede ne ölçüldüğü ve nasıl doğrulandığı yazılır. Son satır:

```
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

### Kod stili

- Çevredeki kodun deyimine uy; yorumlar neden'i anlatır ve ölçüme atıf yapar.
- Tip ipuçları ve (paket `__init__` dosyaları dışında yaygın olarak)
  `from __future__ import annotations` kullanılır.
- Hatalar sınıflandırılır: `LeanPrintError`, `UndeclaredSymbolError`, `ClaimNotAValue`,
  `LLMFatalError`.
- Karar kapsamı bayraklarla, makine tarafından okunabilir biçimde verilir.

---

## 11. Tuzaklar

### SymPy

- **SymPy ≥ 1.13'te `Float(3.0) == 3` False döner.** Tam sayılığı `sp.Rational(Float)` ile
  kontrol et; `exact_integer` bunu yapıyor.
- `sp.sqrt` bir sınıf değil fonksiyondur; `isinstance` kontrolünde kullanılamaz. sqrt
  `Pow(…, 1/2)` olarak işlenir.
- `parse_expr` için `rational=True` diye bir parametre yok; `rationalize` dönüşümü kullanılır.
- `sp.evaluate(False)` altında ayrıştırmada `NameError: Add` alınabilir; yapısal ad alanına
  `Add/Mul/Pow` eklendi.
- `is_subset` sonucu hash tohumuna bağlı değişebiliyor; sandbox dışında `PYTHONHASHSEED`
  sabitlenmemişse sonuçlar koşudan koşuya değişebilir.

### Ayrıştırıcı

- `#` iddialarda yasak: Python tokenizer'ı satırın kalanını yorum sayar (`2*x ### …` → `2*x`).
- Çıplak `open(` yasak ama `Interval.open(1, oo)` serbest.
- LaTeX dalı örtük çarpma yapar (`\frac{zzz}{2}` → `z*z*z/2`). Bu yüzden LaTeX sonucundaki her
  serbest sembolün tanımlı olması şart.
- `5π/6` gibi rakam + unicode sembol biçiminde çarpım açıkça yazılır; genel örtük çarpma kapalı.

### Lean ve Mathlib

- **Junk değerler** ve `first`/`done` tuzağı: §3 karar 12 ve §4.
- Mathlib türev kombinatörleri noktasal işlem kullanır (`f * g`); kapanışta `Pi.*_apply` ile
  köprülenir.
- `tests/test_f5_lean.py` içindeki Lean gerektiren testler (`_lean()` yardımcısını çağıranlar)
  Lean yoksa **sessizce atlanır**; yazıcı testleri çevrimdışı koşar. Lean'e dokunan bir
  değişiklikten sonra `pytest -rs` ile atlanan sayısına bakın (bugün 1: `test_f5_lean.py:66`,
  "statement out of scope", beklenen) ve `harness.run_lean`'i ayrıca koşturun.

### Windows ve araçlar

- Bash aracı Git Bash'tir. **Heredoc `\\` karakterini çökertir**; ters eğik çizgi içeren Python'u
  Write aracıyla dosyaya yazıp öyle çalıştırın.
- Sandbox kullanan her probe gerçek bir dosyada ve `if __name__ == "__main__":` içinde olmalı
  (spawn).
- Scratchpad yolu uzun olduğu için MAX_PATH'e takılabilir; geçici dosya adlarını kısa tutun.
- `ctypes.windll` çağrılarında `restype`/`argtypes` verilmezse tutamaçlar 32 bit'e kırpılır
  (§6.4). Özel `ctypes.WinDLL(..., use_last_error=True)` örneği ve açık prototip kullanın;
  paylaşılan `ctypes.windll` üzerindeki prototipleri değiştirmeyin.
- Python'un `Path.write_text`'i Windows'ta satır sonlarını CRLF'e çevirir (`newline=""` verilmezse). `core.autocrlf=true` olduğu
  için git commit'te normalleştirir, diff'te görünmez; yine de dosyaları Edit aracıyla düzenlemek
  satır sonlarını korur.
- `PYTHONPATH` Windows Python'unda `;` ile ayrılır (`PYTHONPATH=".;src"`), `:` ile değil.
- Bu makinede git kimliği ayarlı değil; commit komut başına kimlikle yapılır (§10).

### Depo ve ölçüm

- **Ana dal `master`, `main` değil.** Bazı araçlar varsayılan olarak `main` varsayar.
- `reports/*.json` git-ignore'lu. `check.py` kapıları bu yerel JSON'lardan okur; temiz bir
  klonda önce harness koşmalıdır.
- `reports/check_full.log`'u `check.py --full` kendisi yazar; elle yönlendirme gerekmez. Koşu
  başında dosya sıfırlanır, yarıda kalan koşu yarım günlük bırakır.
- `llm_cache/` git'te izleniyor (145 dosya, `828fb95`'ten beri). İçinde 18–19 Eylül F3
  koşularının gerçek API yanıtları var; `run_f3` varsayılan `auto` modda aynı istekleri ücretsiz
  tekrar oynatır. **Testler buna bağlı değil:** `ScriptedClient` ve `tmp_path` kullanıyorlar.
  DECISIONS §18'deki "testler bunu kullanır" ifadesi yalnız önbellek anlamlarının testine
  (`tests/test_f3_pipeline.py`) karşılık geliyor.
- `check.py --full` ~25–45 dk sürer. Adversaryal tarama tek başına 21–38 dk (23 Eylül'de iki
  koşu: 1245 s ve 2249 s, aynı kodla aynı hız ölçüldüğü için fark makineden); arka planda
  koşturun.
- `soundness_fuzz`'a yeni bir "eşdeğer" varyant eklerken kâhinin kendisinin kesin olduğundan emin
  olun (§4: 30 basamaklı ondalık hatası).
- `DECISIONS.md` §2 ve §3.9 bilerek Faz 1 anlık görüntüsüdür (180 öğe, "LLM yok"); güncel durum
  README ve bu belgededir.

### LLM ve maliyet

- Bir katmanda `except LLMError` yazmak `LLMFatalError`'ı yakalamaz ve yakalamamalı. Faturalama
  hatasını yutan bir kod yazmayın.
- `run_f3`'ü `--max-cost` olmadan gözetimsiz koşturmayın.
- 42 örnek, eşik 9 ve onarım bütçesi 2, Claude'un davranışına bakılarak seçildi. Başka bir modelle
  yalnız mekanik hataları düzeltin; istem metnine ve eşiklere dokunmayın.

---

## 12. Açık sorular

Kullanıcıdan onay ya da girdi bekleyen noktalar:

1. **`denetim-2026-09-20` dalı `master`a birleştirilsin mi?** İçinde iki denetimin tamamı var;
   `master` hâlâ denetim öncesinde.
2. **Commit edilmemiş değişiklikler (§5.3) commit edilsin mi?** Commit yalnız istenirse yapılır.
3. **Anthropic bakiyesi ne zaman ve ne kadar yüklenecek?** F3'ün kalanı için ~10 $, F4 için
   ~15–25 $ tahmini var. *Kısmen cevaplandı (23 Eylül):* F3/F4 bütün lokal iş bitince koşulacak
   (§7).
4. **Gerçek AI çözücü çıktıları nereden gelecek?** Hangi model ya da uygulama, kaç çözüm? Bu adım
   ertelendi.
5. **Uzak depo, CI ve LICENSE:** nerede (GitHub mı), hangi lisansla, kimin hesabında?
6. **`tyt-prob-018` kuralı:** F4 ölçüldükten sonra "sertifika kritiği ezer" kuralı daraltılsın mı?
   Karar ölçüme bağlı.
7. **API anahtarları yenilensin mi?**
8. **Çözücü sembolü adımları (§6.2):** bu sınır kabul mü, yoksa yapısal formata sembol tanımı
   eklensin mi?
9. **İsteğe bağlı Lean şablonları** (`domain_of`, `simplify_expression`, `count_solutions`)
   istenir mi?
10. **Başka sağlayıcıyla ölçüm** (GPT/Gemini, `set_client_override` ile) istenir mi? Ölçüm
    sonuçları o konfigürasyona özgü kalır.
11. **Uygulamanın adı ve ayrıntıları** (§1): ne depoda ne şartnamede geçiyor.
12. **Tek seferlik betikler** (§6.8): tutulsun mu, silinsin mi, `scripts/dev/` altına mı taşınsın?
13. **`count_real_roots` içindeki ölü `nsimplify` dalı** (§6.8): kaldırılsın mı (ulaşılamıyor ama
    §3 karar 15'e aykırı)?
