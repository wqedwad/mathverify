# F5 (Lean) taraması — modelsiz, deterministik ifade + Mathlib taktik merdiveni

- Öğe: **260** · Lean ifadesi üretilebilen: **68** (26.2%)
- Kanıtlanan: **49** · denetimden geçen (sorry/aksiyom/vakum/kullanılmayan hipotez): **49**
- **Yanlış cevaplı öğelerde kanıt (FP): 0** ✓ hedef 0
- Kapsama (tüm sette formal sertifika): 18.8% · ifadesi olanlar içinde: 72.1%
- Şablon türleri: {'closed_arithmetic': 38, 'evaluate_system': 29, 'solve_equation_set': 1}
- Süre: 35 s (ortalama 133 ms/öğe)

- Sertifikalı öğelerin hücre dağılımı: {'A': 20, 'B': 16, 'D': 12, 'C': 1} (D hücresi = cevabı doğru, adımı bozuk: formal katman cevabı onaylar, adımı değil)
- Kullanılan taktikler: {'  norm_num': 27, '  nlinarith': 2, '  linarith': 10, '  omega': 10}

## İfadesi üretilip kanıtlanamayanlar (19)

- ayt-ana-012 [closed_arithmetic] cevap YANLIŞ (kanıtlanamaması beklenir): `theorem mv_claim  : 5 = 25`
- ayt-ana-014 [closed_arithmetic] cevap YANLIŞ (kanıtlanamaması beklenir): `theorem mv_claim  : 4 = 20`
- ayt-ana-015 [closed_arithmetic] cevap YANLIŞ (kanıtlanamaması beklenir): `theorem mv_claim  : 6 = 12`
- ayt-ana-022 [closed_arithmetic] cevap YANLIŞ (kanıtlanamaması beklenir): `theorem mv_claim  : 6 = 7`
- ayt-trig-012 [closed_arithmetic] cevap YANLIŞ (kanıtlanamaması beklenir): `theorem mv_claim  : ((Real.sqrt 2 / 4) + (Real.sqrt 6 / 4)) = (((-Real.sqrt 2) / 4) + (Real.sqrt 6 / 4))`
- ayt-trig-019 [closed_arithmetic] cevap doğru: `theorem mv_claim  : ((Real.sqrt 2 / 4) + (Real.sqrt 6 / 4)) = (Real.sqrt (2 + Real.sqrt 3) / 2)`
- tyt-den-003 [solve_equation_set] cevap doğru: `theorem mv_claim  : (∀ x : ℝ, (((-3 : ℝ) + x) ≠ 0) → ¬((x / ((-3 : ℝ) + x)) = (2 + (3 / ((-3 : ℝ) + x)))))`
- tyt-den-012 [evaluate_system] cevap YANLIŞ (kanıtlanamaması beklenir): `theorem mv_claim (m : ℝ) (h1 : ((-16 : ℝ) + ((1 + m) ^ 2)) = 0) (h2 : m > 0) : m = 15`
- tyt-prob-013 [evaluate_system] cevap YANLIŞ (kanıtlanamaması beklenir): `theorem mv_claim (a b : ℤ) (h1 : (a + b) = 30) (h2 : ((2 * a) + (4 * b)) = 88) (h3 : 0 < a) (h4 : 0 < b) : a = 14`
- tyt-prob-014 [evaluate_system] cevap YANLIŞ (kanıtlanamaması beklenir): `theorem mv_claim (t : ℝ) (h1 : (t / 2) = 1) (h2 : 0 < t) : t = 3`
- tyt-prob-015 [evaluate_system] cevap YANLIŞ (kanıtlanamaması beklenir): `theorem mv_claim (x : ℝ) (h1 : (5 + (3 * x)) = ((-7 : ℝ) + (5 * x))) : x = 1`
- tyt-prob-016 [evaluate_system] cevap YANLIŞ (kanıtlanamaması beklenir): `theorem mv_claim (o b : ℤ) (h1 : b = (4 * o)) (h2 : (5 + b) = (15 + (3 * o))) (h3 : 0 < o) (h4 : 0 < b) : b = 30`
- tyt-prob-017 [evaluate_system] cevap YANLIŞ (kanıtlanamaması beklenir): `theorem mv_claim (x : ℝ) (h1 : ((6 * x) / 5) = 360) (h2 : 0 < x) : x = 288`
- tyt-say-010 [closed_arithmetic] cevap YANLIŞ (kanıtlanamaması beklenir): `theorem mv_claim  : 12 = 24`
- tyt-say-011 [evaluate_system] cevap YANLIŞ (kanıtlanamaması beklenir): `theorem mv_claim (a b : ℤ) (h1 : (a + b) = 11) (h2 : (((-9 : ℤ) * a) + (9 * b)) = 27) (h3 : a ≥ 1) (h4 : a ≤ 9) (h5 : b ≥ 0) (h6 : b ≤ 9) : (b + (10 *`
- uni-011 [closed_arithmetic] cevap YANLIŞ (kanıtlanamaması beklenir): `theorem mv_claim  : (-2 : ℝ) = 2`
- uni-014 [closed_arithmetic] cevap YANLIŞ (kanıtlanamaması beklenir): `theorem mv_claim  : 3 = 1`
- uni-020 [closed_arithmetic] cevap YANLIŞ (kanıtlanamaması beklenir): `theorem mv_claim  : (-2 : ℝ) = (-1 : ℝ)`
- uni-la-017 [closed_arithmetic] cevap YANLIŞ (kanıtlanamaması beklenir): `theorem mv_claim  : 0 = 4`
