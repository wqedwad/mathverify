"""AYT — diziler ve seriler: rekürans, genel terim, toplamlar."""
from common import item, mutate, steps, mc

ITEMS = []
VK = [{"name": "k", "domain": "positive_integer"}, {"name": "n", "domain": "positive_integer"}]

# ----------------------------------------------------------------------------- 001 rekürans terimi
Q1 = "a₁ = 1, a₂ = 3 ve n ≥ 3 için aₙ = aₙ₋₁ + 2aₙ₋₂ olduğuna göre a₆ kaçtır?"
IR1 = {"task": {"kind": "recurrence_term", "params": {"recurrence": "a(n) = a(n-1) + 2*a(n-2)", "initial": {"1": "1", "2": "3"},
                                                      "index": 6, "var": "n"}}, "vars": VK, "givens": [],
       "answer_shape": "scalar", "options": mc(21, 32, 43, 64, 85)}
A1 = item("ayt-diz-001", "A", "AYT", "diziler", Q1, IR1,
          {"claimed_answer": {"kind": "value", "payload": "43", "option": "C"},
           "steps": steps(("s1", "compute", "3 + 2*1 = 5", [], "a₃"), ("s2", "compute", "5 + 2*3 = 11", ["s1"], "a₄"),
                          ("s3", "compute", "11 + 2*5 = 21", ["s2"], "a₅"), ("s4", "compute", "21 + 2*11 = 43", ["s3"], "a₆"))},
          "43", options=IR1["options"], solution_text="a₃ = 5, a₄ = 11, a₅ = 21, a₆ = 43. Cevap: C")
ITEMS.append(A1)
ITEMS.append(item("ayt-diz-007", "B", "AYT", "diziler", Q1, IR1,
                  {"claimed_answer": {"kind": "value", "payload": "43", "option": "C"},
                   "steps": steps(("s1", "note", "", [], "karakteristik denklem r² − r − 2 = 0 ⇒ r = 2, −1; aₙ = (2ⁿ⁺¹ + (−1)ⁿ)/3"),
                                  ("s2", "compute", "(2**7 + (-1)**6)/3 = 43", ["s1"], "n = 6"))},
                  "43", options=IR1["options"], solution_text="Kapalı form (2ⁿ⁺¹ + (−1)ⁿ)/3; n = 6 için 43. Cevap: C",
                  notes="kapalı form üzerinden; kanonik olmayan yol"))

# ----------------------------------------------------------------------------- 002 aritmetik dizi
Q2 = "İlk terimi 5 ve ortak farkı 3 olan aritmetik dizinin 20. terimi kaçtır?"
IR2 = {"task": {"kind": "recurrence_term", "params": {"recurrence": "a(n) = a(n-1) + 3", "initial": {"1": "5"}, "index": 20, "var": "n"}},
       "vars": VK, "givens": [], "answer_shape": "scalar", "options": mc(59, 60, 62, 65, 68)}
A2 = item("ayt-diz-002", "A", "AYT", "diziler", Q2, IR2,
          {"claimed_answer": {"kind": "value", "payload": "62", "option": "C"},
           "steps": steps(("s1", "compute", "5 + 19*3 = 62", [], "a₂₀ = a₁ + 19d"))},
          "62", options=IR2["options"], solution_text="a₂₀ = 5 + 19·3 = 62. Cevap: C")
ITEMS.append(A2)
ITEMS.append(item("ayt-diz-008", "B", "AYT", "diziler", Q2, IR2,
                  {"claimed_answer": {"kind": "value", "payload": "62", "option": "C"},
                   "steps": steps(("s1", "eq", "a(n) = 3*n + 2", [], "genel terim"),
                                  ("s2", "compute", "3*20 + 2 = 62", ["s1"], ""))},
                  "62", options=IR2["options"], solution_text="aₙ = 3n + 2 ⇒ a₂₀ = 62. Cevap: C", notes="genel terim yolu"))

# ----------------------------------------------------------------------------- 003 geometrik dizi genel terim
Q3 = "İlk terimi 3 ve ortak çarpanı 2 olan geometrik dizinin genel terimi aşağıdakilerden hangisidir?"
IR3 = {"task": {"kind": "closed_form", "params": {"recurrence": "a(n) = 2*a(n-1)", "initial": {"1": "3"}, "var": "n"}},
       "vars": VK, "givens": [], "answer_shape": "expression",
       "options": mc("3*2**n", "3*2**(n-1)", "2*3**(n-1)", "6**(n-1)", "3**n")}
A3 = item("ayt-diz-003", "A", "AYT", "diziler", Q3, IR3,
          {"claimed_answer": {"kind": "expression", "payload": "3*2**(n-1)", "option": "B"},
           "steps": steps(("s1", "note", "", [], "aₙ = a₁·rⁿ⁻¹"))},
          "3*2**(n-1)", options=IR3["options"], solution_text="aₙ = 3·2ⁿ⁻¹. Cevap: B")
