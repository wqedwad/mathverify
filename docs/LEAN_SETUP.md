# Lean 4 + Mathlib kurulumu (F5)

L7 katmanı WSL içinde çalışan kalıcı bir Lean REPL kullanır. Kurulum tek seferliktir.

## Kurulum

```bash
wsl -d Ubuntu -- bash /mnt/c/Users/kullanici/mathverify/scripts/setup_lean.sh
```

Bu betik `elan`'ı kurar, `~/mathverify-lean` altında Mathlib bağımlı bir proje açar ve önceden
derlenmiş olean cache'ini indirir (~6.7 GB, 8546 dosya). Cache'te üst düzey `Mathlib.olean`
eksik gelirse (upstream ile küçük bir sapma olduğunda olur) tamamlamak için:

```bash
wsl -d Ubuntu -- bash /mnt/c/Users/kullanici/mathverify/scripts/lean_fix.sh
```

Sonra REPL'i derleyin:

```bash
wsl -d Ubuntu -- bash /mnt/c/Users/kullanici/mathverify/scripts/setup_lean_repl.sh
```

Durum kontrolü:

```bash
wsl -d Ubuntu -- bash /mnt/c/Users/kullanici/mathverify/scripts/lean_status.sh
```

## Doğrulama

```bash
.venv/Scripts/python.exe -m harness.run_lean --timeout 45
```

Rapor `reports/lean_report.md` dosyasına yazılır. Beklenen: ifade üretilen öğelerin çoğunda
sertifika, **yanlış cevaplı hiçbir öğede kanıt yok (FP = 0)**.

## Çalışma zamanı ayarları

| Değişken | Varsayılan | Anlamı |
|---|---|---|
| `MATHVERIFY_LEAN_PROJECT` | `~/mathverify-lean` | Mathlib bağımlı proje dizini |
| `MATHVERIFY_LEAN_REPL` | `~/repl/.lake/build/bin/repl` | REPL ikilisi |
| `MATHVERIFY_WSL_DISTRO` | `Ubuntu` | WSL dağıtımı |

## Kurulumda karşılaşılan iki tuzak (ölçülmüş)

1. **`LEAN_PATH=... exec repl` değişkeni dışa aktarmaz.** `exec` özel bir builtin olduğu için
   atama kabuğa kalır, çocuk sürece geçmez; Lean o zaman Mathlib'i hiç görmez ve `import Mathlib`
   3 saniyede boş bir ortam yaratır (normali ~13 s). Belirtisi: `ℝ` ve hatta `+` ayrıştırılamaz,
   `Unknown constant OfNat` hatası. Çözüm: `lake env <repl>` ile çalıştırmak. İstemci ayrıca
   açılışta ortamın gerçekten Mathlib olduğunu bir örnek teoremle doğrular.
2. **Matris literalleri tip belirtimi ister.** `!![1, 1; 2, 4]` bağlamsız kullanıldığında ℕ
   olarak elaborate olur ve `failed to synthesize CommRing ℕ` hatası verir. Yazıcı her matrisi
   `(!![...] : Matrix (Fin n) (Fin m) ℝ)` biçiminde üretir. Ayrıca bu araç zincirinde `*ᵥ`
   gösterimi elaborate olmuyor; `Matrix.mulVec` açıkça yazılır ve `dotProduct` kök ad alanındadır.
