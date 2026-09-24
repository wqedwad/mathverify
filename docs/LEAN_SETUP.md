# Lean 4 + Mathlib kurulumu (F5)

L7 katmanı WSL içinde çalışan kalıcı bir Lean REPL kullanır. Kurulum tek seferliktir.

> **Düzeltme (24 Eylül 2026):** yalnız Windows'ta WSL içinde. Linux'ta (Claude Code bulut
> oturumları dahil) aynı REPL WSL'siz, yerel `bash -lc` ile çalışır (DECISIONS §40). Sürümler
> artık depoda sabit (`lean/PINS`, DECISIONS §38). Bulut kurulumu `docs/BULUT.md`'de.

## Sabit sürümler

`lean/PINS` (bash ile okunur) ve `lean/` altındaki proje dosyaları (WSL kurulumunun bayt bayt
kopyası, `lean/README.md`):

| Bileşen | Sürüm |
|---|---|
| Araç zinciri | `leanprover/lean4:v4.34.0` (elan dizini `leanprover--lean4---v4.34.0`) |
| elan | 4.2.4 |
| Mathlib | `5ed2965256430c3649e86755f9576b54eca72435` (etiket `v4.34.0`) + `lake-manifest.json`'daki bağımlılık revizyonları |
| REPL | `https://github.com/leanprover-community/repl` @ `646a77338cfee0d09219688efffe122650cee73a`; kendi `lean-toolchain`'i `v4.35.0-rc2` der, `setup_lean_repl.sh` onu `v4.34.0` yapar |

Kurulum betikleri `lake new` ve `lake update` **çalıştırmaz**: proje dosyalarını `lean/`'dan
kopyalar, her paketin manifest revizyonunda olduğunu denetler ve duman testi geçmezse düşer.
Sürüm yükseltmesi yeni bir WSL kurulumundan `lean/` ve `PINS` birlikte yeniden kopyalanarak
yapılır; bulutun araç ref'i de yenilenir (`docs/BULUT.md` §11).

## Kurulum — Windows (WSL)

```bash
wsl -d Ubuntu -- bash /mnt/c/Users/kullanici/mathverify/scripts/setup_lean.sh
```

Bu betik `elan`'ı kurar, `~/mathverify-lean` altında Mathlib bağımlı bir proje açar ve önceden
derlenmiş olean cache'ini indirir (~6.7 GB, 8546 dosya). Cache'te üst düzey `Mathlib.olean`
eksik gelirse (upstream ile küçük bir sapma olduğunda olur) tamamlamak için:

```bash
wsl -d Ubuntu -- bash /mnt/c/Users/kullanici/mathverify/scripts/lean_fix.sh
```

