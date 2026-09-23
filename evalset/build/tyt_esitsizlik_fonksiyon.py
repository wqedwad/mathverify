"""TYT — eşitsizlikler, fonksiyonlar, polinomlar."""
from common import item, mutate, steps, mc

ITEMS = []

# ----------------------------------------------------------------------------- 001 ikinci derece eşitsizlik
Q1 = "x² − 5x − 14 < 0 eşitsizliğinin çözüm kümesi aşağıdakilerden hangisidir?"
IR1 = {"task": {"kind": "solve_inequality", "params": {"var": "x"}}, "vars": [{"name": "x"}],
       "givens": ["x**2 - 5*x - 14 < 0"], "answer_shape": "interval",
       "options": mc("(-2, 7)", "[-2, 7]", "(-oo, -2) U (7, oo)", "(-7, 2)", "(2, 7)")}
A1 = item("tyt-esf-001", "A", "TYT", "eşitsizlik", Q1, IR1,
          {"claimed_answer": {"kind": "interval", "payload": "(-2, 7)", "option": "A"},
           "steps": steps(("s1", "eq", "x**2 - 5*x - 14 = (x - 7)*(x + 2)", [], "çarpanlara ayır"),
                          ("s2", "note", "", ["s1"], "kökler −2 ve 7; başkatsayı pozitif ⇒ kökler arasında negatif"))},
          "(-2, 7)", options=IR1["options"], solution_text="(x − 7)(x + 2) < 0 ⇒ −2 < x < 7. Cevap: A")
ITEMS.append(A1)
ITEMS.append(item("tyt-esf-008", "B", "TYT", "eşitsizlik", Q1, IR1,
                  {"claimed_answer": {"kind": "interval", "payload": "(-2, 7)", "option": "A"},
                   "steps": steps(("s1", "note", "", [], "kökler −2 ve 7"),
                                  ("s2", "compute", "0**2 - 5*0 - 14 = -14", [], "x = 0 test noktası"),
                                  ("s3", "assert", "-14 < 0", ["s2"], "aradaki bölge sağlar"),
                                  ("s4", "compute", "10**2 - 5*10 - 14 = 36", [], "x = 10 test noktası sağlamaz"))},
                  "(-2, 7)", options=IR1["options"],
                  solution_text="Kökler −2, 7. x = 0 denenirse −14 < 0 ✓, x = 10 için 36 > 0 ✗. Çözüm (−2, 7). Cevap: A",
                  notes="test noktası yöntemi"))

# ----------------------------------------------------------------------------- 002 rasyonel eşitsizlik
Q2 = "(x − 1)/(x + 2) ≥ 0 eşitsizliğinin çözüm kümesi aşağıdakilerden hangisidir?"
IR2 = {"task": {"kind": "solve_inequality", "params": {"var": "x"}}, "vars": [{"name": "x"}],
       "givens": ["(x - 1)/(x + 2) >= 0"], "answer_shape": "interval",
       "options": mc("(-oo, -2) U [1, oo)", "(-oo, -2] U [1, oo)", "[-2, 1]", "(-2, 1)", "(-oo, -2) U (1, oo)")}
A2 = item("tyt-esf-002", "A", "TYT", "eşitsizlik", Q2, IR2,
          {"claimed_answer": {"kind": "interval", "payload": "(-oo, -2) U [1, oo)", "option": "A"},
           "steps": steps(("s1", "assert", "x != -2", [], "payda"),
                          ("s2", "note", "", [], "işaret tablosu: −2'nin solunda +, arada −, 1'in sağında +"),
                          ("s3", "note", "", ["s1", "s2"], "1 dahil, −2 hariç"))},
          "(-oo, -2) U [1, oo)", options=IR2["options"],
          solution_text="Kritik noktalar −2 (payda, hariç) ve 1 (dahil). İşaret tablosundan (−∞, −2) ∪ [1, ∞). Cevap: A")
