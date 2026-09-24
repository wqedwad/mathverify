# lean/ — sabitlenmiş Lean projesi

Bu dizin, L7 katmanının kullandığı Mathlib bağımlı Lean projesinin (`mathverify-lean`) sabitlenmiş
dosyalarını taşır. `scripts/setup_lean.sh` bu dosyaları proje dizinine
(`MATHVERIFY_LEAN_PROJECT`, varsayılan `~/mathverify-lean`) kopyalar; `lake new` ya da
`lake update` çalıştırmaz. Böylece Windows/WSL'deki kurulum ile bulut (Linux) kurulumu aynı
araç zincirini, aynı Mathlib revizyonunu ve aynı bağımlılık revizyonlarını kullanır.

| Dosya | Ne |
|---|---|
| `lakefile.toml`, `lean-toolchain`, `lake-manifest.json`, `MathverifyLean.lean`, `MathverifyLean/Basic.lean` | Çalışan WSL kurulumundaki `~/mathverify-lean` dosyalarının **bayt bayt aynı** kopyaları (2026-09-24, SHA256 eşitliği WSL ile depo arasında doğrulandı) |
| `PINS` | Bash ile okunabilen sabitler: `LEAN_TOOLCHAIN`, `MATHLIB_REV`, `REPL_URL`, `REPL_REV`, `ELAN_VERSION` |
| `.gitattributes` | `* -text`: Git bu dizindeki dosyalarda satır sonu dönüşümü yapmaz (Windows'ta `core.autocrlf=true` olsa da kopyalar bayt bayt aynı kalır) |

Sabitler:

- Araç zinciri `leanprover/lean4:v4.34.0` (elan dizini `leanprover--lean4---v4.34.0`), elan 4.2.4.
- Mathlib `5ed2965256430c3649e86755f9576b54eca72435` (etiket `v4.34.0`) ve `lake-manifest.json`'daki
  8 bağımlılık revizyonu.
- REPL `https://github.com/leanprover-community/repl` @ `646a77338cfee0d09219688efffe122650cee73a`;
  bu revizyonun kendi `lean-toolchain`'i `v4.35.0-rc2` der, `scripts/setup_lean_repl.sh` onu
  `LEAN_TOOLCHAIN` ile değiştirir (WSL kurulumunda da yerel değişiklik olarak böyledir).

Bu dosyalar elle düzenlenmez. Sürüm yükseltmesi yeni bir WSL kurulumundan yeniden kopyalanarak,
`PINS` ve bulut araç ref'i (`refs/arac/bulut-v*`) birlikte güncellenerek yapılır.
