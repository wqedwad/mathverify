# HANDOFF — mathverify

Bu belge, projeyi hiç görmemiş bir oturumun devralabilmesi için yazıldı. 18–19 Eylül 2026'da
yapılan işin tamamını, ölçülen sonuçları, kararların gerekçelerini, yol boyunca bulunan hataları
ve kalan işi içerir.

**Proje:** `C:\Users\kullanici\mathverify` · yerel git deposu, uzak yok · Python 3.14 · `.venv` yerinde
**Kaynak handoff:** `C:\Users\kullanici\Downloads\fable-handoff-matematik-dogrulama_1.md`
**Son commit:** `53ab97b` · **Durum:** 12/12 kapı geçiyor, 328 test yeşil, çalışma ağacı temiz

---

## 1. Ürün ne yapıyor

Bir matematik sorusu ve bir AI'ın ürettiği çözüm veriliyor. Araç çözümün geçerli olup olmadığına
**üç değerli** karar veriyor: CORRECT / INCORRECT / UNKNOWN.

İki şey bu aracı sıradan bir "cevabı karşılaştır" yaklaşımından ayırıyor:

- **Cevap anahtarı doğrulama hattına hiç girmez.** `ProblemIR` şemasında gold alanı yoktur;
  `FORBIDDEN_KEYS` listesi IR'ın ve çözümün her seviyesinde özyinelemeli taranır ve sızma
  hâlinde `LeakageError` fırlatılır. Etiketler yalnızca harness'te durur.
- **Karar üretilerek değil, kanıtlanarak verilir.** Katmanlar iddiayı sınar; kendi cevabını üretip
  karşılaştırmaz. Çekimserlik birinci sınıf bir sonuçtur, başarısızlık değil.

Girdi iki yoldan gelebilir: uygulamanın kendi çözücüsünün yapısal çıktısı, ya da dış bir serbest
metin çözümü.

---

## 2. Tek komutla doğrulama

```bash
.venv/Scripts/python.exe scripts/check.py --full
```

Testler, deterministik değerlendirme, Lean taraması, adversaryal tarama ve kalibrasyonu koşturur;
her kapının ölçülen sayısını ve hedefini yazar; biri düşerse çıkış kodu 1. Yaklaşık 15 dakika
sürer. Windows'ta `PYTHONUTF8=1` gerekir.

---

## 3. Ölçülen durum (19 Eylül 2026)

| Kapı | Değer | Hedef |
|---|---|---|
| Birim testleri | 328 geçti, 2 atlandı | hepsi geçer |
| Cevap düzeyi pozitif precision | 1.000 | ≥ 0.98 |
| Cevap düzeyi negatif precision | 1.000 | ≥ 0.98 |
| Kapsama | 1.000 | ≥ 0.85 |
| B hücresi yanlış red | 0.000 | < 0.10 |
| Anahtar sızma testi | geçti | zorunlu |
| Çözüm düzeyi pozitif precision | 0.993 (1 FP) | raporlanır |
| D hücresi tespiti | 0.974 (38/39) | raporlanır |
| Lean yanlış pozitif | 0 | 0 |
| Lean sertifika | 107/260 | raporlanır |
| Adversaryal saldırı başarısı | %0.000 (6009 saldırı) | < %2 |

Değerlendirme seti 260 öğe, hücre dağılımı A/B/C/D = %30/25/30/15. A = doğru çözüm, B = doğru ama
kanonik olmayan çözüm, C = yanlış çözüm, D = doğru cevap ama bozuk adım.

Formal katman ayrıntısı: 156 öğe için Lean ifadesi üretilebiliyor, bunların 107'si kanıtlanıp
denetimden geçiyor. Yanlış cevaplı hiçbir öğede kanıt yok.

Raporların tamamı `reports/` altında ve hepsi üretilmiştir, elle yazılmamıştır.

---

## 4. Ne inşa edildi (kronolojik)