ITEMS.append(A2)

# ----------------------------------------------------------------------------- 003 mutlak değer eşitsizliği sayım
Q3 = "|x − 3| < 2 eşitsizliğini sağlayan kaç farklı x tam sayısı vardır?"
IR3 = {"task": {"kind": "count_integers", "params": {"var": "x"}}, "vars": [{"name": "x", "domain": "integer"}],
       "givens": ["Abs(x - 3) < 2"], "answer_shape": "count", "options": mc(2, 3, 4, 5, 6)}
A3 = item("tyt-esf-003", "A", "TYT", "eşitsizlik", Q3, IR3,
          {"claimed_answer": {"kind": "count", "payload": 3, "option": "B"},
           "steps": steps(("s1", "eq", "-2 < x - 3", [], ""), ("s2", "eq", "x - 3 < 2", [], ""),
                          ("s3", "note", "", ["s1", "s2"], "1 < x < 5 ⇒ x ∈ {2, 3, 4}"))},
          "3", options=IR3["options"], solution_text="−2 < x − 3 < 2 ⇒ 1 < x < 5 ⇒ x ∈ {2, 3, 4}: 3 tam sayı. Cevap: B")
ITEMS.append(A3)

# ----------------------------------------------------------------------------- 004 bileşke
Q4 = "f(x) = 2x + 3 ve g(x) = x² − 1 olduğuna göre (f∘g)(2) kaçtır?"
IR4 = {"task": {"kind": "evaluate", "params": {"expr": "f(g(2))"}}, "vars": [],
       "functions": [{"name": "f", "expr": "2*x + 3", "args": ["x"]}, {"name": "g", "expr": "x**2 - 1", "args": ["x"]}],
       "givens": [], "answer_shape": "scalar", "options": mc(7, 8, 9, 10, 11)}
A4 = item("tyt-esf-004", "A", "TYT", "fonksiyonlar", Q4, IR4,
          {"claimed_answer": {"kind": "value", "payload": "9", "option": "C"},
           "steps": steps(("s1", "compute", "g(2) = 3", [], ""), ("s2", "compute", "f(3) = 9", ["s1"], ""))},
          "9", options=IR4["options"], solution_text="g(2) = 3, f(3) = 9. Cevap: C")
ITEMS.append(A4)
ITEMS.append(item("tyt-esf-009", "B", "TYT", "fonksiyonlar", Q4, IR4,
                  {"claimed_answer": {"kind": "value", "payload": "9", "option": "C"},
                   "steps": steps(("s1", "eq", "f(g(x)) = 2*x**2 + 1", [], "genel bileşke"),
                                  ("s2", "compute", "2*2**2 + 1 = 9", ["s1"], ""))},
                  "9", options=IR4["options"],
                  solution_text="(f∘g)(x) = 2(x² − 1) + 3 = 2x² + 1 ⇒ (f∘g)(2) = 9. Cevap: C", notes="önce genel bileşke"))

# ----------------------------------------------------------------------------- 005 ters fonksiyon
Q5 = "f(x) = (2x + 3)/(x − 1) olduğuna göre f⁻¹(5) kaçtır?"
IR5 = {"task": {"kind": "solve_equation", "params": {"var": "x", "equation": "f(x) = 5"}}, "vars": [{"name": "x"}],
       "functions": [{"name": "f", "expr": "(2*x + 3)/(x - 1)", "args": ["x"], "domain": "x != 1"}],
       "givens": ["f(x) = 5"], "answer_shape": "scalar", "options": mc("2/3", "8/3", "3", "10/3", "4")}
