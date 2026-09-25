# Bulutta çalışma — Claude Code on the web el kitabı

## Senin yapman gerekenler (kullanıcı, bir kez; 24 Eylül 2026)

claude.ai'de bir kez yapılacak ayarlar; gerisini depo yapar (kurulum betiği + oturum kancası).
Sayılar 24 Eylül'deki tek seferlik routine oturumunun ölçümüdür (§12,
`docs/bulut_tani_2026-09-24.md`).

1. **Ağ: varsayılan "Trusted" olduğu gibi kalır.** Kurulumun, testlerin ve Anthropic ailesinin
   eriştiği her adres, ağ ayarına dokunulmamış (varsayılan Trusted) ortamda açık ölçüldü: GitHub
   (araç ref'i dahil), PyPI, `api.anthropic.com` (tablo §3.1). Tek istisna kredili F3/F4 ölçümü: Meta ailesi `api.meta.ai`
   ister ve vekil bu adresi 403 ile kesiyor. O koşudan önce ağ **Custom** yapılır, "also include
   default list" işaretlenir ve `api.meta.ai` eklenir.
2. **Kurulum betiği:** claude.ai/code → ortam (environment) → "Setup script" alanına aşağıdaki
   önyükleyici olduğu gibi yapıştırılır. `scripts/cloud/setup_env.sh`'in başlık yorumundan birebir
   alıntıdır: depodaki güncel `setup_env.sh`'i bulup çalıştırır ve oturumu hiçbir durumda engellemez
   (her zaman 0 ile çıkar).

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

   Beklenen süre: aynı kurulumun Lean kısmı (`setup_env.sh --lean-only`, kancanın başlattığı yol)
   routine oturumunda **195 s** sürdü (çekim 55 s, Python 1 s, `setup_lean` 119 s, REPL 19 s), yani
   ~5 dakikalık yönergenin altında. Alanın kendisinden (uv önbelleği ısıtması dahil) henüz hiç
   koşmadı. Sonuç `/opt/mathverify-logs/setup_env.status`'ta (§6). Betik tanımlanmasa da kanca aynı
   kurulumu arka planda başlatır (routine oturumunda böyle oldu), ama o zaman kurulum oturumun
   içinde koşar ve bitene dek Lean kullanılamaz.
3. **Ortam değişkeni gerekmez** (§3.3). Anahtarlar depodaki `.env`'den gelir (§10).
   **Düzeltme (24 Eylül 2026, gece, ölçüm):** kurulum betiği alanından ilk gerçek koşu araç ref'ini
   çekemedi: betik, Claude Code'un GitHub vekili bağlanmadan önce koştuğu için özel depo 401 döndü
   (§3.2, HANDOFF §0.11). Değişken yine zorunlu değil (kanca Lean'i her yeni sohbette ~3 dk'da
   kurar), ama anlık görüntünün Lean'i taşıması için **önerilir**. Kullanıcının bir kez yapacakları:
   1. GitHub → Settings → Developer settings → Personal access tokens → **Fine-grained tokens** →
      Generate new token. Token name: ör. `mathverify-bulut-kurulum`; Resource owner: `wqedwad`;
      Expiration: kullanıcının seçimi (kişisel depoda süresiz de olur; 90 gün ya da 1 yıl önerilir);
      Repository access: **Only select repositories** → `wqedwad/asd`; Permissions → Repository
      permissions → yalnız **Contents: Read-only** (Metadata: Read-only kendiliğinden gelir).
      Belirteç bir kez gösterilir; sohbete yapıştırılmaz.
   2. claude.ai → oturumun başlık çubuğundaki bulut ortamı menüsü → Edit → **Environment
      variables** alanına `MATHVERIFY_GITHUB_TOKEN=<belirteç>` satırı. Ad `GITHUB_TOKEN` ya da
      `GH_TOKEN` **olmaz**: belgeye göre o adlar vekilin yer tutucusu yerine oturumlara olduğu gibi
      geçer (§3.3).
   3. Aynı pencerede **Setup script** alanının sonuna bir yorum satırı eklenir (ör. `# belirtec v1`):
      belgeye göre görüntü yalnız betiğin metni ya da ağ ayarı değişince (ya da ~7 günde) yeniden
      kurulur; değişken eklemek tek başına yetmeyebilir. Bu adım, `fetch_artifacts.sh`'in belirteçli
      hâli `master`a birleştikten **sonra** yapılır: betik checkout'taki `master` kopyasını çalıştırır.
   4. Yeni bir sohbet açılır; oturum §12'deki "belirteçle kurulum" maddesini ölçer.
   Belirtecin süresi dolarsa hiçbir şey bozulmaz: çekim yine 401 alır, kanca kurulumu devralır.
4. **Routine istemleri:** bir bulut routine'inin (zamanlanmış ya da tek seferlik ajan) istemi push
   hedefini açıkça **yeni bir dal** olarak verir ya da hiç push istemez. "Oturumun kendi dalına push
   et" yazılmaz: 24 Eylül'deki routine oturumu varsayılan dal `master`da başladı ve `master`a push
   etti (§13).
5. Claude GitHub App ile depo erişimi için yeni bir şey gerekmez: routine oturumu özel depoyu
   klonladı ve push edebildi (24 Eylül).

> **Yazıldığı tarih: 24 Eylül 2026.** Kaynaklar: resmî belgeler
> (`code.claude.com/docs/en/cloud-environments` ve `claude-code-on-the-web`, 24 Eylül'de okundu)
> ve bu depodaki betikler (`scripts/cloud/`, `scripts/setup_lean*.sh`, `scripts/fetch_artifacts.sh`).
> Bu belge yazılırken **bulutta hiç oturum açılmamıştı.** Bulut davranışı hakkındaki her şey ya
> resmî belgeden ya da WSL içinde bulut düzeninin taklit edilmesinden (temiz `HOME`, `/opt` önekli
> kurulum, 4 CPU'ya sabitlenmiş) geliyor. İlk oturumda ölçülecekler §12'de ve
> **[DOĞRULANMADI]** işaretli.
>
> **Düzeltme (24 Eylül 2026, akşam):** bu belge yazıldıktan sonra bulutta tek seferlik bir routine
> oturumu ölçüm yaptı (11:51–12:01 UTC, Sonnet 5, "Default" ortam, kurulum betiği tanımlı değildi;
> `bulut-2026-09-24`'ün `4d01ba2` hâli). Rapor `docs/bulut_tani_2026-09-24.md`, karar DECISIONS §44.
> Ölçülen maddeler §12'de işaretli; ölçümle çürüyen ifadelerin yanında "Düzeltme" notu var. O
> oturumdan sonraki davranış değişiklikleri (`7993055`…`4002898`) de ilgili bölümlere eklendi.

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
   **Düzeltme (24 Eylül 2026):** GitHub'daki `master` artık `572ef57`: routine oturumu
   `bulut-2026-09-24`'ün `4d01ba2` hâlini ve tanı raporunu `master`a push etti (§13, DECISIONS §45).
   `scripts/cloud/` bu yüzden `master`da var ve klon yedeği için `MATHVERIFY_REPO_REF` gerekmez. Ama
   dalın sonraki commit'leri (`7993055`…`4002898`: Python yedeği, çevrimdışı ve aşamalı kurulum,
   `ANTHROPIC_BASE_URL`) `master`a birleştirilene dek `master`da başlayan bir oturum betiklerin
   `4d01ba2` hâlini çalıştırır.
3. `claude.ai/code` → ortam (environment) oluşturulur ya da düzenlenir: ağ (§3.1), kurulum betiği
   (§3.2), ortam değişkenleri (§3.3).

**Ek (24 Eylül 2026):** 1. madde fiilen sağlanmış: routine oturumu özel depoyu klonladı ve push
edebildi.

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

**Düzeltme (24 Eylül 2026, ölçüm):** yukarıdaki tahminlerin yerine routine oturumunda ağ ayarına
dokunulmamış "Default" ortamda ölçülenler (yalnız HTTP durum kodu, 20 s zaman aşımı; ayrıntı
`docs/bulut_tani_2026-09-24.md` §5):

| Adres | Sonuç | Projede kim kullanır |
|---|---|---|
| `github.com` (git; `leanprover/elan` release dosyası dahil) | **açık**: release indirmesi 200 (`release-assets.githubusercontent.com` yönlendirmesiyle); oturuma bağlı olmayan açık bir depoya (`leanprover-community/repl`) `git ls-remote` de çalıştı | klon, `fetch_artifacts.sh` (araç ref'i) |
| `raw.githubusercontent.com` | **açık** (200) | — |
| `pypi.org` | **açık** (200) | uv önbellek ısıtması, kancanın çevrimiçi yedeği |
| `api.anthropic.com` | **açık** (kökte 404: TLS ve vekil geçti, kaynak yok) | F3 Anthropic ailesi |
| `releases.lean-lang.org` | **kapalı** (`CONNECT tunnel failed, response 403`) | elan'ın araç zinciri indirmesi → araç ref'i |
| `cache.mathlib.org` | **kapalı** (403) | `lake exe cache get` → araç ref'i |
| `releases.astral.sh` | **kapalı** (403) | uv'nin Python indirmesi → araç ref'i |
| `api.meta.ai` | **kapalı** (403) | F3 Meta ailesi → Custom ağ gerekir |

Sonuç: Trusted ağ F3/F4 dışındaki her şeye yeter; F3/F4 için yalnız `api.meta.ai` eklenir.
Yukarıdaki "GitHub vekili ... release dosyalarına 403 döndürür" ifadesi bu oturumda
tekrarlanmadı (elan release'i 200); o genelleme belgeden alınmıştı ve yanlış çıktı (DECISIONS §37
düzeltmesi). Araç ref'inin gerekçesi yine geçerli: Lean araç zinciri, Mathlib önbelleği ve uv'nin
Python'u bulutta indirilemiyor, ve kurulum SHA256'larla sabit kalıyor.

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

**Ek (24 Eylül 2026, `eba49b5`, `a02e65c`):** routine ölçümünden sonra değişen davranış.

- **Çekim başarısızsa kurulum yok.** 2. adım başarısızsa ya da çekilen dizin kendi
  `SHA256SUMS.full`'una uymuyorsa Python ve Lean aşamaları **koşmaz**: `setup_env.status`'ta
  `(skipped)` görünürler, satırda `reason=fetch` (ya da `reason=artifacts`) yazar ve var olan
  kurulum olduğu gibi kalır (`lean=stale` ya da `lean=missing`, §6). Önce, gözden geçirmede
  ölçüldüğü üzere, başarısız bir çekimden sonra Lean aşaması yine koşuyor, canlı
  `/opt/mathverify-lean` dosyalarını yeniden yazıyor ve `cache.mathlib.org`'a karşı
  `lake exe cache get` içinde 24 dakikadan fazla asılı kalıyordu.
- **Sıkı çevrimdışı.** Lean betikleri `MATHVERIFY_LEAN_OFFLINE=1` ile koşar: her çevrimiçi yedek
  (elan ya da araç zinciri indirmesi, `lake exe cache get`, Lake klonu, `apt-get`) reddedilir; eksik
  bir artefakt betiği hiçbir şey yazmadan saniyeler içinde durdurur.
- **Aşamalı güncelleme.** `setup_lean.sh` kullanacağı her artefaktı projeye dokunmadan önce
  doğrular. Sabitlere uymayan bir projeyi yanında ayrı bir dizinde kurar ve ancak `import Mathlib`
  duman testi orada ve yeniden adlandırmadan **sonra** yerinde yeniden geçerse eskisinin yerine
  koyar; geçmezse eskisini geri koyar (`docs/LEAN_SETUP.md`).
- **Anlık görüntüde indirme önbelleği kalmaz.** Mathlib `.ltar`'ları `$OPT/.mathlib-ltar`'a açılır ve
  Lean aşamalarından sonra silinir (oleanlar o zaman açılmış olur); pip `--no-cache-dir` ile koşar.
  Routine oturumunun ölçtüğü `/root/.cache/mathlib` (448 MB, `4d01ba2`) artık oluşmaz.

**Ölçüm (24 Eylül, routine):** checkout `/home/user/asd` idi; önyükleyicinin `/home/*/*` araması
bu yolu kapsar. Kurulum betiği alanından çalıştığında checkout'un orada hazır olup olmadığı henüz
ölçülmedi (§12).

**Ölçüm (24 Eylül, gece, ilk normal oturum; HANDOFF §0.11, DECISIONS §53):** alan gerçekten koştu
(`mode=all`, kancadan 2 s önce) ve checkout hazırdı (`repository: /home/user/asd (18fd298)`). Ama araç
ref'inin çekimi 0 s'de düştü: `fatal: could not read Username for 'https://github.com'` (özel depo
401), yedek yol da aynı; durum satırı
`FAILED mode=all failed=[fetch_artifacts python uv_prewarm setup_lean setup_lean_repl] ... reason=fetch python=missing lean=missing total=0s`.
Resmî belgeye göre Claude Code ajan vekiline kurulum betiğinden sonra bağlanır ve GitHub kimliğini
oturumdaki GitHub vekili ekler; oturum içinde vekil atlanınca aynı 401 yeniden üretildi. Anlık
görüntü bu başarısız koşudan sonra alındığı için Lean taşımaz; kanca her yeni sohbette kurar (bu
oturumda 167 s). Çözüm: `MATHVERIFY_GITHUB_TOKEN` (§3.3, "Senin yapman gerekenler" 3. madde);
`fetch_artifacts.sh` düz çekim düşünce onunla bir kez daha dener.

### 3.3 Ortam değişkenleri

**Gerekli değişken yok.** Anahtarlar `.env`'den okunur (§10). İsteğe bağlı olanlar:

| Değişken | Ne zaman |
|---|---|
| `MATHVERIFY_REPO_REF` | Kurulum betiğinin klon yedeği varsayılan dal dışında bir dalı çeksin (ör. birleştirmeden önce `bulut-2026-09-24`) |
| `MATHVERIFY_SKIP_LEAN=1` | Kanca Lean kurulumunu arka planda **başlatmasın** (var olanı yine bildirir) |
| `MATHVERIFY_ARTIFACT_REF` | Varsayılan araç ref'i dışında bir sürüm (`refs/arac/bulut-vN`) |
| `MATHVERIFY_ANTHROPIC_BASE_URL` | (24 Eylül'de eklendi) projenin Anthropic çağrıları varsayılan `https://api.anthropic.com` dışında bir uç noktaya gitsin; platformun `ANTHROPIC_BASE_URL`'i bilerek okunmaz (§10) |
| `MATHVERIFY_GITHUB_TOKEN` | (24 Eylül gecesi eklendi, önerilir) yalnız `wqedwad/asd`'yi okuyabilen fine-grained GitHub belirteci (Contents: read-only). Kurulum betiği GitHub vekilinden önce koştuğu için araç ref'ini ancak bununla çekebilir (§3.2). `fetch_artifacts.sh` belirteci yalnız düz çekim düştükten sonra ve yalnız `https://github.com/` altına gönderir; oturum içinde vekil kimliği eklediği için orada hiç gönderilmez; değer hiçbir çıktıya yazılmaz (DECISIONS §53). Belgeye göre ortam değişkenlerini ortamı kullanan herkes ve oturumdaki her komut okuyabilir. `GITHUB_TOKEN`/`GH_TOKEN` adı kullanılmaz: belgeye göre o adlarla girilen değer vekilin yer tutucusu yerine oturumlara olduğu gibi geçer |

**Düzeltme (24 Eylül 2026):** `MATHVERIFY_REPO_REF` satırındaki örnek artık gerekmiyor:
`scripts/cloud/` GitHub'daki `master`da (`572ef57`) var (§2).

**Düzeltme (24 Eylül 2026, gece):** "Gerekli değişken yok" işlev için hâlâ doğru, ama kurulum
betiğinin anlık görüntüye Lean koyabilmesi için `MATHVERIFY_GITHUB_TOKEN` gerekiyor (tablo, §3.2).

## 4. Oturum başında ne olur

| | Kurulum betiği (`setup_env.sh`) | SessionStart kancası (`session_start.sh`) |
|---|---|---|
| Nerede tanımlı | claude.ai ortam ayarı | depo: `.claude/settings.json` (`startup\|resume`, zaman aşımı 600 s) |
| Ne zaman | Claude başlamadan önce; anlık görüntü eskiyince | her oturum başında ve devamında; **yerelde de** tetiklenir ama `CLAUDE_CODE_REMOTE=true` değilse hiçbir şey yapmadan çıkar |
| Kim olarak | root | oturum kullanıcısı **[DOĞRULANMADI]** |
| Ne yapar | §3.2 | aşağıda |
| Çıkış | her zaman 0 | her zaman 0 |

**Düzeltme (24 Eylül 2026, ölçüm):** routine oturumunda oturum kullanıcısı **root** (`uid=0`,
`HOME=/root`), checkout `/home/user/asd`. Kanca o oturumda elle, root olarak çalıştırıldı
(`CLAUDE_CODE_REMOTE=true`); oturum `master`da başladığı ve kanca o an `master`da olmadığı için
platform onu ilk turda çalıştırmadı. Normal `Bash` komutlarında `CLAUDE_PROJECT_DIR` boş.

Kanca sırasıyla:

1. Python seçer: `/opt/python3.14` (kurulum betiğinden), yoksa `python3.14`, yoksa sistem
   `python3` (Ubuntu 24.04'te 3.12; durum bloğunda "YEDEK" diye uyarır).
   **Düzeltme (24 Eylül 2026, ölçüm):** bulut imajında `python3` 3.12 değil **3.11.15**
   (`/usr/local/bin/python3`); `/usr/bin/python3.12` ve `/usr/bin/python3.13` ayrıca kurulu,
   `python3.14` yok. Kurulum betiği yokken kanca çıplak `python3`'ü seçti ve `.venv` kurulamadı
   (`mathverify` `>=3.12` ister; `.venv: HATA, 4 s`). Artık 3.12'den eski ya da `.venv` içindeki
   yorumlayıcı reddedilir. Sıra: öneğin `python3.14`'ü (`/opt/python3.14`) > `PATH`'teki
   `python3.14` > `uv python find 3.14` > `python3.12` > `python3.13` > yalnız ≥ 3.12 ise `python3`.
   3.12, 3.13'ten önce gelir çünkü yedek yorumlayıcılardan yalnız 3.12.11'de tam takım ölçüldü
   (DECISIONS §42); 3.13 hiç ölçülmedi. Hangi yedeğin seçildiği ve reddedilenler durum bloğunda
   yazılır; hiçbiri yoksa `.venv` kurulmaz, var olanına dokunulmaz.
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

**Ek (24 Eylül 2026, `eba49b5`, `a02e65c`):**

- **Arka plan kurulumundan sonra yeniden çalıştırma.** Kanca kurulumu arka planda başlattığında
  (KURULUYOR) kurulum bitince hiçbir şey onu bu oturumda yeniden çalıştırmaz. Yedek yorumlayıcıyla
  kurulmuş (ya da hiç kurulamamış) `.venv` ve `~/.elan`, `~/mathverify-lean`, `~/repl`
  bağlantıları o yeniden çalıştırmayı bekler. Durum bloğu komutu kendisi basar:
  `CLAUDE_CODE_REMOTE=true CLAUDE_ENV_FILE="<oturumun dosyası>" bash "<depo>/scripts/cloud/session_start.sh"`
  (kurulum `setup_env.status` "OK" ile başlayınca). Damga yorumlayıcı yolunu tuttuğu için yeniden
  çalıştırma `.venv`'i sabit 3.14.6 ile yeniden kurar. Routine oturumunda tam olarak bu elle
  yapıldı: ikinci koşuda `.venv` 7 s'de 3.14.6 ile kuruldu.
- **Salt okunur `/opt` ve eski sabitler.** Kurulum `lean/` sabitlerinden farklıysa ve önek bu
  kullanıcıya yazılabilir değilse (root'un kurduğu `/opt`, root olmayan oturum) kanca ikinci bir tam
  kurulumu **başlatmaz**; Lean satırı "ESKİ" der ve kullanıcı kurulumunun komutunu, gereken diski
  (~12 GB) ve `$HOME` altındaki boş alanı basar (yetmiyorsa "YETERSİZ"):
  `MATHVERIFY_OPT="$HOME/.mathverify-opt" bash scripts/cloud/setup_env.sh --lean-only`.
  Önek yazılabilirse güncelleme arka planda kendiliğinden başlar ("HAZIR ama … güncelleniyor").

Ölçüm (24 Eylül, WSL içinde yerel Linux, root değil): kanca ilk koşuda 2.5 s, ikinci koşuda
85 ms; Windows'ta Git Bash altında 0 bayt çıktı, çıkış 0, ~0.3 s.

**Ölçüm (24 Eylül, bulut, routine oturumu, elle ve root olarak):** ilk koşu **7 s** (Python 3.11.15
yedeği, `.venv` 4 s'de HATA, Lean arka planda başlatıldı, 7 rapor JSON'u kopyalandı); Lean hazır
olduktan sonra ikinci koşu **7 s** (Python 3.14.6, `.venv` 7 s'de KURULDU, Lean HAZIR). Platformun
kendisinin tetiklediği kanca henüz ölçülmedi (§12).

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
| `/opt/.mathlib-ltar/` | (24 Eylül'de eklendi) Mathlib `.ltar`'ları, yalnız kurulum sırasında; Lean aşamalarından sonra silinir |

**Düzeltme (24 Eylül 2026, `eba49b5`):** `~/.cache/mathlib/` satırı artık bulut kurulumu için doğru
değil. `setup_env.sh` `.ltar`'ları `$OPT/.mathlib-ltar`'a açar ve Lean aşamalarından sonra siler;
anlık görüntüde `.ltar` kalmaz. `setup_lean.sh` tek başına araç diziniyle koşunca `.ltar`'lar
projenin yanında geçici bir `.<proje>.ltar.<pid>` dizinine gider ve çıkışta silinir; `$HOME/.cache/mathlib`
yalnız araç dizini olmadan (çevrimiçi, bulut dışında) ya da `MATHLIB_CACHE_DIR`/`XDG_CACHE_HOME`
verilince kullanılır. Routine oturumunda (`4d01ba2`, bu değişiklikten önce) ölçülen boyutlar
(`du -sh`): `/opt/elan` 3.0G, `/opt/mathverify-lean` 7.2G, `/root/.cache/mathlib` 448M,
`/opt/python3.14` 107M, `/opt/mathverify-logs` 48K.

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
| `MATHVERIFY_GITHUB_TOKEN` | — | (24 Eylül gecesi eklendi) araç ref'inin düz çekimi düşerse bir kez daha bununla denenir (kurulum betiği aşaması; §3.3, DECISIONS §53) |
| `MATHVERIFY_GITHUB_TOKEN_URL` | `https://github.com/` | belirtecin gönderilebileceği adres öneki; dışındaki adrese gönderilmez (testler yerel sunucu için değiştirir) |
| `MATHVERIFY_SKIP_LEAN` | — | `1`: kanca Lean kurulumu başlatmaz |
| `MATHVERIFY_REPO_URL` / `MATHVERIFY_REPO_REF` | `https://github.com/wqedwad/asd` / uzak varsayılan dal | kurulum betiğinin klon yedeği |
| `MATHVERIFY_PROFILE_D` | `/etc/profile.d` | `mathverify.sh`'in yazıldığı yer |
| `MATHVERIFY_HOOK_PREFIXES` | — | kancanın önek listesini değiştirir (iki nokta ile ayrılmış); yalnız testler için |
| `MATHLIB_CACHE_DIR`, `XDG_CACHE_HOME` | `$HOME/.cache/mathlib` | Mathlib `.ltar` önbelleği (Mathlib'in kendi kuralıyla çözülür) |
| `CLAUDE_CODE_REMOTE` | platform verir | `true` değilse kanca hiçbir şey yapmaz |
| `CLAUDE_PROJECT_DIR`, `CLAUDE_ENV_FILE` | platform verir | depo kökü; oturumun sonraki komutlarına aktarılacak değişkenlerin dosyası |
| `UV_PYTHON_DOWNLOADS` | kanca `never` yapar | uv Python indirmeye çalışmasın (`releases.astral.sh` kapalı) |
| `MATHVERIFY_LEAN_OFFLINE` | `0`; `setup_env.sh` her zaman `1` verir | (24 Eylül'de eklendi) `1`: `setup_lean.sh` ve `setup_lean_repl.sh` her çevrimiçi yedeği reddeder (araç zinciri indirmesi, `lake exe cache get`, klon, `apt-get`); eksik artefakt betiği bir şey yazmadan durdurur |

**Düzeltme (24 Eylül 2026):** `MATHLIB_CACHE_DIR` bulut kurulumunda `setup_env.sh` tarafından
`$OPT/.mathlib-ltar` verilir (yukarıdaki düzeltme). Routine oturumunda `CLAUDE_PROJECT_DIR`
normal `Bash` komutlarında boş ölçüldü; kanca bu değişken boşsa depoyu kendi konumundan bulur.

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

**Ek (24 Eylül 2026): `setup_env.status` satırının alanları.**

```
OK|FAILED mode=all|lean|python failed=[<aşamalar>] stages=[<ad>(<süre>s|skipped) ...] [reason=fetch|artifacts|no-repo] python=3.14.6|missing lean=ready|stale|missing total=<N>s
```

- `stages=[...]`: her aşama süresiyle; çalıştırılmadan atlanan aşama `(skipped)` yazar ve
  `failed=[...]`'de de görünür (günlüğünde nedeni var).
- `reason=`: yalnız bir neden varsa. `fetch`: araç ref'i çekilemedi; `artifacts`: çekilen dizin
  `SHA256SUMS.full`'a uymuyor; ikisinde de Python ve Lean aşamaları koşmaz, var olan kurulum olduğu
  gibi kalır. `no-repo`: depo bulunamadı ve klon başarısız.
- `lean=ready`: kurulum var ve `lean/` sabitleriyle aynı (`lean.done`); `lean=stale`: bitmiş bir
  kurulum var ama başka sabitlerle yapılmış (kullanılır, güncellenmesi gerekir); `lean=missing`:
  bitmiş kurulum yok.

Routine oturumunda ölçülen satır (kancanın başlattığı `--lean-only`, `4d01ba2`):
`OK mode=lean failed=[] stages=[fetch_artifacts(55s) python(1s) setup_lean(119s) setup_lean_repl(19s)] python=3.14.6 lean=ready total=195s`.
O sürümde `reason=fetch|artifacts` ve `(skipped)` henüz yoktu (yalnız `reason=no-repo` vardı).

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

**Ek (24 Eylül 2026):** son satırdaki kullanıcı öneki komutunu kanca, `/opt` salt okunur ve
sabitleri eskiyken kendisi basar, ama başlatmaz: ikinci bir tam kurulum ~12 GB disk ister ve bulut
diski ~30 GB boş (§8). `reason=fetch` ile düşen bir kurulumdan sonra önce
`/opt/mathverify-logs/fetch_artifacts.log` okunur; başarısız bir kurulumdan sonra `/opt/arac`
silinmez (yalnız `OK` biten kurulum siler).

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
836 passed / 2 skipped; yerel `check.py --full`
**24/24** hem Windows'ta (~68 dk (4107 s; adversaryal 3563 s)) hem yerel Linux'ta (~36 dk (2186 s; adversaryal 1870 s)) (ayrıntı HANDOFF §0.6). Bulutta ölçülenler §12'ye yazılır.

**Bulutta ölçülen (24 Eylül, routine oturumu, `4d01ba2`):** `lean_available()` baştan sona `True`;
`pytest tests -q -rs` 517 test: **515 passed / 2 skipped / 0 failed**, 50 s (atlananlar: opt-in bulut
indirme testi `MATHVERIFY_CLOUD_INTEGRATION=1` ister; `test_f5_lean.py:68` "statement out of scope";
Lean yüzünden atlanan yok); `harness.run_lean --limit 5 --timeout 45`: 5 öğenin 4'ünde ifade, 4
sertifika, FP 0, junk sertifikası 0, koşu sonunda REPL kalmadı; hızlı `check.py` **12/12**, 115 s.
Bu sayılar sonraki commit'lerden önceki takıma aittir; test sayısı o günden beri değişti.
`check.py --full` bulutta henüz koşmadı.

**Ek (24 Eylül 2026, `7993055`, `5e16a31`, `911aca5`):** Lean kapıları artık Lean'in gerçekten cevap
vermesini ister. Junk ifadelerinde ve yanlış cevaplı öğelerde her taktik denemesi cevaplanmış olmalı
(`n_unanswered == 0`) ve ispatlanmış ifadenin denetim sondalarından hiçbiri cevapsız kalmamalı;
yoksa junk ve FP kapıları düşer. Zaman aşımı, ölü REPL, yazma hatası, bozuk JSON ve hatasız
başarısızlık cevap sayılmaz. `prove.py`'nin denetimi de vakum ya da hipotezsiz sondası gerçek bir
Lean hükmü almazsa temiz sayılmaz (ilke 7). Ölçüm (Windows, gerçek tam tarama): 121 sertifika
(değişmedi), 869/869 deneme ve 58/58 denetim sondası cevaplı, en yavaş deneme 3.0 s. Bulutta bir
deneme zaman aşımına uğrarsa bu kapılar bilerek düşer; bulutta tam tarama henüz ölçülmedi
(DECISIONS §46–47).

## 8. Sınırlar

- **Makine:** Ubuntu 24.04 x86_64, ~4 vCPU, 16 GB RAM, 30 GB disk. Lean kurulumu bunun ~12–13
  GB'ını kaplar (WSL'deki uçtan uca kurulumda ~12 GB ölçüldü; araçların açıldığı geçici dizin
  kurulum sırasında bunun üstüne biner). Bir Lean REPL'i ~6.9 GB bellek tutabilir (WSL ölçümü);
  16 GB'lık makinede aynı anda iki Lean taraması koşturulmaz **[DOĞRULANMADI: bulutta ölçülmedi]**.
  **Düzeltme (24 Eylül 2026, ölçüm):** routine oturumunun makinesi Ubuntu 24.04.4, 4 CPU,
  **15 GB** RAM (`free -g`; takas yok), `/` üzerinde ~30 GB boş (`df -h`: 252G aygıt, 30G boş;
  `$HOME`, `/opt`, `/tmp` aynı dosya sisteminde), `/opt` yazılabilir, `sudo -n` çalışıyor. Lean
  kurulumu orada `/opt/elan` 3.0G + `/opt/mathverify-lean` 7.2G (+ o sürümde silinmeyen 448M
  `.ltar`) tuttu (§5). Bellek: Lean istemcisi başına ~7.2 GB PSS (REPL ~6.7 GB + `lake env`
  ~0.5 GB; 24 Eylül ölçümü); 15 GB'lık makinede iki istemci ~14.4 GB eder, bu yüzden aynı anda iki
  Lean taraması (ya da Lean'li iki `check.py --full`) koşturulmaz. Bulutta iki taramanın birlikte
  denenmesi ölçülmedi.
- **Boşta kalan VM geri alınır ve arka plandaki kabuk işi kaybolur.** `check.py --full`
  (Windows'ta ~25–70 dk; bulutta ~63 dk (3793 s; adversaryal 3220 s; 4 vCPU), ölçüldü) ya da Lean kurulumu sürerken oturum etkin
  tutulur. `check.py --full` günlüğü `reports/check_full.log`a koşu sırasında yazar; yarıda kalan
  koşu yarım günlük bırakır.
- **Git:** bulut oturumu yalnız **kendi dalına** push edebilir. Etiket, `master` ve başka dallar
  push edilemez. `master`a birleştirme GitHub'da PR ile ya da yerel checkout'ta yapılır;
  birleştirmeden önceki yedek (etiket + bundle) de yerelde alınır (§9).
  **Düzeltme (24 Eylül 2026, ölçüm):** "`master` push edilemez" koşulsuz doğru değil. Oturumun
  kendi dalı, oturumun başladığı daldır: 24 Eylül'deki routine oturumu varsayılan dal `master`da
  başladı ve `origin/master`'a push etti (`572ef57`, §13, DECISIONS §45). Etiket push'unun
  reddedilip reddedilmediği ölçülmedi.
- **Ağ:** §3.1. uv Python indiremez; Python yalnız araç ref'inden gelir.
- **Anlık görüntü** ~7 gün sonra eskir; kurulum betiği o zaman baştan koşar.
- **Devam ettirilen sohbet** (24 Eylül gecesi ölçüldü, HANDOFF §0.11): boşta kalan sohbete dönülünce
  makine yeniden başlatılmış olabilir; disk (Lean, `.venv`) korunur, kanca kurulum yapmaz. Ama Lean'in
  ilk açılışı çok yavaş olabilir: ölçülen bir durumda ilk canlı Lean testi 300 s'de zaman aşımına
  uğradı; sonra sıcak açılış 5.8 s, önbellek boşaltılmış açılış 26.9 s. `check.py --full` ya da Lean
  testlerinden önce Lean dosyaları bir kez okunur, sonra Lean denenir (`lean_available(900)` tek
  başına yetmez: istemcinin `import Mathlib` sınırı ayrıca 300 s, `LeanClient.boot_timeout`; ısıtmanın
  bu durumu çözdüğü ölçülmedi):
  `find "$MATHVERIFY_LEAN_PROJECT/.lake" "$ELAN_HOME/toolchains" -name '*.olean' -print0 | xargs -0 cat > /dev/null`
  ve ardından `PYTHONUTF8=1 .venv/bin/python -c "from mathverify.formal.lean_client import lean_available; print(lean_available())"`.
- **Bellek dosyaları:** `~/.claude` taşınmaz; kalıcı her bilgi depoya yazılır.

## 9. Buluttan yerele ve birleştirme

- `claude --teleport <oturum-id>` bir bulut oturumunu yerel checkout'a (`C:\Users\kullanici\mathverify`)
  çeker. Öncesinde bulut oturumunun dalı commit edilip push edilmiş olmalı.
- Birleştirme akışı: bulut oturumu kendi dalını push eder → PR ya da yerelde `git fetch` →
  **birleştirmeden önce yerelde yedek**: `yedek/master-YYYY-MM-DD[-N]` etiketi ve
  `C:\Users\kullanici\mathverify-yedek\` altına `git bundle create ... --all` (HANDOFF §5.4) → `master`
  fast-forward → etiket ve `master` yerelden push edilir. Yedekler kullanıcıya sormadan silinmez.
- Birleştirme yalnız kullanıcı isterse yapılır (CLAUDE.md).
- **Düzeltme (24 Eylül 2026):** bu akış 24 Eylül'de bir kez bozuldu. Routine oturumu `master`da
  başladığı için "kendi dalına push" `master`a push demekti: `bulut-2026-09-24` (`4d01ba2`) ve tanı
  raporu (`572ef57`) son doğrulamadan ve yedekten **önce** `origin/master`a gitti. Kod kaybı yok
  (`4d01ba2..572ef57` farkı yalnız rapor). Birleştirme öncesi `master` (`23d7c6b`) sonradan
  yedeklendi: etiket `yedek/master-2026-09-24` (GitHub'a da push edildi) ve
  `C:\Users\kullanici\mathverify-yedek\mathverify-master-23d7c6b-2026-09-24.bundle` (doğrulandı).
  Kural §13'te.

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
  **Düzeltme (24 Eylül 2026, ölçüm):** routine oturumunun kabuğunda `ANTHROPIC_API_KEY` ve
  `ANTHROPIC_AUTH_TOKEN` **tanımlı değil** (yalnız adlar okundu), yani `.env`'deki anahtar
  gölgelenmez. Ama `ANTHROPIC_BASE_URL` tanımlı (Claude Code'un kendi trafiği için) ve SDK
  `base_url` verilmezse onu ortamdan okur: projenin F3 çağrıları `.env`'deki anahtarla platformun uç
  noktasına gidecekti. Düzeltildi (`4002898`, DECISIONS §48): istemci `base_url`'i her zaman açıkça
  verir, `MATHVERIFY_ANTHROPIC_BASE_URL` ya da SDK'nın varsayılanı `https://api.anthropic.com`
  (`docs/LLM_LAYERS.md`).
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

**Düzeltme (24 Eylül 2026, ölçüm):** "GitHub release dosyaları 403 döndürdüğü için" gerekçesi bulutta
tekrarlanmadı: routine oturumunda `github.com/leanprover/elan` release indirmesi 200 döndü. Kapalı
olanlar `releases.lean-lang.org` (Lean araç zinciri), `cache.mathlib.org` (Mathlib önbelleği) ve
`releases.astral.sh` (uv'nin Python'u), hepsi 403 (§3.1). Araç ref'i bu yüzden yine gerekli.
Bulutta çekim ölçüldü: `fetch_artifacts.sh` 50 s (git çekimi 37 s, 1.1G git nesnesi; SHA256
doğrulaması 1 s), 5/5 dosya OK; kurulumun içindeki aşama olarak 55 s.

| Sürüm | İçerik |
|---|---|
| `refs/arac/bulut-v1` (24 Eylül'de push edildi) | Lean araç zinciri `lean-4.34.0-linux.tar.zst` (580 367 391 B; `bin/lean` ve `bin/lake` SHA256'ları WSL kurulumuyla aynı), elan 4.2.4 (`elan-x86_64-unknown-linux-gnu.tar.gz`), CPython 3.14.6 (`cpython-3.14.6-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz`, python-build-standalone 20260728), Mathlib `.ltar` önbelleği (`mathlib-cache-5ed2965.tar`, 8906 dosya) |
| `refs/arac/bulut-v2` (`fetch_artifacts.sh`'in varsayılanı) | v1 + Lake paketlerinin (`lake-manifest.json`'daki revizyonlar) ve REPL'in sabit kaynakları, böylece kurulum GitHub'dan klon yapmaz. Boyut (bulutta ölçüldü, 24 Eylül; commit `f90d5e4`): çekim 1.1G git nesnesi; birleştirilmiş 5 dosya toplam 1 140 156 848 B: `lean-4.34.0-linux.tar.zst` 580 367 391 B, `mathlib-cache-5ed2965.tar` 457 768 960 B, v1'e eklenen `lean-sources-5ed2965.tar.gz` **61 132 808 B**, CPython 35 891 118 B, elan 4 996 571 B |

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
*Ek (24 Eylül 2026):* v2 bulutta doğrulandı (yukarıda); v1'in içeriği v2'de de var. v1 geçmiş için
duruyor, silinip silinmeyeceği hâlâ açık soru (HANDOFF §12, madde 15).

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

**Düzeltme (24 Eylül 2026):** listenin çoğu 24 Eylül'deki routine oturumunda ölçüldü (11:51–12:01
UTC, `4d01ba2`, kurulum betiği tanımlı değildi, kanca elle root olarak çalıştırıldı; rapor
`docs/bulut_tani_2026-09-24.md`). Ölçülenler `[x]` ve sonuçla işaretli; açık kalanlar sonda.
Açık maddeler, bu dalın kalan commit'leri `master`a alındıktan sonra açılan ilk normal oturumda
(kurulum betiği tanımlıyken) ölçülür.

- [x] Oturum kullanıcısı ve `HOME` (`id -un; echo $HOME`); root mu?
      → **root** (`uid=0`), `HOME=/root`, checkout `/home/user/asd`.
- [ ] Kurulum betiği çalışırken checkout nerede (`setup_env.log`'daki `repository:` satırı);
      `CLAUDE_PROJECT_DIR` tanımlı mıydı, yoksa klon yedeğine mi düştü?
      → **Açık:** kurulum betiği tanımlı değildi. Bilinen: oturumdaki checkout `/home/user/asd`
      (önyükleyicinin `/home/*/*` aramasına girer); normal `Bash` komutlarında `CLAUDE_PROJECT_DIR`
      boş.
- [x] `refs/arac/*` çekimi GitHub vekilinden geçiyor mu (`fetch_artifacts.log`)? Paket kaynakları
      v2'den mi geldi, yoksa GitHub'dan klon denendi mi (`setup_lean.log`)?
      → **Geçiyor:** bağımsız deneme 50 s (1.1G git nesnesi 37 s'de), aşama olarak 55 s, 5/5
      SHA256 OK. Paket kaynakları v2'den geldi: `lean-sources-5ed2965.tar.gz` çekildi ve
      `setup_lean` başarıyla bitti; o sürümdeki betik, arşiv varken Lake bir paket klonlarsa düşer.
      Önbellekte eksik `Mathlib/Probability/Kernel/Invariance` ve kök `Mathlib` `lake build Mathlib`
      ile derlendi (beklenen, `docs/LEAN_SETUP.md` tuzak 3).
- [x] Kurulum betiğinin süresi (`setup_env.status`, `total=`), ~5 dakikalık öneriye göre:
      **195 s**, kancanın başlattığı yoldan ölçüldü (`OK mode=lean`, çekim 55 s + Python 1 s +
      `setup_lean` 119 s + REPL 19 s). Kurulum betiği alanından (`mode=all`, uv önbellek ısıtması
      dahil) süre hâlâ açık (aşağıda).
- [ ] Anlık görüntü `/opt`'u koruyor mu: ikinci oturumda kanca Lean'i "HAZIR" buluyor ve kurulum
      betiği her şeyi atlıyor mu? → **Açık** (tek oturum vardı).
- [x] Platformun hazır araçları: `check-tools` çıktısı; `python3 --version`, `uv --version`
      (uv yoksa kurulum betiği PyPI'den kurar).
      → `check-tools` "All tool validations passed"; `python3` **3.11.15** (`/usr/local/bin/python3`),
      `/usr/bin/python3.12` ve `python3.13` var, `python3.14` yok; uv 0.8.17; git 2.43.0; poetry
      2.3.3; Node 22.22.2, Java 21.0.10, Go 1.24.7, Rust 1.94.1, Docker 29.3.1.
- [x] Kancanın süresi (durum bloğunun başlığı): ilk oturum **7 s**, sonraki **7 s** (aynı oturumda
      elle iki koşu: ilki Python 3.11.15 yedeğiyle `.venv` HATA, ikincisi Lean hazırken `.venv` 7 s'de
      kuruldu). Platformun tetiklediği kanca hâlâ ölçülmedi (aşağıda).
- [x] `pytest -q -rs` sayıları ve atlama nedenleri; bellek sınırı testi Linux'ta (`RLIMIT_AS`)
      atlanıyor mu? → 517 test: **515 passed / 2 skipped / 0 failed**, 50 s. Atlananlar yalnız
      opt-in bulut indirme testi ve `test_f5_lean.py:68` ("statement out of scope"); bellek sınırı
      testi **atlanmadı**, Lean yüzünden atlanan yok.
- [x] Kabukta `ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN` tanımlı mı (yalnız adlar:
      `env | cut -d= -f1 | grep -i anthropic`). Tanımlıysa `.env`'deki anahtarı gölgeler
      (`load_dotenv(override=False)`), F3'ten önce çözülür. `api.anthropic.com` erişilebilir mi?
      → İkisi de **tanımlı değil**; `ANTHROPIC_BASE_URL` **tanımlı** (düzeltildi, `4002898`, §10).
      `api.anthropic.com` erişilebilir (kökte 404, TLS ve vekil geçti).
- [x] `check.py` (hızlı), sonra `check.py --full` (arka planda, oturum etkin): sonuç ve süre.
      → Hızlı `check.py` **12/12**, 115 s (ölçüldü). `--full` bulutta **24/24**, ~63 dk (3793 s; adversaryal 3220 s; 4 vCPU) (ikinci routine oturumu, `74d9da1`); birim testleri 833 passed / 5 skipped.
- [ ] `git push` yalnız oturumun kendi dalına gidiyor mu, etiket push'u gerçekten reddediliyor mu?
      → Kısmen: push oturumun kendi dalına gidiyor, ama routine oturumu `master`da başladığı için o
      dal `master`dı ve `origin/master`a push kabul edildi (§13). Etiket push'u **açık**.

Listeye eklenen açık maddeler (24 Eylül; yukarıdaki açık maddelerle birlikte sıradaki normal
oturumda ölçülür):

- [~] Kurulum betiği alanından gerçek koşu: `setup_env.status` (`mode=all`), toplam süre, günlükteki
      `repository:` satırı, uv önbellek ısıtmasının süresi.
      → Alanın yapacağı koşu oturum içinden temiz önekte ölçüldü: `mode=all` **234 s** (çekim 58,
      Python 1, uv ön ısıtma 11, `setup_lean` 144, REPL 26; 11 GB), `repository: /home/user/asd`.
      Alanın kendisinden (Claude'dan önce) koşu ve anlık görüntünün `/opt`'u koruması **açık**:
      kullanıcı betiği yapıştırınca ilk oturumda `/opt/mathverify-logs/setup_env.status` okunur.
- [x] Platformun kendisinin tetiklediği kanca: süre ve durum bloğu.
      → İkinci routine oturumunda kanca açılışta **kendiliğinden** çalıştı: 10 s, 3.14 henüz yokken
      yedek 3.12.3, `.venv` 9 s, Lean arka planda başlatıldı; Lean 239 s'de hazır.
- [x] `CLAUDE_ENV_FILE` ile dışa aktarılan değişkenler (`MATHVERIFY_LEAN_REPL`, `ELAN_HOME`, …)
      oturumun sonraki `Bash` komutlarına ulaşıyor mu?
      → **Evet**: dört değişken ve `PATH` sonraki her komutta görünüyor; `$CLAUDE_ENV_FILE`
      komutun içinde boş (platform kabuk anlık görüntüsüyle enjekte ediyor), elle `source` gerekmez.
- [x] Tam Lean taraması bulutta (`harness.run_lean --timeout 45`, `check.py --full`'un parçası).
      → `run_lean` 150 s, 121 sertifika, FP 0, junk 0/17. Bir Lean istemcisinin bulutta bellek
      tüketimi ayrıca ölçülmedi (WSL'de ~7.2 GB PSS).
- [x] Yedek yorumlayıcı 3.12.3 (Ubuntu 24.04) ile takım: Lean kurulurken 824 passed / 14 skipped
      (9'u Lean henüz yok, 3'ü root altında salt okunur dizin taklit edilemediği için, 1 isteğe
      bağlı indirme, 1 kapsam dışı ifade).
- [x] Uzun `--full` sırasında makine geri alınıyor mu? → Hayır: ajan arka plan işini boşta
      beklerken koşu bitti ve ajan bildirimle uyandı (63 dk). Kural yine de geçerli: gerekirse
      kısa durum komutlarıyla oturum etkin tutulur.
- [x] Ortamın stop hook'u: `~/.claude/stop-hook-git-check.sh` commit edilmemiş değişiklik görünce
      commit + push ister (`check.py` `reports/`'u yeniden yazar). Normal oturumda raporlar
      commit edilir; teşhis oturumunda yok sayılır.

**Düzeltme (24 Eylül 2026, gece, ilk normal oturum; HANDOFF §0.11):**

- [x] Kurulum betiği çalışırken checkout nerede? → `/home/user/asd` (`18fd298`), betik koşarken
      hazırdı (`setup_env.log`: `repository:` satırı). `CLAUDE_PROJECT_DIR`'in o anda tanımlı olup
      olmadığı hâlâ bilinmiyor (önyükleyici checkout'u `/home/*/*` aramasıyla bulur).
- [x] Kurulum betiği alanından gerçek koşu → **başarısız**: `mode=all`, `total=0s`, araç ref'i 401
      (kimliksiz; GitHub vekili betikten sonra bağlanıyor). Kanca devraldı: Lean 167 s'de hazır.
- [x] Aynı sohbete dönüş → ~50 dk sonra makine yeniden başlatılmıştı, disk korunmuştu; kanca 15 s,
      Lean HAZIR, kurulum betiği yeniden koşmadı.
- [x] Değişikliğin kendisi bulutta: `check.py --full` **24/24** (`b042729`, 22:15–22:55 UTC, aşamaların toplamı 2344 s ≈ 39 dk: pytest 98, `run_eval` 58, `run_lean` 92, adversaryal 1985, sağlamlık 79, kalibrasyon 31 s); birim testleri 840 passed / 5 skipped; kapı değerleri önceki koşularla aynı (121 sertifika, FP 0, junk 0/17, 21 139 saldırıda %0, 0/448, 0/214, 0/46, 0/184, 0/6); raporlarda yalnız süre satırları değişti.
- [ ] **Belirteçle kurulum** (`MATHVERIFY_GITHUB_TOKEN`, "Senin yapman gerekenler" 3. madde,
      değişiklik `master`a birleştikten sonra): yeni sohbette `setup_env.status` `OK mode=all`,
      `fetch_artifacts.log`'da "retrying the fetch with MATHVERIFY_GITHUB_TOKEN" ve "the token fetch
      succeeded", uv ön ısıtma süresi, kanca "Lean: HAZIR" ile açılıyor mu; değişkenin kurulum
      betiğine ulaştığı (belge bunu açıkça söylemiyor).
- [ ] Anlık görüntü `/opt`'u koruyor mu: belirteçli koşudan sonraki **ikinci** yeni sohbette kanca
      Lean'i ilk anda "HAZIR" buluyor ve `setup_env.log`'a yeni bir `mode=all` satırı eklenmiyor mu.

## 13. Bulut routine istemleri

Routine: claude.ai'de zamanlanmış ya da tek seferlik bir bulut ajanı (24 Eylül'de `claude --cloud`
etkileşimli terminal istediği için tanı böyle koşturuldu, DECISIONS §44).

- **Ölçülen davranış (24 Eylül):** routine oturumu deponun varsayılan dalı `master`da başladı;
  "oturumun kendi dalı" `master`dı. İstem "oturumun kendi dalına push et" dediği için oturum
  `bulut-2026-09-24`'ü `master`a ileri sardı, tanı raporunu ekledi ve `origin/master`'a push etti
  (`572ef57`). `master` birleştirmesi son doğrulamadan ve yedekten önce oldu (DECISIONS §45, §9).
- **Kural:** bir bulut routine istemi push hedefini açıkça **yeni bir dal** olarak verir (ör.
  "sonucu `tani-YYYY-MM-DD` adlı yeni bir dala push et; `master`a ve başka dallara push etme") ya
  da hiç push istemez ve sonucu son mesajında döndürür. "Kendi dalına", "mevcut dala" gibi
  göreli ifadeler kullanılmaz.
- İstem ayrıca `master`a birleştirme, ileri sarma ya da dal değiştirme istemez; ölçülecek dal
  gerekiyorsa oturum onu yeni bir yerel dala çeker (`git switch -c <yeni-dal> origin/<dal>`).
- Birleştirme yalnız kullanıcı isteyince ve yerelde yedekten sonra yapılır (§9, CLAUDE.md).
