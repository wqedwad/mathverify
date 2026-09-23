"""TYT — denklemler (log / köklü / rasyonel / mutlak değer / parametreli). Domain traps."""
from common import item, mutate, steps, mc

ITEMS = []

# ----------------------------------------------------------------------------- 001 log
Q1 = "log(x − 1) + log(x − 3) = log 3 denkleminin çözüm kümesi aşağıdakilerden hangisidir?"
IR1 = {"task": {"kind": "solve_equation", "params": {"var": "x"}}, "vars": [{"name": "x"}],
       "givens": ["log(x - 1) + log(x - 3) = log(3)"], "answer_shape": "set",
       "options": mc("{0}", "{4}", "{0, 4}", "{1}", "{}")}
A1 = item("tyt-den-001", "A", "TYT", "denklem", Q1, IR1,
          {"claimed_answer": {"kind": "set", "payload": "{4}", "option": "B"},
           "steps": steps(("s1", "eq", "log((x - 1)*(x - 3)) = log(3)", [], "log toplamı"),
                          ("s2", "eq", "(x - 1)*(x - 3) = 3", ["s1"], ""),
                          ("s3", "eq", "x**2 - 4*x = 0", ["s2"], ""),
                          ("s4", "eq", "x in {0, 4}", ["s3"], ""),
                          ("s5", "assert", "x > 3", [], "tanım kümesi: x − 1 > 0 ve x − 3 > 0"),
                          ("s6", "eq", "x = 4", ["s4", "s5"], "0 tanım kümesinde değil"))},
          "{4}", options=IR1["options"],
          solution_text="log((x−1)(x−3)) = log 3 ⇒ x² − 4x = 0 ⇒ x ∈ {0, 4}. Tanım kümesi x > 3 olduğundan x = 4.\nÇözüm kümesi: {4}")
ITEMS.append(A1)
ITEMS.append(item("tyt-den-006", "B", "TYT", "denklem", Q1, IR1,
                  {"claimed_answer": {"kind": "set", "payload": "{4}", "option": "B"},
                   "steps": steps(("s1", "case", "x = 4", [], "B şıkkını dene"),
                                  ("s2", "compute", "log(4 - 1) + log(4 - 3) = log(3)", ["s1"], "log 3 + 0 ✓"),
                                  ("s3", "note", "", [], "x = 0 için log(−1) tanımsız, C elenir"))},
                  "{4}", options=IR1["options"],
                  solution_text="x = 4: log 3 + log 1 = log 3 ✓. x = 0: log(−1) tanımsız. Çözüm kümesi: {4}", notes="şık deneme"))

# ----------------------------------------------------------------------------- 002 köklü
Q2 = "√(x + 4) = x − 2 denkleminin çözüm kümesi aşağıdakilerden hangisidir?"
IR2 = {"task": {"kind": "solve_equation", "params": {"var": "x"}}, "vars": [{"name": "x"}],
       "givens": ["sqrt(x + 4) = x - 2"], "answer_shape": "set",
       "options": mc("{0}", "{5}", "{0, 5}", "{-4}", "{}")}
A2 = item("tyt-den-002", "A", "TYT", "denklem", Q2, IR2,
          {"claimed_answer": {"kind": "set", "payload": "{5}", "option": "B"},
           "steps": steps(("s1", "eq", "x + 4 = (x - 2)**2", [], "kare al"),
                          ("s2", "eq", "x**2 - 5*x = 0", ["s1"], ""),
                          ("s3", "eq", "x in {0, 5}", ["s2"], ""),
                          ("s4", "assert", "x - 2 >= 0", [], "sağ taraf negatif olamaz"),
                          ("s5", "eq", "x = 5", ["s3", "s4"], "x = 0 için √4 = 2 ≠ −2"))},
          "{5}", options=IR2["options"],
          solution_text="Kare alınca x + 4 = x² − 4x + 4 ⇒ x² − 5x = 0 ⇒ x ∈ {0, 5}. x = 0 sağlamaz (2 ≠ −2). Çözüm kümesi: {5}")
ITEMS.append(A2)
ITEMS.append(item("tyt-den-007", "B", "TYT", "denklem", Q2, IR2,
                  {"claimed_answer": {"kind": "set", "payload": "{5}", "option": "B"},
                   "steps": steps(("s1", "note", "", [], "u = √(x+4) ≥ 0 olsun; x = u² − 4"),
                                  ("s2", "eq", "u = u**2 - 6", [], "u = x − 2 = u² − 6"),
                                  ("s3", "eq", "u = 3", ["s2"], "u² − u − 6 = (u − 3)(u + 2), u ≥ 0"),
                                  ("s4", "eq", "x = 5", ["s3"], "x = 9 − 4"))},
                  "{5}", options=IR2["options"],
                  solution_text="u = √(x+4) dersek x = u² − 4 ve u = u² − 6 ⇒ u = 3 (u ≥ 0) ⇒ x = 5. Çözüm kümesi: {5}",
                  notes="değişken değiştirme; u sembolü IR'da yok → adımlar atlanır"))

