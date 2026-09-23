"""AYT — türev: ekstremum, teğet, türev alma, parametre."""
from common import item, mutate, steps, mc

ITEMS = []
VX = [{"name": "x"}]

# ----------------------------------------------------------------------------- 001 kapalı aralıkta maksimum (E5)
Q1 = "f(x) = x³ − 3x fonksiyonunun [−2, 3] aralığındaki en büyük değeri kaçtır?"
IR1 = {"task": {"kind": "extremum", "params": {"f": "x**3 - 3*x", "var": "x", "interval": "[-2, 3]", "which": "max"}},
       "vars": VX, "givens": [], "answer_shape": "scalar", "options": mc(2, 16, 18, 20, 24)}
A1 = item("ayt-tur-001", "A", "AYT", "türev", Q1, IR1,
          {"claimed_answer": {"kind": "value", "payload": "18", "option": "C"},
           "steps": steps(("s1", "compute", "diff(x**3 - 3*x, x) = 3*x**2 - 3", [], ""),
                          ("s2", "note", "", ["s1"], "kritik noktalar x = ±1, uçlar −2 ve 3"),
                          ("s3", "compute", "at(x**3 - 3*x, x, -1) = 2", [], ""),
                          ("s4", "compute", "at(x**3 - 3*x, x, 1) = -2", [], ""),
                          ("s5", "compute", "at(x**3 - 3*x, x, -2) = -2", [], ""),
                          ("s6", "compute", "at(x**3 - 3*x, x, 3) = 18", [], ""),
                          ("s7", "note", "", ["s3", "s4", "s5", "s6"], "en büyüğü 18"))},
          "18", options=IR1["options"],
          solution_text="f' = 3x² − 3 = 0 ⇒ x = ±1. f(−1) = 2, f(1) = −2, f(−2) = −2, f(3) = 18. En büyük 18. Cevap: C")
ITEMS.append(A1)
ITEMS.append(item("ayt-tur-008", "B", "AYT", "türev", Q1, IR1,
                  {"claimed_answer": {"kind": "value", "payload": "18", "option": "C"},
                   "steps": steps(("s1", "note", "", [], "f, [1, 3] üzerinde artan (f' = 3(x−1)(x+1) > 0)"),
                                  ("s2", "compute", "at(x**3 - 3*x, x, 3) = 18", [], "sağ uçtaki değer"),
                                  ("s3", "compute", "at(x**3 - 3*x, x, -1) = 2", [], "yerel maksimum"),
                                  ("s4", "assert", "2 < 18", ["s2", "s3"], ""))},
                  "18", options=IR1["options"],
                  solution_text="[1,3] üzerinde artan; f(3) = 18, yerel maksimum f(−1) = 2 < 18. Cevap: C",
                  notes="monotonluk argümanı; kanonik olmayan yol"))

# ----------------------------------------------------------------------------- 002 çarpım türevi noktada
Q2 = "f(x) = x²·eˣ olduğuna göre f'(0) kaçtır?"
IR2 = {"task": {"kind": "derivative", "params": {"f": "x**2*exp(x)", "var": "x", "at": "0"}}, "vars": VX,
       "givens": [], "answer_shape": "scalar", "options": mc(-1, 0, 1, 2, "E")}
A2 = item("ayt-tur-002", "A", "AYT", "türev", Q2, IR2,
          {"claimed_answer": {"kind": "value", "payload": "0", "option": "B"},
           "steps": steps(("s1", "compute", "diff(x**2*exp(x), x) = (2*x + x**2)*exp(x)", [], "çarpım kuralı"),
                          ("s2", "compute", "at((2*x + x**2)*exp(x), x, 0) = 0", ["s1"], ""))},
          "0", options=IR2["options"], solution_text="f' = (2x + x²)eˣ ⇒ f'(0) = 0. Cevap: B")
ITEMS.append(A2)

