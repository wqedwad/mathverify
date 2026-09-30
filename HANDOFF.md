# HANDOFF — mathverify (güncel durum)

> **Son güncelleme: 30 Eylül 2026, sabah (UTC)**, dal `claude/sharp-lamport-f9m2w3` (`7f35e1d` + bu belge; birleşmedi, PR yok). Sohbet bağlamı dolduğu için yeni sohbete devredildi: §3 adım 1'den devam.
> Bu belge yalnız **bugünün** durumunu, açık işleri ve sırayı taşır; ~300 satırı geçmez. Tarihçe burada birikmez: 26 Eylül'e
> kadarki 2102 satırlık belge `docs/arsiv/HANDOFF-2026-09-26.md`'de (§0–§12). Kararlar ve gerekçeleri
> `DECISIONS.md`'de, kalıcı kurallar `CLAUDE.md`'de, bulut işletimi `docs/BULUT.md`'de.
> **[DOĞRULANMADI]** = ölçülmedi ya da yalnız çıkarım; işaretsiz her sayı ölçümden gelir. DECISIONS ve
> BULUT'taki "HANDOFF §N" göndermeleri yazıldıkları günün HANDOFF'una aittir: 26 Eylül öncesininkiler
> arşive, 26 Eylül'ünkiler o commit'teki `HANDOFF.md`'ye (`git log -p HANDOFF.md`).

## 0. İlk 10 dakika

1. `CLAUDE.md` (kurallar) → bu belge → `DECISIONS.md` §63–§72; bulutta oturum başı bloğu ve `docs/BULUT.md`.
2. `git status`, `git log --oneline -5`, `git ls-remote origin` (birleşmemiş dal, §6); bulut klonunda `git fetch
   origin master` (yerel `master`/`origin/master` bayat olabilir).
3. Takım: `PYTHONUTF8=1 .venv/bin/python -m pytest tests -rs` → **1930 passed / 5 skipped** (`0ec6126`) (3 root salt okunur dizin,
   1 isteğe bağlı indirme, 1 kapsam dışı ifade); sıcak Lean'le ~400 s, soğukta önce 345–470 s ısınma (B6). Lean yüzünden
   atlama = Lean hazır değil; ek `-q` özeti siler. Hangi kontrolün gerektiği: `scripts/check.py --plan`.
4. §3'teki ilk işe geç. Tekrar denenmeyecekler: arşiv §4.

## 1. Proje (kısaca)

