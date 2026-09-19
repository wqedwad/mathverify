# Kalibrasyon raporu (F6, deterministik katmanlar)

Eğitim 149 öğe (75 geçerli / 74 geçersiz) · önsel log-odds 0.0132

Seçilen eşikler (doğrulama kümesinde hedef precision 0.98): **CORRECT ≥ 0.12**, **INCORRECT ≤ -1.69**

## Bölme bazında sonuç (test bölmesi hiçbir uyumda kullanılmadı)

| Bölme | n | Pozitif precision | Negatif precision | Kapsama | fp | fn | UNKNOWN |
|---|---|---|---|---|---|---|---|
| train | 149 | 0.971 | 1.000 | 0.866 | 2 | 0 | 20 |
| val | 62 | 1.000 | 1.000 | 0.855 | 0 | 0 | 9 |
| test | 49 | 1.000 | 1.000 | 0.857 | 0 | 0 | 7 |

## Ölçülen sinyal güvenilirlikleri (eğitim bölmesi)

| Sinyal | destek | geçerli | geçersiz | güvenilirlik | log-odds ağırlığı | kullanıldı |
|---|---|---|---|---|---|---|
| `steps.refute:fail:support` | 43 | 0 | 43 | 0.000 | -3.797 | evet |
| `flag:step_refuted` | 43 | 0 | 43 | 0.000 | -3.797 | evet |
| `certify.algebra:fail:primary` | 15 | 0 | 15 | 0.000 | -2.786 | evet |
| `certify.calculus:fail:primary` | 7 | 0 | 7 | 0.000 | -2.092 | evet |
| `certify.wordproblem:fail:primary` | 6 | 0 | 6 | 0.000 | -1.959 | evet |
| `certify.geometry_numeric:fail:primary` | 5 | 0 | 5 | 0.000 | -1.805 | evet |
| `certify.combinatorics:fail:primary` | 5 | 0 | 5 | 0.000 | -1.805 | evet |
| `mc.consistency:fail:support` | 4 | 0 | 4 | 0.000 | -1.623 | hayır (destek < eşik) |
| `certify.geometry:fail:primary` | 3 | 0 | 3 | 0.000 | -1.399 | hayır (destek < eşik) |
| `certify.series:fail:primary` | 3 | 0 | 3 | 0.000 | -1.399 | hayır (destek < eşik) |
| `certify.limits:fail:primary` | 3 | 0 | 3 | 0.000 | -1.399 | hayır (destek < eşik) |
| `certify.trig:fail:primary` | 3 | 0 | 3 | 0.000 | -1.399 | hayır (destek < eşik) |
| `certify.counting:fail:primary` | 2 | 0 | 2 | 0.000 | -1.112 | hayır (destek < eşik) |
| `certify.linalg:pass:primary` | 10 | 8 | 2 | 0.800 | +1.085 | evet |
| `certify.algebra:pass:primary` | 41 | 31 | 10 | 0.756 | +1.055 | evet |
| `certify.wordproblem:pass:primary` | 20 | 15 | 5 | 0.750 | +0.968 | evet |
| `certify.limits:pass:primary` | 5 | 4 | 1 | 0.800 | +0.903 | evet |
| `certify.trig:pass:primary` | 5 | 4 | 1 | 0.800 | +0.903 | evet |
| `certify.calculus:pass:primary` | 11 | 8 | 3 | 0.727 | +0.798 | evet |
| `certify.extremum:fail:primary` | 1 | 0 | 1 | 0.000 | -0.706 | hayır (destek < eşik) |
| `sanity:fail:support` | 1 | 0 | 1 | 0.000 | -0.706 | hayır (destek < eşik) |
| `certify.geometry:pass:primary` | 4 | 3 | 1 | 0.750 | +0.680 | hayır (destek < eşik) |
| `certify.series:pass:primary` | 7 | 5 | 2 | 0.714 | +0.680 | evet |
| `certify.extremum:pass:primary` | 4 | 3 | 1 | 0.750 | +0.680 | hayır (destek < eşik) |
| `certify.counting:pass:primary` | 1 | 1 | 0 | 1.000 | +0.680 | hayır (destek < eşik) |
| `certify.geometry_numeric:pass:primary` | 7 | 4 | 3 | 0.571 | +0.210 | evet |
| `certify.combinatorics:pass:primary` | 7 | 4 | 3 | 0.571 | +0.210 | evet |
| `mc.consistency:pass:support` | 129 | 68 | 61 | 0.527 | +0.094 | evet |
| `flag:z3_unsupported` | 2 | 1 | 1 | 0.500 | -0.013 | hayır (destek < eşik) |

## Abstain eğrisi (test bölmesi)

| Eşik ±z | Kapsama | Pozitif precision | Negatif precision | fp | fn |
|---|---|---|---|---|---|
| 0.0 | 1.000 | 0.875 | 1.000 | 4 | 0 |
| 0.5 | 0.735 | 1.000 | 1.000 | 0 | 0 |
| 1.0 | 0.592 | 1.000 | 1.000 | 0 | 0 |
| 1.5 | 0.408 | 1.000 | 1.000 | 0 | 0 |
| 2.0 | 0.408 | 1.000 | 1.000 | 0 | 0 |
| 3.0 | 0.327 | n/a | 1.000 | 0 | 0 |
| 4.0 | 0.327 | n/a | 1.000 | 0 | 0 |
| 6.0 | 0.327 | n/a | 1.000 | 0 | 0 |
| 8.0 | 0.122 | n/a | 1.000 | 0 | 0 |
| 12.0 | 0.061 | n/a | 1.000 | 0 | 0 |
