# HANDOFF — mathverify (güncel durum)

> **Son güncelleme: 27 Eylül 2026 (öğle)**, dal `claude/dreamy-meitner-rvrwlj` (PR açık, birleşmedi; §3 adım 1).
> Bu belge yalnız **bugünün** durumunu, açık işleri ve sırayı taşır; ~300 satırı geçmez. Tarihçe burada birikmez: 26 Eylül'e
> kadarki 2102 satırlık belge `docs/arsiv/HANDOFF-2026-09-26.md`'de (§0–§12). Kararlar ve gerekçeleri
> `DECISIONS.md`'de, kalıcı kurallar `CLAUDE.md`'de, bulut işletimi `docs/BULUT.md`'de.
> **[DOĞRULANMADI]** = ölçülmedi ya da yalnız çıkarım; işaretsiz her sayı ölçümden gelir. DECISIONS ve
> BULUT'taki "HANDOFF §N" göndermeleri yazıldıkları günün HANDOFF'una aittir: 26 Eylül öncesininkiler
> arşive, 26 Eylül'ünkiler o commit'teki `HANDOFF.md`'ye (`git log -p HANDOFF.md`).

## 0. İlk 10 dakika

1. `CLAUDE.md` (kurallar) → bu belge → `DECISIONS.md` §57–§60 (son dört madde). Bulutta ayrıca
   oturum başındaki `[mathverify bulut oturumu …]` bloğu ve `docs/BULUT.md`.
2. `git status`, `git log --oneline -5`; birleşmemiş başka dal var mı: `git ls-remote origin` (§6).
   Bulut klonunda yerel `master` ve `origin/master` bayat olabilir: `git fetch origin master`.
3. Takım: `PYTHONUTF8=1 .venv/bin/python -m pytest tests -rs`. Beklenen (Linux, Lean kurulu): **1531
   passed / 5 skipped**, ~330 s (3 root salt okunur dizin, 1 isteğe bağlı indirme, 1 kapsam dışı
   ifade). Lean testi seçen oturum önce Lean'i ısıtır ("Lean ısınması: N s"; soğuk konteynerde ~345 s,
   B6); Lean yüzünden atlama = Lean hazır değil.
   `addopts` `-q` içerir; ek `-q` özeti siler. Hangi kontrolün gerektiği: `scripts/check.py --plan`.
4. §3'teki ilk işe geç. Tekrar denenmemesi gerekenler: arşiv §4.

## 1. Proje (kısaca)

Türkçe bir matematik sorusu ve bir AI'ın çözümüne **üç değerli** karar verir (CORRECT / INCORRECT /
UNKNOWN); karar kanıtla verilir (sertifikalar, adım reddedici, Lean 4 + Mathlib), cevap anahtarı hatta
girmez, LLM katmanları kararı yalnız daha temkinli yapar. İlkeler `CLAUDE.md`'de, mimari ve gerekçeler
arşiv §2–§3 ve `docs/ARCHITECTURE.md`'de; kilitli kararlar D1–D6 (`DECISIONS.md` §1) sorulmaz.
Giriş: `verifier.verify` (deterministik), `pipeline.run_pipeline` (LLM'li), `scripts/verify_cli.py`,
`scripts/check.py`. Değerlendirme seti 280 sentetik öğe (A/B/C/D = %30/%25/%30/%15).

## 2. Durum (27 Eylül 2026)

**Kod.** `master` = `wqedwad/asd#8`'in birleşmesi (öncesi `5c2f83e`, yedeği `yedek/master-2026-09-27`).
`#7`: adversaryal tarama 4 sürece dağıtıldı, kademeli kontrol kuralı `check.py --plan` ve çalışma anı
belge-okuma bekçisi. `#8`: `--plan` satırındaki üç görünüm kusuru düzeltildi (kararlar ve çıkış kodları
aynı). Dört inceleme turu, depodaki koşucuyla 162/162 mutasyon (DECISIONS §59); `src/` değişmedi.
**Bu dal** (`claude/dreamy-meitner-rvrwlj`, DECISIONS §60): düz `pytest` Lean testinden önce Lean'i
ısıtır (B6), kalibrasyon raporu tohumdan bağımsız (T4), çalışma anındaki kalibre skor uyumun skoru
(yan bulgu: `tyt-geo-009` eşiği yanlış tarafta geçiyordu), kurulum betiğinin aşama günlükleri
ekleyerek yazılır (B3); 21/21 mutasyon. Kodda yarım iş yok.

**Fazlar.** F0–F2, F5 (Lean), F6 (adversaryal + kalibrasyon), F7 (Lean şablonları): tamam ve ölçüldü.
F3 (LLM ön yüzü, L4, L5): kod tamam, **ölçüm yarım ve eski** (18 Eylül kodu, 218 öğenin 64'ü, kredi
bitti). F4 (kritik + meta-doğrulama): kod tamam, çevrimdışı testli, **hiç koşmadı**. Denetimler: 20, 23
ve 25–26 Eylül (formal katmanda 53/98 yanlış sertifika → 0/99; DECISIONS §26–30, §55).

**Son `check.py --full`.** **24/24**, `14d4e9d` (bu dalın son kodu), bulutta 27 Eylül 10:19:33–10:44:17 UTC,
**~25 dk** (adversaryal 772 s, 4 süreç, zaman aşımı 0), 1531 passed / 5 skipped; raporlar `f3105ef`'ninkilerden
yalnız süre satırlarında ve kalibrasyon tablosunun artık ada göre sıralı satırlarında farklı (DECISIONS §60).

## 3. Sıradaki adımlar (sırayla)

1. **Bu dalın PR'ı birleştirilecek mi** (kullanıcı kararı). `--plan`: TAM; son `--full` (24/24,
   `14d4e9d`) geçerli ve öteki bütün koşullar tutuyor, yalnız kuralın kendi dosyası `tests/conftest.py`
   değişti (ısınma kancasını yükleyen bir satır). Birleştirmeden önce yedek (§6 yöntemi) ve `--plan`.
