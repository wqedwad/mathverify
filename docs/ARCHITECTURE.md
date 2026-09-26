# Mimari

Bu belge katmanların ne yaptığını, hangi yetkiye sahip olduğunu ve neden öyle tasarlandığını
anlatır. Sayılar [reports/](../reports/) altındaki üretilmiş raporlardan gelir; hiçbiri tahmin
değildir.

## Akış

```
soru (TR) + çözüm
   │
   ├─ L0 normalize/     Türkçe sayı biçimi, derece/yüzde/unicode, görünmez karakter temizliği,
   │                    beyaz listeli ifade ayrıştırma, konu sınıflandırıcı
   ├─ L1 ir / extract/  Problem IR. Elle yazılabilir (yol a) veya LLM ile çıkarılır (F3):
   │                    çıkarım → deterministik doğrulama → iki aileli round-trip denetimi
   │                    → sınırlı onarım döngüsü. Kabul edilmezse UNKNOWN.
   ├─ intake/           çözüm: yapısal format (yol a) veya serbest metin (yol b: LLM yeniden
   │                    yapılandırma + deterministik cevap çıkarıcıyla çapraz kontrol)
   ├─ L3 certify/       13 sertifika modülü — iddiayı sınar, cevabı üretmez     [hard, primary]
   ├─ L6 steps/         deterministik adım reddedici: yalnız somut karşı örnekle  [hard, veto]
   ├─ mc.consistency / sanity                                                    [hard, veto]
   ├─ L4 resolve/       çapraz aile yeniden çözüm                                [soft]
   ├─ L5 meta/          metamorfik yöntem testi                                  [soft]
   ├─ L6' critic/       çapraz aile kritik + meta-doğrulama                      [soft]
   ├─ L7 formal/        Lean 4 + Mathlib, yalnız pozitif kanıt                   [hard, primary]
   └─ L8 fuse/          veto + noisy-OR + abstain (+ opsiyonel kalibrasyon)
                        → VerificationResult(verdict, confidence, first_bad_step, layers,
                                             decision_trace, versions, flags)
```

## Yetki tablosu (handoff §4.1, §11/16)