A5 = item("tyt-esf-005", "A", "TYT", "fonksiyonlar", Q5, IR5,
          {"claimed_answer": {"kind": "value", "payload": "8/3", "option": "B"},
           "steps": steps(("s1", "eq", "(2*x + 3)/(x - 1) = 5", [], "f(x) = 5"),
                          ("s2", "eq", "2*x + 3 = 5*x - 5", ["s1"], ""),
                          ("s3", "eq", "3*x = 8", ["s2"], ""),
                          ("s4", "eq", "x = 8/3", ["s3"], ""))},
          "8/3", options=IR5["options"], solution_text="f(x) = 5 ⇒ 2x + 3 = 5x − 5 ⇒ x = 8/3. Cevap: B")
ITEMS.append(A5)

# ----------------------------------------------------------------------------- 006 polinom kalan
Q6 = "P(x) = x³ − 2x² + kx + 6 polinomunun (x − 3) ile bölümünden kalan 0 olduğuna göre k kaçtır?"
IR6 = {"task": {"kind": "evaluate", "params": {"expr": "k"}}, "vars": [{"name": "k"}],
       "functions": [{"name": "P", "expr": "x**3 - 2*x**2 + k*x + 6", "args": ["x"], "params": ["k"]}],
       "givens": ["P(3) = 0"], "unknown_of_interest": "k", "answer_shape": "scalar", "options": mc(-5, -3, 3, 5, 7)}
A6 = item("tyt-esf-006", "A", "TYT", "polinom", Q6, IR6,
          {"claimed_answer": {"kind": "value", "payload": "-5", "option": "A"},
           "steps": steps(("s1", "eq", "27 - 18 + 3*k + 6 = 0", [], "P(3) = 0"),
                          ("s2", "eq", "3*k = -15", ["s1"], ""),
                          ("s3", "eq", "k = -5", ["s2"], ""))},
          "-5", options=IR6["options"], solution_text="P(3) = 27 − 18 + 3k + 6 = 15 + 3k = 0 ⇒ k = −5. Cevap: A")
ITEMS.append(A6)
ITEMS.append(item("tyt-esf-010", "B", "TYT", "polinom", Q6, IR6,
                  {"claimed_answer": {"kind": "value", "payload": "-5", "option": "A"},
                   "steps": steps(("s1", "note", "", [], "P(x) = (x − 3)(x² + x + c) yazılabilir"),
                                  ("s2", "eq", "-3 + 1 = -2", [], "x² katsayısı ✓"),
                                  ("s3", "eq", "-3*c = 6", [], "sabit terim"),
                                  ("s4", "eq", "c = -2", ["s3"], ""),
                                  ("s5", "eq", "k = c - 3", ["s1"], "x katsayısı"),
                                  ("s6", "eq", "k = -5", ["s4", "s5"], ""))},
                  "-5", options=IR6["options"],
                  solution_text="P(x) = (x−3)(x²+x+c): sabit −3c = 6 ⇒ c = −2; x katsayısı k = c − 3 = −5. Cevap: A",
                  notes="çarpanlara ayırma ile katsayı karşılaştırma; c IR'da yok"))

# ----------------------------------------------------------------------------- 007 kök sayısı
Q7 = "P(x) = x⁵ − 3x³ + x + 1 polinomunun kaç farklı reel kökü vardır?"
IR7 = {"task": {"kind": "count_roots", "params": {"expr": "x**5 - 3*x**3 + x + 1", "var": "x"}}, "vars": [{"name": "x"}],
       "givens": [], "answer_shape": "count", "options": mc(1, 2, 3, 4, 5)}
A7 = item("tyt-esf-007", "A", "TYT", "polinom", Q7, IR7,
          {"claimed_answer": {"kind": "count", "payload": 3, "option": "C"},
           "steps": steps(("s1", "compute", "1 - 3 + 1 + 1 = 0", [], "x = 1 kök"),
                          ("s2", "eq", "x**5 - 3*x**3 + x + 1 = (x - 1)*(x**4 + x**3 - 2*x**2 - 2*x - 1)", [], "bölme"),
                          ("s3", "note", "", ["s2"], "kalan çarpanın işaret değişimleri: (−2,−1) ve (1,2) aralıklarında birer kök"))},
          "3", options=IR7["options"], solution_text="x = 1 bir kök; kalan 4. derece çarpanın 2 reel kökü var. Toplam 3. Cevap: C")
