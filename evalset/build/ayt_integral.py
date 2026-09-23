"""AYT — integral: belirsiz (türev sertifikası, E8), belirli (kırılma noktalı nümerik, E3)."""
from common import item, mutate, steps, mc

ITEMS = []
VX = [{"name": "x"}]

# ----------------------------------------------------------------------------- 001 ∫ ln x dx
Q1 = "∫ ln x dx integrali aşağıdakilerden hangisine eşittir? (C sabit)"
IR1 = {"task": {"kind": "antiderivative", "params": {"integrand": "log(x)", "var": "x"}}, "vars": VX, "givens": [],
       "answer_shape": "expression",
       "options": mc("x*log(x) - x + C", "x*log(x) + C", "log(x)/x + C", "x*log(x) + x + C", "1/x + C")}
A1 = item("ayt-int-001", "A", "AYT", "integral", Q1, IR1,
          {"claimed_answer": {"kind": "expression", "payload": "x*log(x) - x + C", "option": "A"},
           "steps": steps(("s1", "note", "", [], "kısmi integrasyon: u = ln x, dv = dx"),
                          ("s2", "compute", "Integral(log(x), x) = x*log(x) - x", ["s1"], "x ln x − ∫ x·(1/x) dx"))},
          "x*log(x) - x + C", options=IR1["options"],
          solution_text="u = ln x, dv = dx ⇒ x ln x − ∫ dx = x ln x − x + C. Cevap: A")
ITEMS.append(A1)
ITEMS.append(item("ayt-int-005", "B", "AYT", "integral", Q1, IR1,
                  {"claimed_answer": {"kind": "expression", "payload": "x*log(x) - x + C", "option": "A"},
                   "steps": steps(("s1", "note", "", [], "Şıkları türevle kontrol edelim"),
                                  ("s2", "compute", "diff(x*log(x) - x, x) = log(x)", [], "A şıkkı sağlar"),
                                  ("s3", "compute", "diff(x*log(x), x) = log(x) + 1", [], "B sağlamaz"))},
                  "x*log(x) - x + C", options=IR1["options"],
                  solution_text="A şıkkının türevi ln x + 1 − 1 = ln x. Cevap: A", notes="şıkları türevleyerek; kanonik değil"))

# ----------------------------------------------------------------------------- 002 mutlak değerli belirli integral (E3)
Q2 = "∫₋₃³ (|x − 1| + |x + 2|) dx integralinin değeri kaçtır?"
IR2 = {"task": {"kind": "definite_integral", "params": {"integrand": "Abs(x - 1) + Abs(x + 2)", "var": "x", "a": "-3", "b": "3"}},
       "vars": VX, "givens": [], "answer_shape": "scalar", "options": mc(6, 21, 23, 25, 27)}
A2 = item("ayt-int-002", "A", "AYT", "integral", Q2, IR2,
          {"claimed_answer": {"kind": "value", "payload": "23", "option": "C"},
           "steps": steps(("s1", "note", "", [], "kırılma noktaları x = −2 ve x = 1"),
                          ("s2", "compute", "Integral(-2*x - 1, (x, -3, -2)) = 4", [], "[−3,−2]: (1−x) + (−x−2)"),
                          ("s3", "compute", "Integral(3, (x, -2, 1)) = 9", [], "[−2,1]: (1−x) + (x+2)"),
                          ("s4", "compute", "Integral(2*x + 1, (x, 1, 3)) = 10", [], "[1,3]: (x−1) + (x+2)"),
                          ("s5", "compute", "4 + 9 + 10 = 23", ["s2", "s3", "s4"], ""))},
          "23", options=IR2["options"],
          solution_text="Parçalara ayır: [−3,−2]: 4, [−2,1]: 9, [1,3]: 10; toplam 23. Cevap: C")
