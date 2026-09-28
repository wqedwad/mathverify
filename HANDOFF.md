# HANDOFF — mathverify (güncel durum)

> **Son güncelleme: 28 Eylül 2026, akşam**, dal `claude/busy-bardeen-ckr5bw` (`wqedwad/asd#11`; birleşmedi, yedek kararı kullanıcıda).
> Bu belge yalnız **bugünün** durumunu, açık işleri ve sırayı taşır; ~300 satırı geçmez. Tarihçe burada birikmez: 26 Eylül'e
> kadarki 2102 satırlık belge `docs/arsiv/HANDOFF-2026-09-26.md`'de (§0–§12). Kararlar ve gerekçeleri
> `DECISIONS.md`'de, kalıcı kurallar `CLAUDE.md`'de, bulut işletimi `docs/BULUT.md`'de.
> **[DOĞRULANMADI]** = ölçülmedi ya da yalnız çıkarım; işaretsiz her sayı ölçümden gelir. DECISIONS ve
> BULUT'taki "HANDOFF §N" göndermeleri yazıldıkları günün HANDOFF'una aittir: 26 Eylül öncesininkiler
> arşive, 26 Eylül'ünkiler o commit'teki `HANDOFF.md`'ye (`git log -p HANDOFF.md`).

## 0. İlk 10 dakika

1. `CLAUDE.md` (kurallar) → bu belge → `DECISIONS.md` §60–§63 (son dört madde). Bulutta ayrıca
   oturum başındaki `[mathverify bulut oturumu …]` bloğu ve `docs/BULUT.md`.
2. `git status`, `git log --oneline -5`; birleşmemiş başka dal var mı: `git ls-remote origin` (§6).
   Bulut klonunda yerel `master` ve `origin/master` bayat olabilir: `git fetch origin master`.
3. Takım: `PYTHONUTF8=1 .venv/bin/python -m pytest tests -rs`. Beklenen (Linux, Lean kurulu): **1639
   passed / 5 skipped**, sıcak Lean'le ~400 s (3 root salt okunur dizin, 1 isteğe bağlı indirme, 1 kapsam dışı
   ifade). Lean testi seçen oturum önce Lean'i ısıtır (soğukta 345–470 s, B6); Lean yüzünden atlama = Lean
   hazır değil. `addopts` `-q` içerir; ek `-q` özeti siler. Hangi kontrolün gerektiği: `scripts/check.py --plan`.
4. §3'teki ilk işe geç. Tekrar denenmemesi gerekenler: arşiv §4.

## 1. Proje (kısaca)

Türkçe bir matematik sorusu ve bir AI'ın çözümüne **üç değerli** karar verir (CORRECT / INCORRECT /
UNKNOWN); karar kanıtla verilir (sertifikalar, adım reddedici, Lean 4 + Mathlib), cevap anahtarı hatta
girmez, LLM katmanları kararı yalnız daha temkinli yapar. İlkeler `CLAUDE.md`'de, mimari ve gerekçeler
arşiv §2–§3 ve `docs/ARCHITECTURE.md`'de; kilitli kararlar D1–D6 (`DECISIONS.md` §1) sorulmaz.
Giriş: `verifier.verify` (deterministik), `pipeline.run_pipeline` (LLM'li), `scripts/verify_cli.py`,
`scripts/check.py`. Değerlendirme seti 280 sentetik öğe (A/B/C/D = %30/%25/%30/%15).

## 2. Durum (28 Eylül 2026)

**Kod.** `master` = `wqedwad/asd#10`'un birleşmesi (`2f11c84`; öncesi `622a178` ve `#9` öncesi `c2e4fdf` yedeksiz,
kullanıcı talimatı). `#7`–`#8`: 4 süreçli adversaryal tarama, kademeli kontrol `check.py --plan`, belge-okuma
bekçisi (DECISIONS §59). `#9`: soğuk Lean ısınması, kalibrasyon sırası, aşama günlükleri (§60). `#10`: K4 düzeneği
`harness/run_solver.py`, Windows `--full`, Meta TLS, K4 kısmi koşusu (§61–§62).
**Bu dal** (`claude/busy-bardeen-ckr5bw`, `wqedwad/asd#11`, birleşmedi; DECISIONS §63): adım reddedicinin üç haksız reddi
(görevin aralığı öncül ama bağlamaz; yalnız tanım kümesinin bağladığı atama tanımsal; teğetin eğrisi ve
`equation_of`'un verilen nesneleri öncül değil), "verified" yalnız kanıtta (örneklenen sonuç `unknown`; And/Or
iddiaları küme yolunda), Meta istemcisi ilk denemeden akışla (`usage`'sız akış yeniden denenir, önbelleğe
girmez), K4 etiketleyicisi (`+ C`, DNE, açıda derece, genel trigonometrik çözüm, demet), aynı isteğe kilit.
42/42 mutasyon (`denetim/2026-09-28/mutasyon.py`).

