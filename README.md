# mathverify — AI matematik çözümü doğrulama aracı

Üç değerli (CORRECT / INCORRECT / UNKNOWN) doğrulayıcı: bir matematik sorusu ve bir AI'ın
ürettiği çözüm verildiğinde, çözümün geçerli olup olmadığına **kanıtla** karar verir, cevabı
kendisi üretip karşılaştırarak değil. Cevap anahtarı doğrulama hattına hiç girmez.

**Yeni bir oturum devralıyorsa önce [HANDOFF.md](HANDOFF.md) okunmalı:** güncel durum, son ölçülen
sayılar, açık işlerin tam listesi ve sıradaki adımlar orada. 26 Eylül'e kadarki ayrıntılı tarihçe
(kararların gerekçesi, denenip işe yaramayanlar, tuzaklar):
[docs/arsiv/HANDOFF-2026-09-26.md](docs/arsiv/HANDOFF-2026-09-26.md).

Şartname (handoff): [docs/sartname/fable-handoff-matematik-dogrulama_1.md](docs/sartname/fable-handoff-matematik-dogrulama_1.md)
(24 Eylül 2026'dan beri depoda; önce yalnız yerel `Downloads` klasöründeydi) · Kararlar: [DECISIONS.md](DECISIONS.md)
Bulutta çalışma: [docs/BULUT.md](docs/BULUT.md)
Mimari: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · Çözücü formatı: [docs/SOLVER_FORMAT.md](docs/SOLVER_FORMAT.md)
§6 ölçümleri: [docs/E1-E10-measurement.md](docs/E1-E10-measurement.md) · LLM katmanları: [docs/LLM_LAYERS.md](docs/LLM_LAYERS.md)
Lean kurulumu: [docs/LEAN_SETUP.md](docs/LEAN_SETUP.md) · Raporlar: [reports/](reports/)
**Kalite ilkeleri (literatür → mekanizma → kapı):** [docs/QUALITY.md](docs/QUALITY.md)

## Durum (23 Eylül 2026; 24 Eylül ekleri son iki satırda)

| Faz | Durum |
|---|---|
| F0 §6 sözleşmeleri, IR, sandbox, §9 seti, iki intake yolu | **tamam** |
| F1-TYT / F1-AYT sertifikaları | **tamam** |
| F2 sentetik geometri, kombinatorik, seriler, lineer cebir | **tamam** |
| F3 LLM ön yüzü, L4 çapraz aile, L5 metamorfik | **kod tamam, ölçüm yarım** (Anthropic kredisi bitti) |
| F4 kritik + meta-doğrulama | **kod tamam, hiç koşmadı** (ölçüm hattı hazır, kredi bekliyor) |
| Denetim (20 Eylül): krediyle ilgisi olmayan 11 boşluk | **kapatıldı ve ölçüldü** ([HANDOFF arşivi §4](docs/arsiv/HANDOFF-2026-09-26.md), DECISIONS §23–25) |
| İkinci denetim (23 Eylül): literatür + doğrulayıcının metamorfik testi | **4 yanlış-onay sınıfı kapatıldı** ([HANDOFF arşivi §3–4](docs/arsiv/HANDOFF-2026-09-26.md), DECISIONS §26–30, [docs/QUALITY.md](docs/QUALITY.md)) |
| F5 Lean 4 + Mathlib | **tamam ve ölçüldü** (model gerektirmeyen yolla) |
| F6 adversaryal sertleştirme + kalibrasyon | **tamam ve ölçüldü** |
| 24 Eylül: özel GitHub deposu, Linux/bulut desteği, sabit Lean sürümleri, kapı sertleştirmesi (`check.py --full` 24 kapı) | **tamam** (`bulut-2026-09-24`; [HANDOFF arşivi §0](docs/arsiv/HANDOFF-2026-09-26.md), DECISIONS §34–43, [docs/BULUT.md](docs/BULUT.md)) |
| 24 Eylül: gerçek bulut ölçümü (tek seferlik routine oturumu, `4d01ba2`) | **ölçüldü**: Lean kurulumu 195 s, testler 515 passed / 2 skipped / 0 failed, hızlı `check.py` 12/12; bulunan iki sorun (Python yedeği, `ANTHROPIC_BASE_URL`) düzeltildi; `check.py --full` bulutta henüz koşmadı ([docs/bulut_tani_2026-09-24.md](docs/bulut_tani_2026-09-24.md), DECISIONS §44–48) |
| 25–26 Eylül: sistematik denetim (kod çalıştırma, yanlış onay sınıfları, formal katman) ve bulut kurulumu | **ölçüldü**: `check.py --full` bulutta **24/24** (son `5414d6b`, 1323 passed / 5 skipped; 24 Eylül satırındaki "bulutta henüz koşmadı" o günden sonra eskidi); kurulum betiği alandan ilk kez başarılı (`OK mode=all`, 180 s; o sohbet "Lean: HAZIR" ile açıldı), ama sonraki yeni sohbet anlık görüntüyü kullanmadı ve betik 250 s sınırında kesildi ([HANDOFF §4.1](HANDOFF.md), [arşiv §0.12–0.14](docs/arsiv/HANDOFF-2026-09-26.md), DECISIONS §54–56) |
| 26 Eylül: tam kontrolün kısaltılması (adversaryal tarama 4 süreçte, kademeli kontrol `check.py --plan`, belge-okuma bekçisi) | **ölçüldü**: `check.py --full` bulutta **24/24**, ~26 dk (önce bulutta 39–77 dk, tek süreç); adversaryal rapor yalnız süre satırında farklı; 1513 passed / 5 skipped; 158/158 mutasyon öldü (`claude/keen-ramanujan-oqseru`, DECISIONS §59) |
| 26–27 Eylül: `--plan` karar satırındaki üç görünüm kusuru (kararlar aynı) | **ölçüldü**: `check.py --full` bulutta **24/24** (`f3105ef`), 1514 passed / 5 skipped; 162/162 mutasyon öldü (`wqedwad/asd#8`, DECISIONS §59) |

## Ölçülen sonuçlar

Deterministik hat, 280 öğelik değerlendirme seti ([reports/eval_report.md](reports/eval_report.md)):

| Metrik | Değer | Hedef |
|---|---|---|
| Pozitif precision (cevap düzeyi) | **1.000** | ≥ 0.98 |
| Negatif precision (cevap düzeyi) | **1.000** | ≥ 0.98 |
| Kapsama | **1.000** | ≥ 0.85 |
| Pozitif precision (çözüm düzeyi) | 0.994 (1 FP) | — |
| B hücresi yanlış red | **0.000** | < 0.10 |
| D hücresi tespit | 0.976 (41/42) | ayrı raporlanır |
| Adım lokalizasyonu (tam eşleşme) | 1.000 (73/120 lokalize) | — |
| Anahtar sızma testi | geçti | zorunlu |
| Ölçülmeyen görev türü | **yok** | yok |
| Ortalama süre / öğe | ~0.15–0.2 s (makine yüküne bağlı) | — |

Yol (b) sadakati **iki** sayıdır, çünkü tek sayı yanıltıcıydı: 280 öğenin 260'ı yalnız şık
harfi eşleştiği için sadık sayılıyor, cevabın kendisi yalnız **20** öğede karşılaştırılıyor
(20/20 sadık). L5'in uygulanabilirlik tavanı modelsiz ölçüldü: **21/280** öğe, D hücresinde
**3/42** — bu bir bütçe değil kapsam sınırı.

Formal katman, modelsiz ([reports/lean_report.md](reports/lean_report.md)):

| Metrik | Değer | Hedef |
|---|---|---|
| Lean ifadesi üretilebilen öğe | 172 / 280 (%61.4) | — |
| Denetimden geçmiş formal sertifika | **121** (%43.2) | — |
| Yanlış cevaplı öğede kanıt | **0** | 0 |
| Junk-value sondası (gerçekte yanlış, Lean'de doğru 17 iddia) | **0** sertifika | 0 |
| Süre / öğe | ~0.3–0.5 s | — |

> 23 Eylül'de `domain_of`, `simplify_expression` ve `count_solutions` şablonları eklendi: bu 20
> öğenin 14 A/B/D öğesi sertifika aldı, 6 C öğesinin hiçbiri kanıtlanmadı. Her şablonun korumasının
> naif biçimi Lean'de gerçekten ispatlanıyor (`∀ x, x = x²/x` gibi); bu teste bağlı.
>
> **Junk value:** Lean `x/0 = 0`, `Real.sqrt (−3) = 0`, `Real.log 0 = 0`, `Real.tan (π/2) = 0`
> tanımlar. Tanımlılık korumalarından önce "tan(π/2) = 0" `--lean` ile bütün doğrulayıcıdan
> CORRECT (0.995) çıkıyordu. Ayrıntı: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#leanin-junk-değerleri).

Adversaryal sertleştirme, **üç yüzeyde** ([reports/adversarial_report.md](reports/adversarial_report.md)):

| Metrik | Değer | Hedef |
|---|---|---|
| Saldırı sayısı | 21 139 | — |
| **Saldırı başarısı** | **%0.000** | < %2 |
| Cevap yükü / şık harfi korunarak / adım iddiaları | 7354 / 7279 / 6506 saldırı, hepsinde 0 başarı | üç yüzey de koşmalı |
| Anlamı koruyan saldırıda karar değişimi | 0 | 0 |
| Anlamı değiştiren saldırıda yanlış onay | 0 | 0 |

Eski tarama 6009 saldırıyı **tek** yüzeye uyguluyordu ve her saldırıda şık harfini siliyordu.
Genişletildiğinde iki gerçek zafiyet çıktı ve ikisi de kapatıldı: adım iddiasını bozarak reddi
iptal etmek (INCORRECT → CORRECT) ve küme cevaplarında `{` önekinin doğru cevabı reddettirmesi
(CORRECT → INCORRECT). Ayrıntı: [HANDOFF arşivi §4](docs/arsiv/HANDOFF-2026-09-26.md).

Metamorfik sağlamlık taraması — doğrulayıcının kendisinin testi ([reports/soundness_report.md](reports/soundness_report.md)). Her problemin altın cevabından
SymPy ile kesin olarak yanlış ve kesin olarak eşdeğer cevaplar üretilir:

| Metrik | Değer | Hedef |
|---|---|---|
| Yanlış cevapta yanlış onay | **0 / 448** | 0 |
| Eşdeğer cevapta yanlış red | **0 / 214** | 0 |
| Cevap olmayan iddiada (soruyu yazan / CAS'a hesaplatan) CORRECT | **0 / 46** | 0 |
| Geçerli adım dönüşümünde yanlış red | **0 / 184** | 0 ([10]: LLM doğrulayıcılarında %75–85) |
| Bir tarafı bozulan adımın yakalanması | 40 / 46 | raporlanır |
| Nedeni açıklanmayan kaçırılan bozuk adım | **0 / 6** (5 çözücü sembolü, 1 çözümsüz öncül) | 0 |

Bu tarama ilk koşusunda **448 yanlış cevabın 27'sini CORRECT** buldu (`int(7/2) = 3`, `nsimplify` ile 1/6'ya yakalanan bir kesir); ayrıca soruyu cevap olarak geri yazan 7 iddianın 7'si CORRECT alıyordu. İkisi de kapatıldı.

23 Eylül'de bir yanlış-onay sınıfı daha bulundu ve kapatıldı: SymPy ayrıştırırken `x/x`'i 1'e, `(√x)²`'yi
x'e sadeleştirdiği için tanımsız noktalar kayboluyordu. "`x/x`'in tanım kümesi ℝ", "`x²/x = 0`'ın kökü
0", "x = 0'da `x/x` = 1" gibi 11 vaka CORRECT (0.99–0.995) alıyordu; tanım kümesi, denklem ve
eşitsizlikte doğru cevaplar da INCORRECT alıyordu. Tanımlılık artık ifadenin yazıldığı biçimden
okunuyor ([docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#tanımlılık-ifadenin-yazıldığı-biçimden-okunur),
`tests/test_written_definedness.py`); değerlendirme setinin sayıları değişmedi.

F3 (tam otomatik hat) kısmi ölçümü ([reports/f3_report.md](reports/f3_report.md)): 218 öğenin
151'i `Your credit balance is too low` ile düştü — ve tarama durması gerekirken durmadı; o hata
20 Eylül'de kapatıldı (HANDOFF arşivi §4, DECISIONS §23). Faturalama hatası almayan 67 öğede IR kabulü
**64/67**; reddedilen 3 öğe (`ayt-diz-008`, `ayt-diz-013`, `ayt-diz-018`) üç turun sonunda
round-trip'te Meta yargıcının puan döndürmediği öğeler. Kabul edilen 64 öğede görev türü elle
yazılanla aynı 64/64, çıkarılan IR ile elle yazılan IR'ın kararı aynı 63/64, cevap düzeyi
precision 1.000/1.000 (çözüm düzeyinde pozitif precision 0.967, 1 FP). Sayılar 18 Eylül koduna
aittir.

## Bilinen açıklar

Üçü var. Birincisi deterministik hattın tek yanlış onayı, ikisi ölçümün kapsamı hakkında.

### 1. Deterministik hattın tek yanlış onayı

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

### 2. Adımsız bir çözümde CORRECT yalnız cevap düzeyindedir

Serbest metin yolunda (yol b) çoğu zaman denetlenebilir adım üretilmez; o hâlde CORRECT
"cevap doğru" demektir, "çözüm geçerli" demez. Karar artık `answer_level_only` /
`answer_from_option_letter` bayraklarını ve karar izinde bir `KAPSAM:` satırını taşıyor, ama
bayrağa bakmayan bir tüketici için ayrım hâlâ görünmez. Çözüm düzeyinde kanıt isteniyorsa bu
bayraklar üzerinden kapı konmalıdır.

### 3. Ölçüm hâlâ sentetik

Değerlendirme setinin tamamını biz ürettik. Aşağıdaki precision sayıları gerçek bir modelin
çözümlerine karşı değil, kendi yazdığımız çözümlere karşıdır. Bu, krediyle ilgisi olmayan ve
kod değişikliğiyle kapanmayan tek açık.

## Kurulum

Windows (Git Bash):

```bash
uv venv --python 3.14 .venv
uv pip install --python .venv/Scripts/python.exe -e ".[llm,dev]"
```

Linux (bulutta bunu oturum kancası kendisi yapar, bkz. [docs/BULUT.md](docs/BULUT.md)):

```bash
uv venv --python 3.14 .venv
uv pip install --python .venv/bin/python -r requirements.lock
uv pip install --python .venv/bin/python --no-deps -e .
```

`requirements.lock`, başvuru Windows `.venv`'inde yüklü 32 paketin sürümlerine eşit, evrensel bir
kilittir (DECISIONS §43); Linux ortamı böylece aynı paket sürümleriyle kurulur.

`llm` ekstrası F3+ katmanlarını çalıştırır (`anthropic`, `python-dotenv`); ikisi de diğer
bağımlılıklar gibi sabitlenmiştir, çünkü `anthropic` bir beta API yüzeyini sürüyor.

LLM katmanları için `.env` (git tarafından yok sayılır):

```
ANTHROPIC_API_KEY=...
META_MODEL_API_KEY=...
```

> **Düzeltme (24 Eylül 2026):** `.env` artık yok sayılmıyor. Kullanıcının açık kararıyla bu özel
> depoda izlenir, bulut oturumları anahtarları oradan okur (DECISIONS §35). Değerler hiçbir
> çıktıya yazılmaz; depo açılacak ya da paylaşılacaksa önce anahtarlar yenilenir ve `.env`
> geçmişten temizlenir.

Lean için [docs/LEAN_SETUP.md](docs/LEAN_SETUP.md). Kısaca (sürümler `lean/PINS`'te sabit):

```bash
# Windows: WSL içinde
wsl -d Ubuntu -- bash /mnt/c/Users/kullanici/mathverify/scripts/setup_lean.sh
wsl -d Ubuntu -- bash /mnt/c/Users/kullanici/mathverify/scripts/setup_lean_repl.sh
# Linux (bulutta ortamın kurulum betiği yapar)
bash scripts/setup_lean.sh
bash scripts/setup_lean_repl.sh
```

## Bulutta çalışma

Proje özel GitHub deposunda (`github.com/wqedwad/asd`) ve Claude Code on the web oturumlarında
çalışacak biçimde hazırlandı: ortamın kurulum betiği (`scripts/cloud/setup_env.sh`) Python 3.14.6'yı
ve Lean'i `/opt` altına kurar, SessionStart kancası (`scripts/cloud/session_start.sh`) her oturumda
`.venv`'i ve Lean ortam değişkenlerini hazırlar. Ön koşullar, ağ ayarı, günlükler, sınırlar ve
ilk oturumda ölçülecekler: [docs/BULUT.md](docs/BULUT.md).

## Çalıştırma

Komutlar proje kökünden; yorumlayıcı platforma göre:

```bash
PY=.venv/Scripts/python.exe     # Windows (Git Bash; PowerShell için HANDOFF arşivi §9)
PY=.venv/bin/python             # Linux / bulut
export PYTHONUTF8=1
```

```bash
$PY scripts/check.py --plan     # hangi kontrol gerekli: YOK / TAMAM / TAM (DECISIONS §59)
$PY scripts/check.py --full
```

Tek komutta 23 kapı: testler, pyflakes, deterministik değerlendirme, Lean taraması (junk-value sondası dahil),
adversaryal tarama (3 yüzey), metamorfik sağlamlık taraması, kalibrasyon. Kapı düşerse çıkış kodu 1.
Çıktı ayrıca `reports/check_full.log`a yazılır (tarih, dal ve commit ile).
**Düzeltme (26 Eylül 2026):** günlük artık başta ve sonda UTC saat, dal, commit ve commit edilmemiş dosya
sayısını, bir ortam satırını (Python, platform, çekirdek paket sürümleri), `requirements.lock` denetimini ve
sonda raporların SHA-256 özetini yazar; `check.py --plan` bir koşuyu bunlara bakarak kabul eder (DECISIONS §59).

> **Düzeltme (24 Eylül 2026):** artık **24 kapı** ("Lean erişilebilir" eklendi; hızlı mod 12).
> Bir koşu çökerse, raporunu yazmazsa, Lean yoksa ya da tarama sırasında kaybolursa o koşunun
> kapıları düşer; önceden eski bir JSON ya da Lean'siz bir makine 23/23 gösterebiliyordu
> (DECISIONS §39).

Tek tek:

```bash
$PY -m pytest tests -q
```

```bash
$PY evalset/build/build_all.py
```

```bash
$PY -m harness.run_eval
```

```bash
$PY -m harness.run_lean --timeout 45
```

```bash
$PY -m harness.adversarial
```

```bash
$PY -m harness.soundness_fuzz
```

```bash
$PY -m harness.run_f3 --workers 6 --pathb
```

F3 koşusu L4, L5 ve L6'yı birlikte ölçer; `--no-l4` / `--no-l5` / `--no-l6` ile tek tek
kapatılır. F4 kritiğinin sayıları raporun "L6 kritik + meta-doğrulama (F4)" bölümünde çıkar.
`--max-cost 20` verilirse toplam harcama o dolar değerine ulaştığında tarama kendini durdurur;
gözetimsiz bir koşunun bakiyeyi boşaltmasına karşı. Sağlayıcı faturalama/kimlik hatası verirse
koşu ilk hatada durur — **bu 20 Eylül'de düzeltildi, öncesinde durmuyordu** (HANDOFF arşivi §4, DECISIONS §23).

Gerçek bir AI çözücünün çıktıları ölçülecekse `--solver-family anthropic|meta` **verilmelidir**:
çapraz aile ayrımı (DECISIONS §17) ancak o zaman uygulanır, yoksa her kayda
`solver_family_unknown` bayrağı konur.

> `reports/f3_report.md` 18 Eylül'deki yarım koşudan kalmadır ve eski raporlayıcıyla
> üretilmiştir; "Yol (b)" bölümü HANDOFF arşivi §6.6 ve güncel HANDOFF §4.3 (K1) ile birlikte okunmalıdır.

Tek bir öğeyi doğrulamak:

```bash
$PY scripts/verify_cli.py --item evalset/items/tyt-geo-001.json
```

`--lean` eklenirse formal katman da koşar. Model gerektirmez, yalnız yerel Lean/Mathlib ister,
ve yalnız pozitif kanıt üretir: sertifika ekleyebilir, hiçbir kararı ters çeviremez.

Sürümler sabittir: SymPy 1.14.0, mpmath 1.3.0, z3-solver 5.1.0, math-verify 0.9.0,
Lean 4.34.0 + Mathlib. Windows'ta `PYTHONUTF8=1` ile çalıştırın.
Ek (24 Eylül 2026): bütün Python paketleri `requirements.lock`'ta; Mathlib `5ed2965`, REPL
`646a773` ve elan 4.2.4 `lean/PINS`'te. Python yerelde 3.14.7, bulutta 3.14.6 (DECISIONS §42).

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

Kararın **kapsamı** çıktıda yazar: denetlenebilir adım yoksa `answer_level_only`, iddia yalnız
şık harfinden okunduysa `answer_from_option_letter` bayrağı konur ve karar izine bir `KAPSAM:`
satırı eklenir — o CORRECT cevap düzeyindedir, çözümün geçerliliği hakkında değil. Bir
`eq`/`compute` iddiası hiç ayrıştırılamıyorsa iki durum ayrılır: çözücünün kendi sembolü
(`u = sqrt(x+4)`) cezasız atlanır, bozuk iddia (`a = 20}`) `malformed_step_claim` ile CORRECT'i
engeller — aksi hâlde iddiayı bozmak reddi iptal ediyordu.

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
                  tyt_kapsam.py: domain_of / simplify_expression / count_solutions + LaTeX kapsamı
evalset/items/    280 JSON öğe (üretilir)
harness/          run_eval · run_lean · run_f3 · adversarial · calibrate · metrics · loader
docs/             ARCHITECTURE · SOLVER_FORMAT · LLM_LAYERS · LEAN_SETUP · BULUT · E1-E10-measurement
docs/sartname/    özgün şartname (kanonik `_1.md` ve daha eski `_eski.md`)
lean/             sabitlenmiş Lean projesi dosyaları ve PINS (sürümler)
scripts/          check · verify_cli · probe_e1_e10 · lean_* · setup_lean* · fetch_artifacts
scripts/cloud/    setup_env.sh (bulut ortam kurulum betiği) · session_start.sh (oturum kancası)
scripts/dev/      kapıların parçası olmayan geliştirme betikleri (smoke_*, lean_try, clean_imports)
reports/          üretilmiş raporlar
reports/arsiv/    git'e girmeyen rapor JSON'larının tarihli anlık görüntüsü
requirements.lock sabit paket sürümleri (Linux/bulut kurulumu)
.claude/          settings.json: SessionStart kancası
```