# ----------------------------------------------------------------------------- 003 rasyonel (boş küme)
Q3 = "x/(x − 3) = 3/(x − 3) + 2 denkleminin çözüm kümesi aşağıdakilerden hangisidir?"
IR3 = {"task": {"kind": "solve_equation", "params": {"var": "x"}}, "vars": [{"name": "x"}],
       "givens": ["x/(x - 3) = 3/(x - 3) + 2"], "answer_shape": "set",
       "options": mc("{3}", "{}", "{0}", "{-3}", "{0, 3}")}
A3 = item("tyt-den-003", "A", "TYT", "denklem", Q3, IR3,
          {"claimed_answer": {"kind": "set", "payload": "{}", "option": "B"},
           "steps": steps(("s1", "assert", "x != 3", [], "payda sıfır olamaz"),
                          ("s2", "eq", "x = 3 + 2*(x - 3)", [], "(x − 3) ile çarp"),
                          ("s3", "eq", "x = 3", ["s2"], ""),
                          ("s4", "note", "", ["s1", "s3"], "x = 3 tanım kümesinde değil ⇒ çözüm yok"))},
          "{}", options=IR3["options"],
          solution_text="Paydayı yok edince x = 3 + 2x − 6 ⇒ x = 3, fakat x = 3 paydayı sıfırlar. Çözüm kümesi: {}")
ITEMS.append(A3)

# ----------------------------------------------------------------------------- 004 mutlak değer
Q4 = "|2x − 3| = 5 denkleminin çözüm kümesi aşağıdakilerden hangisidir?"
IR4 = {"task": {"kind": "solve_equation", "params": {"var": "x"}}, "vars": [{"name": "x"}],
       "givens": ["Abs(2*x - 3) = 5"], "answer_shape": "set",
       "options": mc("{4}", "{-1, 4}", "{-4, 1}", "{1, 4}", "{-1}")}
A4 = item("tyt-den-004", "A", "TYT", "denklem", Q4, IR4,
          {"claimed_answer": {"kind": "set", "payload": "{-1, 4}", "option": "B"},
           "steps": steps(("s1", "case", "2*x - 3 = 5", [], "1. durum"),
                          ("s2", "eq", "x = 4", ["s1"], ""),
                          ("s3", "case", "2*x - 3 = -5", [], "2. durum"),
                          ("s4", "eq", "x = -1", ["s3"], ""),
                          ("s5", "eq", "x in {-1, 4}", ["s2", "s4"], ""))},
          "{-1, 4}", options=IR4["options"],
          solution_text="2x − 3 = 5 ⇒ x = 4; 2x − 3 = −5 ⇒ x = −1. Çözüm kümesi: {-1, 4}")
ITEMS.append(A4)
ITEMS.append(item("tyt-den-008", "B", "TYT", "denklem", Q4, IR4,
                  {"claimed_answer": {"kind": "set", "payload": "{-1, 4}", "option": "B"},
                   "steps": steps(("s1", "eq", "Abs(x - 3/2) = 5/2", [], "2'ye böl"),
                                  ("s2", "note", "", ["s1"], "3/2'ye uzaklığı 5/2 olan noktalar"),
                                  ("s3", "eq", "x in {3/2 + 5/2, 3/2 - 5/2}", ["s1"], ""),
                                  ("s4", "eq", "x in {4, -1}", ["s3"], ""))},
                  "{-1, 4}", options=IR4["options"],
                  solution_text="|x − 3/2| = 5/2: sayı doğrusunda 3/2'ye uzaklığı 5/2 olan noktalar 4 ve −1. Çözüm kümesi: {-1, 4}",
                  notes="geometrik/uzaklık yorumu"))

# ----------------------------------------------------------------------------- 005 parametre
Q5 = "x² − (m + 1)x + 4 = 0 denkleminin çakışık iki reel kökü olduğuna göre m'nin pozitif değeri kaçtır?"
IR5 = {"task": {"kind": "evaluate", "params": {"expr": "m"}}, "vars": [{"name": "m"}],
       "givens": ["(m + 1)**2 - 4*4 = 0", "m > 0"], "unknown_of_interest": "m", "answer_shape": "scalar",
       "options": mc(1, 3, 5, 7, 15)}