| Commit | Ne |
|---|---|
| `7c222fd` | Faz 1: F0 sözleşmeleri, IR, sandbox, §9 değerlendirme seti, iki intake yolu, F1-TYT ve F1-AYT sertifikaları |
| `d5c8ee8` | F2: sentetik geometri nümerik realizasyon, kombinatorik/olasılık, seriler, lineer cebir |
| `828fb95` | F3–F5: LLM ön yüzü, çapraz aile katmanları, kritik, Lean formal katmanı |
| `b768e09` | F5 kapsamı iki katına çıktı, iki şablon sadakat hatası düzeltildi |
| `674b34a` | F6: adversaryal sertleştirme, ölçülmüş kalibrasyon, kapı koşucusu |
| `a94860d` | F7: belirli integral için Lean, temel teorem yoluyla |
| `77cc9d9` | F7: türev ve ilkel fonksiyon şablonları |
| `a9d264f` | F7: sayma ve tekrarlama bağıntısı şablonları |
| `53ab97b` | Denetim: beş kod boşluğu kapatıldı, iki yanlış iddia düzeltildi |

Ölçek: 63 kaynak modülü, 10.855 satır kaynak, 2.712 satır test, 4.127 satır harness/script/set
üreticisi, 745 satır doküman.

### Katman mimarisi

