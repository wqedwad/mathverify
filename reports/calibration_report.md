# Kalibrasyon raporu (F6, deterministik katmanlar)

Eğitim 160 öğe (80 geçerli / 80 geçersiz) · önsel log-odds 0.0

Seçilen eşikler (doğrulama kümesinde hedef precision 0.98): **CORRECT ≥ 0.07**, **INCORRECT ≤ -0.35**

## Bölme bazında sonuç (test bölmesi hiçbir uyumda kullanılmadı)

| Bölme | n | Pozitif precision | Negatif precision | Kapsama | fp | fn | UNKNOWN |
|---|---|---|---|---|---|---|---|
| train | 160 | 0.971 | 0.972 | 0.881 | 2 | 2 | 19 |
| val | 66 | 1.000 | 1.000 | 0.879 | 0 | 0 | 8 |
| test | 54 | 1.000 | 1.000 | 0.870 | 0 | 0 | 7 |

## Ölçülen sinyal güvenilirlikleri (eğitim bölmesi)

| Sinyal | destek | geçerli | geçersiz | güvenilirlik | log-odds ağırlığı | kullanıldı |
|---|---|---|---|---|---|---|
| `flag:step_refuted` | 49 | 0 | 49 | 0.000 | -3.912 | evet |
| `steps.refute:fail:support` | 49 | 0 | 49 | 0.000 | -3.912 | evet |
| `certify.algebra:fail:primary` | 17 | 0 | 17 | 0.000 | -2.890 | evet |
| `certify.calculus:fail:primary` | 7 | 0 | 7 | 0.000 | -2.079 | evet |
| `certify.wordproblem:fail:primary` | 6 | 0 | 6 | 0.000 | -1.946 | evet |
| `certify.combinatorics:fail:primary` | 5 | 0 | 5 | 0.000 | -1.792 | evet |
| `certify.geometry_numeric:fail:primary` | 5 | 0 | 5 | 0.000 | -1.792 | evet |
| `mc.consistency:fail:support` | 4 | 0 | 4 | 0.000 | -1.609 | hayır (destek < eşik) |
| `certify.counting:fail:primary` | 3 | 0 | 3 | 0.000 | -1.386 | hayır (destek < eşik) |
| `certify.domain:pass:primary` | 3 | 3 | 0 | 1.000 | +1.386 | hayır (destek < eşik) |
| `certify.geometry:fail:primary` | 3 | 0 | 3 | 0.000 | -1.386 | hayır (destek < eşik) |
| `certify.limits:fail:primary` | 3 | 0 | 3 | 0.000 | -1.386 | hayır (destek < eşik) |
| `certify.series:fail:primary` | 3 | 0 | 3 | 0.000 | -1.386 | hayır (destek < eşik) |
| `certify.trig:fail:primary` | 3 | 0 | 3 | 0.000 | -1.386 | hayır (destek < eşik) |
| `certify.domain:fail:primary` | 2 | 0 | 2 | 0.000 | -1.099 | hayır (destek < eşik) |
| `certify.linalg:pass:primary` | 10 | 8 | 2 | 0.800 | +1.099 | evet |
| `certify.algebra:pass:primary` | 41 | 31 | 10 | 0.756 | +1.068 | evet |
| `certify.wordproblem:pass:primary` | 20 | 15 | 5 | 0.750 | +0.981 | evet |
| `certify.limits:pass:primary` | 5 | 4 | 1 | 0.800 | +0.916 | evet |
| `certify.trig:pass:primary` | 5 | 4 | 1 | 0.800 | +0.916 | evet |
| `certify.calculus:pass:primary` | 11 | 8 | 3 | 0.727 | +0.811 | evet |
| `certify.counting:pass:primary` | 4 | 3 | 1 | 0.750 | +0.693 | hayır (destek < eşik) |
| `certify.extremum:fail:primary` | 1 | 0 | 1 | 0.000 | -0.693 | hayır (destek < eşik) |
| `certify.extremum:pass:primary` | 4 | 3 | 1 | 0.750 | +0.693 | hayır (destek < eşik) |
| `certify.geometry:pass:primary` | 4 | 3 | 1 | 0.750 | +0.693 | hayır (destek < eşik) |
| `certify.series:pass:primary` | 7 | 5 | 2 | 0.714 | +0.693 | evet |
| `flag:answer_from_option_letter` | 1 | 1 | 0 | 1.000 | +0.693 | hayır (destek < eşik) |
| `sanity:fail:support` | 1 | 0 | 1 | 0.000 | -0.693 | hayır (destek < eşik) |
| `flag:answer_level_only` | 8 | 3 | 5 | 0.375 | -0.406 | evet |
| `certify.combinatorics:pass:primary` | 7 | 4 | 3 | 0.571 | +0.223 | evet |
| `certify.geometry_numeric:pass:primary` | 7 | 4 | 3 | 0.571 | +0.223 | evet |
| `mc.consistency:pass:support` | 138 | 71 | 67 | 0.514 | +0.057 | evet |
| `flag:z3_unsupported` | 2 | 1 | 1 | 0.500 | +0.000 | hayır (destek < eşik) |

## Abstain eğrisi (test bölmesi)

| Eşik ±z | Kapsama | Pozitif precision | Negatif precision | fp | fn |
|---|---|---|---|---|---|
| 0.0 | 1.000 | 0.939 | 1.000 | 2 | 0 |
| 0.5 | 0.722 | 1.000 | 1.000 | 0 | 0 |
| 1.0 | 0.463 | 1.000 | 1.000 | 0 | 0 |
| 1.5 | 0.407 | 1.000 | 1.000 | 0 | 0 |
| 2.0 | 0.407 | 1.000 | 1.000 | 0 | 0 |
| 3.0 | 0.333 | n/a | 1.000 | 0 | 0 |
| 4.0 | 0.333 | n/a | 1.000 | 0 | 0 |
| 6.0 | 0.333 | n/a | 1.000 | 0 | 0 |
| 8.0 | 0.111 | n/a | 1.000 | 0 | 0 |
| 12.0 | 0.056 | n/a | 1.000 | 0 | 0 |