ITEMS.append(A7)

# ----------------------------------------------------------------------------- C cells
ITEMS.append(mutate(A1, "tyt-esf-011", mutation="inequality_direction",
                    claimed={"kind": "interval", "payload": "(-oo, -2) U (7, oo)", "option": "C"},
                    steps_=steps(("s1", "eq", "x**2 - 5*x - 14 = (x - 7)*(x + 2)", [], ""),
                                 ("s2", "note", "", ["s1"], "dış bölge alındı (yön hatası)")),
                    first_bad_step=2, solution_text="(x − 7)(x + 2) < 0 ⇒ x < −2 veya x > 7. Cevap: C"))
ITEMS.append(mutate(A2, "tyt-esf-012", mutation="endpoint_error",
                    claimed={"kind": "interval", "payload": "(-oo, -2] U [1, oo)", "option": "B"},
                    steps_=steps(("s1", "note", "", [], "kritik noktalar −2 ve 1, ikisi de dahil (payda unutuldu)")),
                    first_bad_step=1, solution_text="(−∞, −2] ∪ [1, ∞). Cevap: B"))
ITEMS.append(mutate(A5, "tyt-esf-013", mutation="arithmetic_slip",
                    claimed={"kind": "value", "payload": "2/3", "option": "A"},
                    steps_=steps(("s1", "eq", "(2*x + 3)/(x - 1) = 5", [], ""),
                                 ("s2", "eq", "2*x + 3 = 5*x - 5", ["s1"], ""),
                                 ("s3", "eq", "3*x = 2", ["s2"], "işaret hatası"),
                                 ("s4", "eq", "x = 2/3", ["s3"], "")),
                    first_bad_step=3, solution_text="2x + 3 = 5x − 5 ⇒ 3x = 2 ⇒ x = 2/3. Cevap: A"))
ITEMS.append(mutate(A7, "tyt-esf-014", mutation="wrong_formula",
                    claimed={"kind": "count", "payload": 5, "option": "E"},
                    steps_=steps(("s1", "note", "", [], "5. dereceden polinomun 5 kökü vardır (reel/karmaşık ayrımı yapılmadı)")),
                    first_bad_step=1, solution_text="Derecesi 5 olduğundan 5 kökü vardır. Cevap: E"))

# ----------------------------------------------------------------------------- D cells
ITEMS.append(mutate(A4, "tyt-esf-015", mutation="arithmetic_slip", cell="D",
                    claimed={"kind": "value", "payload": "9", "option": "C"},
                    steps_=steps(("s1", "compute", "g(2) = 5", [], "2² − 1 yanlış hesaplandı"),
                                 ("s2", "compute", "f(5) = 9", ["s1"], "2·5 + 3 yanlış hesaplandı; hatalar birbirini götürdü")),
                    first_bad_step=1, solution_text="g(2) = 5, f(5) = 9. Cevap: C"))
ITEMS.append(mutate(A6, "tyt-esf-016", mutation="arithmetic_slip", cell="D",
                    claimed={"kind": "value", "payload": "-5", "option": "A"},
                    steps_=steps(("s1", "compute", "3**3 = 24", [], "yanlış"),
                                 ("s2", "compute", "2*3**2 = 15", [], "yanlış"),
                                 ("s3", "compute", "24 - 15 + 6 = 15", ["s1", "s2"], ""),
                                 ("s4", "eq", "15 + 3*k = 0", ["s3"], ""),
                                 ("s5", "eq", "k = -5", ["s4"], "")),
                    first_bad_step=1, solution_text="P(3) = 24 − 15 + 3k + 6 = 15 + 3k = 0 ⇒ k = −5. Cevap: A"))
