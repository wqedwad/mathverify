# HANDOFF — mathverify

> **Son güncelleme: 24 Eylül 2026** (GitHub ve bulut hazırlığı: yeni §0 ve eskiyen her ifadenin
> yanında "Düzeltme (24 Eylül 2026)" notu). §1–§12'nin geri kalanı ve aşağıdaki paragraf 23 Eylül
> oturumunundur.
>
> **25 Eylül eklendi:** kurulum betiğinin belirteçle ikinci gerçek koşusu ve ölçümü (§0.12): claude.ai
> ortam değişkenleri kurulum betiğine ulaşmıyor; belirteç artık önyükleyicinin metninde, araç
> dosyaları gerekirse `raw.githubusercontent.com`'dan. Kararı DECISIONS §54, yeni sıra §7 başında.
>
> **Yeni sohbete geçiş (26 Eylül 2026).** Bu belgenin bu hâli ve 25 Eylül'ün bütün işi (§0.12, §0.13)
> `claude/compassionate-shannon-759r85` dalındadır; `master`a birleştirilene kadar `master`da yoktur.
> Yeni bir bulut sohbeti varsayılan dal `master`dan başlar ve eski HANDOFF'u okur. O yüzden ya dal
> önce `master`a birleştirilir (kullanıcı onayı ve yedek, §5.4), ya da yeni sohbetin ilk mesajı dalı
> söyler: "`claude/compassionate-shannon-759r85` dalından devam et; önce HANDOFF §0.13 ve §7'yi oku."
> Oturumun geçici alanı yeni sohbete taşınmaz; denetimin ölçüm betikleri bu yüzden
> `denetim/2026-09-25/`'dedir.
>
> **25 Eylül, aynı oturumun devamı:** sistematik denetim (§0.13). Cevap metni kod olarak çalışıyordu;
> yanlış onay sınıfları ve formal katmandaki 53 yanlış sertifika kapatıldı. "Lean FP 0" yalnız
> değerlendirme setinde ölçülmüştü (Düzeltme §5.1). Kararlar DECISIONS §55, yeni sıra §7 başında.
>
> **24 Eylül akşamı eklendi:** gerçek bulut ölçümü (§0.8), `master`ın erken birleşmesi olayı (§0.9),
> WSL diskinin C:'yi doldurması olayı (§0.10), ölçümden sonraki kod değişiklikleri (§0.5 eki) ve
> yeni sıradaki adımlar (§7 başı). Kararları DECISIONS §44–49.
>
> **23 Eylül 2026.** Bu belge, projeyi hiç görmemiş bir oturumun **yalnız bu dosyayı
> okuyarak** devralabilmesi için yazıldı. Yazılmadan önce `git status`, `git log`, `git diff`
> çalıştırıldı; adı geçen her dosya, fonksiyon ve komut depoda arandı; sayılar `reports/` altındaki
> üretilmiş raporlardan okundu; `check.py --full` bu oturumda yeniden koşturuldu (son koşu 23/23
> kapı, 438 test geçti, 1 atlandı; günlük `reports/check_full.log`).
>
> **[DOĞRULANMADI]** işareti şu demek: bilgi önceki (özetlenmiş) bir oturumdan geliyor ve bu oturumda
> yeniden ölçülemedi ya da kontrol edilemedi. İşaretsiz her şey bu oturumda kontrol edildi.

**Durum (24 Eylül 2026):** Proje kullanıcının **özel** GitHub deposunda
(`origin` = `https://github.com/wqedwad/asd`, varsayılan dal `master`). İş bundan sonra Claude Code
on the web (bulut oturumları) üzerinden sürecek; bulut el kitabı `docs/BULUT.md`. 24 Eylül işi
(Linux/bulut desteği, sabit Lean sürümleri, çevrimdışı kurulum, sertleştirilmiş kapılar,
`check.py --full` artık 24 kapı) `bulut-2026-09-24` dalında; doğrulandıktan sonra kullanıcı onayıyla
("dal, doğrula, birleştir") ve önce yedek alınarak `master`a fast-forward edilir (§5.4). Özet §0'da.
Son `check.py --full`: **24/24** (Windows, `f0e950c`, ~68 dk; yerel Linux/WSL, `74d9da1`, ~36 dk). Kredili ölçüm kuralı değişmedi (§7).

**Düzeltme (24 Eylül 2026, akşam):** "doğrulandıktan sonra ve önce yedek alınarak" olmadı. Bir
bulut routine oturumu dalın `4d01ba2` hâlini ve tanı raporunu **doğrulamadan ve yedekten önce**
GitHub'daki `master`a push etti (`origin/master` = `572ef57`; §0.9). Kod kaybı yok; yedek sonradan
alındı. Dalın sonraki commit'leri (`7993055`…`4002898`) `572ef57`'nin üstünde, `bulut-2026-09-24`
dalında; `master`a birleştirilmeleri yine kullanıcı onayı ve yedekle olur.

**Düzeltme (24 Eylül 2026, gece, bulut oturumu, `git ls-remote origin`):** birleştirme yapılmış:
GitHub'da `master` = `bulut-2026-09-24` = `18fd298`. GitHub'da ayrıca `yedek/master-2026-09-24-2` →
`572ef57` etiketi var; bu, `master` `572ef57`'den ileri alınmadan önceki yedek olmalı (çıkarım;
yerel bundle'ı buluttan görülemez **[DOĞRULANMADI]**). Bu oturumun ölçümleri ve kurulum betiğinin
GitHub belirteci §0.11'de.

**Durum tek cümlede (23 Eylül):** Kodda yarım kalmış bir iş yok ve commit edilmemiş değişiklik yok.
`scripts/check.py --full` 23/23 kapı geçiyor. 23 Eylül'deki bütün iş (iki denetim, bellek sınırı,
tanımlılık açığı, üç Lean şablonu, pyflakes kapısı, temizlik) `master`da; her birleştirmeden önceki
`master`ın yedeği §5.4'te. Kredili ölçümler (F3/F4) kullanıcı kararıyla lokal iş bitince, kod
dondurulup anahtarlar yenilendikten sonra yapılacak (§7).

**İlk 10 dakika:**

1. Bu belgeyi oku: en az §3 (kararlar), §4 (işe yaramayanlar), §10 (kurallar) ve §11 (tuzaklar).
2. `git status` çalıştır. Bu belgenin yazıldığı andaki commit edilmemiş dosyalar §5.3'te
   listeli. Başka bir değişiklik görürsen, bu belgeden sonra yapılmıştır.
3. `PYTHONUTF8=1 .venv/Scripts/python.exe -m pytest tests -q` çalıştır (Git Bash; PowerShell için
   §9). Beklenen: `438 passed, 1 skipped`, yaklaşık 90 saniye.
   **Düzeltme (24 Eylül 2026):** Linux'ta ve bulutta yorumlayıcı `.venv/bin/python`. Test sayısı
   değişti (838 test): Windows'ta 776 passed / 62 skipped; Linux'ta Lean
   kuruluyken 836 passed / 2 skipped. Atlananlar `-rs` ile
   görülür; Lean kurulu bir makinede "Lean/Mathlib toolchain not available" nedeniyle atlama olmamalı.
4. §7'deki ilk işe geç.

Bulut oturumundaysan önce oturum başındaki `[mathverify bulut oturumu …]` durum bloğuna, sonra
`docs/BULUT.md`'ye bak: Python, `.venv` ve Lean'in hazır olup olmadığı orada yazar.

---

## 0. GitHub ve bulut (24 Eylül 2026)

Bu bölüm 24 Eylül'de eklendi. Kararların gerekçesi ve reddedilen seçenekler DECISIONS §34–43'te,
bulutun işletimi `docs/BULUT.md`'de. *Ek (24 Eylül akşamı):* bulut ölçümü, iki olay ve sonraki
düzeltmeler §0.5 eki ve §0.8–0.10'da, kararları DECISIONS §44–49'da.

### 0.1 Uzak depo

- `origin` = `https://github.com/wqedwad/asd`, **özel**, kullanıcının hesabı. Push edilenler ve
  hash'leri (`git ls-remote origin`, yerel hash'lerle aynı): `master` `23d7c6b` (varsayılan dal),
  `denetim-2026-09-20` `e2aa08d`, `yerel-kalite-2026-09-23` `23d7c6b`, `bulut-2026-09-24`,
  etiketler `yedek/master-2026-09-23` `2744677` ve `yedek/master-2026-09-23-2` `e2aa08d`, ve dal
  olmayan araç ref'i `refs/arac/bulut-v1` (§0.5).
- `bulut-2026-09-24` doğrulandıktan sonra `master`a fast-forward edilir. Kullanıcı onayı var
  ("dal, doğrula, birleştir"); önceki birleştirmeler gibi önce etiket + bundle yedeği alınır (§5.4).
- CI ve LICENSE hâlâ yok (§12).
- **Düzeltme (24 Eylül 2026, akşam):** GitHub'daki `master` artık `572ef57` (`4d01ba2` + tanı
  raporu), routine oturumunun push'uyla, doğrulamadan ve yedekten önce (§0.9). Yeni etiket
  `yedek/master-2026-09-24` → `23d7c6b` (birleştirme öncesi `master`) GitHub'a push edildi.

### 0.2 Bulut ortamı (resmî belgelerden, 24 Eylül'de okundu)

Kaynak: `code.claude.com/docs/en/cloud-environments` ve `claude-code-on-the-web`. Bulutta henüz
oturum açılmadı; aşağıdakiler belgeden, ölçüm değil.

- Ubuntu 24.04 x86_64, ~4 vCPU / 16 GB RAM / 30 GB disk.
- Ortamın "Setup script"i root olarak Claude başlamadan önce koşar, 0 ile çıkmalı, ~5 dakikada
  bitmesi önerilir; sonucu anlık görüntüye alınır ve ~7 gün yeniden kullanılır.
- Depodaki `.claude/settings.json` SessionStart kancaları her oturumda (yerelde de) koşar.
- Kullanıcının `~/.claude` belleği buluta **taşınmaz**. O bellekte olup depoda olmayan kurallar
  (birleştirme öncesi yedek, F3/F4 zamanı) 24 Eylül'de `CLAUDE.md`'ye ve buraya yazıldı.
- Özel depo için Claude GitHub App kurulu olmalı (`https://github.com/apps/claude/installations/new`).
- Bütün GitHub trafiği bir vekilden geçer; oturuma bağlı olmayan depoların release dosyalarına 403
  döner. Bu yüzden `github.com/leanprover/...` indirmeleri orada çalışmaz.
- Varsayılan "Trusted" ağ PyPI ve GitHub'ı (vekil üzerinden) kapsar; `releases.lean-lang.org`,
  `cache.mathlib.org`, `releases.astral.sh` ve `api.meta.ai`'yi kapsamaz.
- Bulut oturumundan `git push` yalnız oturumun **kendi dalına** çalışır: etiketler ve `master`
  buluttan push edilemez; birleştirme PR ile ya da yerel checkout'ta yapılır.
- Boşta kalan VM geri alınınca arka plandaki kabuk işi kaybolur.
- `claude --teleport <id>` bir bulut oturumunu yerel checkout'a çeker.

**Düzeltme (24 Eylül 2026, akşam, ölçüm §0.8):** bulutta artık bir oturum açıldı ve üç ifade
ölçümle düzeltildi. (1) Makine 4 CPU, **15 GB** RAM (belge 16 GB diyordu), ~30 GB boş disk.
(2) GitHub release dosyaları 403 dönmedi: `github.com/leanprover/elan` release indirmesi 200.
Kapalı olanlar `releases.lean-lang.org`, `cache.mathlib.org`, `releases.astral.sh` ve `api.meta.ai`
(hepsi vekilde `CONNECT` 403); açık olanlar `github.com`, `pypi.org`, `raw.githubusercontent.com`,
`api.anthropic.com`. (3) "`master` buluttan push edilemez" koşulsuz doğru değil: oturumun kendi dalı
başladığı daldır ve routine oturumu `master`da başlayıp `origin/master`a push etti (§0.9).

### 0.3 Gizli bilgiler

Kullanıcı kararı (24 Eylül). `.env` bu özel depoda **izlenir** (commit `6323de7`;
`.gitignore` artık `.env`'i yok saymıyor, `.env.*`'i yok sayıyor). Bu, eski "`.env`'i commit etme"
kuralının yerini aldı (§10, `CLAUDE.md`, DECISIONS §35). Değişmeyen: anahtar değerleri hiçbir
çıktıya yazılmaz. Önceki karar sürüyor: anahtarlar kredili F3/F4 koşularından önce yenilenir,
sonra `.env` güncellenip commit edilir. Depo herkese açılacak ya da paylaşılacaksa önce anahtarlar
yenilenir ve `.env` geçmişten temizlenir. `python-dotenv` `.env`'i `override=False` ile ve yalnız
projenin Python süreçlerinde yükler, yani Claude Code'un kendi `ANTHROPIC_API_KEY`'i olmaz.