ITEMS.append(A2)
ITEMS.append(item("ayt-int-006", "B", "AYT", "integral", Q2, IR2,
                  {"claimed_answer": {"kind": "value", "payload": "23", "option": "C"},
                   "steps": steps(("s1", "note", "", [], "|x−1| grafiği altındaki alan iki üçgen: tabanlar 4 ve 2"),
                                  ("s2", "compute", "(4**2 + 2**2)/2 = 10", [], "∫|x−1| = 16/2 + 4/2"),
                                  ("s3", "compute", "(1**2 + 5**2)/2 = 13", [], "∫|x+2| = 1/2 + 25/2"),
                                  ("s4", "compute", "10 + 13 = 23", ["s2", "s3"], ""))},
                  "23", options=IR2["options"],
                  solution_text="Alan olarak: ∫|x−1| = 10, ∫|x+2| = 13; toplam 23. Cevap: C",
                  notes="geometrik alan hesabı; ilkel kullanılmadı"))
ITEMS.append(item("ayt-int-009", "B", "AYT", "integral", Q2, IR2,
                  {"claimed_answer": {"kind": "value", "payload": "23", "option": "C"},
                   "steps": steps(("s1", "eq", "Abs(x - 1) = Abs(1 - x)", [], "simetri"),
                                  ("s2", "compute", "Integral(Abs(x - 1), (x, -3, 3)) = 10", [], ""),
                                  ("s3", "compute", "Integral(Abs(x + 2), (x, -3, 3)) = 13", [], ""),
                                  ("s4", "compute", "10 + 13 = 23", ["s2", "s3"], ""))},
                  "23", options=IR2["options"],
                  solution_text="Doğrusallık: ∫|x−1| + ∫|x+2| = 10 + 13 = 23. Cevap: C", notes="integralleri ayrı ayrı"))

# ----------------------------------------------------------------------------- 003 kısmi integrasyon
Q3 = "∫₀¹ x·eˣ dx integralinin değeri kaçtır?"
IR3 = {"task": {"kind": "definite_integral", "params": {"integrand": "x*exp(x)", "var": "x", "a": "0", "b": "1"}},
       "vars": VX, "givens": [], "answer_shape": "scalar", "options": mc(0, 1, "E - 1", "E/2", "2*E - 1")}
A3 = item("ayt-int-003", "A", "AYT", "integral", Q3, IR3,
          {"claimed_answer": {"kind": "value", "payload": "1", "option": "B"},
           "steps": steps(("s1", "compute", "Integral(x*exp(x), x) = x*exp(x) - exp(x)", [], "kısmi integrasyon"),
                          ("s2", "compute", "at(x*exp(x) - exp(x), x, 1) - at(x*exp(x) - exp(x), x, 0) = 1", ["s1"], "(e − e) − (0 − 1)"))},
          "1", options=IR3["options"], solution_text="[x eˣ − eˣ]₀¹ = 0 − (−1) = 1. Cevap: B")
ITEMS.append(A3)
ITEMS.append(item("ayt-int-007", "B", "AYT", "integral", Q3, IR3,
                  {"claimed_answer": {"kind": "value", "payload": "1", "option": "B"},
                   "steps": steps(("s1", "compute", "diff((x - 1)*exp(x), x) = x*exp(x)", [], "tahmin edilen ilkelin türevi"),
                                  ("s2", "compute", "at((x - 1)*exp(x), x, 1) - at((x - 1)*exp(x), x, 0) = 1", ["s1"], ""))},
                  "1", options=IR3["options"],
                  solution_text="(x − 1)eˣ türevi x eˣ olduğundan integral [(x−1)eˣ]₀¹ = 0 − (−1) = 1. Cevap: B",
                  notes="ilkel tahmini + türevle doğrulama"))
ITEMS.append(item("ayt-int-019", "B", "AYT", "integral", Q3, IR3,
                  {"claimed_answer": {"kind": "value", "payload": "1", "option": "B"},
                   "steps": steps(("s1", "note", "", [], "Şıkları sayısal olarak ele: integral ≈ 1.0000"),
                                  ("s2", "compute", "Integral(x*exp(x), (x, 0, 1)) = 1", [], "hesap"))},
                  "1", options=IR3["options"],
                  solution_text="Sayısal hesapla integral 1'e eşittir. Cevap: B", notes="doğrudan hesap; ara adımsız"))

