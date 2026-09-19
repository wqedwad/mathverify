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