Türkçe bir matematik sorusu ve bir AI'ın çözümüne **üç değerli** karar verir (CORRECT / INCORRECT /
UNKNOWN); karar kanıtla verilir (sertifikalar, adım reddedici, Lean 4 + Mathlib), cevap anahtarı hatta
girmez, LLM katmanları kararı yalnız daha temkinli yapar. İlkeler `CLAUDE.md`'de, mimari ve gerekçeler
arşiv §2–§3 ve `docs/ARCHITECTURE.md`'de; kilitli kararlar D1–D6 (`DECISIONS.md` §1) sorulmaz.
Giriş: `verifier.verify` (deterministik), `pipeline.run_pipeline` (LLM'li), `scripts/verify_cli.py`,
`scripts/check.py`. Değerlendirme seti 280 sentetik öğe (A/B/C/D = %30/%25/%30/%15).

## 2. Durum (30 Eylül 2026)

**Kod.** `master` = `wqedwad/asd#12`'nin birleşmesi (öncesi `c0a2caf` = `#11`'in birleşmesi; `#12`, `#9`, `#10` öncesi
yedeksiz, kullanıcı talimatı; `#11` öncesi `yedek/master-2026-09-28`, §6). `#7`–`#10`: DECISIONS §59–§62 (paralel tarama, `--plan`, bekçi, soğuk Lean, K4 düzeneği).
`#11` (DECISIONS §63): adım reddedicinin üç haksız reddi (görevin aralığı öncül ama bağlamaz; yalnız tanım kümesinin
bağladığı atama tanımsal; teğetin eğrisi ve `equation_of`'un verilen nesneleri öncül değil), "verified" yalnız kanıtta,
Meta istemcisi akışla, K4 etiketleyicisi, aynı isteğe kilit; 42/42 mutasyon (`denetim/2026-09-28/mutasyon.py`).
**Bu dal** (`claude/sharp-lamport-f9m2w3`, birleşmedi; DECISIONS §72): V14 düzeltildi ve üç turlu adversaryal denetimin
bulduğu yanlış onaylar kapatıldı: kapalı `Integral`/`Sum`/`Product`/`Limit` yalnız sayıyla doğrulanan değeriyle kullanılır
(SymPy ∫₋₁¹|cos x| = 0 diyordu), bağlı değişkenin koşulu problemin koşulu olmaz, IR fonksiyonu yazıldığı biçimde açılır ve
`domain` alanı uygulanır, yönsüz limit iki taraflı, yazılı türev yalnız türevlenebildiği yerde. 558 çözümde karar değişimi 0
(adım 26, doğru adımlar unknown → verified). `#12` (`claude/inspiring-cori-xcgjld`, §64–§70) `master`da.

**Fazlar.** F0–F2, F5 (Lean), F6 (adversaryal + kalibrasyon), F7 (Lean şablonları): tamam ve ölçüldü. F3 (LLM ön yüzü,
L4, L5): kod tamam, **ölçüm yarım ve eski** (18 Eylül, 218 öğenin 64'ü). F4 (kritik + meta-doğrulama): kod tamam,
çevrimdışı testli, **hiç koşmadı**. Denetimler: 20, 23, 25–26 Eylül (DECISIONS §26–30, §55).

**Son `check.py --full`.** **24/24**, `14f4d07` (`#12`'nin son kodu, raporlar `7fbf9ac`), bulutta 29 Eylül 17:59:56–18:23:09 UTC,
**~23 dk** (ısınma 39 s, pytest 349 s, adversaryal 661 s), 1726 passed / 5 skipped; `--plan` TAMAM (DECISIONS §71). Windows'ta son: `eab80f1` 24/24, 31 dk (DECISIONS §61).

**K4 (Muse Spark 1.3, 280 öğe, koşu 3, `776e5b4`; DECISIONS §63).** 278 çözüm; CORRECT|right 274, INCORRECT|right 4,
yanlış onay **0**, `undecided` 0; çözücü 278/278 doğru (yakalama gücü bu modelle ölçülemedi). 4 INCORRECT tek soru
(`tyt-say-*`): çözücü IR'ın `n`'ini başka anlamda kullandı (istem sembolün anlamını vermiyor). Çözümsüz 2 (tek
soru, `tyt-esf-007/-014`): akış kesildi, sonra Meta 504. Bugünkü harcama ~1.3 $ (önbellek kayıtlarından).

## 3. Sıradaki adımlar (sırayla)

1. **Yeni sohbet (V14'ün kapanışı):** `git fetch origin claude/sharp-lamport-f9m2w3` ve o dalda çalış (yeni dal açma;
   bulut oturumu başka dalda başlarsa bu dalı birleştirip kendi dalına push et). `--plan` koş (TAM beklenir: kod değişti).
   (a) Üçüncü denetimin **eleştirmeni bitti** (`e6712f5` üzerinde, 548 sonda), 9 bulgusu **henüz ele alınmadı**; ham hâli,
   tekrar betikleri ve beklenen değerler `denetim/2026-09-29/v14/bulgular/tur3_e6712f5.json` → `critic`. Bu turun açtıkları:
   N1 (yüksek, yanlış onay: parametreli integral/limit gövdeli IR fonksiyonunda değerin tanımlılığı kaybolur), N2 (yüksek,
   haksız red: değeri tam 0 olan kapalı integral göreli toleransla hiç onaylanmaz), N6 (düşük). Önceden var: N3 (yüksek,
   LaTeX `\lim` yönsüz sağdan okunur), N8 (yüksek, `limit(a*n*tan(pi/n), n, oo)` parametreli olduğu için ayrıştırmada 0),
   N5 (alan tek ilişki değilse yok sayılır), N4, N7, N9. Önce güncel kodda yeniden koş (bir kısmı `d38da47`–`7f35e1d`'de
   kapanmış olabilir), sonra sonda + test + mutasyonla kapat. (b) Tam takım ve 280 + 278 farkı `7f35e1d`'de (ya da sonrasında) koşulmadı:
   `denetim/2026-09-29/v14/fark.py dump/compare` (eski kod `35af293` ayrı worktree'de; karşılaştırma dökümü yeniden
   üretilir); ölçüm sürerken aynı checkout'ta dosya değiştirme (ayrı `git worktree` kullan).
2. **`--full`** son kodda, temiz ağaçta (~25–30 dk; oturum etkin tutulur, ≤10 dk beklemelerle izlenir); raporlar ve günlük
   değiştirilmeden commit + push; `--plan` TAMAM olmalı. Beklenen: sağlamlık/adversaryal kapıları 0; Lean sertifika sayısı
   değişebilir (alanlı/`Mod` gövdeli fonksiyonlar, V15). DECISIONS §72'nin "ölçülmedi" satırı sonuçla güncellenir.
3. **PR** `master`a (kullanıcı isteyince); birleştirmeden önce kullanıcı yerelde yedek alır (§6 yöntemi), `--plan` hemen önce.
4. **V15'ten (§4.2) kullanıcı kararı:** F9 (parametreli integral SymPy'ye güveniliyor, yanlış onay) düzeltilsin mi (seçenek:
   parametreli belirli integral biçim kalır; "∫₀^a x dx = 2" gibi sorular UNKNOWN olur)?
5. **Kod dondurmadan önce sorulacak** (§4.4 madde 3): çözücü istemi IR sembollerinin anlamını versin mi (`tyt-say-*`).
6. **Kod dondurma → F3 baştan, F4 ilk kez** (K1–K3; anahtar yenileme önkoşul değil, §64; Anthropic bakiyesi gerekir):
   önce kalibrasyon (`run_f3 --limit 10 --workers 3 --max-cost 5`), sonra tam koşu.
7. **İsteğe bağlı / kullanıcı kararı:** yanlış onay direnci için daha zayıf ya da başka aileden çözücü (K4 e); yedek
   etiketleri (PR #3, #4, #9, #10 öncesi, §6); bulut önyükleyicisi 250 → 275 s (B1–B2); açık kapsama işleri (§4.2, V1–V14).

## 4. Açık maddeler (tam liste)

Kaynak: arşivdeki §0.8–§0.14, §5–§7, §12, DECISIONS §53–§63 ve BULUT §12. Bir madde yalnız kapandığında,
kanıtıyla birlikte (DECISIONS'ta) buradan çıkarılır.

### 4.1 Bulut ve ortam

- **B1. Anlık görüntü bazen kullanılmıyor** (DECISIONS §56 Ek, §59 (e), §61; BULUT §12). 26 Eylül 11:00 sohbeti
  `new` ile betiği yeniden koşturdu (252 s bekleme); sonraki sohbetler (27 Eylül 09:39, 28 Eylül 16:36 dahil)
  `resume-cached`: `/opt` 26 Eylül 07:39'daki `setup-only` koşusunun (199 s) görüntüsünden, kanca 2 s. `new`'in
  nedeni **[DOĞRULANMADI]** (en olası: ağ ayarının değişmesi, §61).
- **B2. 250 s sınırı aşıldı** (11:00 sohbeti; REPL aşamasında durduruldu, kanca kalanı 42 s'de kurdu). Süre
  180–250 s arasında oynuyor.
- **B4.** `raw.githubusercontent.com` dosya indirme yolu kurulum aşamasında hiç koşmadı (yedek; oturum
  içinde 32 s, 5/5 OK; DECISIONS §54). **B5.** "claude.ai ortam değişkenleri kurulum betiğine hiç
  ulaşmıyor mu": kanarya (`MATHVERIFY_SETUP_CANARY=1`) eklenmedi, sınanmadı; düzeni etkilemiyor.
- **B6. Soğuk Lean açılışı** ~340–470 s (28 Eylül akşam düz `pytest`'te 405 s); `pytest` ve `--full` ilk Lean
  testinden önce ısınır (DECISIONS §60–§61). Açık: yavaşlığın nedeni (sayfa önbelleği değil; görüntü diskinin ilk
  okunması çıkarım **[DOĞRULANMADI]**).
- **B7.** Belirteç yenileme: yeni fine-grained belirteç (Contents: read-only, yalnız `wqedwad/asd`) Setup script'in
  `T='...'` satırına. **B8.** Etiket ve `master` buluttan push edilmez; etiket push'u bulutta hiç denenmedi.
- **B9.** Bulutta `repl` RSS 7.08 GB / PSS 6.78 GB (27 Eylül); `lake env`'in payı ölçülmedi. **B10. Kullanım/maliyet**
  (BULUT §8): bulut kredisinin kaynağı ve abonelik sınırının jeton ağırlığı **[DOĞRULANMADI]**; yerel maliyet ölçülmedi.

### 4.2 Doğrulayıcı: bilinen sınırlar ve kapsama

V11 ve V13 dışında hiçbiri doğru cevabı reddetmez; ya UNKNOWN (kapsama kaybı) ya da bilinçli sınır.

- **V1. `tyt-prob-018`:** çözüm düzeyindeki tek yanlış onay (doğru ama gerekçesiz adım; kanıtlanmış adım L6
  kritiğini ezer; aynı sınıf: C'deki 12 aritmetiği doğru `compute` adımı, §63). Karar F4 ölçümüne bağlı
  (DECISIONS §3.3, §4); `test_a_true_but_unjustified_step_is_still_overruled_by_its_certificate` ile testli.
- **V2. Çözücünün kendi sembolüyle yazdığı adımlar denetlenmez** (ilke 5). +1 bozulan 46 adımın 6'sı
  kaçıyor (5'i bu sınıf, 1'i çözümsüz öncül); nedenler `soundness_fuzz.ACCEPTED_MISS_REASONS`'da,
  açıklanmayan kaçırma bir kapı. Kapatmak `docs/SOLVER_FORMAT.md` sözleşmesini değiştirir.
- **V3. Tanımlılık türev/ekstremum/seride yalnız çekimser:** "`x²/x`'in [−1, 1]'deki minimumu −1"
  UNKNOWN. Tanımsız noktaları dışlayarak hesaplama ölçülmedi. `antiderivative` yazıldığı biçimde
  tanımlılık için ayrıca sınanmadı.
- **V4.** Adımsız çözümde CORRECT yalnız cevap düzeyindedir (`answer_level_only`,
  `answer_from_option_letter`, `KAPSAM:` satırı); bayrağa bakmayan tüketici farkı görmez.
- **V5. 25 Eylül'de bilerek bırakılanlar** (DECISIONS §55): kanıtsız eşdeğer biçimler ("(2x − y + 1)(x² + 1) = 0"),
  sembolik kanıtsız kapalı biçimler, periyodik tanım kümeli ilkeller, sonsuz sınırlı integraller, floor/ceiling
  özdeşlikleri, gelenek farklı tek taraflı durumlar (√x'in 0'daki limiti), `asec`/`acsc` yok.
- **V6.** Yanlış çarpanlara ayırma adımı (`x² − 5x + 6 = 2(x − 2)(x − 3)`, öncül `x² − 5x + 6 = 0`)
  öncüllerin çözümlerinde doğru olduğu için reddedilmez; ayrım sözdiziminden yapılamaz.
- **V7. Denetim kalıntıları** (`denetim/2026-09-25/`): C grubunda 20 fark (16 UNKNOWN, 2 beklenti
  hatası, `dc_eqof_eqstep` bilinen sınır, iki kayıt); A derleminde 5 (4'ü denetçinin etiket hatası, 1'i V6).
- **V8. Lean'de bilerek kapsam dışı:** olasılık olay yüklemleri, limitler, sentetik geometri, parçalı
  ve has olmayan integraller. Yazıcı çeviremediğini tahmin etmez.
- **V9. Ölçüm sentetik.** Precision 1.000 ve "Lean FP 0" bu sete özgü; 25 Eylül'de set dışı 98 yanlış
  iddianın 53'ü Lean'de sertifika alıyordu. Yeni bir denetim yeni sınıf bulabilir.
- **V10.** Sandbox süreç izolasyonudur, güvenlik sandbox'ı değil. Girdi artık kod olarak
  çalışmıyor (ilke 13), ama model kodu çalıştırılacaksa gVisor/Firecracker gerekir.
- **V11. Aralıkta örneği olmayan öncülde esas kök** (DECISIONS §65): `cos x = −1`, [0, π) gibi aralıkta kökü
  olmayan görevde periyotsuz yazılan doğru esas kök adımı (`x = pi`) reddedilir (x = 3π); `#11` öncesiyle aynı, D6 gereği.
- **V12. Tanım kümesine uyan yanlış atama** (DECISIONS §66): IR'da öncülün bağlamadığı bir sembole yanlış değer
  (`ayt-diz-002`'de `n = 21`) tanımsal kalır; sonra çelişilmezse çözüm CORRECT. `#11` öncesi doğrusu da reddediliyordu.
- **V13. Aynı doğrunun ikinci noktası** (DECISIONS §67–§68): seçim kuralı y-kesişimini kabul eder, ama ardından x-kesişimi
  (`y = 0`) seçilen x = 0 noktasında reddedilir (yanlış ordinattan ayrılamaz; D6); doğru çözüm INCORRECT. Gerçek veride yok.
- **V15. V14 denetiminden kalanlar** (DECISIONS §72; V14 kapandı). Yanlış onay (önceden var): parametreli belirli integral,
  belirsiz `integrate` ve parametreli `limit` ayrıştırmada SymPy'ye bırakılır (F9). Haksız red (önceden var): verilenlerin
  belirlediği sembollü `compute` adımı özdeşlik gibi denetlenir (S1); tam sayı bildirilmemiş üst sınırlı toplam (R1). Lean:
  `Mod`/`floor` gövdeli, tam sayı adlı argümanlı fonksiyon reddedilir (L1). Değer doğru: `gcd(120, 84)` "değer" (GCD-10).
  Mutasyon: R02 ve L07'nin eşdeğerliği kanıtlanmadı. Çok sayıda kapsama kaybı (UNKNOWN), liste §72'de.

### 4.3 Kredili ölçüm

- **K1. F3 baştan koşulmalı.** 18 Eylül sayıları eski kodun ve yarım: IR kabulü 64/67 (`ayt-diz-008/-013/-018`'de
  Meta yargıcı puan döndürmedi), yeniden yapılandırılan 34 öğede 32/34, iki yanlış karar D'de yanlış onay
  (`ayt-ana-017`, `-019`). `reports/f3_report.md` eski raporlayıcıdan. Kalan ~154 öğe ~10 $.
- **K2. F4 ilk kez** (L6 açık; ~15–25 $). Belirleyici sayılar: D tespiti, doğru çözümde yanlış
  suçlama, "sertifikanın iptal ettiği kritik raporu" (V1). 28 Eylül'den beri çapraz denetim eleştirmeni yalnız
  kanıtlanmış (`verified`) adımda geçersiz sayar; örneklenmiş adımlar artık `unknown` (DECISIONS §63 D).
- **K3. Ön koşullar:** kod dondurulur (sonraki her değişiklik sayıları eskitir); anahtar yenileme gerekmez
  (kullanıcı, DECISIONS §64); `--max-cost` olmadan koşulmaz; `llm_cache/` istek hash'iyle
  anahtarlı, değişen istem yeniden ücretlenir; bulutta `api.meta.ai` ortamın API kimlik bilgisiyle açık
  (DECISIONS §62; vekil anahtarı ekler); ~0,066 $/öğe (yarım koşu).
- **K4. Gerçek AI çözücü çıktıları:** `harness/run_solver.py`; Muse Spark 1.3 ile 280 öğe tamam (§2; DECISIONS §63).
  Açık: (a) `tyt-say-*` sembol anlamı: istem sembol adını verir, anlamını vermez (kullanıcı kararı, §4.4 madde 3);
  (b) `tyt-esf-007/-014`'ün sorusu çözülemiyor (akış kesilmesi, sonra Meta 504 "request timed out");
  (c) akışın `usage`'sız kesilmesinin nedeni **[DOĞRULANMADI]** (koşu 2'de 48 canlı çağrının 5'i; istemci yeniden
  dener); (d) eksik akışların ve 504'lerin ücretlendirilip ücretlendirilmediği **[DOĞRULANMADI]**; (e) çözücü hiç
  yanlış cevap vermedi: yanlış onay direnci için başka çözücü gerekir. ((f) anahtarlar 86/86, §69; (g) etiketleyici
  farkı kanıtlıyor, §70: kapandı. Kalan: ilkel eşitliği yerel, ℝ'de sıçrayan ilkel `right` etiketlenebilir.)

### 4.4 Kullanıcı kararları (açık sorular)

1. Ne zaman silinebilir (sormadan silinmez, §6): yedek etiketleri ve bundle'lar; `refs/arac/bulut-v1`
   (v2 doğrulandı, v1'in içeriğini taşıyor); `master`a girmiş uzak dallar (`bulut-2026-09-24`,
   `claude/funny-cray-bey5o1`, `-compassionate-shannon-…`, `-practical-faraday-…`, `-trusting-curie-…`,
   `-keen-ramanujan-…`, `-dreamy-meitner-…`, `-busy-bardeen-…`).
2. Anthropic bakiyesi ne zaman, ne kadar (F3 ~10 $, F4 ~15–25 $; kod dondurulunca)? Anahtar yenileme
   F3/F4 için gerekmiyor (DECISIONS §64); depo açılırsa gerekir (madde 8).
3. Gerçek çözücü çıktıları: Muse Spark 1.3 ile 280 öğe yapıldı (§2). Açık: çözücü istemi IR sembollerinin anlamını
   (öncülleri) versin mi (`tyt-say-*`; istem değişirse 280 öğe yeniden ücretli ve ölçülen şey değişir)? **Ertelendi**
   (28 Eylül akşam; kod dondurmadan önce yeniden sorulur). Etki: yalnız haksız red (86 sorudan 1), yanlış onay yok. Yanlış onay
   direnci için hangi (daha zayıf ya da başka aileden) çözücü? (Anahtarlar denetlendi: §69.)
4. Lisans ve CI (özel `wqedwad/asd`; CI ve LICENSE yok; CI açılırsa hızlı `check.py` koşar).
5. Sınırlar: `tyt-prob-018` kuralı F4'ten sonra daraltılsın mı (V1)? Çözücü sembolü adımları sınır mı,
   yapısal formata sembol tanımı mı (V2)? Ekstremum/türev/seride tanımsız noktada çekimserlik yeter mi (V3)?
6. Başka sağlayıcıyla (GPT/Gemini, `set_client_override`) ölçüm istenir mi?
7. Uygulamanın adı ve ayrıntıları (ne depoda ne şartnamede).
8. Depo açılacak/paylaşılacak mı? Açılırsa önce anahtarlar yenilenir, `.env` geçmişten temizlenir.
9. Bulut kurulumu: önyükleyici sınırı 250 → 275 ve Meta için ağ ayarı birlikte mi (§3 adım 4)?

### 4.5 Teknik borç

- **T1.** `DECISIONS.md` bölüm sırası 1, 2, 3, 6, 4, 5, 7–14; madde numaraları atlıyor; §2 ve §3.9 bilerek Faz 1 anlık
  görüntüsü ("180 öğe"). **T2.** Biçimlendirici yok; pyflakes dışında stil denetimi yok. **T3.** CI yok.
- **T5.** `reports/lean_setup.log` eski `stable` kurulumunun günlüğü (sabit kurulumunki bulutta
  `/opt/mathverify-logs/setup_lean.log`). **T6.** 26 Eylül öncesi `check_full.log` başlıklarında
  "commit edilmemiş değişiklik" sayısından 1 düşülür (günlük kendini sayıyordu; `3925180`).
- **T7.** `docs/BULUT.md` ~1070 satır ve tarihçe biriktiriyor (§12'de sonradan kapanmış üç madde
  hâlâ `[ ]`); buradaki gibi güncel durum + arşiv ayrımı gerekebilir. Testler onu okuyor: kod sayılır.
- **T8. Windows** (DECISIONS §59, §61): `eab80f1`'de `windows_full.ps1` ile **24/24, 31 dk**. Git Bash donmasının
  nedeni **[DOĞRULANMADI]**. Ölçülmeyen: ebeveyn izleyicisi, `CopyFile2`/junction yolu, `--plan`'ın buluttaki
  `--full`u Windows checkout'unda kabul etmesi. **T9. Kuralın sınırları:** bekçi alt süreçleri ve
  `os.open(dir_fd=…)`'yu görmez; koşu sırasında yapılıp geri alınan değişiklik günlükten anlaşılmaz; günlük düz metin.

### 4.6 Güvenlik

- **S1.** `.env` kullanıcı kararıyla özel depoda izleniyor (DECISIONS §35),
  değerler git geçmişinde ve GitHub'da. F3/F4 için yenileme gerekmiyor (§64); depo açılırsa önce yenilenir, geçmiş temizlenir.
  Bulutta Meta anahtarı ortamın API kimlik bilgisinde (VM'ye girmez); `.env`'deki eski Meta anahtarının iptali kullanıcıda.
- **S2.** GitHub belirteci Setup script metninde (ortamı kullanan herkes görür); sızarsa depoyu ve `.env`'i okutur. `unset`,
  root'un `/proc/<pid>/environ` okumasına karşı korumaz (DECISIONS §54). Sızıntı taraması yalnız günlüklerde, `/etc/profile.d`'de
  ve `.git/config`'te yapıldı (0 bulgu); daha geniş tarama izin denetimine takıldı, yapılmadı.

### 4.7 Doğrulanmamış kayıtlar

- §6'da **[DOĞRULANMADI]** işaretli yedekler (`572ef57`, `18fd298` bundle'ları; `ee7b2dd`'nin yerel yedeği): buluttan
  görülemez. 26 Eylül 01:06 koşusunda düşen testin adı kaydedilmedi (muhtemelen B6'daki Lean testi).
- Arşiv §4'teki "önce" ölçümlerinden kodu geri almadan üretilemeyenler (7/7, 54 çift, 0.990…) kayıttan; alandaki
  önyükleyici metninin içeriği (yalnız uzunluk eşleşiyor: 750 + 93 = 843); B1, B6, B10 ve K4'teki işaretli maddeler.

## 5. Son ölçülen sayılar (kapılar, `14f4d07`; aksi yazılmadıkça `3e1805d` ve öncekilerle aynı)

| Kapı | Değer | Hedef |
|---|---|---|
| Birim testleri (`0ec6126`) | 1930 passed / 5 skipped | hepsi geçer |
| pyflakes | 0 bulgu | 0 |
| Cevap düzeyi pozitif / negatif precision; kapsama | 1.000 / 1.000; 1.000 | ≥ 0.98; ≥ 0.85 |
| B hücresi yanlış red; anahtar sızma testi | 0.000; geçti | < 0.10; zorunlu |
| Çözüm düzeyi pozitif precision; D tespiti | 0.994 (1 FP, V1); 0.976 (41/42) | raporlanır |
| Lean erişilebilir; sertifika; FP; junk | evet; 121/280; 0; 0/33 | —; —; 0; 0 |
| Adversaryal saldırı başarısı (3 yüzey) | %0 (21 139 saldırı; UNKNOWN'a düşen 2890, önce 2894) | < %2 |
| Yanlış onay / eşdeğerde red / değer olmayan iddia / adım dönüşümünde red | 0/457 (önce 0/448, §70), 0/214, 0/46, 0/184 | 0 |
| Nedeni açıklanmayan kaçırılan bozuk adım; adım lokalizasyonu | 0/6; 75/120 (önce 74) | 0; raporlanır |

Raporlar `reports/*.md` (üretilir, elle yazılmaz), kapı günlüğü `reports/check_full.log`.
Süre: `--full` bulutta **~25–30 dk** (4 süreçli adversaryal 734–811 s), Windows'ta 31 dk; hızlı `check.py` ~7 dk (427 s).

## 6. Dallar, etiketler, yedekler

- **Dallar** (30 Eylül): `claude/sharp-lamport-f9m2w3` `7f35e1d`+ (V14, birleşmedi); `master` = `wqedwad/asd#12`'nin birleşmesi (`35af293`; öncesi `c0a2caf`); `claude/inspiring-cori-xcgjld`
  `wqedwad/asd#12` (birleşti); `claude/busy-bardeen-ckr5bw` `wqedwad/asd#11` (birleşti);
  `claude/dreamy-meitner-rvrwlj` `60d539c` (`#9`, `#10`), `claude/keen-ramanujan-oqseru` (`wqedwad/asd#8`), `claude/trusting-curie-76slml` `1fddfc6`,
  `claude/practical-faraday-7a4iy4` `a078a14`, `claude/compassionate-shannon-759r85` `93343c3`,
  `claude/funny-cray-bey5o1` `51e7651`, `bulut-2026-09-24` `18fd298` (hepsi `master`da);
  `denetim-2026-09-20` `e2aa08d`, `yerel-kalite-2026-09-23` `23d7c6b` (eski); araç ref'leri
  `refs/arac/bulut-v1` `c6d0cc1`, `refs/arac/bulut-v2` `f90d5e4` (kullanılan).
- **Yedek etiketleri** (GitHub'da; bundle'lar yalnız `C:\Users\kullanici\mathverify-yedek\`, geri dönüş
  talimatı orada `OKU.txt`):

  | Etiket | `master` | Bundle |
  |---|---|---|
  | `yedek/master-2026-09-23` | `2744677` | `mathverify-master-2744677-2026-09-23.bundle` |
  | `yedek/master-2026-09-23-2` | `e2aa08d` | `mathverify-master-e2aa08d-2026-09-23.bundle` |
  | `yedek/master-2026-09-24` | `23d7c6b` (birleştirmeden **sonra** alındı) | `mathverify-master-23d7c6b-2026-09-24.bundle` |
  | `yedek/master-2026-09-24-2` | `572ef57` | **[DOĞRULANMADI]** |
  | `yedek/master-2026-09-25` | `18fd298` (PR #1 öncesi) | **[DOĞRULANMADI]** |
  | `yedek/master-2026-09-26` | `d66bf2d` (PR #2 öncesi) | `mathverify-master-d66bf2d-2026-09-26.bundle`; içindeki `refs/heads/master` eski yerel `18fd298`, geri dönüş klon + `git checkout yedek/master-2026-09-26` |
  | yok | `ee7b2dd` (PR #3 öncesi) | **[DOĞRULANMADI]** |
  | yok | `e07d4f7` (PR #4 öncesi) | alınmadı (kullanıcı kararı, "yalnız belge" gerekçesiyle; PR kod da içeriyordu: DECISIONS §59 Düzeltme) |
  | `yedek/master-2026-09-26-2` | `849b492` (PR #7 öncesi) | `mathverify-master-849b492-2026-09-26.bundle` (kullanıcının betiği: yerel `master` önce ileri sarıldı, `bundle verify` ve deneme klonu geçti; etiket buluttan doğrulandı) |
  | `yedek/master-2026-09-27` | `5c2f83e` (PR #8 öncesi) | `mathverify-master-5c2f83e-2026-09-27.bundle` (kullanıcının betiği "YEDEK TAMAM" yazdı: `bundle verify` ve deneme klonu geçti; etiket buluttan doğrulandı) |
  | yok | `c2e4fdf`, `622a178` (PR #9, #10 öncesi) | alınmadı (kullanıcı kararı, 27 Eylül "yedeğe gerek yok"; 28 Eylül "birleştir") |
  | `yedek/master-2026-09-28` | `2f11c84` (PR #11 öncesi) | `mathverify-master-2f11c84-2026-09-28.bundle` (kullanıcı, 28 Eylül akşam: `bundle verify` "okay", deneme klonu `2f11c84`; etiket buluttan doğrulandı. İlk denemede etiket bayat yerel `master`ı (`5c2f83e`) göstermişti, silinip yeniden kondu) |
  | yok | `c0a2caf` (PR #12 öncesi) | alınmadı (kullanıcı kararı, 29 Eylül "birleştir bu dalı yedeğe gerek yok") |

- **Yedek yöntemi** (her `master` birleştirmesinden hemen önce, yerel checkout `C:\Users\kullanici\mathverify`'da): (0) `git fetch
  origin`, `git checkout master`, `git merge --ff-only origin/master`, `git log -1 --oneline` = beklenen commit (28 Eylül:
  checkout başka daldaydı ve kirli `reports/` onu engelledi, etiket bayat `master`ı gösterdi); (1) `git tag
  yedek/master-YYYY-MM-DD[-N] master`; (2) `git bundle create C:/Users/kullanici/mathverify-yedek/mathverify-master-<kısa-hash>-YYYY-MM-DD.bundle
  --all`, `git bundle verify` ve deneme klonu; (3) `git push origin <etiket>`; etiket buluttan `git ls-remote` ile doğrulanır;
  (4) hemen önce `scripts/check.py --plan`. Geri dönüş `git reset --hard <etiket>`. Buluttan `master`/etiket push edilmez.
- **Yerel checkout** (28 Eylül akşam): `master` `2f11c84`; `#11` ve `#12`den sonra `git pull` gerekir. Stash'te Windows `--full`
  raporları (`eab80f1`; kullanıcı silebilir), yerel `claude/dreamy-meitner-rvrwlj` eski (`eab80f1`, birleşmiş).

## 7. Bulut özeti (ölçülmüş)

- Ubuntu 24.04, 4 CPU, 15 GB RAM, ~30 GB disk, root, `/home/user/asd`. Ağ: açık GitHub, PyPI, `raw.githubusercontent.com`,
  `api.anthropic.com`, `api.meta.ai` (kimlik bilgisiyle); Lean/Mathlib/araç ref'leri kapalı, araç ref'inden gelir.
- Kurulum betiğinde git vekili yok (401), ortam değişkenleri ulaşmaz; belirteç önyükleyicide (DECISIONS §53–§56). Kanca
  6–15 s, eksikse Lean'i arka planda kurar (167–239 s); `/opt` ~10.7 GB.
- **Tur bitince uzun iş sürerken konteyner kapatılabiliyor** (26 Eylül `--full` kayboldu; 30 Eylül bir iş akışı): koşu ön
  planda ≤10 dk'lık beklemelerle izlenir. Alt ajanlar oturum kullanım sınırına takılabilir (30 Eylül).
- Meta (DECISIONS §63): akışsız ~31 s'de 502, akış bazen `usage`'sız kesilir, uzun `xhigh`'ta 504. Stop kancası commit +
  push ister; `ANTHROPIC_BASE_URL` okunmaz (§48); `rsync` yok (CLAUDE.md).

## 8. Komutlar

`PY=.venv/bin/python` (Windows: `.venv/Scripts/python.exe`); her komutta `PYTHONUTF8=1`, proje kökünde.

| Komut | Ne |
|---|---|
| `$PY -m pytest tests -rs` | Takım, atlama nedenleriyle |
| `$PY scripts/check.py --plan [--no-fetch]` | Hangi kontrol gerekli: YOK / TAMAM (çıkış 0) / TAM (1) (DECISIONS §59, CLAUDE.md) |
| `$PY scripts/check.py` / `--full` | Hızlı (~7 dk) / 24 kapı (~26 dk bulutta; günlüğü kendisi yazar, arka planda izlenir) |
| `$PY -m harness.run_eval` · `run_lean --timeout 45` · `adversarial [--workers N]` · `soundness_fuzz` · `calibrate` | Tek tek ölçümler → `reports/` (`--full`dan sonra koşulursa `--plan` o koşuyu kabul etmez; `git restore reports/`) |
| `$PY denetim/2026-09-2{6,7,8}/mutasyon.py [-j N] [ön ek…]` | Mutasyon denetimleri: kural/bekçi/tarama (README 26'da), Lean ısınması/kalibrasyon/günlükler (§60), K4 düzeltmeleri (§63); `2026-09-28/mutasyon_gece.py` hedefli denetim (§65) |
| `$PY -m harness.run_solver --family meta --max-cost 10 --workers 6` | K4 (kredili; aynı istekler kilitle sıralanır, önbellekten gelenler ücretsiz ama sınıra sayılır) |
| `$PY -m harness.run_f3 --workers 6 --pathb --max-cost 40 --solver-family …` | Kredili F3/F4 (`--no-l4/--no-l5/--no-l6`, `--limit`, `--ids`) |
| `$PY scripts/verify_cli.py --item evalset/items/tyt-prob-001.json [--lean] [--text "…"]` | Tek öğe |
| `$PY evalset/build/build_all.py` | 280 öğeyi yeniden üretir |
| `denetim/2026-09-25/araclar/olc.sh src <dizin>` + `say.py <dizin>` | 25 Eylül denetiminin ölçümleri (README orada) |

Kurulum (Linux; bulutta kanca yapar): `docs/BULUT.md` §4, Lean `docs/LEAN_SETUP.md`. Ortam
değişkenlerinin tam tablosu arşiv §9 ve `docs/BULUT.md` §5.

## 9. Nerede ne var

Arşiv `docs/arsiv/HANDOFF-2026-09-26.md` (§0 bulut tarihçesi, §2 mimari, **§4 tekrar denenmeyecekler**, §11 tuzaklar);
`DECISIONS.md` (§1 kilitli kararlar, §7–§15 tarih sırasıyla, son §72); `docs/` (`ARCHITECTURE`, `QUALITY`, `SOLVER_FORMAT`,
`LLM_LAYERS`, `LEAN_SETUP`, `BULUT`, `sartname/`); `reports/arsiv/`; `denetim/` (ölçüm ve mutasyon betikleri).
