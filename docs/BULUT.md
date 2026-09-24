# Bulutta çalışma — Claude Code on the web el kitabı

> **Yazıldığı tarih: 24 Eylül 2026.** Kaynaklar: resmî belgeler
> (`code.claude.com/docs/en/cloud-environments` ve `claude-code-on-the-web`, 24 Eylül'de okundu)
> ve bu depodaki betikler (`scripts/cloud/`, `scripts/setup_lean*.sh`, `scripts/fetch_artifacts.sh`).
> Bu belge yazılırken **bulutta hiç oturum açılmamıştı.** Bulut davranışı hakkındaki her şey ya
> resmî belgeden ya da WSL içinde bulut düzeninin taklit edilmesinden (temiz `HOME`, `/opt` önekli
> kurulum, 4 CPU'ya sabitlenmiş) geliyor. İlk oturumda ölçülecekler §12'de ve
> **[DOĞRULANMADI]** işaretli.

Kalıcı kurallar `CLAUDE.md`'de, güncel durum `HANDOFF.md`'de (§0 bulut özeti). Bu belge yalnız
bulut ortamını anlatır.

## 1. Özet

| Ne | Nasıl | Kim, ne zaman |
|---|---|---|
| Depo | Özel GitHub deposu `https://github.com/wqedwad/asd` (`origin`), varsayılan dal `master` | bir kez kuruldu (24 Eylül) |
| Depoya erişim | Claude GitHub App bu depoya kurulu olmalı | kullanıcı, bir kez |
| Ortam kurulumu (Python 3.14.6, uv önbelleği, Lean + Mathlib + REPL) | ortamın "Setup script" alanı → `scripts/cloud/setup_env.sh` (root) | platform, anlık görüntü eskiyince (~7 gün) |
| Oturum hazırlığı (`.venv`, rapor JSON'ları, Lean ortam değişkenleri) | `.claude/settings.json` SessionStart kancası → `scripts/cloud/session_start.sh` | her oturum başında ve devamında, kendiliğinden |
| API anahtarları | depodaki `.env` (kullanıcı kararı, §10) | hiçbir şey gerekmez |

Kullanıcının kendi makinesindeki `~/.claude` belleği buluta **taşınmaz**. Bu yüzden oturumun
bilmesi gereken her şey depodadır: `CLAUDE.md`, `HANDOFF.md`, `DECISIONS.md` ve bu belge.

## 2. Ön koşullar (bir kez)

1. **Claude GitHub App** depoya erişebilmeli. Özel depolar için şart:
   `https://github.com/apps/claude/installations/new` → `wqedwad/asd` seçilir.
2. **Varsayılan dal `master`.** 24 Eylül'de `git ls-remote origin` ile görüldü: `HEAD` =
   `refs/heads/master` = `23d7c6b`. Kurulum betiğinin klon yedeği (§3.2) varsayılan dalı çeker; bu
   yüzden `scripts/cloud/` `master`a birleştirilmeden önce bulut denenecekse ortam değişkenlerine
   `MATHVERIFY_REPO_REF=bulut-2026-09-24` eklenir (§3.3).
3. `claude.ai/code` → ortam (environment) oluşturulur ya da düzenlenir: ağ (§3.1), kurulum betiği
   (§3.2), ortam değişkenleri (§3.3).

## 3. Ortam ayarları

### 3.1 Ağ

- **Varsayılan "Trusted" yeterli.** PyPI ve GitHub (GitHub'ın vekili üzerinden) açık. Lean araç
  zinciri, elan, Mathlib önbelleği ve CPython internetten değil depodaki araç ref'inden gelir
  (§11). Bu yüzden Trusted listesinde olmayan şu adreslere gerek yok: `releases.lean-lang.org`,
  `cache.mathlib.org`, `releases.astral.sh`.
- GitHub vekili, oturuma bağlı olmayan depoların **release dosyalarına 403** döndürür
  (`github.com/leanprover/...` indirmeleri bu yüzden bulutta çalışmaz). Araç ref'i bu yüzden var.
- **F3/F4 (kredili ölçüm) koşulacağı zaman:** Meta ailesi `api.meta.ai` ister ve bu adres Trusted
  listesinde yok. Ağ ayarı **Custom** yapılır, "also include default list" işaretlenir ve
  `api.meta.ai` eklenir. `api.anthropic.com` resmi belgede varsayılan Trusted listesinin
  "Anthropic services" başlığında yazılı (24 Eylül'de okundu); bulut oturumundan erişim
  **[DOĞRULANMADI]**, F3'ten önce ölçülür.

### 3.2 Kurulum betiği ("Setup script")

Alan root olarak, Claude Code başlamadan **önce** çalışır. Sıfırdan farklı bir çıkış oturumu
engeller; ~5 dakikada bitmesi önerilir; ortaya çıkan dosya sistemi anlık görüntü olarak saklanır
ve ~7 gün sonraki oturumlarda yeniden kullanılır.

Alana `scripts/cloud/setup_env.sh`'in başlık yorumundaki önyükleyici yapıştırılır (betiğin
kendisi de yapıştırılabilir, ama önyükleyici depodaki güncel kopyayı çalıştırır). Betikten
birebir alıntı:

```bash
#!/bin/bash
S=
for d in "${CLAUDE_PROJECT_DIR:-}" /home/*/* /root/* /workspace /workspace/* /tmp/*; do
  if [ -f "$d/scripts/cloud/setup_env.sh" ] && grep -qs 'wqedwad/asd' "$d/.git/config"; then
    S="$d/scripts/cloud/setup_env.sh"; break
  fi
done
if [ -z "$S" ]; then
  rm -rf /tmp/mv-boot
  GIT_TERMINAL_PROMPT=0 git clone -q --depth 1 ${MATHVERIFY_REPO_REF:+--branch "$MATHVERIFY_REPO_REF"} \
    https://github.com/wqedwad/asd /tmp/mv-boot && S=/tmp/mv-boot/scripts/cloud/setup_env.sh
fi
if [ -n "$S" ]; then bash "$S"; else echo "mathverify: setup_env.sh not found"; fi
rm -rf /tmp/mv-boot
exit 0
```

`setup_env.sh` ne yapar (ayrıntı betiğin başlığında):

1. Depoyu bulur (`CLAUDE_PROJECT_DIR`, kendi konumu, olası kökler; yoksa sığ klon).
2. Araç ref'ini çeker ve SHA256 ile doğrular (`scripts/fetch_artifacts.sh`, §11).
3. CPython 3.14.6'yı `/opt/python3.14`'e açar.
4. Paralel olarak: `requirements.lock` ile uv önbelleğini ısıtır (depo checkout'una hiçbir şey
   yazmadan, geçici bir kopyadan) ve Lean kurulumunu yapar (`scripts/setup_lean.sh` ardından
   `scripts/setup_lean_repl.sh`, ikisi de duman testi geçmezse düşer).
5. Her şeyi oturum kullanıcısının okuyabileceği hâle getirir (oturum kullanıcısı kurulum anında
   bilinmiyor), root ise `/etc/profile.d/mathverify.sh` yazar.
6. **Her durumda 0 ile çıkar**; hatayı günlüğe ve `setup_env.status`'a yazar (§6). Lean kısmı
   başarısız olursa oturum kancası onu arka planda yeniden dener.

Bir şey zaten kuruluysa (parmak izleri tutuyorsa) atlanır: Python sürümü, `requirements.lock` +
`pyproject.toml` + yorumlayıcı parmak izi, `lean/` altındaki sabit dosyaların parmak izi
(`lean.done`).

### 3.3 Ortam değişkenleri

**Gerekli değişken yok.** Anahtarlar `.env`'den okunur (§10). İsteğe bağlı olanlar:

| Değişken | Ne zaman |
|---|---|
| `MATHVERIFY_REPO_REF` | Kurulum betiğinin klon yedeği varsayılan dal dışında bir dalı çeksin (ör. birleştirmeden önce `bulut-2026-09-24`) |
| `MATHVERIFY_SKIP_LEAN=1` | Kanca Lean kurulumunu arka planda **başlatmasın** (var olanı yine bildirir) |
| `MATHVERIFY_ARTIFACT_REF` | Varsayılan araç ref'i dışında bir sürüm (`refs/arac/bulut-vN`) |

## 4. Oturum başında ne olur

| | Kurulum betiği (`setup_env.sh`) | SessionStart kancası (`session_start.sh`) |
|---|---|---|
| Nerede tanımlı | claude.ai ortam ayarı | depo: `.claude/settings.json` (`startup\|resume`, zaman aşımı 600 s) |
| Ne zaman | Claude başlamadan önce; anlık görüntü eskiyince | her oturum başında ve devamında; **yerelde de** tetiklenir ama `CLAUDE_CODE_REMOTE=true` değilse hiçbir şey yapmadan çıkar |
| Kim olarak | root | oturum kullanıcısı **[DOĞRULANMADI]** |
| Ne yapar | §3.2 | aşağıda |
| Çıkış | her zaman 0 | her zaman 0 |

Kanca sırasıyla:

1. Python seçer: `/opt/python3.14` (kurulum betiğinden), yoksa `python3.14`, yoksa sistem
   `python3` (Ubuntu 24.04'te 3.12; durum bloğunda "YEDEK" diye uyarır).
2. `.venv`'i `requirements.lock` + `--no-deps -e .` ile kurar. Önce çevrimdışı (ısıtılmış uv
   önbelleği), olmazsa çevrimiçi. Damga (`requirements.lock`, `pyproject.toml`, yorumlayıcı yolu ve
   sürümü) değişmediyse atlar.
3. `reports/arsiv/2026-09-24/` içindeki JSON'lardan `reports/`ta **eksik** olanları kopyalar,
   var olanın üstüne yazmaz.
4. Lean: kurulum hazırsa (`lean.done` var ve parmak izi `lean/` ile aynı) ortam değişkenlerini
   `CLAUDE_ENV_FILE` üzerinden oturuma verir ve `~/.elan`, `~/mathverify-lean`, `~/repl`
   bağlantılarını kurar. Kurulum yoksa ya da yarım kalmışsa `setup_env.sh --lean-only`'yi arka
   planda başlatır. `lean.done` yalnız REPL duman testinden sonra yazılır; duman testinden önce
   bırakılmış bir REPL ikilisi "hazır" sayılmaz.
5. Oturum bağlamına Türkçe bir durum bloğu basar:

```
[mathverify bulut oturumu — session_start.sh, N s]
- Python: 3.14.6 (/opt/python3.14/bin/python3.14)
- .venv: HAZIR (değişiklik yok); komutlar .venv/bin/python ile (PYTHONUTF8=1) çalışır, ...
- Lean: HAZIR (/opt/repl/.lake/build/bin/repl)
- Günlükler: ...
- Önce HANDOFF.md, sonra docs/BULUT.md okunur.
```

Lean satırının olası değerleri: **HAZIR**; **KURULUYOR** (başka bir kurulum sürüyor ya da kanca
arka planda başlattı; bitene dek Lean testleri atlanır ve `check.py --full`'da Lean kapıları
düşer); **HAZIR ama … güncelleniyor** (`lean/` sabitleri değişmiş, eski kurulum kullanılırken
yenisi kuruluyor); **ESKİ** (güncelleme başlatılamadı); **YOK**. Önceki kurulum başarısızsa
`setup_env.status` satırı da basılır.

Ölçüm (24 Eylül, WSL içinde yerel Linux, root değil): kanca ilk koşuda 2.5 s, ikinci koşuda
85 ms; Windows'ta Git Bash altında 0 bayt çıktı, çıkış 0, ~0.3 s.

## 5. Dizin düzeni ve ortam değişkenleri

Önek `MATHVERIFY_OPT` (varsayılan `/opt`). `/opt` oturum kullanıcısı için yazılabilir değilse
kanca kendi kurulumunu `~/.mathverify-opt` altına yapar.

| Yol | İçerik |
|---|---|
| `/opt/python3.14/` | CPython 3.14.6 (python-build-standalone 20260728) |
| `/opt/uv-cache/` | `requirements.lock` ile ısıtılmış uv önbelleği |
| `/opt/elan/` | elan 4.2.4 + araç zinciri `leanprover--lean4---v4.34.0` |
| `/opt/mathverify-lean/` | Mathlib bağımlı proje (dosyalar `lean/`'dan kopyalanır) |
| `/opt/repl/` | REPL `646a773`, ikili `/opt/repl/.lake/build/bin/repl` |
| `/opt/arac/` | Araç ref'inin açıldığı geçici dizin; kurulum başarılıysa silinir, başarısızsa yeniden deneme için tutulur |
| `/opt/mathverify-logs/` | günlükler ve durum dosyaları (§6) |
| `/etc/profile.d/mathverify.sh` | `MATHVERIFY_OPT`, `ELAN_HOME`, `MATHVERIFY_LEAN_PROJECT`, `MATHVERIFY_LEAN_REPL`, `PATH` (yalnız root kurulumunda ve Lean hazırsa yazılır) |
| `~/.cache/mathlib/` | Mathlib `.ltar` önbelleği (kurulumu yapan kullanıcının `HOME`'u; root için `/root/.cache/mathlib`) |

| Değişken | Varsayılan | Anlamı |
|---|---|---|
| `MATHVERIFY_OPT` | `/opt` | kurulum öneki |
| `ELAN_HOME` | `$HOME/.elan` (bulutta `/opt/elan`) | elan evi; `lean_client` `PATH`'e `${ELAN_HOME:-$HOME/.elan}/bin` ekler |
| `MATHVERIFY_LEAN_PROJECT` | `~/mathverify-lean` (bulutta `/opt/mathverify-lean`) | Mathlib projesi |
| `MATHVERIFY_LEAN_REPL` | `~/repl/.lake/build/bin/repl` (bulutta `/opt/repl/...`) | REPL ikilisi |
| `MATHVERIFY_ARTIFACT_DIR` | `fetch_artifacts.sh`: `$HOME/.cache/mathverify/arac`; `setup_env.sh`: `/opt/arac` | araçların açıldığı dizin; `setup_lean.sh` burada bulduğunu çevrimdışı kurar |
| `MATHVERIFY_ARTIFACT_URL` | `origin` uzak adresi | araç ref'inin çekileceği depo |
| `MATHVERIFY_ARTIFACT_REF` | `refs/arac/bulut-v2` | araç ref'i |
| `MATHVERIFY_ARTIFACT_SRC` | — | `parts/` + `SHA256SUMS.full` içeren yerel dizin (tamamen çevrimdışı kurulum ve test için) |
| `MATHVERIFY_SKIP_LEAN` | — | `1`: kanca Lean kurulumu başlatmaz |
| `MATHVERIFY_REPO_URL` / `MATHVERIFY_REPO_REF` | `https://github.com/wqedwad/asd` / uzak varsayılan dal | kurulum betiğinin klon yedeği |
| `MATHVERIFY_PROFILE_D` | `/etc/profile.d` | `mathverify.sh`'in yazıldığı yer |
| `MATHVERIFY_HOOK_PREFIXES` | — | kancanın önek listesini değiştirir (iki nokta ile ayrılmış); yalnız testler için |
| `MATHLIB_CACHE_DIR`, `XDG_CACHE_HOME` | `$HOME/.cache/mathlib` | Mathlib `.ltar` önbelleği (Mathlib'in kendi kuralıyla çözülür) |
| `CLAUDE_CODE_REMOTE` | platform verir | `true` değilse kanca hiçbir şey yapmaz |
| `CLAUDE_PROJECT_DIR`, `CLAUDE_ENV_FILE` | platform verir | depo kökü; oturumun sonraki komutlarına aktarılacak değişkenlerin dosyası |
| `UV_PYTHON_DOWNLOADS` | kanca `never` yapar | uv Python indirmeye çalışmasın (`releases.astral.sh` kapalı) |

## 6. Günlükler, durum dosyaları ve yeniden deneme

`/opt/mathverify-logs/` (ya da kullanılan önekin `mathverify-logs/` dizini):

| Dosya | İçerik |
|---|---|
| `setup_env.status` | tek satır: `OK` ya da `FAILED`, başarısız aşamalar, aşama süreleri, Python ve Lean durumu, toplam süre |
| `setup_env.log` | zaman damgalı ana günlük; başarısız aşamanın son 25 satırı buraya da kopyalanır |
| `fetch_artifacts.log`, `python.log`, `uv_prewarm.log`, `setup_lean.log`, `setup_lean_repl.log` | aşama başına tam çıktı |
| `lean.done`, `uv-prewarm.done` | tamamlanan kurulumun parmak izi |
| `setup_env.lock`, `setup_env.pid` | aynı anda tek kurulum; kanca "kuruluyor"u "yok"tan böyle ayırır |
| `setup_env.nohup.log` | kancanın arka planda başlattığı kurulumun çıktısı |
| `session_start.log`, `venv.log` | kancanın ve `.venv` kurulumunun günlüğü |

Yeniden deneme:

```bash
cat /opt/mathverify-logs/setup_env.status
tail -n 60 /opt/mathverify-logs/setup_env.log
bash scripts/cloud/setup_env.sh --lean-only        # uzun sürer: arka planda koşturun
bash scripts/cloud/setup_env.sh --python-only      # yalnız Python + uv önbelleği
# /opt oturum kullanıcısı için yazılabilir değilse (kancanın kendi seçtiği önek):
MATHVERIFY_OPT="$HOME/.mathverify-opt" bash scripts/cloud/setup_env.sh --lean-only
```

Aynı anda tek kurulum koşar; ikinci çağrı kilidi görür ve hiçbir şey yapmadan çıkar.

Kurulum dakikalar sürer; bu sırada oturum etkin tutulur (§8).

## 7. Oturumu doğrulama

```bash
bash scripts/lean_status.sh
PYTHONUTF8=1 .venv/bin/python -c "from mathverify.formal.lean_client import lean_available; print(lean_available())"
PYTHONUTF8=1 .venv/bin/python -m pytest tests -q -rs
PYTHONUTF8=1 .venv/bin/python scripts/check.py
PYTHONUTF8=1 .venv/bin/python scripts/check.py --full     # uzun: arka planda, oturum etkin
```

Beklenen: `lean_available()` → `True`; `pytest -rs` çıktısında Lean yüzünden atlanan test yok
(atlama nedeni "Lean/Mathlib toolchain not available" olmamalı); hızlı `check.py` 12/12;
`check.py --full` 24/24 ve "Lean erişilebilir" kapısı "evet". Lean yoksa ya da tarama sırasında
kaybolursa Lean kapıları bilerek **düşer** (DECISIONS §39); 24/24 görmeden Lean ölçüldü denmez.

Bulut dışında ölçülen karşılaştırma sayıları (24 Eylül): yerel Linux (WSL, Lean kurulu) testler
«SAYI-GÜNCELLENECEK» passed / «SAYI-GÜNCELLENECEK» skipped; yerel `check.py --full`
«SAYI-GÜNCELLENECEK»/24 (ayrıntı HANDOFF §0.6). Bulutta ölçülenler §12'ye yazılır.

## 8. Sınırlar

- **Makine:** Ubuntu 24.04 x86_64, ~4 vCPU, 16 GB RAM, 30 GB disk. Lean kurulumu bunun ~12–13
  GB'ını kaplar (WSL'deki uçtan uca kurulumda ~12 GB ölçüldü; araçların açıldığı geçici dizin
  kurulum sırasında bunun üstüne biner). Bir Lean REPL'i ~6.9 GB bellek tutabilir (WSL ölçümü);
  16 GB'lık makinede aynı anda iki Lean taraması koşturulmaz **[DOĞRULANMADI: bulutta ölçülmedi]**.
- **Boşta kalan VM geri alınır ve arka plandaki kabuk işi kaybolur.** `check.py --full`
  (Windows'ta ~25–70 dk; bulutta «SAYI-GÜNCELLENECEK») ya da Lean kurulumu sürerken oturum etkin
  tutulur. `check.py --full` günlüğü `reports/check_full.log`a koşu sırasında yazar; yarıda kalan
  koşu yarım günlük bırakır.
- **Git:** bulut oturumu yalnız **kendi dalına** push edebilir. Etiket, `master` ve başka dallar
  push edilemez. `master`a birleştirme GitHub'da PR ile ya da yerel checkout'ta yapılır;
  birleştirmeden önceki yedek (etiket + bundle) de yerelde alınır (§9).
- **Ağ:** §3.1. uv Python indiremez; Python yalnız araç ref'inden gelir.
- **Anlık görüntü** ~7 gün sonra eskir; kurulum betiği o zaman baştan koşar.
- **Bellek dosyaları:** `~/.claude` taşınmaz; kalıcı her bilgi depoya yazılır.

## 9. Buluttan yerele ve birleştirme

- `claude --teleport <oturum-id>` bir bulut oturumunu yerel checkout'a (`C:\Users\kullanici\mathverify`)
  çeker. Öncesinde bulut oturumunun dalı commit edilip push edilmiş olmalı.
- Birleştirme akışı: bulut oturumu kendi dalını push eder → PR ya da yerelde `git fetch` →
  **birleştirmeden önce yerelde yedek**: `yedek/master-YYYY-MM-DD[-N]` etiketi ve
  `C:\Users\kullanici\mathverify-yedek\` altına `git bundle create ... --all` (HANDOFF §5.4) → `master`
  fast-forward → etiket ve `master` yerelden push edilir. Yedekler kullanıcıya sormadan silinmez.
- Birleştirme yalnız kullanıcı isterse yapılır (CLAUDE.md).

## 10. Gizli bilgiler

- `.env` bu **özel** depoda izlenir (kullanıcının açık kararı, 24 Eylül 2026; DECISIONS §35).
  Bulut oturumu anahtarları olduğu gibi kullanır. Değerler hiçbir zaman ekrana, belgeye ya da
  günlüğe yazılmaz; varlık kontrolü değer basmadan yapılır:
  `grep -q '^ANTHROPIC_API_KEY=.' .env && echo var || echo yok`.
- `python-dotenv` `.env`'i `override=False` ile ve yalnız projenin Python süreçlerinde yükler
  (`llm/__init__.py`). Claude Code'un kendi kimliğine karışmaz. Ters yönü de var: kabukta aynı adla
  bir değişken zaten tanımlıysa `.env`'deki **değil o** kullanılır. Bulut kabuğunda
  `ANTHROPIC_API_KEY` tanımlı mı **[DOĞRULANMADI]**; F3'ten önce değer basmadan kontrol edilir:
  `test -n "${ANTHROPIC_API_KEY:-}" && echo tanımlı || echo yok`.
- Kredili F3/F4 koşularından önce anahtarlar yenilenir, `.env` güncellenip commit edilir (HANDOFF
  §7, §6.9).
- Depo herkese açılacak ya da başkasıyla paylaşılacaksa **önce** anahtarlar yenilenir ve `.env`
  geçmişten temizlenir (ör. `git filter-repo`); yalnız son commit'ten silmek yetmez.

## 11. Araç ref'i (`refs/arac/bulut-vN`)

Bulutta GitHub release dosyaları 403 döndürdüğü için kurulumun internetten indirdiği her şey bu
depoda, **dal olmayan** bir git ref'inde durur. Normal `git clone` onu indirmez (ölçüldü, 24 Eylül:
klon 3 s, 1.2 MB); yalnız `scripts/fetch_artifacts.sh` çeker: önce geçici, ayrı bir depoya sığ
(`--depth 1`) olarak, checkout'un depoya özgü `http.*`/`credential.*`/`url.*` ayarlarını taşıyarak;
bu olmazsa checkout'un kendi uzak ayarı ve kimlik bilgileriyle, ama nesneleri geçici depoya yazarak
(checkout'a ref, `FETCH_HEAD` ya da nesne eklenmez).

| Sürüm | İçerik |
|---|---|
| `refs/arac/bulut-v1` (24 Eylül'de push edildi) | Lean araç zinciri `lean-4.34.0-linux.tar.zst` (580 367 391 B; `bin/lean` ve `bin/lake` SHA256'ları WSL kurulumuyla aynı), elan 4.2.4 (`elan-x86_64-unknown-linux-gnu.tar.gz`), CPython 3.14.6 (`cpython-3.14.6-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz`, python-build-standalone 20260728), Mathlib `.ltar` önbelleği (`mathlib-cache-5ed2965.tar`, 8906 dosya) |
| `refs/arac/bulut-v2` (`fetch_artifacts.sh`'in varsayılanı) | v1 + Lake paketlerinin (`lake-manifest.json`'daki revizyonlar) ve REPL'in sabit kaynakları, böylece kurulum GitHub'dan klon yapmaz. Boyut: «SAYI-GÜNCELLENECEK» |

Biçim (`fetch_artifacts.sh`'in beklediği): kökte `SHA256SUMS.full` (her birleştirilmiş dosyanın
SHA256'sı; dosya adında `/` yok), `parts/<ad>.part-<rakamlar>` parçaları (49 MiB). Betik parçaları
sırayla birleştirir, `sha256sum -c --strict` ile doğrular, hedefe ancak doğrulama geçince taşır ve
`.source` işaretçisi yazar; aynı kaynaktan ikinci çağrı hiçbir şey indirmez.

```bash
bash scripts/fetch_artifacts.sh /tmp/arac                              # varsayılan ref
MATHVERIFY_ARTIFACT_REF=refs/arac/bulut-v1 bash scripts/fetch_artifacts.sh /tmp/arac-v1
MATHVERIFY_ARTIFACT_SRC=/yol/parts-dizini bash scripts/fetch_artifacts.sh /tmp/arac   # çevrimdışı
```

**Kural:** bir ref asla yerinde yeniden yazılmaz; yeni içerik yeni ad alır (`bulut-v3`, …). Eski
ref'ler kullanıcıya sormadan silinmez.

**Yeni bir Lean sürümü için yeniden üretme** (ağı açık bir Linux/WSL makinesinde; bu tarif depoda
betik olarak yok, adımları `fetch_artifacts.sh` ve `setup_lean.sh`'in beklediği adlardan
çıkarıldı **[DOĞRULANMADI: uçtan uca yeniden üretilmedi]**):

1. WSL'de yeni sürümü kur, ölç, `lean/` dosyalarını ve `lean/PINS`'i oradan bayt bayt kopyala
   (`lean/README.md`).
2. `lean/PINS`'teki adlarla dosyaları topla: `lean-<sürüm>-linux.tar.zst`, `elan-x86_64-unknown-linux-gnu.tar.gz`,
   `cpython-<sürüm>-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz`,
   `mathlib-cache-<MATHLIB_REV ilk 7>.tar` (tek üst dizin `mathlib/`, içinde `.ltar`'lar) ve
   varsa paket kaynakları.
3. `SHA256SUMS.full`'u yaz, her dosyayı 49 MiB'lık `parts/<ad>.part-NNN` parçalarına böl.
4. Ayrı bir çalışma dizininde bu ağacı tek bir öksüz (orphan) commit yap ve
   `git push origin <commit>:refs/arac/bulut-vN` ile gönder.
5. `fetch_artifacts.sh`'in varsayılan ref'ini güncelle; önce `MATHVERIFY_ARTIFACT_SRC` ile
   çevrimdışı, sonra ref'ten temiz `HOME`'lu bir uçtan uca kurulumla doğrula (24 Eylül ölçümü:
   141 s, araç zinciri/`.ltar` indirmesi 0, manifest aynı, mathlib HEAD = `5ed2965`, 17 738
   dosyalık araç zinciri ağacı WSL kurulumuyla aynı).

## 12. İlk bulut oturumunda ölçülecekler [DOĞRULANMADI]

Bunların hiçbiri henüz ölçülmedi. Sonuçlar HANDOFF §0'a ve buraya "Düzeltme" ya da ölçüm notu
olarak yazılır.

- [ ] Oturum kullanıcısı ve `HOME` (`id -un; echo $HOME`); root mu?
- [ ] Kurulum betiği çalışırken checkout nerede (`setup_env.log`'daki `repository:` satırı);
      `CLAUDE_PROJECT_DIR` tanımlı mıydı, yoksa klon yedeğine mi düştü?
- [ ] `refs/arac/*` çekimi GitHub vekilinden geçiyor mu (`fetch_artifacts.log`)? Paket kaynakları
      v2'den mi geldi, yoksa GitHub'dan klon denendi mi (`setup_lean.log`)?
- [ ] Kurulum betiğinin süresi (`setup_env.status`, `total=`), ~5 dakikalık öneriye göre:
      «SAYI-GÜNCELLENECEK».
- [ ] Anlık görüntü `/opt`'u koruyor mu: ikinci oturumda kanca Lean'i "HAZIR" buluyor ve kurulum
      betiği her şeyi atlıyor mu?
- [ ] Platformun hazır araçları: `check-tools` çıktısı; `python3 --version`, `uv --version`
      (uv yoksa kurulum betiği PyPI'den kurar).
- [ ] Kancanın süresi (durum bloğunun başlığı): ilk oturum «SAYI-GÜNCELLENECEK», sonraki
      «SAYI-GÜNCELLENECEK».
- [ ] `pytest -q -rs` sayıları ve atlama nedenleri; bellek sınırı testi Linux'ta (`RLIMIT_AS`)
      atlanıyor mu?
- [ ] Kabukta `ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN` tanımlı mı (yalnız adlar:
      `env | cut -d= -f1 | grep -i anthropic`). Tanımlıysa `.env`'deki anahtarı gölgeler
      (`load_dotenv(override=False)`), F3'ten önce çözülür. `api.anthropic.com` erişilebilir mi?
- [ ] `check.py` (hızlı), sonra `check.py --full` (arka planda, oturum etkin): sonuç ve süre
      «SAYI-GÜNCELLENECEK».
- [ ] `git push` yalnız oturumun kendi dalına gidiyor mu, etiket push'u gerçekten reddediliyor mu?