A5 = item("tyt-den-005", "A", "TYT", "denklem", Q5, IR5,
          {"claimed_answer": {"kind": "value", "payload": "3", "option": "B"},
           "steps": steps(("s1", "eq", "(m + 1)**2 - 16 = 0", [], "Δ = 0"),
                          ("s2", "eq", "m + 1 = 4", ["s1"], "m > 0 için"),
                          ("s3", "eq", "m = 3", ["s2"], ""))},
          "3", options=IR5["options"], solution_text="Δ = (m+1)² − 16 = 0 ⇒ m + 1 = ±4 ⇒ m = 3 (pozitif). Cevap: B")
ITEMS.append(A5)

# ----------------------------------------------------------------------------- C cells
ITEMS.append(mutate(A1, "tyt-den-009", mutation="log_domain",
                    claimed={"kind": "set", "payload": "{0, 4}", "option": "C"},
                    steps_=steps(("s1", "eq", "log((x - 1)*(x - 3)) = log(3)", [], ""),
                                 ("s2", "eq", "(x - 1)*(x - 3) = 3", ["s1"], ""),
                                 ("s3", "eq", "x**2 - 4*x = 0", ["s2"], ""),
                                 ("s4", "eq", "x in {0, 4}", ["s3"], ""),
                                 ("s5", "conclude", "", ["s4"], "tanım kümesi kontrol edilmedi")),
                    first_bad_step=5, solution_text="x² − 4x = 0 ⇒ x ∈ {0, 4}. Çözüm kümesi: {0, 4}"))
ITEMS.append(mutate(A2, "tyt-den-010", mutation="sqrt_pm_loss",
                    claimed={"kind": "set", "payload": "{0, 5}", "option": "C"},
                    steps_=steps(("s1", "eq", "x + 4 = (x - 2)**2", [], ""),
                                 ("s2", "eq", "x**2 - 5*x = 0", ["s1"], ""),
                                 ("s3", "eq", "x in {0, 5}", ["s2"], ""),
                                 ("s4", "conclude", "", ["s3"], "yabancı kök kontrolü yok")),
                    first_bad_step=4, solution_text="x² − 5x = 0 ⇒ x ∈ {0, 5}. Çözüm kümesi: {0, 5}"))
ITEMS.append(mutate(A3, "tyt-den-011", mutation="domain_violation",
                    claimed={"kind": "set", "payload": "{3}", "option": "A"},
                    steps_=steps(("s1", "eq", "x = 3 + 2*(x - 3)", [], ""),
                                 ("s2", "eq", "x = 3", ["s1"], ""),
                                 ("s3", "conclude", "", ["s2"], "payda kontrolü yapılmadı")),
                    first_bad_step=3, solution_text="x = 3 + 2x − 6 ⇒ x = 3. Çözüm kümesi: {3}"))
ITEMS.append(mutate(A5, "tyt-den-012", mutation="arithmetic_slip",
                    claimed={"kind": "value", "payload": "15", "option": "E"},
                    steps_=steps(("s1", "eq", "(m + 1)**2 - 16 = 0", [], ""),
                                 ("s2", "eq", "m + 1 = 16", ["s1"], "kare unutuldu"),
                                 ("s3", "eq", "m = 15", ["s2"], "")),
                    first_bad_step=2, solution_text="(m+1)² = 16 ⇒ m + 1 = 16 ⇒ m = 15. Cevap: E"))

# ----------------------------------------------------------------------------- D cells
ITEMS.append(mutate(A2, "tyt-den-013", mutation="arithmetic_slip", cell="D",
                    claimed={"kind": "set", "payload": "{5}", "option": "B"},
                    steps_=steps(("s1", "eq", "x + 4 = (x - 2)**2", [], ""),
                                 ("s2", "eq", "x**2 - 5*x + 8 = 0", ["s1"], "sabit terim hatası (doğrusu x² − 5x = 0)"),
                                 ("s3", "eq", "x = 5", ["s2"], "deneyerek"),
                                 ("s4", "assert", "x - 2 >= 0", [], "")),
                    first_bad_step=2, solution_text="x² − 5x + 8 = 0 … x = 5 sağlar. Çözüm kümesi: {5}"))
ITEMS.append(mutate(A4, "tyt-den-014", mutation="wrong_identity", cell="D",
                    claimed={"kind": "set", "payload": "{-1, 4}", "option": "B"},
                    steps_=steps(("s1", "compute", "Abs(-5) = -5", [], "mutlak değer tanımı yanlış ifade edildi"),
                                 ("s2", "case", "2*x - 3 = 5", [], ""),
                                 ("s3", "eq", "x = 4", ["s2"], ""),
                                 ("s4", "case", "2*x - 3 = -5", [], ""),
                                 ("s5", "eq", "x = -1", ["s4"], ""),
                                 ("s6", "eq", "x in {-1, 4}", ["s3", "s5"], "")),
                    first_bad_step=1, solution_text="|−5| = −5 olduğundan iki durum: … x = 4 veya x = −1. Çözüm kümesi: {-1, 4}"))
