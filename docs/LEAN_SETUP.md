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

**Bulutta** bunların hepsini ortamın kurulum betiği yapar (`scripts/cloud/setup_env.sh`, önek
`/opt`); elle kurulum gerekmez. Ayrıntı ve yeniden deneme: `docs/BULUT.md`.

Ölçüm (24 Eylül 2026, WSL içinde temiz `HOME`, bulut düzeni, 4 CPU, araç ref'inden): toplam
141 s; araç zinciri ve `.ltar` indirmesi 0; `lake-manifest.json` aynı; mathlib HEAD `5ed2965`;
`bin/lean` SHA256'sı ve 17 738 dosyalık araç zinciri ağacı WSL kurulumuyla aynı; disk ~12 GB.

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