2. **Windows'ta tam kontrol yarıda kaldı** (T8): ilk denemede testler sırasında ya da sonrasında Git Bash
   yanıt vermez oldu, kullanıcı durdurdu. Tam kontrol bulutta koşar; Windows'ta yeniden denenecekse
   Görev Yöneticisi'nde bellek izlenir ve donduğu adım günlükten okunur (günlük geri alınmadan önce).
3. **Yedek etiketleri (isteğe bağlı):** PR #3 ve PR #4 öncesi `master` için etiket yok (§6).
4. **Bulut kurulum kararı** (B1–B2: görüntü 13:35 sohbetinde kullanıldı, 11:00'dekinde kullanılmadı).
   Seçenekler: (a) bir iki yeni sohbette daha ölçmek (hangi koşulda `new` açılıyor?); (b) betiği ~5 dk
   yönergesine kadar uzatmak (`timeout` 250 → ~280 s) ya da REPL derlemesini kancaya bırakmak; (c) Setup
   script'i boşaltıp kurulumu yalnız kancaya bırakmak. Karar kullanıcının; ölçmeden kod yok.
5. **Soğuk açılışta `--full`:** gerçek bir yeniden başlatmadan sonraki ilk `--full`'da `lean_warmup`
   satırı okunur (B6): exit 0 beklenir, süre 300 s'yi aşabilir (düz pytest'in ısınması 345 s ölçüldü).
6. **Kod dondurma → anahtarları yenileme → F3 baştan, F4 ilk kez** (K1–K3; kullanıcı kararı,
   23 Eylül). Önce kalibrasyon koşusu (`run_f3 --limit 10 --workers 3 --max-cost 5`), sonra tam koşu.
7. **Gerçek veri** (K4) ve **açık kapsama işleri** (§4.2). Hepsi kullanıcı kararı ister (§4.4).

## 4. Açık maddeler (tam liste)