ITEMS.append(A3)
ITEMS.append(item("ayt-diz-009", "B", "AYT", "diziler", Q3, IR3,
                  {"claimed_answer": {"kind": "expression", "payload": "6*2**n/4", "option": "B"},
                   "steps": steps(("s1", "note", "", [], "a₂ = 6; aₙ = a₂·2ⁿ⁻² = 6·2ⁿ/4"),
                                  ("s2", "compute", "6*2**1/4 = 3", ["s1"], "n = 1 kontrolü"))},
                  "3*2**(n-1)", options=IR3["options"], solution_text="aₙ = 6·2ⁿ⁻² = 6·2ⁿ/4, B ile aynı. Cevap: B",
                  notes="eşdeğer farklı biçim"))

# ----------------------------------------------------------------------------- 004 Binet
Q4 = "a₁ = a₂ = 1 ve aₙ = aₙ₋₁ + aₙ₋₂ (Fibonacci) dizisinin genel terimi aşağıdakilerden hangisidir?"
BINET = "(((1+sqrt(5))/2)**n - ((1-sqrt(5))/2)**n)/sqrt(5)"
IR4 = {"task": {"kind": "closed_form", "params": {"recurrence": "a(n) = a(n-1) + a(n-2)", "initial": {"1": "1", "2": "1"}, "var": "n"}},
       "vars": VK, "givens": [], "answer_shape": "expression",
       "options": mc(BINET, "(((1+sqrt(5))/2)**n + ((1-sqrt(5))/2)**n)/sqrt(5)", "((1+sqrt(5))/2)**n",
                     "(((1+sqrt(5))/2)**(n-1) - ((1-sqrt(5))/2)**(n-1))/sqrt(5)", "2**(n-1)")}
A4 = item("ayt-diz-004", "A", "AYT", "diziler", Q4, IR4,
          {"claimed_answer": {"kind": "expression", "payload": BINET, "option": "A"},
           "steps": steps(("s1", "note", "", [], "karakteristik r² = r + 1, kökler φ, ψ; aₙ = cφⁿ + dψⁿ"),
                          ("s2", "compute", "(((1+sqrt(5))/2) - ((1-sqrt(5))/2))/sqrt(5) = 1", ["s1"], "n = 1"),
                          ("s3", "compute", "(((1+sqrt(5))/2)**2 - ((1-sqrt(5))/2)**2)/sqrt(5) = 1", ["s1"], "n = 2"))},
          BINET, options=IR4["options"], solution_text="Binet formülü. Cevap: A")
ITEMS.append(A4)

# ----------------------------------------------------------------------------- 005 kare toplamı
Q5 = "1² + 2² + … + 10² toplamı kaçtır?"
IR5 = {"task": {"kind": "series_sum", "params": {"term": "k**2", "var": "k", "lo": "1", "hi": "10"}}, "vars": VK, "givens": [],
       "answer_shape": "scalar", "options": mc(285, 330, 385, 440, 505)}
A5 = item("ayt-diz-005", "A", "AYT", "diziler", Q5, IR5,
          {"claimed_answer": {"kind": "value", "payload": "385", "option": "C"},
           "steps": steps(("s1", "compute", "10*11*21/6 = 385", [], "n(n+1)(2n+1)/6"))},
          "385", options=IR5["options"], solution_text="10·11·21/6 = 385. Cevap: C")
ITEMS.append(A5)
ITEMS.append(item("ayt-diz-010", "B", "AYT", "diziler", Q5, IR5,
                  {"claimed_answer": {"kind": "value", "payload": "385", "option": "C"},
                   "steps": steps(("s1", "compute", "1 + 4 + 9 + 16 + 25 + 36 + 49 + 64 + 81 + 100 = 385", [], "doğrudan toplama"))},
                  "385", options=IR5["options"], solution_text="Terimleri toplayınca 385. Cevap: C", notes="doğrudan toplama"))

# ----------------------------------------------------------------------------- 006 geometrik seri
Q6 = "Σ_{k=1}^{∞} 1/2ᵏ serisinin toplamı kaçtır?"
IR6 = {"task": {"kind": "series_sum", "params": {"term": "1/2**k", "var": "k", "lo": "1", "hi": "oo"}}, "vars": VK, "givens": [],
       "answer_shape": "scalar", "options": mc("1/2", 1, "3/2", 2, "∞")}
A6 = item("ayt-diz-006", "A", "AYT", "diziler", Q6, IR6,
          {"claimed_answer": {"kind": "value", "payload": "1", "option": "B"},
           "steps": steps(("s1", "compute", "(1/2)/(1 - 1/2) = 1", [], "a/(1 − r)"))},
          "1", options=IR6["options"], solution_text="(1/2)/(1 − 1/2) = 1. Cevap: B")
