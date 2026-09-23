# HANDOFF — mathverify

Bu belge, projeyi hiç görmemiş bir oturumun devralabilmesi için yazıldı. 18–23 Eylül 2026'da
yapılan işin tamamını, ölçülen sonuçları, kararların gerekçelerini, yol boyunca bulunan hataları
ve kalan işi içerir.

**Son iki denetim için doğrudan [13.](#13-20-eylül-2026-denetimi--bulunan-ve-kapatılan-boşluklar) ve [14. bölüme](#14-23-eylül-2026--ikinci-denetim-önce-literatür-sonra-doğrulayıcının-kendisini-test-etmek)
gidin.** Kalite ilkeleri ve karşılıkları: [docs/QUALITY.md](docs/QUALITY.md).

**Proje:** `C:\Users\kullanici\mathverify` · yerel git deposu, uzak yok · Python 3.14 · `.venv` yerinde
**Kaynak handoff:** `C:\Users\kullanici\Downloads\fable-handoff-matematik-dogrulama_1.md`
**Durum:** 21/21 kapı geçiyor, 400 test yeşil (2 atlandı). 20 ve 23 Eylül denetimleri
`denetim-2026-09-20` dalında; `master`a henüz birleştirilmedi.

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

## 3. Ölçülen durum (23 Eylül 2026)

| Kapı | Değer | Hedef |
|---|---|---|
| Birim testleri | 400 geçti, 2 atlandı | hepsi geçer |
| Cevap düzeyi pozitif precision | 1.000 | ≥ 0.98 |
| Cevap düzeyi negatif precision | 1.000 | ≥ 0.98 |
| Kapsama | 1.000 | ≥ 0.85 |
| B hücresi yanlış red | 0.000 | < 0.10 |
| Anahtar sızma testi | geçti | zorunlu |
| Çözüm düzeyi pozitif precision | 0.994 (1 FP) | raporlanır |
| D hücresi tespiti | 0.976 (41/42) | raporlanır |
| Yol (b): cevabın kendisi karşılaştırılan öğe | 20/20 | raporlanır |
| L5 uygulanabilirlik tavanı | 21/280 (D'de 3/42) | raporlanır |
| Ölçülmeyen görev türü | yok | yok |
| Lean yanlış pozitif | 0 | 0 |
| Lean sertifika | 107/280 | raporlanır |
| Lean junk-value sertifikası | 0/12 | 0 |
| Adversaryal saldırı başarısı | %0.000 (21 139 saldırı, 3 yüzey) | < %2 |
| Saldırı yüzeyleri | cevap + şık + adım | üçü de koşmalı |
| SymPy üretimli yanlış cevapta yanlış onay | 0/448 | 0 |
| SymPy üretimli eşdeğer cevapta yanlış red | 0/214 | 0 |
| Cevap olmayan iddiada CORRECT | 0/46 | 0 |
| Geçerli adım dönüşümünde yanlış red | 0/184 | 0 |

Değerlendirme seti **280 öğe**, hücre dağılımı A/B/C/D = %30/25/30/15. A = doğru çözüm, B = doğru
ama kanonik olmayan çözüm, C = yanlış çözüm, D = doğru cevap ama bozuk adım. 19 Eylül'de 260'tı;
router'da tanımlı olup hiç ölçülmemiş üç görev türü için 20 öğe eklendi (§13.7).

Formal katman ayrıntısı: 156 öğe için Lean ifadesi üretilebiliyor, bunların 107'si kanıtlanıp
denetimden geçiyor. Yanlış cevaplı hiçbir öğede kanıt yok. Mutlak sayılar 19 Eylül ile aynı;
yüzde düştü çünkü yeni 20 öğe L7'nin bilerek çevirmediği sınıflardan.

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

Kaba maliyet: yarım koşunun **ölçülen** rakamı öğe başına **0,066 dolar** (handoff'un 0,23 dolar
kestirimi prompt caching öncesiydi). Kalan 154 öğe için yaklaşık 10 dolar, F4'ün 238 öğede ilk
koşusu için yaklaşık 15–25 dolar. Yine de `--max-cost` ile koşun.

**Önce §13.1'i okuyun:** faturalama durdurucusu 18 Eylül'de ateşlemiyordu ve 151 öğe boşa gitti.
Düzeltildi ve teste bağlandı, ama harcamadan önce bilinmesi gereken şey bu.

Bakiye gelince körlemesine tam sete girmeyin. Önce kalibrasyon koşusu yapın:

```bash
.venv/Scripts/python.exe -m harness.run_f3 --limit 10 --workers 3 --max-cost 5
```

Öğe başına gerçek maliyeti ölçün, sonra tam ölçüme geçin. `--max-cost` gözetimsiz bir koşunun
bakiyeyi boşaltmasına karşı vardır; sağlayıcı faturalama hatası verirse koşu zaten ilk hatada durur.

Tam koşu:

```bash
.venv/Scripts/python.exe -m harness.run_f3 --workers 6 --pathb --max-cost 40
```

Gerçek bir AI çözücünün çıktıları ölçülecekse `--solver-family` **verilmelidir** (§13.9);
verilmezse her kayda `solver_family_unknown` bayrağı konur ve çapraz aile ayrımı uygulanmaz.

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

---

## 13. 20 Eylül 2026 denetimi — bulunan ve kapatılan boşluklar

Bu bölüm, "tek eksik API anahtarı mı?" sorusunun cevabını veriyor: **hayır**. Aşağıdakilerin
hiçbiri krediye bağlı değildi; hepsi koddaydı ve hepsi kapatıldı. Her biri ölçümle bulundu,
ölçümle doğrulandı ve teste bağlandı.

### 13.1 Faturalama durdurucusu hiç ateşlemiyordu (en kritik)

`f3_results.json` içinde `aborted: None` yazarken 151 öğe `Your credit balance is too low` ile
düşmüştü — yani kredi bittikten sonra tarama 151 öğe boyunca boşa devam etti. Zinciri:

1. `LLMCreditError` bir `LLMError`'dı, `extract_ir`'ın `except LLMError`'ı yuttu;
2. mesaj `str(e)[:120]` ile kırpıldı; harness'in aradığı `credit` kelimesi **tam bir karakter**
   sonra başlıyordu;
3. durdurucu o kırpılmış dizgiyi arıyordu.

Üstelik durdurucu yalnız `ir_reason`'a bakıyordu: IR başarılı olup L4/L5/L6/L7 sırasında kredi
bitseydi tümüyle kördü. Testin kendisi de kusurluydu — 24 karakterlik sahte bir mesaj kullanıyor,
yani kırpmanın altında kalıyordu.

**Kapatıldı:** `LLMFatalError` artık `LLMError`'ın alt sınıfı değil, her katmandan yükseliyor;
harness yapısal `fatal` alanıyla ilk hatada duruyor; mesaj kırpılmıyor; test sağlayıcının
gerçek mesajını kullanıyor. `DECISIONS.md` §23 düzeltildi.

### 13.2 Yalnız şık harfi veren "çözüm" CORRECT alıyordu

`verify_cli --text "Bilmiyorum ama tahminim. Cevap: B"` → `CORRECT 0.990`, hiçbir bayrak yok.
Doğrulayıcı yükü şıkkın kendi değerinden dolduruyor, `mc.consistency` şıkkı kendisiyle
karşılaştırıyor ve sertifika şıkkın değerini doğruluyordu. §2'deki CORRECT tanımının ikinci
koşulu ("hiçbir adım reddedilmedi") adım yokken boş doğru.

**Kapatıldı:** `answer_level_only` / `steps_not_checked` / `answer_from_option_letter`
bayrakları ve karar izinde `KAPSAM:` satırı. Verdict bilerek korundu — çekimser kalmak yol
(b)'nin cevap düzeyi kapsamasını yok ederdi — ama kapsam artık makine tarafından okunabilir.

Ayrıca gerçek dünya tarafı: `x ∈ {30, 150, 210, 330}. Cevap: B` metninde çıkarıcı kümeyi atıp
yalnız harfi tutuyordu. Artık soru küme/aralık istiyorsa metindeki son küme iddiası kurtarılıyor
(`payload_source="recovered_text"`, **tavsiye niteliğinde**: şıkla çelişirse çekimser kalır,
asla reddetmez). O öğe artık doğru biçimde INCORRECT.

İlk deneme çok agresifti ve ölçüldü: her `<sym> = <token>` kurtarılınca 94 kurtarmanın 59'u
çözücünün gerçekten iddia ettiği şey değildi (ara adımlar, `y = 2x + 1` → `2x` kırpması). Bu
yüzden yalnız küme/aralık literalleri kurtarılıyor: 5 kurtarma, 5'i doğru, 0 yanlış.

### 13.3 Adım iddiasını bozmak reddi iptal ediyordu

Adversaryal tarama adımlara hiç dokunmuyordu. Dokunur dokunmaz çıktı: reddedilmiş bir adımın
iddiasına `}` ya da bir istem enjeksiyonu eklemek iddiayı ayrıştırılamaz yapıyor, reddedici
onu cezasız atlıyor ve **INCORRECT → CORRECT** oluyordu (54 saldırı/öğe çifti, %2.118 başarı).

**Kapatıldı:** ayrıştırılamayan iddia iki sınıfa ayrıldı. `u = sqrt(x+4)` iyi biçimli
matematiktir, cezasız atlanır (`UndeclaredSymbolError`); `a = 20}` matematik değildir,
`malformed_step_claim` bayrağıyla CORRECT engellenir. Ayrım tahminle değil ayrıştırmayla
yapılır: bilinmeyen adlar serbest sembol (çağrılıyorsa `Function`) kabul edilip metin yeniden
ayrıştırılır. Ayrıca `#` yasaklandı — Python tokenizer'ı satırın kalanını yorum sayıyor, yani
`2*x ### ...` sessizce `2*x`e dönüşüyordu.

### 13.4 Adversaryal tarama tek yüzeyi ölçüyordu

6009 saldırının hepsi *cevap yüküne* uygulanıyordu ve her saldırı şık harfini siliyordu —
oysa 260 çözümün 257'si harf taşıyor. Küme/aralık cevaplar, adımlar ve LaTeX hiç saldırıya
uğramıyordu. Artık üç yüzey ayrı ölçülüyor (cevap yükü · şık harfi korunarak · adım iddiaları)
ve **üçünün de var olması bir kapı**: tek yüzeyde %0 başarı, ölçülenin dar olduğunu gizler.

### 13.5 LaTeX dalı hem beyaz listeyi atlıyordu hem hiç ölçülmüyordu

`\frac{zzz}{2}` sessizce `z*z*z/2` oluyordu (latex2sympy örtük çarpma uygular), oysa kanonik
dal `zzz`'yi reddediyordu: bir çözücünün `\frac{ab}{2}` yazması iddiayı başka bir şeye çevirirdi.
Ve 260 öğenin **sıfırı** LaTeX dalını tetikliyordu — gerçek bir modelin yazdığı çözümün baskın
biçimi. Artık LaTeX sonucundaki her serbest sembolün tanımlı olması şart ve sette LaTeX iddia
taşıyan öğe var (`tyt-kap-011`), ayrıca `latex_form` bir saldırı türü.

Yan bulgu: `5π/6` ayrıştırılamıyordu (`5pi/6` sözdizimi hatası). Unicode değer sembolü bir
rakamın ardından gelince çarpım açıkça yazılıyor artık; örtük çarpma genel olarak hâlâ kapalı.

### 13.6 `Interval.open(...)` Faz 1'den beri kullanılamıyordu

`open(` yasak-jeton listesindeydi ve `Interval.open(1, oo)` içinde de eşleşiyordu — oysa bu
biçim `_ALLOWED_DOTTED` içinde ve `SOLVER_FORMAT.md`'de belgeli. Artık yalnız *çıplak* `open(`
reddediliyor. Bu hata, kapsam öğeleri yazılırken ortaya çıktı.

### 13.7 Üç görev türünün sette hiç öğesi yoktu

`count_solutions`, `domain_of`, `simplify_expression` router'da tanımlı, sertifika modülleri
yazılı ve birim testli — ama değerlendirme setinde tek öğeleri yoktu, yani raporlanan precision
onlar hakkında hiçbir şey söylemiyordu. 20 yeni öğe eklendi (`evalset/build/tyt_kapsam.py`),
hücre oranları tam olarak korundu (280 öğe: %30/25/30/15). Artık "router'da tanımlı her türün
öğesi vardır" bir kapı.

Bunu yazarken `render_ir` içinde `simplify_expression` ve `count_solutions` şablonlarının
eksik olduğu da çıktı: round-trip yargıcına ham JSON gidiyordu, yani F3 bu türlerde bir IR'ı
zaten kabul edemezdi.

### 13.8 Ölçüm dürüstlüğü: iki sayı yanıltıcıydı

* **"Restructuring (yol b) sadıklığı 1.000"** neredeyse boştu: 260 öğenin 245'i yalnız şık
  harfi eşleştiği için sadık sayılıyordu ve bunların 244'ünde hiçbir yük kurtarılmamıştı.
  Artık iki sayı raporlanıyor; cevabın kendisinin karşılaştırıldığı öğe sayısı ayrı.
* **F3 raporunun "Yol (b)" bölümü yol (b)'yi ölçmüyordu**: 218 öğenin 184'ü kredi bittiği için
  deterministik cevap-çıkarıcıya düşmüştü ve adımsız bir öğede D hücresi yapısal olarak
  yakalanamaz. "37 yanlış karar, D tespiti 3/39" o geri-düşmenin ölçümüydü; gerçekten
  yeniden yapılandırılan 34 öğede 32/34 doğru karar, D 3/5. Rapor artık ikisini ayırıyor.
* **L5'in tavanı** modelsiz ölçülüp raporlanıyor: 21/280 öğe (%7.5), D hücresinde 3/42.
  L5 D hücresini yakalamak için var ve sınırsız bütçeyle bile D'lerin %7'sine dokunabiliyor.
  Bu bir bütçe sorunu değil, kapsam sorunu.

### 13.9 Çapraz aile ayrımı geçiriliyor ama hiç verilmiyordu

`solver_family` her katmana parametre olarak gidiyordu; hiçbir çağıran vermiyordu, dolayısıyla
L4, L5, kritik ve Lean ispatı hep `anthropic`'e düşüyordu. `ROLE_FAMILY` tanımlı ve dışa
aktarılmış ama **hiçbir yerde okunmuyordu**. Sentetik set için zararsız; gerçek bir Claude
çözücü takıldığında Claude'u Claude eleştirir ve hiçbir uyarı çıkmaz.

**Kapatıldı:** `run_f3 --solver-family`, `client_for_role()` / `judge_families()` (ROLE_FAMILY
artık tek kaynak) ve `solver_family` verilmediğinde her kayda konan `solver_family_unknown`
bayrağı. Gerçek çözücü çıktıları ölçülürken bu bayrak verilmelidir.

### 13.10 Paketleme ve sessiz geri-düşmeler

* `anthropic` ve `python-dotenv` beyan edilmemişti; `anthropic` tek sabitlenmemiş bağımlılıktı
  ve bir beta API yüzeyini sürüyor. Artık `[llm]` ekstrası altında sabit.
* `MATHVERIFY_CALIBRATION=on` ile `reports/calibration.json` yoksa (git-ignore'lu) **sessizce**
  hiçbir şey yapmıyordu. Artık `CalibrationUnavailable` fırlatıyor.
* `pyproject` açıklaması hâlâ "Phase 1: no LLM layers" diyordu.

### 13.11 Değerlendirme setinin üreticileri hiç commit edilmemişti

En sessiz hata bu. `.gitignore`'daki `build/` deseni ankrajsızdı ve `evalset/build/` dizinini de
yakalıyordu. Sonuç: **16 üretici modülün hiçbiri depoda değildi** (`git ls-files evalset/build`
→ 0). Üretilen `evalset/items/*.json` commit'liydi ama onları üreten kod değildi; temiz bir
klonda README'nin belgelediği `python evalset/build/build_all.py` komutu çalışmazdı ve set ne
yeniden üretilebilir ne genişletilebilirdi. HANDOFF'un "4.127 satır ... set üreticisi" ölçüsü de
depoda olmayan dosyaları sayıyordu.

Desen `/build/` ve `/dist/` olarak kök'e ankrajlandı; 17 modül (yenisiyle birlikte) artık
görünür. Bu hata, yeni üretici modülün commit edilmediğini fark edince ortaya çıktı.

### Kapatılmayanlar ve neden

* **Gerçek AI çözücü çıktıları** — kullanıcının ertelediği karar; kodla kapanmaz.
* **Git uzak deposu, CI, LICENSE yok.** Proje tek makinede duruyor. Bunlar sahiplik/altyapı
  kararları olduğu için dokunulmadı; uzak depo açmak ve `check.py --full`'u CI'ya bağlamak
  bir sonraki oturumun ilk işi olmalı.
* **`tyt-prob-018`** — "doğru ama gerekçesiz adım". Gerekçesi 8. bölümde; karar ölçüme bağlı.

---

## 14. 23 Eylül 2026 — ikinci denetim: önce literatür, sonra doğrulayıcının kendisini test etmek

Bu tur, "bu tür bir doğrulayıcı en iyi nasıl yapılır" sorusuyla başladı; özeti ve her ilkenin bu
projedeki karşılığı [docs/QUALITY.md](docs/QUALITY.md). Oradan çıkan iki teknik — **Lean'e özgü
junk-value tehlikelerinin denetimi** ve **doğrulayıcının metamorfik/diferansiyel testi** — 13. bölümdeki
denetimin göremediği, üçü doğrudan yanlış onay üreten hata sınıfı buldu. Hepsi kapatıldı ve kalıcı
kapıya bağlandı.

### 14.1 Formal katman matematiksel olarak yanlış iddiaları kanıtlıyordu

Lean her kısmi işlemi tamamlar: `x/0 = 0`, `Real.sqrt (−3) = 0`, `Real.log 0 = 0`,
`Real.tan (π/2) = 0`, integrallenemeyen fonksiyonun integrali 0. Bu değerlere dokunan ifadeler
ispatlanabilir ve aksiyom/sorry/vakum/kullanılmayan-hipotez denetimleri bunu göremez.

Ölçüm (değişiklikten önce): "tan(π/2) = 0", "√(2−5) = 0", "0/0 = 0", "log 0 = 0", "sin 0 = √(−4)" —
beşi de temiz, denetimden geçmiş sertifika aldı. `--lean` ile ilki bütün doğrulayıcıdan
**CORRECT, 0.995** çıktı; deterministik katman orada UNKNOWN diyordu, yanlış onayı tek başına Lean
üretti.

Kapatıldı (DECISIONS §26): kapalı kısmi işlemler yazıcıda karara bağlanıyor; açık olanlar şablona göre
koruma hipotezi, bölge üzerinde kanıtlanmış tanımlılık ya da ret. 12 junk sondasının 11'i ifade bile
üretmiyor, 1'i ispatlanıyor ama denetim çelişkiyi yakalıyor. **Mevcut 107 sertifika aynen korundu**;
düşen 4 ifade (∫₀¹ ln x/√x, has olmayan integral) zaten hiç ispatlanmamıştı.

Bunu kovalarken daha eski bir hata çıktı: **vakum sondası F5'ten beri tasarlandığından zayıftı.**
`first | … | norm_num at * | simp_all` zincirinde `norm_num at *` hedefi kapatmadan "başarılı" sayılıyor
ve `first` ona kilitleniyordu. HANDOFF §6 bu tuzağı ispat merdivenleri için belgeleyip düzeltmişti;
sonda eski biçimde kalmıştı. Artık her alternatif `done` ile kapanıyor ve sonda ispat merdiveninin
kombinasyonlarını da deniyor. Güçlendirilmiş sonda mevcut 107 sertifikanın hiçbirinde çelişki bulmadı.

### 14.2 Doğrulayıcı cevabı kendisi üretiyordu

İddia ayrıştırıcısının ad alanında `integrate`, `limit`, `diff`, `nsimplify`, `simplify` ve
problemin kendi fonksiyonları açıktı. Soruyu cevap olarak geri yazan her iddia CORRECT alıyordu:
`integrate(log(x), x)`, `limit(sin(x)/x, x, 0)`, `diff(x**3, x)`, `f(g(2))`, `gcd(84, 120)`,
`nsimplify(500000003/3000000000)` — **7'de 7**. Projenin 1 numaralı ilkesinin ("karar üretilerek
değil, kanıtlanarak verilir") doğrudan ihlali.

Kapatıldı (DECISIONS §28): iddia değer-yalnız bir ad alanında okunuyor; dört sertifika iddiayı kendi
yoluyla tam ad alanında okuyordu, hepsi `Ctx.claim_ns`'e bağlandı; formal katman da aynı kuralı
uyguluyor. Setteki hiçbir iddia bu adları kullanmadığı için kapsama maliyeti sıfır.

### 14.3 İddia karşılaştırılmadan önce yeniden yazılıyordu — 27 yanlış onay

`harness/soundness_fuzz.py` (yeni) her problemin altın cevabından SymPy ile kesin olarak yanlış
cevaplar üretti. Sonuç: **448 yanlış cevabın 27'si CORRECT.** İki sebep, 11 yerde:

* `int()` kesmesi: sayısı 3 olan soruda `7/2` → 3 → CORRECT (sayma, `mc.consistency`, `equiv` count,
  Lean sayma şablonu);
* `nsimplify` "güzel sayıya yakalama": `500000003/3000000000` → 1/6 (olasılık); seriler, trigonometri,
  derece dönüşümü ve L5'te de aynı çağrı *doğru* değeri değiştirebiliyordu.

Kapatıldı (DECISIONS §29): `equiv.exact_integer` — tam sayı değilse yanlış sayımdır, yuvarlanmaz;
hiçbir iddia ya da hesaplanan değer `nsimplify`'dan geçmiyor.

### 14.4 Eşdeğerlik motoru üç yerde "eşit" diyordu

Diferansiyel bir sonda (doğrusu bilinen 20 çift): **10³⁰+1 = 10³⁰**, **e^{π√163} = 262537412640768744**
(Ramanujan sabiti tam sayı değildir) ve **1/(x−1) = 1/(x−1) + e⁻¹⁰⁰⁰** — sonuncusu "sembolik" yolla.

Kapatıldı (DECISIONS §27): kesin sayılar kesin; nümerik eşitlik her hassasiyet basamağında; sembolik
sıfır testinden `nsimplify` çıktı; rastgele noktalarda farkın kendisi uyarlamalı hassasiyetle
değerlendiriliyor; Math-Verify'in tek başına karar verdiği dal kaldırıldı (modül belgesi "yalnız ikinci
görüş" diyordu, kod karar verdiriyordu).

### 14.5 Ölçülen: tasarımın doğru olduğu yerler

* **Geçerli adım dönüşümü: 184'te 0 yanlış red.** [10] aynı dönüşümlerle LLM adım doğrulayıcılarında
  %75–85 yanlış red ölçüyor. "Yalnız somut karşı örnekle reddet" ilkesi burada kendini kanıtlıyor.
* **SymPy üretimli eşdeğer cevaplar: 214'te 0 yanlış red.**
* **Etiket denetimi:** setin hücre etiketleri altın cevaplarla tutarlı; gerçek bir etiket hatası yok.
* **Bir tarafı bozulan adım: 46'da 40 yakalandı.** Kaçan 6'nın 5'i çözücünün kendi sembolüyle
  (`t`, `u`) yazılmış adım — özdeşlik mi denklem mi belirsiz, bilerek atlanıyor (DECISIONS §3 bu
  noktada kesinleştirildi) — 1'i öncülleri hiç çözümü olmayan bir öğe.

### 14.6 Yeni kalıcı kapılar

`check.py --full`: SymPy üretimli yanlış cevapta yanlış onay = 0; eşdeğer cevapta yanlış red = 0;
cevap olmayan iddiada CORRECT = 0; geçerli adım dönüşümünde yanlış red = 0; Lean junk-value
sertifikası = 0.