# ----------------------------------------------------------------------------- 004 ∫ sin
Q4 = "∫₀^π sin x dx integralinin değeri kaçtır?"
IR4 = {"task": {"kind": "definite_integral", "params": {"integrand": "sin(x)", "var": "x", "a": "0", "b": "pi"}},
       "vars": VX, "givens": [], "answer_shape": "scalar", "options": mc(0, 1, 2, "pi", -2)}
A4 = item("ayt-int-004", "A", "AYT", "integral", Q4, IR4,
          {"claimed_answer": {"kind": "value", "payload": "2", "option": "C"},
           "steps": steps(("s1", "compute", "Integral(sin(x), x) = -cos(x)", [], ""),
                          ("s2", "compute", "-cos(pi) + cos(0) = 2", ["s1"], ""))},
          "2", options=IR4["options"], solution_text="[−cos x]₀^π = 1 + 1 = 2. Cevap: C")
ITEMS.append(A4)
ITEMS.append(item("ayt-int-008", "B", "AYT", "integral", Q4, IR4,
                  {"claimed_answer": {"kind": "value", "payload": "2", "option": "C"},
                   "steps": steps(("s1", "note", "", [], "sin x, x = π/2 etrafında simetrik"),
                                  ("s2", "compute", "Integral(sin(x), (x, 0, pi/2)) = 1", [], ""),
                                  ("s3", "compute", "2*1 = 2", ["s2"], ""))},
                  "2", options=IR4["options"], solution_text="Simetriden 2·∫₀^{π/2} sin x dx = 2. Cevap: C", notes="simetri"))

# ----------------------------------------------------------------------------- C cells
ITEMS.append(mutate(A1, "ayt-int-010", mutation="wrong_formula",
                    claimed={"kind": "expression", "payload": "x*log(x) + C", "option": "B"},
                    steps_=steps(("s1", "compute", "Integral(log(x), x) = x*log(x)", [], "ikinci terim unutuldu")),
                    first_bad_step=1, solution_text="∫ ln x dx = x ln x + C. Cevap: B"))
ITEMS.append(mutate(A1, "ayt-int-014", mutation="wrong_formula",
                    claimed={"kind": "expression", "payload": "1/x + C", "option": "E"},
                    steps_=steps(("s1", "compute", "Integral(log(x), x) = 1/x", [], "türev ile integral karıştırıldı")),
                    first_bad_step=1, solution_text="∫ ln x dx = 1/x + C. Cevap: E"))
ITEMS.append(mutate(A2, "ayt-int-011", mutation="missing_case",
                    claimed={"kind": "value", "payload": "6", "option": "A"},
                    steps_=steps(("s1", "eq", "Abs(x - 1) + Abs(x + 2) = 2*x + 1", [], "mutlak değerler kaldırıldı (yanlış)"),
                                 ("s2", "compute", "Integral(2*x + 1, (x, -3, 3)) = 6", ["s1"], "")),
                    first_bad_step=1, solution_text="∫₋₃³ (2x + 1) dx = 6. Cevap: A"))
ITEMS.append(mutate(A2, "ayt-int-020", mutation="arithmetic_slip",
                    claimed={"kind": "value", "payload": "21", "option": "B"},
                    steps_=steps(("s1", "compute", "Integral(-2*x - 1, (x, -3, -2)) = 4", [], ""),
                                 ("s2", "compute", "Integral(3, (x, -2, 1)) = 9", [], ""),
                                 ("s3", "compute", "Integral(2*x + 1, (x, 1, 3)) = 8", [], "yanlış hesap"),
                                 ("s4", "compute", "4 + 9 + 8 = 21", ["s1", "s2", "s3"], "")),
                    first_bad_step=3, solution_text="4 + 9 + 8 = 21. Cevap: B"))