# ----------------------------------------------------------------------------- 003 teğet doğrusu
Q3 = "y = x² eğrisine x = 1 apsisli noktasından çizilen teğetin denklemi aşağıdakilerden hangisidir?"
IR3 = {"task": {"kind": "tangent_line", "params": {"f": "x**2", "var": "x", "at": "1", "dep": "y"}},
       "vars": [{"name": "x"}, {"name": "y"}], "givens": [], "answer_shape": "equation",
       "options": mc("y = 2*x - 1", "y = 2*x + 1", "y = x", "y = 2*x", "y = x + 1")}
A3 = item("ayt-tur-003", "A", "AYT", "türev", Q3, IR3,
          {"claimed_answer": {"kind": "equation", "payload": "y = 2*x - 1", "option": "A"},
           "steps": steps(("s1", "compute", "diff(x**2, x) = 2*x", [], ""),
                          ("s2", "compute", "at(2*x, x, 1) = 2", ["s1"], "eğim"),
                          ("s3", "compute", "at(x**2, x, 1) = 1", [], "nokta (1, 1)"),
                          ("s4", "conclude", "y - 1 = 2*(x - 1)", ["s2", "s3"], "nokta-eğim"))},
          "y = 2*x - 1", options=IR3["options"], solution_text="m = 2, nokta (1,1): y − 1 = 2(x − 1) ⇒ y = 2x − 1. Cevap: A")
ITEMS.append(A3)
ITEMS.append(item("ayt-tur-010", "B", "AYT", "türev", Q3, IR3,
                  {"claimed_answer": {"kind": "equation", "payload": "2*x - y - 1 = 0", "option": "A"},
                   "steps": steps(("s1", "compute", "Limit(((1 + x)**2 - 1)/x, x, 0) = 2", [], "türev tanımı (h yerine x)"),
                                  ("s2", "eq", "y - 1 = 2*(x - 1)", ["s1"], "teğet"),
                                  ("s3", "eq", "2*x - y - 1 = 0", ["s2"], "genel biçim"))},
                  "y = 2*x - 1", options=IR3["options"],
                  solution_text="Türev tanımıyla eğim 2; teğet 2x − y − 1 = 0. Cevap: A",
                  notes="türev tanımı + farklı denklem biçimi; kanonik olmayan yol"))

# ----------------------------------------------------------------------------- 004 zincir kuralı (ifade)
Q4 = "f(x) = ln(x² + 1) fonksiyonunun türevi aşağıdakilerden hangisidir?"
IR4 = {"task": {"kind": "derivative", "params": {"f": "log(x**2 + 1)", "var": "x"}}, "vars": VX, "givens": [],
       "answer_shape": "expression",
       "options": mc("2*x/(x**2 + 1)", "1/(x**2 + 1)", "2*x*log(x**2 + 1)", "x/(x**2 + 1)", "2/(x**2 + 1)")}
A4 = item("ayt-tur-004", "A", "AYT", "türev", Q4, IR4,
          {"claimed_answer": {"kind": "expression", "payload": "2*x/(x**2 + 1)", "option": "A"},
           "steps": steps(("s1", "compute", "diff(x**2 + 1, x) = 2*x", [], "iç türev"),
                          ("s2", "compute", "diff(log(x**2 + 1), x) = 2*x/(x**2 + 1)", ["s1"], "zincir kuralı"))},
          "2*x/(x**2 + 1)", options=IR4["options"], solution_text="(ln u)' = u'/u ⇒ 2x/(x² + 1). Cevap: A")
ITEMS.append(A4)

# ----------------------------------------------------------------------------- 005 açık aralıkta minimum
Q5 = "x > 0 olmak üzere f(x) = x + 4/x fonksiyonunun en küçük değeri kaçtır?"
IR5 = {"task": {"kind": "extremum", "params": {"f": "x + 4/x", "var": "x", "interval": "(0, oo)", "which": "min"}},
       "vars": [{"name": "x", "domain": "positive_real"}], "givens": [], "answer_shape": "scalar",
       "domain_of_discourse": "x > 0", "options": mc(2, 4, 6, 8, 0)}
