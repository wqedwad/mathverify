# HANDOFF — mathverify (güncel durum)

> **Son güncelleme: 3 Kasım 2026 (bulut)**: **`master` `7dcc979` = PR #15'in birleşmesi** (3 Kasım; yedek `yedek/master-2026-11-03`): `master`
> (`#14`) + dördüncü denetim (A+ adım i–vii, DECISIONS §89–§90) + yerel kalite (ix, §91) + son saldırı ve düzeltme turları (viii, §92). **A+ bitti:** son
> saldırının 52 adayı (50 gerçek) ve sekiz bağımsız denetimin bulguları düzeltildi ya da V20'ye kaydedildi; kullanıcının **durma kuralı** (22 Ekim) yeni denetim
> turu açmadı. Son ölçüm turu ve `--full` temiz (§2, §5). Oturum dalı `claude/focused-albattani-jlomk1` birleşmeden sonra `master`dan yeniden başladı. Bu belge yalnız **bugünü** taşır
> (~300 satır); tarihçe `docs/arsiv/HANDOFF-2026-09-26.md` ve `git log -p HANDOFF.md`'de ("HANDOFF §N" göndermesi yazıldığı günündür).
> **[DOĞRULANMADI]** = ölçülmedi ya da çıkarım; işaretsiz sayı ölçüm.

## 0. İlk 10 dakika

1. `CLAUDE.md` (kurallar) → bu belge → `DECISIONS.md` §63–§92; bulutta oturum başı bloğu ve `docs/BULUT.md`.
2. `git status`, `git log --oneline -5`, `git ls-remote origin` (§6); bulut klonunda `git fetch origin master` (yerel `master` bayat olabilir).
3. Takım: `PYTHONUTF8=1 .venv/bin/python -m pytest tests -rs`. `master`ınki §5 (5 atlama: 3 root salt okunur dizin, 1 isteğe bağlı indirme, 1 kapsam dışı ifade).
   Oturum dalı `62fb71e`: 6045 passed / 5 skipped (`--full`, Lean'li, 3 Kasım). Soğuk Lean'le ~17–20 dk (B6); Lean atlaması = Lean hazır değil.
4. Hangi kontrol gerekli: `scripts/check.py --plan`. Sonra §3'teki ilk iş. Tekrar denenmeyecekler: arşiv §4.

## 1. Proje (kısaca)

Türkçe bir matematik sorusu ve bir AI'ın çözümüne **üç değerli** karar verir (CORRECT / INCORRECT / UNKNOWN); karar kanıtla verilir (sertifikalar, adım
reddedici, Lean 4 + Mathlib), cevap anahtarı hatta girmez, LLM katmanları kararı yalnız daha temkinli yapar. İlkeler `CLAUDE.md`'de, mimari arşiv §2–§3 ve
`docs/ARCHITECTURE.md`'de; D1–D6 (§1) sorulmaz. Giriş: `verifier.verify`, `pipeline.run_pipeline` (LLM'li), `scripts/verify_cli.py`; set 280 sentetik öğe.

## 2. Durum (3 Kasım 2026)

