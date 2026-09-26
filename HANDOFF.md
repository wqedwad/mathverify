# HANDOFF — mathverify (güncel durum)

> **Son güncelleme: 26 Eylül 2026**, dal `claude/trusting-curie-76slml`. Bu belge yalnız **bugünün**
> durumunu, açık işleri ve sırayı taşır; ~300 satırı geçmez. Tarihçe burada birikmez: 26 Eylül'e
> kadarki 2102 satırlık belge `docs/arsiv/HANDOFF-2026-09-26.md`'de (§0–§12). Kararlar ve gerekçeleri
> `DECISIONS.md`'de, kalıcı kurallar `CLAUDE.md`'de, bulut işletimi `docs/BULUT.md`'de.
> **[DOĞRULANMADI]** = ölçülmedi ya da yalnız çıkarım; işaretsiz her sayı ölçümden gelir. DECISIONS ve
> BULUT'taki 26 Eylül öncesi "HANDOFF §N" göndermeleri arşivdeki numaralara aittir.

## 0. İlk 10 dakika

1. `CLAUDE.md` (kurallar) → bu belge → `DECISIONS.md` §55–§57 (son üç karar). Bulutta ayrıca
   oturum başındaki `[mathverify bulut oturumu …]` bloğu ve `docs/BULUT.md`.
2. `git status`, `git log --oneline -5`. Yeni bir bulut sohbeti `master`dan başlar; başka bir dalda
   birleşmemiş iş varsa `git ls-remote origin` ile görülür (§6).