A5 = item("ayt-tur-005", "A", "AYT", "türev", Q5, IR5,
          {"claimed_answer": {"kind": "value", "payload": "4", "option": "B"},
           "steps": steps(("s1", "compute", "diff(x + 4/x, x) = 1 - 4/x**2", [], ""),
                          ("s2", "note", "", ["s1"], "1 − 4/x² = 0 ⇒ x = 2 (x > 0)"),
                          ("s3", "compute", "at(x + 4/x, x, 2) = 4", [], ""),
                          ("s4", "note", "", [], "x → 0⁺ ve x → ∞ için f → ∞; x = 2 minimum"))},
          "4", options=IR5["options"], solution_text="f' = 1 − 4/x² = 0 ⇒ x = 2; f(2) = 4. Cevap: B")
ITEMS.append(A5)
ITEMS.append(item("ayt-tur-009", "B", "AYT", "türev", Q5, IR5,
                  {"claimed_answer": {"kind": "value", "payload": "4", "option": "B"},
                   "steps": steps(("s1", "note", "", [], "AO ≥ GO: x + 4/x ≥ 2√(x·4/x)"),
                                  ("s2", "compute", "2*sqrt(4) = 4", [], ""),
                                  ("s3", "note", "", ["s1", "s2"], "eşitlik x = 4/x ⇒ x = 2'de sağlanır"))},
                  "4", options=IR5["options"],
                  solution_text="Aritmetik-geometrik ortalama: x + 4/x ≥ 2·2 = 4, eşitlik x = 2. Cevap: B",
                  notes="türev kullanmadan eşitsizlikle; kanonik olmayan yol"))

# ----------------------------------------------------------------------------- 006 yerel maksimum
Q6 = "f(x) = x³ − 6x² + 9x + 1 fonksiyonunun yerel maksimum değeri kaçtır?"
IR6 = {"task": {"kind": "extremum", "params": {"f": "x**3 - 6*x**2 + 9*x + 1", "var": "x", "which": "local_max"}},
       "vars": VX, "givens": [], "answer_shape": "scalar", "options": mc(1, 3, 5, 7, 9)}
A6 = item("ayt-tur-006", "A", "AYT", "türev", Q6, IR6,
          {"claimed_answer": {"kind": "value", "payload": "5", "option": "C"},
           "steps": steps(("s1", "compute", "diff(x**3 - 6*x**2 + 9*x + 1, x) = 3*x**2 - 12*x + 9", [], ""),
                          ("s2", "eq", "3*x**2 - 12*x + 9 = 3*(x - 1)*(x - 3)", [], ""),
                          ("s3", "note", "", ["s2"], "işaret: x = 1'de + → −, yerel maksimum"),
                          ("s4", "compute", "at(x**3 - 6*x**2 + 9*x + 1, x, 1) = 5", [], ""))},
          "5", options=IR6["options"], solution_text="f' = 3(x−1)(x−3); x = 1'de yerel maksimum f(1) = 5. Cevap: C")
ITEMS.append(A6)

# ----------------------------------------------------------------------------- 007 parametre
Q7 = "f(x) = x³ + ax² + bx fonksiyonu x = 1 noktasında yerel ekstremuma sahiptir ve f(1) = −3'tür. a·b çarpımı kaçtır?"
IR7 = {"task": {"kind": "evaluate", "params": {"expr": "a*b"}}, "vars": [{"name": "a"}, {"name": "b"}],
       "functions": [{"name": "f", "expr": "x**3 + a*x**2 + b*x", "args": ["x"], "params": ["a", "b"]}],
       "givens": ["at(diff(f(x), x), x, 1) = 0", "f(1) = -3"], "unknown_of_interest": "a*b", "answer_shape": "scalar",
       "options": mc(-5, -4, 4, 5, 6)}
A7 = item("ayt-tur-007", "A", "AYT", "türev", Q7, IR7,
          {"claimed_answer": {"kind": "value", "payload": "-5", "option": "A"},
           "steps": steps(("s1", "eq", "3 + 2*a + b = 0", [], "f'(1) = 0"),
                          ("s2", "eq", "1 + a + b = -3", [], "f(1) = −3"),
                          ("s3", "eq", "a = 1", ["s1", "s2"], ""),
                          ("s4", "eq", "b = -5", ["s3"], ""),
                          ("s5", "compute", "1*(-5) = -5", ["s3", "s4"], ""))},
          "-5", options=IR7["options"], solution_text="f'(1) = 3 + 2a + b = 0, f(1) = 1 + a + b = −3 ⇒ a = 1, b = −5 ⇒ ab = −5. Cevap: A")