- **certify/** (13 modül) iddiayı sınar: cebir, z3 sözel problem ve teklik, tanım kümesi, sayım,
  analiz, limit, ekstremum, trigonometri, analitik geometri, sentetik geometri, kombinatorik,
  seriler, lineer cebir. Bir `fail` sert delildir, `pass` sert pozitif delildir, `unknown` ağırlık
  taşımaz.
- **steps/** adımları yalnız somut karşı örnekle çürütür. Kanıtlayamadığı adımı cezalandırmaz.
- **formal/** IR'dan deterministik şablonla Lean 4 ifadesi üretir, taktik merdivenini dener,
  hiçbir ispatı denetimden geçmeden kabul etmez.
- **resolve/ meta/ critic/** çapraz aile LLM sinyalleridir; kararı yalnız daha temkinli yapabilirler.
- **fuse/** sert veto artı noisy-OR artı çekimserlik eşikleri.

---

## 5. Bozulmaması gereken ilkeler

Bunlar handoff'un kilitli kararlarından ve ölçümden gelir. Değiştirmeden önce ölçün.

1. **Üreten hesap ile kontrol eden hesap ayrıdır.** SymPy bir ilkel fonksiyon ya da tanık nokta
   *önerebilir*, ama öneri asla teoremin ifadesine girmez, yalnız taktiğe girer. Yanlış öneri
   ispatı düşürür, sertifika üretemez.
2. **Cevap anahtarı yalıtımı yapısaldır.** Gold alanı hiç yoktur. Sızma testi mutasyonu öğenin
   kendisine, harness ayrıştırmasından önce uygular.
3. **Adım reddedici yalnız çürütür.** Doğrulanamayan adım cezalandırılmaz. Aksi hâlde kanonik
   olmayan doğru çözümlerde %75–85 yanlış red görülür.
4. **LLM sinyali sert sertifikayı ters çeviremez.** Yalnız CORRECT'i engelleyebilir.
5. **Lean ifadesi modele yazdırılmaz.** Otomatik formalizasyonda ifadelerin %89,5'i derleniyor ama
   yalnız %60,5'i sadık. Bu boşluk şablonla kapatıldı; yazıcı çeviremediğini tahmin etmez,
   `LeanPrintError` fırlatır ve katman çalışmaz.
6. **Sayma teoremleri Lean'in kendi tanımları üzerinden kurulur.** `Nat.factorial 5 = 120` yazmak
   yalnız bizim formül seçimimizi onaylar; `Fintype.card (Equiv.Perm (Fin 5)) = 120` nesneyi
   doğrular.
7. **Geçerli tek kanıt §9 setinde ölçülmüş precision/recall'dur.** Ölçülmemiş iyileştirme
   iyileştirme sayılmaz.

---

## 6. Yol boyunca bulunan hatalar ve çıkarılan dersler

Bu bölüm belgenin en değerli kısmı: aynı tuzaklara ikinci kez düşmemek için.

### Ortam

- **MSIX sanallaştırılmış scratch dizininde pip/uv/venv çalışmıyor.** Proje bu yüzden
  `C:\Users\kullanici\mathverify` altına taşındı.
- **Windows MAX_PATH.** Scratchpad yolu uzun olduğu için 14 karakterlik dosya adı sınırı aşıyor;
  geçici script adlarını kısa tutun.
- **Heredoc içinden Python yazarken `\n` kaçışları gerçek satır sonuna dönüşebiliyor.** Çok satırlı
  dize üreten yamaları Edit aracıyla yapın, heredoc ile değil.
- **`<stdin>` üzerinden çalıştırılan script'lerde multiprocessing spawn kırılıyor.** Sandbox havuzu
  kullanan probe'ları gerçek bir dosyaya yazıp öyle çalıştırın.

### Determinizm

- **`is_subset` sonucu hash tohumuna bağlı değişiyordu.** ImageSet birleşimlerinde None ile True
  arasında gidip geliyordu. Sandbox worker'larında `PYTHONHASHSEED=0` sabitlendi.
- **Math-Verify Windows'ta her çağrıda süreç açıyor.** Sandbox içinden `timeout_seconds=None` ile
  çağrılıyor.

### Sayısal doğruluk

- **Gauss–Legendre `∫ ln x/√x` üzerinde 5e-3 hata veriyordu.** Yalnız tanh-sinh kullanılıyor ve
  tolerans hata kestiriminden türetiliyor.
- **`lambdify` karmaşık sabitleri 15 basamağa düşürüyordu.** Yerine `sp.N(expr, dps)` ve
  `as_real_imag`.
- **Sabit 1e-12 tolerans yanlış.** Göreli tolerans ve hassasiyet merdiveni kullanılıyor.

### SymPy tuzakları

- **Kayan noktalı örnekleme doğru özdeşlikleri "çürütüyordu".** Kesin rasyonel örnekleme ve
  `evaluate=False` ilişkiler.
- **SymPy varsayımları kısıtları yutuyordu.** Pozitif tanımlı bir sembolde `x > 0` doğrudan True'ya
  katlanıyordu. İlişkiler `evaluate=False` kuruluyor, z3 köprüsü varsayımları yan kısıt olarak
  aynalıyor.
- **`_FUNC` sözlüğüne `sp.sqrt` konmuştu**, o bir fonksiyon, sınıf değil; `isinstance` TypeError
  veriyordu. sqrt `Pow(1/2)` üzerinden işleniyor.
- **`parse_expr(rational=True)` diye bir parametre yok**; `rationalize` dönüşümü kullanılıyor.
- **`sp.evaluate(False)` ayrıştırması `NameError: Add` veriyordu**; yapısal ad alanına
  `Add/Mul/Pow` eklendi.

### Lean ve Mathlib

- **`LEAN_PATH=... exec repl` ortam değişkenini dışa aktarmıyor**, çünkü `exec` özel bir yerleşik.
  Lean Mathlib'i hiç görmüyordu ve `import Mathlib` 13 saniye yerine 3 saniyede dönüyordu. Çözüm
  `lake env <repl>` artı açılışta gerçekten Mathlib yüklendiğini doğrulayan bir sonda.
- **Matris literalleri ℕ olarak elaborate ediliyordu**, `failed to synthesize CommRing ℕ`. Her
  literale tip ataması yapılıyor.
- **`*ᵥ` gösterimi bu araç zincirinde elaborate olmuyor**; açıkça `Matrix.mulVec` yazılıyor.
  `dotProduct` kökte, `Matrix.dotProduct` değil.
- **`rw` listesi her lemma ateşlemezse düşüyor**; standart trigonometrik değerler için
  `simp only [...]` kullanılıyor.
- **`hasDerivAt_id` terimi `id ^ 2 * Real.exp` biçimine düşürüyordu** ve ifadeyle birleşmiyordu;
  `hasDerivAt_id'` lambda ürettiği için onunla değiştirildi.
- **Mathlib türev kombinatörleri fonksiyonlar üzerinde noktasal işlem kullanıyor** (`f * g`), yani
  Lean'in çıkardığı tip bizim lambdamıza yalnız tanımsal olarak eşit. Kapanış taktikleri
  `Pi.*_apply` ile köprüleniyor.
- **`simp` hedefi kapatmadan da "başarılı" olabiliyor**, bu da `first | ... | ...` zincirinde işe
  yarayan alternatifi sessizce eliyordu. Her alternatif `done` ile sarıldı.
- **Türevin değerini elle yazmak kırılgandı**, çünkü SymPy `0^2`yi sadeleştirip eşleşmeyi bozuyordu.
  Artık değer hiç yazılmıyor; Lean terimden kendisi çıkarıyor, geriye yalnız "iddia edilen değer
  buna eşit mi" kalıyor.
- **Yan koşullar satır içi `by` bloğunda ertelenip çözümsüz hedef olarak dışarı sızıyordu.** Ayrı
  `have hs0 : (...) ≠ 0 := by ...` satırlarına çıkarıldı.

### Sadakat hataları (şablonun kendisi yanlış teoremi yazıyordu)

Bunlar Lean taramasının kendisi tarafından bulundu; üçü de düzeltilip teste bağlandı.

1. **CAS hedefi önceden hesaplıyordu.** `gcd(84,120) + lcm(4,6)` SymPy'de 24'e katlanıp teorem
   `24 = 24` tautolojisine dönüyordu. Artık yapısal ayrıştırma var ve kalan tautolojiler
   `is_trivial` ile reddediliyor.
2. **Korumalı iff, tanım dışı kökü göremiyordu.** Çözüm kümesi iddiası, kök tanım kümesi dışındayken
   iki taraf da yanlış olduğu için doğru çıkıyordu. Artık her kökün koşulları ve denklemi
   sağladığı da iddia ediliyor.
3. **Aynı boşluk eşitsizlikte**, yalnız uç noktada hatalı iddialarda.

### Adversaryal taramanın bulduğu iki gerçek zafiyet

1. **Yük temizleyici sondaki matematiği atıyordu**, `12 + 1` tekrar `12`ye dönüyordu, yani saldırgana
   çözücünün hiç vermediği bir cevap için karar kazandırıyordu. Yalnız düzyazı jetonlarını atan
   kural eklendi.
2. **`\boxed{}` ayrıştırıcıya kadar ulaşıp bir kararı çeviriyordu.** Sunum sarmalayıcıları
   ayrıştırmadan önce soyuluyor.

### Son denetimin bulduğu beş boşluk (19 Eylül)

1. **F4 bir kez bile koşmamıştı.** Harness kritik katmanını pipeline'a geçirmiyor, sonucunu
   kaydetmiyor, raporda bölümü yoktu. Artık `--no-l6` bayrağı, öğe başına kayıt ve rapor bölümü var.
2. **Anahtar sızma testinin gücü yoktu.** Mutasyon yalnız yerel bir değişkene uygulanıyor, iki koşu
   birebir aynı argümanlarla yapılıyordu; bu determinizmi kanıtlar, yalıtımı değil. Mutasyon artık
   öğenin kendisine, ayrıştırmadan önce uygulanıyor.
3. **`from mathverify.certify import *` ModuleNotFoundError veriyordu**; `__all__` router kayıt
   anahtarlarını öznitelik adı sanıyordu.
4. **Ölü kod:** `intake.restructure_llm` hâlâ "F3'e ertelendi" diye hata fırlatıyordu.
5. **Ürün boşluğu:** formal katman CLI'dan erişilemiyordu; `verify_cli.py --lean` eklendi.

### Ölçümün "hayır" dediği yer

**Kalibrasyon kapalı gönderildi.** `harness/calibrate.py` log-odds ağırlıkları üretiyor ve eşikleri
tutulan bölmeden seçiyor. Ölçüm: kalibre model kapsamadan 13 öğe götürüyor ve tek yanlış pozitifi
kaldırmıyor, çünkü o öğe tam olarak doğru bir öğenin sinyallerini yayıyor. Altyapı duruyor çünkü
asıl gerekeceği yer yumuşak LLM sinyalleridir. `MATHVERIFY_CALIBRATION=on` ile açılır.

---

## 7. Bilerek kapsam dışı bırakılanlar

Bunlar eksik değil, gerekçeli kararlardır. Gerekçeler `docs/ARCHITECTURE.md` içinde.

- **Olasılık kalemleri Lean'e çevrilmiyor.** Olay yüklemini çevirmek sadakat riski taşıyor: zar
  yüzlerini `Fin 6` ile kodlarken bir birim kayması teoremi sessizce başka bir soruya çevirir.
- **Limitler Lean'e çevrilmiyor.** Her biçim ayrı bir Mathlib kalıbı ister ve yarısı için sadık
  ifade "limit yoktur"un olumsuzlamasını gerektirir; L7 yalnız pozitif kanıt üretir.
- **Sentetik geometri Lean'e çevrilmiyor.**
- **Parçalı integrandlar ve has olmayan integraller** temel teorem uygulanamadığı için dışarıda.
- **İspat türü görevler** (`task.kind = proof`) router'da ertelenmiş olarak tanımlı; doğrulayıcı
  `UNKNOWN` döndürür, asla tahmin etmez.

---

## 8. Bilinen tek açık ve neden kapanmadığı

`tyt-prob-018`: cevabı doğru, ara adımı doğru ama gerekçesiz. "İki denklemi çıkarınca a − b = 2"
deniyor; ifade doğru, gerekçe yanlış. Deterministik reddedici yalnız somut karşı örnekle çürütür,
bu adım öncüllerden çıkarılabilir olduğu için çürütülemez.

**Bunun F4 kritiğiyle kapanacağı varsayılıyordu; kapanmıyor.** L6'daki deterministik çapraz kontrol,
kritiğin işaretlediği adım deterministik olarak doğrulanmışsa raporu iptal ediyor. Sertifika adımın
*iddiasının doğru* olduğunu kanıtlar; kritiğin şikâyeti ise iddianın yanlışlığı değil, öncüllerden
çıkmaması. Çapraz kontrol bu ikisini ayırmıyor.

Kuralı daraltmak, gerekçesiz bir suçlamanın sertifikayı ezmesine kapı açar; handoff'un en çok
uyardığı hata biçimi bu. Karar ölçüme bırakıldı ve bugünkü davranış
`test_a_true_but_unjustified_step_is_still_overruled_by_its_certificate` ile teste bağlandı.

---

## 9. Kalan iş

### Engel 1: Anthropic bakiyesi

F3 ölçümü 218 öğenin 64'ünde tamamlandı, kalanı `Your credit balance is too low` ile düştü.
F4 ise hiç koşmadı. İki anahtar da `.env` içinde ve çalışıyor; eksik olan yalnızca bakiye.
Yükleme `console.anthropic.com` üzerinden Billing bölümünden yapılır. Meta Muse Spark anahtarında
sorun yok.

Kaba maliyet: tam işlenen öğe başına yaklaşık 0,23 dolar ölçüldü. Kalan 154 öğe için yaklaşık 35
dolar, F4'ün 218 öğede ilk koşusu için yaklaşık 20–35 dolar. Üst sınır 70 dolar, ama o ölçümden
sonra prompt caching eklendiği için gerçek rakam daha düşük olmalı.

Bakiye gelince körlemesine tam sete girmeyin. Önce kalibrasyon koşusu yapın:

```bash
.venv/Scripts/python.exe -m harness.run_f3 --limit 10 --workers 3 --max-cost 5
```

Öğe başına gerçek maliyeti ölçün, sonra tam ölçüme geçin. `--max-cost` gözetimsiz bir koşunun
bakiyeyi boşaltmasına karşı vardır; sağlayıcı faturalama hatası verirse koşu zaten ilk hatada durur.

Tam koşu:

```bash
.venv/Scripts/python.exe -m harness.run_f3 --workers 6 --pathb --max-cost 60
```

F4'ün sayıları raporun "L6 kritik + meta-doğrulama (F4)" bölümünde çıkar. Oradaki iki satır kararı
verir: D hücresi tespiti ve doğru çözümde yanlış suçlama. Bir de "sertifikanın iptal ettiği kritik
raporu" satırı, 8. bölümdeki tasarım gerilimini sayıyla gösterir.

### Engel 2: gerçek AI çözücü çıktıları (kullanıcının ertelediği 3. adım)

Değerlendirme setinin tamamı sentetiktir: soruları da çözümleri de biz ürettik. Ölçülen 1.000
precision, gerçek bir modelin ürettiği çözümlere karşı değil, kendi ürettiğimiz çözümlere karşıdır.
Bu farklı bir dağılımdır ve sayıların oraya taşınacağının garantisi yoktur. Bu, kredi ile ilgili
olmayan gerçek bir boşluktur.

### İsteğe bağlı: başka bir sağlayıcıyla ölçüm

Mimari buna hazır: `LLMClient` tek metotlu bir Protocol ve `set_client_override` zaten var. GPT ya
da Gemini'yi mevcut aile adının arkasına koymak tek bir yeni istemci dosyası demektir. İki bağımsız
aile şartı da bozulmaz.

Ama **ölçüm taşınmaz**: başka modelle ölçülen sayılar o konfigürasyonu anlatır, Claude eklendiğinde
her şey yeniden ölçülür. Tek gerçek kalıcı risk **istem kayması**: 42 örnek, eşik 9 ve onarım
bütçesi 2 Claude'un davranışına bakılarak seçildi. Yedek modelle yalnız mekanik hatalar düzeltilmeli,
istem metnine ve eşiklere dokunulmamalı.

---

## 10. Çalıştırma kılavuzu

```bash
.venv/Scripts/python.exe -m pytest tests -q                      # testler
.venv/Scripts/python.exe evalset/build/build_all.py              # 260 öğeyi yeniden üret
.venv/Scripts/python.exe -m harness.run_eval                     # deterministik ölçüm
.venv/Scripts/python.exe -m harness.run_lean --timeout 90        # Lean taraması, modelsiz
.venv/Scripts/python.exe -m harness.adversarial                  # 6009 saldırı
.venv/Scripts/python.exe -m harness.calibrate                    # kalibrasyon raporu
```

Tek bir öğeyi doğrulamak:

```bash
.venv/Scripts/python.exe scripts/verify_cli.py --item evalset/items/tyt-prob-001.json --lean
```

Sürümler sabittir: SymPy 1.14.0, mpmath 1.3.0, z3-solver 5.1.0, math-verify 0.9.0,
Lean 4.34.0 artı Mathlib. Lean kurulumu `docs/LEAN_SETUP.md` içinde.

---

## 11. Okuma sırası

Yeni bir oturum şu sırayla okursa en hızlı devralır:

1. `README.md` — durum tablosu ve ölçülen sayılar
2. `DECISIONS.md` bölüm 1 ve 3 — kilitli kararlar ve gerekçeleri
3. `docs/ARCHITECTURE.md` — katman yetki tablosu ve tasarım gerekçeleri
4. `docs/E1-E10-measurement.md` — §6 sözleşme ölçümleri
5. Bu belgenin 5. ve 6. bölümleri — bozulmaması gereken ilkeler ve bulunan hatalar

Doğrulayıcıya dokunmadan önce `DECISIONS.md` bölüm 3 ve 5 okunmalı. Her değişiklik
`scripts/check.py --full` çıktısını 12/12 bırakmalı. Lean tarafında özellikle: yanlış pozitif
kapısı 0'da kalmalı ve her yeni şablon yalnız doğru cevaplara değil, **yanlış cevaplı öğelere de**
koşturulmalı.

---

## 12. Güvenlik notu

İki API anahtarı yalnızca git'in yok saydığı `.env` dosyasında duruyor.
Git geçmişinde anahtar yok, bu doğrulandı. İş bitince ikisini de yenilemek iyi olur.
