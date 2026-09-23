# §6 ölçüm raporu — E1–E10 bu makinede yeniden üretildi

Ortam: Python 3.14.7 (Windows 11), SymPy 1.14.0, mpmath 1.3.0, z3-solver 5.1.0, math-verify 0.9.0,
latex2sympy2_extended 1.11.0. Ham ölçüm betiği: `scripts/probe_e1_e10.py`. Sözleşme testleri:
`tests/test_e01_*.py` … `tests/test_e10_*.py` (her commit'te koşar).

Handoff'un talimatı: "kendi ölçümün farklı çıkarsa dur ve raporla". Aşağıda her madde için
handoff değeri, bu makinedeki değer ve fark verilmiştir.

| # | Ölçüm | Handoff | Bu makine | Durum |
|---|---|---|---|---|
| E1 | `solveset(cos 2x = 1/2, Reals)` | ImageSet birleşimi | `Union(ImageSet(n·π + π/6), ImageSet(n·π + 5π/6))` | aynı |
| E1 | `== aday` | False | False | aynı |
| E1 | `is_subset(aday)` | None | **hash tohumuna bağlı**: `PYTHONHASHSEED` 0,1,2,4,5 → None; 3,6,7 → True | **FARK (aşağıda)** |
| E1 | pencere yöntemi `[0, π)` | {π/6, 5π/6} her iki taraf, True | aynı, 93 ms | aynı |
| E2 | `solve(log(x−1)+log(x−3)=log 3)` | [4] | [4] | aynı |
| E2 | `solveset(…, Reals)` | {0, 4} | {0, 4} (22 ms) | aynı |
| E2 | `√(x+4)=x−2` naif kareleme | [0, 5] | [0, 5] | aynı |
| E3 | SymPy `integrate(ln x/√x, 0, 1)` | 6.6 s sonra çözemedi (meijerg) | 0.5 s'de çözemedi (meijerg yığını) | davranış aynı, süre farklı |
| E3 | naif `mp.quad` (dps 15) | −3.99999997553 (8 basamak) | −3.99999997553465 | aynı |
| E3 | tanh-sinh dps 40 | −4.0 | −4.0 (39 ms) | aynı |
| E3 | `∫₋₃³ (|x−1|+|x+2|)` naif | 22.9994651291 | 22.999465129086 | aynı |
| E3 | kırılma noktalı `[−3,−2,1,3]` | 23.0 | 23.0 | aynı |
| E4 | `√(x²)` vs `x` yalnız pozitif 30 nokta | "eşit" | eşit (yanlış) | aynı |
| E4 | negatif dahil | False | False | aynı |
| E4 | `continuous_domain` | ~2.3 s | 0.02–0.04 s (log ve √ ifadeleri) | süre farklı; cache yine tutuluyor |
| E5 | adaylar + `{f>18}` | [(−1,2),(1,−2),(−2,−2),(3,18)], EmptySet | aynı, 27 ms | aynı |
| E6 | `limit(|x|/x, x, 0)` | 1 | 1 | aynı |
| E6 | tek yönlüler | (1, −1) | (1, −1) | aynı |
| E6 | `limit(sin(1/x), x, 0)` | AccumBounds(−1, 1) | AccumBounds(−1, 1) | aynı |
| E7 | z3 sat / `a≠16` unsat | sat (16,14) / unsat | sat (16,14) / unsat, 6 ms | aynı |
| E8 | türev sertifikası | 0 / 1 / 0 | 0 / 1 / 0 | aynı |
| E9 | `simplify(I**I)`, `expand_complex` | sadeleşmedi | `I**I` / `I**I` | aynı |
| E9 | `N(I**I)` | 0.207879576350762 | 0.207879576350762 | aynı |
| E10 | `count_roots` / `real_roots` | 3 / 3 | 3 / 3 (1 ms) | aynı |
| E10 | `x²−5x−14<0` | (−2, 7), 8 tam sayı | aynı | aynı |

## Yeni bulgular (handoff'ta yok)

1. **`is_subset` süreçler arasında deterministik değil.** Aynı girdide sonuç Python hash
   tohumuna göre `None` veya `True` çıkıyor (asla `False` görülmedi). Karar prosedürü olarak
   kullanılamaz; pencere yöntemi (`certify/trig.py`) tek deterministik yoldur. Sonuç: sandbox
   worker'larında `PYTHONHASHSEED=0` sabitlendi (§11/13 determinizm).
2. **Math-Verify Windows'ta her `verify` çağrısında yeni bir süreç açıyor** (`utils.timeout`
   → `multiprocessing.Process`). Ölçülen etki: her karşılaştırmada yüzlerce ms gecikme ve
   ana süreç kapanırken yetim bootstrap süreçlerinden `WinError 6` gürültüsü. Çözüm:
   `timeout_seconds=None` ile sandbox worker içinde çağrılır; timeout'u sandbox uygular.
3. **`lambdify` sabit karmaşık ifadeleri çift hassasiyete düşürüyor.** `I**I` lambdify ile
   15 basamak veriyor; `sp.N(expr, dps)` + `as_real_imag` yolu arbitrary precision. `equiv/numeric.py`
   buna göre yazıldı (E9'un "nümerik ana yol" kuralı bu detay olmadan yanlış çalışıyordu).
4. **Gauss–Legendre uç tekilliklerde çöküyor.** `∫₀¹ ln x/√x` için dps 80'de −3.9799 (hata
   5e-3); tanh-sinh dps 50'de 1.8e-25. Belirli integral sertifikası yalnız tanh-sinh
   merdiveni + `mp.quad` hata kestirimi kullanır; tolerans sabit değil, kestirimden türetilir.
   **Düzeltme (23 Eylül 2026):** "hata 5e-3" **göreli** hatadır. Yeniden ölçüldü: Gauss–Legendre
   dps 80'de −3.979932618, mutlak hata 2.0e-2 (0.0201/4 = 5.0e-3 göreli); tanh-sinh dps 50'de
   mutlak hata 1.81e-25.
5. **Float örnekleme özdeşlikleri "çürütüyor".** `x²−5x−14 = (x−7)(x+2)` 20 basamaklı Float
   noktada son bitte farklı çıkıp `Eq` otomatik `False` oluyordu. Rastgele noktalar artık kesin
   rasyonel (6 ondalık) ve bağıntılar `evaluate=False` ile kurulup toleranslı karşılaştırılıyor.
6. **SymPy varsayımı kısıtı yutuyor.** `x` pozitif sembolse `x > 0` ifadesi `True`'ya
   çöküyor ve z3'e ulaşmadan kayboluyor (ölçüm: `3x+5y=41` için `x=−3` çözümü "sat" çıktı).
   z3 köprüsü sembol varsayımlarını yan kısıt olarak ekler; IR bağıntıları `evaluate=False`.
7. **`Limit.doit()` tek yönlü varsayılanı adım katmanına sızar.** `compute` adımlarında
   `Limit(...)` iki yönlü sınıflandırıcıyla değerlendirilir; aksi hâlde `Limit(|x|/x, x, 0) = 1`
   adımı "doğrulanır"dı.

## Zamanlama (bu makine)

E1 110 ms (solveset) + 93 ms (pencere), E2 22–38 ms, E3 39 ms (tanh-sinh dps 40), E5 27 ms,
E6 2 ms, E7 6 ms, E10 1 ms. Handoff'un "7–170 ms" bandıyla uyumlu.