**Kod.** `master` `7dcc979` = `#15`'in birleşmesi (3 Kasım; ağacı ölçülen dal başı `08336f1`'inkiyle aynı; önceki `1df0558` = `#14`; yedekler §6; PR
içerikleri §59–§92). **Birleşen dal** (son kod commit'i `62fb71e`): dördüncü denetim ve A+
(§85–§90), yerel kalite (§91), son saldırı (§92; kararlar, raporlar, denetim bulguları `denetim/2026-10-01/d4/saldiri/son/`, EK 1–11). Beş düzeltici dal
`wip/son-{sayisal,integral,adim,ayristirici,kalkulus}` (ikişer-üçer tur) `wip/son-birlesik`'te birleşti (`7b8d4f8`), o da oturum dalına (`cdc39b4`); kayıtlar
`b2d4fa6`, son mutasyon ölçümünün üç testi `ca8e31d`, raporların `.txt`'ye çevrilmesi `62fb71e` (§92).

**Kullanıcı kararları.** A+ (15 Ekim, §89). **Durma kuralı** (22 Ekim, "önerini uygula"; EK 7): ikinci tur düzeltmeleri ve onların bağımsız denetiminden sonra
yeni denetim turu açılmaz; denetim bulgusundan yalnız (a) dalın getirdiği ya da (b) gerçekçi ve yüksek önemli olan düzeltilir, gerisi V20'ye (ayrıntı
DECISIONS'a); üçüncü tur düzeltmeleri bağımsız denetimden geçmez (güvence: düzelticinin sondası, testleri, mutasyonu ve birleşik son ölçüm).

**Son ölçüm turu** (`b2d4fa6`'nın kodu = `ca8e31d`'ninki, Lean'siz, 2 Kasım): dokuz parça sondası 0 beklenmeyen (d4a 316, d4b 743, d4c 442, d4d 340, d4e 2757,
d4f 335, d4g 229, d4h 657, d4j 298); beş son sondası 0 (adım 407, sayısal 356, ayrıştırıcı 611, integral 226, kalkülüs 473); `fark.py` 558 çözümde tabana ve
`782431c`'ye karar 0, ilk kötü adım 0; `test_d4_*`/`test_parca*` altı parça geçti; kap/kap2 89 vaka: kayıp 0, kazanç 1; mutasyon altı listede 357/357 (üçü,
S53, S37, K62, birleşimde başka korumayla örtülüyordu; testleri `ca8e31d`'de). Belirlenim: |x² − 4|'(3) ailesi 8 vaka × 12 tohum 96/96 aynı; C3 vakaları 16 tohumda
kararlı. **Bilinen açıklar:** V20 (a) (gerçekçi denen yok), V21.

**Son `check.py --full`.** **24/24**, `62fb71e` (raporlar `978ae7f`), bulutta 3 Kasım 01:14–02:30 UTC, ~76 dk (ısınma 567 s, pytest 2790 s, adversaryal
803 s), 6045 passed / 5 skipped; `--plan` TAMAM. `master`ın kodunda 24/24 (`1775b3f`, 1 Ekim; §83); Windows `eab80f1` 24/24.

**Fazlar.** F0–F2, F5 (Lean), F6 (adversaryal + kalibrasyon), F7 (Lean şablonları): tamam, ölçüldü. F3 (LLM ön yüzü, L4, L5): kod tamam, **ölçüm yarım ve
eski** (18 Eylül, 218 öğenin 64'ü). F4 (kritik + meta-doğrulama): kod tamam, çevrimdışı testli, **hiç koşmadı**. **K4** (Muse Spark 1.3, `776e5b4`; §63): 278
çözüm, CORRECT|right 274, INCORRECT|right 4 (`tyt-say-*`), yanlış onay **0**; çözücü 278/278 doğru (yakalama gücü ölçülemedi); çözümsüz 2; ~1.3 $.

## 3. Sıradaki adımlar (sırayla)

1. **Yeni sohbet:** `git fetch origin claude/focused-albattani-jlomk1 && git merge --ff-only FETCH_HEAD` (push yalnız oturumun dalına). `wip/*` dalları ve
   depodaki ara yedekleri 3 Kasım'da silindi: içerikleri `master`da; eski arşivler git geçmişinde (`git show c563096:denetim/2026-10-01/d4/wip/<dosya>`
   gibi). `--plan` koş. Konteyner oturum sınırında yeniden başlar:
   ajanlar `SendMessage`, iş akışları resume, mutasyon `--kayit` ile sürer.
2. **A+ kapandı** (§92): son ölçüm ve `--full` temiz, belgeler yazıldı, `--plan` TAMAM.
3. **`master` birleştirmesi yapıldı** (3 Kasım, kullanıcı onayıyla): yedek kullanıcının yerelinde (`yedek/master-2026-11-03` = `1df0558`, bundle, deneme
   klonu; etiket buluttan doğrulandı), `--plan` TAMAM (`08336f1`), PR #15 → `master` `7dcc979`. Sonraki birleştirmeler aynı yöntemle (§6).
4. **Uzak dallar silindi** (kullanıcı kararı ve betiği, 3 Kasım): `master`a girmiş 16 dal, `claude/inspiring-franklin-l3cocz` ve `refs/arac/bulut-v1`;
   GitHub'da yalnız `master`, oturum dalı, `refs/arac/bulut-v2` ve 10 yedek etiketi kaldı (`git ls-remote`).
5. **Kod dondurmadan önce sorulacak** (§4.4 madde 3): çözücü istemi IR sembollerinin anlamını versin mi (`tyt-say-*`).
6. **Kod dondurma → F3 baştan, F4 ilk kez** (K1–K3; anahtar yenileme önkoşul değil, §64; Anthropic bakiyesi gerekir): önce kalibrasyon (`run_f3 --limit 10
   --workers 3 --max-cost 5`), sonra tam koşu; aynı koşuda SS-OT-1 (çıkarıcının "esas argüman"ı `arg` mı `atan2` mı) ölçülür.
7. **YKS 2025–2026 matematik ölçümü:** birleştirmeden sonra, ayrı sohbette, abonelikle (DECISIONS §87).
8. **V19'a dokunulmaz** (kullanıcı: "sonra çözeceğiz"). İsteğe bağlı: başka aileden çözücü (K4 e); önyükleyici 250 → 275 s (B1–B2); kapsama işleri (§4.2); eksik
   yedek etiketleri (PR #3, #4, #9, #10, #12–#14 öncesi, §6).

## 4. Açık maddeler (tam liste)

Bir madde yalnız kapandığında, kanıtıyla (DECISIONS'ta ya da bir commit'te) buradan çıkarılır.

### 4.1 Bulut ve ortam

- **B1. Anlık görüntü bazen kullanılmıyor** (§56 Ek, §59 (e), §61; BULUT §12): 26 Eylül 11:00 sohbeti `new` ile betiği yeniden koşturdu, sonrakiler
  `resume-cached`; `new`'in nedeni **[DOĞRULANMADI]** (en olası ağ ayarı). **B2.** 250 s sınırı o sohbette aşıldı (kanca kalanı 42 s'de kurdu); süre 180–250 s.
- **B4.** `raw.githubusercontent.com` yolu kurulumda hiç koşmadı (oturumda 32 s, 5/5 OK; §54). **B5.** Ortam değişkeninin kurulum betiğine ulaşmadığı sınanmadı.
- **B6. Soğuk Lean açılışı** ~340–470 s (düz `pytest`'te 405 s; `--full` ısınması 452 s; §60–§61); nedeni (görüntü diskinin ilk okunması) **[DOĞRULANMADI]**.
- **B7.** Belirteç yenileme: fine-grained (Contents: read-only, yalnız `wqedwad/asd`), Setup script'in `T='...'` satırına. **B8.** Etiket/`master` buluttan
  push edilmez; etiket push'u bulutta hiç denenmedi. **B9.** Bulutta `repl` RSS 7.08 GB / PSS 6.78 GB (27 Eylül); `lake env`'in payı ölçülmedi.
- **B10. Kullanım/maliyet** (BULUT §8): bulut kredisinin kaynağı ve abonelik sınırının jeton ağırlığı **[DOĞRULANMADI]**; yerel maliyet ölçülmedi.
- **B11. Alt ajanlar kuruluş erişim hatasıyla durdu** (23 Ekim): "Your organization has disabled Claude subscription access for Claude Code" (HTTP 403,
  `oauth_org_not_allowed`); ana oturum 2 Kasım'da yeniden çalıştı, A+'nın kalanı alt ajansız yapıldı. Nedeni ve sürüp sürmediği **[DOĞRULANMADI]**.

### 4.2 Doğrulayıcı: bilinen sınırlar ve kapsama

Doğru cevabı reddedenler: V11, V13, V20 (b). Yanlış onaylar: V1 (çözüm düzeyi), V20 (a). Ötekiler UNKNOWN, kaçırılan adım (V2, V6) ya da sınır.

- **V1. `tyt-prob-018`:** çözüm düzeyindeki tek yanlış onay (doğru ama gerekçesiz adım; kanıtlanmış adım L6 kritiğini ezer; aynı sınıf: C'deki 12 aritmetiği
  doğru `compute` adımı, §63). Karar F4 ölçümüne bağlı (§3.3, §4); `test_a_true_but_unjustified_step_is_still_overruled_by_its_certificate`.
- **V2. Çözücünün kendi sembolüyle yazdığı adımlar denetlenmez** (ilke 5): +1 bozulan 46 adımın 6'sı kaçıyor (5'i bu sınıf, 1'i çözümsüz öncül); nedenler
  `soundness_fuzz.ACCEPTED_MISS_REASONS`'da, açıklanmayan kaçırma bir kapı. Kapatmak `docs/SOLVER_FORMAT.md` sözleşmesini değiştirir.
- **V3. Türev/ekstremum/seride tanımlılık yalnız çekimser:** `x²/x`'in [−1, 1]'de min −1 UNKNOWN; tanımsız noktayı dışlayarak hesaplama ve
  `antiderivative`'in yazılı tanımlılığı sınanmadı.
- **V4.** Adımsız çözümde CORRECT yalnız cevap düzeyinde (`answer_level_only`, `answer_from_option_letter`, `KAPSAM:`); bayrağa bakmayan tüketici farkı görmez.
- **V5. Bilerek bırakılanlar** (§55): kanıtsız eşdeğer biçimler, sembolik kanıtsız kapalı biçimler, periyodik tanım kümeli ilkeller, sonsuz sınırlı
  integraller, floor/ceiling özdeşlikleri, gelenek farklı tek taraflı durumlar (√x'in 0'daki limiti), `asec`/`acsc` yok.
- **V6.** Yanlış çarpanlara ayırma adımı (`x² − 5x + 6 = 2(x − 2)(x − 3)`, öncül `x² − 5x + 6 = 0`) öncüllerin çözümlerinde doğru: reddedilmez.
- **V7. Denetim kalıntıları** (`denetim/2026-09-25/`): C'de 20 fark (16 UNKNOWN, 2 beklenti hatası, `dc_eqof_eqstep`, iki kayıt); A'da 5 (4 etiket hatası, V6).
- **V8. Lean'de bilerek kapsam dışı:** olasılık olay yüklemleri, limitler, sentetik geometri, parçalı ve has olmayan integraller; yazıcı tahmin etmez.
- **V9. Ölçüm sentetik.** Precision 1.000 ve "Lean FP 0" bu sete özgü; 25 Eylül'de set dışı 98 yanlış iddianın 53'ü Lean'de sertifika alıyordu.
- **V10.** Sandbox süreç izolasyonudur, güvenlik sandbox'ı değil; model kodu çalıştırılacaksa gVisor/Firecracker gerekir.
- **V11. Aralıkta örneği olmayan öncülde esas kök** (§65): `cos x = −1`, [0, π) görevinde periyotsuz doğru `x = pi` adımı reddedilir; D6 gereği.
- **V12. Tanım kümesine uyan yanlış atama** (§66): öncülün bağlamadığı sembole yanlış değer (`ayt-diz-002`'de `n = 21`) tanımsal kalır; çözüm CORRECT olabilir.
- **V13. Aynı doğrunun ikinci noktası** (§67–§68): y-kesişiminden sonra x-kesişimi (`y = 0`) x = 0'da reddedilir (D6); doğru çözüm INCORRECT; gerçek veride yok.
- **V15. V14 denetiminden kalanlar** (§72; S1, R1 (karar: UNKNOWN) ve L1 §91'de kapandı): mutasyon R02 ve L07'nin eşdeğerliği kanıtlanmadı; çok sayıda kapsama
  kaybı (UNKNOWN), liste §72'de; Lean yazıcısında `floor` gövdesi yok (karar etkisi yok, §91).
- **V16. Taşıma denetiminden kalanlar** (§73; pinli yeniden denetim, eşit yazımlı uç varyantı kapısı ve `fark.py` §91'de kapandı). Bilinçli: 300'den çok sabit
  uçlu küme (§78 A (6)); çok değişkenli `Subs`; ters aralık çekimser (§81).
- **V19. Güvenlik için kabul edilen kapsama kayıpları** (§84 tam liste; §80; kullanıcı: "sonra çözeceğiz"): serbest parametreli integral/limit, iç içe kapalı
  integral, `vars.constraints`'le sabitlenen parametre, tam sayı değişkende ve kısıt ucunda türev, gcd/n!'li kalkülüs, ters aralık değerleri; veri setinde 0.
- **V20. A+ sonunda açık kalanlar** (§89–§92; kararlar `d4/saldiri/son/kararlar.txt` EK 1–11; envanter `d4/a_arti/envanter.json` 15 Ekim hâli: 115 açık kaydın her
  biri bir parçanın son turuna ya da `a_arti/kararlar_kalan.txt` A/B/C'ye düşer, C aşağıda; kayıt kayıt yeniden ölçülmedi). Kod düzeltmesi olmayanlar:
  - **(a) Açık yanlış onaylar** (doğrulayıcının gerçekçi dediği yok). Gerçekçiliği belirsiz: **SS2-YO-1** (orta, tabanda da; EK 10): `certify_local_extremum`'un
    birinci türev testi süreksiz (sgn, Heaviside, atan2) fonksiyonda yerel olmayan noktayı onaylıyor (x² + sgn x için local_min 0 CORRECT); **YO-T2-4** (düşük,
    tabanda da): kuşku sözcükleri ('muhtemel', 'olası', 'mümkün', 'tahmin edilen') temizlenip değer CORRECT (`d1a1ee2` yalnız '5 muhtemeldir'
    biçimini kapattı); **YO-T2-6** (düşük): 'radyan'/'rad' düzyazı sayılıp atılıyor ('30 radyan' düz 30'a CORRECT). (YO-K3, YO-K5 kalkülüs 2. turda
    kapandı, §92.) Yapay ya da gerçekçi değil:
    evaluate'te `Integral(...)` formu sertifikayı zarf denetimsiz alıyor (`equiv/forms.py`; yalnız ekilmiş sertifikayla); SS2-YO-2 (sanal kısım noktada
    süreksizken [0, 2π) okuması bir yanın tamamında (−π, π]'ye çöküyor); YO-T2-5 (tanım kümesi önekli '∅' her görevde boş küme); D4C-T4-PI ve G2YO-6'nın kalanı
    (örnekleyiciyi bilen kurgu fark, cosh + sinh arkasına gizlenen fark: Richardson, bilinen sınır). Gerçekçiliği sınıflanmadı: boş öncülde karmaşık çözümler
    kesin hesaplanamayınca yanlış eq adımı unknown, çözüm CORRECT olabilir (EK 3 (iii); kaçırılan adım; çıkarım **[DOĞRULANMADI]**).
  - **(b) Haksız retler.** T2-RK-5 (sınır kuralı trig/üstel eşitsizlikte tetiklenmiyor; doğru çözüm INCORRECT, tabanda da), SA-RK-7'nin kalanı (Δ < 0 sınır
    denklemi, dışarıdaki deneme noktası, tam sayı değişkende irrasyonel sınır), '1/2 saat' iddiası INCORRECT (birim sözcüğü asimetrisi), durum (case) dalında
    türetilen çelişki çürütülüyor, tek kök adımları T01/02/07/10/11/14 (eq anlamı, önceden var), sınır kümesinin tek noktasını yazan adım ('x = 2', küme {2, 3};
    adım 1. tur raporu, sonraki turlarda yeniden ölçülmedi **[DOĞRULANMADI]**), G5 (`positive_integer` tanım kümeli boş eşitsizlik sayımı iki kopyada INCORRECT,
    tabanda da; son-adim denetimi; adım 2. tur raporunda kayıt); yapay: RK-T2-5, RK-T2-6.
  - **(c) Kapsama kayıpları** (çoğu önceden var; G1RK-4/6/7, G2RK-6, SON-G3-RK-10'u dördüncü denetimin A+ öncesi düzeltmeleri getirdi, `master`da yok). Kalkülüs:
    SON-G3-RK-5 (ℝ'de trig ekstremum, ~8.6 s), RK-6 ((−1)ⁿ dizileri), RK-7 (logaritmik limitler), RK-10 (monoton dış fonksiyonlu ekstremum), RK9-10 (0⁺'da tek
    yanlı), RK1-W6, evaluate yolunda köşedeki at(diff) ("Yoktur" yükü EK 11'de kapandı). Integral: G2RK-6 (floor integralleri), G2RK-8 (iç tekillikte iyimser kareleme). Adım/ÇS:
    G1RK-4 (çok açılı trig), G1RK-6 (asin/acos/cosh), G1RK-7 (basamak integralleri), SA-RK-10 ('3 ln 2', bileşik birim, değer sorusunda 'x = 6'), U09, Z06,
    compute sınır adımları, kök denkleminden sonra tek nokta ya da hepsi içeride liste skipped (tabanla aynı), okunmayan şıklar (adım 1. tur raporu, yeniden
    ölçülmedi): '2 ve 3', ']2, 3[', '{x | …}', 'Ç={…}', '\frac12', 'e⁻¹'. Sayısal: LaTeX `\arg`/`Arg`, karmaşık değişkenli arg(z), Σ iᵏ, 15 basamaklı varsayım
    yolu, Max(sin x, cos x) + x/4, sin x cos x sıfırları; `exactsets` büyük büyüklükte mutlak tolerans (üretilemedi **[DOĞRULANMADI]**); `strict_sign`'ın iki
    parçası tam sıfır değeri 0 sayıyor (önceden var; etkisi ölçülmedi). Ayrıştırıcı: `\bigl`, `\displaystyle` bölenden sonra (ölçülmedi); başka köke dair olumsuz
    parantez ('diğer kök … girmez') UNKNOWN; DNE kelime testi metnin içine bakıyor ('tanımsız değil'); 'İ' büyük harfli şık kısayola girmiyor (adım 3. turun İ/ı
    katlaması kapattı mı, ölçülmedi). Dördüncü denetimden (`a_arti/kararlar_kalan.txt` C): D4F2B-RK-4 (üçgensel sayı sınırlı Σ), RK-5 (1/det), D4E4-U1,
    wordproblem bileşik verilenleri ("x**2 = 9 ve x < 0"; gerçekçi), x**a = 4 (a = 2) (GAP-XA/D4D-XA), D4D-KAPSAMA-KALAN, Limit(|x|/x) kısıtla UNKNOWN
    (GAP-LIMABS), `rank`'ın `layer_exception`'ı (GAP-RANK). Yerel kalite (§91): Σ'lı denklemlerin doğru cevabı UNKNOWN (çözücü Σ'yı açmıyor), eşitsizlikte 0⁰
    noktası, Y4 (kararsız gelenek noktasında compute adımı 0⁰ = 1 ile verified; hükmü etkilemiyor).
  - **(d) A+'nın bilinçli kapsama bedelleri** (karar gereği CORRECT → UNKNOWN): birim kararı (EK 8): birimi kanıtsız işaretli cevap ('%20' kesir IR'ında, '180°'
    ters trig toplamında, '45°' ekstremumda; 169 ortak vakada 27) ve `units`'siz '30^\circ'; SI-YO-2: iç noktada güçlü tekillik (üs −19/20, −99/100) 4 vaka;
    G2YO-2: işaret değiştiren 4 vaka (sign(x)|x|^(−4/5), [−1, 32], = 5); (−π, π]'deki 6 tek gelenekli arg değeri ve √(−X − 16)'nın gerçel okuması; xˣ ailesi
    kısıtsız x'te (türev, ilkel; x > 0 bildirilince CORRECT); izin sözlüğü dışındaki düzyazı kuyruğu (derlemde kayıp 0); G2RK-11: bir trig özdeşliğinin 0 iddiası
    176–204 s'de UNKNOWN (`1df0558`'de CORRECT); SK-RK-5: x² sin(1/x)'in 0'da türevi (eski CORRECT bozuk yoldan); EK 9: harften sonra grup gelen LaTeX adımı ('\cos x(2\sin x − 1) = 0')
    UNKNOWN; EK 11: küme cevabında 'Yok' değeri UNKNOWN (SK-RK-6 kalkülüs 2. turda kapandı). Karar gereği kaçırılan adım: boş eşitsizlik öncülünde yanlış 'x = 5' çürütülmüyor (SA-RK-1; testli).
  - **(e) Süre ve başarım.** d4c kesin zarfı sech² tepeli integralde tek verify 100–150 s (d4c sondası H grubu 1352 s; §91); arg yazan problemlerde süre ×2; G14
    testi yük altında zaman bütçesiyle UNKNOWN; d4g süre bütçesi işbirlikçi (süreç içi çağrı yalnız sandbox'ta kesilir; D3 ile çelişmez, §89); sertifikasız
    integral adımı başına tam zarf bütçesi (G2RK-12: iki adımlı çözüm 97–127 s, UNKNOWN doğru) (SK-RK-1 kapandı: |x² − 4|'(3) 13–48 s → ~1 s, §92).
  - **(f) Bağımsız denetimden geçmemiş son diff'ler** (durma kuralı): integral 2. tur, kalkülüs 2. tur, adım 3. tur, ayrıştırıcı 3. tur ve EK 11, sayısal 3.
    tur; güvence düzelticinin sondası, testleri, mutasyonu ve birleşik son ölçüm (§2). A+ (4)'ün istediği d4d 2. turunun taranması kayıtlı değil
    **[DOĞRULANMADI]**.
- **V21. Sıraya/tohuma bağlı kararlar** (görev #7; §90, §92). Kapanan kök: Mul(0, x)'in `is_even`'ı (§90). Gözlemler: d4b sondası M3 Q1 {2} PYTHONHASHSEED 3'te
  INCORRECT, 0–2'de UNKNOWN (doğrusu INCORRECT; ikisi de güvenli yön); `test_parca11_ters_aralik_adim::…[route0]` yüke duyarlı (karar aynı); SS-ND-1
  (üretilemedi): ağır yükte 8 doğru `solve_equation` cevabı bir kez INCORRECT; C3 = (1 + √3 i)³ vakaları ('sin(C3) + sin 8 = 1', argmin 0) `0e93ed5`'te tohuma
  bağlı rastgele CORRECT (önceden var yanlış onay), birleşikte (`084ae53`) 16 tohumda kararlı; |x² − 4|'(3) ailesi `da5ba37`'de koşudan koşuya değişiyordu,
  kalkülüs 2. turdan sonra 96/96 aynı (§92). Açık: genel kök neden (SymPy önbelleği, hash sırası); bilinenler dışında tohum taraması yapılmadı.

### 4.3 Kredili ölçüm

- **K1. F3 baştan koşulmalı.** 18 Eylül sayıları eski kodun ve yarım: IR kabulü 64/67 (`ayt-diz-008/-013/-018`'de Meta yargıcı puan döndürmedi), yeniden
  yapılandırılan 34 öğede 32/34, iki yanlış karar D'de yanlış onay (`ayt-ana-017`, `-019`); `reports/f3_report.md` eski raporlayıcıdan; kalan ~154 öğe ~10 $.
- **K2. F4 ilk kez** (L6 açık; ~15–25 $): D tespiti, doğru çözümde yanlış suçlama, sertifikanın iptal ettiği kritik rapor (V1); eleştirmen §63 D'ye göre.
- **K3. Ön koşullar:** kod dondurulur; anahtar yenileme gerekmez (§64); `--max-cost` olmadan koşulmaz; `llm_cache/` istek hash'iyle anahtarlı (değişen istem
  yeniden ücretlenir); bulutta `api.meta.ai` ortamın API kimlik bilgisiyle açık (§62); ~0,066 $/öğe (yarım koşu).
- **K4. Gerçek AI çözücü çıktıları** (`harness/run_solver.py`; §63). Açık: (a) `tyt-say-*` sembol anlamı (§4.4 madde 3); (b) `tyt-esf-007/-014` çözülemiyor
  (akış kesilmesi, sonra Meta 504); (c) `usage`'sız kesilmenin nedeni ve (d) eksik akış/504 ücreti **[DOĞRULANMADI]**; (e) çözücü hiç yanlış cevap vermedi:
  yanlış onay direnci için başka çözücü gerekir. Kalan: ilkel eşitliği yerel, ℝ'de sıçrayan ilkel `right` etiketlenebilir.

### 4.4 Kullanıcı kararları (açık sorular)

Verilmiş kararlar: depo paylaşılmayacak, açılmayacak (8 Ekim, §87); A+ (15 Ekim, §89); durma kuralı (22 Ekim, §92); PR #15 ile birleştirme (3 Kasım). Açık sorular:

1. Yedek etiketleri ve yerel bundle'lar ne zaman silinebilir (sormadan silinmez, §6)? (Uzak dallar ve `refs/arac/bulut-v1` 3 Kasım'da silindi.)
2. Anthropic bakiyesi ne zaman, ne kadar (F3 ~10 $, F4 ~15–25 $; kod dondurulunca)? Anahtar yenileme F3/F4 için gerekmiyor (§64).
3. Çözücü istemi IR sembollerinin anlamını (öncülleri) versin mi (`tyt-say-*`; istem değişirse 280 öğe yeniden ücretli, ölçülen şey değişir)? **Ertelendi**
   (28 Eylül; kod dondurmadan önce sorulur). Etki: yalnız haksız red (86 sorudan 1). Yanlış onay direnci için hangi çözücü?
4. Lisans ve CI (özel `wqedwad/asd`; CI ve LICENSE yok; CI açılırsa hızlı `check.py` koşar).
5. Sınırlar: `tyt-prob-018` kuralı F4'ten sonra daraltılsın mı (V1)? Çözücü sembolü adımları sınır mı, sembol tanımı mı (V2)? Çekimserlik yeter mi (V3)?
6. Başka sağlayıcıyla (GPT/Gemini, `set_client_override`) ölçüm istenir mi?
7. Uygulamanın adı ve ayrıntıları (ne depoda ne şartnamede).
8. Depo kararı değişirse önce anahtarlar yenilenir; `.env` ve YKS kaynak PDF'leri geçmişten temizlenir (§87).
9. Bulut kurulumu: önyükleyici sınırı 250 → 275 ve Meta için ağ ayarı birlikte mi (§3 adım 8)?

### 4.5 Teknik borç

- **T1.** `DECISIONS.md` bölüm sırası 1, 2, 3, 6, 4, 5, 7–16, madde numaraları atlıyor; §2 ve §3.9 bilerek Faz 1 anlık görüntüsü. **T2.** Biçimlendirici
  ve pyflakes dışı stil denetimi yok. **T3.** CI yok. **T5.** `reports/lean_setup.log` eski `stable` kurulumunun (sabitinki `/opt/mathverify-logs/`). **T6.** 26
  Eylül öncesi `check_full.log` başlıklarındaki "commit edilmemiş değişiklik" sayısından 1 düşülür (`3925180`). **T7.** `docs/BULUT.md` ~1070 satır,
  tarihçe biriktiriyor (§12'de kapanmış üç madde hâlâ `[ ]`; araç ref tablosundaki `bulut-v1` 3 Kasım'da silindi); güncel durum + arşiv ayrımı gerekebilir; testler okuyor.
- **T8. Windows** (§59, §61): `eab80f1`'de 24/24, 31 dk; Git Bash donmasının nedeni **[DOĞRULANMADI]**; ölçülmeyen: ebeveyn izleyicisi, `CopyFile2`/junction
  yolu, `--plan`'ın buluttaki `--full`u Windows'ta kabulü. **T9. Kuralın sınırları:** bekçi alt süreçleri ve `os.open(dir_fd=…)`'yu görmez; koşu sırasında
  yapılıp geri alınan değişiklik günlükten anlaşılmaz; günlük düz metin.

### 4.6 Güvenlik

- **S1.** `.env` kullanıcı kararıyla özel depoda izleniyor (§35), değerler git geçmişinde ve GitHub'da; F3/F4 için
  yenileme gerekmiyor (§64); depo açılırsa önce yenilenir, geçmiş temizlenir. Bulutta Meta anahtarı ortamın kimlik bilgisinde; eskinin iptali kullanıcıda.
- **S2.** GitHub belirteci Setup script metninde (ortamı kullanan herkes görür); sızarsa depoyu ve `.env`'i okutur. `unset`, root'un `/proc/<pid>/environ`
  okumasına karşı korumaz (§54). Sızıntı taraması yalnız günlüklerde, `/etc/profile.d`'de ve `.git/config`'te yapıldı (0 bulgu); daha geniş tarama yapılmadı.

### 4.7 Doğrulanmamış kayıtlar

- §6'daki işaretli yedekler (`572ef57`, `18fd298` bundle'ları; `ee7b2dd`'nin yerel yedeği); 26 Eylül 01:06'da düşen testin adı; arşiv §4'ün "önce" ölçümleri
  (7/7, 54 çift, 0.990…); önyükleyici metninin içeriği (yalnız uzunluk: 843); B1, B6, B10, K4, V20, V21'deki işaretliler; 30 Eylül kopya silinmesi (§73).

## 5. Son ölçülen sayılar (kapılar, oturum dalı `62fb71e`, `--full` 3 Kasım; `master` `1775b3f` ile karşılaştırmalı)

| Kapı | Değer | Hedef |
|---|---|---|
| Birim testleri (`62fb71e` bulut, `--full`; `master` `1775b3f`; `d914dbc` Windows) | 6045 passed / 5 skipped; 3212 / 5; 2064 passed / 106 skipped (+4 ortam) | hepsi geçer |
| pyflakes | 0 bulgu | 0 |
| Cevap düzeyi pozitif / negatif precision; kapsama | 1.000 / 1.000; 1.000 | ≥ 0.98; ≥ 0.85 |
| B hücresi yanlış red; anahtar sızma testi | 0.000; geçti | < 0.10; zorunlu |
| Çözüm düzeyi pozitif precision; D tespiti | 0.994 (1 FP, V1); 0.976 (41/42) | raporlanır |
| Lean erişilebilir; sertifika; FP; junk | evet; 121/280; 0; 0/33 | —; —; 0; 0 |
| Adversaryal saldırı başarısı (3 yüzey) | %0 (21 139 saldırı; anlamı koruyup UNKNOWN'a düşen 2928, `master`da 2890) | < %2 |
| Yanlış onay / eşdeğerde red / değer olmayan iddia / adım dönüşümünde red | 0/467, 0/224, 0/46, 0/184 (`master`da 0/457, 0/214) | 0 |
| Nedeni açıklanmayan kaçırılan bozuk adım; adım lokalizasyonu | 0/6; 75/120 (önce 74) | 0; raporlanır |

Raporlar `reports/*.md` (üretilir), günlük `reports/check_full.log`. Ara ölçümler: sağlamlık kapısı 0/467 yanlış onay, 0/224 yanlış red (`afab1ac`, §91);
adversaryal 100 öğe / 7115 saldırıda flipped 0, accepted_wrong 0 (`wip/son-ayristirici` `3b08689`). Süre: `--full` ~25–40 dk (Windows 31 dk), hızlı ~7 dk.

## 6. Dallar, etiketler, yedekler

- **Dallar** (3 Kasım; `git merge-base --is-ancestor`, `git ls-remote`): `master` `7dcc979` (PR #15). **Oturum dalı** `claude/focused-albattani-jlomk1`
  birleşmeden sonra `master`dan yeniden başladı (belge güncellemesi; birleşen hâli `08336f1`); içerdiği eski oturum dalları `claude/amazing-edison-0g21ci`, `-upbeat-mccarthy-ef2oub`, `-trusting-lovelace-vp1boa`.
  **Yerel `wip/*`** ve worktree'ler 3 Kasım'da silindi (17 dal; commit'leri `master`da). **Depodaki ara yedekler** (`denetim/2026-10-01/d4/wip/`, 66 MB:
  yedi bundle, ajan notu ve scratch arşivleri, yamalar) aynı gün ağaçtan kaldırıldı: bundle'ların 32 ucunun hepsi `master`da (ölçüldü); dosyalar git
  geçmişinde.
- **Uzakta başka dal yok** (3 Kasım'da silindi: `franklin` ve `master`a girmiş 16 dal, commit'leri `master`da; `franklin`'in parçası ve testleri §73'te
  taşınmıştı). Araç ref'i `refs/arac/bulut-v2` `f90d5e4` (kullanılan); `bulut-v1` silindi (`docs/BULUT.md`'nin v1 satırları bayat, T7).
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
  | `yedek/master-2026-11-03` | `1df0558` (PR #15 öncesi) | `mathverify-master-1df0558-2026-11-03.bundle` (kullanıcının betiği: `bundle verify` ve deneme klonu `1df0558`; etiket buluttan doğrulandı) |
  | `yedek/master-2026-09-28` | `2f11c84` (PR #11 öncesi) | `mathverify-master-2f11c84-2026-09-28.bundle` (kullanıcı, 28 Eylül akşam: `bundle verify` "okay", deneme klonu `2f11c84`; etiket buluttan doğrulandı. İlk denemede etiket bayat yerel `master`ı (`5c2f83e`) göstermişti, silinip yeniden kondu) |

- **Yedek yöntemi** (her `master` birleştirmesinden hemen önce, yerel checkout `C:\Users\kullanici\mathverify`'da): (0) `git fetch origin`, `git checkout master`,
  `git merge --ff-only origin/master`, `git log -1 --oneline` = beklenen commit (28 Eylül: kirli `reports/` checkout'u engelledi, etiket bayat `master`ı
  gösterdi); (1) `git tag yedek/master-YYYY-MM-DD[-N] master`; (2) `git bundle create
  C:/Users/kullanici/mathverify-yedek/mathverify-master-<kısa-hash>-YYYY-MM-DD.bundle --all`, `git bundle verify`, deneme klonu; (3) `git push origin <etiket>`,
  buluttan `git ls-remote` ile doğrula; (4) hemen önce `check.py --plan`. Geri dönüş `git reset --hard <etiket>`. Buluttan `master`/etiket push edilmez.
- **Yerel checkout** (30 Eylül akşam): `master` `35af293`; `#13` ve `#14`'ten sonra `git pull` gerekir (çalışma dalı `claude/sharp-lamport-f9m2w3`). Stash'te
  Windows `--full` raporları (`eab80f1`; kullanıcı silebilir), yerel `claude/dreamy-meitner-rvrwlj` eski (birleşmiş).

## 7. Bulut özeti (ölçülmüş)

- Ubuntu 24.04, 4 CPU, 15 GB RAM, ~30 GB disk, root. Ağ: GitHub, PyPI, `raw.githubusercontent.com`, `api.anthropic.com`, `api.meta.ai` açık; Lean/Mathlib
  kapalı (araç ref'inden). Kurulum betiğinde git vekili yok (401), ortam değişkenleri ulaşmaz, belirteç önyükleyicide (§53–§56); kanca 6–15 s; `/opt` ~10.7 GB.
- **Tur bitince uzun iş sürerken konteyner kapatılabiliyor** (26 Eylül `--full`, 2 Kasım son ölçümün ilk koşusu kayboldu): koşu ön planda ≤10 dk'lık beklemelerle izlenir. Oturum sınırında
  konteyner yeniden başlar, arka plan süreçleri ölür (worktree'ler ve scratchpad kalır); ağır süreç semaforu `agir.sh` 3 yuva (§90).
- Meta (§63): akışsız ~31 s'de 502, akış bazen `usage`'sız kesilir, uzun `xhigh`'ta 504. Stop kancası commit + push ister; `ANTHROPIC_BASE_URL` okunmaz
  (§48); `rsync` yok; GitHub GraphQL kapalı, `gh api` (REST) çalışır.

## 8. Komutlar

`PY=.venv/bin/python` (Windows: `.venv/Scripts/python.exe`); her komutta `PYTHONUTF8=1`, proje kökünde.

| Komut | Ne |
|---|---|
| `$PY -m pytest tests -rs` | Takım, atlama nedenleriyle (ek `-q` özeti siler) |
| `$PY scripts/check.py --plan [--no-fetch]` | Hangi kontrol gerekli: YOK / TAMAM (çıkış 0) / TAM (1) (DECISIONS §59, CLAUDE.md) |
| `$PY scripts/check.py` / `--full` | Hızlı (~7 dk) / 24 kapı (~26–40 dk bulutta; günlüğü kendisi yazar, ön planda izlenir) |
| `$PY -m harness.run_eval` · `run_lean --timeout 45` · `adversarial [--workers N]` · `soundness_fuzz` · `calibrate` | Tek tek ölçümler → `reports/` (`--full`dan sonra koşulursa `--plan` o koşuyu kabul etmez; `git restore reports/`) |
| `$PY denetim/2026-10-01/{d4a…d4j,son/<mercek>}/sonda.py <çıktı.json>` · `…/mutasyon.py [-j N] [--kayit F]` · `denetim/2026-09-2{6,7,8}/mutasyon.py` | Dördüncü denetimin ve son saldırının sondaları ve mutasyonları; birleşik ölçüm `d4/araclar/birlesik_olc.sh`; eski mutasyon denetimleri (README 26'da; §60, §63, §65); 25 Eylül ölçümleri `denetim/2026-09-25/araclar/` |
| `$PY denetim/2026-09-29/v14/fark.py dump -j N` | 558 çözümün karar dökümü ve farkı (karar / ilk kötü adım / adım / K4; §91) |
| `$PY -m harness.run_solver --family meta --max-cost 10 --workers 6` · `$PY -m harness.run_f3 --workers 6 --pathb --max-cost 40 --solver-family …` | K4 (kredili; önbellekten gelenler sınıra sayılır) · kredili F3/F4 (`--no-l4/--no-l5/--no-l6`, `--limit`, `--ids`) |
| `$PY scripts/verify_cli.py --item evalset/items/tyt-prob-001.json [--lean] [--text "…"]` · `$PY evalset/build/build_all.py` | Tek öğe · 280 öğeyi yeniden üretir |

Kurulum (Linux; bulutta kanca yapar): `docs/BULUT.md` §4, Lean `docs/LEAN_SETUP.md`. Ortam değişkenleri: arşiv §9 ve `docs/BULUT.md` §5.

## 9. Nerede ne var

Arşiv `docs/arsiv/HANDOFF-2026-09-26.md` (§0 bulut tarihçesi, §2 mimari, **§4 tekrar denenmeyecekler**, §11 tuzaklar); `DECISIONS.md` (§1 kilitli kararlar,
§7–§16 tarih sırasıyla, son §92); `docs/` (`ARCHITECTURE`, `QUALITY`, `SOLVER_FORMAT`, `LLM_LAYERS`, `LEAN_SETUP`, `BULUT`, `sartname/`); `reports/arsiv/`;
`denetim/` (ölçüm ve mutasyon betikleri; dördüncü denetim ve A+ `2026-10-01/`, karar kayıtları `d4/saldiri/<parça><tur>/`, son saldırı `d4/saldiri/son/`).