3. Takım: `PYTHONUTF8=1 .venv/bin/python -m pytest tests` (Windows'ta `.venv/Scripts/python.exe`).
   Beklenen (Linux, Lean kurulu): **1323 passed / 5 skipped / 0 failed**, ~250–330 s (atlananlar: 3
   root altında salt okunur dizin, 1 isteğe bağlı indirme, 1 kapsam dışı ifade). Lean yüzünden atlama
   Lean'in hazır olmadığını gösterir (`-rs`). `addopts` `-q` içerir; ek `-q` özet satırını siler.
4. §3'teki ilk işe geç. Tekrar denenmemesi gerekenler: arşiv §4.

## 1. Proje (kısaca)

Türkçe bir matematik sorusu (TYT/AYT ya da üniversite) ve bir AI'ın çözümü verildiğinde çözüme
**üç değerli** karar verir: CORRECT / INCORRECT / UNKNOWN. Karar kanıtla verilir (sertifikalar, adım
reddedici, Lean 4 + Mathlib). Cevap anahtarı hatta hiç girmez. LLM katmanları (L4/L5/L6') kararı
yalnız daha temkinli yapabilir. Değişmez ilkeler `CLAUDE.md`'de (1–13). Mimari, yetki tablosu ve
kararların gerekçesi arşiv §2–§3'te ve `docs/ARCHITECTURE.md`'de. Kilitli kararlar D1–D6
(`DECISIONS.md` §1) yeniden sorulmaz. Giriş noktaları: `mathverify.verifier.verify` (deterministik),
`mathverify.pipeline.run_pipeline` (LLM'li tam hat), `scripts/verify_cli.py`, `scripts/check.py`.
Değerlendirme seti 280 sentetik öğe (A/B/C/D = %30/%25/%30/%15), ÖSYM metni yok.

## 2. Durum (26 Eylül 2026)

**Kod.** `master` = `fa94093` (`wqedwad/asd#4`: bu belgenin yeniden yapılandırılması, yalnız belgeler
ve bir yorum). Ondan önce `e07d4f7` (`wqedwad/asd#3`: `check.py` günlük başlığı ve soğuk Lean ısıtması
düzeltmeleri, DECISIONS §56). Birleşmemiş dal yok. Kodda yarım iş yok.

**Fazlar.** F0–F2, F5 (Lean), F6 (adversaryal + kalibrasyon), F7 (Lean şablonları): tamam ve ölçüldü.
F3 (LLM ön yüzü, L4, L5): kod tamam, **ölçüm yarım ve eski** (18 Eylül kodu, 218 öğenin 64'ü, kredi
bitti). F4 (kritik + meta-doğrulama): kod tamam, çevrimdışı testli, **hiç koşmadı**. Denetimler:
20 Eylül (11 boşluk), 23 Eylül (4 yanlış onay sınıfı + tanımlılık), 25–26 Eylül (kod çalıştırma,
cebir/kalkülüs/geometri/girdi sınıfları, formal katmanda 53/98 yanlış sertifika → 0/99; DECISIONS §55).

**Son `check.py --full`.** **24/24**, `e933ffb` (kodu `master` `fa94093` ile aynı), bulutta
11:09–12:26 UTC, ~77 dk (adversaryal 3764 s), 1323 passed / 5 skipped. Önceki: `5414d6b`, 59 dk.

**Bulut.** Kurulum betiği alanda, belirteç önyükleyicinin `T=''` satırında. 26 Eylül sabahı alandan
ilk kez `OK mode=all` 180 s (git + belirteç yolu). **Ama bu oturumda (26 Eylül 11:00 UTC, yeni
sohbet) anlık görüntü kullanılmadı**; betik baştan koştu ve 250 s sınırında kesildi (§4.1 B1–B2).

## 3. Sıradaki adımlar (sırayla)

1. **Yedek etiketleri (isteğe bağlı, yerelde):** PR #3 (`ee7b2dd`) ve PR #4 (`e07d4f7`) öncesi
   `master` için etiket yok (§6). PR #4'te kullanıcı, kod değişikliği olmadığı için yedek almamayı
   seçti. Sonraki kod birleştirmelerinde kural yine geçerli: etiket + bundle.
2. **Bulut kurulum kararı** (B1–B2): anlık görüntü yeniden kullanılmıyorsa her yeni sohbet açılmadan
   ~3–4 dk bekliyor ve üstüne kanca kalanı kuruyor. Seçenekler: (a) bir yeni sohbette daha ölçmek
   (görüntü bir kez mi kaçtı?); (b) betiği ~5 dk yönergesine kadar uzatmak (`timeout` 250 → ~280 s)
   ya da REPL derlemesini kancaya bırakmak; (c) Setup script'i boşaltıp kurulumu yalnız kancaya
   bırakmak (sohbet hemen açılır, Lean ~3–4 dk arka planda). Karar kullanıcının; ölçmeden kod yok.
3. **Küçük, krediye bağlı olmayan:** `fetch_artifacts.log`'un üzerine yazılması (B3) ve kalibrasyon
   raporunun belirlenimsiz satır sırası (T4); ikisi bir `--full`'la birlikte yapılabilir.
4. **Gerçek bir yeniden başlatmadan sonra** ilk `--full`'un `lean_warmup` satırı okunur (B6):
   `exit 0` beklenir, süre 300 s'yi aşabilir. Yeniden başlatma: devam ettirilen sohbette `uptime`
   birkaç dakika.
5. **Kod dondurma → anahtarları yenileme → F3 baştan, F4 ilk kez** (K1–K3; kullanıcı kararı,
   23 Eylül). Önce kalibrasyon koşusu (`run_f3 --limit 10 --workers 3 --max-cost 5`), sonra tam koşu.
6. **Gerçek veri** (K4) ve **açık kapsama işleri** (§4.2). Hepsi kullanıcı kararı ister (§4.4).

## 4. Açık maddeler (tam liste)

Kaynak: arşivdeki §0.8–§0.14, §5–§7, §12, DECISIONS §53–§57 ve BULUT §12. Bir madde yalnız kapandığında,
kanıtıyla birlikte (DECISIONS'ta) buradan çıkarılır.

### 4.1 Bulut ve ortam

- **B1. Anlık görüntü kullanılmadı** (bu oturum, ölçüm; DECISIONS §56 Ek, BULUT §12). Başarılı
  koşudan (07:39–07:42 UTC) ~3,5 saat sonra açılan yeni sohbette platform `session_mode: "new"` ile
  11:00:50'de betiği yeniden koşturdu (`script_length: 843`, aynı uzunluk: metnin değişmediği
  çıkarım); plan `python=1 uv-prewarm=1 lean=1`, yani `/opt` boştu. Sohbet açılmak için 252 s bekledi,
  kanca "Lean: KURULUYOR" yazdı. Belgeye göre görüntü ~7 gün kullanılmalıydı; neden **[DOĞRULANMADI]**.
- **B2. 250 s sınırı aşıldı** (bu oturum). Çekim 66 s, doğrulama 4, python 1, uv ön ısıtma 17
  (paralel), `setup_lean` 156 s; REPL aşamasında 250 s'de durduruldu (`reason=terminated`; durum
  dosyası artık kancanın `OK mode=lean` satırını taşıyor, `setup_env.log`'da "stopped by a signal
  after 250s"). Sabah 180 s'ydi. Kanca kalanı 42 s'de kurdu. Süre 180–250 s arasında oynuyor.
- **B3. Bu koşunun çekim yolu bilinmiyor:** kancanın `--lean-only` koşusu `fetch_artifacts.log`'u
  sıfırladı (`setup_env.log` ekleyerek yazıyor). Düzeltme: çekim günlüğü de eklemeli yazmalı.
- **B4.** `raw.githubusercontent.com` dosya indirme yolu kurulum aşamasında hiç koşmadı (yedek;
  oturum içinde 32 s, 5/5 OK). DECISIONS §54.
- **B5.** "claude.ai ortam değişkenleri kurulum betiğine hiç ulaşmıyor mu": kanarya
  (`MATHVERIFY_SETUP_CANARY=1`) eklenmedi, sınanmadı. Düzeni etkilemiyor.
- **B6. Soğuk Lean açılışı.** Yeniden başlatmadan sonra ilk `import Mathlib` ~340–400 s. `5414d6b`
  ısıtmayı kendi `LeanClient(boot_timeout=900)` istemcisiyle yapar; soğuk yolda **[DOĞRULANMADI]**
  (bu oturumda Lean yeni kurulmuştu, ısınma 12 s). Yavaşlığın nedeni **[DOĞRULANMADI]**. Kancanın
  arka planda ısıtması önerildi, yapılmadı; ancak gerçek bir yeniden başlatmada ölçülerek eklenir.
- **B7. Belirteç yenileme** (süresi dolunca): GitHub'da yeni fine-grained belirteç (Contents:
  read-only, yalnız `wqedwad/asd`), Setup script'in `T='...'` satırına. Süresi dolmuş belirteç bir
  şey bozmaz: çekim düşer, kanca kurar (167–239 s).
- **B8.** Etiket ve `master` buluttan push edilmez (kural); etiket push'u bulutta hiç denenmedi.
- **B9.** Lean istemcisinin bulutta bellek tüketimi ölçülmedi (WSL'de ~7.2 GB PSS; makine 15 GB).
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

1. Yedek etiketleri ve bundle'lar ne zaman silinebilir? Sormadan silinmez (§6).
2. Anthropic bakiyesi ne zaman, ne kadar? (F3 ~10 $, F4 ~15–25 $; F3/F4 kod dondurulunca.)
3. Gerçek çözücü çıktıları: hangi model/uygulama, kaç çözüm, etiketleri kim koyacak?
4. Lisans ve CI (uzak depo özel GitHub `wqedwad/asd`; CI ve LICENSE yok). CI açılırsa hızlı
   `scripts/check.py` koşar; Lean ve `--full` kurulum ister.
5. `tyt-prob-018` kuralı F4'ten sonra daraltılsın mı (V1)?
6. API anahtarları ne zaman yenilenecek (§4.6)?
7. Çözücü sembolü adımları: sınır kabul mü, yapısal formata sembol tanımı mı (V2)?
8. Başka sağlayıcıyla (GPT/Gemini, `set_client_override`) ölçüm istenir mi?
9. Uygulamanın adı ve ayrıntıları (ne depoda ne şartnamede).
10. Ekstremum/türev/seride tanımsız nokta: çekimserlik yeter mi (V3)?
11. `refs/arac/bulut-v1` silinsin mi (v2 doğrulandı, v1'in içeriğini taşıyor)? Sormadan silinmez.
12. Depo herkese açılacak ya da paylaşılacak mı? Açılırsa önce anahtarlar yenilenir ve `.env`
    geçmişten temizlenir.
13. Bulut kurulumu: §3 adım 2'nin (a)/(b)/(c) seçeneği.
14. Birleşmiş uzak dallar (`bulut-2026-09-24`, `claude/funny-cray-bey5o1`, `-compassionate-shannon-…`,
    `-practical-faraday-…`, `-trusting-curie-…`; hepsi `master`da, §6) silinsin mi?

### 4.5 Teknik borç

- **T1.** `DECISIONS.md` bölüm sırası 1, 2, 3, 6, 4, 5, 7–10; madde numaraları atlıyor; §2 ve §3.9
  bilerek Faz 1 anlık görüntüsü ("180 öğe").
- **T2.** Biçimlendirici yok; pyflakes dışında stil denetimi yok. **T3.** CI yok.
- **T4.** Kalibrasyon raporunda eşit ağırlıklı satırların sırası koşudan koşuya değişiyor
  (`fit`'te `set(...)` yinelemesi). Üç tohumda sonuçlar aynı; `score` toplam sırasının bir eşikte
  kararı çevirip çeviremeyeceği ölçülmedi. Öneri: `(-abs(ağırlık), ad)` sırası, `sorted(set(...))`.
- **T5.** `reports/lean_setup.log` eski `stable` kurulumunun günlüğü (sabit kurulumunki bulutta
  `/opt/mathverify-logs/setup_lean.log`). **T6.** 26 Eylül öncesi `check_full.log` başlıklarında
  "commit edilmemiş değişiklik" sayısından 1 düşülür (günlük kendini sayıyordu; `3925180`).
- **T7.** `docs/BULUT.md` ~1070 satır ve tarihçe biriktiriyor (§12'de sonradan kapanmış üç madde
  hâlâ `[ ]`); buradaki gibi güncel durum + arşiv ayrımı gerekebilir.

### 4.6 Güvenlik

- **S1.** `.env` kullanıcı kararıyla özel depoda izleniyor
  (DECISIONS §35); değerler git geçmişinde ve GitHub'da. F3/F4'ten önce yenilenir; depo açılırsa önce
  yenilenir ve geçmiş temizlenir. Geçerlilikleri en son 19 Eylül'de görüldü **[DOĞRULANMADI]**.
- **S2.** GitHub belirteci Setup script metninde (ortamı kullanan herkes görür). Sızarsa depoyu ve
  `.env`'i okutur. `unset`, root'un `/proc/<pid>/environ` okumasına karşı korumaz (DECISIONS §54).
  Sızıntı taraması yalnız günlüklerde, `/etc/profile.d`'de ve `.git/config`'te yapıldı (0 bulgu);
  daha geniş tarama izin denetimine takıldı, yapılmadı.

### 4.7 Doğrulanmamış kayıtlar

- `yedek/master-2026-09-24-2` (`572ef57`) ve `yedek/master-2026-09-25` (`18fd298`) etiketlerinin
  bundle'ı yerel makinede var mı: buluttan görülemez. PR #3'ten önceki `master` (`ee7b2dd`) için
  GitHub'da etiket yok; yerelde yedek alınıp alınmadığı bilinmiyor.
- 26 Eylül 01:06 koşusunda düşen testin adı kaydedilmedi (en olası `test_lean_client_survives_a_timeout`).
- Arşiv §4'teki "önce" ölçümlerinden kodu geri almadan üretilemeyenler (7/7 iddia, 54 çift,
  `Bilmiyorum` 0.990, 13 öğe, junk 0.995, 245/260, `}` saldırısı) yalnız kayıttan.
- Alandaki önyükleyici metninin içeriği (yalnız uzunluk eşleşiyor: 750 + 93 = 843).
- B1, B6 ve B10'daki işaretli maddeler.

## 5. Son ölçülen sayılar (kapılar, `e933ffb`; `5414d6b` ile aynı)

| Kapı | Değer | Hedef |
|---|---|---|
| Birim testleri | 1323 passed / 5 skipped | hepsi geçer |
| pyflakes | 0 bulgu | 0 |
| Cevap düzeyi pozitif / negatif precision; kapsama | 1.000 / 1.000; 1.000 | ≥ 0.98; ≥ 0.85 |
| B hücresi yanlış red; anahtar sızma testi | 0.000; geçti | < 0.10; zorunlu |
| Çözüm düzeyi pozitif precision; D tespiti | 0.994 (1 FP, V1); 0.976 (41/42) | raporlanır |
| Lean erişilebilir; sertifika; FP; junk | evet; 121/280; 0; 0/33 | —; —; 0; 0 |
| Adversaryal saldırı başarısı (3 yüzey) | %0 (21 139 saldırı; UNKNOWN'a düşen 2894) | < %2 |
| Yanlış onay / eşdeğerde red / değer olmayan iddia / adım dönüşümünde red | 0/448, 0/214, 0/46, 0/184 | 0 |
| Nedeni açıklanmayan kaçırılan bozuk adım | 0/6 | 0 |

Raporlar `reports/*.md` (üretilir, elle yazılmaz), kapı günlüğü `reports/check_full.log`.
Süre: bulutta 39–63 dk, yerel Linux ~36 dk, Windows ~68 dk; adversaryal tek başına 21–58 dk.
`e933ffb` günlüğü, koşu sürerken yapılan bir `git stash` yüzünden kesildi; aynı metni taşıyan
stdout'undan geri kondu (DECISIONS §57).

## 6. Dallar, etiketler, yedekler

- **Dallar** (`git ls-remote origin`, 26 Eylül): `master` `fa94093`; `claude/trusting-curie-76slml`,
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
  | yok | `e07d4f7` (PR #4 öncesi) | alınmadı (kullanıcı kararı: yalnız belge değişikliği) |

- **Yedek yöntemi** (her `master` birleştirmesinden hemen önce, yerel checkout'ta): (1)
  `git tag yedek/master-YYYY-MM-DD[-N] master`; (2) `git bundle create
  C:/Users/kullanici/mathverify-yedek/mathverify-master-<kısa-hash>-YYYY-MM-DD.bundle --all`, sonra
  `git bundle verify` ve deneme klonu; (3) `git push origin <etiket>`. Geri dönüş
  `git reset --hard <etiket>`. Yerel checkout `~/mathverify` (Windows `C:\Users\kullanici\mathverify`).
  Birleştirme PR ile ya da yerelde; buluttan `master`/etiket push edilmez.

## 7. Bulut özeti (ölçülmüş)

- Makine: Ubuntu 24.04, 4 CPU, 15 GB RAM, ~30 GB disk, root, checkout `/home/user/asd`. Sistem
  `python3` 3.11; kanca 3.14.6'yı `/opt`'tan, yoksa 3.12/3.13'ü seçer.
- Ağ (Trusted): açık GitHub, PyPI, `raw.githubusercontent.com`, `api.anthropic.com`; kapalı
  `releases.lean-lang.org`, `cache.mathlib.org`, `releases.astral.sh`, `api.meta.ai`. Lean, Mathlib
  önbelleği ve Python araç ref'inden gelir.
- Kurulum betiği aşamasında GitHub git vekili yok; özel depoya kimliksiz 401. claude.ai ortam
  değişkenleri betiğe ulaşmaz; belirteç önyükleyicinin metninde (DECISIONS §53–§54, §56).
- Kanca (`scripts/cloud/session_start.sh`) 6–15 s; eksikse Lean'i arka planda kurar (167–239 s).
  Kurulum `/opt`'ta ~10.7 GB. Devam ettirilen sohbet kurulum betiğini hiç koşturmaz; disk korunur.
- **Konteyner, tur bitince uzun iş sürerken SIGTERM ile kapatılabiliyor** (26 Eylül, ~57 dk'lık
  `--full` kayboldu): tur bitirilmez, koşu ön planda ≤10 dk'lık beklemelerle izlenir (`CLAUDE.md`).
- Platformun Stop kancası commit edilmemiş değişiklikte (ör. `check.py`'nin yazdığı `reports/`)
  commit + push ister. Claude Code `ANTHROPIC_BASE_URL` tanımlar; istemci onu okumaz (DECISIONS §48).

## 8. Komutlar

`PY=.venv/bin/python` (Windows: `.venv/Scripts/python.exe`); her komutta `PYTHONUTF8=1`, proje kökünde.

| Komut | Ne |
|---|---|
| `$PY -m pytest tests -rs` | Takım, atlama nedenleriyle |
| `$PY scripts/check.py` / `--full` | Hızlı (~3–5 dk) / 24 kapı (~36–68 dk; günlüğü kendisi yazar, arka planda izlenir) |
| `$PY -m harness.run_eval` · `run_lean --timeout 45` · `adversarial` · `soundness_fuzz` · `calibrate` | Tek tek ölçümler → `reports/` |
| `$PY -m harness.run_f3 --workers 6 --pathb --max-cost 40 --solver-family …` | Kredili F3/F4 (`--no-l4/--no-l5/--no-l6`, `--limit`, `--ids`) |
| `$PY scripts/verify_cli.py --item evalset/items/tyt-prob-001.json [--lean] [--text "…"]` | Tek öğe |
| `$PY evalset/build/build_all.py` | 280 öğeyi yeniden üretir |
| `denetim/2026-09-25/araclar/olc.sh src <dizin>` + `say.py <dizin>` | 25 Eylül denetiminin ölçümleri (README orada) |

Kurulum: Linux `uv venv --python 3.14 .venv && uv pip install --python .venv/bin/python -r
requirements.lock && uv pip install --python .venv/bin/python --no-deps -e .`; Lean
`bash scripts/setup_lean.sh && bash scripts/setup_lean_repl.sh` (Windows'ta `wsl -d Ubuntu --`
önekiyle; `docs/LEAN_SETUP.md`). Ortam değişkenlerinin tam tablosu arşiv §9 ve `docs/BULUT.md` §5.

## 9. Nerede ne var

- **Arşiv** `docs/arsiv/HANDOFF-2026-09-26.md`: §0 bulut tarihçesi ve olaylar (0.9 `master`ın erken
  birleşmesi, 0.10 WSL diskinin C:'yi doldurması), §1 proje, §2 mimari ve klasör yapısı, §3 kararlar
  ve reddedilen seçenekler, **§4 denenen ve işe yaramayanlar (tekrar denenmez)**, §8 kritik dosyalar,
  §9 komutlar ve ortam değişkenleri, §11 tuzaklar (SymPy, ayrıştırıcı, Lean, Windows, bulut).
- **`DECISIONS.md`:** §1 kilitli kararlar, §7 (34–43) GitHub/bulut, 44–54 bulut ölçümleri, §8 (55)
  25 Eylül denetimi, §9 (56) 26 Eylül bulut ölçümü, §10 (57) bu belgenin düzeni.
- **`docs/`:** `ARCHITECTURE`, `QUALITY` (literatür → mekanizma → kapı), `SOLVER_FORMAT`,
  `LLM_LAYERS`, `LEAN_SETUP`, `E1-E10-measurement`, `BULUT` (§12 ölçüm listesi, §13 routine
  istemleri), `sartname/` (kanonik şartname), `bulut_tani_2026-09-24.md`.
- **`reports/arsiv/2026-09-24/`:** rapor JSON'larının anlık görüntüsü; iki F3 dosyası yeniden
  üretilemez.