**Fazlar.** F0–F2, F5 (Lean), F6 (adversaryal + kalibrasyon), F7 (Lean şablonları): tamam ve ölçüldü.
F3 (LLM ön yüzü, L4, L5): kod tamam, **ölçüm yarım ve eski** (18 Eylül kodu, 218 öğenin 64'ü, kredi
bitti). F4 (kritik + meta-doğrulama): kod tamam, çevrimdışı testli, **hiç koşmadı**. Denetimler: 20, 23
ve 25–26 Eylül (formal katmanda 53/98 yanlış sertifika → 0/99; DECISIONS §26–30, §55).

**Son `check.py --full`.** **24/24**, `3e1805d` (bu dalın son kodu), bulutta 28 Eylül 18:14:01–18:40:57 UTC, **~27 dk**
(ısınma 11 s, pytest 399 s, adversaryal 793 s), 1639 passed / 5 skipped; `--plan` TAMAM (DECISIONS §63). Windows'ta son: `eab80f1` 24/24, 31 dk (DECISIONS §61).

**K4 (Muse Spark 1.3, 280 öğe, koşu 3, `776e5b4`; DECISIONS §63).** 278 çözüm; CORRECT|right 274, INCORRECT|right 4,
yanlış onay **0**, `undecided` 0; çözücü 278/278 doğru (yakalama gücü bu modelle ölçülemedi). 4 INCORRECT tek soru
(`tyt-say-*`): çözücü IR'ın `n`'ini başka anlamda kullandı (istem sembolün anlamını vermiyor). Çözümsüz 2 (tek
soru, `tyt-esf-007/-014`): akış kesildi, sonra Meta 504. Bugünkü harcama ~1.3 $ (önbellek kayıtlarından).

## 3. Sıradaki adımlar (sırayla)

1. **Bu dalın birleştirilmesi** (`wqedwad/asd#11`): önce kullanıcıya yedek sorulur (§6 yöntemi, yerelde), birleştirmeden
   hemen önce `scripts/check.py --plan`. Kuralın kendi dosyalarına dokunulmadı: son `--full` geçerliyse TAMAM beklenir.
2. **K4'ün açık kararları** (§4.3 K4, §4.4 madde 3): çözücü istemi IR sembollerinin anlamını versin mi
   (`tyt-say-*`; önbellek anahtarları değişir, 280 öğe yeniden ücretli ~1.3–5 $); bu model hiç yanlış cevap
   vermediği için yanlış onay direnci için daha zayıf bir çözücü ya da başka aile gerekir.
3. **Yedek etiketleri (isteğe bağlı):** PR #3, #4, #9 ve #10 öncesi `master` için etiket yok (§6).
4. **Bulut kurulumu** (B1–B2, DECISIONS §61): görüntü yalnız betik metni, ağ ayarı ya da ~7 gün değişince
   yeniden kurulur. Öneri: ağ ayarı değişecekse aynı anda önyükleyicide `timeout -k 10 250` → `275`;
   sonra ilk yeni sohbette süreler okunur. Karar kullanıcının (Setup script alanını o değiştirir).
5. **Kod dondurma → anahtarları yenileme → F3 baştan, F4 ilk kez** (K1–K3; kullanıcı kararı,
   23 Eylül). Önce kalibrasyon koşusu (`run_f3 --limit 10 --workers 3 --max-cost 5`), sonra tam koşu.
6. **Açık kapsama işleri** (§4.2) kullanıcı kararı. Gerçek çözücü için Anthropic ailesi bakiye bekliyor.

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
- **B7. Belirteç yenileme:** yeni fine-grained belirteç (Contents: read-only, yalnız `wqedwad/asd`)
  Setup script'in `T='...'` satırına; süresi dolmuşsa çekim düşer, kanca kurar (167–239 s). **B8.**
  Etiket ve `master` buluttan push edilmez (kural); etiket push'u bulutta hiç denenmedi.