ITEMS.append(A6)
ITEMS.append(item("ayt-diz-011", "B", "AYT", "diziler", Q6, IR6,
                  {"claimed_answer": {"kind": "value", "payload": "1", "option": "B"},
                   "steps": steps(("s1", "compute", "Sum(1/2**k, (k, 1, n)) = 1 - 1/2**n", [], "kısmi toplam"),
                                  ("s2", "compute", "Limit(1 - 1/2**n, n, oo) = 1", ["s1"], ""))},
                  "1", options=IR6["options"], solution_text="Kısmi toplam 1 − 1/2ⁿ → 1. Cevap: B", notes="kısmi toplam limiti"))

# ----------------------------------------------------------------------------- C cells
ITEMS.append(mutate(A1, "ayt-diz-012", mutation="off_by_one",
                    claimed={"kind": "value", "payload": "21", "option": "A"},
                    steps_=steps(("s1", "compute", "3 + 2*1 = 5", [], ""), ("s2", "compute", "5 + 2*3 = 11", ["s1"], ""),
                                 ("s3", "compute", "11 + 2*5 = 21", ["s2"], "a₅ hesaplandı, a₆ sanıldı"),
                                 ("s4", "conclude", "", ["s3"], "")),
                    first_bad_step=4, solution_text="a₃ = 5, a₄ = 11, a₅ = 21 ⇒ a₆ = 21. Cevap: A"))
ITEMS.append(mutate(A2, "ayt-diz-013", mutation="off_by_one",
                    claimed={"kind": "value", "payload": "65", "option": "D"},
                    steps_=steps(("s1", "compute", "5 + 20*3 = 65", [], "n yerine n−1 alınmadı")),
                    first_bad_step=1, solution_text="a₂₀ = 5 + 20·3 = 65. Cevap: D"))
ITEMS.append(mutate(A3, "ayt-diz-014", mutation="off_by_one",
                    claimed={"kind": "expression", "payload": "3*2**n", "option": "A"},
                    steps_=steps(("s1", "note", "", [], "aₙ = a₁·rⁿ (üs hatası)")),
                    first_bad_step=1, solution_text="aₙ = 3·2ⁿ. Cevap: A"))
ITEMS.append(mutate(A4, "ayt-diz-015", mutation="sign_flip",
                    claimed={"kind": "expression", "payload": "(((1+sqrt(5))/2)**n + ((1-sqrt(5))/2)**n)/sqrt(5)", "option": "B"},
                    steps_=steps(("s1", "note", "", [], "işaret hatası")),
                    first_bad_step=1, solution_text="(φⁿ + ψⁿ)/√5. Cevap: B"))
ITEMS.append(mutate(A5, "ayt-diz-016", mutation="wrong_formula",
                    claimed={"kind": "value", "payload": "330", "option": "B"},
                    steps_=steps(("s1", "compute", "10*11*(2*10 + 1)/6 = 330", [], "hesap hatası")),
                    first_bad_step=1, solution_text="10·11·21/6 = 330. Cevap: B"))
ITEMS.append(mutate(A6, "ayt-diz-017", mutation="off_by_one",
                    claimed={"kind": "value", "payload": "2", "option": "D"},
                    steps_=steps(("s1", "compute", "1/(1 - 1/2) = 2", [], "ilk terim 1 alındı (k = 0'dan başlatıldı)")),
                    first_bad_step=1, solution_text="1/(1 − 1/2) = 2. Cevap: D"))

# ----------------------------------------------------------------------------- D cells
ITEMS.append(mutate(A2, "ayt-diz-018", mutation="arithmetic_slip", cell="D",
                    claimed={"kind": "value", "payload": "62", "option": "C"},
                    steps_=steps(("s1", "compute", "20*3 = 57", [], "yanlış çarpım"),
                                 ("s2", "compute", "5 + 57 = 62", ["s1"], "")),
                    first_bad_step=1, solution_text="20·3 = 57, 5 + 57 = 62. Cevap: C"))
ITEMS.append(mutate(A5, "ayt-diz-019", mutation="wrong_identity", cell="D",
                    claimed={"kind": "value", "payload": "385", "option": "C"},
                    steps_=steps(("s1", "compute", "Sum(k, (k, 1, 10)) = 50", [], "yanlış yan hesap"),
                                 ("s2", "compute", "10*11*21/6 = 385", [], "")),
                    first_bad_step=1, solution_text="1 + … + 10 = 50; kare toplamı 385. Cevap: C"))
ITEMS.append(mutate(A6, "ayt-diz-020", mutation="arithmetic_slip", cell="D",
                    claimed={"kind": "value", "payload": "1", "option": "B"},
                    steps_=steps(("s1", "compute", "Sum(1/2**k, (k, 1, 3)) = 3/4", [], "yanlış kısmi toplam (7/8)"),
                                 ("s2", "note", "", [], "toplam 1'e yaklaşır")),
                    first_bad_step=1, solution_text="İlk üç terim 3/4; toplam 1. Cevap: B"))