ITEMS.append(mutate(A3, "ayt-int-012", mutation="sign_flip",
                    claimed={"kind": "value", "payload": "2*E - 1", "option": "E"},
                    steps_=steps(("s1", "compute", "Integral(x*exp(x), x) = x*exp(x) + exp(x)", [], "kısmi integrasyonda işaret hatası"),
                                 ("s2", "compute", "at(x*exp(x) + exp(x), x, 1) - at(x*exp(x) + exp(x), x, 0) = 2*E - 1", ["s1"], "")),
                    first_bad_step=1, solution_text="[x eˣ + eˣ]₀¹ = 2e − 1. Cevap: E"))
ITEMS.append(mutate(A3, "ayt-int-015", mutation="chain_rule",
                    claimed={"kind": "value", "payload": "E/2", "option": "D"},
                    steps_=steps(("s1", "compute", "Integral(x*exp(x), x) = x**2/2*exp(x)", [], "çarpım integrali yanlış"),
                                 ("s2", "compute", "at(x**2/2*exp(x), x, 1) - at(x**2/2*exp(x), x, 0) = E/2", ["s1"], "")),
                    first_bad_step=1, solution_text="∫ x eˣ dx = (x²/2)eˣ ⇒ e/2. Cevap: D"))
ITEMS.append(mutate(A4, "ayt-int-013", mutation="sign_flip",
                    claimed={"kind": "value", "payload": "0", "option": "A"},
                    steps_=steps(("s1", "compute", "Integral(sin(x), (x, 0, pi)) = -cos(pi) - cos(0)", [], "F(b) − F(a) yanlış uygulandı"),
                                 ("s2", "compute", "-cos(pi) - cos(0) = 0", ["s1"], "")),
                    first_bad_step=1, solution_text="−cos π − cos 0 = 1 − 1 = 0. Cevap: A"))

# ----------------------------------------------------------------------------- D cells
ITEMS.append(mutate(A3, "ayt-int-016", mutation="wrong_identity", cell="D",
                    claimed={"kind": "value", "payload": "1", "option": "B"},
                    steps_=steps(("s1", "compute", "diff(x*exp(x), x) = exp(x)", [], "yanlış türev (kullanılmadı)"),
                                 ("s2", "compute", "Integral(x*exp(x), (x, 0, 1)) = 1", [], "")),
                    first_bad_step=1, solution_text="(x eˣ)' = eˣ … ∫₀¹ x eˣ dx = 1. Cevap: B"))
ITEMS.append(mutate(A2, "ayt-int-017", mutation="arithmetic_slip", cell="D",
                    claimed={"kind": "value", "payload": "23", "option": "C"},
                    steps_=steps(("s1", "compute", "Integral(-2*x - 1, (x, -3, -2)) = 5", [], "yanlış"),
                                 ("s2", "compute", "Integral(3, (x, -2, 1)) = 9", [], ""),
                                 ("s3", "compute", "Integral(2*x + 1, (x, 1, 3)) = 9", [], "yanlış"),
                                 ("s4", "compute", "5 + 9 + 9 = 23", ["s1", "s2", "s3"], "")),
                    first_bad_step=1, solution_text="5 + 9 + 9 = 23. Cevap: C"))
ITEMS.append(mutate(A4, "ayt-int-018", mutation="sign_flip", cell="D",
                    claimed={"kind": "value", "payload": "2", "option": "C"},
                    steps_=steps(("s1", "compute", "Integral(sin(x), x) = cos(x)", [], "işaret hatası"),
                                 ("s2", "compute", "at(cos(x), x, pi) - at(cos(x), x, 0) = 2", ["s1"], "ikinci işaret hatası")),
                    first_bad_step=1, solution_text="[cos x]₀^π = 2. Cevap: C"))
ITEMS.append(mutate(A1, "ayt-int-021", mutation="wrong_identity", cell="D",
                    claimed={"kind": "expression", "payload": "x*log(x) - x + C", "option": "A"},
                    steps_=steps(("s1", "compute", "diff(log(x), x) = log(x)/x", [], "yanlış ara ifade"),
                                 ("s2", "compute", "Integral(log(x), x) = x*log(x) - x", [], "sonuç doğru")),
                    first_bad_step=1, solution_text="(ln x)' = ln x / x … ∫ ln x dx = x ln x − x + C. Cevap: A"))