> **Düzeltme (24 Eylül 2026):** betik artık proje "açmaz", `lean/` dosyalarını
> `~/mathverify-lean`'e kopyalar ve sabit sürümleri kurar. `lean_fix.sh` adımı artık
> **kendiliğinden** yapılıyor: bu Mathlib revizyonunun önbelleğinde iki modül eksik (kök `Mathlib`
> ve `Mathlib/Probability/Kernel/Invariance`; `cache get` sunucuda da bulamadı) ve
> `setup_lean.sh` ikisini `lake build Mathlib` ile derler (4 CPU'da 12 s). 20'den fazla modül
> eksikse saatler sürecek tam derlemeye girmeden düşer. `lean_fix.sh` yalnız eski kurulumları
> onarmak için duruyor.

Sonra REPL'i derleyin:

```bash
wsl -d Ubuntu -- bash /mnt/c/Users/kullanici/mathverify/scripts/setup_lean_repl.sh
```

Durum kontrolü:

```bash
wsl -d Ubuntu -- bash /mnt/c/Users/kullanici/mathverify/scripts/lean_status.sh
```

## Kurulum — Linux ve bulut

Aynı betikler, WSL'siz, proje kökünden:

```bash
bash scripts/setup_lean.sh
bash scripts/setup_lean_repl.sh
bash scripts/lean_status.sh
```

Varsayılanlar `~/.elan`, `~/mathverify-lean`, `~/repl`; hepsi ortam değişkenleriyle değişir
(aşağıdaki tablo). İnternetten indirmek yerine depodaki araç ref'inden, ağ kapalıyken kurmak için:

```bash
bash scripts/fetch_artifacts.sh ~/.cache/mathverify/arac
MATHVERIFY_ARTIFACT_DIR=~/.cache/mathverify/arac bash scripts/setup_lean.sh
MATHVERIFY_ARTIFACT_DIR=~/.cache/mathverify/arac bash scripts/setup_lean_repl.sh
```

`setup_lean.sh` araç dizininde bulduğu her bileşeni (elan, araç zinciri, Mathlib `.ltar`
önbelleği) SHA256 ile doğrulayıp vekil değişkenleri kapalı bir porta yönlendirilmişken kurar;
gizli bir indirme denemesi böylece düşer. Bulamadığını internetten indirir.

> **Düzeltme (24 Eylül 2026, `eba49b5`):** "bulamadığını internetten indirir" yalnız
> `MATHVERIFY_LEAN_OFFLINE` verilmediğinde (ya da `0` iken) doğru. `MATHVERIFY_LEAN_OFFLINE=1`
> sıkı çevrimdışı moddur (`scripts/cloud/setup_env.sh` onu her zaman verir): elan ya da araç zinciri
> indirmesi, `lake exe cache get`, Lake'in paket klonu ve `apt-get install zstd` dahil her çevrimiçi
> yedek reddedilir; eksik bir artefakt betiği hiçbir şey yazmadan saniyeler içinde durdurur. Neden:
> gözden geçirmede başarısız bir çekimden sonra kurulum `cache.mathlib.org`'a karşı
> `lake exe cache get` içinde 24 dakikadan fazla asılı kaldı; o adres bulutta kapalı
> (`docs/BULUT.md` §3.1). `setup_lean_repl.sh` de aynı değişkene uyar (klon ya da `git fetch` yok).

**Ek (24 Eylül 2026, `eba49b5`, `a02e65c`): kurulum sırası ve var olan projenin korunması.**

1. **Önce doğrulama.** Koşunun kullanacağı her artefakt, projeye ya da araç zincirine dokunmadan
   `SHA256SUMS.full`'a karşı doğrulanır; uyuşmazlık ya da (çevrimdışı modda) eksik artefakt koşuyu
   orada bitirir.
2. **Önce disk.** Büyük bir yazmadan önce boş alan denetlenir: yeni bir proje için ölçülen 7.7 GB
   (7.2 GB proje + 448 MB `.ltar`), araç zinciri kurulu değilse +3.0 GB, üstüne 1 GB pay. Var olan
   proje sabitlere uyuyorsa yalnız eksik kalan kısım aranır. WSL içinde aynı miktar, sanal diski
   tutan Windows sürücüsünde de aranır (beşinci tur; aşağıdaki uyarı).
3. **Sabitlere uyan proje yerinde tamamlanır** (kalan iş yalnız dosya ekler).
4. **Uymayan proje yerinde yeniden yazılmaz.** Yeni proje yanında `.<proje>.stage.<pid>` dizininde
   kurulur ve `import Mathlib` duman testinden geçer. Sonra eski proje `.<proje>.old.<pid>`'e
   çekilir, yenisi yerine adlandırılır ve duman testi yeniden adlandırmadan **sonra**, son yolunda
   bir kez daha koşar (ilki aşama yolunda koşmuştu). Geçerse eskisi silinir; geçmezse yenisi geri
   çekilip eskisi yerine konur ve koşu düşer. Yarıda kalmış bir değişimden kalan
   `.<proje>.old.<pid>` bir sonraki koşuda, proje yoksa geri konur, varsa silinir; ölü koşuların
   `.stage`/`.ltar` dizinleri silinir. `setup_lean_repl.sh` REPL checkout'u için benzer bir
   aşamalı değişim yapar (eski checkout yalnız REPL duman testi geçince silinir).
5. **Mathlib `.ltar` yeri.** `setup_env.sh` altında `$OPT/.mathlib-ltar` (kurulumdan sonra silinir).
   `setup_lean.sh` tek başına, araç diziniyle ve `MATHLIB_CACHE_DIR` verilmeden koşunca projenin
   yanında geçici `.<proje>.ltar.<pid>` (çıkışta silinir). Araç dizini yoksa Mathlib'in kendi kuralı:
   `MATHLIB_CACHE_DIR`, yoksa `$XDG_CACHE_HOME/mathlib`, yoksa `$HOME/.cache/mathlib`.

Ölçüm: `tests/test_cloud_scripts.py` (commit mesajlarına göre dosyanın tamamı: `eba49b5` WSL'de 46 passed /
1 skipped, `a02e65c` WSL'de kullanıcı olarak 59 passed / 1 skipped, root olarak 56 passed / 4 skipped); aşamalı değişimin duman işlevi kullanıcının WSL
kurulumunda gerçek Lean'le 26 s'de geçti ve projeye dosya yazmadı. Gerçek Lean'le uçtan uca bir
aşamalı güncelleme ölçülmedi **[DOĞRULANMADI]** (WSL diski doldu, aşağıdaki uyarı).

**Bulutta** bunların hepsini ortamın kurulum betiği yapar (`scripts/cloud/setup_env.sh`, önek
`/opt`); elle kurulum gerekmez. Ayrıntı ve yeniden deneme: `docs/BULUT.md`.

Ölçüm (24 Eylül 2026, WSL içinde temiz `HOME`, bulut düzeni, 4 CPU, araç ref'inden): toplam
141 s; araç zinciri ve `.ltar` indirmesi 0; `lake-manifest.json` aynı; mathlib HEAD `5ed2965`;
`bin/lean` SHA256'sı ve 17 738 dosyalık araç zinciri ağacı WSL kurulumuyla aynı; disk ~12 GB.

**Ölçüm (24 Eylül 2026, gerçek bulut, routine oturumu, `4d01ba2`):** kancanın başlattığı kurulumda
`setup_lean` 119 s (önbellekte eksik `Mathlib/Probability/Kernel/Invariance` ve kök `Mathlib`
derlendi, tuzak 3; duman testi 8 s), `setup_lean_repl` 19 s; disk `/opt/elan` 3.0G,
`/opt/mathverify-lean` 7.2G, o sürümde silinmeyen `/root/.cache/mathlib` 448M. Ayrıntı
`docs/bulut_tani_2026-09-24.md` §7.

> **Uyarı (24 Eylül 2026): WSL içinde `df` C:'yi görmez.** WSL'nin kök dosya sistemi Windows'ta tek
> bir sanal disk dosyasıdır (`ext4.vhdx`; bu makinede
> `C:\Users\kullanici\AppData\Local\wsl\{WSL-GUID}\ext4.vhdx`). WSL içinde
> `df` o sanal diskin kendi boyutunu gösterir (olay sırasında 942 GB boş), C:'deki gerçek boş alanı
> değil. 24 Eylül'de bir ajanın gerçek Lean test kurulumları WSL içinde `/var/tmp` altına ~60 GB
> yazdı: `.vhdx` 103.8 GB'a büyüdü, C: 0 bayta düştü ve WSL açılamadı (DECISIONS §49). Silinen
> dosyalar `.vhdx`'i küçültmez: temizlik ve `fstrim`'den sonra WSL 15 GB kullanıyor ama `.vhdx` hâlâ
> 103.8 GB (bu belge yazılırken ölçüldü; C:'de 6.1 GB boş). **Düzeltme (24 Eylül 2026, 16:54):** kullanıcının yetkisiyle sıkıştırıldı. UAC onayıyla yönetici PowerShell'de `wsl --shutdown` + `diskpart` (`attach vdisk readonly`, `compact vdisk`, `detach vdisk`) çalıştı, 20 s sürdü: `.vhdx` 103.79 → 15.98 GB, C: boş alanı 6.10 → 93.95 GB. Ardından WSL açıldı; Lean 4.34.0, Mathlib `5ed2965` ve REPL duman testi (`{"env": 0}`) sağlam. Küçültmek yönetici ister: `wsl --shutdown`,
> sonra `diskpart` içinde `select vdisk file="<.vhdx yolu>"`, `attach vdisk readonly`,
> `compact vdisk`, `detach vdisk`. Önlem (beşinci tur): `setup_lean.sh`'in boş alan denetimi WSL
> altında dağıtımın `ext4.vhdx`'ini tutan Windows sürücüsüne de bakar (sürücü kayıt defterindeki
> `BasePath`'ten, yoksa `%LOCALAPPDATA%`'dan bulunur, o da olmazsa `/mnt/c`; elle vermek için
> `MATHVERIFY_WSL_DRIVE_DIR`) ve yeni kurulumu yukarıdaki ölçülen boyutla hesaplar. Ajanlar WSL'de
> büyük bir kurulumdan önce C:'nin boş alanına Windows tarafından bakar.

## Doğrulama

```bash
.venv/Scripts/python.exe -m harness.run_lean --timeout 45      # Windows
PYTHONUTF8=1 .venv/bin/python -m harness.run_lean --timeout 45 # Linux / bulut
```

Rapor `reports/lean_report.md` dosyasına yazılır. Beklenen: ifade üretilen öğelerin çoğunda
sertifika, **yanlış cevaplı hiçbir öğede kanıt yok (FP = 0)**.

> **Ek (24 Eylül 2026):** rapor artık Lean'in taramanın başında ve sonunda erişilebilir olup
> olmadığını ve Lean'e ulaşamayan ifade sayısını da yazar. `scripts/check.py --full`'da Lean
> yoksa ya da tarama sırasında kaybolursa "Lean erişilebilir" dahil dört Lean kapısı düşer
> (DECISIONS §39); "sertifika 0, FP 0" Lean'siz bir makinede artık geçmez.
>
> **Ek (24 Eylül 2026, `7993055`, `5e16a31`, `911aca5`):** Lean'e "ulaşmak" da yetmez; Lean'in
> cevap vermesi gerekir. Her ifadeli kayıt `lean_answered`, `n_attempts`, `n_unanswered` taşır.
> Junk ifadelerinde ve yanlış cevaplı öğelerde her taktik denemesi cevaplanmış olmalı
> (`n_unanswered == 0`) ve ispatlanmış ifadenin denetim sondalarından hiçbiri cevapsız kalmamalı;
> yoksa junk ve FP kapıları düşer ("Lean kısmen cevap vermedi k/M deneme"). Zaman aşımı, ölü REPL,
> yazma hatası, bozuk JSON ve hatasız başarısızlık cevap sayılmaz. Doğru cevaplı öğede zaman aşımı
> yalnız sertifikayı kaybettirir. `prove.py`'nin denetimi de vakum ya da hipotezsiz sondası gerçek
> bir Lean hükmü almazsa temiz sayılmaz (`audit["unanswered"]`, ilke 7); önce bu durumda
> hipotezleri çelişen bir ifade temiz sertifika alabiliyordu. Ölçüm (Windows, gerçek tam tarama,
> 45 s zaman aşımı): 121 sertifika (değişmedi), FP 0, junk 0/17; 869/869 deneme ve 58/58 denetim
> sondası cevaplı, en yavaş deneme 3.0 s (DECISIONS §46–47).

## Çalışma zamanı ayarları

| Değişken | Varsayılan | Anlamı |
|---|---|---|
| `MATHVERIFY_LEAN_PROJECT` | `~/mathverify-lean` | Mathlib bağımlı proje dizini |
| `MATHVERIFY_LEAN_REPL` | `~/repl/.lake/build/bin/repl` | REPL ikilisi |
| `MATHVERIFY_WSL_DISTRO` | `Ubuntu` | WSL dağıtımı |

**Ek (24 Eylül 2026)**, kurulum betikleri ve Linux/bulut için:

| Değişken | Varsayılan | Anlamı |
|---|---|---|
| `ELAN_HOME` | `$HOME/.elan` | elan evi; istemci `PATH`'e `${ELAN_HOME:-$HOME/.elan}/bin` ekler (bulutta `/opt/elan`) |
| `MATHVERIFY_ARTIFACT_DIR` | — (`fetch_artifacts.sh` için `$HOME/.cache/mathverify/arac`) | araç dizini; burada bulunan bileşenler çevrimdışı kurulur |
| `MATHVERIFY_ARTIFACT_URL` / `_REF` / `_SRC` | `origin` / `refs/arac/bulut-v2` / — | araç ref'inin kaynağı; `_SRC` yerel bir `parts/` dizini (`docs/BULUT.md` §11) |
| `MATHVERIFY_OPT` | `/opt` | bulut kurulum öneki; `setup_lean.sh` yalnız `$MATHVERIFY_OPT/python3.14`'ü yedek zstd açıcı olarak arar |
| `MATHLIB_CACHE_DIR`, `XDG_CACHE_HOME` | `$HOME/.cache/mathlib` | Mathlib `.ltar` önbelleği, Mathlib'in kendi kuralıyla |
| `MATHVERIFY_SKIP_LEAN` | — | `1`: bulut oturum kancası Lean kurulumunu başlatmaz |
| `MATHVERIFY_LEAN_OFFLINE` | `0` (`setup_env.sh` her zaman `1` verir) | (24 Eylül'de eklendi) `1`: kurulum betikleri her çevrimiçi yedeği reddeder (yukarıda) |
| `MATHVERIFY_WSL_DRIVE_DIR` | kayıt defterindeki `BasePath`, yoksa `%LOCALAPPDATA%`, yoksa `/mnt/c` | (24 Eylül, beşinci tur) yalnız WSL: `ext4.vhdx`'i tutan Windows sürücüsünde bir dizin; `setup_lean.sh` o sürücünün boş alanını da denetler (yukarıdaki WSL disk uyarısı) |

**Düzeltme (24 Eylül 2026, `eba49b5`):** `MATHLIB_CACHE_DIR` satırındaki varsayılan
(`$HOME/.cache/mathlib`) yalnız araç dizini olmadan yapılan kurulumda geçerli. Araç diziniyle
`setup_lean.sh` `.ltar`'ları projenin yanında geçici `.<proje>.ltar.<pid>`'e, bulut kurulumu
`$OPT/.mathlib-ltar`'a açar ve ikisi de kurulumdan sonra silinir (yukarıda, madde 5). Routine
oturumunun ölçtüğü `/root/.cache/mathlib` (448 MB) bu değişiklikten önceki sürümdendi.

`MATHVERIFY_WSL_DISTRO` yalnız Windows'ta okunur.

## İstemci REPL'i nasıl başlatır

`src/mathverify/formal/lean_client.py` şu kabuk satırını çalıştırır:
`cd <proje> && export PATH="${ELAN_HOME:-$HOME/.elan}/bin:$PATH" && lake env <repl>`.
Windows'ta `wsl -d <distro> -- bash -lc "<satır>"`, Linux'ta yerel `bash -lc "<satır>"`.
Linux'ta başlatıcı kendi süreç grubunda açılır ve zaman aşımında `killpg` ile bütün grup
öldürülür. Başlatıcı yoksa ya da (Linux'ta) REPL ikilisi yoksa `LeanUnavailable` fırlatılır ve
`lake env` hiç başlatılmaz. Açılışta açık bir ℝ sondası
(`example : (2 : ℝ) + 2 = 4 := by norm_num`) ortamın gerçekten Mathlib olduğunu doğrular.

## Kurulumda karşılaşılan iki tuzak (ölçülmüş)

1. **`LEAN_PATH=... exec repl` değişkeni dışa aktarmaz.** `exec` özel bir builtin olduğu için
   atama kabuğa kalır, çocuk sürece geçmez; Lean o zaman Mathlib'i hiç görmez ve `import Mathlib`
   3 saniyede boş bir ortam yaratır (normali ~13 s). Belirtisi: `ℝ` ve hatta `+` ayrıştırılamaz,
   `Unknown constant OfNat` hatası. Çözüm: `lake env <repl>` ile çalıştırmak. İstemci ayrıca
   açılışta ortamın gerçekten Mathlib olduğunu bir örnek teoremle doğrular.

   **Düzeltme (24 Eylül 2026):** hızlı açılış **tek başına belirti değildir**. Gerçek bir Mathlib
   ortamı sıcak önbellekle 2.6 s'de açıldı (soğuk ~30 s); "normali ~13 s" o makinenin o anki
   ölçümüydü. Boş ortamı ayıran süre değil, `_spawn`'daki açık ℝ sondasıdır: sonda temiz
   geçmezse `LeanUnavailable`.
2. **Matris literalleri tip belirtimi ister.** `!![1, 1; 2, 4]` bağlamsız kullanıldığında ℕ
   olarak elaborate olur ve `failed to synthesize CommRing ℕ` hatası verir. Yazıcı her matrisi
   `(!![...] : Matrix (Fin n) (Fin m) ℝ)` biçiminde üretir. Ayrıca bu araç zincirinde `*ᵥ`
   gösterimi elaborate olmuyor; `Matrix.mulVec` açıkça yazılır ve `dotProduct` kök ad alanındadır.

**Ek (24 Eylül 2026), Linux ve bulut kurulumunda ölçülen tuzaklar:**

3. **Önbellek eksik.** Mathlib `5ed2965` için hazır önbellekte kök `Mathlib` ve
   `Mathlib/Probability/Kernel/Invariance` yok; `setup_lean.sh` ikisini derler (yukarıda).
4. **Yetim REPL.** Yerel Linux'ta `lake env` REPL'i çocuk süreç olarak başlatır; yalnız
   başlatıcıyı öldürmek REPL'i (~6.9 GB) yetim bırakıyordu. Çözüm: süreç grubu + `killpg`
   (DECISIONS §40).
5. **REPL ikilisi yokken `lake env`.** `lake env` önce projenin eksik bağımlılıklarını getirir,
   ikilinin yokluğunu sonra fark eder (oyuncak projede ölçüldü: paket dizini ve yeni bir
   `lake-manifest.json` kaldı, çıkış 255). Yarım bir kurulumda her çağrı Mathlib'i yeniden
   klonlardı. Çözüm: istemci ikiliyi önce kendisi arar.
6. **Root kurulumu, root olmayan oturum.** `lake`/`leantar` önbellekten gelen oleanları 0600 ile
   yazar; git de başkasına ait checkout'ta "dubious ownership" ile reddeder ve `lake` o zaman
   paketi silip yeniden klonlar (git `PATH`'te yokken `lake env`'in `.lake/packages/mathlib`'i
   sildiği ölçüldü). `setup_lean.sh` root olarak kurarken her şeyi herkese okunur yapar ve paket
   checkout'larını sistem git ayarında `safe.directory` olarak kaydeder.
7. **`.zst` açıcı.** Araç zinciri arşivi zstd ile sıkıştırılmış; `zstd` yoksa Python ≥ 3.14'ün
   `compression.zstd` modülü (ya da araç ref'indeki CPython) kullanılır, root ise `apt-get install
   zstd`.
