# Kalite: bu tür bir doğrulayıcı nasıl iyi yapılır

Bu belge, 23 Eylül 2026'daki ikinci denetimden önce yapılan literatür taramasının özetidir ve her
ilkenin bu projede **hangi mekanizmaya** ve **hangi ölçüme/kapıya** karşılık geldiğini gösterir. Bir
ilkenin karşılığı yoksa o bir açık demektir; bu yüzden tablo aynı zamanda bir denetim listesidir.

## 1. Literatürün söyledikleri

**Doğru cevap yeterli değildir.** Modeller sıkça doğru cevaba bozuk akıl yürütmeyle ulaşır; yalnız
sonuca bakan doğrulama bunu ödüllendirir ([Right Is Not Enough](https://arxiv.org/pdf/2506.06877)).
Süreç doğrulaması "ilk hatalı adımı bul" görevi olarak ölçülür
([ProcessBench](https://www.alphaxiv.org/abs/2412.06559)) ve zorluk artınca en iyi doğrulayıcılar bile
çöker: 78.3 → 37.3 ([Hard2Verify](https://arxiv.org/html/2510.13744v1)).

**Adım doğrulayıcıları şablona duyarlıdır.** Aynı matematiği kanonik olmayan biçimde yazmak (iki tarafa
terim eklemek, taraf değiştirmek, sabitle çarpmak) LLM adım doğrulayıcılarında %75–85 yanlış red üretir;
hata lokalizasyonu %95'ten %14–24'e düşer; çoğunluk oylaması sistematik hatayı büyütür
([Beyond the Answer Key](https://arxiv.org/html/2608.28725)).

**Karamsar doğrulama.** Bir çözümü, paralel doğrulayıcılardan herhangi biri kusur bulursa reddetmek
basit ve etkilidir ([Pessimistic Verification](https://arxiv.org/abs/2511.21522)). Bunun karşılığı
burada sert vetodur — ama veto yalnız somut kanıttan (karşı örnek) gelir, aksi hâlde şablon
duyarlılığı geri döner.

**Sembolik eşitlik yanlış negatif verir ama yanlış pozitif vermez; nümerik eşitlik tersidir**
([TinyV](https://arxiv.org/pdf/2505.14625)). Yani sayısal bir "eşit" kanıt değildir; ancak hassasiyet
arttıkça farkın küçülmesiyle desteklenirse güvenilir olur.

**Formal kanıt, ifadesi kadar iyidir.** Lean benchmark'larının denetimi 398 mekanik olarak kanıtlanmış
kusur buldu: karşı örnekler, boş (vacuous) teoremler, eksik hipotezler — ve Lean'e özgü tehlikeler:
sıfıra bölme `x/0 = 0`, ℕ çıkarmasının kırpılması, `Real.sqrt`/`Real.log`'un tanım dışı "junk"
değerleri ([Faults in Our Formal Benchmarking](https://arxiv.org/html/2606.29493v1)). Otomatik
biçimlendirmede derlenen ifadelerin yalnız bir kısmı sadıktır; modeller girdideki hataları sessizce
"onarır" ([Proof Autoformalization in Lean 4](https://www.alphaxiv.org/abs/2606.14867)).

**Doğrulayıcının kendisi test edilmelidir.** Program doğrulayıcılarını sınamanın yerleşik yolu
metamorfik testtir (eşdeğer girdiler eşit çıktı vermeli) ve diferansiyel testtir (bağımsız bir kâhin her
çıktıyı çapraz denetler) ([Robustness Testing of Intermediate Verifiers](https://arxiv.org/pdf/1805.03296)).
Benchmark'ın kendisi de denetlenmelidir: veri kusurları puanları hem şişirebilir hem düşürebilir.

**Çekimserlik birinci sınıf bir çıktıdır.** Seçici tahmin bir risk–kapsama problemidir; kabul edilen
alt kümede hatayı en aza indirmek için belirsizlikte çekimser kalınır
([Prover–Verifier Deliberation](https://arxiv.org/html/2605.25133)).

## 2. İlke → mekanizma → ölçüm

| İlke | Bu projede | Ölçüm / kapı |
|---|---|---|
| Cevap anahtarı hatta girmez | `FORBIDDEN_KEYS`, yapısal tarama | Sızma testi (öğe üzerinde mutasyon) |
| Doğrulayıcı cevap üretmez | İddia **değer-yalnız** ad alanında okunur (`COMPUTING_OPERATORS`) | Metamorfik tarama: "cevap olmayan" iddialarda CORRECT = 0 |
| İddia olduğu gibi sınanır | `exact_integer`; `nsimplify`/`int()` yasak | Metamorfik tarama: yanlış varyantta yanlış onay = 0 |
| Yalnız somut karşı örnekle reddet | `steps/` yalnız çürütür | Geçerli adım dönüşümünde yanlış red = 0 |
| Bozuk girdi ≠ kanıtlanamayan adım | `malformed_step_claim` / `UndeclaredSymbolError` ayrımı | Adversaryal: adım yüzeyi |
| Sayısal "eşit" kanıt değildir | Kesin kesirler kesin; eşitlik her hassasiyet basamağında; farkın kendisi değerlendirilir | `tests/test_equiv.py` (10³⁰+1, Ramanujan sabiti, e⁻¹⁰⁰⁰) |
| Math-Verify ikinci görüştür | Tek başına karar vermez | birim testi |
| Formal ifade sadık olmalı | Şablonla, modelsiz; tanımlılık (junk-value) korumaları | Lean FP = 0; junk-value sondası = 0 |
| Kanıt denetlenir | sorry/aksiyom/vakum/kullanılmayan hipotez; her sonda alternatifi `done` ile kapanır | Lean taraması |
| LLM sinyali yalnız temkin katar | yetki tablosu, `_BLOCK_POSITIVE_FLAGS` | F3/F4 birim testleri |
| Kararın kapsamı açık | `answer_level_only`, `KAPSAM:` satırı | birim testi |
| Doğrulayıcı test edilir | `harness/soundness_fuzz.py`, `harness/adversarial.py` (3 yüzey) | `check.py --full` kapıları |
| Benchmark denetlenir | Etiket tutarlılık denetimi; her görev türünün öğesi var | "ölçülmeyen görev türü = yok" |
| Faturalama ölçüm değildir | `LLMFatalError` | F3 birim testleri |

## 3. Bilinen ve bilerek bırakılan sınırlar

* **Çözücünün kendi sembolüyle yazılmış adım** (`u = u² − 6`, `t² = 4t − 3`) denetlenmez: özdeşlik mi
  çözülen denklem mi olduğu belirsizdir ve belirsizken reddetmek geçerli adımları cezalandırır. Adım
  düzeyi taramada kaçırılan bozuk adımların çoğu bu sınıftandır.
* **Doğru ama gerekçesiz adım** (`tyt-prob-018`) deterministik olarak yakalanamaz.
* **Set sentetiktir**; gerçek bir modelin çözüm dağılımında ölçülmedi.