| Katman | Verdict üretebilir mi | Neden |
|---|---|---|
| `certify.*` (primary) | **Evet** — pass → CORRECT, fail → INCORRECT | İddiayı deterministik olarak sınar; kanıt üretir |
| `formal.lean` | **Evet** — yalnız pass | Lean çekirdeği + aksiyom denetimi; ispat yanlış teoremi doğrulayamaz |
| `steps.refute` | Yalnız INCORRECT (veto) | Somut karşı örnek bir çürütmedir; kanıtlayamamak kanıt değildir |
| `mc.consistency`, `sanity` | Yalnız INCORRECT (veto) | İç tutarsızlık |
| `resolve` (L4) | **Hayır** | Üreten hesap; çözücünün hata modlarını miras alır |
| `meta` (L5) | **Hayır** | Yöntem sinyali, cevap kanıtı değil |
| `critic` (L6') | **Hayır** — CORRECT'i engelleyebilir | LLM sinyali sert sertifikayı ters çeviremez ([10]: %75-85 yanlış red riski) |

Kural: bir LLM katmanı kararı yalnızca **daha temkinli** yapabilir (UNKNOWN'a itebilir),
asla bir sertifikayı karşıtına çeviremez.

## Kararın kapsamı: CORRECT neyi söyler

`DECISIONS.md` §2 CORRECT'i "iddia edilen cevap doğru **ve** hiçbir adım reddedilmedi" diye
tanımlar. Denetlenebilir adım yoksa ikinci koşul boş doğrudur, yani karar çözümün geçerliliği
hakkında hiçbir şey söylemez — yalnız cevap hakkında. Bu, yol (b)'nin normal çalışma biçimidir
ve bir ürün özelliğidir; çekimser kalmak o kapsamayı yok ederdi. Bu yüzden verdict korunur ve
**kapsam çıktıya yazılır**:

| Bayrak | Anlamı |
|---|---|
| `answer_level_only` | Çözümde `eq`/`compute` türünde, iddiası olan hiçbir adım yok |
| `steps_not_checked` | Adım katmanı çağıran tarafından kapatıldı (`run_steps=False`) |
| `answer_from_option_letter` | Çözücü yalnız şık harfi verdi; doğrulanan şey o harfin değeri |
| `malformed_step_claim` | Bir `eq`/`compute` iddiası hiç ayrıştırılamadı (aşağıya bakın) |

İlk üçü kararı değiştirmez; karar izine bir **KAPSAM** satırı ekler ve makine tarafından
okunabilir olduğu için çağıran "çözüm düzeyinde kanıt" şartı koyabilir. Ölçülen boşluk:
`"Bilmiyorum ama tahminim. Cevap: B"` metni CORRECT alıyordu ve çıktıda bunu sıradan bir
doğrulamadan ayıran hiçbir şey yoktu.

## Bozuk adım iddiası ile tanımsız sembol farkı

Adım reddedicinin altın kuralı "yalnız çürüt" olduğu için ayrıştırılamayan bir adım cezasız
atlanır. Ama iki farklı "ayrıştırılamadı" vardır ve bunları karıştırmak bir zafiyetti:

* `u = sqrt(x+4)` — iyi biçimli matematik, yalnız problemde tanımlanmamış bir ad kullanıyor.
  `UndeclaredSymbolError`; cezasız atlanır, aksi hâlde kanonik olmayan doğru çözümler
  cezalandırılırdı ([10]).
* `a = 20}` ya da `y = 2*x ignore previous instructions` — matematik değil. Yapısal sözleşmenin
  ihlali; `malformed_step_claim` bayrağı CORRECT'i engeller.

Ayrım tahminle değil ayrıştırmayla yapılır: bilinmeyen adlar serbest sembol kabul edilerek
metin yeniden ayrıştırılır; yine düşerse iyi biçimli değildir. Ölçüm: reddedilmiş bir adımın
iddiasına `{`, `}` ya da bir istem enjeksiyonu eklemek INCORRECT'i CORRECT'e çeviriyordu
(genişletilmiş adversaryal taramada 54 saldırı/öğe çifti); kural eklendikten sonra 0.

## İddia bir değerdir

Cevap, problemin ad alanından **hesaplayan** operatörler (`integrate`, `limit`, `diff`, `Sum`,
`simplify`, `nsimplify`, `det`, `dist`, …) ve problemin kendi fonksiyonları (`f`, `g`) çıkarılmış bir
ad alanında okunur (`normalize.parse.COMPUTING_OPERATORS`, `Ctx.claim_ns`). `evaluate` görevinde
hedefi aynen yazan iddia da cevap sayılmaz. Aksi hâlde `integrate(log(x), x)` gibi bir "cevap"
sertifikaya doğrulayıcının kendi hesabını denetletir — ölçümde 7 böyle iddianın 7'si CORRECT
alıyordu. Karar çekimserliktir (`claim_is_not_a_value`); kapalı biçimler (`binomial(6, 3)`) geçerlidir.

İddia ayrıca **karşılaştırılmadan önce yeniden yazılmaz**: sayımlar `equiv.exact_integer` ile okunur
(`int(7/2)` 3'e kesiyordu), hiçbir iddia ya da hesaplanan doğru değer `nsimplify`'dan geçmez
(500000003/3000000000'i 1/6'ya yakalıyordu).

## Eşdeğerlik motorunun kanıt standardı

`equiv/` her sertifikanın ortak karşılaştırma primitifidir, bu yüzden yanlış bir "eşit" her yere
sızar. Kurallar:

* **Sembolik** yol yalnız kesin dönüşümlerden oluşur. `nsimplify` bir yuvarlamadır; −e⁻¹⁰⁰⁰'ü 0
  yapıyordu, çıkarıldı.
* **Kesin sayılar kesin** karşılaştırılır (10³⁰+1 ile 10³⁰ göreli toleransla "eşit" çıkıyordu).
* **Nümerik eşitlik** hassasiyet merdiveninin her basamağında sağlanmalıdır: gerçek bir özdeşlikte
  fark hassasiyetle küçülür, gerçek bir küçük fark küçülmez (e^{π√163} ile 262537412640768744
  30 basamakta eşit, 50 basamakta değil).
* **Rastgele noktalarda** iki tarafı ayrı değerlendirip çıkarmak çalışma hassasiyetinin altındaki
  farkı göremez; farkın kendisi SymPy'nin uyarlamalı `evalf`'iyle değerlendirilir. Gerçek bir sıfır
  `0` ya da anlamlı biti olmayan `0.e-167` verir, gerçek bir fark ~100 bit taşır.
* **Math-Verify** ikinci görüştür, kanıta yazılır, tek başına karar vermez.

Bu kuralların her biri `harness/soundness_fuzz.py`'nin ya da diferansiyel bir sondanın bulduğu somut
bir yanlış eşitlikten gelir ve `tests/test_equiv.py`'ye bağlıdır.

## Lean'in junk değerleri

Lean/Mathlib her kısmi işlemi tamamlar: `x / 0 = 0`, `Real.sqrt x = 0` (x < 0), `Real.log 0 = 0`,
`Real.log (−x) = Real.log x`, `Real.tan (π/2) = 0` ve integrallenemeyen fonksiyonun aralık integrali
0'dır. Böyle bir değere dokunan ifade gerçek matematik hakkında değildir ama **ispatlanabilir** —
aksiyom, `sorry`, vakum ve kullanılmayan hipotez denetimleri bunu göremez, çünkü ispatlar junk
ifadelerin gerçek ispatlarıdır. Ölçüm: "tan(π/2) = 0" `--lean` ile bütün doğrulayıcıdan CORRECT (0.995)
çıkıyordu.

Kural (`formal/statement.py`, bölüm "junk values"):

* **Kapalı** kısmi işlem (değişkensiz) yazıcıda karara bağlanır: tanımsız ya da karar verilemezse
  ifade yok. Böylece iddialar, sınırlar, kökler, matris girdileri kendiliğinden kapsanır.
* **Açık** olanlar şablonun işidir: `evaluate`'te koruma hipotezi olur (verilerle çelişirse vakum
  sondası ispatı reddeder); integral/ekstremum/seri toplamında nicelenen bölgenin tamamında tanımlı
  olduğu kanıtlanır; noktada türevde nokta tanım kümesinin *içinde* olmalıdır (√x'in −1'de türevi
  Lean'de 0'dır); fonksiyonel türevde gerçek tanım kümesi boş olmamalıdır; tekrarlama bağıntısında ve
  eğri denklemlerinde kısmi işlem kapsam dışıdır.
* 23 Eylül'de eklenen üç şablon aynı kurala uyar, her biri ölçülmüş bir tehlikeye karşı:
  * `domain_of` ifadesi fonksiyonu hiç içermez, yalnız tanımlılık koşullarını: `∀ x, (koşullar) ↔
    x ∈ S`. İçinde kısmi işlem olan bir koşul (`log(√x − 1)`) kapsam dışıdır.
  * `simplify_expression`'da korumalar yalnız problemin ifadesinden gelir; iddianın kendi
    tanımlılığı **hedefte** kanıtlanır. Aksi hâlde `∀ x, x = x²/x` Lean'de doğrudur (0/0 = 0).
    Tanım kümesi hiçbir yerde iç noktası olmayan ifade (`√(−x²−1)`) reddedilir; aksi hâlde
    `∀ x, −x²−1 ≥ 0 → √(−x²−1) = 0` boş yere ispatlanır.
  * `count_solutions`'da ℤ bölmesi ve `Mod` reddedilir (Lean'in ℤ `/`'ı taban bölmesi,
    `x / 0 = 0`; `%` Öklidçi). Kutunun bütün çözümleri içerdiği de Lean'de kanıtlanır, yani IR'daki
    sınırlara güvenilmez.
  Parantez içindeki naif ifadelerin üçü de Lean'de gerçekten ispatlanıyor
  (`test_the_naive_statements_these_templates_avoid_are_provable`).
* Tanımlılık `certify.domain.definedness_conditions`'tan gelir — deterministik katmanla aynı tanım.
* Vakum sondası ispat aramasından zayıf olamaz: ispat merdiveninin kombinasyonlarını ve her `≠`
  hipotezi için yasakladığı eşitliği kanıtlama denemesini içerir, ve her alternatif `done` ile kapanır.

`harness/run_lean.py` her koşuda 17 junk-value sondasını yeniden dener (23 Eylül'e kadar 12); bir
tanesinin sertifika alması kapıyı düşürür.
**Düzeltme (25 Eylül 2026):** sonda sayısı 33. 25 Eylül formal denetiminin aileleri eklendi: kapalı
hedefte ℕ bölmesi, güvenli alt küme dışında Mod, özyinelemede ℕ çıkarması, düşürülen kısıt
(`domain_of_discourse`, değişken kısıtı, ikinci veri), karmaşık değişken, çelişik veriler,
sadeleştiren ayrıştırma ve iddianın junk bölgesi (DECISIONS §55). Hipotezli bir ifade artık yalnız
tanıkla kanıtlanan `∃ vars, h1 ∧ … ∧ hn` ile temizdir; Mod yalnız pozitif tam sayı sabit bölen ve tam
sayı bölünende basılır.

## Tanımlılık, ifadenin yazıldığı biçimden okunur

SymPy ayrıştırırken ifadeyi kendiliğinden sadeleştirir: `x/x` → 1, `√x²` (`sqrt(x)**2`) → x,
`x²/x` → x, `log x − log x` → 0. Tanımsız noktalar böylece daha hiçbir koşul okunmadan kaybolur.
23 Eylül'de ölçüldü: "`x/x`'in tanım kümesi ℝ", "`x²/x = 0`'ın kökü 0", "`(√x)² = −1`'in kökü −1",
"`x/x > 0` bütün ℝ'de" ve "x = 0'da `x/x` = 1" CORRECT (0.99–0.995) alıyordu; ilk dördünün doğru
cevabı da INCORRECT alıyordu. Aynı tuzak türevde ("`(x²/x)'` 0'da 1"), ekstremumda ("[−1, 1]'de
`x/x − x²`'nin maksimumu 1", hiç ulaşılmıyor) ve seride ("Σ_{k=−1}^{1} k/k = 3") de vardı.

Kural: problemin ifadeleri, yalnız tanımlılık için, sadeleştirme kapalıyken bir kez daha okunur
(`normalize.parse.parse_as_written`, `certify.domain.written_definedness`). Koşullar iki yere girer:
`Ctx.domain_for` (tek değişkenli) ve `Ctx.var_constraints` (her sayıda değişken). Böylece denklem,
eşitsizlik, tanım kümesi, `evaluate`, sayım ve adım reddedici aynı tanımı kullanır. Türev, ekstremum
ve seri kendi bölgesini (nokta, aralık, indis aralığı) `written_undefined_in` ile sınar; tanımsız bir
nokta varsa karar vermez. `limit` bilerek dışarıdadır: lim x→0 x/x = 1 doğrudur, yaklaşılan nokta
çoğu zaman tam da tanımsız noktadır. Kaldırılabilir nokta integrali değiştirmez, integral de
dışarıdadır. Teste bağlı: `tests/test_written_definedness.py`.

## Neden IR'dan deterministik Lean ifadesi

[5] ölçümü: otomatik formalizasyonda ifadelerin %89.5'i derleniyor ama yalnız %60.5'i sadık.
Bu %29 puanlık boşluk L7'nin bütün riskidir. Biz ifadeyi modele yazdırmıyoruz: zaten iki aileli
round-trip denetiminden geçmiş IR'dan şablonla üretiyoruz, yazıcı tam çeviremediği hiçbir şeyi
tahmin etmiyor (`LeanPrintError` → L7 çalışmıyor). Modele yalnız **ispat** kalıyor ve bir ispat
yanlış bir ifadeyi doğru yapamaz.

Bu tasarımın kendisi üç sadakat hatası ortaya çıkardı; üçü de düzeltildi ve teste bağlandı:

1. **CAS hedefi önceden hesaplıyordu.** `gcd(84,120) + lcm(4,6)` SymPy'de 24'e katlanıyor,
   teorem `24 = 24` tautolojisine dönüyordu. Artık ifadeler yapısal (değerlendirilmeden)
   ayrıştırılıyor ve kalan tautolojiler `is_trivial` ile reddediliyor.
2. **Korumalı iff, tanım dışı kökü göremiyordu.** `çözüm kümesi {3}` iddiası, 3 tanım kümesi
   dışındayken `denklem ↔ x=3` biçiminde doğru çıkıyordu (iki taraf da yanlış). Artık ifade her
   kökün koşulları **ve** denklemi sağladığını da iddia ediyor.
3. **Aynı boşluk eşitsizlikte.** Yalnız uç noktada hatalı bir iddia (`x ≤ -2` vs `x < -2`,
   -2 tanımsız) korumalı iff ile ayırt edilemiyordu. Artık "iddia edilen her nokta tanım
   kümesindedir" koşulu da ifadenin parçası.

### Analiz: üreten hesap ile kontrol eden hesabın ayrımı

Türev, ilkel fonksiyon ve belirli integral iddialarının üçü de tek bir Lean nesnesine indiriliyor:
`HasDerivAt f v a`. Bu seçim bilinçli — `deriv f a = v` fonksiyon türevlenebilir *değilken* de
boş yere doğru çıkar ve yanlış gerekçeyle sertifika üretirdi; `HasDerivAt` türevlenebilirliği de
iddia ediyor.

| Görev | Teorem |
|---|---|
| `derivative` (noktada) | `HasDerivAt (fun t => f t) (iddia) a` |
| `derivative` (fonksiyon) | `∀ x, <tekillik koşulları> → HasDerivAt (fun t => f t) (iddia x) x` |
| `antiderivative` | `∀ x, <tekillik koşulları> → HasDerivAt (fun t => F t) (f x) x` |
| `definite_integral` | `∫ x in a..b, f x = iddia` (temel teorem taktiğiyle) |

Belirli integralde Mathlib'in hazır lemmaları polinom, `sin`, `cos`, `exp`, `1/x` gibi tekil
şekilleri kapatıyor ama `x·eˣ` gibi çarpımları kapatmıyor. Orada analizin temel teoremini
kullanıyoruz: SymPy bir ilkel fonksiyon **öneriyor**, Lean hem onun gerçekten ilkel olduğunu hem
de uç nokta farkının iddiaya eşit olduğunu bağımsız kanıtlıyor.

Üç nokta bu katmanı güvenli tutuyor:

- **Önerilen ilkel fonksiyon teoremin ifadesine girmiyor**, yalnız taktiğe giriyor. Yanlış bir
  öneri ispatın düşmesine yol açar, asla yanlış bir sertifikaya değil.
- **Türev ispatı SymPy'den alınmıyor, aynı ifade ağacından terim terim derleniyor**
  (`_hasderiv_proof`): `hasDerivAt_id'`, `hasDerivAt_const`, `HasDerivAt.add/mul/pow/const_mul`,
  `Real.hasDerivAt_exp/sin/cos/log` ve zincir kuralı sürümleri. Türevin **değeri hiç yazılmıyor**:
  Lean terimden kendisi çıkarıyor, geriye yalnız "iddia edilen değer buna eşit mi" kalıyor. İddia
  türev ispatının içine hiç girmiyor, yani ispatı kendi lehine yönlendiremiyor.
- **Yan koşullar varsayılmıyor.** `Real.log`'un türevi için gereken `x ≠ 0` ayrı bir Lean hedefi
  olarak yazılıyor (`have hs0 : (x) ≠ 0 := by …`) ve Lean onu da kanıtlıyor.

İfadedeki tekillik koşulları (`x ≠ 0`) SymPy'nin `singularities` kümesinden, yani **problemin
kendi ifadelerinden** geliyor; iddiadan değil. Böylece yanlış bir iddia, sağlaması gereken
teoremi daraltamıyor. SymPy koşulu kesin belirleyemezse şablon ifade üretmiyor.

Kapsam dışı iki sınıf bilerek reddediliyor: mutlak değer/tam değer içeren parçalı integrandlar
(`build_statement` → None) ve `∫₀¹ ln x/√x` gibi **has olmayan** integraller — ilkel fonksiyon
kapalı aralığın ucunda türevlenebilir olmadığı için temel teorem uygulanamaz. Bu üç görevin
30 kaleminde ölçüm: **13 kanıt, 0 yanlış pozitif**; kapsam içindeki doğru cevapların tamamı
kanıtlandı, kalan kalemlerde katman çekimser kalıyor.

### Sayma: formülü değil, sayılan nesneyi doğrula

Kombinatorik saymalarda kolay ama değersiz yol `Nat.factorial 5 = 120` yazmaktır: bu teorem
yalnız *bizim formül seçimimizi* onaylar, yani üreten hesabın kendisini tekrar eder. Bunun yerine
ifade, Lean'in nesneyi kendi tanımı üzerinden kuruluyor:

| Soru | Teorem |
|---|---|
| n nesnenin tüm dizilişleri | `Fintype.card (Equiv.Perm (Fin n)) = iddia` |
| n elemandan k'lı seçim | `((Finset.univ : Finset (Fin n)).powersetCard k).card = iddia` |
| n elemandan k'lı sıralı seçim | `Fintype.card (Fin k ↪ Fin n) = iddia` |

11 kalemde 8 kanıt, 0 yanlış pozitif — doğru cevapların tamamı kanıtlandı, üç yanlış cevabın
üçü de reddedildi.

### Tekrarlama bağıntısı: veriyi hipotez yap, hesabı Lean yapsın

`a(n) = a(n-1) + 2a(n-2)`, `a(1)=1`, `a(2)=3` iken `a(6) = 43` iddiası şu teoreme dönüşüyor:

```lean
theorem mv_claim (a : ℕ → ℝ) (h1 : a 1 = 1) (h2 : a 2 = 3)
    (h3 : ∀ n : ℕ, 3 ≤ n → a n = (a (n - 1) + (2 * a (n - 2)))) : a 6 = 43
```

Ara değerlerin hiçbirini biz vermiyoruz; taktik yalnız `h3`'ü 3'ten 6'ya kadar örnekliyor ve
aritmetiği Lean yapıyor. Bağıntının sağ tarafı yazıcıdan geçiyor: `a (n-1)` gibi uygulamalar
geçici sembollere çevrilip kesin yazıcıyla basılıyor, sonra geri konuyor — yani yazıcı yine
çeviremediği hiçbir şeyi tahmin etmiyor. Hipotezler var olduğu için **vakum denetimi** ve
**kullanılmayan hipotez denetimi** de bu ifadede çalışıyor.

**Olasılık kalemleri bilerek kapsam dışı.** Onlarda olay yüklemi (`sum(t) == 7` gibi) Lean'e
çevrilmek zorunda ve sadakat riski tam orada: zar yüzlerini `Fin 6` ile kodlarken bir birim
kayması teoremi sessizce başka bir soruya dönüştürebilir. Katman ifade üretmeyip çekimser
kalıyor; bu kalemler zaten deterministik katmanlarca karara bağlanıyor. Aynı gerekçeyle
`limit` kalemleri de dışarıda: her limit biçimi (kaldırılabilir tekillik, sonsuzda limit, tek
taraflı limit, `(1+1/n)ⁿ`) ayrı bir Mathlib kalıbı istiyor ve yarısı için sadık bir ifade
"DNE"nin olumsuzlamasını gerektiriyor; L7 ise yalnız pozitif kanıt üretiyor.

## Determinizm

- Tüm CAS/z3 çağrıları kalıcı worker süreçte, sert timeout'lu; worker'da `PYTHONHASHSEED=0`
  (ölçüm: `is_subset` sonucu hash tohumuna bağlı değişiyor).
- Rastgele nokta testleri sabit seed, kesin rasyonel örnekleme.
- LLM çağrıları kayıt/tekrar önbelleğinde: aynı istek aynı yanıtı verir; `MATHVERIFY_LLM_CACHE=replay`
  ağa hiç çıkmaz.
- Sürümler her `VerificationResult.versions` içine yazılır.

## Anahtar izolasyonu (D2)

`ProblemIR` şemasında cevap alanı yoktur; anahtar benzeri her alan adı özyinelemeli taranıp
`LeakageError` ile reddedilir. LLM çıkarıcının ürettiği bilinmeyen üst alanlar dönüştürücü
tarafından zaten kopyalanmaz; `task.params` içine sızan bir anahtar ise yapısal taramada
yakalanıp IR tümüyle reddedilir. Harness etiketleri ayrı tutar ve her koşuda sızma testi yapar
(aynı öğeyi iki kez koşturup verdict + confidence'ın birebir aynı olduğunu doğrular).

## Ölçüm disiplini

- Değerlendirme seti dört hücreli (§9): A kanonik doğru, B kanonik olmayan doğru, C yanlış
  cevap, D doğru cevap + geçersiz adım. Oranlar tam olarak %30/%25/%30/%15.
- Metriklerde accuracy tek başına raporlanmaz; pozitif/negatif precision, kapsama, hücre ve
  konu kırılımı, B'de yanlış red, D'de tespit, adım lokalizasyonu ayrı ayrı verilir.
- Kalibrasyon train/val/test bölmesiyle yapılır (id hash'inden, konumdan değil) ve test
  bölmesi hiçbir uyumda kullanılmaz.
- Adversaryal testte anlamı koruyan ve anlamı değiştiren saldırılar ayrı sayılır; UNKNOWN'a
  düşmek "sağlamlık kaybı" olarak raporlanır ama yanlış karar sayılmaz.
- Adversaryal tarama **üç yüzeyi** ayrı ayrı ölçer ve üçünün de var olması bir kapıdır:
  cevap yükü, **şık harfi korunarak** (çözümlerin 257/260'ı bir harf taşıyor ve eski tarama
  hepsinde harfi siliyordu) ve **adım iddiaları**. Tek yüzeyde %0 başarı, ölçülen şeyin dar
  olduğunu gizleyebilir.
- Router'da tanımlı her görev türünün sette öğesi olması bir kapıdır. `count_solutions`,
  `domain_of` ve `simplify_expression` modülleri yazılıydı ve birim testleri vardı ama sette
  tek öğeleri yoktu; raporlanan precision onlar hakkında hiçbir şey söylemiyordu.
- Yol (b) sadakati **iki** sayı olarak raporlanır: şık harfi üzerinden sayılanlar ve cevabın
  kendisinin karşılaştırıldığı öğeler. Tek sayı yanıltıcıydı: 260 öğenin 245'i yalnız harf
  eşleştiği için "sadık" sayılıyordu ve bunların 244'ünde hiçbir yük kurtarılmamıştı.
- L5'in **uygulanabilirlik tavanı** modelsiz ölçülür ve raporlanır. L5 D hücresini yakalamak
  için vardır ama `perturb_ir` yalnız denklem verili `evaluate` görevlerine uygulanır; bu bir
  bütçe değil kapsam sınırıdır ve yarım kalmış bir ölçümün bütçe sorunu sanılmasını engeller.
