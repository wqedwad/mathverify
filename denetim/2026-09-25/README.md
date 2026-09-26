# 25 Eylül 2026 sistematik denetiminin betikleri

Bu dizin, 25 Eylül denetiminin (DECISIONS §55, HANDOFF §0.13) tekrar-üretim ve ölçüm betiklerini
taşır. Denetim sırasında oturumun geçici alanındaydılar; yeni bir oturum "önce → sonra" sayılarını
yeniden ölçebilsin diye depoya alındılar. Kalıcı kapı bunlar değil, `tests/test_audit_2026_09_25_*.py`
ve `check.py --full`'dur. Bu betikler pyflakes kapısının ve pytest'in dışında durur (denetçi kodu,
`from common import *` gibi kalıplar var).

## Dizinler

| Dizin | Denetçi | İçerik |
|---|---|---|
| `A/` | cebir, sayma | `p*.py` sonda derlemi (25 betik, denetçinin kendi doğru/yanlış etiketleriyle), `repro/r*.py` bulgu başına tekrar betikleri |
| `B/` | kalkülüs, limit, ekstremum, trigonometri | `C*`, `H*`, `M*` bulgu başına tekrar betikleri |
| `C/` | geometri, kombinatorik, seriler, lineer cebir | geometri ajanının düzeltmeden sonraki beklentili betikleri (`!!! MISMATCH` = beklenenden farklı karar) |
| `D/` | ayrıştırıcı, girdi, birleştirme | `repro_D.py` (işaret basmaz, çıktısı okunur) |
| `E/` | Lean formal katmanı | `cases_*.py` denetim vakaları; `calistir_E.py` bunları deterministik katmanda koşturur. Lean'li koşu `tests/test_lean_audit_2026_09_25.py`'dedir |
| `araclar/` | ölçüm | `olc.sh` (hepsini koşturur), `say.py` (sayar), `fuzz_fields.py` (alan/tür taraması), `sweep_eval_inject.py` (enjeksiyon taraması) |

Her betik kaynak ağacını `MV_SRC` ortam değişkeninden alır; verilmezse bu deponun `src/`'si.

## Koşturma (Linux/bulut; Windows'ta `.venv/Scripts/python.exe`)

```bash
# yeni kod
denetim/2026-09-25/araclar/olc.sh src /tmp/olc_yeni
.venv/bin/python denetim/2026-09-25/araclar/say.py /tmp/olc_yeni

# eski kod: ayrı bir worktree kopyasında (ölçüm sürerken değişen bir checkout kullanılmaz)
git worktree add --detach /tmp/eski da963b2
denetim/2026-09-25/araclar/olc.sh /tmp/eski/src /tmp/olc_eski
.venv/bin/python denetim/2026-09-25/araclar/say.py /tmp/olc_eski

# enjeksiyon ve alan taraması (alan taraması yeni kodda ~40 dk; eski kodda ilk öğelerde asılır)
MV_SRC=src PYTHONUTF8=1 .venv/bin/python denetim/2026-09-25/araclar/sweep_eval_inject.py
MV_SRC=src PYTHONUTF8=1 MATHVERIFY_LEAN_REPL=/nonexistent .venv/bin/python denetim/2026-09-25/araclar/fuzz_fields.py
```

Sandbox `spawn` kullandığı için betikler dosyadan ve `if __name__ == "__main__":` altından koşar.

## Ölçülmüş sonuçlar

`araclar/olc.sh` + `say.py`, Lean'siz, 26 Eylül 2026. "Eski" = `da963b2` (denetimden önce), "yeni" = bu
dizinin eklendiği commit. Sayılar betiklerin kendi etiketlerine göre; aşağıdaki bilinen etiket
hataları dahil.

| Grup | Dosya | Eski | Yeni | Yeni koddaki kalanlar |
|---|---|---|---|---|
| A tekrar (`A/repro`) | 17 | 78 | 0 | — |
| A sonda derlemi (`A/p*`) | 25 | 123 (yanlış onay 85, yanlış ret 38) | 5 (2 / 3) | 4 etiket hatası + 1 bilinen sınır |
| B | 23 | 94 | 0 | — |
| C (beklentiden farklı) | 45 | 94 | 20 | 16 UNKNOWN (kapsama, bilerek), 2 beklenti hatası, `dc_eqof_eqstep` ×2 (bilinen sınır) |
| E, deterministik katman | 1 (99+ vaka) | 17 | 0 | — |
| D | 1 | işaret basmaz | bütün vakalar beklenen | — |

Tarama araçları: `sweep_eval_inject.py` eski 113/282 CORRECT, yeni 0/282; `fuzz_fields.py` yeni kodda
4753 durumda kod çalıştırma 0 ve sızan istisna 0, eski kodda ilk öğelerde 18 kod çalıştırma ve
ardından asılma.

## Bilinen etiket hataları ve sınır

- `A/p03_countint.py`: üç "doğru" etiketi yanlış. Kaba kuvvet: (x−2)(x−5) > 0, x < 9 pozitif tam
  sayılarda 4 çözüm; |x−3| > 1, x < 10'da 6; x² − 5x + 4 > 0, 0 ≤ x ≤ 8'de 5. İddialar 6, 7, 6
  yanlıştır; yeni kodun INCORRECT'i doğrudur, `say.py` bunları "yanlış ret" sayar.
- `A/p03b_countint.py`: pozitif tam sayılarda x² = 4'ün tek çözümü var; iddia 1 doğrudur, "yanlış
  onay" sayılan CORRECT doğrudur.
- `C/p_eq1.py` `circ_cubic`: iddia `(x-1)² + (y-2)² + x³ = 9 + x³ - x³ + x³` doğru çembere özdeş (x³
  terimleri sadeleşir); CORRECT doğrudur, beklenti ("INCORRECT") yanlış.
- `C/p_geo3.py` `area_det_len`: alan 8 olan dik ikizkenar üçgenin hipotenüsü 4√2'dir, 8 değil;
  INCORRECT doğrudur, beklenti ve betikteki yorum yanlış.
- `C/p_dcell*.py` `dc_eqof_eqstep`: `equation_of` görevinde "y = 3x + 1" gibi bir eğri denklemi adımı
  "öncüller altında doğru" kuralıyla denetlenemez (öncül yok; doğru adım da her noktada doğru değil);
  ilke 5 gereği atlanır. Bilinen sınır.
- C'deki 16 UNKNOWN, geometri dalının bilerek kabul ettiği kapsama kayıplarıdır (kanıtsız eşdeğer
  doğru biçimleri, sembolik kanıtı olmayan kapalı biçimler, gelenek farkları); hiçbiri doğru cevabı
  reddetmez.
- `A/p13_steps.py` "wrong factor constant": bilinen sınır. `x² − 5x + 6 = 2(x − 2)(x − 3)` adımı
  öncül x² − 5x + 6 = 0'ın çözümlerinde doğrudur; "öncüller altında doğru" kuralı meşru adımları da
  korur (DECISIONS §55).