- **B9.** Bulutta `repl` RSS 7.08 GB / PSS 6.78 GB (27 Eylül); `lake env`'in payı ölçülmedi. **B10. Kullanım/maliyet**
  (BULUT §8): bulut kredisinin kaynağı ve abonelik sınırının jeton ağırlığı **[DOĞRULANMADI]**; yerel maliyet ölçülmedi.

### 4.2 Doğrulayıcı: bilinen sınırlar ve kapsama

Hiçbiri doğru cevabı reddetmez; ya UNKNOWN (kapsama kaybı) ya da bilinçli sınır.

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

### 4.3 Kredili ölçüm

- **K1. F3 baştan koşulmalı.** 18 Eylül sayıları eski koda ait ve yarım: IR kabulü faturalama hatası
  almayan 67 öğede 64/67 (reddedilen `ayt-diz-008/-013/-018`'de Meta yargıcı puan döndürmedi, nedeni
  bilinmiyor); gerçekten yeniden yapılandırılan 34 öğede 32/34, 2 yanlış kararın ikisi D'de yanlış
  onay (`ayt-ana-017`, `-019`). `reports/f3_report.md` eski raporlayıcıdan. Kalan ~154 öğe ~10 $.
- **K2. F4 ilk kez** (L6 açık; ~15–25 $). Belirleyici sayılar: D tespiti, doğru çözümde yanlış
  suçlama, "sertifikanın iptal ettiği kritik raporu" (V1). 28 Eylül'den beri çapraz denetim eleştirmeni yalnız
  kanıtlanmış (`verified`) adımda geçersiz sayar; örneklenmiş adımlar artık `unknown` (DECISIONS §63 D).
- **K3. Ön koşullar:** kod dondurulur (sonraki her değişiklik sayıları eskitir); anahtarlar yenilenir,
  `.env` güncellenip commit edilir; `--max-cost` olmadan koşulmaz; `llm_cache/` istek hash'iyle
  anahtarlı, değişen istem yeniden ücretlenir; bulutta `api.meta.ai` ortamın API kimlik bilgisiyle açık
  (DECISIONS §62; vekil anahtarı ekler); ~0,066 $/öğe (yarım koşu).
- **K4. Gerçek AI çözücü çıktıları:** `harness/run_solver.py`; Muse Spark 1.3 ile 280 öğe tamam (§2; DECISIONS §63).
  Açık: (a) `tyt-say-*` sembol anlamı: istem sembol adını verir, anlamını vermez (kullanıcı kararı, §4.4 madde 3);
  (b) `tyt-esf-007/-014`'ün sorusu çözülemiyor (akış kesilmesi, sonra Meta 504 "request timed out");
  (c) akışın `usage`'sız kesilmesinin nedeni **[DOĞRULANMADI]** (koşu 2'de 48 canlı çağrının 5'i; istemci yeniden
  dener); (d) eksik akışların ve 504'lerin ücretlendirilip ücretlendirilmediği **[DOĞRULANMADI]**; (e) çözücü hiç
  yanlış cevap vermedi: yanlış onay direnci için başka çözücü gerekir; (f) cevap etiketleri kaba kuvvetle ya da
  ikinci kişiyle denetlenmeli (denetim derlemlerinde 4 etiket yanlış çıktı; bugün etiketleyicinin 3 "yanlış onayı"
  kendi hatasıydı).

### 4.4 Kullanıcı kararları (açık sorular)

1. Ne zaman silinebilir (sormadan silinmez, §6): yedek etiketleri ve bundle'lar; `refs/arac/bulut-v1`
   (v2 doğrulandı, v1'in içeriğini taşıyor); `master`a girmiş uzak dallar (`bulut-2026-09-24`,
   `claude/funny-cray-bey5o1`, `-compassionate-shannon-…`, `-practical-faraday-…`, `-trusting-curie-…`,
   `-keen-ramanujan-…`, `-dreamy-meitner-…`).
2. Anthropic bakiyesi ne zaman, ne kadar (F3 ~10 $, F4 ~15–25 $; kod dondurulunca)? API anahtarları
   ne zaman yenilenecek (§4.6)?
3. Gerçek çözücü çıktıları: Muse Spark 1.3 ile 280 öğe yapıldı (§2). Açık: çözücü istemi IR sembollerinin anlamını
   (öncülleri) versin mi (`tyt-say-*`; istem değişirse 280 öğe yeniden ücretli ve ölçülen şey değişir)? Yanlış onay
   direnci için hangi (daha zayıf ya da başka aileden) çözücü? Etiketleri kim denetleyecek?