**Ek (24 Eylül 2026, ölçüm):** bulut kabuğunda `ANTHROPIC_API_KEY` ve `ANTHROPIC_AUTH_TOKEN`
tanımlı değil (yalnız adlar okundu), `.env`'deki anahtar gölgelenmez. `ANTHROPIC_BASE_URL` ise
tanımlı (Claude Code'un kendisi için); istemci artık onu miras almaz, uç noktayı
`MATHVERIFY_ANTHROPIC_BASE_URL` ya da `https://api.anthropic.com` olarak açıkça verir (`4002898`,
DECISIONS §48, `docs/LLM_LAYERS.md`).

### 0.4 Depoya alınanlar

- **Şartname:** `docs/sartname/fable-handoff-matematik-dogrulama_1.md` (kanonik, SHA256
  `079d9355…`) ve `docs/sartname/fable-handoff-matematik-dogrulama_eski.md` (aynı günün 20:52
  sürümü, `b6fc530b…`). Belgeler önceden `C:\Users\kullanici\Downloads`'a işaret ediyordu.
- **Rapor JSON arşivi:** `reports/*.json` kuralı değişmedi (git-ignore'lu, üretilir), ama yedi
  dosyanın 24 Eylül hâli `reports/arsiv/2026-09-24/` altında. İkisi (`f3_results.json`,
  `f3_smoke_results.json`) 18 Eylül'deki ücretli koşudan ve **yeniden üretilemez**. Bulut kancası
  eksik olanları `reports/`a kopyalar, var olanın üstüne yazmaz.

### 0.5 Kod ve betik değişiklikleri (`bulut-2026-09-24`)

| Değişiklik | Davranış | Karar |
|---|---|---|
| `src/mathverify/formal/lean_client.py` | POSIX'te REPL yerel `bash -lc` ile (Windows'ta yine `wsl -d Ubuntu`); `PATH` `${ELAN_HOME:-$HOME/.elan}/bin`; REPL kendi süreç grubunda, `killpg` ile öldürülür (yerel Linux'ta `lake env` ~6.9 GB'lık REPL'i yetim bırakıyordu); başlatıcı yoksa ve (POSIX'te) REPL ikilisi yoksa `LeanUnavailable`, `lake env` hiç başlatılmaz | DECISIONS §40 |
| `scripts/check.py`, `harness/run_lean.py` | her harness'ten önce JSON'u silinir; çıkış kodu sıfır değilse ya da rapor yok/okunamıyorsa o harness'in bütün kapıları aynı adla FAIL; yeni kapı "Lean erişilebilir" (`--full` 23 → 24, hızlı 12); Lean taramanın ortasında kaybolursa (`lean_reached`, `lean_available_end`) dört Lean kapısı da düşer. Linux'ta yorumlayıcı `.venv/bin/python` | DECISIONS §39 |
| `lean/` (`lakefile.toml`, `lean-toolchain`, `lake-manifest.json`, `MathverifyLean.lean`, `MathverifyLean/Basic.lean`, `PINS`) | WSL kurulumunun bayt bayt kopyası; araç zinciri `v4.34.0`, Mathlib `5ed2965`, REPL `646a773`, elan 4.2.4 | DECISIONS §38 |
| `scripts/setup_lean.sh`, `setup_lean_repl.sh` | sabit sürümleri kurar (`stable`/`lake new`/`lake update` yok), ortam değişkenlerine uyar, araç dizininden çevrimdışı kurar, eksik kök modülleri kendisi derler (`lean_fix.sh` artık gereksiz), duman testi geçmezse düşer | DECISIONS §38 |
| `scripts/fetch_artifacts.sh`, `refs/arac/bulut-v1` / `-v2` | Lean araç zinciri, elan, CPython 3.14.6, Mathlib `.ltar` önbelleği (v2'de ayrıca Lake paket ve REPL kaynakları) dal olmayan bir ref'te, 49 MiB parçalar + `SHA256SUMS.full`; normal klon indirmez | DECISIONS §37, `docs/BULUT.md` §11 |
| `scripts/cloud/setup_env.sh`, `scripts/cloud/session_start.sh`, `.claude/settings.json` | ortam kurulum betiği (root, `/opt`, her zaman 0) ve oturum kancası (`.venv`, rapor JSON'ları, Lean ortam değişkenleri, arka planda yeniden deneme, Türkçe durum bloğu) | DECISIONS §41 |
| `requirements.lock` | yerel `.venv`'deki 32 paketin evrensel kilidi | DECISIONS §43 |
| `.gitattributes` | `* text=auto`, `*.sh eol=lf`; `lean/` bayt bayt (`lean/.gitattributes`) | DECISIONS §41 |

**Ek (24 Eylül 2026, akşam): bulut ölçümünden sonraki commit'ler** (`7993055`…`4002898`; beşinci
turun değişiklikleri bu belge yazılırken sürüyordu, tabloda "beşinci turda" diye işaretli):

| Değişiklik | Davranış | Karar |
|---|---|---|
| `harness/run_lean.py`, `scripts/check.py` | her ifadeli kayıt `lean_answered`, `n_attempts`, `n_unanswered` taşır; junk ifadelerinde ve yanlış cevaplı öğelerde her deneme cevaplanmış olmalı (`n_unanswered == 0`), beşinci turda ayrıca cevapsız denetim sondası olmamalı; yoksa junk ve FP kapıları düşer. Zaman aşımı, ölü REPL, yazma hatası, bozuk JSON, hatasız başarısızlık cevap sayılmaz | DECISIONS §46 |
| `src/mathverify/formal/prove.py` | vakum ya da hipotezsiz denetim sondası gerçek bir Lean hükmü almazsa denetim temiz sayılmaz (`audit["unanswered"]`, ilke 7); denetimde Lean kaybolursa `lean_unavailable` hatası yazılır | DECISIONS §47 |
| `scripts/cloud/setup_env.sh`, `scripts/setup_lean.sh`, `scripts/setup_lean_repl.sh` | çekim başarısızsa ya da doğrulanmazsa Python ve Lean aşamaları koşmaz (`reason=fetch`, `(skipped)`, `lean=stale`); Lean betikleri `MATHVERIFY_LEAN_OFFLINE=1` ile her çevrimiçi yedeği reddeder; artefaktlar projeye dokunmadan doğrulanır; sabitlere uymayan proje yanında kurulur ve duman testi yeniden adlandırmadan sonra da geçerse yerine konur, yoksa eskisi geri konur; `.ltar` `$OPT/.mathlib-ltar`'da, kurulumdan sonra silinir; pip `--no-cache-dir`; boş alan denetimi ölçülen boyutla (7.7 GB, araç zinciri yoksa +3.0 GB, +1 GB pay), beşinci turda WSL altında `ext4.vhdx`'i tutan Windows sürücüsüne de bakar (kayıt defteri `BasePath`, yoksa `%LOCALAPPDATA%`, yoksa `/mnt/c`; `MATHVERIFY_WSL_DRIVE_DIR`) | DECISIONS §41, §49; `docs/BULUT.md` §3.2, `docs/LEAN_SETUP.md` |
| `scripts/cloud/session_start.sh` | 3.12'den eski yorumlayıcıyla `.venv` kurmaz; sıra öneğin `python3.14`'ü > `PATH`'teki `python3.14` > `uv python find 3.14` > `python3.12` > `python3.13` > (≥ 3.12 ise) `python3` (beşinci turda; `a02e65c`'de 3.13, 3.12'den önceydi, ama yalnız 3.12.11 ölçüldü); arka plan kurulumundan sonra kendini yeniden çalıştırma komutunu basar; salt okunur `/opt` ve eski sabitlerde ikinci kurulumu başlatmaz, kullanıcı öneki komutunu ~12 GB disk notuyla basar | DECISIONS §42 düzeltmesi |
| `src/mathverify/llm/anthropic_client.py` | `base_url` her zaman açık: `MATHVERIFY_ANTHROPIC_BASE_URL` ya da `https://api.anthropic.com`; platformun `ANTHROPIC_BASE_URL`'i okunmaz | DECISIONS §48 |

Ölçüm (Windows, gerçek tam Lean taraması, 45 s zaman aşımı): 121 sertifika (değişmedi), FP 0, junk
0/17; 869/869 deneme ve 58/58 denetim sondası cevaplı, en yavaş deneme 3.0 s.

### 0.6 Ölçümler (24 Eylül)

| Ne | Sonuç | Nerede |
|---|---|---|
| Lean istemcisi, WSL içinde `wsl.exe`'siz yerel Linux (`test_lean_client_posix` + `test_f5_lean`, ilk tur) | 70 passed / 1 skipped; 6 canlı Lean testi koştu; koşu sonrası yetim REPL 0 | WSL |
| Aynı iki dosya, Windows (ilk tur) | 69 passed / 2 skipped | Windows |
| Lean uçtan uca kurulum (temiz `HOME`, bulut düzeni, 4 CPU, araç ref'inden) | 141 s; araç zinciri/`.ltar` indirmesi 0; manifest aynı; mathlib HEAD `5ed2965`; `bin/lean` SHA256'sı ve 17 738 dosyalık araç zinciri ağacı WSL kurulumuyla aynı; disk ~12 GB | WSL |
| Oturum kancası | ilk koşu 2.5 s, ikinci 85 ms (WSL, root değil); Windows'ta 0 bayt çıktı, ~0.3 s | WSL, Windows |
| Tam takım, yerel Linux (ilk tur, Lean kurulmamış test yatağı) | 464 passed / 7 skipped / 0 failed (6 atlama Lean yokluğundan) | WSL |
| Tam takım, Python 3.12.11 (yedek yorumlayıcı) | 438 passed / 1 skipped (o günkü takım) | Linux |
| `check.py` ilk tur: hızlı takım | 469 passed / 2 skipped; 27 yeni kapı testi; altı mutasyonun her biri testleri düşürdü | commit `9ad931b` |
| Normal `git clone` (araç ref'i inmez) | 3 s, 1.2 MB | — |
| İkinci tur sonrası tam takım, Windows | 776 passed / 62 skipped (62 atlamanın 60'ı yalnız POSIX'te koşan bulut betiği testleri) | Windows, `f0e950c` |
| İkinci tur sonrası tam takım, Linux (Lean kurulu) | 836 passed / 2 skipped (isteğe bağlı indirme testi + kapsam dışı ifade) | WSL, yerel bash, CPython 3.14.6, `74d9da1` |
| `check.py --full` | **24/24** Windows'ta (~68 dk (4107 s; adversaryal 3563 s)) ve yerel Linux'ta (~36 dk (2186 s; adversaryal 1870 s)); kapı değerleri iki platformda aynı | Windows `f0e950c`; WSL `74d9da1` |
| Bulut: kurulum betiği süresi, kanca süresi, `check.py --full` | kurulum (kancanın başlattığı `setup_env.sh --lean-only`) **195 s**: çekim 55 s, Python 1 s, `setup_lean` 119 s, REPL 19 s; kanca **7 s** / **7 s** (elle iki koşu); `check.py --full` bulutta **24/24**, ~63 dk (3793 s; adversaryal 3220 s; 4 vCPU) (ikinci routine oturumu, `master` `74d9da1`) | bulut, routine oturumu, `4d01ba2` (§0.8, `docs/BULUT.md` §12) |
| Bulut: tam takım, `run_lean --limit 5`, hızlı `check.py` | 517 test: 515 passed / 2 skipped / 0 failed (50 s; Lean yüzünden atlama yok); 4 sertifika, FP 0, junk 0, REPL geride kalmadı; 12/12 (115 s) | bulut, routine oturumu, `4d01ba2` |
| Bulut: araç ref'i çekimi | `fetch_artifacts.sh` 50 s, 1.1G git nesnesi, 5/5 SHA256 OK | bulut, routine oturumu |

### 0.7 Dal commit'leri (`git log master..bulut-2026-09-24`, eskiden yeniye)

| Commit | Ne |
|---|---|
| `eff4a7b` | Lean istemcisi Linux'ta yerel bash ile, süreç grubu öldürülür |
| `9ad931b` | `check.py` çöken ya da rapor yazmayan koşuda kapıyı düşürür; "Lean erişilebilir" kapısı |
| `83dd418` | Lean v4.34.0, Mathlib `5ed2965`, REPL `646a773` depoda sabit |
| `7d94a81` | oturum kancası, ortam kurulum betiği, `requirements.lock` |
| `4cce784` | şartname ve rapor JSON arşivi depoda |
| `6323de7` | `.env` özel depoda izlenir (kullanıcı kararı) |

Bu belge yazılırken ikinci tur düzeltmeleri (Lean'in tarama ortasında kaybolması, REPL ikilisi
yokken `lake env`, bulut betiklerinin sertleştirilmesi) henüz commit edilmemişti; `git log` ile
kontrol edin.

**Düzeltme (24 Eylül 2026, akşam):** tablo `6323de7`'de kalmıştı. Sonrası (`git log --oneline
23d7c6b..bulut-2026-09-24`, eskiden yeniye):

| Commit | Ne |
|---|---|
| `96a8e63` | eksik REPL ikilisi Lake'e dokunmadan reddedilir; zaman aşımı testi gerçekten zaman aşımına uğrar |
| `65ff280` | Lean tarama ortasında kaybolursa dört Lean kapısı da düşer |
| `27e5a16` | Lean kurulumu tamamen çevrimdışı (`refs/arac/bulut-v2` kaynakları) |
| `cbe01a7` | kanca durumları, root ön ısıtması repoya yazmaz, kanca kabuğu bash |
| `4d01ba2` | belgeler: GitHub ve bulut, `docs/BULUT.md` (routine oturumunun ölçtüğü hâl) |
| `572ef57` | tanı: bulut ortamı ölçümü (`bulut_tani.md`, şimdi `docs/bulut_tani_2026-09-24.md`); **GitHub'daki `master` burada** (§0.9) |
| `7993055` | Lean'in cevap vermediği junk ya da yanlış cevaplı ifade Lean kapılarını geçemez |
| `eba49b5` | çekim başarısızsa Lean aşaması koşmaz; kurulum sıkı çevrimdışı ve aşamalı |
| `911aca5` | cevapsız vakum ya da hipotezsiz sonda denetimi geçemez (ilke 7) |
| `5e16a31` | Lean kısmen cevap vermediyse junk ve FP kapıları düşer |
| `a02e65c` | kanca 3.12 altı Python'la `.venv` kurmaz; aşamalı güncelleme yeniden adlandırmadan sonra sınanır |
| `4002898` | Anthropic istemcisi platformun `ANTHROPIC_BASE_URL`'ini miras almaz |

`7993055`'ten sonrası `572ef57`'nin üstüne yeniden kuruldu (geçmiş doğrusal); `git log` ile kontrol
edin, beşinci turun commit'leri bunlardan sonra gelir.

### 0.8 Gerçek bulut ölçümü (24 Eylül, routine oturumu)

`claude --cloud` etkileşimli terminal istediği için tek seferlik bir routine açıldı (Sonnet 5,
"Default" ortam, kurulum betiği tanımlı değildi, 11:51–12:01 UTC); `bulut-2026-09-24`'ün `4d01ba2`
hâlini ölçtü. Rapor `docs/bulut_tani_2026-09-24.md`, karar DECISIONS §44; belgeye işlenmiş hâli
`docs/BULUT.md` (§3.1 ağ tablosu, §12 kontrol listesi).

- **Makine:** oturum kullanıcısı root, `HOME=/root`, checkout `/home/user/asd`; Ubuntu 24.04.4,
  4 CPU, 15 GB RAM, ~30 GB boş disk; `/opt` yazılabilir, `sudo` var; git 2.43.0, uv 0.8.17. Sistem
  `python3` **3.11.15** (`/usr/local/bin/python3`), `/usr/bin/python3.12` ve `python3.13` ayrıca var,
  `python3.14` yok.
- **Ortam değişkenleri (yalnız adlar):** `ANTHROPIC_BASE_URL` var; `ANTHROPIC_API_KEY` ve
  `ANTHROPIC_AUTH_TOKEN` yok; normal `Bash` komutlarında `CLAUDE_PROJECT_DIR` boş.
- **Ağ:** açık `github.com` (release dosyaları dahil; elan release'i 200), `pypi.org`,
  `raw.githubusercontent.com`, `api.anthropic.com`, bağlı olmayan açık depolara `git ls-remote`.
  Vekilde `CONNECT` 403: `releases.lean-lang.org`, `cache.mathlib.org`, `releases.astral.sh`,
  `api.meta.ai`. Yani Trusted ağ F3/F4 dışında her şeye yeter; F3/F4 için `api.meta.ai` eklenir.
- **Kurulum:** oturum `master`da başladı ve kanca orada yoktu; dal `master`a ileri sarıldıktan sonra
  kanca elle çalıştırıldı ve kurulumu arka planda başlattı: çekim 55 s, Python 1 s, `setup_lean`
  119 s, REPL 19 s, toplam **195 s** (kurulum betiği yönergesi ~5 dk). Bağımsız çekim denemesi 50 s,
  5/5 SHA256 OK.
- **Sonrası:** tam takım 515 passed / 2 skipped / 0 failed (50 s), `run_lean --limit 5` 4 sertifika /
  FP 0 / junk 0, hızlı `check.py` 12/12 (115 s), REPL geride kalmadı.
- **Bulunan iki sorun, ikisi de düzeltildi:** (1) kurulum betiği yokken kanca çıplak `python3`'ü
  (3.11.15) seçti ve `.venv` kurulamadı → 3.12 altı reddedilir, sıra §0.5 ekinde (`a02e65c` +
  beşinci tur; DECISIONS §42 düzeltmesi); (2) `ANTHROPIC_BASE_URL` SDK'ya miras kalacaktı →
  `4002898` (DECISIONS §48).
- **Ölçülmeyenler** (ilk normal oturumda, `docs/BULUT.md` §12): kurulum betiği alanından gerçek
  koşu, anlık görüntünün `/opt`'u koruması, platformun tetiklediği kanca, `CLAUDE_ENV_FILE`'ın
  sonraki komutlara ulaşması, bulutta `check.py --full` ve tam Lean taraması, etiket push'u.
- **Düzeltme (24 Eylül 2026, akşam) — İkinci routine oturumu (24 Eylül 16:49–18:04 UTC, `master` = `74d9da1`, kurulum betiği tanımlı değil, push yok):** yukarıdaki açıkların çoğu ölçüldü. Platform kancayı oturum açılışında **kendiliğinden** çalıştırdı (10 s; 3.14 henüz yokken 3.12.3 seçildi, `.venv` 9 s, Lean arka planda başlatıldı). Kancanın dışa aktardığı `ELAN_HOME` ve `MATHVERIFY_*` sonraki her `Bash` komutunda görünüyor (`$CLAUDE_ENV_FILE` komutta boş; platform değişkenleri kabuk anlık görüntüsüyle enjekte ediyor). Lean 239 s'de hazır (çekim 54, Python 1, `setup_lean` 152, REPL 27). Kurulum betiğinin tamamı temiz önekte 234 s (çekim 58, Python 1, uv ön ısıtma 11, `setup_lean` 144, REPL 26; 11 GB). 3.12.3 yedek `.venv`'le Lean kurulurken takım 824 passed / 14 skipped. `check.py --full` **24/24**, ~63 dk (3793 s; adversaryal 3220 s; 4 vCPU); birim testleri 833 passed / 5 skipped; kapı değerleri Windows ve yerel Linux ile aynı (121 sertifika, FP 0, junk 0/17, saldırı %0). Arka planda süren `--full` sırasında ajan boşta beklediği hâlde makine geri alınmadı. Yeni gözlemler: oturum `HEAD detached from refs/heads/master` ile başladı (ilk routine `master` dalındaydı); ortamın kendi stop hook'u (`~/.claude/stop-hook-git-check.sh`) commit edilmemiş değişiklik (ör. `check.py`'nin yeniden yazdığı `reports/`) görünce commit + push ister. Hâlâ açık: kurulum betiğinin claude.ai alanından gerçek koşusu ve anlık görüntünün `/opt`'u koruması, etiket push'u.

### 0.9 Olay: `master` doğrulamadan ve yedekten önce ileri alındı (24 Eylül)

Routine istemini yazan oturumun (Claude'un) hatası (DECISIONS §45). İstem "oturumun kendi dalına
push et" diyordu. Routine oturumu varsayılan dal `master`da başladığı için oturumun dalı
`master`dı: oturum `master`ı
`bulut-2026-09-24`'e (`4d01ba2`) ileri sardı, üstüne `bulut_tani.md`'yi ekledi ve
`origin/master` = `572ef57` olarak push etti. Yani `master` birleştirmesi son doğrulamadan
(`check.py --full`) ve yedekten önce oldu.

- **Kod kaybı yok:** `4d01ba2..572ef57` farkı yalnız rapor dosyası.
- **Yedek sonradan alındı:** birleştirme öncesi `master` `23d7c6b` → etiket
  `yedek/master-2026-09-24` (GitHub'a da push edildi) ve
  `C:\Users\kullanici\mathverify-yedek\mathverify-master-23d7c6b-2026-09-24.bundle` (`git bundle verify`
  geçti). Tablo §5.4'te.
- Dalın sonraki commit'leri `572ef57`'nin üstüne taşındı; geçmiş doğrusal.
- **Kural** (`CLAUDE.md` "Asla", `docs/BULUT.md` §13): bir bulut routine istemi push hedefini
  açıkça **yeni bir dal** olarak verir ya da hiç push istemez; "kendi dalına" gibi göreli hedef
  yazılmaz.

### 0.10 Olay: WSL diski C:'yi doldurdu (24 Eylül)

Bir ajanın gerçek Lean testleri WSL içinde `/var/tmp` altına ~60 GB kurulum yazdı. WSL'nin disk
imajı `ext4.vhdx` 103.8 GB'a büyüdü, C: 0 bayta düştü ve WSL açılamadı. WSL içinde `df` sanal diski
gösterdiği (942 GB boş) için hiçbir şey uyarmadı (DECISIONS §49).

- **Temizlik:** Windows'taki çalışma kopyaları ve WSL içindeki ajan test ağaçları silindi;
  kullanıcının kendi `~/mathverify-lean`, `~/repl` ve `~/.elan`'ına dokunulmadı; WSL yine 15 GB
  kullanıyor; `fstrim` çalıştırıldı.
- **Açık:** `.vhdx` kendiliğinden küçülmez. Bu belge yazılırken
  `C:\Users\kullanici\AppData\Local\wsl\{WSL-GUID}\ext4.vhdx` hâlâ 103.8 GB
  ve C:'de 6.1 GB boş. Sıkıştırma yönetici ister ve kullanıcıya bırakıldı (§7, adım 1).
  **Düzeltme (24 Eylül 2026, 16:54):** kullanıcının yetkisiyle sıkıştırıldı. UAC onayıyla yönetici PowerShell'de `wsl --shutdown` + `diskpart` (`attach vdisk readonly`, `compact vdisk`, `detach vdisk`) çalıştı, 20 s sürdü: `.vhdx` 103.79 → 15.98 GB, C: boş alanı 6.10 → 93.95 GB. Ardından WSL açıldı; Lean 4.34.0, Mathlib `5ed2965` ve REPL duman testi (`{"env": 0}`) sağlam.
- **Önlem:** `setup_lean.sh`'in boş alan denetimi WSL altında `.vhdx`'i tutan Windows sürücüsüne de
  bakar (bulunamazsa `/mnt/c`; `docs/LEAN_SETUP.md`) ve yeni kurulumu ölçülen boyutla hesaplar (7.7 GB, araç zinciri yoksa +3.0 GB, +1 GB pay;
  beşinci tur). Kural (`CLAUDE.md` "Ortam tuzakları / Windows"): WSL'de büyük bir kurulumdan önce
  C:'nin boş alanına Windows tarafından bakılır.

### 0.11 İlk normal bulut oturumu: kurulum betiği alanından gerçek koşu (24 Eylül, gece)

Kullanıcının açtığı normal (routine olmayan) bir bulut oturumu, `master` = `18fd298`, ortamın
"Setup script" alanında önyükleyici tanımlı. Dal `claude/funny-cray-bey5o1`. Karar DECISIONS §53.

- **Kurulum betiği gerçekten koştu ama hiçbir şey kuramadı.** `setup_env.status`:
  `FAILED mode=all ... reason=fetch python=missing lean=missing total=0s`, 19:54:52 UTC, kancadan
  2 s önce (kanca yalnız `--lean-only` başlatır; `mode=all` alandan gelir). Günlükteki satır
  `repository: /home/user/asd (18fd298)`: checkout betik koşarken hazırdı. Araç ref'inin çekimi 0 s'de
  düştü: `fatal: could not read Username for 'https://github.com'` (özel depo 401 döndü), yedek yol
  (`git ls-remote origin`) da aynı hatayla. Python ve Lean aşamaları bilerek atlandı, betik 0 ile
  çıktı, oturum engellenmedi.
- **Neden** (resmî belge, `code.claude.com/docs/en/cloud-environments`, 24 Eylül'de okundu): Claude
  Code ajan vekiline kurulum betiğinden **sonra** bağlanır; GitHub kimliğini oturumdaki GitHub vekili
  ekler. Oturum içinde yeniden üretildi: vekil değişkenleri kaldırılıp GitHub'a doğrudan gidilince
  aynı 401 ve aynı ileti; vekil üzerinden (git kimlik değişkenleri kaldırılsa bile) çekim çalışıyor.
  Ortamın "API credentials" özelliği çözüm değil: belgeye göre GitHub isteklerine ve kurulum betiği
  isteklerine hiç eklenmez.
- **Sonucu:** belgeye göre anlık görüntü kurulum betiğinin ilk koşusundan sonra alınır, ~7 gün
  yeniden kullanılır; betik yalnız metni ya da ağ ayarı değişince ya da süre dolunca yeniden koşar.
  Görüntüde Lean ve Python 3.14.6 yok; her yeni sohbette kanca kurulumu arka planda yeniden yapar.
- **Kancanın devraldığı kurulum:** kanca 7 s (3.14.6 yok, yedek 3.12.3, `.venv` 7 s), Lean
  **167 s**'de hazır: çekim 48 s, Python 1 s, `setup_lean` 99 s, REPL 17 s (`OK mode=lean`).
  Kancanın elle yeniden koşusu 6 s, `.venv` 3.14.6 ile. `lean_available()` True. `pytest tests -rs`:
  838 test, **833 passed / 5 skipped / 0 failed**, 89 s (atlananlar: 3'ü root altında salt okunur
  dizin, 1 isteğe bağlı indirme, 1 kapsam dışı ifade; Lean yüzünden yok).
- **Aynı sohbete devam:** ~50 dk boşluktan sonra makine yeniden başlatılmıştı (açılış 20:50:45 UTC)
  ama disk korunmuştu: Lean, `.venv`, günlükler yerinde; kanca 15 s, Lean HAZIR, kurulum betiği
  yeniden koşmadı (belgeyle uyumlu: "resuming never re-runs the setup script").
- **Devam ettirilen sohbette Lean'in ilk açılışı çok yavaş.** Sohbet ikinci kez devam ettirilince
  makine yine yeniden başlatılmıştı (açılış 21:45:52 UTC). Ardından koşan tam takımda ilk canlı Lean
  testi (`test_lean_proves_true_and_refuses_false`) pytest'in 300 s sınırında zaman aşımına uğradı ve
  sonraki 8 canlı Lean testi "Lean/Mathlib toolchain not available" ile atlandı (843 test: 1 failed,
  13 skipped, 476 s). Hemen sonra `lean_available()` 5.8 s'de True; disk önbelleği bilerek
  boşaltılınca (`drop_caches`) 26.9 s; Lean test dosyaları ve tam takım yeniden temiz: **838 passed /
  5 skipped / 0 failed**, 94 s. Yani yeniden başlatmadan sonraki ilk açılış sıradan bir soğuk
  önbellekten çok daha yavaş; neden (geri yüklenen diskin ilk okunuşta yavaş gelmesi) çıkarım
  **[DOĞRULANMADI]**. Kural: devam ettirilmiş bir sohbette `check.py --full` ya da Lean testlerinden
  önce Lean dosyaları bir kez okunarak ısıtılır (komut `docs/BULUT.md` §8; `lean_available(900)`
  yetmez, istemcinin `import Mathlib` sınırı ayrıca 300 s: `LeanClient.boot_timeout`); yoksa "Lean
  erişilebilir" kapısı ve canlı Lean testleri bilerek düşer. Isıtmanın bu durumu çözdüğü ölçülmedi. Kancanın arka planda ısıtması önerildi,
  yapılmadı (§7).
- **Düzeltme: `MATHVERIFY_GITHUB_TOKEN`** (`scripts/fetch_artifacts.sh`, DECISIONS §53). Ortam
  değişkeninde yalnız bu depoyu okuyabilen bir GitHub belirteci varsa, çekim düz denemesi düştükten
  **sonra** onunla bir kez daha denenir; yalnız `https://github.com/` altındaki adrese, komut satırına,
  günlüğe ya da diske yazılmadan. Oturum içinde düz deneme vekil sayesinde başarılı olduğu için
  belirteç hiç gönderilmez. 7 yeni test (gerçek `git http-backend`, 401 döndüren yerel sunucu);
  8 mutasyonun hepsi en az bir testi düşürdü. Takım 845 test. `check.py --full` **24/24** (`b042729`, 22:15–22:55 UTC, aşamaların toplamı 2344 s ≈ 39 dk: pytest 98, `run_eval` 58, `run_lean` 92, adversaryal 1985, sağlamlık 79, kalibrasyon 31 s); birim testleri 840 passed / 5 skipped; kapı değerleri önceki koşularla aynı (121 sertifika, FP 0, junk 0/17, 21 139 saldırıda %0, 0/448, 0/214, 0/46, 0/184, 0/6); raporlarda yalnız süre satırları değişti. Gerçek belirteçle kurulum betiği
  alanından koşu henüz ölçülmedi **[DOĞRULANMADI]**: kullanıcı adımları `docs/BULUT.md` "Senin yapman
  gerekenler" 3. madde, ölçülecekler §12.
  **Düzeltme (25 Eylül 2026, ölçüm §0.12):** belirteç claude.ai ortam değişkeni olarak verilince
  kurulum betiğine hiç ulaşmadı (oturumda tanımlıydı, betik "not set" yazdı). Belirteç artık
  önyükleyicinin metninde verilir ve `fetch_artifacts.sh` git denemeleri düşerse dosyaları
  `raw.githubusercontent.com`'dan indirir (DECISIONS §54).

### 0.12 İkinci normal bulut oturumu: belirteç ortam değişkeninde, kurulum betiği yine düştü (25 Eylül)

Kullanıcının açtığı normal bir bulut oturumu (`master` = `d66bf2d`, `wqedwad/asd#1` birleşmişti; dal
`claude/compassionate-shannon-759r85`). Kullanıcı `docs/BULUT.md` "Senin yapman gerekenler" 3.
maddeyi yapmıştı. Oturumun isteği "kurulum betiğini ölç". Karar DECISIONS §54.

- **Kurulum betiği yine düştü.** Makine 08:02:44 UTC'de açıldı; alan 08:02:50'de `mode=all` koştu
  (checkout `/home/user/asd` `d66bf2d` hazırdı). Düz çekim `could not read Username`, ardından
  `MATHVERIFY_GITHUB_TOKEN is not set: no token retry`; durum
  `FAILED mode=all failed=[fetch_artifacts python uv_prewarm setup_lean setup_lean_repl] ... reason=fetch python=missing lean=missing total=1s`.
  Oturumun `Bash`'inde aynı değişken tanımlı (`github_pat_` biçiminde, 93 karakter; değer basılmadı).
- **Neden: claude.ai ortam değişkenleri kurulum betiğine ulaşmıyor, yalnız oturuma veriliyor.**
  Başka açıklamalar ölçümle elendi: kendi betiklerimiz değil (dışa aktarılmış bir değişken
  önyükleyiciden `token_applies`'a ulaşıyor); zamanlama değil (platform günlüğü
  `/tmp/environment-manager-*.diag.log`: `init_script_completed` 08:02:51.149,
  `starting_claude_code` 08:02:51.165); eski görüntü ya da başka makine değil (24 Eylül kaydı yok;
  platform günlüğündeki betik çıktısı 2137 bayt = bu koşunun `setup_env.log` satırları). Resmî
  belge sessiz; aynı gözlem `anthropics/claude-code#63541`, `#55440` ve bağımsız bir kurulum
  deposunda. Açık kalan dar varyantlar (boş değer, dışa aktarılmamış değer, ada göre süzme) düzeltmeyi
  etkilemez.
- **Anlık görüntü yeniden kuruldu:** `/opt/mathverify-logs`'ta 24 Eylül'den kayıt yok ve betik bu
  makinede açılıştan 6 s sonra koştu. Belgeye göre betik ancak metni ya da ağ ayarı değişince (ya da
  ~7 günde) yeniden koşar. Platform günlüğü (`/tmp/env-manager.log`) alandaki betiği 618 bayt
  yazıyor, belgelenen önyükleyici 605 bayt: kısa bir ek satır (kullanıcının yorum satırıyla
  tutarlı), belirteç yok. Aynı günlükte betikten önce `Git proxy sidecar skipped: boot-clone mount
  is on`: kurulum betiği aşamasında GitHub git vekili çalışmıyor.
- **Belirteç geçerli, ama hangi yoldan?** Oturum içinde GitHub vekili `api.github.com`'a giden
  `Authorization` başlığını kendi kimliğiyle değiştiriyor: uydurma belirteç de 200 aldı, aynı
  `Github-Authentication-Token-Expiration` ile; kimliksiz git isteğine de özel depo için 200. Yani
  oturum içinden belirteç git yolunda sınanamıyor ve kurulum betiği aşamasında vekilin başlığı
  geçirip geçirmediği bilinmiyor. `raw.githubusercontent.com` ise belgeye göre güvenlik vekilinin
  arkasında: başlıksız 404, uydurma belirteçle 404, gerçek belirteçle 200 (belirteç geçerli, başlık
  değişmeden ulaşıyor). Ref adıyla ve commit'le adreslenebiliyor; `SHA256SUMS.parts` ref'te var.
- **Kancanın devraldığı kurulum (bu oturum):** kanca 8 s (3.14.6 yok, yedek 3.12.3, `.venv` 7 s),
  Lean **222 s**'de hazır (`OK mode=lean`: çekim 55, Python 1, `setup_lean` 142, REPL 20). Kancanın
  elle yeniden koşusu **35 s**: `.venv` 3.14.6 ile; uv ön ısıtması hiç koşmadığı için çevrimdışı
  deneme düştü, çevrimiçi çözümleme 27.5 s sürdü (24 Eylül gecesi aynı adım 6 s'ydi). Tam takım 845
  test: **840 passed / 5 skipped / 0 failed**, 112 s (atlananlar: 3'ü root altında salt okunur dizin,
  1 isteğe bağlı indirme, 1 kapsam dışı ifade).
- **Alanın yapacağı tam koşu** (oturum içinden, temiz önek, oturumun ağ yolu): `OK mode=all`
  **192 s** (çekim 47, Python 1, uv ön ısıtma 8, `setup_lean` 118, REPL 22; 11 GB). ~5 dk yönergesinin
  altında.
- **Düzeltme** (DECISIONS §54): (1) Belirteç Setup script metnine yapıştırılır. Önyükleyicinin
  `T=''` satırı dışa aktarılmaz, `setup_env.sh`'e yalnız o komut için verilir, `{ set +vx; }` satırı
  izlenen bir kabuğun belirteci basmasını önler, `|| true` betik `-e` ile koşsa bile oturumu
  engellemez. (2) `setup_env.sh` belirteci yalnız çekim aşamasına verir; uv, pip, Lean ve Lake
  görmez. (3) `fetch_artifacts.sh` belirteci kendi kabuğunda tutar. Düz çekim ve belirteçle git
  çekimi düşerse dosyaları `raw.githubusercontent.com`'dan indirir, her parçayı `SHA256SUMS.parts`'a
  karşı doğrular (`MATHVERIFY_ARTIFACT_VIA=raw` yalnız bu yol). Ölçüm (oturum içinde, gerçek
  belirteç): **32 s**, 5/5 SHA256 OK, günlükte belirteç 0 kez. (4) `setup_env.sh` gördüğü
  değişkenlerin yalnız adlarını yazar (`environment (names only): set=[...] unset=[...]`); sonraki
  alan koşusu, kurulum betiği aşamasında belirteç, vekil değişkenleri ve `CLAUDE_PROJECT_DIR` olup
  olmadığını gösterir. (5) **Süre sınırı:** resmî belgeye göre ~5 dakikayı aşan kurulum betiği yeni
  oturumları kilitler; çekim başarılı olunca tam koşu 192–234 s sürüyor. Önyükleyici `setup_env.sh`'i
  `timeout -k 10 250` ile koşturur; sınıra takılan koşu `reason=terminated` yazar, kanca kalanını
  kurar. (6) Bağımsız inceleme bulguları (curl çıkış durumu, `curl -q`, adres ve ref denetimi,
  `unset` sırası) düzeltildi. Testler ve `check.py --full` sonucu DECISIONS §54'te.
- **Doğrulama (25 Eylül 2026):** `check.py --full` **24/24** (`b4e91f0`, 09:16–10:05 UTC, 2937 s ≈ 49 dk: pytest 131, `run_eval` 72, `run_lean` 117, adversaryal 2478, sağlamlık 98, kalibrasyon 39 s); birim testleri 870 passed / 5 skipped; kapı değerleri önceki koşularla aynı (121 sertifika, Lean FP 0, junk 0/17, 21 139 saldırıda %0, 0/448, 0/214, 0/46, 0/184, 0/6); raporlarda yalnız süre satırları değişti. Ardından bağımsız incelemenin son bulgusu için bir test eklendi (`9aa6c2d`, betik değişmedi): tam takım 876 test, **871 passed / 5 skipped / 0 failed** (136 s; Lean yüzünden atlama yok); toplam 35 mutasyonun hepsi en az bir testi düşürdü.
- **Açık [DOĞRULANMADI]:** kurulum betiği aşamasında `raw.githubusercontent.com`'a (ya da belirteçle
  git'e) erişim. Bu değişiklik `master`a birleşip kullanıcı önyükleyiciyi belirteçle güncelleyince ilk
  yeni sohbette ölçülür (`docs/BULUT.md` §12).

### 0.13 25 Eylül sistematik denetimi: kod çalıştırma, yanlış onay sınıfları, formal katman

Aynı oturumun devamı (dal `claude/compassionate-shannon-759r85`). Kullanıcı sordu: "localdeki bütün
sorunlar çözülmüş mü, tek kalan API anahtarı ekleyip test etmek mi?" **Cevap: hayır.** Yeni bir
denetim, yerelde krediye bağlı olmayan ciddi açıklar buldu. Hepsi aynı oturumda düzeltildi ve
ölçüldü. Karar ve ayrıntı DECISIONS §55.

- **Yöntem.** Beş bağımsız denetçi (A cebir/sayma, B kalkülüs/trig, C geometri/kombinatorik/seri/
  lineer cebir, D ayrıştırıcı/girdi/birleştirme, E Lean), her bulgu kendi doğruluk denetimiyle
  (kesin SymPy, kaba kuvvet, el ispatı). Düzeltmeler dosya sahipliğine göre beş dalda yapıldı
  (`claude/denetim-wt|geo|alg|lean|calc`; çakışma yalnız `certify/domain.py`'de ve çekirdek test
  dosyasında, ikisi de ekleme) ve `claude/denetim-int`'te birleştirilip oturum dalına ileri sarıldı.
  Lean'i yalnız bir ajan kullandı (tek REPL).
- **En ciddi bulgu: kod çalıştırma.** Cevap metni `sympify` ile okunduğunda Python kodu doğrulayıcının
  kendi sürecinde çalışıyordu (`__import__('os')...`). Birleştirmeden sonra ikinci kapı bulundu:
  `sympify(..., strict=True)` sözlük/demet içindeki metni yine değerlendirir. Artık: AST beyaz
  listesi (`guarded_parse_expr`), metin dışı değer yalnız sayı/SymPy nesnesi (`sympify_nontext`),
  girdi biçimi denetimi (`MalformedSolution`, `MalformedIR`).
- **Ölçüm (eski kod `da963b2` → yeni kod, aynı betikler, Lean'siz):**

  | Ölçüm | Eski kod | Yeni kod |
  |---|---|---|
  | Enjeksiyon taraması (doğru 141 cevap × 2 sarmal): kod çalıştırıp CORRECT | 113/282 | 0/282 |
  | Alan taraması (23 görev türü, her alan × 7 tür, 4753 durum): kod çalıştırma / sızan istisna | ilk öğelerde 18 kod çalıştırma, sonra asıldı | 0 / 0 |
  | Denetçi A tekrar betikleri (17 dosya): hatalı karar | 78 | 0 |
  | Denetçi A sonda derlemi (25 betik): yanlış onay / yanlış ret | 85 / 38 | 2 / 3 (4'ü etiket hatası, 1'i bilinen sınır) |
  | Denetçi B tekrar betikleri (23 dosya): hatalı karar | 94 | 0 |
  | Denetçi E vakaları, deterministik katman: yanlış karar | 17 | 0 |
  | Lean: yanlış iddiaya sertifika (denetçinin 98'lik kümesi; el ispatı 14) | 53/98 (12/14) | 0/99 (0/14) |
  | `run_lean`: sertifika / FP / junk | 121 / 0 / 0 of 17 | 121 / 0 / 0 of 33 |

- **Değerlendirme seti** (280 kayıt): hiçbir karar değişmedi; cevap düzeyi 154 / 0 / 84 / 0 / 0
  (TP / FP / TN / FN / UNKNOWN), çözüm düzeyinde bilinen tek FP `tyt-prob-018`.
- **Düzeltme (25 Eylül 2026): "Lean FP 0" yalnız değerlendirme setindeki sorularda ölçülmüştü.**
  Denetçinin set dışında yazdığı 98 yanlış iddianın 53'ü Lean'de temiz sertifika alıyordu (model
  yazımı 14 ispatın 12'si de). Önceki oturum raporlarında bu sayı genel bir güvence gibi sunuldu;
  yanlıştı. Düzeltmeden sonra 0/99 ve 0/14; yeni sınıflar `run_lean`'in junk kapısında kalıcı (17 → 33).
- **Hatalarım (bu oturum).** (1) İlk geniş "verilen eşitsizlik tanım kümesini daraltır" kuralı
  birleştirmede iki doğru cevabı bozdu (sayma TypeError, küp kökü); ölçümle bulundu ve daraltıldı.
  (2) Arka plan komutunda `a && (b) & (c)` yazdım: `cd` ve değişken yalnız ilk alt kabuğa uygulandı,
  bir koşu hiç başlamadı ve ana checkout'a boş bir dosya düştü (taşındı). (3) `pkill -f <desen>`
  komut satırında deseni taşıyan kendi kabuğumu iki kez öldürdü (çıkış 144; §11). (4) "Önce" tür
  taraması ileri sardığım dalın kaynağını okuyordu; `da963b2`'nin ayrı bir kopyasında yeniden koşuldu.
- **Açık kalanlar** (hiçbiri doğru cevabı reddetmez; UNKNOWN kapsama kaybı ya da bilinen sınır):
  kanıtsız eşdeğer doğru biçimleri, sembolik kanıtı olmayan kapalı biçimler, periyodik tanım kümeli
  ilkeller, sonsuz sınırlı integraller, gelenek farkı olan tek taraflı durumlar, `asec`/`acsc`
  ayrıştırıcıda yok. Yanlış çarpanlara ayırma adımı (`x² − 5x + 6 = 2(x − 2)(x − 3)`, öncül
  x² − 5x + 6 = 0) öncüllerin çözümlerinde doğru olduğundan reddedilmez (DECISIONS §55).
- **Ölçüm betikleri depoda (26 Eylül eki):** `denetim/2026-09-25/` (README'de koşturma ve sonuçlar).
  Depodaki çalıştırıcı eski kodda aynı sayıları üretti. İlk kez koşulan C grubu (geometri denetçisinin
  beklentili betikleri) bir açık daha gösterdi: toplamın bağlı değişkeni (`Sum(k, (k, 1, 4)) = 11`)
  tanımsız ad sayılıp yanlış adım atlanıyordu; düzeltildi (DECISIONS §55 Ek). C'de kalan 20 fark:
  16 UNKNOWN (kapsama), 2 beklenti hatası, 1 bilinen sınır (iki kayıt).
- **Son doğrulama (26 Eylül):** `check.py --full` **24/24** (`67d1619`, ≈ 60 dk), **1321 passed / 5 skipped**,
  Lean 121 / FP 0 / junk 0/33, saldırı %0. Konteyner yeniden başlatılınca ilk Lean açılışı ~400 s
  sürüyor; `--full` artık önce Lean'i ısıtır (DECISIONS §55 Ek 3). Önceki doğrulama:
- **Doğrulama:** `check.py --full` **24/24** (`c1d4c3e`, 16:30–17:30 UTC, aşamaların toplamı 3595 s ≈ 60 dk: pytest 276, `run_eval` 87, `run_lean` 131, adversaryal 2936, sağlamlık 119, kalibrasyon 44 s); birim testleri **1314 passed / 5 skipped** (denetim öncesi 871 / 5); Lean 121 sertifika (24 Eylül kümesiyle aynı), FP 0, junk **0/33**; 21 139 saldırıda %0; 0/448, 0/214, 0/46, 0/184, 0/6. İlk birleşik koşu (`0eb99b6`) de 24/24 geçmişti, ama adversaryal raporda anlamı koruyan saldırılarda UNKNOWN'a düşen 2896 → 2964 çıktı: `x in {…}` adım biçimi görünmez karakter ya da `\boxed{}` ile 7 doğru çözümde UNKNOWN oluyordu. Düzeltildi (`c1d4c3e`); son koşuda 2894, karşıt karara dönen yine 0. Değerlendirme setinde karar değişmedi. Denetimin 29 düzeltme commit'i (beş dal ve birleşik dal) ve 10 birleştirme commit'i bu dalda (`da963b2..`); geçici dallar ve worktree'ler silindi (içerikleri bu dalda). Push: yalnız bu oturumun dalı.


---

## 1. Proje özeti

### Ne yapıyor

Bir matematik sorusu (Türkçe; TYT/AYT biçiminde çoktan seçmeli ya da üniversite düzeyinde açık uçlu)
ve bir AI'ın ürettiği çözüm verildiğinde, çözümün geçerli olup olmadığına **üç değerli** karar verir:
`CORRECT` / `INCORRECT` / `UNKNOWN`. Çıktı bir `VerificationResult`: verdict, güven, ilk hatalı adım,
katman sonuçları, Türkçe karar izi, sürümler ve bayraklar.

İki şey onu sıradan bir "cevabı karşılaştır" aracından ayırır:

1. **Cevap anahtarı doğrulama hattına hiç girmez.** `ProblemIR`'da cevap alanı yoktur.
   `src/mathverify/ir.py` içindeki `FORBIDDEN_KEYS` (gold_answer, answer_key, expected,
   correct_option, cell, …) IR'ın ve çözümün her seviyesinde özyinelemeli taranır; bulunursa
   `LeakageError` fırlatılır. Etiketler yalnız harness'te durur.
2. **Karar üretilerek değil, kanıtlanarak verilir.** Katmanlar çözücünün *iddiasını* sınar;
   cevabı kendileri üretip karşılaştırmazlar. Çekimser kalmak (`UNKNOWN`) bir başarısızlık değil,
   birinci sınıf bir sonuçtur.

### Kim için

Kendi AI çözücüsü olan bir matematik eğitim uygulamasının doğrulama bileşeni olarak tasarlandı.
Girdi iki yoldan gelir (karar D1): uygulamanın kendi çözücüsünün yapısal çıktısı (**yol a**,
`docs/SOLVER_FORMAT.md`) ya da dış bir serbest metin çözüm (**yol b**). Uygulamanın kendisi bu depoda
değil. Adı ne depoda ne şartnamede geçiyor (23 Eylül'de ikisi de tarandı; şartname yalnız
"uygulama soruyu bir AI'a kendisi soruyor" diyor). Adı ve ayrıntıları için kullanıcıya sorulmalı.

Özgün şartname: `C:\Users\kullanici\Downloads\fable-handoff-matematik-dogrulama_1.md` (18 Eylül 2026,
47 KB; dosya yerinde). Numaralı literatür kaynakları (`[5]`, `[10]` gibi) oradaki §13'e aittir.
Kilitli kararlar (D1–D6) oradan gelir ve **yeniden sorulmaz**.

**Düzeltme (24 Eylül 2026):** şartname artık depoda:
`docs/sartname/fable-handoff-matematik-dogrulama_1.md` (46 971 B, SHA256 `079d9355…`, kanonik).
Aynı günün daha eski 20:52 sürümü `docs/sartname/fable-handoff-matematik-dogrulama_eski.md`
(`b6fc530b…`). `Downloads` yolu yalnız kullanıcının makinesinde geçerliydi; bulut onu göremez.

### Temel amaç ve başarı ölçütü

Yanlış onay, yanlış redden daha pahalıdır (D6). "Çalışıyor" demenin tek geçerli kanıtı, §9
değerlendirme setinde **ölçülmüş** precision/recall değeridir. Testlerin geçmesi ya da çıktının
makul görünmesi kanıt sayılmaz.

### Tech stack

| Bileşen | Sürüm | Not |
|---|---|---|
| Python | 3.14.7 (`.venv`) | `pyproject.toml`: `requires-python >=3.12` |
| SymPy | 1.14.0 | sabit |
| mpmath | 1.3.0 | sabit |
| z3-solver | 5.1.0.0 | sabit |
| math-verify | 0.9.0 | yalnız ikinci görüş |
| latex2sympy2-extended | 1.11.0 | LaTeX dalı |
| anthropic / python-dotenv | 1.7.0 / 1.2.3 | `[llm]` ekstrası; beta API yüzeyi kullanıldığı için sabit |
| pytest (≥9), pytest-timeout, hypothesis | — | `[dev]` ekstrası |
| Lean 4 + Mathlib | v4.34.0 | WSL `Ubuntu` içinde; `reports/lean_setup.log` |
| LLM aileleri | `claude-opus-5` (anthropic), `muse-spark-1.3` (meta) | ortam değişkeniyle değiştirilebilir |

Depo yereldir: git uzak deposu, CI ve LICENSE yok. Proje tek makinede duruyor.

**Düzeltme (24 Eylül 2026):** uzak depo var: özel `https://github.com/wqedwad/asd` (`origin`, §0.1).
CI ve LICENSE hâlâ yok. Tabloya ek: Linux/bulutta Lean WSL'siz, yerel olarak çalışır (Mathlib
`5ed2965`, REPL `646a773`, elan 4.2.4; `lean/PINS`); bulutta Python 3.14.6 (python-build-standalone;
yerel `.venv` 3.14.7, DECISIONS §42); paket sürümleri `requirements.lock`'ta. `reports/lean_setup.log`
eski `stable` kurulumunun günlüğüdür; sabit kurulumun günlüğü bulutta `/opt/mathverify-logs/setup_lean.log`.

---

## 2. Mimari

### Katmanlar ve veri akışı

```
soru (TR) + çözüm
   │
   ├─ L0 normalize/     Türkçe sayı biçimi, derece/yüzde/unicode, beyaz listeli ifade ayrıştırma
   ├─ L1 ir / extract/  ProblemIR. Elle verilir (yol a) ya da LLM ile çıkarılır (F3):
   │                    çıkarım → deterministik doğrulama → iki aileli round-trip → ≤2 onarım
   ├─ intake/           çözüm: yapısal format (yol a) ya da serbest metin (yol b)
   ├─ verifier ön kontrolleri: şık harfinden yük doldurma + kapsam bayrakları, yük temizleyici,
   │                    "iddia bir değer mi" (_claim_not_a_value), mc.consistency, sanity
   ├─ L3 certify/       13 sertifika modülü, iddiayı sınar                   [sert, primary]
   ├─ L6 steps/         deterministik adım reddedici, yalnız karşı örnekle    [sert, veto]
   ├─ L4 resolve/       çapraz aile yeniden çözüm                             [yumuşak]
   ├─ L5 meta/          metamorfik yöntem testi                               [yumuşak]
   ├─ L6' critic/       çapraz aile kritik + meta-doğrulama                   [yumuşak]
   ├─ L7 formal/        Lean 4 + Mathlib, yalnız pozitif kanıt                [sert, primary]
   └─ L8 fuse/          sert veto + noisy-OR + çekimserlik eşikleri (+ kapalı kalibrasyon)
                        → VerificationResult
```

### Katmanların yetkisi

| Katman | Verdict üretebilir mi |
|---|---|
| `certify.*` (primary) | Evet: pass → CORRECT, fail → INCORRECT |
| `formal.lean` (L7) | Yalnız pass (sertifika ekler, hiçbir kararı ters çeviremez) |
| `steps.refute`, `mc.consistency`, `sanity` | Yalnız veto (INCORRECT) |
| `resolve` (L4), `meta` (L5) | Hayır |
| `critic` (L6') | Hayır; yalnız CORRECT'i engelleyebilir |

Kural: bir LLM katmanı kararı yalnız **daha temkinli** yapabilir. `fuse/rules.py` içindeki
`_BLOCK_POSITIVE_FLAGS` bayrakları (ör. `recovered_answer_mismatch`, `malformed_step_claim`,
`claim_is_not_a_value`) CORRECT'i engeller.

### Bileşenler nasıl bağlanıyor

- **Deterministik giriş:** `mathverify.verifier.verify(problem_ir, solution)`. Önce
  `verify_layers()` → `make_ctx()`. Sonra ön kontroller, ardından `router.route(ir)`. Bu çağrı
  `task.kind` değerini `certify.MODULES` içindeki modül adlarına eşler ve her modülün
  `verify(ir, solution, ctx)` fonksiyonu çağrılır. Adımlar varsa `steps.deterministic.check_steps`
  koşar. En son `fuse_layers()` → `fuse.rules.fuse()`.
- **Tam otomatik giriş (LLM):** `mathverify.pipeline.run_pipeline(question_tr, …)`. IR yoksa
  `extract.extract_ir` ile çıkarır. Serbest metni `extract.restructure_llm` ile yapılandırır.
  Deterministik katmanlara L4/L5/L6'yı, `use_l7=True` ise L7'yi (`formal.prove.l7_layer`) ekler ve
  hepsini birlikte füzyona verir.
- **Ortak karşılaştırma primitifi:** `equiv/`. Bütün sertifikalar iki değerin eşitliğini buradan
  sorar; bu yüzden buradaki yanlış bir "eşit" her yere sızar (§3, karar 14).
- **Her CAS/z3 çağrısı** `sandbox/pool.py` içindeki kalıcı worker süreçlerde, sert zaman aşımıyla
  koşar (varsayılan 8 s). Ağır işlemler `sandbox/ops.py` içinde tanımlıdır.
- **LLM istemcileri** `llm/__init__.py` üzerinden alınır: `ROLE_FAMILY`, `client_for_role()`,
  `judge_families()`, `set_client_override()`. Her çağrı `llm/cache.py` içindeki kayıt/tekrar
  önbelleğinden geçer (`llm_cache/`, git'te izleniyor).
- **Lean**, WSL içinde kalıcı bir REPL'dir: `formal/lean_client.py` → `lake env <repl>`.
  `formal/statement.py` IR'dan deterministik şablonla teorem üretir. `formal/prove.py` taktik
  merdivenini dener ve ispatı denetler (sorry, aksiyom, vakum, kullanılmayan hipotez).
  **Düzeltme (24 Eylül 2026):** WSL yalnız Windows'ta; Linux'ta aynı satır yerel `bash -lc` ile
  koşar, REPL kendi süreç grubunda açılır ve `killpg` ile kapatılır (DECISIONS §40).

### Klasör yapısı (önemli kısımlar)

```
src/mathverify/   63 modül, ~11 650 satır
  normalize/      parse.py (beyaz liste ayrıştırıcı, değer-yalnız ad alanı), turkish.py
  equiv/          __init__ (eşdeğerlik girişi, exact_integer), numeric, random_point, sets, symbolic
  sandbox/        pool.py (süreç havuzu, zaman aşımı, bellek sınırı), ops.py
  certify/        base.py (Ctx) + 13 modül + _z3bridge.py
  steps/          deterministic.py (reddedici)
  fuse/           rules.py
  intake/         structured.py (yol a), restructure.py (yol b, deterministik çıkarıcı)
  extract/        ir_extract, prompts, restructure_llm, roundtrip (F3)
  llm/            base (hata sınıfları), anthropic_client, meta_client, cache, schemas
  resolve/ meta/ critic/   L4 / L5 / L6'
  formal/         statement.py, prove.py, lean_client.py (L7)
  ir.py solution.py types.py router.py verifier.py pipeline.py versions.py
tests/            30 test dosyası + conftest.py + conftest_llm.py (ScriptedClient), 439 test
evalset/build/    17 modül: build_all.py, common.py ve 15 konu üreticisi
evalset/items/    280 JSON öğe (üretilmiş, commit'li)
harness/          run_eval, run_lean, adversarial, soundness_fuzz, calibrate, run_f3, metrics, loader
scripts/          check.py (kapı koşucusu), verify_cli.py, Lean kurulum betikleri, smoke/probe betikleri
docs/             ARCHITECTURE, QUALITY, SOLVER_FORMAT, LLM_LAYERS, LEAN_SETUP, E1-E10-measurement
reports/          üretilmiş .md raporlar (commit'li); *.json raporlar git-ignore'lu
```

**Düzeltme (24 Eylül 2026):** `tests/` artık 32 test dosyası (`test_lean_client_posix.py`,
`test_check_gates_harness.py` eklendi); 24 Eylül sonunda 36 test dosyası, 838 test (`test_cloud_scripts.py`, `test_llm_base_url.py`,
`test_prove_audit_timeout.py`, `test_lean_elaboration.py` de eklendi). Yeni klasörler ve dosyalar:

```
lean/             sabitlenmiş Lean projesi dosyaları + PINS (§0.5)
scripts/cloud/    setup_env.sh (bulut ortam kurulum betiği), session_start.sh (oturum kancası)
scripts/          + fetch_artifacts.sh (araç ref'ini çeker ve doğrular)
docs/             + BULUT.md (bulut el kitabı); docs/sartname/ (özgün şartname)
reports/arsiv/    git-ignore'lu rapor JSON'larının 2026-09-24 anlık görüntüsü
requirements.lock sabit paket sürümleri
.claude/          settings.json (SessionStart kancası)
.env              API anahtarları, izleniyor (§0.3)
```

### Değerlendirme seti

280 öğe. Hücre oranları A/B/C/D = %30/%25/%30/%15:

| Hücre | Anlamı |
|---|---|
| A | Kanonik doğru çözüm |
| B | Doğru ama kanonik olmayan çözüm |
| C | Yanlış cevap (adlandırılmış mutasyonla üretilir) |
| D | Doğru cevap ama bozuk adım |

Tamamen sentetiktir, ÖSYM metni içermez. Cevap düzeyi metrikleri A+B+C üzerinden, çözüm düzeyi
metrikleri A+B+C+D üzerinden ayrı raporlanır.

---

## 3. Alınan kararlar ve gerekçeleri

Ayrıntılı kayıt `DECISIONS.md` içinde (bölüm sırası 1, 2, 3, 6, 4, 5; madde numaraları 1–30).
Burada her kararın **neden** alındığı ve **hangi alternatifin neden reddedildiği** özetleniyor.

### Kilitli ürün kararları (şartname §2, yeniden sorulmaz)

- **D1:** Hem uygulamanın kendi çözücüsü hem dış çözüm desteklenir.
- **D2:** Doğrulayıcı cevap anahtarını görmez.
- **D3:** Süre sınırı yok. Erken çıkış yalnız kesin kararda yapılır; 8 s zaman aşımı yalnız askıda
  kalmaya karşıdır, hız için değil.
- **D4:** Her şey API üzerinden çalışır, yerel GPU yok.
- **D5:** TYT + AYT + üniversite, ispat dahil. İspat türü ertelendi: `UNKNOWN` + `unsupported_task_kind`.
- **D6:** Yanlış onay, yanlış redden daha kötüdür. CORRECT ve INCORRECT için füzyon eşiği ≥ 0.90.

### Mimari ve doğrulama kararları

1. **Cevap anahtarı yalıtımı yapısaldır** (şemada alan yok + özyinelemeli tarama).
   *Reddedilen:* anahtarı "karşılaştırma için" hatta tutmak. Doğrulayıcıyı anahtar
   eşleştiricisine çevirirdi. *Sızma testi:* her öğe doğru ve kasıtlı yanlış anahtarla iki kez
   koşar; verdict ve güven birebir aynı olmalı. Mutasyon öğenin kendisine, harness
   ayrıştırmasından **önce** uygulanır (§4'e bakın: eski test yerel bir değişkeni değiştiriyordu).

2. **Adım reddedici yalnız somut karşı örnekle çürütür** (DECISIONS §3.3). Doğrulanamayan adım
   cezalandırılmaz. *Neden:* literatür [10], LLM adım doğrulayıcılarının kanonik olmayan doğru
   adımlarda %75–85 yanlış red verdiğini ölçüyor. Bu projede aynı dönüşümlerde ölçülen yanlış
   red 0/184. *Reddedilen:* LLM'i adım yargıcı yapmak ya da "kanıtlanamayanı şüpheli say" kuralı.

3. **Çözücünün kendi sembolüyle yazdığı adım atlanır** (DECISIONS §3.3, 23 Eylül'de
   kesinleştirildi). Örnek: `t² = 4t − 3`, `u = u² − 6`. *Neden:* bir özdeşlik mi, çözülmekte olan
   bir denklem mi olduğu belirsiz. *Reddedilen:* bunları özdeşlik sayıp sınamak; çözülen her
   denklemi "çürütür" ve geçerli çözümleri cezalandırırdı. *Bedel:* bozulmuş adım taramasında
   kaçan 6 adımın 5'i bu sınıftan.

4. **Bozuk adım iddiası atlanmaz, çekimser kalınır** (DECISIONS §25). `u = sqrt(x+4)` iyi biçimli
   matematiktir: `UndeclaredSymbolError`, cezasız atlanır. `a = 20}` matematik değildir:
   `malformed_step_claim` bayrağı CORRECT'i engeller. Ayrım ayrıştırmayla yapılır: bilinmeyen adlar
   `Symbol` (çağrılıyorsa `Function`) kabul edilip metin yeniden ayrıştırılır. *Reddedilen:* her
   ayrıştırılamayanı atlamak. Reddedilmiş bir adıma `}` eklemek INCORRECT'i CORRECT'e çeviriyordu
   (54 saldırı/öğe çifti).

5. **LLM sinyali sert sertifikayı ters çeviremez**, yalnız CORRECT'i engelleyebilir.
   *Reddedilen:* katman çıktılarının ortalaması. Füzyon sert veto + noisy-OR biçimindedir
   (DECISIONS §3.4); yalnız `primary=True` sertifikalar CORRECT'i temellendirir.

6. **İki model ailesi ve zorunlu rol ayrımı** (DECISIONS §17). Bir çözümü üreten aile o çözümü
   yargılayamaz. L4, kritik ve Lean ispatı çözücünün karşıt ailesinden; meta-doğrulayıcı kritiğin
   karşıt ailesinden gelir. `run_f3 --solver-family` verilmezse her kayda
   `solver_family_unknown` bayrağı konur. *Reddedilen:* tek aile. Aynı model kendi hatasını
   görmüyor ([6]).

7. **IR çıkarımı kabul edilmeden kullanılmaz** (DECISIONS §19). Sıra: şema ve ayrıştırma
   doğrulaması → iki aileli round-trip (ikisi de ≥ 9/10) → en fazla 2 onarım turu. Kabul
   edilmezse `UNKNOWN` döner. *Reddedilen:* "en iyi tahmin" IR'ı ile devam etmek.

8. **Lean ifadesi modele yazdırılmaz, IR'dan şablonla üretilir** (DECISIONS §20). *Neden:* [5]'e
   göre otomatik formalizasyonda ifadelerin %89,5'i derleniyor ama yalnız %60,5'i sadık. Yazıcı
   çeviremediği bir şeyi tahmin etmez, `LeanPrintError` fırlatır ve L7 çalışmaz. Modelin tek işi
   ispattır; ispat da `sorry`, aksiyom, vakum ve kullanılmayan hipotez denetimlerinden geçmeden
   kabul edilmez. Tautoloji olan ifadeler `is_trivial` ile reddedilir.

9. **Üreten hesap ile kontrol eden hesap ayrıdır.** SymPy bir ilkel fonksiyon ya da tanık nokta
   *önerebilir*; öneri teoremin ifadesine asla girmez, yalnız taktiğe girer. Yanlış bir öneri
   ispatı düşürür, sertifika üretemez. Türev ispatı ifade ağacından terim terim derlenir
   (`_hasderiv_proof`) ve türevin değerini Lean kendisi çıkarır.

10. **Türev, ilkel ve integral `HasDerivAt` üzerinden kurulur.** *Reddedilen:* `deriv f a = v`.
    Fonksiyon türevlenebilir değilken de doğru çıkar ve yanlış gerekçeyle sertifika üretirdi.

11. **Sayma teoremleri Lean'in kendi tanımlarıyla kurulur**: `Fintype.card (Equiv.Perm (Fin n))`,
    `powersetCard`, `Fin k ↪ Fin n`. *Reddedilen:* `Nat.factorial 5 = 120`. Bu yalnız bizim formül
    seçimimizi onaylar, sayılan nesneyi doğrulamaz.

12. **Lean'in junk değerleri sertifika üretemez** (DECISIONS §26). Mathlib'de `x/0 = 0`,
    `Real.sqrt` negatifte 0, `Real.log 0 = 0`, `Real.tan (π/2) = 0` ve integrallenemeyen fonksiyonun
    integrali 0'dır. Kural `formal/statement.py` içindeki "junk values" bölümünde:
    - Kapalı (değişkensiz) kısmi işlemi yazıcı karara bağlar (`_check_closed_definedness`).
      Tanımsızsa ya da karar verilemezse ifade üretilmez.
    - Açık kısmi işlemleri şablon ele alır. Seçenekler: `evaluate`'te koruma hipotezi
      (`open_guards`), bölgenin tamamında tanımlılık kanıtı (`defined_on`), noktada türevde iç nokta
      (`interior_defined_at`), fonksiyonel türevde boş olmayan tanım kümesi
      (`has_interior_point`), ya da ret.
    - Tanımlılık `certify.domain.definedness_conditions`'tan gelir, yani deterministik katmanla
      aynı tanım kullanılır.

    *Reddedilen:* junk değerleri yalnız denetimlere bırakmak. Aksiyom ve vakum denetimleri bunu
    göremez, çünkü ispatlar junk ifadelerin gerçek ispatlarıdır.

13. **İddia bir değerdir, hesaplama değil** (DECISIONS §28). İddia, `normalize.parse.COMPUTING_OPERATORS`
    (integrate, limit, diff, Sum, simplify, nsimplify, det, dist, …) ve problemin kendi
    fonksiyonları çıkarılmış bir ad alanında okunur (`claim_namespace`, `check_claim_is_value`,
    `Ctx.claim_ns`). `evaluate` görevinde hedefi aynen yazan iddia da cevap sayılmaz
    (`verifier._same_structure`). Karar **çekimserliktir** (`claim_is_not_a_value`), ret değil:
    ortada yanlış bir cevap değil, hiç cevap yok. Kapalı biçimler (`binomial(6, 3)`) geçerlidir.

14. **Sayısal "eşit" kanıt değildir** (DECISIONS §27). Kurallar:
    - Kesin kesirler kesin karşılaştırılır.
    - Tolerans verilmemişse eşitlik hassasiyet merdiveninin (30/50/80 basamak) **her**
      basamağında sağlanmalıdır.
    - Sembolik sıfır testi (`sandbox.ops.zero_test_battery`) yalnız kesin dönüşümlerden oluşur;
      `nsimplify` bir yuvarlamadır.
    - Rastgele noktalarda iki taraf ayrı ayrı değerlendirilip çıkarılmaz; farkın kendisi
      uyarlamalı `evalf` ile değerlendirilir (`equiv.random_point._definite_nonzero_difference`).
    - Math-Verify yalnız ikinci görüştür; tek başına karar verdiği dal kaldırıldı.

    *Neden:* sembolik eşitlik yanlış negatif verebilir ama yanlış pozitif vermez; nümerik
    eşitlikte durum tersidir (TinyV).

15. **İddia karşılaştırılmadan önce yeniden yazılmaz** (DECISIONS §29). Sayılar
    `equiv.exact_integer` ile okunur: tam sayı değilse yanlış bir sayımdır, yuvarlanmaz.
    Hiçbir iddia ya da hesaplanan doğru değer `nsimplify`'dan geçmez. *Reddedilen:* `int()` ve
    "güzel sayıya yakalama".

16. **Kararın kapsamı çıktıya yazılır** (DECISIONS §24). Denetlenebilir adım yoksa verdict korunur
    ama `answer_level_only`, `steps_not_checked` ya da `answer_from_option_letter` bayrağı konur ve
    karar izine `KAPSAM:` satırı eklenir. *Reddedilen:* çekimser kalmak. Yol (b)'nin cevap düzeyi
    kapsamasını yok ederdi.

17. **Yol (b)'de yük kurtarma yalnız küme/aralık literalleri içindir**
    (`payload_source="recovered_text"`). Tavsiye niteliğindedir: şıkla çelişirse
    `recovered_answer_mismatch` ile çekimser kalınır, asla reddedilmez. *Reddedilen:* her
    `<sym> = <token>` biçimini kurtarmak (ölçüm §4'te).

18. **Temizleyici matematiği asla atmaz** (DECISIONS §21). Ayrıştırılamayan yükte yalnız düz yazı
    parçaları atılır. *Reddedilen:* sondaki parçaları kırpmak; `12 + 1` ifadesini `12`ye
    indiriyordu.

19. **Faturalama hatası bir ölçüm değildir** (DECISIONS §23). `LLMCreditError` ve `LLMAuthError`,
    `LLMFatalError` altındadır ve bilerek `LLMError`'ın alt sınıfı **değildir**. Harness yapısal
    `fatal` alanıyla ilk hatada durur. *Reddedilen:* hata metninde "credit" dizgisini aramak
    (§4'e bakın).

20. **Kalibrasyon ölçüldü ve varsayılan olarak kapalı** (DECISIONS §22). Kalibre model kapsamadan
    13 öğe götürdü (1.000 → 0.950) ve tek FP'yi kaldırmadı. Açmak için
    `MATHVERIFY_CALIBRATION=on`; `reports/calibration.json` yoksa `CalibrationUnavailable`
    fırlatılır. Altyapı yumuşak LLM sinyalleri için duruyor.

21. **`tyt-prob-018` açık bırakıldı.** Doğru ama gerekçesiz bir adımı deterministik reddedici
    çürütemez. L6 çapraz kontrolü, sertifikayla doğrulanmış bir adım hakkındaki kritik raporunu
    iptal ediyor. *Reddedilen:* kuralı daraltmak; gerekçesiz bir LLM suçlamasının sertifikayı
    ezmesine kapı açar. Karar F4 ölçümüne bırakıldı. Bugünkü davranış
    `test_a_true_but_unjustified_step_is_still_overruled_by_its_certificate` ile teste bağlı.

22. **Bilerek kapsam dışı (Lean):**
    - Olasılık olay yüklemleri: `Fin 6` ile bir birim kayması teoremi sessizce değiştirir.
    - Limitler: her biçim ayrı bir Mathlib kalıbı ister ve yarısı "limit yoktur"un
      olumsuzlamasını gerektirir.
    - Sentetik geometri.
    - Parçalı ve has olmayan integraller.
    - (`domain_of`, `simplify_expression`, `count_solutions` 23 Eylül'de kapsama alındı, karar 31.)

23. **Sandbox süreç izolasyonudur, güvenlik sandbox'ı değildir** (DECISIONS §3.5). Model kod
    çalıştırmadığı için yeterli. Model kodu gelirse gVisor/Firecracker şart. Bellek sınırı
    Windows'ta Job Object ile uygulanır ve Windows'ta **atlanamayan bir teste** bağlıdır
    (23 Eylül'e kadar hiç uygulanmıyordu, §6.4).

24. **Determinizm:**
    - Worker'larda `PYTHONHASHSEED=0` (`is_subset` hash tohumuna bağlı değişiyordu).
    - Rastgele noktalarda sabit tohum ve kesin rasyonel örnekleme.
    - LLM için kayıt/tekrar önbelleği (`MATHVERIFY_LLM_CACHE=replay` ağa hiç çıkmaz).
    - Sürümler her sonuca yazılır.

25. **Nümerik integral yalnız tanh-sinh ile yapılır**; tolerans hata kestiriminden türetilir.
    *Reddedilen:* Gauss–Legendre (`∫₀¹ ln x/√x` üzerinde dps 80'de mutlak hata 2.0e-2, göreli
    5e-3; 23 Eylül'de yeniden ölçüldü, eski belgelerdeki "5e-3 hata" göreli hatadır) ve sabit
    1e-12 tolerans.

26. **Doğrulayıcının kendisi metamorfik ve diferansiyel olarak test edilir** (DECISIONS §30,
    `harness/soundness_fuzz.py`). Değerlendirme seti bir sabittir; bu tarama problemin
    üretebileceği cevaplar üzerinde ölçer. Dört sayının sıfır olması `check.py --full` kapısıdır.

27. **Router'da tanımlı her görev türünün sette öğesi olması bir kapıdır.** 20 Eylül'de üç türün
    hiç öğesi yoktu; `evalset/build/tyt_kapsam.py` ile 20 öğe eklendi ve oranlar korundu.

28. **Adversaryal tarama üç yüzeyi ayrı ölçer** (cevap yükü, şık harfi korunarak, adım
    iddiaları) ve üçünün de var olması bir kapıdır. *Neden:* eski tarama tek yüzeydeydi ve her
    saldırıda şık harfini siliyordu, ama çözümlerin çoğu harf taşıyor. Tek yüzeyde %0 başarı,
    ölçülenin dar olduğunu gizler.

29. **`.gitignore` içinde `/build/` ve `/dist/` köke ankrajlı.** *Neden:* ankrajsız `build/`,
    `evalset/build/` klasörünü de yok sayıyordu ve set üreticileri hiç commit edilmemişti.

30. **Tanımlılık, ifadenin yazıldığı biçimden okunur** (DECISIONS §31, 23 Eylül). SymPy'nin
    otomatik sadeleştirmesi (`x/x` → 1) tanımsız noktayı daha koşul okunmadan siliyordu. Yanlış
    cevap alıp CORRECT (0.99–0.995) veren ölçülmüş vakalar: `domain_of` (5 ifade), `solve_equation`
    (2), `solve_inequality`, `evaluate`, türev, ekstremum, seri. İlk dördünde doğru cevaplar da
    INCORRECT alıyordu. Değer için normal ayrıştırma, tanımlılık için yazıldığı biçim
    (`parse_as_written`) kullanılır. *Reddedilen:* ayrıştırmayı tümüyle sadeleştirmesiz yapmak;
    çözücüler kanonik biçim bekliyor. `limit` bilerek dışarıda.

31. **Üç yeni Lean şablonu** (DECISIONS §32): `domain_of` (yalnız koşullar, fonksiyon yok),
    `simplify_expression` (korumalar ifadeden, iddianın tanımlılığı hedefte), `count_solutions`
    (kutunun yeterliliği de kanıtlanır; ℤ bölmesi ve `Mod` reddedilir). Her korumanın naif biçimi
    Lean'de gerçekten ispatlanıyor; bu teste bağlı. *Reddedilen:* bu türleri kapsam dışı bırakmak.
    Lean katmanı yalnız pozitif kanıttır; ölçülen FP 0, junk 0/17.

32. **pyflakes kapısı** (DECISIONS §33). Nadiren çalışan `except` dallarındaki tanımsız adlar
    için. Bulgu yalnız kendi satırındaki `# noqa` ile muaf; pyflakes çalışmazsa kapı geçmez.

---

## 4. Denenen ve işe yaramayanlar

Bunlar **tekrar denenmemeli.** Her birinin neden başarısız olduğu yanında yazıyor.

> Aşağıdaki "önce" ölçümleri hataların bulunduğu anki koşulardan geliyor. Çoğu `DECISIONS.md` ve
> `docs/ARCHITECTURE.md` içinde kayıtlı; üçü başka yerde: 94/59 kurtarma ölçümü
> `src/mathverify/intake/restructure.py` yorumunda, Gauss–Legendre `docs/E1-E10-measurement.md`
> içinde, 8/3 kâhin hatası `harness/soundness_fuzz.py` yorumunda.
>
> 23 Eylül'de kütüphane ya da matematik gerçeği olanlar kod geri alınmadan yeniden üretildi ve
> tuttu: `int(7/2) = 3`; `nsimplify` 500000003/3000000000'ı 1/6'ya, −e⁻¹⁰⁰⁰'ü 0'a götürüyor;
> 10³⁰+1 ile 10³⁰'un göreli farkı 1e-30; e^{π√163} 30 basamakta tam sayıya eşit, 50 ve 80'de
> değil; 8/3'ün 30 basamaklı ondalığı 8/3 değil; F3'te 151 kayıt aynı faturalama hatasıyla düşmüş
> ve kırpılmış metin `'message': 'Your` ile bitiyor. "Yerine" sütunundaki mekanizmalar kodda
> duruyor. Kodu geri almadan üretilemeyenler (7/7 iddia, 54 çift, `Bilmiyorum` 0.990, 13 öğe,
> junk 0.995, 245/260, `}` saldırısı) yalnız kayıttan geliyor **[DOĞRULANMADI]**.

### Doğrulama mantığı

| Denenen | Neden başarısız oldu | Yerine |
|---|---|---|
| Sayma iddiasını `int()` ile okumak | `7/2` → 3 → sayısı 3 olan soruda CORRECT | `equiv.exact_integer` |
| İddiayı/doğruyu `nsimplify` ile "güzelleştirmek" | `500000003/3000000000` → 1/6; `−e⁻¹⁰⁰⁰` → 0 | Kesin dönüşümler; `nsimplify` yok |
| Kesin sayıları göreli toleransla karşılaştırmak | `10³⁰+1 == 10³⁰` çıkıyordu | Kesin rasyonel karşılaştırma |
| Nümerik eşitliği tek hassasiyet basamağında kabul etmek | `e^{π√163}` 30 basamakta tam sayıya "eşit" | Her basamakta eşitlik |
| Rastgele noktada iki tarafı ayrı değerlendirip çıkarmak | Çalışma hassasiyetinin altındaki farkı görmüyor | Farkın kendisini uyarlamalı `evalf` ile değerlendirmek |
| Math-Verify'ın tek başına karar vermesi | Belge "ikinci görüş" diyordu, kod karar veriyordu | Yalnız nota yazılıyor |
| İddiayı tam ad alanında okumak | `integrate(log(x), x)`, `f(g(2))`, `gcd(84,120)`: 7 iddianın 7'si CORRECT | Değer-yalnız ad alanı |
| Kayan noktalı örnekleme ile adım çürütmek | Doğru özdeşlikleri "çürütüyordu" | Kesin rasyonel örnekleme |
| `evaluate=True` ile ilişki kurmak | Pozitif sembolde `x > 0` True'ya katlanıyordu | `evaluate=False` ilişkiler + z3'te yan kısıt |
| Her ayrıştırılamayan adımı cezasız atlamak | `}` eklemek reddi iptal ediyordu | `malformed_step_claim` ayrımı |
| Yol (b)'de her `<sym> = <token>` biçimini kurtarmak | 94 kurtarmanın 59'u çözücünün iddiası değildi | Yalnız küme/aralık literalleri: 5/5 doğru |
| Yük temizleyicinin sondaki matematiği atması | `12 + 1` → `12` | Yalnız düz yazı jetonları |
| Yalnız şık harfi veren çözümü sessizce CORRECT saymak | `"Bilmiyorum ama tahminim. Cevap: B"` → CORRECT 0.990, bayraksız | Kapsam bayrakları |
| Kalibrasyonu varsayılan olarak açmak | Kapsamadan 13 öğe götürdü, FP'yi kaldırmadı | Kapalı |
| F4 kritiğinin `tyt-prob-018`'i kapatacağını varsaymak | Çapraz kontrol, sertifikalı adımdaki raporu iptal ediyor | Açık bırakıldı |
| Tanımlılığı SymPy'nin sadeleştirdiği ifadeden okumak | `x/x` → 1: "tanım kümesi ℝ", "`x²/x = 0`'ın kökü 0", "x = 0'da `x/x` = 1" dahil 11 vaka CORRECT alıyordu (23 Eylül) | `parse_as_written` + `Ctx.written_conditions` (karar 30) |

### Lean

| Denenen | Neden başarısız oldu |
|---|---|
| `first \| a \| b` alternatiflerini `done` olmadan yazmak | `first` ilk *çalışan* alternatifi seçer; `norm_num at *` ya da `simp` hedefi kapatmadan çalışınca arkadaki doğru alternatif gölgelenir. İspat merdivenlerinde F5'te düzeltilmişti; **vakum sondası 23 Eylül'e kadar eski biçimde kaldı** ve çelişkili hipotezleri kaçırıyordu. |
| Junk değerleri yalnız denetime bırakmak | "tan(π/2) = 0", "√(2−5) = 0", "0/0 = 0", "log 0 = 0" temiz sertifika aldı; ilki `--lean` ile bütün doğrulayıcıdan CORRECT 0.995 çıktı |
| `LEAN_PATH=... exec repl` | `exec` özel bir yerleşik; değişken çocuğa geçmiyor ve Mathlib görünmüyor. Çözüm `lake env <repl>` ve açılışta Mathlib sondası. |
| Bağlamsız matris literali `!![1, 1; 2, 4]` | ℕ olarak elaborate ediliyor (`failed to synthesize CommRing ℕ`); her literale tip ataması yapılmalı |
| `*ᵥ` gösterimi, `Matrix.dotProduct` | Elaborate olmuyor; `Matrix.mulVec` ve kökteki `dotProduct` kullanılmalı |
| Standart trig değerleri için `rw [...]` listesi | Bir lemma ateşlemezse düşüyor; `simp only [...]` kullanılmalı |
| `hasDerivAt_id` | `id ^ 2 * Real.exp` biçimi üretiyor ve eşleşmiyor; `hasDerivAt_id'` kullanılmalı |
| Türevin değerini elle yazmak | SymPy `0^2`'yi sadeleştirip eşleşmeyi bozuyordu; değeri Lean çıkarsın |
| Yan koşulları satır içi `by` bloğunda bırakmak | Ertelenen hedef dışarı sızıyordu; ayrı `have hs0 : (...) ≠ 0 := by ...` satırı gerekiyor |
| CAS'ın hedefi önceden hesaplaması | `gcd(84,120)+lcm(4,6)` → `24 = 24` tautolojisi; artık yapısal ayrıştırma + `is_trivial` |
| Korumalı iff ile çözüm kümesi ifadesi | Kök tanım kümesi dışındaysa iki taraf da yanlış ve iff doğru çıkıyordu; artık her kökün koşulları ve denklemi sağladığı da iddia ediliyor. Aynı açık eşitsizlik uç noktalarında da vardı. |
| Sadeleştirme ifadesinde iddianın tanımlılığını hedefe koymamak | `∀ x, x = x²/x` Lean'de ispatlanıyor (0/0 = 0); iddia tanım kümesini daraltabilirdi (23 Eylül ölçümü) |
| Korumalı `∀`'yı iç nokta kontrolü olmadan kurmak | `∀ x, −x²−1 ≥ 0 → √(−x²−1) = 0` boş yere ispatlanıyor |
| Sayımda ℤ bölmesini yazdırmak | `#{(x,y) ∈ [0,2]² : x/y = 0} = 6` Lean'de doğru (taban bölmesi, x/0 = 0), gerçekte 2 |
| `field_simp`'in paydayı korumadaki biçimde bulacağını varsaymak | Yazıcı paydayı `as_numer_denom()` ile `1 + x` basıyor, koruma `x + 1`; `field_simp` sadeleştiremedi. Her payda için `linear_combination` ile türetilen `have` gerekiyor. |

### Ölçüm ve harness

| Denenen | Neden başarısız oldu |
|---|---|
| Faturalama durdurucusunun `ir_reason` içinde "credit" araması | `str(e)[:120]` kelimeyi bir karakter önce kesiyordu; `except LLMError` sınıfı yutuyordu. 18 Eylül'de 151 öğe boşa gitti ve tarama durmadı. `828fb95`'teki dizgi durdurucusu o koşunun kendi kayıtlarında 0/218 ateşliyor. (Eski belgelerdeki "`aborted: None`" ifadesi dosyayla desteklenmiyor: o koşunun JSON'unda `aborted` anahtarı hiç yok; DECISIONS §23 "Düzeltme (23 Eylül)".) |
| 24 karakterlik sahte hata mesajıyla test | Kırpma sınırının altında kaldığı için hatayı hiç göremedi; test artık sağlayıcının gerçek mesajını kullanıyor |
| Sızma testinde mutasyonu yerel bir değişkene uygulamak | Aynı argümanlarla iki koşu yalnız determinizmi kanıtlar, yalıtımı değil |
| Adversaryal taramanın tek yüzeyde koşması | %0 başarı gösteriyordu ama adım yüzeyindeki açığı (INCORRECT → CORRECT) göremiyordu |
| "Yol (b) sadakati 1.000" tek sayısı | 260 öğenin 245'i yalnız şık harfiyle eşleşiyordu; sayı neredeyse boştu |
| `soundness_fuzz`'ta her kesrin 30 basamaklı ondalığını "eşdeğer" saymak | `8/3` ve `1/6`'nın 30 basamaklı ondalığı gerçekten eşit değil; kâhin hatasıydı. Artık yalnız sonlu ondalıklar üretiliyor (`sp.Float(decimal_str, 30)`). |
| Kaçırılan bozuk adımlar için rapora sabit bir açıklama cümlesi yazmak | Cümle ölçülmüyordu ("`t`, `u`" diyordu, gerçek semboller n, a, t, u, t); kaçan küme değişse de aynı kalırdı. Artık neden adım katmanının kanıtından okunuyor ve açıklanmayan kaçırma bir kapı (23 Eylül). |
| Atlanabilen bellek testi | `test_memory_cap_is_enforced_best_effort` bellek sınırı yokken sessizce atlanıyordu; Faz 1'den 23 Eylül'e kadar hiçbir worker'da sınır yoktu ve kimse fark etmedi. Windows'ta artık atlanamaz. |

### Kapatılmış diğer hatalar (yeniden açılmasın)

- `from mathverify.certify import *` → `ModuleNotFoundError`: `__all__`, router kayıt anahtarlarını
  öznitelik adı sanıyordu.
- `intake.restructure_llm` F3'ten sonra da "ertelendi" diye hata fırlatan ölü koddu.
- Formal katman CLI'dan erişilemiyordu; `verify_cli.py --lean` eklendi.
- F4 bir kez bile koşamazdı: harness kritiği pipeline'a geçirmiyordu. `--no-l6`, kayıt ve rapor
  bölümü eklendi.
- `render_ir` içinde `simplify_expression` ve `count_solutions` şablonları yoktu; round-trip
  yargıcına ham JSON gidiyordu.
- `pipeline` ve `verify_cli`, deterministik geri-düşmeyi `answer_shape` vermeden çağırıyordu
  (DECISIONS §16, "Düzeltme").
- Küme cevaplarında `{` öneki doğru cevabı reddettiriyordu (CORRECT → INCORRECT).
- `Interval.open(...)` Faz 1'den beri kullanılamıyordu; `open(` yasağı onu da yakalıyordu.
- `5π/6` ayrıştırılamıyordu.
- LaTeX dalı beyaz listeyi atlıyordu ve 260 öğenin hiçbiri o dalı tetiklemiyordu. Artık
  `tyt-kap-011` LaTeX iddia taşıyor ve `latex_form` bir saldırı türü.
- `anthropic` ve `python-dotenv` beyan edilmemişti. `MATHVERIFY_CALIBRATION=on` ile kalibrasyon
  dosyası yoksa sessizce hiçbir şey yapmıyordu.
- `solver_family` hiçbir çağırandan verilmiyordu ve `ROLE_FAMILY` hiçbir yerde okunmuyordu.

### Ortam

| Denenen | Neden başarısız oldu |
|---|---|
| Uygulamanın MSIX sanallaştırılmış scratch dizininde pip/uv/venv | Çalışmıyor; proje bu yüzden `C:\Users\kullanici\mathverify` altında |
| Heredoc içinden ters eğik çizgili Python yazmak | `\\boxed` → `\b` gibi çöküşler yanıltıcı sonuç verdi; Write aracıyla gerçek dosya yazılmalı |
| `<stdin>` ya da `-c` ile sandbox kullanan probe | Windows multiprocessing spawn kırılıyor; gerçek dosya ve `if __name__ == "__main__":` gerekli |
| Git kimliği ayarlanmadan commit | `Author identity unknown`; komut başına `git -c user.name=… -c user.email=…` kullanıldı |
| Math-Verify'ı kendi zaman aşımıyla çağırmak | Windows'ta her çağrıda süreç açıyordu; sandbox içinden `timeout_seconds=None` ile çağrılıyor |
| `lambdify` ile karmaşık sabit değerlendirmek | 15 basamağa düşüyordu; yerine `sp.N(expr, dps)` + `as_real_imag` |

---

## 5. Mevcut durum

### 5.1 Tamamlanan ve çalışan

| Faz | Durum |
|---|---|
| F0: §6 sözleşmeleri (E1–E10), IR, sandbox, değerlendirme seti, iki intake yolu | tamam |
| F1-TYT / F1-AYT sertifikaları | tamam |
| F2: sentetik geometri (nümerik realizasyon), kombinatorik/olasılık, seriler, lineer cebir | tamam |
| F3: LLM ön yüzü, L4, L5 | kod tamam; **ölçüm yarım** (218 öğenin 64'ü, sonra kredi bitti) |
| F4: kritik + meta-doğrulama | kod tamam, çevrimdışı testli; **hiç koşmadı** |
| F5: Lean 4 + Mathlib | tamam ve ölçüldü (modelsiz yol) |
| F6: adversaryal sertleştirme + kalibrasyon | tamam ve ölçüldü |
| F7: integral/türev/ilkel/sayma/tekrarlama Lean şablonları | tamam (107 sertifika) |
| 20 Eylül denetimi: 11 boşluk | kapatıldı (DECISIONS §23–25) |
| 23 Eylül denetimi: 4 yanlış-onay sınıfı | kapatıldı (DECISIONS §26–30, `docs/QUALITY.md`) |
| 23 Eylül ikinci oturum: [DOĞRULANMADI] kontrolü, bellek sınırı, belge düzeltmeleri, yeni kapı | tamam, `master`a birleştirildi (`e2aa08d`) |
| 23 Eylül, aynı oturumun devamı: tanımlılık açığı (11 yanlış-onay vakası), üç Lean şablonu, pyflakes kapısı, temizlik | tamam, `master`a birleştirildi (§5.3) |
| 24 Eylül: özel GitHub deposu, Linux/bulut desteği, sabit Lean + çevrimdışı kurulum, kapı sertleştirmesi (24 kapı) | tamam, `bulut-2026-09-24` dalında (§0) |
| 24 Eylül akşamı: gerçek bulut ölçümü, Lean kapılarının "cevap verdi" koşulu, denetim sondası (ilke 7), çevrimdışı ve aşamalı kurulum, Python yedeği, `ANTHROPIC_BASE_URL` | ölçüldü ve düzeltildi (§0.5 eki, §0.8); `bulut-2026-09-24` dalında. **Düzeltme:** dalın `4d01ba2` hâli GitHub'daki `master`da (`572ef57`, §0.9) |
| 25 Eylül sistematik denetimi: kod çalıştırma, yanlış onay sınıfları (cebir, kalkülüs, geometri, girdi), formal katman | kapatıldı ve ölçüldü (§0.13, DECISIONS §55); `claude/compassionate-shannon-759r85` dalında |

Son `check.py --full` sonucu (23 Eylül 2026 15:56, `yerel-kalite-2026-09-23` @ `e2aa08d` + §5.3'teki
commit edilmemiş değişiklikler; günlük `reports/check_full.log`; toplam ~67 dk, adversaryal 3490 s):

| Kapı | Değer | Hedef |
|---|---|---|
| Birim testleri | 438 geçti, 1 atlandı (`test_f5_lean.py:66`, beklenen) | hepsi geçer |
| pyflakes (yeni) | 0 bulgu (3 satır `# noqa` ile muaf) | 0 |
| Cevap düzeyi pozitif / negatif precision | 1.000 / 1.000 | ≥ 0.98 |
| Kapsama | 1.000 | ≥ 0.85 |
| B hücresi yanlış red | 0.000 | < 0.10 |
| Anahtar sızma testi | geçti | zorunlu |
| Çözüm düzeyi pozitif precision | 0.994 (1 FP: `tyt-prob-018`) | raporlanır |
| D hücresi tespiti | 0.976 (41/42) | raporlanır |
| Yol (b): cevabın kendisi karşılaştırılan öğe | 20/20 | raporlanır |
| L5 uygulanabilirlik tavanı | 21/280 (D'de 3/42) | raporlanır |
| Ölçülmeyen görev türü | yok | yok |
| Lean FP | 0 | 0 |
| Lean sertifika | 121/280 (172 öğede ifade üretiliyor; 23 Eylül öncesi 107/152) | raporlanır |
| Lean junk-value sertifikası | 0/17 (23 Eylül öncesi 0/12) | 0 |
| Adversaryal saldırı başarısı | %0.000 (21 139 saldırı) | < %2 |
| Saldırı yüzeyleri | cevap, şık, adım | üçü de |
| SymPy üretimli yanlış cevapta yanlış onay | 0/448 | 0 |
| SymPy üretimli eşdeğer cevapta yanlış red | 0/214 | 0 |
| Cevap olmayan iddiada CORRECT | 0/46 | 0 |
| Geçerli adım dönüşümünde yanlış red | 0/184 | 0 |
| Nedeni açıklanmayan kaçırılan bozuk adım (yeni) | 0/6 | 0 |
| Kalibre test precision (poz/neg) | 1.0 / 1.0 | raporlanır |

Kaynaklar: `reports/eval_report.md`, `lean_report.md`, `adversarial_report.md`,
`soundness_report.md`, `calibration_report.md`. Kapı çıktısının tamamı `reports/check_full.log`
içinde (§6.5).

**Düzeltme (24 Eylül 2026):** yukarıdaki tablo 23 Eylül koşusudur ve artık "son" değil. Kapı sayısı
24 oldu ("Lean erişilebilir", DECISIONS §39) ve `check.py` artık her harness'i yeniden koşturup
yalnız o koşunun raporunu okur. 24 Eylül koşusu: **24/24**, birim testleri
776 passed / 62 skipped, süre ~68 dk (4107 s; adversaryal 3563 s) (Windows, `f0e950c`); yerel Linux'ta da 24/24, 836 passed / 2 skipped, ~36 dk (2186 s; adversaryal 1870 s);
günlük `reports/check_full.log`.

**Süre notu:** Koşular gün içinde yavaşladı (adversaryal 1245 → 2249 → 3490 s). İki A/B ölçümü:
(1) bellek sınırı süreyi değiştirmiyor (`run_eval` eski/yeni `pool.py` ile dört kez: hepsi 64 s,
113–114 ms/öğe); (2) tanımlılık kancası (karar 30) değerlendirmeyi ~%12–15 yavaşlatıyor (kancalı
158–161, kancasız 137–144 ms/öğe; raporlar süre dışında birebir aynı). Kalan fark makinenin o anki
durumundan. D3 gereği süre bir kapı değil. Hiçbir sonuç dosyasında `MemoryError` ya da worker
ölümü yok. Önceki koşuya göre değişen tek sayı: anlamı koruyan saldırılarda UNKNOWN'a düşen 2898 →
2896 (`homoglyph`, karşıt karara dönen yine 0) ve kalibrasyon doğrulama kapsaması 0.864 → 0.879.

**Düzeltme (25 Eylül 2026): "Lean FP 0" genel bir güvence değildi.** Tablodaki ve bu belgenin
başka yerlerindeki "Lean FP 0" yalnız değerlendirme setinin cevabı yanlış öğelerinde ölçülmüştü.
25 Eylül denetiminde set dışında yazılan 98 yanlış iddianın 53'ü Lean'de temiz sertifika aldı
(kısıtların düşürülmesi, sadeleştiren ayrıştırma, ℕ'de okunan kapalı hedefler, Mod, zayıf boşluk
sondası; §0.13, DECISIONS §55). Düzeltildi (0/99) ve bu aileler artık junk kapısında kalıcı sonda
(17 → 33). Aynı denetim, deterministik katmanda da set dışı yanlış onay sınıfları ve cevap
metninin kod olarak çalıştığı bir açık buldu. Değerlendirme setindeki precision 1.000'ın o sete
özgü olduğu, genelleme olmadığı bir kez daha görüldü. Son `check.py --full`: §0.13.

### 5.2 Yarım kalan iş

**Kodda yarım kalan bir iş yok.** Son oturumun sırası şöyleydi:

1. 20 Eylül denetimi: "tek eksik API anahtarı mı?" sorusu. Cevap hayırdı; 11 boşluk bulundu ve
   kapatıldı.
2. 23 Eylül: önce literatür tarandı (`docs/QUALITY.md`), sonra doğrulayıcının kendisi test edildi.
   4 yanlış-onay sınıfı bulundu ve kapatıldı.
3. İkisi birlikte `0f14380` olarak commit'lendi (93 dosya, +7235/−320). Kullanıcıya sonuç
   raporu verildi.
4. Bu belge 12 bölümlü yapıya çevrildi, `CLAUDE.md` oluşturuldu ve README'deki eski bölüm
   göndermeleri güncellendi.

O oturumda fark edilip düzeltilmeyen iki şey (bellek sınırı §6.4, kapı günlüğü §6.5) 23 Eylül
ikinci oturumunda kapatıldı. O oturumun sırası:

5. Belgedeki 8 [DOĞRULANMADI] noktası kodla ve ölçümle kontrol edildi. 6'sı doğrulandı ve
   işareti kaldırıldı. Kalanlar: §4'te kod geri alınmadan üretilemeyen "önce" ölçümleri ve
   anahtarların hâlâ geçerli olup olmadığı. İki ifade yanlış çıktı ve "Düzeltme" notuyla
   düzeltildi: `aborted: None` (DECISIONS §23) ve Gauss–Legendre "5e-3 hata", ki göreli hatadır
   (`docs/E1-E10-measurement.md`). README'deki F3 cümlesi de yanlıştı ("64/64", "154 öğe kredi
   hatasıyla"); düzeltildi (§6.6).
6. Bellek sınırı düzeltildi ve atlanamayan teste bağlandı (§6.4).
7. `soundness_fuzz` kaçırma nedenlerini ölçümden yazıyor; yeni kapı (§6.2).
8. `check.py --full` günlüğü kendisi yazıyor (§6.5). 22/22 kapı geçti.
9. Kullanıcı onayıyla: `master`ın yedeği alındı (§5.4), bu iş üç commit olarak işlendi
   (`1098a6b`, `86197e4`, `e2aa08d`) ve `master` fast-forward ile ileri alındı.
10. "Geri kalan lokal işlemler" `yerel-kalite-2026-09-23` dalında yapıldı: ölü kod, betikler,
    zaman aşımı, pyflakes kapısı, üç Lean şablonu. Şablonları yazarken deterministik katmanda
    tanımlılık açığı bulundu (11 yanlış-onay vakası) ve kapatıldı (karar 30).
11. `check.py --full` 23/23 (15:56 koşusu).
12. Kullanıcı onayıyla ("al"): `master`ın (`e2aa08d`) ikinci yedeği alındı (§5.4), iş dört commit
    olarak işlendi ve `master` fast-forward ile ileri alındı.

24 Eylül oturumu (kullanıcı çalışmayı buluta taşımak istedi; ayrıntı §0):

13. Özel GitHub deposu açıldı; bütün dallar, iki yedek etiketi ve `master` push edildi.
14. `bulut-2026-09-24` dalında Lean istemcisi Linux'a taşındı, kapılar sertleştirildi, Lean
    sürümleri sabitlendi, bulut kurulum betiği ve oturum kancası yazıldı, şartname ve rapor
    arşivi depoya alındı, `.env` kullanıcı kararıyla izlenmeye başladı (6 commit, §0.7).
15. İkinci bir düzeltme turu (Lean'in tarama ortasında kaybolması, REPL ikilisi yokken
    `lake env`, bulut betiklerinin sertleştirilmesi) ve belgeler; ardından `check.py --full` ve
    yedekle birlikte `master`a fast-forward (kullanıcı onayı: "dal, doğrula, birleştir").
    **Düzeltme (24 Eylül 2026, akşam):** sıra böyle olmadı. İkinci tur ve belgeler `4d01ba2`'de
    bitti; sonra:
16. Tek seferlik bir bulut routine oturumu `4d01ba2`'yi ölçtü (§0.8) ve istemdeki "kendi dalına push"
    yüzünden `master`ı doğrulama ve yedekten önce `572ef57`'ye ileri aldı (§0.9); yedek sonradan
    alındı.
17. Ölçümde bulunan iki sorun (Python yedeği, `ANTHROPIC_BASE_URL`) ve gözden geçirmede bulunan
    Lean kapısı ve kurulum açıkları düzeltildi (`7993055`…`4002898`, §0.5 eki).
18. Bir ajanın WSL'deki test kurulumları C:'yi doldurdu (§0.10); temizlendi, `.vhdx` sıkıştırması
    kullanıcıda. **Düzeltme (24 Eylül, 16:54):** sıkıştırıldı, `.vhdx` 15.98 GB, C:'de 93.95 GB boş.
19. Beşinci tur (Python sırası, WSL'de Windows sürücüsünün disk denetimi, denetim sondası kapısı) ve bu
    belgeler bu satır yazılırken sürüyordu; son `check.py --full` sonucu §0.6'da.

### 5.3 Commit edilmemiş değişiklikler

**Yok.** 23 Eylül'ün son commit dizisi (`yerel-kalite-2026-09-23`, `master`a fast-forward ile
birleştirildi; hash'ler `git log` ile görülür) şunları taşır. Ölçüm 23/23 kapı, 15:56 koşusu:

| Dosya | Ne |
|---|---|
| `src/mathverify/normalize/parse.py` | `parse_as_written` (karar 30) |
| `src/mathverify/certify/base.py` | `Ctx.written_conditions` → `domain_for`, `var_constraints` (karar 30) |
| `src/mathverify/certify/domain.py` | `written_definedness`, `written_undefined_in` (karar 30) |
| `src/mathverify/certify/calculus.py`, `extremum.py`, `series.py` | yazıldığı haliyle tanımsız noktada çekimserlik (karar 30) |
| `src/mathverify/formal/statement.py` | `domain_of`, `simplify_expression`, `count_solutions` şablonları (karar 31) |
| `harness/run_lean.py` | 5 yeni junk sondası (12 → 17); varsayılan zaman aşımı 45 |
| `src/mathverify/certify/counting.py` | kesin olmayan katsayı reddediliyor (ölü `nsimplify` dalı yerine) |
| `src/mathverify/sandbox/ops.py` | hiç çağrılmayan `nroots_scan` silindi |
| `src/mathverify/steps/deterministic.py`, `scripts/probe_e1_e10.py`, `tests/test_f3_report.py` | kullanılmayan importlar (pyflakes) |
| `scripts/check.py`, `pyproject.toml` | pyflakes kapısı, `pyflakes>=3` `[dev]`'de (karar 32) |
| `scripts/dev/` (6 taşıma + `README.md`), `scripts/diag_sandbox.py` (silindi) | geliştirme betikleri ayrıldı |
| `tests/test_written_definedness.py`, `tests/test_check_gates.py` (yeni), `test_f5_lean.py`, `test_e10_counting_exact.py` | yeni testler |
| `DECISIONS.md` (§31–33), `HANDOFF.md`, `CLAUDE.md` (ilke 12), `README.md`, `docs/ARCHITECTURE.md`, `docs/QUALITY.md` | belgeler |
| `reports/*.md`, `reports/check_full.log` | 23 Eylül 15:56 koşusu |

İleride de commit ve birleştirme yalnız kullanıcı isterse yapılır; birleştirmeden önce `master`ın
yedeği alınır (kullanıcının talebi, §5.4).

**Düzeltme (24 Eylül 2026):** bu bölüm 23 Eylül'ündür. 24 Eylül işi `bulut-2026-09-24` dalında
(§0.5, §0.7). Bu belge yazılırken ikinci turun kod değişiklikleri (`harness/run_lean.py`,
`scripts/check.py`, `src/mathverify/formal/lean_client.py`, `tests/test_check_gates_harness.py`,
`tests/test_f5_lean.py`, `tests/test_lean_client_posix.py`) ve belgeler henüz commit
edilmemişti; güncel durum `git status` ile görülür.

### 5.4 Dal durumu

- `master`: 23 Eylül'de iki kez fast-forward ile ileri alındı, ikisi de kullanıcının isteğiyle:
  önce `denetim-2026-09-20` (→ `e2aa08d`), sonra `yerel-kalite-2026-09-23`. Şu an ikincisiyle aynı.
- `yerel-kalite-2026-09-23`: `master` ile aynı. `denetim-2026-09-20`: `e2aa08d`'de kaldı.
- **Yedekler** (her birleştirmeden hemen önce; kullanıcıya sormadan silinmez):

  | Etiket | `master` | Bundle (`C:\Users\kullanici\mathverify-yedek\`) |
  |---|---|---|
  | `yedek/master-2026-09-23` | `2744677` | `mathverify-master-2744677-2026-09-23.bundle` |
  | `yedek/master-2026-09-23-2` | `e2aa08d` | `mathverify-master-e2aa08d-2026-09-23.bundle` |

  Bundle'lar alındıkları andaki bütün dalları içerir; ikisi de `git bundle verify` ve deneme klonuyla
  doğrulandı. Geri dönüş talimatı aynı klasörde `OKU.txt`.
- Uzak depo yok.

**Düzeltme (24 Eylül 2026):**

- Uzak depo var: `origin` = `https://github.com/wqedwad/asd` (özel). Dallar ve iki yedek etiketi
  (hafif etiketler) push edildi; hash'ler yukarıdakilerle ve yerel ref'lerle aynı (§0.1).
  `bulut-2026-09-24` dalı eklendi; doğrulamadan sonra `master`a fast-forward edilecek.
- **Bundle'lar yalnız yerel makinededir** (`C:\Users\kullanici\mathverify-yedek\`, kullanıcının
  Windows makinesi). Depoda ve GitHub'da yoktur, bulut oturumu onları göremez. Etiketler ise
  GitHub'da da var.
- Yedek yöntemi (her `master` birleştirmesinden hemen önce, yerel checkout'ta):
  1. `git tag yedek/master-YYYY-MM-DD[-N] master` (aynı gün ikinciyse `-2`, `-3`, …);
  2. `git bundle create C:/Users/kullanici/mathverify-yedek/mathverify-master-<kısa-hash>-YYYY-MM-DD.bundle --all`,
     sonra `git bundle verify` ve bir deneme klonu;
  3. etiketi `git push origin <etiket>` ile gönder (buluttan olmaz: bulut yalnız kendi dalını
     push edebilir).
- Geri dönüş: `git reset --hard <etiket>` ya da `git clone --branch master <bundle>`. Etiket ve
  bundle'lar kullanıcıya sormadan silinmez.
- Bulutta birleştirme doğrudan yapılamaz (`master` push edilemez): PR ile ya da yerel checkout'ta,
  yedek de yerelde alınır.

**Düzeltme (24 Eylül 2026, akşam):**

- "Buluttan `master` push edilemez" koşulsuz doğru değil: `master`da başlayan bir bulut oturumunun
  kendi dalı `master`dır. 24 Eylül'de routine oturumu `origin/master`ı `572ef57`'ye ileri aldı
  (§0.9). GitHub'daki `master` artık `572ef57` (`4d01ba2` + tanı raporu).
- Üçüncü yedek, birleştirmeden **sonra** alındı:

  | Etiket | `master` | Bundle (`C:\Users\kullanici\mathverify-yedek\`) |
  |---|---|---|
  | `yedek/master-2026-09-24` | `23d7c6b` (routine push'undan önceki `master`) | `mathverify-master-23d7c6b-2026-09-24.bundle` (`git bundle verify` geçti) |

  Etiket GitHub'a da push edildi. Geri dönüş talimatı yine `OKU.txt`'te.

**Düzeltme (24 Eylül 2026, gece, bulut oturumu):** tablo eksik. GitHub'da (`git ls-remote origin`)
dördüncü bir etiket var: `yedek/master-2026-09-24-2` → `572ef57`; `master` ve `bulut-2026-09-24` ikisi
de `18fd298`. Yani dal `master`a birleştirildi ve etiket, `master` `572ef57`'den ileri alınmadan
önceki yedek olmalı (çıkarım). Buna karşılık gelen bundle'ın `C:\Users\kullanici\mathverify-yedek\`
altında olup olmadığı buluttan görülemez **[DOĞRULANMADI]**.

Commit geçmişi (eskiden yeniye):

| Commit | Ne |
|---|---|
| `7c222fd` | Faz 1: F0 sözleşmeleri, IR, sandbox, değerlendirme seti, iki intake yolu, F1-TYT/AYT |
| `651f2ec` | README'de kesin test sayısı |
| `d5c8ee8` | F2: sentetik geometri, kombinatorik/olasılık, seriler, lineer cebir |
| `828fb95` | F3–F5: LLM ön yüzü, çapraz aile katmanları, kritik, Lean katmanı (+ `llm_cache/`) |
| `b768e09` | F5: formal kapsam iki katına çıktı, iki şablon sadakat hatası düzeltildi |
| `674b34a` | F6: adversaryal sertleştirme, ölçülmüş kalibrasyon, `check.py` |
| `a94860d` `77cc9d9` `a9d264f` | F7: belirli integral, türev/ilkel, sayma/tekrarlama şablonları (107 sertifika) |
| `abc33d0` `3afda33` | Temizlik ve Lean yeniden ölçümü |
| `53ab97b` | 19 Eylül denetimi: beş boşluk, iki yanlış iddia |
| `2744677` | Önceki HANDOFF.md (`master` burada) |
| `0f14380` | 20 ve 23 Eylül denetimleri (`denetim-2026-09-20`, HEAD) |

**Düzeltme (24 Eylül 2026):** tablo `0f14380`'de kalmıştı ("HEAD" artık doğru değil). Sonrası
(`git log --oneline master`):

| Commit | Ne |
|---|---|
| `1098a6b` `86197e4` `e2aa08d` | 23 Eylül ikinci oturum: bellek sınırı, 22. kapı + kendini yazan kapı günlüğü, [DOĞRULANMADI] kontrolü (`denetim-2026-09-20` burada) |
| `5a6b1ad` `934bb14` `347f810` `23d7c6b` | pyflakes kapısı ve temizlik, tanımlılık açığı, üç Lean şablonu, belgeler ve 23/23 raporları (`master` ve `yerel-kalite-2026-09-23` burada) |
| `eff4a7b` … `6323de7` | 24 Eylül, `bulut-2026-09-24` dalı (§0.7) |

Literatür kaynaklarının bağlantıları (ProcessBench, Hard2Verify, Beyond the Answer Key,
Pessimistic Verification, TinyV, Faults in Our Formal Benchmarking, Right Is Not Enough, Robustness
Testing of Intermediate Verifiers, Prover–Verifier Deliberation) `docs/QUALITY.md` içindedir.

---

## 6. Bilinen sorunlar

### 6.1 Deterministik hattın tek yanlış onayı: `tyt-prob-018`

Cevap doğru, ara adım doğru ama gerekçesiz ("iki denklemi çıkarınca a − b = 2"). Çözüm düzeyi
pozitif precision'daki tek FP bu (0.994). Gerekçesi §3 karar 21'de; F4 koşmadan karar verilemez.
Raporun "Sertifikanın iptal ettiği kritik raporu" satırı kararı sayıyla verecek.

### 6.2 Çözücünün kendi sembolüyle yazılmış adımlar denetlenmiyor

Bilerek böyle (§3 karar 3). `reports/soundness_report.md`'ye göre bir tarafı +1 bozulan 46 adımın
40'ı yakalanıyor. Kaçan 6 adımın nedeni artık raporda adım katmanının kendi kanıtından yazılıyor
(23 Eylül'e kadar sabit bir cümleydi):

| Öğe / adım | Neden | Sembol |
|---|---|---|
| `ayt-ana-006` s2 | `undeclared_symbol` | `n` |
| `ayt-diz-008` s1 | `undeclared_symbol` | `a` (dizinin adı, `a(n)`) |
| `ayt-lim-008` s2 | `undeclared_symbol` | `t` |
| `tyt-den-007` s2 | `undeclared_symbol` | `u` |
| `uni-la-002` s1 | `undeclared_symbol` | `t` |
| `tyt-den-003` s2 | `premises_have_no_solution`: öncül `x/(x−3) = 3/(x−3) + 2` çözümsüz, altın cevap `{}` | — |

Bilerek kabul edilen nedenler `harness/soundness_fuzz.py::ACCEPTED_MISS_REASONS` içinde. Başka bir
nedenle kaçırılan bozuk adım `check.py --full`'da "nedeni açıklanmayan kaçırılan bozuk adım"
kapısını düşürür (bugün 0/6).

### 6.3 Adımsız çözümde CORRECT yalnız cevap düzeyindedir

Yol (b)'de çoğu zaman denetlenebilir adım yoktur. Karar `answer_level_only` /
`answer_from_option_letter` bayraklarını ve `KAPSAM:` satırını taşır, ama bayrağa bakmayan bir
tüketici farkı görmez.

### 6.4 Sandbox bellek sınırı hiç uygulanmıyordu — DÜZELTİLDİ (23 Eylül)

`tests/test_sandbox.py::test_memory_cap_is_enforced_best_effort` Faz 1'den beri
`unavailable:AssignProcessToJobObject` ile sessizce atlanıyordu.

**Kök neden (probe ile doğrulandı):** `src/mathverify/sandbox/pool.py` içinde
`ctypes.windll.kernel32` fonksiyonları `restype`/`argtypes` verilmeden çağrılıyordu.
`GetCurrentProcess()`'in 64 bit sözde tutamacı 32 bit'e kırpılıyordu. Sonuç:

- `_apply_mem_limit` → `AssignProcessToJobObject` başarısız. Job Object sınırı yok.
- Yedek `_start_mem_watchdog` → `_rss_bytes()` `None`, çünkü `GetProcessMemoryInfo` aynı
  tutamaçla düşüyordu. Bekçi de başlamıyordu.

Yani worker'ları yalnız zaman aşımı koruyordu.

**Düzeltme:** `pool.py::_win_api()` özel `ctypes.WinDLL("kernel32"/"psapi", use_last_error=True)`
örnekleri ve açık prototipler kullanıyor; hata dizgisine Windows hata kodu ekleniyor.
Ölçüm: 512 MB sınırda 1500 MB'lık ve 2048 MB sınırda 3000 MB'lık ayırma `MemoryError` ile durdu;
sınır altında sympy/mpmath/z3 ısınma importu sorunsuz. Bu makinede süreçler zaten bir Job Object
içinde (`IsProcessInJob` True, muhtemelen masaüstü uygulaması); iç içe job çalışıyor.

**Teste bağlı:** Windows'ta `test_memory_cap_is_enforced_best_effort` artık atlanamaz
(`mem_mode == "job_object"` ve hata `MemoryError` olmalı). Yeni
`test_watchdog_fallback_can_read_process_memory` bekçinin bellek okuyabildiğini sınar. İkisi de
eski `pool.py` ile düşüyor, yenisiyle geçiyor (mutasyon kontrolü yapıldı).

### 6.5 Depodaki kapı günlüğü eskiydi — DÜZELTİLDİ (23 Eylül)

`reports/check_full.log` 19 Eylül'den kalmaydı (`12/12`); 23 Eylül'deki 21/21 çıktısı yalnız o
oturumun geçici görev dosyasındaydı. Artık `check.py --full` günlüğü kendisi yazıyor: başlıkta
tarih, dal, commit ve commit edilmemiş dosya sayısı var, satırlar koşu sırasında yazılıyor.

### 6.6 F3 yarım ölçüldü, F4 hiç koşmadı

`reports/f3_report.md` 18 Eylül'deki yarım koşudan ve eski raporlayıcıdan kalma:

- IR kabulü 64/218.
- 151 öğe `Your credit balance is too low` ile düştü.
- "Yol (b)" bölümü yol (b)'yi ölçmüyor. 218 öğenin 184'ü kredi bittiği için deterministik cevap
  çıkarıcıya düşmüştü (hepsinde `restructure_deterministic_only`), ve adımsız bir öğede D hücresi
  yapısal olarak yakalanamaz. Oradaki "37 yanlış karar, D tespiti 3/39" bu geri-düşmenin
  ölçümüdür.
- Gerçekten yeniden yapılandırılan 34 öğede 32/34 doğru karar, 0 UNKNOWN, D tespiti 3/5. 23 Eylül'de
  `reports/f3_results.json`'dan `run_f3`'ün kendi ayrımıyla (`n_steps > 0`) yeniden hesaplandı;
  LLM çağrısı yapılan öğelerle birebir aynı küme. **2 yanlış kararın ikisi de D hücresinde yanlış
  onay** (`ayt-ana-017`, `ayt-ana-019` → CORRECT), yani pahalı olan hata türü. Sayılar 18 Eylül
  koduna ait; o günden beri iki denetim yapıldı.
- IR kabulü: faturalama hatası almayan 67 öğede 64/67. Reddedilen 3 öğe (`ayt-diz-008`, `-013`,
  `-018`) üç turun sonunda round-trip'te Meta yargıcının puan döndürmediği (`meta: None`) öğeler;
  nedeni kayıtlardan anlaşılmıyor. README'deki eski "64/64" ve "kalan 154 öğe kredi hatasıyla
  düştü" ifadeleri 23 Eylül'de düzeltildi.
- Rapor yeniden koşulunca yeni raporlayıcı iki durumu ayrı yazacak.

### 6.7 Ölçüm hâlâ sentetik

Setin tamamını biz ürettik. Ölçülen 1.000 precision, gerçek bir modelin çözüm dağılımına karşı
değil. Bu açık kodla kapanmaz.

### 6.8 Teknik borç ve küçük tutarsızlıklar

- `DECISIONS.md` bölüm sırası 1, 2, 3, 6, 4, 5 ve madde numaraları bölümler arasında atlıyor.
  §3.9 hâlâ "180 öğe" diyor; bu Faz 1 anlık görüntüsü, güncel sayı 280.
- 23 Eylül'de kapatılanlar (DECISIONS §33): `run_lean` zaman aşımı 45'e hizalandı (60 ile aynı
  107 sertifika); tek seferlik betikler `scripts/dev/` altında (`diag_sandbox.py` silindi);
  `count_real_roots`'taki ölü `nsimplify` dalı artık kesin olmayan katsayıyı reddediyor, hiç
  çağrılmayan `nroots_scan` silindi; pyflakes bir kapı (tanımsız ad yakalar).
- Biçimlendirici (black/ruff format) yapılandırılmamış; pyflakes dışında stil denetimi yok.
- CI yok. Kapılar yalnız elle `check.py` ile koşuyor.
- Tanımlılık düzeltmesi (karar 30) türev, ekstremum ve seride yalnız **çekimser kalıyor**: f
  yazıldığı haliyle bölgede bir yerde tanımsızsa UNKNOWN. Bu yüzden "`x²/x`'in [−1, 1]'deki
  minimumu −1" doğru olduğu hâlde UNKNOWN. İstenirse ekstremum tanımsız noktaları dışlayarak
  hesaplanabilir; ölçülmedi.
- `antiderivative` yazıldığı haliyle tanımlılık için ayrıca sınanmadı (kaldırılabilir nokta ilkel
  fonksiyonu değiştirmez; ölçülmedi). `tangent_line`'ın noktası sınanıyor.

### 6.9 Güvenlik

İki API anahtarı yalnız git'in yok saydığı `.env` dosyasında
duruyorlar (`.gitignore:13`). 23 Eylül'de yeniden tarandı, değerler yazdırılmadan: iki anahtarın
değeri, tam ya da 16 karakterlik parça olarak, 14 commit'in (reflog dahil) tam diff'inde, izlenen
dosyalarda (`llm_cache/` dahil) ve 20 erişilemez blob'da **0** kez geçiyor; `sk-ant-` deseni 0;
stash yok. İş bitince ikisinin de yenilenmesi önerilir. Anahtarların hâlâ geçerli olduğu en son
19 Eylül'de görüldü **[DOĞRULANMADI: ağ isteği gerektirir, kontrol edilmedi]**.

**Düzeltme (24 Eylül 2026):** "yalnız git'in yok saydığı `.env`" ve "hiçbir commit'te 0 kez"
artık doğru değil. Kullanıcının açık kararıyla `.env` commit `6323de7`'de depoya girdi ve özel
GitHub deposuna push edildi (§0.3, DECISIONS §35); anahtar değerleri artık git geçmişinde ve
GitHub'ın sunucularında. Kural: değerler yine hiçbir çıktıya yazılmaz; anahtarlar kredili F3/F4
koşularından **önce** yenilenir (karar sürüyor) ve `.env` güncellenip commit edilir; depo açılır ya
da paylaşılırsa önce anahtarlar yenilenir ve `.env` geçmişten temizlenir. Bulut kabuğunda aynı adla
bir ortam değişkeni tanımlıysa `override=False` yüzünden `.env`'deki değil o kullanılır
**[DOĞRULANMADI: bulutta kontrol edilmedi, `docs/BULUT.md` §10]**.
**Düzeltme (24 Eylül 2026, akşam, ölçüm):** bulut kabuğunda `ANTHROPIC_API_KEY` ve
`ANTHROPIC_AUTH_TOKEN` tanımlı değil; `.env`'deki anahtar kullanılır. Tanımlı olan
`ANTHROPIC_BASE_URL` artık istemciye ulaşmaz (§0.3 eki, `4002898`).

---

## 7. Sıradaki adımlar

**Güncel sıra (25 Eylül 2026, denetimden sonra; §0.13).** Bunlar önce gelir:

1. Bu dal (`claude/compassionate-shannon-759r85`: kurulum betiği işi, §0.12, ve 25 Eylül denetimi,
   §0.13) kullanıcı onayı ve yedekle (etiket + bundle, §5.4) `master`a birleştirilir.
2. Aşağıdaki §0.12 sırasının 2.–4. adımları (Setup script metni, belirteç, sonraki sohbette ölçüm).
3. Krediye bağlı ölçümler (F3/F4) kod dondurulup anahtarlar yenilendikten sonra (kullanıcı kararı,
   23 Eylül). Bu denetimden sonra F3 ölçümü baştan koşulmalı: iddia okuma ve birleştirme kuralları
   değişti; eski F3 sayıları eski koda aittir.
4. Gerçek veri: hangi modelin çözümleri, hangi sorular, etiketleri kim koyacak (kullanıcı kararı).
   Denetçilerin sonda derlemlerinde 4 etiket yanlış çıktı; etiketler kaba kuvvetle ya da ikinci bir
   kişiyle denetlenmeli.
5. Açık kapsama işleri (hiçbiri doğru cevabı reddetmiyor): §0.13 "Açık kalanlar".

**Güncel sıra (25 Eylül 2026; §0.12).** Aşağıdaki listeler geçerli kalır; bunlar önce gelir. 24 Eylül
gecesi sırasının 2. adımı (belirteç ortam değişkeninde) yapıldı ama işe yaramadı:

1. Bu oturumun dalı (`claude/compassionate-shannon-759r85`: `fetch_artifacts.sh`'in belirteçli
   `raw.githubusercontent.com` adımı, belirtecin yalnız çekim aşamasına gitmesi, değişken adları
   satırı, yeni önyükleyici, belgeler) kullanıcı onayı ve yedekle (etiket + bundle, §5.4) `master`a
   birleştirilir. Kurulum betiği checkout'taki `master` kopyasını çalıştırır.
2. Kullanıcı: Setup script alanının metnini yeni önyükleyiciyle değiştirir ve belirteci `T=''`
   tırnaklarının arasına yapıştırır; Environment variables'taki `MATHVERIFY_GITHUB_TOKEN` satırını
   siler; isteğe bağlı `MATHVERIFY_SETUP_CANARY=1` ekler (`docs/BULUT.md` "Senin yapman
   gerekenler" 3. madde, 25 Eylül düzeltmesi). Metin değiştiği için görüntü yeniden kurulur.
3. Sonraki yeni sohbette ölçüm (`docs/BULUT.md` §12): `setup_env.status` `OK mode=all`;
   `environment (names only)` satırı; `fetch_artifacts.log`'da hangi yolun çalıştığı; kanca açılışta
   "Lean: HAZIR". Bir sonraki yeni sohbette görüntünün `/opt`'u koruduğu. Dosya indirme yolu da
   düşerse (ör. kurulum aşamasında `raw.githubusercontent.com` kapalıysa), kalan seçenekler
   DECISIONS §54 *Seçilmeyenler* (b) ve (c): açık bir araç deposu (kullanıcı kararı) ya da yalnız
   kanca (her yeni sohbet ~4 dk).
4. Devam ettirilen sohbette Lean'in ilk açılışı >300 s sürebiliyor (§0.11; değişmedi).

**Güncel sıra (24 Eylül 2026, akşam).** Aşağıdaki eski liste geçerli kalır; bunlar önce gelir:

1. **Kullanıcı WSL disk imajını sıkıştırır** (§0.10). Bu belge yazılırken `.vhdx` 103.8 GB, C:'de
   6.1 GB boş. Yönetici PowerShell ya da komut isteminde:
   ```
   wsl --shutdown
   diskpart
   select vdisk file="C:\Users\kullanici\AppData\Local\wsl\{WSL-GUID}\ext4.vhdx"
   attach vdisk readonly
   compact vdisk
   detach vdisk
   exit
   ```
   WSL içinde kullanılan ~15 GB'ın yakınına inmesi beklenir [DOĞRULANMADI: sıkıştırma henüz
   yapılmadı].
   **Yapıldı** — **Düzeltme (24 Eylül 2026, 16:54):** kullanıcının yetkisiyle sıkıştırıldı. UAC onayıyla yönetici PowerShell'de `wsl --shutdown` + `diskpart` (`attach vdisk readonly`, `compact vdisk`, `detach vdisk`) çalıştı, 20 s sürdü: `.vhdx` 103.79 → 15.98 GB, C: boş alanı 6.10 → 93.95 GB. Ardından WSL açıldı; Lean 4.34.0, Mathlib `5ed2965` ve REPL duman testi (`{"env": 0}`) sağlam.
2. **Kullanıcı kurulum betiğini yapıştırır:** `docs/BULUT.md` "Senin yapman gerekenler": ağ Trusted
   kalır, "Setup script" alanına önyükleyici, ortam değişkeni gerekmez.
3. **İlk normal bulut oturumu `master`da `docs/BULUT.md` §12'nin açık maddelerini ölçer** (kurulum
   betiğinin gerçek koşusu, anlık görüntü, platformun tetiklediği kanca, `CLAUDE_ENV_FILE`, bulutta
   `check.py --full`). Önce bu dalın kalan commit'leri kullanıcı onayı ve yedekle `master`a alınır
   (§5.4); yoksa `master`daki betikler `4d01ba2` hâlindedir. Oturum bir routine ise istem push
   hedefini yeni bir dal olarak verir (§0.9).
4. **F3/F4** anahtarlar yenilendikten sonra, kararı değişmeden (aşağıda 3–4; bulutta `api.meta.ai`
   için Custom ağ).

**Düzeltme (24 Eylül 2026, gece):** 2. adım yapıldı (kurulum betiği alanda tanımlı) ve 3. adım bu
oturumda başladı (§0.11): kurulum betiği alanından koştu ama özel depoya kimliksiz gittiği için
araç ref'ini çekemedi. Yeni sıra, F3/F4'ten önce:

1. `MATHVERIFY_GITHUB_TOKEN` değişikliğinin (`claude/funny-cray-bey5o1` dalı) `check.py --full`
   24/24 ile doğrulanması ve kullanıcı onayı + yedekle `master`a birleştirilmesi (kurulum betiği
   checkout'taki `master`ın kopyasını çalıştırır; birleşmeden etkisi olmaz).
2. Kullanıcı: GitHub'da belirteç + ortam değişkeni + kurulum betiğine bir yorum satırı (görüntünün
   yeniden kurulması için), adımlar `docs/BULUT.md` "Senin yapman gerekenler" 3. madde.
3. Sonraki yeni sohbette ölçüm: `setup_env.status` `OK mode=all`, `fetch_artifacts.log`'da "the
   token fetch succeeded", kanca "Lean: HAZIR" ile açılıyor; bir sonraki yeni sohbette de görüntünün
   `/opt`'u koruduğu (`docs/BULUT.md` §12).
4. Devam ettirilen sohbette Lean'in ilk açılışı >300 s sürebiliyor (§0.11). Kancanın, yeniden
   başlatmadan sonra Lean dosyalarını arka planda bir kez okuyarak ısıtması düşünülebilir; ancak
   gerçek bir yeniden başlatmada ölçülerek eklenir (ölçülmemiş iyileştirme iyileştirme sayılmaz).

Eski listenin ilk iki maddesi 23 Eylül'de tamamlandı: sandbox bellek sınırı (§6.4) ve kapı
günlüğü (§6.5). Aynı gün, kullanıcının "geri kalan lokal işlemleri yap" talimatıyla, eski 2.
maddedeki lokal kalite işlerinin hepsi yapıldı (ölü `nsimplify` dalı, betikler, zaman aşımı, üç
Lean şablonu) ve bu sırada bulunan tanımlılık açığı kapatıldı (karar 30). Bunlar `master`da.

**Kullanıcı kararı (23 Eylül 2026):** krediye bağlı ölçümler (aşağıda 3–5) ancak bütün lokal iş
bitip program en kaliteli hâline geldikten sonra koşulacak. Bunun iki sonucu var: (a) F3/F4
koşusundan önce kod dondurulur; ölçümden sonraki her kod değişikliği o sayıları yeniden eskitir
(18 Eylül F3 sayıları bugün bu durumda). (b) Bazı kararlar yalnız o ölçümle verilebilir
(`tyt-prob-018` kuralı, §3 karar 21; F4'ün yerini hak edip etmediği); "en kaliteli" lokal durum
bu soruları açık bırakır.

Öncelik sırasıyla:

1. **Kullanıcıya §12'deki açık soruları sor** (birleştirme soruları cevaplandı).

2. **Kalan lokal işler (ikisi de ürün kararı ister, kod değil):**
   - Çözücü sembolü adımları (§6.2): yapısal formatta çözücünün kendi sembolünü tanımlamasını
     zorunlu kılmak `docs/SOLVER_FORMAT.md` sözleşmesini değiştirir. Karar verilmedi.
   - Tanımlılık düzeltmesinin türev/ekstremum/seride çekimser kalmak yerine hesaplaması (§6.8).
   Kodda kredi gerektirmeyen başka açık iş bilinmiyor. Yeni bir denetim turu her zaman yeni
   sınıflar bulabilir (bu oturum 11 yanlış-onay vakası buldu); "en kaliteli" iddiası ancak ölçümle
   verilir.

3. **Kod dondurulduktan ve anahtarlar yenilendikten sonra F3'ü tamamla.** Önce kalibrasyon
   koşusu: `.venv/Scripts/python.exe -m harness.run_f3 --limit 10 --workers 3 --max-cost 5`.
   Öğe başına gerçek maliyeti ölç; yarım koşuda 0,066 $/öğe ölçülmüştü (`docs/LLM_LAYERS.md`).
   Sonra tam koşu: `.venv/Scripts/python.exe -m harness.run_f3 --workers 6 --pathb --max-cost 40`.
   Kalan 154 öğe için kaba tahmin ~10 $. `llm_cache/` istek hash'iyle anahtarlıdır; istem ya da IR
   metni değiştiyse eski kayıtlar tekrar oynatılmaz ve yeniden ücretlendirilir.
   **Ek (24 Eylül 2026):** Linux/bulutta yorumlayıcı `.venv/bin/python`. Bulutta koşulacaksa ağ
   ayarı Custom + "also include default list" + `api.meta.ai` yapılır; `api.anthropic.com`
   varsayılan Trusted listesinde ("Anthropic services", resmi belge 24 Eylül'de okundu; bulutta
   erişim henüz ölçülmedi, `docs/BULUT.md` §3.1). Uzun koşu sürerken
   bulut oturumu etkin tutulur.
   **Düzeltme (24 Eylül 2026, akşam, ölçüm):** bulutta `api.anthropic.com` erişilebilir,
   `api.meta.ai` vekilde 403 ile kapalı (§0.8); Custom ağ yalnız `api.meta.ai` için gerekir.
   İstemci platformun `ANTHROPIC_BASE_URL`'ini okumaz; farklı bir uç nokta gerekirse
   `MATHVERIFY_ANTHROPIC_BASE_URL` (§9).

4. **F4'ü ilk kez koştur** (aynı koşuda L6 açık). Kaba tahmin 15–25 $. Raporun "L6 kritik +
   meta-doğrulama (F4)" bölümündeki iki sayı belirleyici: D tespiti ve doğru çözümde yanlış
   suçlama. "Sertifikanın iptal ettiği kritik raporu" satırı `tyt-prob-018` kararını verir
   (§3 karar 21).

5. **Gerçek AI çözücü çıktılarıyla ölç.** `--solver-family anthropic|meta` **mutlaka** verilmeli.
   Kullanıcı bu adımı erteledi.

6. **Uzak depo + CI + LICENSE.** Bunlar sahiplik kararları. Açılırsa CI hızlı modda
   `scripts/check.py` çalıştırmalı; Lean ve `--full` WSL ister.
   **Düzeltme (24 Eylül 2026):** uzak depo açıldı (özel GitHub, §0.1). Lean ve `--full` artık WSL
   istemiyor, Linux'ta da çalışıyor (bulutta kurulumla birlikte, `docs/BULUT.md`). CI ve LICENSE
   hâlâ açık (§12).

7. **İlk bulut oturumu** (24 Eylül'de eklendi): `docs/BULUT.md` §12'deki ölçüm listesi. Sonuçlar
   §0.6'ya ve `docs/BULUT.md`'ye yazılır.
   **Düzeltme (24 Eylül 2026, akşam):** listenin çoğu routine oturumunda ölçüldü (§0.8); kalanı
   yukarıdaki güncel sıranın 3. adımı.

---

## 8. Kritik dosyalar

| Yol | Açıklama |
|---|---|
| `src/mathverify/verifier.py` | Deterministik giriş: `verify`, `verify_layers`, `fuse_layers`, şık/kapsam bayrakları, `_sanitize_payload`, `_claim_not_a_value`, `_mc_consistency`, `_sanity` |
| `src/mathverify/pipeline.py` | `run_pipeline`: soru metninden karara tam otomatik hat (IR çıkarımı + L4/L5/L6/L7) |
| `src/mathverify/ir.py` | `ProblemIR`, `FORBIDDEN_KEYS`, `LeakageError` |
| `src/mathverify/solution.py` | `Solution`, `ClaimedAnswer`, `Step` |
| `src/mathverify/types.py` | `LayerResult`, `VerificationResult` |
| `src/mathverify/router.py` | `ROUTES` (görev türü → modüller), `DEFERRED_KINDS`, `route` |
| `src/mathverify/normalize/parse.py` | Beyaz listeli ayrıştırıcı; `COMPUTING_OPERATORS`, `claim_namespace`, `check_claim_is_value`, `UndeclaredSymbolError`, `ClaimNotAValue`, `parse_as_written` (yalnız tanımlılık için, sadeleştirmesiz) |
| `src/mathverify/normalize/turkish.py` | Türkçe sayı biçimi ve metin normalizasyonu |
| `src/mathverify/equiv/__init__.py` | Eşdeğerlik motorunun girişi, `exact_integer` |
| `src/mathverify/equiv/numeric.py` | Hassasiyet merdiveni (her basamakta eşitlik) |
| `src/mathverify/equiv/random_point.py` | Rastgele nokta testi, `_definite_nonzero_difference` |
| `src/mathverify/sandbox/pool.py` | Worker havuzu, zaman aşımı, bellek sınırı (`_win_api`: tipli ctypes prototipleri, §6.4) |
| `src/mathverify/sandbox/ops.py` | Sandbox içindeki işlemler, `zero_test_battery` |
| `src/mathverify/certify/base.py` | `Ctx`, `Ctx.claim_ns`, `Ctx.claimed`, `Ctx.written_conditions` → `domain_for` / `var_constraints` |
| `src/mathverify/certify/__init__.py` | `MODULES` kaydı (13 sertifika modülü) |
| `src/mathverify/certify/domain.py` | `definedness_conditions`, `written_definedness`, `written_undefined_in`; Lean junk korumaları da bunu kullanır |
| `src/mathverify/steps/deterministic.py` | `check_steps`: yalnız karşı örnekle çürüten adım reddedici |
| `src/mathverify/fuse/rules.py` | `fuse`, `_BLOCK_POSITIVE_FLAGS`, kalibrasyon, `CalibrationUnavailable` |
| `src/mathverify/intake/restructure.py` | Yol (b) deterministik cevap çıkarıcı ve küme/aralık kurtarma |
| `src/mathverify/extract/ir_extract.py` | LLM ile IR çıkarımı + round-trip + onarım |
| `src/mathverify/llm/__init__.py` | Aile/rol eşlemesi, istemci seçimi, `set_client_override` |
| `src/mathverify/llm/base.py` | `LLMError`, `LLMFatalError` (alt sınıfı değil!) |
| `src/mathverify/llm/cache.py` | Kayıt/tekrar önbelleği |
| `src/mathverify/formal/statement.py` | Lean ifade şablonları (`build_statement`, `_t_*`; 23 Eylül'de `_t_domain_of` + `_region_iff_hints`, `_t_simplify_expression`, `_t_count_solutions`), junk-value korumaları, `vacuity_probe`, `is_trivial` |
| `src/mathverify/formal/prove.py` | Taktik merdiveni, ispat denetimleri, `l7_layer` |
| `src/mathverify/formal/lean_client.py` | WSL içindeki Lean REPL istemcisi. *Düzeltme (24 Eylül 2026):* Linux'ta yerel `bash -lc`; `repl_command`, `native_repl_path`, süreç grubu + `killpg` (DECISIONS §40) |
| `harness/run_eval.py` | Deterministik ölçüm ve sızma testi → `reports/eval_report.md` |
| `harness/run_lean.py` | Lean taraması + 12 `JUNK_PROBES` → `reports/lean_report.md`. *Düzeltme (24 Eylül 2026):* sonda sayısı 23 Eylül'den beri 17; rapor `lean_available`, `lean_available_end` ve kayıt başına `lean_reached` yazar (DECISIONS §39) |
| `harness/adversarial.py` | 3 yüzeyli adversaryal tarama → `reports/adversarial_report.md` |
| `harness/soundness_fuzz.py` | Metamorfik/diferansiyel sağlamlık taraması → `reports/soundness_report.md`; `ACCEPTED_MISS_REASONS`, `_missed_step_reason` |
| `harness/calibrate.py` | Kalibrasyon (train/val/test) |
| `harness/run_f3.py` | LLM'li tam hat ölçümü (F3/F4); `--max-cost`, `--solver-family`, `--pathb` |
| `scripts/check.py` | Bütün kapılar tek komutta; `--full` günlüğü `reports/check_full.log`a kendisi yazar |
| `scripts/verify_cli.py` | Tek öğe ya da serbest metin doğrulama; `--lean` |
| `scripts/dev/` | Kapıların parçası olmayan geliştirme betikleri (`README.md` içinde listeli) |
| `tests/test_written_definedness.py` | Tanımlılık düzeltmesinin 11 vakası (karar 30) |
| `evalset/build/build_all.py` | 280 öğeyi yeniden üretir |
| `tests/conftest_llm.py` | `ScriptedClient`: F3/F4 testleri ağsız koşar |
| `DECISIONS.md` | Kilitli kararlar ve 30 uygulama kararı. *Düzeltme (24 Eylül 2026):* madde numaraları 43'e kadar; 24 Eylül kararları §7 (34–43) |
| `docs/ARCHITECTURE.md` | Yetki tablosu ve tasarım gerekçeleri |
| `docs/QUALITY.md` | Literatür → mekanizma → kapı tablosu |
| `docs/SOLVER_FORMAT.md` | Yol (a) yapısal çözüm formatı ve görev türleri |
| `docs/LLM_LAYERS.md` | Roller, modeller, önbellek, maliyet, hata sınıfları |
| `docs/LEAN_SETUP.md` | WSL + Lean + Mathlib kurulumu. *Düzeltme (24 Eylül 2026):* Linux/bulut kurulumu ve sabit sürümler de orada |
| `docs/E1-E10-measurement.md` | Şartname §6 davranış sözleşmelerinin ölçümü |
| `docs/BULUT.md` | Bulut el kitabı: ön koşullar, ortam ayarı, kurulum betiği + kanca, `/opt` düzeni, günlükler, sınırlar, ilk oturumda ölçülecekler (24 Eylül) |
| `docs/sartname/` | Özgün şartname (kanonik `_1.md`, eski `_eski.md`) |
| `lean/` (`PINS` + proje dosyaları) | Sabit Lean/Mathlib/REPL/elan sürümleri; elle düzenlenmez (`lean/README.md`) |
| `scripts/setup_lean.sh`, `scripts/setup_lean_repl.sh` | Sabit, çevrimdışı yapılabilen Lean kurulumu (WSL ve Linux) |
| `scripts/fetch_artifacts.sh` | Araç ref'ini (`refs/arac/bulut-vN`) çeker, parçaları birleştirir, SHA256 ile doğrular. *Ek (24 Eylül gecesi):* düz çekim düşerse `MATHVERIFY_GITHUB_TOKEN` ile bir kez daha dener (kurulum betiği aşaması, §0.11, DECISIONS §53). *Ek (25 Eylül):* o da düşerse dosyaları belirteçle `raw.githubusercontent.com`'dan indirir, her parçayı `SHA256SUMS.parts`'a karşı doğrular; belirteç ortamda değil kabuk değişkeninde (§0.12, DECISIONS §54) |
| `scripts/cloud/setup_env.sh` | Bulut ortam kurulum betiği (root, `/opt`, her zaman 0); başlığında yapıştırılacak önyükleyici. *Ek (25 Eylül):* önyükleyici belirteci `T=''` satırında alır; betik belirteci yalnız çekim aşamasına verir ve gördüğü değişkenlerin adlarını günlüğe yazar (§0.12) |
| `scripts/cloud/session_start.sh`, `.claude/settings.json` | SessionStart kancası; yalnız `CLAUDE_CODE_REMOTE=true` iken iş yapar |
| `requirements.lock` | Paket kilidi (32 paket) |
| `reports/arsiv/2026-09-24/` | Rapor JSON'larının anlık görüntüsü; iki F3 dosyası yeniden üretilemez |
| `tests/test_lean_client_posix.py`, `tests/test_check_gates_harness.py` | Linux Lean istemcisi ve kapı sertleştirmesinin testleri |
| `docs/bulut_tani_2026-09-24.md` | (24 Eylül akşamı) gerçek bulut ölçümünün ham raporu, `4d01ba2` (§0.8) |
| `tests/test_cloud_scripts.py` | bulut betiklerinin testleri (`cbe01a7`'den beri; 24 Eylül akşamı çevrimdışı, aşamalı kurulum ve Python seçimi testleriyle genişledi) |
| `tests/test_prove_audit_timeout.py`, `tests/test_llm_base_url.py` | (24 Eylül akşamı, yeni) cevapsız denetim sondası (ilke 7), Anthropic uç noktası |

---

## 9. Komutlar ve ortam

Bütün komutlar proje kökünden. Windows'ta **`PYTHONUTF8=1`** gerekir; `check.py` bunu alt süreçlere
kendisi verir. Bu belgedeki `PYTHONUTF8=1 komut` biçimi **Git Bash** içindir. PowerShell'de önce
`$env:PYTHONUTF8 = "1"` çalıştırılır, sonra komut öneksiz yazılır.

**Ek (24 Eylül 2026):** aşağıdaki tablolardaki `.venv/Scripts/python.exe` Windows yoludur; Linux'ta
ve bulutta yerine `.venv/bin/python` yazılır (`PYTHONUTF8=1` yine verilir). `check.py` hangi
platformda olduğunu kendisi bulur.

### Kurulum

```bash
uv venv --python 3.14 .venv
uv pip install --python .venv/Scripts/python.exe -e ".[llm,dev]"
```

Linux (bulutta bunu oturum kancası yapar, `docs/BULUT.md` §4):

```bash
uv venv --python 3.14 .venv
uv pip install --python .venv/bin/python -r requirements.lock
uv pip install --python .venv/bin/python --no-deps -e .
```

Lean, tek seferlik kurulum (ayrıntı: `docs/LEAN_SETUP.md`):

```bash
wsl -d Ubuntu -- bash /mnt/c/Users/kullanici/mathverify/scripts/setup_lean.sh
wsl -d Ubuntu -- bash /mnt/c/Users/kullanici/mathverify/scripts/setup_lean_repl.sh
wsl -d Ubuntu -- bash /mnt/c/Users/kullanici/mathverify/scripts/lean_status.sh
```

`setup_lean.sh` sonrasında üst düzey `Mathlib.olean` eksikse `scripts/lean_fix.sh` çalıştırılır.
Lean bu makinede kurulu: WSL `Ubuntu` mevcut ve 23 Eylül Lean taraması çalıştı.

**Düzeltme (24 Eylül 2026):** yukarıdaki komutlar yalnız Windows (WSL) içindir. Linux'ta aynı
betikler WSL'siz koşar: `bash scripts/setup_lean.sh`, `bash scripts/setup_lean_repl.sh`,
`bash scripts/lean_status.sh`; bulutta hepsini ortamın kurulum betiği yapar. Betikler artık
`lean/PINS`'teki sabit sürümleri kurar ve eksik kök modülleri kendileri derler, `lean_fix.sh`
adımı gereksiz (yalnız eski kurulumları onarmak için duruyor). Ayrıntı `docs/LEAN_SETUP.md`,
DECISIONS §38.

### Test ve kapılar

| Komut | Ne yapar | Süre |
|---|---|---|
| `.venv/Scripts/python.exe -m pytest tests -q` | 439 test (438 geçer, 1 atlanır) | ~90 s |
| `.venv/Scripts/python.exe scripts/check.py` | Hızlı: testler + pyflakes + deterministik ölçüm (12 kapı) | ~3 dk |
| `.venv/Scripts/python.exe scripts/check.py --full` | + Lean, adversaryal, sağlamlık, kalibrasyon (23 kapı); günlüğü `reports/check_full.log`a yazar | **~25–70 dk** (adversaryal tek başına 21–58 dk, makine yüküne bağlı) |

**Düzeltme (24 Eylül 2026):** `pytest` artık 838 test (Windows'ta
776 geçer, 62 atlanır; yerel Linux'ta 836 / 2); `--full` **24 kapı** ("Lean
erişilebilir"). Bir harness çökerse, raporunu yazmazsa, Lean yoksa ya da tarama sırasında
kaybolursa ilgili kapılar FAIL olur (DECISIONS §39). Bulutta `--full` süresi
~63 dk (3793 s; adversaryal 3220 s; 4 vCPU); 24/24 (ikinci routine oturumu, `74d9da1`).

### Tek tek ölçümler

| Komut | Çıktı |
|---|---|
| `.venv/Scripts/python.exe evalset/build/build_all.py` | 280 öğeyi yeniden üretir |
| `.venv/Scripts/python.exe -m harness.run_eval` | `reports/eval_report.md` |
| `.venv/Scripts/python.exe -m harness.run_lean --timeout 45` | `reports/lean_report.md` |
| `.venv/Scripts/python.exe -m harness.adversarial` | `reports/adversarial_report.md`; `--ids a,b` hedefli tekrar |
| `.venv/Scripts/python.exe -m harness.soundness_fuzz` | `reports/soundness_report.md` |
| `.venv/Scripts/python.exe -m harness.calibrate` | `reports/calibration_report.md` |
| `.venv/Scripts/python.exe -m harness.run_f3 --workers 6 --pathb --max-cost 40` | `reports/f3_report.md`; kredi ister. `--no-l4/--no-l5/--no-l6`, `--limit`, `--ids`, `--solver-family` |

### Tek öğe doğrulama

```bash
.venv/Scripts/python.exe scripts/verify_cli.py --item evalset/items/tyt-prob-001.json --lean
.venv/Scripts/python.exe scripts/verify_cli.py --item evalset/items/tyt-prob-001.json --text "… Cevap: B"
```

Diğer bayraklar: `--ir`, `--solution`, `--json`, `--no-steps`.

### Build ve lint

Ayrı bir build adımı yok; paket `-e` ile kurulu. Lint ya da biçimlendirici **yapılandırılmamış**.

### Ortam değişkenleri (yalnız adlar; değerler `.env` içinde, asla yazılmaz)

| Değişken | Anlamı |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic ailesi (`.env` içinde) |
| `ANTHROPIC_AUTH_TOKEN` | Anthropic için alternatif kimlik bilgisi (kodda okunuyor, `.env`'de yok) |
| `META_MODEL_API_KEY` | Meta Muse Spark ailesi (`.env` içinde) |
| `MATHVERIFY_ANTHROPIC_MODEL` | Varsayılan `claude-opus-5` |
| `MATHVERIFY_ANTHROPIC_BASE_URL` | (24 Eylül'de eklendi) Anthropic uç noktası, varsayılan `https://api.anthropic.com` (SDK varsayılanı). İstemci `base_url`'i hep açıkça verir, çünkü Claude Code'un tanımladığı `ANTHROPIC_BASE_URL` (bulutta ve masaüstünde ölçüldü) yoksa SDK'ya miras kalırdı (`4002898`, DECISIONS §48) |
| `MATHVERIFY_META_MODEL` | Varsayılan `muse-spark-1.3` |
| `MATHVERIFY_LLM_CACHE` | `auto` (varsayılan) / `replay` (ağa çıkmaz) / `off` |
| `MATHVERIFY_LLM_CACHE_DIR` | Varsayılan `llm_cache/` |
| `MATHVERIFY_CALIBRATION` | `on` → kalibre füzyon (varsayılan kapalı) |
| `MATHVERIFY_LEAN_PROJECT` | Varsayılan `~/mathverify-lean` (WSL içinde) |
| `MATHVERIFY_LEAN_REPL` | Varsayılan `~/repl/.lake/build/bin/repl` |
| `MATHVERIFY_WSL_DISTRO` | Varsayılan `Ubuntu` |
| `MATHVERIFY_SANDBOX` | `process` (varsayılan) / `inline` (yalnız hata ayıklama) |
| `PYTHONUTF8` | Windows'ta `1` olmalı |
| `PYTHONHASHSEED` | Sandbox worker'larında `0`'a sabitlenir (kod yapar) |

**Düzeltme ve ek (24 Eylül 2026):** `MATHVERIFY_LEAN_PROJECT` yalnız Windows'ta "WSL içinde" bir
yoldur; Linux'ta yerel yoldur (bulutta `/opt/mathverify-lean`). `MATHVERIFY_WSL_DISTRO` yalnız
Windows'ta okunur. `.env` artık depoda izleniyor (§0.3). Yeni değişkenler (ayrıntı
`docs/BULUT.md` §5):

| Değişken | Anlamı |
|---|---|
| `ELAN_HOME` | elan evi, varsayılan `$HOME/.elan` (bulutta `/opt/elan`); istemci `PATH`'e `${ELAN_HOME:-$HOME/.elan}/bin` ekler |
| `MATHVERIFY_OPT` | Bulut kurulum öneki, varsayılan `/opt` |
| `MATHVERIFY_ARTIFACT_DIR` | Araçların açıldığı dizin; `setup_lean.sh` burada bulduğunu çevrimdışı kurar |
| `MATHVERIFY_ARTIFACT_URL` / `MATHVERIFY_ARTIFACT_REF` / `MATHVERIFY_ARTIFACT_SRC` | Araç ref'inin kaynağı: depo adresi (varsayılan `origin`), ref (varsayılan `refs/arac/bulut-v2`), ya da yerel `parts/` dizini |
| `MATHVERIFY_SKIP_LEAN` | `1`: bulut kancası Lean kurulumunu başlatmaz |
| `MATHVERIFY_REPO_URL` / `MATHVERIFY_REPO_REF` | Kurulum betiğinin klon yedeği (varsayılan `https://github.com/wqedwad/asd` / uzak varsayılan dal) |
| `MATHVERIFY_PROFILE_D` | `mathverify.sh`'in yazıldığı yer, varsayılan `/etc/profile.d` |
| `MATHVERIFY_HOOK_PREFIXES` | Kancanın önek listesi; yalnız testler için |
| `MATHLIB_CACHE_DIR`, `XDG_CACHE_HOME` | Mathlib `.ltar` önbelleği, varsayılan `$HOME/.cache/mathlib` |
| `CLAUDE_CODE_REMOTE`, `CLAUDE_PROJECT_DIR`, `CLAUDE_ENV_FILE` | Platformun verdiği değişkenler; kanca yalnız `CLAUDE_CODE_REMOTE=true` iken iş yapar |
| `MATHVERIFY_LEAN_OFFLINE` | (24 Eylül akşamı eklendi) `1`: `setup_lean.sh` ve `setup_lean_repl.sh` sıkı çevrimdışı; her çevrimiçi yedek (araç zinciri indirmesi, `lake exe cache get`, klon, `apt-get`) reddedilir, eksik artefakt betiği bir şey yazmadan durdurur. `setup_env.sh` her zaman `1` verir; varsayılan `0` |
| `MATHVERIFY_GITHUB_TOKEN` | (24 Eylül gecesi eklendi) yalnız bu depoyu okuyabilen GitHub belirteci (fine-grained, Contents: read-only); claude.ai ortamının değişkenlerinde, depoda değil. `fetch_artifacts.sh` onu yalnız düz çekim düştükten sonra ve yalnız `MATHVERIFY_GITHUB_TOKEN_URL` (varsayılan `https://github.com/`) altındaki adrese gönderir; değer hiçbir çıktıya yazılmaz (§0.11, DECISIONS §53). `GITHUB_TOKEN`/`GH_TOKEN` adı kullanılmaz. **Düzeltme (25 Eylül 2026, ölçüm):** claude.ai ortam değişkeni kurulum betiğine ulaşmaz; belirteç Setup script metnindeki önyükleyicinin `T=''` satırında verilir, ortam değişkeninden silinir (§0.12, DECISIONS §54) |
| `MATHVERIFY_GITHUB_RAW_URL` / `MATHVERIFY_ARTIFACT_VIA` | (25 Eylül'de eklendi) belirteçli dosya indirmenin adresi (varsayılan `https://raw.githubusercontent.com/`; boşsa adım atlanır) / `raw`: yalnız o yol (ölçüm için) |
| `MATHVERIFY_SETUP_CANARY` | (25 Eylül'de eklendi) zararsız işaret; claude.ai ortamına eklenirse `setup_env.sh` adının kurulum betiğine ulaşıp ulaşmadığını yazar |

**Düzeltme (24 Eylül 2026, akşam, `eba49b5`):** `MATHLIB_CACHE_DIR` satırındaki
`$HOME/.cache/mathlib` yalnız araç dizini olmadan yapılan kurulumda geçerli. Bulut kurulumu
`.ltar`'ları `$OPT/.mathlib-ltar`'a, araç diziniyle tek başına koşan `setup_lean.sh` projenin
yanındaki geçici `.<proje>.ltar.<pid>`'e açar; ikisi de kurulumdan sonra silinir. Routine oturumunun
ölçtüğü `/root/.cache/mathlib` (448 MB) bu değişiklikten önceki `4d01ba2`'dendi; anlık görüntüde
artık `.ltar` kalmaz (`docs/LEAN_SETUP.md`, `docs/BULUT.md` §5).

**Düzeltme (25 Eylül 2026, ölçüm):** bu tablodaki değişkenler claude.ai ortam ayarından verilirse
yalnız oturuma (komutlar, kanca, kancanın başlattığı `--lean-only`) ulaşır; anlık görüntüyü kuran
kurulum betiği koşusu yalnız Setup script metninde verilenleri görür (§0.12, `docs/BULUT.md` §3.3).

### Harici servisler ve bağımlılıklar

- Anthropic API: F3+ katmanları. **Bakiye bitti.**
- Meta Muse Spark API: ikinci aile.
- WSL Ubuntu + Lean 4 v4.34.0 + Mathlib: L7. Olean cache ~6.7 GB.
- Başka ağ bağımlılığı yok. Deterministik hat tamamen çevrimdışı çalışır.

**Ek (24 Eylül 2026):**

- GitHub, özel depo `wqedwad/asd`: kaynak, bulut oturumları ve araç ref'i (`refs/arac/bulut-vN`).
- Lean, Linux/bulutta WSL'siz; bulutta kurulumun tamamı ~12–13 GB (WSL ölçümü ~12 GB).
- Claude Code on the web: bulut oturumları (`docs/BULUT.md`).

**Ek (24 Eylül 2026, akşam, bulut ölçümü):** bulutta `/opt/elan` 3.0G + `/opt/mathverify-lean` 7.2G +
`/opt/python3.14` 107M (+ o sürümde kalan 448M `.ltar`, artık silinir). Bulutun ağından açık:
GitHub, PyPI, `api.anthropic.com`; kapalı: `releases.lean-lang.org`, `cache.mathlib.org`,
`releases.astral.sh`, `api.meta.ai` (§0.8).

---

## 10. Kurallar ve tercihler

### Kullanıcının tercihleri

- **Dil:** kullanıcıyla Türkçe konuşulur. Belgeler, raporlar, karar izleri ve commit mesajları
  Türkçe. Kod, tanımlayıcılar ve `src/` içindeki yorumlar İngilizce.
- **Derinlik:** kullanıcı en kaliteli, kapsamlı ve özerk çalışmayı ister. "Emin ol" ya da "tek
  eksik bu mu" gibi sorular harfiyen kastedilir. Cevap, bir önceki cevabın tekrarı değil, yeni ve
  sistematik bir denetim olmalı. Krediye bağlı olmayan bir açık bulunursa aynı turda düzeltilmeli.
- **Dürüstlük:** ölçülmüş sayılar verilir, "testler geçiyor" kanıt sayılmaz. Doğrulanmamış bilgi
  işaretlenir. Önceki bir iddia yanlış çıktıysa bu açıkça söylenir.
- Kilitli kararlar (D1–D6) yeniden sorulmaz.

### Asla yapılmayacaklar

1. Cevap anahtarını ya da anahtar benzeri bir alanı doğrulama hattına sokmak.
2. Bir LLM sinyalinin sert bir sertifikayı ters çevirmesine izin vermek.
3. Bir adımı somut karşı örnek olmadan reddetmek.
4. Lean ifadesini bir modele yazdırmak, ya da bir ispatı sorry/aksiyom/vakum/kullanılmayan
   hipotez denetiminden geçirmeden kabul etmek.
5. `first | …` zincirinde `done` ile kapanmayan bir alternatif yazmak.
6. Bir iddiayı karşılaştırmadan önce yeniden yazmak: `int()`, `nsimplify`, yuvarlama,
   "güzelleştirme" yok.
7. Tek başına nümerik eşitliği kanıt saymak, ya da Math-Verify'ı tek başına karar verdirmek.
8. İddiayı hesaplayan operatörlerin açık olduğu bir ad alanında okumak.
9. `.env`'i, `reports/*.json`'ı ya da herhangi bir anahtarı commit etmek. Anahtar değerlerini
   ekrana, belgeye ya da günlüğe yazmak.
   **Düzeltme (24 Eylül 2026):** `.env` kısmı kullanıcının açık kararıyla kalktı; `.env` bu özel
   depoda izlenir (§0.3, DECISIONS §35). `.env.*` ve `reports/*.json` yine commit edilmez; anahtar
   değerleri yine hiçbir çıktıya yazılmaz.
10. Global git ayarını değiştirmek. Kimlik gerekirse komut başına `git -c user.name=… -c user.email=…`
    verilir; önceki commit'lerle aynı kimlik `git log -1 --format='%an <%ae>'` ile görülür.
11. Kullanıcı istemeden commit ya da birleştirme yapmak. Doğrudan `master` üzerinde commit etmek:
    önce dal açılır.
12. Ölçmeden "iyileştirme" iddia etmek.

**Ek (24 Eylül 2026):** kullanıcının yerel Claude belleğinde olup buluta taşınmayan iki kural
(ikisi de `CLAUDE.md`'de): (a) her `master` birleştirmesinden önce yedek etiketi + yerel bundle
(§5.4), etiket ve bundle'lar sormadan silinmez; (b) krediye bağlı F3/F4 ancak bütün lokal kalite
işi bitip kod dondurulduktan ve anahtarlar yenilendikten sonra (§7). Bulut oturumundan etiket ya
da `master` push edilemez; birleştirme PR ile ya da yerelde yapılır.
**Düzeltme (24 Eylül 2026, akşam):** `master`da başlayan bir bulut oturumu `master`a push edebilir
(§0.9). Üçüncü kural (`CLAUDE.md` "Asla"): bir bulut routine istemi push hedefini açıkça yeni bir
dal olarak verir ya da hiç push istemez.

### Her değişiklikte

- `scripts/check.py --full` 23/23 kalmalı. Hızlı döngüde `scripts/check.py` ve `pytest` yeterli;
  bitirmeden önce `--full` koşturulur.
  **Düzeltme (24 Eylül 2026):** 24/24 ("Lean erişilebilir" eklendi). Lean'siz ya da Lean'i yarıda
  kaybeden bir koşu bilerek geçmez.
- Lean tarafında her yeni şablon **yanlış cevaplı öğelerde de** koşturulur. Lean FP = 0 ve
  junk-value sertifikası = 0 kalmalı.
- Her bulgu önce ölçümle bulunur, sonra ölçümle doğrulanır, sonra bir teste ya da kalıcı bir kapıya
  bağlanır.
- Kararlar `DECISIONS.md`'ye, gerekçe ve ölçümle birlikte yazılır. Yanlış çıkan eski ifade
  silinmez; "Düzeltme (tarih)" notuyla düzeltilir.
- Raporlar üretilir, elle yazılmaz.

### Commit biçimi

Başlık `alan: özet` biçiminde ve Türkçe: `denetim:`, `F7:`, `raporlar:`, `temizlik:`,
`HANDOFF.md:`. Gövdede ne ölçüldüğü ve nasıl doğrulandığı yazılır. Son satır:

```
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

### Kod stili

- Çevredeki kodun deyimine uy; yorumlar neden'i anlatır ve ölçüme atıf yapar.
- Tip ipuçları ve (paket `__init__` dosyaları dışında yaygın olarak)
  `from __future__ import annotations` kullanılır.
- Hatalar sınıflandırılır: `LeanPrintError`, `UndeclaredSymbolError`, `ClaimNotAValue`,
  `LLMFatalError`.
- Karar kapsamı bayraklarla, makine tarafından okunabilir biçimde verilir.

---

## 11. Tuzaklar

### SymPy

- **SymPy ≥ 1.13'te `Float(3.0) == 3` False döner.** Tam sayılığı `sp.Rational(Float)` ile
  kontrol et; `exact_integer` bunu yapıyor.
- `sp.sqrt` bir sınıf değil fonksiyondur; `isinstance` kontrolünde kullanılamaz. sqrt
  `Pow(…, 1/2)` olarak işlenir.
- `parse_expr` için `rational=True` diye bir parametre yok; `rationalize` dönüşümü kullanılır.
- `sp.evaluate(False)` altında ayrıştırmada `NameError: Add` alınabilir; yapısal ad alanına
  `Add/Mul/Pow` eklendi.
- `is_subset` sonucu hash tohumuna bağlı değişebiliyor; sandbox dışında `PYTHONHASHSEED`
  sabitlenmemişse sonuçlar koşudan koşuya değişebilir.
- **Otomatik sadeleştirme tanımsız noktayı siler:** `x/x` → 1, `sqrt(x)**2` → x, `x**2/x` → x.
  Tanımlılık için daima `parse_as_written` / `Ctx.written_conditions` (karar 30).
- Değerlendirilmiş bir `Add`'in `args` sırası kanoniktir (`1 + x`), sadeleştirmesiz ayrıştırılmış
  olanınki yazıldığı gibidir (`x + 1`). Lean yazıcısı paydayı `as_numer_denom()` ile bastığı için
  aynı payda iki biçimde görünebilir; `field_simp` tam biçimi arar.

### Ayrıştırıcı

- `#` iddialarda yasak: Python tokenizer'ı satırın kalanını yorum sayar (`2*x ### …` → `2*x`).
- Çıplak `open(` yasak ama `Interval.open(1, oo)` serbest.
- LaTeX dalı örtük çarpma yapar (`\frac{zzz}{2}` → `z*z*z/2`). Bu yüzden LaTeX sonucundaki her
  serbest sembolün tanımlı olması şart.
- `5π/6` gibi rakam + unicode sembol biçiminde çarpım açıkça yazılır; genel örtük çarpma kapalı.

### Lean ve Mathlib

- **Junk değerler** ve `first`/`done` tuzağı: §3 karar 12 ve §4. Kural 9 artık bütün şablonların
  ipuçları için genel bir testle korunuyor
  (`test_every_first_chain_in_every_template_hint_closes_with_done`).
- Lean `r.clean` yalnız hata ve `sorry` yokluğudur; uyarılar (kullanılmayan `have`) temizliği
  bozmaz.
- Mathlib türev kombinatörleri noktasal işlem kullanır (`f * g`); kapanışta `Pi.*_apply` ile
  köprülenir.
- `tests/test_f5_lean.py` içindeki Lean gerektiren testler (`_lean()` yardımcısını çağıranlar)
  Lean yoksa **sessizce atlanır**; yazıcı testleri çevrimdışı koşar. Lean'e dokunan bir
  değişiklikten sonra `pytest -rs` ile atlanan sayısına bakın (bugün 1: `test_f5_lean.py:66`,
  "statement out of scope", beklenen) ve `harness.run_lean`'i ayrıca koşturun.
  **Düzeltme (24 Eylül 2026):** atlanan sayısı değişti: Windows'ta 62 (60'ı yalnız POSIX'te koşan bulut betiği
  testleri), Linux'ta (Lean kurulu) 2; nedenleri `-rs` çıktısında. Lean yoksa `check.py --full`
  artık bunu gizlemez: "Lean erişilebilir" kapısı düşer.

### Windows ve araçlar

- Bash aracı Git Bash'tir. **Heredoc `\\` karakterini çökertir**; ters eğik çizgi içeren Python'u
  Write aracıyla dosyaya yazıp öyle çalıştırın.
- Sandbox kullanan her probe gerçek bir dosyada ve `if __name__ == "__main__":` içinde olmalı
  (spawn).
- Scratchpad yolu uzun olduğu için MAX_PATH'e takılabilir; geçici dosya adlarını kısa tutun.
- `ctypes.windll` çağrılarında `restype`/`argtypes` verilmezse tutamaçlar 32 bit'e kırpılır
  (§6.4). Özel `ctypes.WinDLL(..., use_last_error=True)` örneği ve açık prototip kullanın;
  paylaşılan `ctypes.windll` üzerindeki prototipleri değiştirmeyin.
- Python'un `Path.write_text`'i Windows'ta satır sonlarını CRLF'e çevirir (`newline=""` verilmezse). `core.autocrlf=true` olduğu
  için git commit'te normalleştirir, diff'te görünmez; yine de dosyaları Edit aracıyla düzenlemek
  satır sonlarını korur.
- `PYTHONPATH` Windows Python'unda `;` ile ayrılır (`PYTHONPATH=".;src"`), `:` ile değil.
- Bu makinede git kimliği ayarlı değil; commit komut başına kimlikle yapılır (§10).
- (24 Eylül akşamı eklendi) **WSL içinde `df` C:'yi görmez**; sanal diskin (`ext4.vhdx`) kendi
  boyutunu gösterir. WSL'deki büyük kurulumlar `.vhdx` üzerinden C:'yi doldurabilir ve `.vhdx`
  kendiliğinden küçülmez (§0.10). WSL'de büyük bir kurulumdan önce C:'nin boş alanına Windows
  tarafından bakılır.

### Linux ve bulut (24 Eylül 2026'da eklendi)

- Yorumlayıcı `.venv/bin/python`; `PYTHONPATH` `:` ile ayrılır.
- Git Bash'teki heredoc sorunu Linux'ta yok, ama ters eğik çizgili Python yine dosyaya yazılır
  (aynı betik Windows'ta da koşabilsin).
- Yerel Linux'ta `lake env` REPL'i çocuk süreç olarak başlatır; yalnız başlatıcıyı öldürmek
  ~6.9 GB'lık REPL'i yetim bırakır. İstemci süreç grubunu öldürür; elle `lake env` başlatan bir
  probe da aynısını yapmalı.
- REPL ikilisi yokken `lake env` önce projenin eksik bağımlılıklarını klonlar (Mathlib: GB'larca);
  istemci bu yüzden ikiliyi önce kendisi arar.
- Root'un kurduğu Lean'i root olmayan bir kullanıcı çalıştırınca git "dubious ownership" ile
  reddeder ve `lake` paketi silip yeniden klonlar; `setup_lean.sh` root kurulumunda izinleri açar ve
  `safe.directory` kaydeder.
- Bulutta GitHub release dosyaları 403 döner, uv Python indiremez: Lean ve Python araç ref'inden
  gelir (`docs/BULUT.md` §11). `stable` ya da `lake update` ile kurulum yapılmaz.
  **Düzeltme (24 Eylül 2026, ölçüm):** GitHub release dosyası (elan) bulutta 200 döndü; kapalı olan
  `releases.lean-lang.org`, `cache.mathlib.org` ve `releases.astral.sh` (403). Sonuç aynı: Lean,
  Mathlib önbelleği ve Python araç ref'inden gelir.
- (24 Eylül akşamı eklendi) Bulut imajında `python3` 3.11.15; `mathverify` ≥ 3.12 ister. Kanca 3.12
  altını reddeder ve sabit 3.14.6'yı, yoksa `python3.12`/`python3.13`'ü kullanır (§0.5 eki).
- (24 Eylül akşamı eklendi) Claude Code alt süreçlere `ANTHROPIC_BASE_URL` verir (bulutta ve
  masaüstünde); Anthropic SDK'sını kullanan her kod `base_url`'i açıkça vermeli (§0.3 eki).
- Bulutta boşta kalan VM geri alınınca arka plan işi kaybolur; `check.py --full` sürerken oturum
  etkin tutulur.
- Kullanıcının `~/.claude` belleği buluta taşınmaz; kalıcı her bilgi depoya yazılır.
- `.gitattributes`: `*.sh` her yerde LF, `lean/` bayt bayt; Windows checkout'u CRLF kalır.

### Depo ve ölçüm

- **Ana dal `master`, `main` değil.** Bazı araçlar varsayılan olarak `main` varsayar.
- `reports/*.json` git-ignore'lu. `check.py` kapıları bu yerel JSON'lardan okur; temiz bir
  klonda önce harness koşmalıdır.
  **Düzeltme (24 Eylül 2026):** `check.py` her harness'i zaten kendisi koşturuyordu ama çıkış
  kodunu okumuyordu: harness çökünce temiz klonda `check.py` de çöküyor, eski bir JSON varsa eski
  sayılarla geçiyordu. Artık her harness'ten önce onun JSON'u silinir ve çöken ya da rapor yazmayan
  koşunun kapıları FAIL olur (DECISIONS §39); temiz klonda ayrıca bir şey gerekmez. 24 Eylül'deki yedi JSON'un anlık görüntüsü `reports/arsiv/2026-09-24/`
  altında (iki F3 dosyası yeniden üretilemez); bulut kancası eksikleri oradan kopyalar.
- Ana dal GitHub'da da `master` ve depo varsayılanı o (24 Eylül).
- `reports/check_full.log`'u `check.py --full` kendisi yazar; elle yönlendirme gerekmez. Koşu
  başında dosya sıfırlanır, yarıda kalan koşu yarım günlük bırakır.
- `llm_cache/` git'te izleniyor (145 dosya, `828fb95`'ten beri). İçinde 18–19 Eylül F3
  koşularının gerçek API yanıtları var; `run_f3` varsayılan `auto` modda aynı istekleri ücretsiz
  tekrar oynatır. **Testler buna bağlı değil:** `ScriptedClient` ve `tmp_path` kullanıyorlar.
  DECISIONS §18'deki "testler bunu kullanır" ifadesi yalnız önbellek anlamlarının testine
  (`tests/test_f3_pipeline.py`) karşılık geliyor.
- `check.py --full` ~25–70 dk sürer. Adversaryal tarama tek başına 21–58 dk (23 Eylül'de üç
  koşu: 1245, 2249, 3490 s; farkın çoğu makineden, ~%12–15'i tanımlılık kancasından); arka planda
  koşturun.
- `soundness_fuzz`'a yeni bir "eşdeğer" varyant eklerken kâhinin kendisinin kesin olduğundan emin
  olun (§4: 30 basamaklı ondalık hatası).
- `DECISIONS.md` §2 ve §3.9 bilerek Faz 1 anlık görüntüsüdür (180 öğe, "LLM yok"); güncel durum
  README ve bu belgededir.

### LLM ve maliyet

- Bir katmanda `except LLMError` yazmak `LLMFatalError`'ı yakalamaz ve yakalamamalı. Faturalama
  hatasını yutan bir kod yazmayın.
- `run_f3`'ü `--max-cost` olmadan gözetimsiz koşturmayın.
- 42 örnek, eşik 9 ve onarım bütçesi 2, Claude'un davranışına bakılarak seçildi. Başka bir modelle
  yalnız mekanik hataları düzeltin; istem metnine ve eşiklere dokunmayın.

---

## 12. Açık sorular

Kullanıcıdan onay ya da girdi bekleyen noktalar:

1. ~~`yerel-kalite-2026-09-23` birleştirilsin mi?~~ Yapıldı (23 Eylül, yedeği §5.4'te).
2. **Yedekler (iki etiket, iki bundle) ne zaman silinebilir?** Sormadan silinmez.
   *Ek (24 Eylül 2026):* etiketler GitHub'da da var; bundle'lar yalnız yerel makinede
   (`C:\Users\kullanici\mathverify-yedek\`). `bulut-2026-09-24` birleştirmesinin yedeği de eklenecek.
   *Düzeltme (24 Eylül 2026, akşam):* eklendi, ama birleştirmeden sonra: `yedek/master-2026-09-24`
   → `23d7c6b` ve `mathverify-master-23d7c6b-2026-09-24.bundle` (§0.9, §5.4). Artık üç etiket, üç
   bundle; soru aynı.
3. **Anthropic bakiyesi ne zaman ve ne kadar yüklenecek?** F3'ün kalanı için ~10 $, F4 için
   ~15–25 $ tahmini var. *Kısmen cevaplandı (23 Eylül):* F3/F4 bütün lokal iş bitince koşulacak
   (§7).
4. **Gerçek AI çözücü çıktıları nereden gelecek?** Hangi model ya da uygulama, kaç çözüm? Bu adım
   ertelendi.
5. **Uzak depo, CI ve LICENSE:** nerede (GitHub mı), hangi lisansla, kimin hesabında?
   *Kısmen cevaplandı (24 Eylül 2026):* uzak depo kullanıcının hesabında özel GitHub deposu
   `wqedwad/asd` (§0.1). **Lisans ve CI hâlâ açık.**
6. **`tyt-prob-018` kuralı:** F4 ölçüldükten sonra "sertifika kritiği ezer" kuralı daraltılsın mı?
   Karar ölçüme bağlı.
7. **API anahtarları yenilensin mi?**
   *Ek (24 Eylül 2026):* anahtarlar artık özel depoda da (`.env`, kullanıcı kararı, §0.3). Karar:
   kredili F3/F4 koşularından önce yenilenir; ne zaman yapılacağı kullanıcıya bağlı.
8. **Çözücü sembolü adımları (§6.2):** bu sınır kabul mü, yoksa yapısal formata sembol tanımı
   eklensin mi?
9. ~~İsteğe bağlı Lean şablonları~~: 23 Eylül'de kullanıcının talimatıyla yapıldı (karar 31).
10. **Başka sağlayıcıyla ölçüm** (GPT/Gemini, `set_client_override` ile) istenir mi? Ölçüm
    sonuçları o konfigürasyona özgü kalır.
11. **Uygulamanın adı ve ayrıntıları** (§1): ne depoda ne şartnamede geçiyor.
12. ~~Tek seferlik betikler~~ ve 13. ~~ölü `nsimplify` dalı~~: 23 Eylül'de, "geri kalan lokal
    işlemleri yap" talimatıyla yapıldı (DECISIONS §33). Betikler silinmedi, `scripts/dev/`e
    taşındı; yalnız `diag_sandbox.py` silindi (testler onu tamamen kapsıyor).
14. **Ekstremum/türev/seride tanımsız nokta:** çekimser kalmak yeterli mi, yoksa ekstremum
    tanımsız noktalar dışlanarak mı hesaplansın (§6.8)?
15. **Eski araç ref'i** (24 Eylül'de eklendi): `refs/arac/bulut-v2` doğrulandıktan sonra
    `refs/arac/bulut-v1` silinsin mi? Sormadan silinmez.
    *Ek (24 Eylül 2026, akşam):* v2 bulutta doğrulandı (5/5 SHA256 OK, §0.8) ve v1'in bütün
    içeriğini taşıyor. **Soru hâlâ açık:** v1 geçmiş için duruyor; kullanıcı karar verene dek
    silinmez.
16. **Depo ileride herkese açılacak ya da paylaşılacak mı?** Açılacaksa önce anahtarlar yenilenir
    ve `.env` geçmişten temizlenir (§0.3).
