# HANDOFF — mathverify (güncel durum)

> **Son güncelleme: 15 Ekim 2026, akşam (bulut)**, dal `claude/focused-albattani-jlomk1` (= `claude/amazing-edison-0g21ci` + kayıt; kodu `d342778`; birleşmedi): `master` (`#14`) + dördüncü denetimin düzeltmeleri (d4a, d4b tur 8, d4c tur 2, d4d, d4e tur 3, d4f tur 2, d4g); süren turlar bundle'da. **Durdurma kararı: A+** (kullanıcı, 15 Ekim; DECISIONS §89; plan §3 adım 2).
> Bu belge yalnız **bugünün** durumunu, açık işleri ve sırayı taşır; ~300 satırı geçmez. Tarihçe burada birikmez: 26 Eylül'e kadarki 2102 satırlık belge
> `docs/arsiv/HANDOFF-2026-09-26.md`'de (§0–§12). Kararlar ve gerekçeleri `DECISIONS.md`'de, kalıcı kurallar `CLAUDE.md`'de, bulut işletimi `docs/BULUT.md`'de.
> **[DOĞRULANMADI]** = ölçülmedi ya da yalnız çıkarım; işaretsiz her sayı ölçümden gelir. DECISIONS ve BULUT'taki "HANDOFF §N" göndermeleri yazıldıkları
> günün HANDOFF'una aittir: 26 Eylül öncesininkiler arşive, 26 Eylül'ünkiler o commit'teki `HANDOFF.md`'ye (`git log -p HANDOFF.md`).

## 0. İlk 10 dakika

1. `CLAUDE.md` (kurallar) → bu belge → `DECISIONS.md` §63–§89; bulutta oturum başı bloğu ve `docs/BULUT.md`.
2. `git status`, `git log --oneline -5`, `git ls-remote origin` (birleşmemiş dal, §6); bulut klonunda `git fetch origin master` (yerel
   `master`/`origin/master` bayat olabilir).