4. Lisans ve CI (uzak depo özel GitHub `wqedwad/asd`; CI ve LICENSE yok). CI açılırsa hızlı
   `scripts/check.py` koşar; Lean ve `--full` kurulum ister.
5. Sınırlar: `tyt-prob-018` kuralı F4'ten sonra daraltılsın mı (V1)? Çözücü sembolü adımları sınır mı,
   yapısal formata sembol tanımı mı (V2)? Ekstremum/türev/seride tanımsız noktada çekimserlik yeter mi (V3)?
6. Başka sağlayıcıyla (GPT/Gemini, `set_client_override`) ölçüm istenir mi?
7. Uygulamanın adı ve ayrıntıları (ne depoda ne şartnamede).
8. Depo herkese açılacak ya da paylaşılacak mı? Açılırsa önce anahtarlar yenilenir, `.env` geçmişten
   temizlenir.
9. Bulut kurulumu: önyükleyici sınırı 250 → 275 ve Meta için ağ ayarı birlikte mi (§3 adım 4)?
10. Bu dalın (`wqedwad/asd#11`) birleştirilmesi ve öncesinde yedek (etiket + bundle, yerelde) alınsın mı?

### 4.5 Teknik borç

- **T1.** `DECISIONS.md` bölüm sırası 1, 2, 3, 6, 4, 5, 7–13; madde numaraları atlıyor; §2 ve §3.9
  bilerek Faz 1 anlık görüntüsü ("180 öğe").
- **T2.** Biçimlendirici yok; pyflakes dışında stil denetimi yok. **T3.** CI yok.
- **T5.** `reports/lean_setup.log` eski `stable` kurulumunun günlüğü (sabit kurulumunki bulutta
  `/opt/mathverify-logs/setup_lean.log`). **T6.** 26 Eylül öncesi `check_full.log` başlıklarında
  "commit edilmemiş değişiklik" sayısından 1 düşülür (günlük kendini sayıyordu; `3925180`).
- **T7.** `docs/BULUT.md` ~1070 satır ve tarihçe biriktiriyor (§12'de sonradan kapanmış üç madde
  hâlâ `[ ]`); buradaki gibi güncel durum + arşiv ayrımı gerekebilir. Testler onu okuyor: kod sayılır.
- **T8. Windows** (DECISIONS §59, §61): `eab80f1`'de `windows_full.ps1` ile **24/24, 31 dk**. Git Bash donmasının
  nedeni **[DOĞRULANMADI]**. Ölçülmeyen: ebeveyn izleyicisi, `CopyFile2`/junction yolu, `--plan`'ın buluttaki
  `--full`u Windows checkout'unda kabul etmesi. **T9. Kuralın
  sınırları:** bekçi alt süreçleri ve `os.open(dir_fd=…)`'yu görmez (test dışı kodun `.md` sabitleri ve
  kabuk betikleri testlerle sabitlendi); koşu sırasında yapılıp bitmeden geri alınan değişiklik
  günlükten anlaşılmaz; günlük düz metin (raporlar özetle bağlı, sahteciliğe karşı koruma yok).

### 4.6 Güvenlik