ITEMS.append(A7)

# ----------------------------------------------------------------------------- C cells
ITEMS.append(mutate(A1, "ayt-tur-011", mutation="endpoint_error",
                    claimed={"kind": "value", "payload": "2", "option": "A"},
                    steps_=steps(("s1", "compute", "diff(x**3 - 3*x, x) = 3*x**2 - 3", [], ""),
                                 ("s2", "note", "", ["s1"], "kritik noktalar ±1"),
                                 ("s3", "compute", "at(x**3 - 3*x, x, -1) = 2", [], ""),
                                 ("s4", "conclude", "", ["s3"], "uç noktalar kontrol edilmedi")),
                    first_bad_step=4, solution_text="Yerel maksimum f(−1) = 2 en büyük değerdir. Cevap: A"))
ITEMS.append(mutate(A2, "ayt-tur-012", mutation="arithmetic_slip",
                    claimed={"kind": "value", "payload": "2", "option": "D"},
                    steps_=steps(("s1", "compute", "diff(x**2*exp(x), x) = (2*x + x**2)*exp(x)", [], ""),
                                 ("s2", "compute", "at((2*x + x**2)*exp(x), x, 0) = 2", ["s1"], "e⁰ = 1 ile 2 çarpıldı (x = 0 unutuldu)")),
                    first_bad_step=2, solution_text="f'(0) = 2·1 = 2. Cevap: D"))
ITEMS.append(mutate(A3, "ayt-tur-013", mutation="wrong_formula",
                    claimed={"kind": "equation", "payload": "y = x", "option": "C"},
                    steps_=steps(("s1", "compute", "diff(x**2, x) = x", [], "türev yanlış"),
                                 ("s2", "compute", "at(x, x, 1) = 1", ["s1"], "eğim 1"),
                                 ("s3", "conclude", "y - 1 = 1*(x - 1)", ["s2"], "")),
                    first_bad_step=1, solution_text="(x²)' = x ⇒ m = 1 ⇒ y = x. Cevap: C"))
ITEMS.append(mutate(A4, "ayt-tur-014", mutation="chain_rule",
                    claimed={"kind": "expression", "payload": "1/(x**2 + 1)", "option": "B"},
                    steps_=steps(("s1", "compute", "diff(log(x**2 + 1), x) = 1/(x**2 + 1)", [], "iç türev unutuldu")),
                    first_bad_step=1, solution_text="(ln u)' = 1/u ⇒ 1/(x² + 1). Cevap: B"))

# ----------------------------------------------------------------------------- D cells
ITEMS.append(mutate(A5, "ayt-tur-015", mutation="sign_flip", cell="D",
                    claimed={"kind": "value", "payload": "4", "option": "B"},
                    steps_=steps(("s1", "compute", "diff(x + 4/x, x) = 1 + 4/x**2", [], "işaret hatası"),
                                 ("s2", "eq", "x**2 = 4", ["s1"], "1 + 4/x² = 0 ⇒ x² = 4 (ikinci hata)"),
                                 ("s3", "eq", "x = 2", ["s2"], ""),
                                 ("s4", "compute", "at(x + 4/x, x, 2) = 4", ["s3"], "")),
                    first_bad_step=1, solution_text="f' = 1 + 4/x² = 0 ⇒ x = 2 ⇒ f(2) = 4. Cevap: B"))
ITEMS.append(mutate(A2, "ayt-tur-016", mutation="wrong_formula", cell="D",
                    claimed={"kind": "value", "payload": "0", "option": "B"},
                    steps_=steps(("s1", "compute", "diff(x**2*exp(x), x) = 2*x*exp(x)", [], "çarpım kuralı uygulanmadı"),
                                 ("s2", "compute", "at(2*x*exp(x), x, 0) = 0", ["s1"], "sonuç tesadüfen doğru")),
                    first_bad_step=1, solution_text="f' = 2x·eˣ ⇒ f'(0) = 0. Cevap: B"))