Kaynak: arşivdeki §0.8–§0.14, §5–§7, §12, DECISIONS §53–§60 ve BULUT §12. Bir madde yalnız kapandığında,
kanıtıyla birlikte (DECISIONS'ta) buradan çıkarılır.

### 4.1 Bulut ve ortam

- **B1. Anlık görüntü bazen kullanılmıyor** (DECISIONS §56 Ek, §59 (e); BULUT §12). 11:00 sohbeti
  `session_mode: "new"` ile betiği yeniden koşturdu (`/opt` boştu, sohbet 252 s bekledi, kanca "Lean:
  KURULUYOR"). 13:35 sohbeti ve 27 Eylül 09:39 sohbeti `resume-cached` ile açıldı: betik koşmadı, `/opt`
  26 Eylül 07:39'daki `setup-only` koşusunun (OK, 199 s) görüntüsünden geldi, kanca 2–3 s. Hangi koşulda `new` açıldığı **[DOĞRULANMADI]**.
- **B2. 250 s sınırı aşıldı** (11:00 sohbeti): çekim 66 s, `setup_lean` 156 s, REPL aşamasında
  durduruldu (`reason=terminated`); kanca kalanı 42 s'de kurdu. Süre 180–250 s arasında oynuyor
  (07:39'daki iki koşu 180 ve 199 s).
- **B4.** `raw.githubusercontent.com` dosya indirme yolu kurulum aşamasında hiç koşmadı (yedek; oturum
  içinde 32 s, 5/5 OK; DECISIONS §54). **B5.** "claude.ai ortam değişkenleri kurulum betiğine hiç
  ulaşmıyor mu": kanarya (`MATHVERIFY_SETUP_CANARY=1`) eklenmedi, sınanmadı; düzeni etkilemiyor.
- **B6. Soğuk Lean açılışı.** Yeniden başlatmadan ya da görüntüden sonra ilk `import Mathlib`
  ~340–400 s. Düz `pytest` artık ilk Lean testinden önce, testlerin 300 s sınırının dışında ısınır;
  27 Eylül soğuk konteynerde 345 s, 1514/5, Lean atlaması yok (DECISIONS §60). Açık: yavaşlığın nedeni
  (konuğun sayfa önbelleği değil: boşaltılınca 31 s; görüntü diskinin ilk okunması çıkarım
  **[DOĞRULANMADI]**) ve `--full`'un ısıtmasının soğuk yolda ölçülmesi (aynı 900 s bütçe; çıkarım).
- **B7. Belirteç yenileme:** yeni fine-grained belirteç (Contents: read-only, yalnız `wqedwad/asd`)
  Setup script'in `T='...'` satırına; süresi dolmuşsa çekim düşer, kanca kurar (167–239 s). **B8.**
  Etiket ve `master` buluttan push edilmez (kural); etiket push'u bulutta hiç denenmedi.
- **B9.** Bulutta `repl` süreci RSS 7.08 GB / PSS 6.78 GB (27 Eylül); `lake env`'in payı ölçülmedi
  (WSL'de istemci başına ~7.2 GB PSS; makine 15 GB).
- **B10. Kullanım/maliyet** (BULUT §8): tek seferlik bulut kredisinin kaynağı haber siteleri
  **[DOĞRULANMADI]**; abonelik sınırının token ağırlıklandırması yayımlanmamış **[DOĞRULANMADI]**;
  yerel tarafın maliyeti ölçülmedi.

### 4.2 Doğrulayıcı: bilinen sınırlar ve kapsama

Hiçbiri doğru cevabı reddetmez; ya UNKNOWN (kapsama kaybı) ya da bilinçli sınır.

- **V1. `tyt-prob-018`:** çözüm düzeyindeki tek yanlış onay (doğru ama gerekçesiz adım; sertifika
  L6 kritiğini ezer). Karar F4 ölçümüne bağlı (DECISIONS §3.3 ve §4, arşiv §3 karar 21). Davranış
  `test_a_true_but_unjustified_step_is_still_overruled_by_its_certificate` ile testli.
- **V2. Çözücünün kendi sembolüyle yazdığı adımlar denetlenmez** (ilke 5). +1 bozulan 46 adımın 6'sı
  kaçıyor (5'i bu sınıf, 1'i çözümsüz öncül); nedenler `soundness_fuzz.ACCEPTED_MISS_REASONS`'da,
  açıklanmayan kaçırma bir kapı. Kapatmak `docs/SOLVER_FORMAT.md` sözleşmesini değiştirir.
- **V3. Tanımlılık türev/ekstremum/seride yalnız çekimser:** "`x²/x`'in [−1, 1]'deki minimumu −1"
  UNKNOWN. Tanımsız noktaları dışlayarak hesaplama ölçülmedi. `antiderivative` yazıldığı biçimde
  tanımlılık için ayrıca sınanmadı.
- **V4.** Adımsız çözümde CORRECT yalnız cevap düzeyindedir (`answer_level_only`,
  `answer_from_option_letter`, `KAPSAM:` satırı); bayrağa bakmayan tüketici farkı görmez.
- **V5. 25 Eylül'de bilerek bırakılanlar** (DECISIONS §55): kanıtsız eşdeğer doğru biçimler
  ("(2x − y + 1)(x² + 1) = 0"), sembolik kanıtı olmayan kapalı biçimler, periyodik tanım kümeli
  ilkeller (∫1/(1+cos x)), sonsuz sınırlı integraller, kanıtsız floor/ceiling özdeşlikleri, gelenek
  farkı olan tek taraflı durumlar (√x'in 0'daki limiti), `asec`/`acsc` ayrıştırıcıda yok.
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
  suçlama, "sertifikanın iptal ettiği kritik raporu" (V1).
- **K3. Ön koşullar:** kod dondurulur (sonraki her değişiklik sayıları eskitir); anahtarlar yenilenir,
  `.env` güncellenip commit edilir; `--max-cost` olmadan koşulmaz; `llm_cache/` istek hash'iyle
  anahtarlı, değişen istem yeniden ücretlenir; bulutta ağ Custom + `api.meta.ai`
  (`api.anthropic.com` açık); ~0,066 $/öğe (yarım koşu).
- **K4. Gerçek AI çözücü çıktıları:** `--solver-family anthropic|meta` zorunlu. Etiketler kaba
  kuvvetle ya da ikinci kişiyle denetlenmeli (denetim derlemlerinde 4 etiket yanlış çıktı).

### 4.4 Kullanıcı kararları (açık sorular)

1. Ne zaman silinebilir (sormadan silinmez, §6): yedek etiketleri ve bundle'lar; `refs/arac/bulut-v1`
   (v2 doğrulandı, v1'in içeriğini taşıyor); `master`a girmiş uzak dallar (`bulut-2026-09-24`,
   `claude/funny-cray-bey5o1`, `-compassionate-shannon-…`, `-practical-faraday-…`, `-trusting-curie-…`,
   `-keen-ramanujan-…`).
2. Anthropic bakiyesi ne zaman, ne kadar (F3 ~10 $, F4 ~15–25 $; kod dondurulunca)? API anahtarları
   ne zaman yenilenecek (§4.6)?
3. Gerçek çözücü çıktıları: hangi model/uygulama, kaç çözüm, etiketleri kim koyacak?
4. Lisans ve CI (uzak depo özel GitHub `wqedwad/asd`; CI ve LICENSE yok). CI açılırsa hızlı
   `scripts/check.py` koşar; Lean ve `--full` kurulum ister.
5. Sınırlar: `tyt-prob-018` kuralı F4'ten sonra daraltılsın mı (V1)? Çözücü sembolü adımları sınır mı,
   yapısal formata sembol tanımı mı (V2)? Ekstremum/türev/seride tanımsız noktada çekimserlik yeter mi (V3)?
6. Başka sağlayıcıyla (GPT/Gemini, `set_client_override`) ölçüm istenir mi?
7. Uygulamanın adı ve ayrıntıları (ne depoda ne şartnamede).
8. Depo herkese açılacak ya da paylaşılacak mı? Açılırsa önce anahtarlar yenilenir, `.env` geçmişten
   temizlenir.
9. Bulut kurulumu: §3 adım 4'ün (a)/(b)/(c) seçeneği.

### 4.5 Teknik borç

- **T1.** `DECISIONS.md` bölüm sırası 1, 2, 3, 6, 4, 5, 7–11; madde numaraları atlıyor; §2 ve §3.9
  bilerek Faz 1 anlık görüntüsü ("180 öğe").
- **T2.** Biçimlendirici yok; pyflakes dışında stil denetimi yok. **T3.** CI yok.
- **T5.** `reports/lean_setup.log` eski `stable` kurulumunun günlüğü (sabit kurulumunki bulutta
  `/opt/mathverify-logs/setup_lean.log`). **T6.** 26 Eylül öncesi `check_full.log` başlıklarında
  "commit edilmemiş değişiklik" sayısından 1 düşülür (günlük kendini sayıyordu; `3925180`).
- **T7.** `docs/BULUT.md` ~1070 satır ve tarihçe biriktiriyor (§12'de sonradan kapanmış üç madde
  hâlâ `[ ]`); buradaki gibi güncel durum + arşiv ayrımı gerekebilir. Testler onu okuyor: kod sayılır.
- **T8. Windows'ta ölçülenler ve ölçülmeyenler** (DECISIONS §59): `.venv` kilitle eşit (32 paket; bulutta
  31, `colorama` yalnız Windows'ta), Lean ısınması 40 s. `--full` bitmedi (neden **[DOĞRULANMADI]**,
  bellek olabilir); 4 süreçli tarama (`spawn`), ebeveyn izleyicisi, bekçinin `CopyFile2`/junction yolu,
  `--plan`'ın buluttaki bir `--full`u Windows checkout'unda kabul etmesi ve süre ölçülmedi. **T9. Kuralın
  sınırları:** bekçi alt süreçleri ve `os.open(dir_fd=…)`'yu görmez (test dışı kodun `.md` sabitleri ve
  kabuk betikleri testlerle sabitlendi); koşu sırasında yapılıp bitmeden geri alınan değişiklik
  günlükten anlaşılmaz; günlük düz metin (raporlar özetle bağlı, sahteciliğe karşı koruma yok).

### 4.6 Güvenlik

- **S1.** `.env` kullanıcı kararıyla özel depoda izleniyor
  (DECISIONS §35); değerler git geçmişinde ve GitHub'da. F3/F4'ten önce yenilenir; depo açılırsa önce
  yenilenir ve geçmiş temizlenir. Geçerlilikleri en son 19 Eylül'de görüldü **[DOĞRULANMADI]**.
- **S2.** GitHub belirteci Setup script metninde (ortamı kullanan herkes görür). Sızarsa depoyu ve
  `.env`'i okutur. `unset`, root'un `/proc/<pid>/environ` okumasına karşı korumaz (DECISIONS §54).
  Sızıntı taraması yalnız günlüklerde, `/etc/profile.d`'de ve `.git/config`'te yapıldı (0 bulgu);
  daha geniş tarama izin denetimine takıldı, yapılmadı.

### 4.7 Doğrulanmamış kayıtlar

- §6'da **[DOĞRULANMADI]** işaretli yedekler (`572ef57`, `18fd298` bundle'ları; `ee7b2dd` için etiket
  yok, yerel yedeği bilinmiyor): yerel makinede var mı, buluttan görülemez.
- 26 Eylül 01:06 koşusunda düşen testin adı kaydedilmedi; aynı günün soğuk açılışında düşen
  `test_lean_proves_true_and_refuses_false` idi (B6), 01:06'daki de o olabilir.
- Arşiv §4'teki "önce" ölçümlerinden kodu geri almadan üretilemeyenler (7/7, 54 çift, 0.990…) kayıttan.
- Alandaki önyükleyici metninin içeriği (yalnız uzunluk eşleşiyor: 750 + 93 = 843).
- B1, B6 ve B10'daki işaretli maddeler.

## 5. Son ölçülen sayılar (kapılar, `14d4e9d`; `f3105ef`, `f93178f`, `a8edb0d` ve `5414d6b` ile aynı)

| Kapı | Değer | Hedef |
|---|---|---|
| Birim testleri | 1531 passed / 5 skipped | hepsi geçer |
| pyflakes | 0 bulgu | 0 |
| Cevap düzeyi pozitif / negatif precision; kapsama | 1.000 / 1.000; 1.000 | ≥ 0.98; ≥ 0.85 |
| B hücresi yanlış red; anahtar sızma testi | 0.000; geçti | < 0.10; zorunlu |
| Çözüm düzeyi pozitif precision; D tespiti | 0.994 (1 FP, V1); 0.976 (41/42) | raporlanır |
| Lean erişilebilir; sertifika; FP; junk | evet; 121/280; 0; 0/33 | —; —; 0; 0 |
| Adversaryal saldırı başarısı (3 yüzey) | %0 (21 139 saldırı; UNKNOWN'a düşen 2894) | < %2 |
| Yanlış onay / eşdeğerde red / değer olmayan iddia / adım dönüşümünde red | 0/448, 0/214, 0/46, 0/184 | 0 |
| Nedeni açıklanmayan kaçırılan bozuk adım | 0/6 | 0 |

Raporlar `reports/*.md` (üretilir, elle yazılmaz), kapı günlüğü `reports/check_full.log`.
Süre: `--full` bulutta **~25–26 dk** (4 süreçli adversaryal 772–811 s); tek süreçli eski koşular bulutta
39–77 dk, yerel Linux ~36 dk, Windows ~68 dk (Windows'ta yeni süre ölçülmedi). Hızlı `check.py` ~7 dk (427 s, ölçüldü).

## 6. Dallar, etiketler, yedekler

- **Dallar** (`git ls-remote origin`, 27 Eylül öğle): `master` `c2e4fdf` (`wqedwad/asd#8`'in birleşmesi);
  `claude/dreamy-meitner-rvrwlj` (bu dal, birleşmedi); `claude/keen-ramanujan-oqseru` (`wqedwad/asd#8`), `claude/trusting-curie-76slml` `1fddfc6`,
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

- **Yedek yöntemi** (her `master` birleştirmesinden hemen önce, yerel checkout'ta): (1)
  `git tag yedek/master-YYYY-MM-DD[-N] master`; (2) `git bundle create
  C:/Users/kullanici/mathverify-yedek/mathverify-master-<kısa-hash>-YYYY-MM-DD.bundle --all`, sonra
  `git bundle verify` ve deneme klonu; (3) `git push origin <etiket>`; (4) birleştirmeden hemen önce
  `scripts/check.py --plan` (CLAUDE.md). Geri dönüş `git reset --hard <etiket>`. Yerel checkout `~/mathverify` (Windows `C:\Users\kullanici\mathverify`).
  Birleştirme PR ile ya da yerelde; buluttan `master`/etiket push edilmez.

## 7. Bulut özeti (ölçülmüş)

- Makine: Ubuntu 24.04, 4 CPU, 15 GB RAM, ~30 GB disk, root, checkout `/home/user/asd`; sistem `python3`
  3.11 (kanca 3.14.6'yı `/opt`'tan, yoksa 3.12/3.13'ü seçer). Ağ (Trusted): açık GitHub, PyPI,
  `raw.githubusercontent.com`, `api.anthropic.com`; kapalı `releases.lean-lang.org`, `cache.mathlib.org`,
  `releases.astral.sh`, `api.meta.ai` (Lean, Mathlib önbelleği ve Python araç ref'inden gelir).
- Kurulum betiği aşamasında GitHub git vekili yok; özel depoya kimliksiz 401. claude.ai ortam
  değişkenleri betiğe ulaşmaz; belirteç önyükleyicinin metninde (DECISIONS §53–§54, §56).
- Kanca (`scripts/cloud/session_start.sh`) 6–15 s; eksikse Lean'i arka planda kurar (167–239 s).
  Kurulum `/opt`'ta ~10.7 GB. Devam ettirilen sohbet kurulum betiğini hiç koşturmaz; disk korunur.
- **Konteyner, tur bitince uzun iş sürerken SIGTERM ile kapatılabiliyor** (26 Eylül, ~57 dk'lık
  `--full` kayboldu): tur bitirilmez, koşu ön planda ≤10 dk'lık beklemelerle izlenir (`CLAUDE.md`).
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
| `$PY denetim/2026-09-26/mutasyon.py [-j N] [C G A]` | Kural, bekçi ve paralel taramanın mutasyon denetimi (README orada) |
| `$PY denetim/2026-09-27/mutasyon.py [-j N] [L K B]` | Lean ısınması, kalibrasyon, aşama günlükleri (DECISIONS §60) |
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
  25 Eylül denetimi, §9 (56) 26 Eylül bulut ölçümü, §10 (57) belge düzeni, (58) tam kontrol süresi,
  §11 (59) paralel tarama, kademeli kontrol, inceleme turları ve mutasyonlar, §12 (60) soğuk Lean,
  kalibrasyon sırası ve çalışma anı skoru, aşama günlükleri.
- **`docs/`:** `ARCHITECTURE`, `QUALITY`, `SOLVER_FORMAT`, `LLM_LAYERS`, `LEAN_SETUP`, `E1-E10-measurement`,
  `BULUT` (§12, §13), `sartname/`; `reports/arsiv/` (iki F3 JSON'u üretilemez); `denetim/` (ölçüm betikleri).