- **S1.** `.env` kullanıcı kararıyla özel depoda izleniyor
  (DECISIONS §35); değerler git geçmişinde ve GitHub'da. F3/F4'ten önce yenilenir; depo açılırsa önce
  yenilenir ve geçmiş temizlenir. Bulutta Meta anahtarı artık ortamın API kimlik bilgisinde (VM'ye girmez);
  `.env`'deki eski Meta anahtarının iptali ve Anthropic anahtarının yenilenmesi kullanıcıda.
- **S2.** GitHub belirteci Setup script metninde (ortamı kullanan herkes görür). Sızarsa depoyu ve
  `.env`'i okutur. `unset`, root'un `/proc/<pid>/environ` okumasına karşı korumaz (DECISIONS §54).
  Sızıntı taraması yalnız günlüklerde, `/etc/profile.d`'de ve `.git/config`'te yapıldı (0 bulgu);
  daha geniş tarama izin denetimine takıldı, yapılmadı.

### 4.7 Doğrulanmamış kayıtlar

- §6'da **[DOĞRULANMADI]** işaretli yedekler (`572ef57`, `18fd298` bundle'ları; `ee7b2dd`'nin yerel yedeği): buluttan
  görülemez. 26 Eylül 01:06 koşusunda düşen testin adı kaydedilmedi (muhtemelen B6'daki Lean testi).
- Arşiv §4'teki "önce" ölçümlerinden kodu geri almadan üretilemeyenler (7/7, 54 çift, 0.990…) kayıttan.
- Alandaki önyükleyici metninin içeriği (yalnız uzunluk eşleşiyor: 750 + 93 = 843).
- B1, B6, B10 ve K4'teki işaretli maddeler.

## 5. Son ölçülen sayılar (kapılar, `3e1805d`; aksi yazılmadıkça `7d9e9a1` ve öncekilerle aynı)

| Kapı | Değer | Hedef |
|---|---|---|
| Birim testleri | 1639 passed / 5 skipped | hepsi geçer |
| pyflakes | 0 bulgu | 0 |
| Cevap düzeyi pozitif / negatif precision; kapsama | 1.000 / 1.000; 1.000 | ≥ 0.98; ≥ 0.85 |
| B hücresi yanlış red; anahtar sızma testi | 0.000; geçti | < 0.10; zorunlu |
| Çözüm düzeyi pozitif precision; D tespiti | 0.994 (1 FP, V1); 0.976 (41/42) | raporlanır |
| Lean erişilebilir; sertifika; FP; junk | evet; 121/280; 0; 0/33 | —; —; 0; 0 |
| Adversaryal saldırı başarısı (3 yüzey) | %0 (21 139 saldırı; UNKNOWN'a düşen 2890, önce 2894) | < %2 |
| Yanlış onay / eşdeğerde red / değer olmayan iddia / adım dönüşümünde red | 0/448, 0/214, 0/46, 0/184 | 0 |
| Nedeni açıklanmayan kaçırılan bozuk adım; adım lokalizasyonu | 0/6; 75/120 (önce 74) | 0; raporlanır |

Raporlar `reports/*.md` (üretilir, elle yazılmaz), kapı günlüğü `reports/check_full.log`.
Süre: `--full` bulutta **~25–30 dk** (4 süreçli adversaryal 734–811 s), Windows'ta 31 dk; hızlı `check.py` ~7 dk (427 s).

## 6. Dallar, etiketler, yedekler

- **Dallar** (`git ls-remote origin`, 28 Eylül akşam): `master` `2f11c84` (`wqedwad/asd#10`'un birleşmesi);
  **`claude/busy-bardeen-ckr5bw`** (bu dal, `wqedwad/asd#11`, birleşmedi);
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

- **Yedek yöntemi** (her `master` birleştirmesinden hemen önce, yerel checkout `C:\Users\kullanici\mathverify`'da): (1) `git tag
  yedek/master-YYYY-MM-DD[-N] master`; (2) `git bundle create C:/Users/kullanici/mathverify-yedek/mathverify-master-<kısa-hash>-YYYY-MM-DD.bundle
  --all`, `git bundle verify` ve deneme klonu; (3) `git push origin <etiket>`; (4) hemen önce `scripts/check.py --plan`.
  Geri dönüş `git reset --hard <etiket>`. Birleştirme PR ile ya da yerelde; buluttan `master`/etiket push edilmez.

## 7. Bulut özeti (ölçülmüş)

- Makine: Ubuntu 24.04, 4 CPU, 15 GB RAM, ~30 GB disk, root, checkout `/home/user/asd`; sistem `python3`
  3.11 (kanca 3.14.6'yı `/opt`'tan, yoksa 3.12/3.13'ü seçer). Ağ (Trusted): açık GitHub, PyPI,
  `raw.githubusercontent.com`, `api.anthropic.com`; kapalı `releases.lean-lang.org`, `cache.mathlib.org`,
  `releases.astral.sh` (Lean, Mathlib önbelleği ve Python araç ref'inden gelir); `api.meta.ai` kimlik bilgisiyle açık.
- Kurulum betiği aşamasında GitHub git vekili yok; özel depoya kimliksiz 401. claude.ai ortam
  değişkenleri betiğe ulaşmaz; belirteç önyükleyicinin metninde (DECISIONS §53–§54, §56).
- Kanca (`scripts/cloud/session_start.sh`) 6–15 s; eksikse Lean'i arka planda kurar (167–239 s).
  Kurulum `/opt`'ta ~10.7 GB. Devam ettirilen sohbet kurulum betiğini hiç koşturmaz; disk korunur.
- **Konteyner, tur bitince uzun iş sürerken SIGTERM ile kapatılabiliyor** (26 Eylül, ~57 dk'lık
  `--full` kayboldu): tur bitirilmez, koşu ön planda ≤10 dk'lık beklemelerle izlenir (`CLAUDE.md`).
- Meta vekil üzerinden (DECISIONS §63): akışsız çağrı ~31 s'de 502; akış çalışır ama bazen `usage`'sız kesilir
  (istemci yeniden dener); çok uzun `xhigh` akıl yürütmede Meta 504 verir.
- Stop kancası commit edilmemiş değişiklikte commit + push ister. `ANTHROPIC_BASE_URL` istemcide
  okunmaz (DECISIONS §48). Bulutta `rsync` yok; alt ajanlara kopya komutu denenerek verilir (CLAUDE.md).

## 8. Komutlar

`PY=.venv/bin/python` (Windows: `.venv/Scripts/python.exe`); her komutta `PYTHONUTF8=1`, proje kökünde.

| Komut | Ne |
|---|---|
| `$PY -m pytest tests -rs` | Takım, atlama nedenleriyle |
| `$PY scripts/check.py --plan [--no-fetch]` | Hangi kontrol gerekli: YOK / TAMAM (çıkış 0) / TAM (1) (DECISIONS §59, CLAUDE.md) |
| `$PY scripts/check.py` / `--full` | Hızlı (~7 dk) / 24 kapı (~26 dk bulutta; günlüğü kendisi yazar, arka planda izlenir) |
| `$PY -m harness.run_eval` · `run_lean --timeout 45` · `adversarial [--workers N]` · `soundness_fuzz` · `calibrate` | Tek tek ölçümler → `reports/` (`--full`dan sonra koşulursa `--plan` o koşuyu kabul etmez; `git restore reports/`) |
| `$PY denetim/2026-09-2{6,7,8}/mutasyon.py [-j N] [ön ek…]` | Mutasyon denetimleri: kural/bekçi/tarama (README 26'da), Lean ısınması/kalibrasyon/günlükler (§60), K4 düzeltmeleri (§63) |
| `$PY -m harness.run_solver --family meta --max-cost 10 --workers 6` | K4 (kredili; aynı istekler kilitle sıralanır, önbellekten gelenler ücretsiz ama sınıra sayılır) |
| `$PY -m harness.run_f3 --workers 6 --pathb --max-cost 40 --solver-family …` | Kredili F3/F4 (`--no-l4/--no-l5/--no-l6`, `--limit`, `--ids`) |
| `$PY scripts/verify_cli.py --item evalset/items/tyt-prob-001.json [--lean] [--text "…"]` | Tek öğe |
| `$PY evalset/build/build_all.py` | 280 öğeyi yeniden üretir |
| `denetim/2026-09-25/araclar/olc.sh src <dizin>` + `say.py <dizin>` | 25 Eylül denetiminin ölçümleri (README orada) |

Kurulum (Linux; bulutta kanca yapar): `docs/BULUT.md` §4, Lean `docs/LEAN_SETUP.md`. Ortam
değişkenlerinin tam tablosu arşiv §9 ve `docs/BULUT.md` §5.

## 9. Nerede ne var

- **Arşiv** `docs/arsiv/HANDOFF-2026-09-26.md`: §0 bulut tarihçesi ve olaylar (0.9 `master`ın erken
  birleşmesi, 0.10 WSL diskinin C:'yi doldurması), §1 proje, §2 mimari ve klasör yapısı, §3 kararlar
  ve reddedilen seçenekler, **§4 denenen ve işe yaramayanlar (tekrar denenmez)**, §8 kritik dosyalar,
  §9 komutlar ve ortam değişkenleri, §11 tuzaklar (SymPy, ayrıştırıcı, Lean, Windows, bulut).
- **`DECISIONS.md`:** §1 kilitli kararlar, §7 (34–43) GitHub/bulut, 44–54 bulut ölçümleri, §8 (55)
  25 Eylül denetimi, §9 (56), §10 (57–58), §11 (59) paralel tarama ve kademeli kontrol, §12 (60–62) soğuk Lean,
  kalibrasyon, K4 düzeneği ve kısmi koşu, §13 (63) K4'ün tamamlanması, adım reddedici düzeltmeleri, Meta akışı.
- **`docs/`:** `ARCHITECTURE`, `QUALITY`, `SOLVER_FORMAT`, `LLM_LAYERS`, `LEAN_SETUP`, `E1-E10-measurement`,
  `BULUT` (§12, §13), `sartname/`; `reports/arsiv/` (iki F3 JSON'u üretilemez); `denetim/` (ölçüm betikleri).