3. Takım: `PYTHONUTF8=1 .venv/bin/python -m pytest tests -rs` → bulutta **3212 passed / 5 skipped** (`1775b3f`, `--full` içinde; düz `pytest` soğuk
   Lean ısınmasıyla ~17–20 dk) (3 root salt okunur dizin, 1 isteğe bağlı indirme, 1 kapsam dışı ifade); Windows'ta `d914dbc`: 2064 passed / 106
   skipped (+4 yalnız `.git`'siz kopyada düşen kural testi; DECISIONS §73); sıcak Lean'le ~480 s, soğukta önce 345–470 s ısınma (B6). Lean yüzünden
   atlama = Lean hazır değil; ek `-q` özeti siler. Hangi kontrolün gerektiği: `scripts/check.py --plan`.
4. §3'teki ilk işe geç. Tekrar denenmeyecekler: arşiv §4.

## 1. Proje (kısaca)

Türkçe bir matematik sorusu ve bir AI'ın çözümüne **üç değerli** karar verir (CORRECT / INCORRECT /
UNKNOWN); karar kanıtla verilir (sertifikalar, adım reddedici, Lean 4 + Mathlib), cevap anahtarı hatta
girmez, LLM katmanları kararı yalnız daha temkinli yapar. İlkeler `CLAUDE.md`'de, mimari ve gerekçeler
arşiv §2–§3 ve `docs/ARCHITECTURE.md`'de; kilitli kararlar D1–D6 (`DECISIONS.md` §1) sorulmaz.
Giriş: `verifier.verify` (deterministik), `pipeline.run_pipeline` (LLM'li), `scripts/verify_cli.py`,
`scripts/check.py`. Değerlendirme seti 280 sentetik öğe (A/B/C/D = %30/%25/%30/%15).

## 2. Durum (15 Ekim 2026)

**Kod.** `master` = `wqedwad/asd#14`'ün birleşmesi (öncesi `aa67b20` = `#13`; `#9`, `#10`, `#12`–`#14` öncesi yedeksiz, kullanıcı talimatı;
`#11` öncesi `yedek/master-2026-09-28`, §6). Geçmiş PR'ların içeriği DECISIONS §59–§84'te (`#11` §63, `#12` §64–§70, `#13` §72–§74,
`#14` §75–§84). **Oturum dalı** `claude/focused-albattani-jlomk1` (birleşmedi; `claude/amazing-edison-0g21ci`'yi ve onun içerdiği
`-upbeat-mccarthy-…`, `-trusting-lovelace-…` dallarını içerir; DECISIONS §85–§89): dördüncü bağımsız denetimin düzeltmeleri; her birleşik ölçümde
558 çözümde karar farkı 0, tam takım (Lean'siz) temiz. **Dalda bilinen açık sorunlar var:** gerçekçi 19 madde (3 yanlış onay, 5 haksız ret, 11
kapsama kaybı; 13'ünü dördüncü denetim getirdi) ve yapay yanlış onaylar (V20); dal bu hâliyle birleştirilmez. `--full` koşulmadı.

**Fazlar.** F0–F2, F5 (Lean), F6 (adversaryal + kalibrasyon), F7 (Lean şablonları): tamam ve ölçüldü. F3 (LLM ön yüzü,
L4, L5): kod tamam, **ölçüm yarım ve eski** (18 Eylül, 218 öğenin 64'ü). F4 (kritik + meta-doğrulama): kod tamam,
çevrimdışı testli, **hiç koşmadı**. Denetimler: 20, 23, 25–26 Eylül (DECISIONS §26–30, §55).

**Son `check.py --full`.** **24/24**, `1775b3f` (`master`ın kodu, raporlar `a9434dc`), bulutta 1 Ekim 16:44:01–17:24:08 UTC, **~40 dk**
(ısınma 14 s, pytest 747 s, adversaryal 1084 s), 3212 passed / 5 skipped; `--plan` TAMAM (DECISIONS §83). Windows'ta son: `eab80f1` 24/24, 31 dk (DECISIONS §61).

**K4 (Muse Spark 1.3, 280 öğe, `776e5b4`; DECISIONS §63).** 278 çözüm: CORRECT|right 274, INCORRECT|right 4 (tek soru
`tyt-say-*`: çözücü `n`'i başka anlamda kullandı), yanlış onay **0**; çözücü 278/278 doğru (yakalama gücü ölçülemedi). Çözümsüz
2 (`tyt-esf-007/-014`: akış kesildi, sonra Meta 504). Harcama ~1.3 $.

## 3. Sıradaki adımlar (sırayla)

1. **Yeni sohbet:** `git fetch origin claude/focused-albattani-jlomk1 && git merge --ff-only FETCH_HEAD` (oturumun dalına; push yalnız oturumun
   dalına; dal adı değiştiyse `git ls-remote origin` ile en yeni oturum dalı). **A+ yarım işleri (15 Ekim):** `git fetch denetim/2026-10-01/d4/wip/wip-2026-10-15.bundle 'refs/heads/wip/*:refs/heads/wip/*'` (`wip/birlesik-a` birleşik dal, `wip/d4e-tur4` d4e tur 5, `wip/d4h` d4h tur 2; worktree'ler `/home/user/wt/{birlesik-a,d4e4,d4h,d4b9,d4c3}`), ajan notları `wip/notlar-2026-10-15.tar.gz` (`-C <scratchpad>`). Daha eski yarım işler (9 Ekim hâli): `git fetch denetim/2026-10-01/d4/wip/wip-2026-10-09.bundle 'refs/heads/wip/*:refs/heads/wip/*'` (`wip/d4b-tur9`
   d4b tur 10, `wip/d4c-tur3` d4c tur 4, `wip/d4e-tur4` d4e tur 4 (bitti), `wip/d4h` d4h tur 2, `wip/birlesik` = `443e078` d4c tur 3 +
   oturum dalı); her biri için `git worktree add /home/user/wt/<ad> wip/<dal>` (ajan notları worktree yolu olarak bunları anar).
   Ajan notları, sondalar, saldırı dizinleri, `fark_taban/taban.json`, `agir.sh` (iki slotlu sıra adaletli ağır süreç semaforu),
   `olc_sira.sh`: `tar -xzf denetim/2026-10-01/d4/wip/scratch-2026-10-09.tar.gz -C <scratchpad>`; eski scratchpad yolları
   (`…/0a3a0f70-…`, `…/e165cf01-…`, `…/fce620cb-…`) yeni scratchpad'e sembolik bağlanır. `--plan` koş. Oturum sınırı ~3–5 saatte bir
   doluyor ve konteyner yeniden başlıyor (8–9 Ekim'de 4 kez): ajanlar `SendMessage`, iş akışları resume, mutasyon `--kayit` ile sürer.
2. **Sıradaki iş: A+ (kullanıcı kararı 15 Ekim, DECISIONS §89).** Yöntem `denetim/2026-10-01/d4/duzeltme_kurallari.txt` ve Ek'leri (düzeltici
   ajan yeniden üretir ve matematik kararını yazar, ana oturum denetler; en çok 3 worktree'li ajan, ağır süreçler `agir.sh` ile en çok 2;
   beklemeler ≤10 dk; parçanın son hâlinde tam ölçüm). Bulgu envanteri `d4/a_arti/envanter.json` (263 kayıt), kural etkisi
   `kural_etkisi.json` (R01–R29). Sıra: (i) **d4b tur 10** bitir (`saldiri/d4b9/kararlar_tur10.txt`; d4b9-YO-1, RK-1 dahil);
   (ii) **d4c tur 4** son ölçümler (mutasyon T ve T4 partileri, tam takım; `saldiri/d4c3/kararlar_tur4.txt`); (iii) **d4e tur 5** = tur 4 +
   kendi getirdikleri (`saldiri/d4e4/bulgular.json`: YO-1, U2, U3, U4; RK-1 ve U5 yalnız INCORRECT → UNKNOWN; YO-2, YO-3 dar fail-closed, geniş
   hâlleri ders kitabı türevlerini bozar: §89); (iv) **d4h tur 2** bitir (`saldiri/d4h/kararlar_tur2.txt`; D1, PRE-RK-4/5 dahil; kendi getirdiği
   D4H-RK-1, D4H-YO-5 kapanır); (v) dördünü oturum dalında birleştir, birleşik ölçüm; (vi) **d4f'nin üç gerçekçi maddesi** kesin düzeltme
   (D4F2B-RK-1, RK-2, ONCEKI-1; `saldiri/d4f2/kararlar_tur3.txt`); (vii) kalan yapay açıklar dar fail-closed (d4f 3. turun geri kalanı, d4i
   CAP-K1, R01–R29'un açıkları), her kural derlemde ölçülür; (viii) **son saldırı** birleşik hâle, parça mercekli (d4d ve d4g 2. turları ve
   saldırılmamış son diff'ler dahil); gerçekçi bulgu kesin düzeltilir, yapay bulgu fail-closed; (ix) **yerel kalite:** V15 S1, R1 (karar:
   UNKNOWN), L1; V16'nın kalanı; (x) `--full`, belgeler, `--plan` TAMAM; birleştirme ve yedek kullanıcı onayıyla. V19'a dokunulmaz.
   `franklin`'in silinmesi kullanıcıya sorulur (§74).
3. **Kod dondurmadan önce sorulacak** (§4.4 madde 3): çözücü istemi IR sembollerinin anlamını versin mi (`tyt-say-*`).
4. **Kod dondurma → F3 baştan, F4 ilk kez** (K1–K3; anahtar yenileme önkoşul değil, §64; Anthropic bakiyesi gerekir): önce kalibrasyon (`run_f3
   --limit 10 --workers 3 --max-cost 5`), sonra tam koşu.
5. **İsteğe bağlı / kullanıcı kararı:** yanlış onay direnci için daha zayıf ya da başka aileden çözücü (K4 e); yedek etiketleri (PR #3, #4, #9, #10,
   #12, #13, #14 öncesi, §6); bulut önyükleyicisi 250 → 275 s (B1–B2); açık kapsama işleri (§4.2, V1–V16); YKS 2025–2026 matematik ölçümü abonelikle, ayrı sohbette, birleştirmeden sonra (DECISIONS §87).

## 4. Açık maddeler (tam liste)

Kaynak: arşivdeki §0.8–§0.14, §5–§7, §12, DECISIONS §53–§63 ve BULUT §12. Bir madde yalnız kapandığında, kanıtıyla birlikte (DECISIONS'ta) buradan çıkarılır.

### 4.1 Bulut ve ortam

- **B1. Anlık görüntü bazen kullanılmıyor** (DECISIONS §56 Ek, §59 (e), §61; BULUT §12): 26 Eylül 11:00 sohbeti `new` ile betiği yeniden koşturdu,
  sonrakiler `resume-cached` (26 Eylül 07:39 `setup-only` görüntüsü); `new`'in nedeni **[DOĞRULANMADI]** (en olası ağ ayarı). **B2.** 250 s sınırı o
  sohbette aşıldı (kanca kalanı 42 s'de kurdu); süre 180–250 s.
- **B4.** `raw.githubusercontent.com` dosya indirme yolu kurulum aşamasında hiç koşmadı (yedek; oturum içinde 32 s, 5/5 OK; DECISIONS §54). **B5.**
  "claude.ai ortam değişkenleri kurulum betiğine hiç ulaşmıyor mu": kanarya (`MATHVERIFY_SETUP_CANARY=1`) eklenmedi, sınanmadı; düzeni etkilemiyor.
- **B6. Soğuk Lean açılışı** ~340–470 s (28 Eylül akşam düz `pytest`'te 405 s; 30 Eylül `--full` ısınması 452 s); `pytest` ve `--full` ilk Lean
  testinden önce ısınır (DECISIONS §60–§61). Açık: yavaşlığın nedeni (sayfa önbelleği değil; görüntü diskinin ilk okunması çıkarım
  **[DOĞRULANMADI]**).
- **B7.** Belirteç yenileme: yeni fine-grained belirteç (Contents: read-only, yalnız `wqedwad/asd`) Setup script'in `T='...'` satırına. **B8.**
  Etiket ve `master` buluttan push edilmez; etiket push'u bulutta hiç denenmedi.
- **B9.** Bulutta `repl` RSS 7.08 GB / PSS 6.78 GB (27 Eylül); `lake env`'in payı ölçülmedi. **B10. Kullanım/maliyet** (BULUT §8): bulut kredisinin
  kaynağı ve abonelik sınırının jeton ağırlığı **[DOĞRULANMADI]**; yerel maliyet ölçülmedi.

### 4.2 Doğrulayıcı: bilinen sınırlar ve kapsama

Doğru cevabı reddedenler: V11, V13, V15 (S1, R1), (ters aralık noktasında adım §83'te kapandı). Yanlış onaylar: V1. Ötekiler UNKNOWN (kapsama kaybı), kaçırılan adım (V2, V6) ya da bilinçli sınır.

- **V1. `tyt-prob-018`:** çözüm düzeyindeki tek yanlış onay (doğru ama gerekçesiz adım; kanıtlanmış adım L6 kritiğini ezer; aynı sınıf: C'deki 12
  aritmetiği doğru `compute` adımı, §63). Karar F4 ölçümüne bağlı (DECISIONS §3.3, §4);
  `test_a_true_but_unjustified_step_is_still_overruled_by_its_certificate` ile testli.
- **V2. Çözücünün kendi sembolüyle yazdığı adımlar denetlenmez** (ilke 5). +1 bozulan 46 adımın 6'sı kaçıyor (5'i bu sınıf, 1'i çözümsüz öncül);
  nedenler `soundness_fuzz.ACCEPTED_MISS_REASONS`'da, açıklanmayan kaçırma bir kapı. Kapatmak `docs/SOLVER_FORMAT.md` sözleşmesini değiştirir.
- **V3. Tanımlılık türev/ekstremum/seride yalnız çekimser:** "`x²/x`'in [−1, 1]'deki minimumu −1" UNKNOWN. Tanımsız noktaları dışlayarak hesaplama
  ölçülmedi. `antiderivative` yazıldığı biçimde tanımlılık için ayrıca sınanmadı.
- **V4.** Adımsız çözümde CORRECT yalnız cevap düzeyindedir (`answer_level_only`, `answer_from_option_letter`, `KAPSAM:` satırı); bayrağa bakmayan
  tüketici farkı görmez.
- **V5. 25 Eylül'de bilerek bırakılanlar** (DECISIONS §55): kanıtsız eşdeğer biçimler ("(2x − y + 1)(x² + 1) = 0"), sembolik kanıtsız kapalı
  biçimler, periyodik tanım kümeli ilkeller, sonsuz sınırlı integraller, floor/ceiling özdeşlikleri, gelenek farklı tek taraflı durumlar (√x'in
  0'daki limiti), `asec`/`acsc` yok.
- **V6.** Yanlış çarpanlara ayırma adımı (`x² − 5x + 6 = 2(x − 2)(x − 3)`, öncül `x² − 5x + 6 = 0`) öncüllerin çözümlerinde doğru olduğu için
  reddedilmez; ayrım sözdiziminden yapılamaz.
- **V7. Denetim kalıntıları** (`denetim/2026-09-25/`): C grubunda 20 fark (16 UNKNOWN, 2 beklenti hatası, `dc_eqof_eqstep` bilinen sınır, iki
  kayıt); A derleminde 5 (4'ü denetçinin etiket hatası, 1'i V6).
- **V8. Lean'de bilerek kapsam dışı:** olasılık olay yüklemleri, limitler, sentetik geometri, parçalı ve has olmayan integraller. Yazıcı
  çeviremediğini tahmin etmez.
- **V9. Ölçüm sentetik.** Precision 1.000 ve "Lean FP 0" bu sete özgü; 25 Eylül'de set dışı 98 yanlış iddianın 53'ü Lean'de sertifika alıyordu. Yeni
  bir denetim yeni sınıf bulabilir.
- **V10.** Sandbox süreç izolasyonudur, güvenlik sandbox'ı değil. Girdi artık kod olarak çalışmıyor (ilke 13), ama model kodu çalıştırılacaksa
  gVisor/Firecracker gerekir.
- **V11. Aralıkta örneği olmayan öncülde esas kök** (DECISIONS §65): `cos x = −1`, [0, π) gibi aralıkta kökü olmayan görevde periyotsuz yazılan
  doğru esas kök adımı (`x = pi`) reddedilir (x = 3π); `#11` öncesiyle aynı, D6 gereği.
- **V12. Tanım kümesine uyan yanlış atama** (DECISIONS §66): IR'da öncülün bağlamadığı bir sembole yanlış değer (`ayt-diz-002`'de `n = 21`) tanımsal
  kalır; sonra çelişilmezse çözüm CORRECT. `#11` öncesi doğrusu da reddediliyordu.
- **V13. Aynı doğrunun ikinci noktası** (DECISIONS §67–§68): seçim kuralı y-kesişimini kabul eder, ama ardından x-kesişimi (`y = 0`) seçilen x = 0
  noktasında reddedilir (yanlış ordinattan ayrılamaz; D6); doğru çözüm INCORRECT. Gerçek veride yok.
- **V15. V14 denetiminden kalanlar** (DECISIONS §72; V14 ve F9 kapandı, §81). Haksız red (önceden var): verilenlerin yalnız dolaylı belirlediği
  sembollü `compute` adımı (a + b = 5, a − b = 1 iken `a*b = 6`) özdeşlik gibi denetlenir (S1; doğrudan sabitlenenler §76'da kapandı); tam sayı
  bildirilmemiş üst sınırlı toplam (R1). Lean: `Mod`/`floor` gövdeli, tam sayı adlı argümanlı fonksiyon reddedilir (L1). (GCD-10 §73'te kapandı.)
  Mutasyon: R02 ve L07'nin eşdeğerliği kanıtlanmadı. Çok sayıda kapsama kaybı (UNKNOWN), liste §72'de.
- **V16. Taşıma denetiminden kalanlar** (DECISIONS §73; §78–§79'da kapandı). Bilinçli: 300'den çok sabit uçlu küme (§78 A (6)); çok değişkenli
  `Subs`. Açık (önceden var, §79): özdeşlik denetimi kararsızken pinli yeniden denetim koşmaz (pinli `Limit` adımı §82'de kapandı). Ters aralık
  §81'de çekimser. Açık öneriler (§74): sağlamlık taramasına eşit yazımlı küme ucu varyantı (kalıcı kapı); `franklin`'in `karar_farki.py`
  yetenekleri `fark.py`'ye.
- **V19. Güvenlik için kabul edilen kapsama kayıpları** (DECISIONS §84, tam liste orada; kullanıcı: "sonra çözeceğiz"): kanıtlanamayan ya da
  geleneğe bağlı durumda CORRECT yerine UNKNOWN (§80). Başlıcaları: serbest parametreli integral/limit, iç içe kapalı integral, yalnız
  `vars.constraints` ile sabitlenen parametre, tam sayı değişkende doğru türev, kısıt ucunda türev, gerçel değişkende gcd/n!'li kalkülüs, ters
  aralığa düşen değerler. Veri setinde etkisi 0. Yalnız kanıtlı yolla geri kazanılır.
- **V20. Dördüncü denetimin kalanları** (DECISIONS §85–§89; §3 adım 2; tam liste `d4/a_arti/envanter.json`: 263 kayıt, açık 115).
  **Gerçekçi 19** (§89): yanlış onay D4C2-YO-4 (`rel_tol`; düzeltmesi d4c tur 4'te), D4E3-YO-7 (parçalı boşluk; d4e tur 4), D1 (`x ∉ [0,3]`;
  d4h); haksız ret D4E3-RK-1, RK-3 (d4e tur 4), PRE-RK-4, PRE-RK-5 (d4h tur 2), D4F2B-ONCEKI-1 (hiçbir dalda); kapsama d4b8-RK-1 (d4b tur 10),
  D4C2-RK-A, D4C3R-KK-1, Gauss ∫_ℝ e^{−x²} (d4c tur 4), D4E3-RK-4/5/6 (d4e tur 4), D4E4-U2 (d4e tur 4 getirdi), D4H-RK-1 (d4h tur 1 getirdi),
  D4F2B-RK-1/2 (hiçbir dalda). **Parçanın getirdiği açık yanlış onaylar (yapay):** d4b8-YO-1 (d4b tur 9'da kapalı), d4b9-YO-1, D4B10-LINEAR
  (tur 10), D4C3-YO-A/R-YO-1 (zarf; d4c tur 4), D4E4-YO-1 (d4e tur 4 getirdi), D4F2A-YO-1, D4F2B-YO-1, D4H-YO-5. **Önceden var yapay yanlış
  onaylar:** d4e3 YO-2–YO-6 ve RK-2 (d4e tur 4'te kapalı), D4E4-YO-2/3, d4f2 (ℂ söylemi, ∞ argümanı, sıfır üs), d4h YO-1–YO-4, D4C-T4-PI,
  CAP-K1 (gizli; d4i). Kapsama: BİRLEŞİK-1 (d4c tur 4). Küçük açıklar: G14 testi yük altında zaman bütçesiyle UNKNOWN; d4g süre bütçesi
  işbirlikçi (tek süreç içi çağrı yalnız sandbox'ta kesilir); `relation_holds_at(Ne)` sayısal eşitliği kanıt sayıyor (envanter: kesin sabitler
  `exact_equal`'la karşılaştırılıyor, geçersiz olabilir **[DOĞRULANMADI]**); wordproblem bileşik verilenleri ("x**2 = 9 ve x < 0") okuyamıyor
  (doğru cevap da UNKNOWN, gerçekçi kapsama); x**a = 4 (a = 2 verilen) yeniden yazılmıyor; evaluate Limit(|x|/x) bildirimle CORRECT, kısıtla
  UNKNOWN; d4h'de `\lfloor\frac{17}{5}\rfloor` yeniden yazımı ve `rank`'ın `layer_exception`'ı. (PRE-RK-6 `5eb38f8`'de kapalı: §89.)

### 4.3 Kredili ölçüm

- **K1. F3 baştan koşulmalı.** 18 Eylül sayıları eski kodun ve yarım: IR kabulü 64/67 (`ayt-diz-008/-013/-018`'de Meta yargıcı puan döndürmedi),
  yeniden yapılandırılan 34 öğede 32/34, iki yanlış karar D'de yanlış onay (`ayt-ana-017`, `-019`). `reports/f3_report.md` eski raporlayıcıdan.
  Kalan ~154 öğe ~10 $.
- **K2. F4 ilk kez** (L6 açık; ~15–25 $). Belirleyici sayılar: D tespiti, doğru çözümde yanlış suçlama, "sertifikanın iptal ettiği kritik raporu"
  (V1). 28 Eylül'den beri çapraz denetim eleştirmeni yalnız kanıtlanmış (`verified`) adımda geçersiz sayar; örneklenmiş adımlar artık `unknown`
  (DECISIONS §63 D).
- **K3. Ön koşullar:** kod dondurulur (sonraki her değişiklik sayıları eskitir); anahtar yenileme gerekmez (kullanıcı, DECISIONS §64); `--max-cost`
  olmadan koşulmaz; `llm_cache/` istek hash'iyle anahtarlı, değişen istem yeniden ücretlenir; bulutta `api.meta.ai` ortamın API kimlik bilgisiyle
  açık (DECISIONS §62; vekil anahtarı ekler); ~0,066 $/öğe (yarım koşu).
- **K4. Gerçek AI çözücü çıktıları:** `harness/run_solver.py`; Muse Spark 1.3 ile 280 öğe tamam (§2; DECISIONS §63). Açık: (a) `tyt-say-*` sembol
  anlamı: istem sembol adını verir, anlamını vermez (kullanıcı kararı, §4.4 madde 3); (b) `tyt-esf-007/-014`'ün sorusu çözülemiyor (akış kesilmesi,
  sonra Meta 504 "request timed out"); (c) akışın `usage`'sız kesilmesinin nedeni **[DOĞRULANMADI]** (koşu 2'de 48 canlı çağrının 5'i; istemci
  yeniden dener); (d) eksik akışların ve 504'lerin ücretlendirilip ücretlendirilmediği **[DOĞRULANMADI]**; (e) çözücü hiç yanlış cevap vermedi:
  yanlış onay direnci için başka çözücü gerekir. ((f) anahtarlar 86/86, §69; (g) etiketleyici farkı kanıtlıyor, §70: kapandı. Kalan: ilkel eşitliği
  yerel, ℝ'de sıçrayan ilkel `right` etiketlenebilir.)

### 4.4 Kullanıcı kararları (açık sorular)

1. Ne zaman silinebilir (sormadan silinmez, §6): yedek etiketleri ve bundle'lar; `refs/arac/bulut-v1` (v2 doğrulandı, v1'in içeriğini taşıyor);
   `master`a girmiş uzak dallar (`bulut-2026-09-24`, `claude/funny-cray-bey5o1`, `-compassionate-shannon-…`, `-practical-faraday-…`,
   `-trusting-curie-…`, `-keen-ramanujan-…`, `-dreamy-meitner-…`, `-busy-bardeen-…`).
2. Anthropic bakiyesi ne zaman, ne kadar (F3 ~10 $, F4 ~15–25 $; kod dondurulunca)? Anahtar yenileme F3/F4 için gerekmiyor (DECISIONS §64); depo
   açılırsa gerekir (madde 8).
3. Gerçek çözücü çıktıları: Muse Spark 1.3 ile 280 öğe yapıldı (§2). Açık: çözücü istemi IR sembollerinin anlamını (öncülleri) versin mi
   (`tyt-say-*`; istem değişirse 280 öğe yeniden ücretli ve ölçülen şey değişir)? **Ertelendi** (28 Eylül akşam; kod dondurmadan önce yeniden
   sorulur). Etki: yalnız haksız red (86 sorudan 1), yanlış onay yok. Yanlış onay direnci için hangi (daha zayıf ya da başka aileden) çözücü?
   (Anahtarlar denetlendi: §69.)
4. Lisans ve CI (özel `wqedwad/asd`; CI ve LICENSE yok; CI açılırsa hızlı `check.py` koşar).
5. Sınırlar: `tyt-prob-018` kuralı F4'ten sonra daraltılsın mı (V1)? Çözücü sembolü adımları sınır mı, yapısal formata sembol tanımı mı (V2)?
   Ekstremum/türev/seride tanımsız noktada çekimserlik yeter mi (V3)?
6. Başka sağlayıcıyla (GPT/Gemini, `set_client_override`) ölçüm istenir mi?
7. Uygulamanın adı ve ayrıntıları (ne depoda ne şartnamede).
8. **Karar (8 Ekim, DECISIONS §87): depo kimseyle paylaşılmayacak, açılmayacak.** Karar değişirse önce anahtarlar yenilenir; `.env` ve YKS kaynak PDF'leri geçmişten temizlenir.
9. Bulut kurulumu: önyükleyici sınırı 250 → 275 ve Meta için ağ ayarı birlikte mi (§3 adım 5)?

### 4.5 Teknik borç

- **T1.** `DECISIONS.md` bölüm sırası 1, 2, 3, 6, 4, 5, 7–14; madde numaraları atlıyor; §2 ve §3.9 bilerek Faz 1 anlık görüntüsü ("180 öğe").
  **T2.** Biçimlendirici yok; pyflakes dışında stil denetimi yok. **T3.** CI yok.
- **T5.** `reports/lean_setup.log` eski `stable` kurulumunun günlüğü (sabit kurulumunki bulutta `/opt/mathverify-logs/setup_lean.log`). **T6.** 26
  Eylül öncesi `check_full.log` başlıklarında "commit edilmemiş değişiklik" sayısından 1 düşülür (günlük kendini sayıyordu; `3925180`).
- **T7.** `docs/BULUT.md` ~1070 satır ve tarihçe biriktiriyor (§12'de sonradan kapanmış üç madde hâlâ `[ ]`); buradaki gibi güncel durum + arşiv
  ayrımı gerekebilir. Testler onu okuyor: kod sayılır.
- **T8. Windows** (DECISIONS §59, §61): `eab80f1`'de `windows_full.ps1` ile **24/24, 31 dk**. Git Bash donmasının nedeni **[DOĞRULANMADI]**.
  Ölçülmeyen: ebeveyn izleyicisi, `CopyFile2`/junction yolu, `--plan`'ın buluttaki `--full`u Windows checkout'unda kabul etmesi. **T9. Kuralın
  sınırları:** bekçi alt süreçleri ve `os.open(dir_fd=…)`'yu görmez; koşu sırasında yapılıp geri alınan değişiklik günlükten anlaşılmaz; günlük düz
  metin.

### 4.6 Güvenlik

- **S1.** `.env` kullanıcı kararıyla özel depoda izleniyor (DECISIONS §35), değerler git geçmişinde ve
  GitHub'da. F3/F4 için yenileme gerekmiyor (§64); depo açılırsa önce yenilenir, geçmiş temizlenir. Bulutta Meta anahtarı ortamın API kimlik
  bilgisinde (VM'ye girmez); `.env`'deki eski Meta anahtarının iptali kullanıcıda.
- **S2.** GitHub belirteci Setup script metninde (ortamı kullanan herkes görür); sızarsa depoyu ve `.env`'i okutur. `unset`, root'un
  `/proc/<pid>/environ` okumasına karşı korumaz (DECISIONS §54). Sızıntı taraması yalnız günlüklerde, `/etc/profile.d`'de ve `.git/config`'te
  yapıldı (0 bulgu); daha geniş tarama izin denetimine takıldı, yapılmadı.

### 4.7 Doğrulanmamış kayıtlar

- §6'da **[DOĞRULANMADI]** yedekler (`572ef57`, `18fd298` bundle'ları; `ee7b2dd`'nin yerel yedeği); 26 Eylül 01:06'da düşen testin adı; arşiv §4'ün
  kodu geri almadan üretilemeyen "önce" ölçümleri (7/7, 54 çift, 0.990…); alandaki önyükleyici metninin içeriği (yalnız uzunluk: 843); B1, B6, B10,
  K4'teki işaretliler; 30 Eylül kopya silinmesinin nedeni (DECISIONS §73).

## 5. Son ölçülen sayılar (kapılar, `1775b3f`; aksi yazılmadıkça `d68070c` ve öncekilerle aynı)

| Kapı | Değer | Hedef |
|---|---|---|
| Birim testleri (`1775b3f` bulut, `--full`; `d914dbc` Windows) | 3212 passed / 5 skipped; 2064 passed / 106 skipped (+4 ortam) | hepsi geçer |
| pyflakes | 0 bulgu | 0 |
| Cevap düzeyi pozitif / negatif precision; kapsama | 1.000 / 1.000; 1.000 | ≥ 0.98; ≥ 0.85 |
| B hücresi yanlış red; anahtar sızma testi | 0.000; geçti | < 0.10; zorunlu |
| Çözüm düzeyi pozitif precision; D tespiti | 0.994 (1 FP, V1); 0.976 (41/42) | raporlanır |
| Lean erişilebilir; sertifika; FP; junk | evet; 121/280; 0; 0/33 | —; —; 0; 0 |
| Adversaryal saldırı başarısı (3 yüzey) | %0 (21 139 saldırı; UNKNOWN'a düşen 2890, önce 2894) | < %2 |
| Yanlış onay / eşdeğerde red / değer olmayan iddia / adım dönüşümünde red | 0/457, 0/214, 0/46, 0/184 | 0 |
| Nedeni açıklanmayan kaçırılan bozuk adım; adım lokalizasyonu | 0/6; 75/120 (önce 74) | 0; raporlanır |

Raporlar `reports/*.md` (üretilir, elle yazılmaz), kapı günlüğü `reports/check_full.log`.
Süre: `--full` bulutta **~25–40 dk** (4 süreçli adversaryal 661–1084 s; soğuk Lean'de +452 s ısınma), Windows'ta 31 dk; hızlı `check.py` ~7 dk (427 s).

## 6. Dallar, etiketler, yedekler

- **Dallar** (15 Ekim, `git merge-base --is-ancestor` ile): `master` = `wqedwad/asd#14`'ün birleşmesi (öncesi `aa67b20`). **Oturum dalları**
  (birleşmedi): `claude/focused-albattani-jlomk1` (güncel), onun içerdiği `claude/amazing-edison-0g21ci`, `-upbeat-mccarthy-ef2oub` ve
  `-trusting-lovelace-vp1boa`; `wip/*` dalları yalnız bundle'larda (§3 adım 1). **Öteki birleşmeyen dal** `claude/inspiring-franklin-l3cocz` `3b030a4` (V14'ün paralel sürümü; bilerek: parçası ve
  testleri taşındı, §73, bilgisi §74; silinmesi kullanıcıya sorulacak, §3). Öteki hepsi `master`da: `claude/loving-bardeen-ninmoo` (`#13`, `#14`),
  `claude/sharp-lamport-f9m2w3` `d68070c`, `claude/inspiring-cori-xcgjld` (`#12`), `claude/busy-bardeen-ckr5bw` (`#11`),
  `claude/dreamy-meitner-rvrwlj` `60d539c` (`#9`, `#10`), `claude/keen-ramanujan-oqseru` (`#8`), `claude/trusting-curie-76slml`,
  `claude/practical-faraday-7a4iy4`, `claude/compassionate-shannon-759r85`, `claude/funny-cray-bey5o1`, `bulut-2026-09-24`, `denetim-2026-09-20`,
  `yerel-kalite-2026-09-23`. Araç ref'leri `refs/arac/bulut-v1` `c6d0cc1`, `refs/arac/bulut-v2` `f90d5e4` (kullanılan).
- **Yedek etiketleri** (GitHub'da; bundle'lar yalnız `C:\Users\kullanici\mathverify-yedek\`, geri dönüş talimatı orada `OKU.txt`):

  | Etiket | `master` | Bundle |
  |---|---|---|
  | `yedek/master-2026-09-23` | `2744677` | `mathverify-master-2744677-2026-09-23.bundle` |
  | `yedek/master-2026-09-23-2` | `e2aa08d` | `mathverify-master-e2aa08d-2026-09-23.bundle` |
  | `yedek/master-2026-09-24` | `23d7c6b` (birleştirmeden **sonra** alındı) | `mathverify-master-23d7c6b-2026-09-24.bundle` |
  | `yedek/master-2026-09-24-2` | `572ef57` | **[DOĞRULANMADI]** |
  | `yedek/master-2026-09-25` | `18fd298` (PR #1 öncesi) | **[DOĞRULANMADI]** |
  | `yedek/master-2026-09-26` | `d66bf2d` (PR #2 öncesi) | `mathverify-master-d66bf2d-2026-09-26.bundle`; içindeki `refs/heads/master` eski yerel `18fd298`, geri dönüş klon + `git checkout yedek/master-2026-09-26` |
  | yok | `ee7b2dd` (PR #3 öncesi) | **[DOĞRULANMADI]** |
  | yok | `e07d4f7` (PR #4 öncesi); `c2e4fdf`, `622a178` (PR #9, #10); `c0a2caf`, `35af293`, `aa67b20` (PR #12, #13, #14) | alınmadı (kullanıcı kararları: #4 "yalnız belge" gerekçesiyle, PR kod da içeriyordu: DECISIONS §59 Düzeltme; #9–#10 27 Eylül "yedeğe gerek yok", 28 Eylül "birleştir"; #12 29 Eylül, #13 30 Eylül "yedeğe gerek yok"; #14 1 Ekim "yedeksiz, PR ile" → "dalı birleştir") |
  | `yedek/master-2026-09-26-2` | `849b492` (PR #7 öncesi) | `mathverify-master-849b492-2026-09-26.bundle` (kullanıcının betiği: yerel `master` önce ileri sarıldı, `bundle verify` ve deneme klonu geçti; etiket buluttan doğrulandı) |
  | `yedek/master-2026-09-27` | `5c2f83e` (PR #8 öncesi) | `mathverify-master-5c2f83e-2026-09-27.bundle` (kullanıcının betiği "YEDEK TAMAM" yazdı: `bundle verify` ve deneme klonu geçti; etiket buluttan doğrulandı) |
  | `yedek/master-2026-09-28` | `2f11c84` (PR #11 öncesi) | `mathverify-master-2f11c84-2026-09-28.bundle` (kullanıcı, 28 Eylül akşam: `bundle verify` "okay", deneme klonu `2f11c84`; etiket buluttan doğrulandı. İlk denemede etiket bayat yerel `master`ı (`5c2f83e`) göstermişti, silinip yeniden kondu) |

- **Yedek yöntemi** (her `master` birleştirmesinden hemen önce, yerel checkout `C:\Users\kullanici\mathverify`'da): (0) `git fetch origin`, `git
  checkout master`, `git merge --ff-only origin/master`, `git log -1 --oneline` = beklenen commit (28 Eylül: checkout başka daldaydı ve kirli
  `reports/` onu engelledi, etiket bayat `master`ı gösterdi); (1) `git tag yedek/master-YYYY-MM-DD[-N] master`; (2) `git bundle create
  C:/Users/kullanici/mathverify-yedek/mathverify-master-<kısa-hash>-YYYY-MM-DD.bundle --all`, `git bundle verify` ve deneme klonu; (3) `git push origin
  <etiket>`; etiket buluttan `git ls-remote` ile doğrulanır; (4) hemen önce `scripts/check.py --plan`. Geri dönüş `git reset --hard <etiket>`.
  Buluttan `master`/etiket push edilmez.
- **Yerel checkout** (30 Eylül akşam): `master` `35af293`; `#13` ve `#14`'ten sonra `git pull` gerekir (çalışma dalı `claude/sharp-lamport-f9m2w3`).
  Stash'te Windows `--full` raporları (`eab80f1`; kullanıcı silebilir), yerel `claude/dreamy-meitner-rvrwlj` eski (birleşmiş).

## 7. Bulut özeti (ölçülmüş)

- Ubuntu 24.04, 4 CPU, 15 GB RAM, ~30 GB disk, root, `/home/user/asd`. Ağ: GitHub, PyPI, `raw.githubusercontent.com`, `api.anthropic.com`,
  `api.meta.ai` açık; Lean/Mathlib kapalı (araç ref'inden). Kurulum betiğinde git vekili yok (401), ortam değişkenleri ulaşmaz; belirteç
  önyükleyicide (§53–§56). Kanca 6–15 s, eksikse Lean'i arka planda kurar; `/opt` ~10.7 GB.
- **Tur bitince uzun iş sürerken konteyner kapatılabiliyor** (26 Eylül `--full` kayboldu; 30 Eylül bir iş akışı): koşu ön planda ≤10 dk'lık
  beklemelerle izlenir. Alt ajanlar oturum kullanım sınırına takılabilir (30 Eylül). İş akışı aynı anda en çok 2 ajan koşturur (CPU − 2).
- Meta (DECISIONS §63): akışsız ~31 s'de 502, akış bazen `usage`'sız kesilir, uzun `xhigh`'ta 504. Stop kancası commit + push ister;
  `ANTHROPIC_BASE_URL` okunmaz (§48); `rsync` yok (CLAUDE.md).

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

Kurulum (Linux; bulutta kanca yapar): `docs/BULUT.md` §4, Lean `docs/LEAN_SETUP.md`. Ortam değişkenlerinin tam tablosu arşiv §9 ve `docs/BULUT.md` §5.

## 9. Nerede ne var

Arşiv `docs/arsiv/HANDOFF-2026-09-26.md` (§0 bulut tarihçesi, §2 mimari, **§4 tekrar denenmeyecekler**, §11 tuzaklar);
`DECISIONS.md` (§1 kilitli kararlar, §7–§16 tarih sırasıyla, son §88); `docs/` (`ARCHITECTURE`, `QUALITY`, `SOLVER_FORMAT`,
`LLM_LAYERS`, `LEAN_SETUP`, `BULUT`, `sartname/`); `reports/arsiv/`; `denetim/` (ölçüm ve mutasyon betikleri).
