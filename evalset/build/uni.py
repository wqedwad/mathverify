"""UNI — üniversite seviyesi hesaplama: has olmayan integral (E3), determinant, limit, seri."""
from common import item, mutate, steps, mc

ITEMS = []

# ----------------------------------------------------------------------------- 001 has olmayan integral
Q1 = "∫₀¹ (ln x)/√x dx integralinin değeri kaçtır?"
IR1 = {"task": {"kind": "definite_integral", "params": {"integrand": "log(x)/sqrt(x)", "var": "x", "a": "0", "b": "1"}},
       "vars": [{"name": "x"}], "givens": [], "answer_shape": "scalar", "options": mc(-4, -2, -1, 0, 2)}
A1 = item("uni-001", "A", "UNI", "reel analiz", Q1, IR1,
          {"claimed_answer": {"kind": "value", "payload": "-4", "option": "A"},
           "steps": steps(("s1", "compute", "Integral(log(x)/sqrt(x), x) = 2*sqrt(x)*log(x) - 4*sqrt(x)", [], "kısmi integrasyon"),
                          ("s2", "compute", "Limit(2*sqrt(x)*log(x), x, 0, '+') = 0", [], "uç noktada limit"),
                          ("s3", "compute", "(2*1*0 - 4*1) - 0 = -4", ["s1", "s2"], ""))},
          "-4", options=IR1["options"],
          solution_text="Kısmi integrasyon: [2√x ln x − 4√x]₀¹; x→0⁺ iken 2√x ln x → 0 ⇒ −4. Cevap: A")
ITEMS.append(A1)
ITEMS.append(item("uni-006", "B", "UNI", "reel analiz", Q1, IR1,
                  {"claimed_answer": {"kind": "value", "payload": "-4", "option": "A"},
                   "steps": steps(("s1", "note", "", [], "x = t² dönüşümü: dx = 2t dt, ln x = 2 ln t, √x = t"),
                                  ("s2", "compute", "Integral(log(x), (x, 0, 1)) = -1", [], "∫₀¹ ln t dt = −1"),
                                  ("s3", "compute", "4*(-1) = -4", ["s2"], "2·2·∫ ln t dt"))},
                  "-4", options=IR1["options"],
                  solution_text="x = t²: ∫₀¹ (2 ln t)/t · 2t dt = 4∫₀¹ ln t dt = −4. Cevap: A", notes="değişken değiştirme"))
ITEMS.append(item("uni-018", "B", "UNI", "reel analiz", Q1, IR1,
                  {"claimed_answer": {"kind": "value", "payload": "-4", "option": "A"},
                   "steps": steps(("s1", "note", "", [], "Γ-türevi: ∫₀¹ x^{s-1} dx = 1/s, s'ye göre türev: ∫₀¹ x^{s-1} ln x dx = −1/s²"),
                                  ("s2", "compute", "at(-1/s**2, s, 1/2) = -4", [], "s = 1/2"))},
                  "-4", options=IR1["options"],
                  solution_text="∫₀¹ x^{s−1} ln x dx = −1/s², s = 1/2 için −4. Cevap: A",
                  notes="parametreye göre türev; s IR'da yok"))

# ----------------------------------------------------------------------------- 002 determinant
Q2 = "A = [[1, 2], [3, 4]] matrisinin determinantı kaçtır?"
IR2 = {"task": {"kind": "evaluate", "params": {"expr": "det(Matrix([[1, 2], [3, 4]]))"}}, "vars": [], "givens": [],
       "answer_shape": "scalar", "options": mc(-2, -1, 0, 1, 2)}
A2 = item("uni-002", "A", "UNI", "lineer cebir", Q2, IR2,
          {"claimed_answer": {"kind": "value", "payload": "-2", "option": "A"},
           "steps": steps(("s1", "compute", "1*4 - 2*3 = -2", [], "ad − bc"))},
          "-2", options=IR2["options"], solution_text="det = 1·4 − 2·3 = −2. Cevap: A")
ITEMS.append(A2)
ITEMS.append(item("uni-007", "B", "UNI", "lineer cebir", Q2, IR2,
                  {"claimed_answer": {"kind": "value", "payload": "-2", "option": "A"},
                   "steps": steps(("s1", "note", "", [], "det = özdeğerlerin çarpımı; λ² − 5λ − 2 = 0"),
                                  ("s2", "compute", "((5 + sqrt(33))/2)*((5 - sqrt(33))/2) = -2", ["s1"], ""))},
                  "-2", options=IR2["options"],
                  solution_text="Özdeğerler (5 ± √33)/2, çarpımları (25 − 33)/4 = −2. Cevap: A", notes="özdeğer çarpımı"))

# ----------------------------------------------------------------------------- 003 e limiti
Q3 = "lim_{n→∞} (1 + 1/n)ⁿ limitinin değeri nedir?"
IR3 = {"task": {"kind": "limit", "params": {"expr": "(1 + 1/n)**n", "var": "n", "to": "oo"}},
       "vars": [{"name": "n", "domain": "positive_integer"}], "givens": [], "answer_shape": "dne_or_scalar",
       "options": mc(1, 2, "E", "E**2", "∞")}
A3 = item("uni-003", "A", "UNI", "reel analiz", Q3, IR3,
          {"claimed_answer": {"kind": "value", "payload": "E", "option": "C"},
           "steps": steps(("s1", "compute", "Limit(n*log(1 + 1/n), n, oo) = 1", [], "ln L"),
                          ("s2", "compute", "exp(1) = E", ["s1"], ""))},
          "E", options=IR3["options"], solution_text="ln L = lim n ln(1 + 1/n) = 1 ⇒ L = e. Cevap: C")
ITEMS.append(A3)
ITEMS.append(item("uni-009", "B", "UNI", "reel analiz", Q3, IR3,
                  {"claimed_answer": {"kind": "value", "payload": "exp(1)", "option": "C"},
                   "steps": steps(("s1", "note", "", [], "binom açılımı: Σ C(n,k)/n^k → Σ 1/k! (k sabitken n → ∞)"),
                                  ("s2", "compute", "Sum(1/factorial(k), (k, 0, oo)) = E", [], ""))},
                  "E", options=IR3["options"],
                  solution_text="Binom açılımı terim terim 1/k!'e yakınsar; Σ 1/k! = e. Cevap: C", notes="seri argümanı"))

# ----------------------------------------------------------------------------- 004 teleskopik seri
Q4 = "Σ_{k=1}^{∞} 1/(k(k+1)) serisinin toplamı kaçtır?"
IR4 = {"task": {"kind": "evaluate", "params": {"expr": "Sum(1/(k*(k + 1)), (k, 1, oo))"}},
       "vars": [{"name": "k", "domain": "positive_integer"}, {"name": "n", "domain": "positive_integer"}], "givens": [],
       "answer_shape": "scalar", "options": mc("1/2", 1, 2, "log(2)", "∞")}
A4 = item("uni-004", "A", "UNI", "reel analiz", Q4, IR4,
          {"claimed_answer": {"kind": "value", "payload": "1", "option": "B"},
           "steps": steps(("s1", "eq", "1/(k*(k + 1)) = 1/k - 1/(k + 1)", [], "kısmi kesir"),
                          ("s2", "compute", "Sum(1/k - 1/(k + 1), (k, 1, n)) = 1 - 1/(n + 1)", ["s1"], "teleskopik"),
                          ("s3", "compute", "Limit(1 - 1/(n + 1), n, oo) = 1", ["s2"], ""))},
          "1", options=IR4["options"], solution_text="1/(k(k+1)) = 1/k − 1/(k+1); kısmi toplam 1 − 1/(n+1) → 1. Cevap: B")
ITEMS.append(A4)
ITEMS.append(item("uni-008", "B", "UNI", "reel analiz", Q4, IR4,
                  {"claimed_answer": {"kind": "value", "payload": "1", "option": "B"},
                   "steps": steps(("s1", "compute", "Sum(1/(k*(k + 1)), (k, 1, 4)) = 4/5", [], "kısmi toplamlar 1/2, 2/3, 3/4, 4/5"),
                                  ("s2", "note", "", ["s1"], "S_n = n/(n+1) deseni; tümevarımla"),
                                  ("s3", "compute", "Limit(n/(n + 1), n, oo) = 1", [], ""))},
                  "1", options=IR4["options"],
                  solution_text="Kısmi toplamlar n/(n+1) desenini verir; limit 1. Cevap: B", notes="desen + tümevarım"))

# ----------------------------------------------------------------------------- 005 özdeğer
Q5 = "A = [[2, 1], [1, 2]] matrisinin en büyük özdeğeri kaçtır?"
IR5 = {"task": {"kind": "evaluate", "params": {"expr": "eigmax(Matrix([[2, 1], [1, 2]]))"}}, "vars": [], "givens": [],
       "answer_shape": "scalar", "options": mc(1, 2, 3, 4, 5)}
A5 = item("uni-005", "A", "UNI", "lineer cebir", Q5, IR5,
          {"claimed_answer": {"kind": "value", "payload": "3", "option": "C"},
           "steps": steps(("s1", "eq", "det(Matrix([[2 - t, 1], [1, 2 - t]])) = (t - 1)*(t - 3)", [], "karakteristik polinom"),
                          ("s2", "note", "", ["s1"], "özdeğerler 1 ve 3; en büyüğü 3"))},
          "3", options=IR5["options"], solution_text="(2 − λ)² − 1 = 0 ⇒ λ = 1, 3. Cevap: C")
# A5 is kept only as the base of its B/C items so that the four cells land on exactly
# 30/25/30/15 % (N = 180); the canonical solution itself is not part of the set.
ITEMS.append(item("uni-019", "B", "UNI", "lineer cebir", Q5, IR5,
                  {"claimed_answer": {"kind": "value", "payload": "3", "option": "C"},
                   "steps": steps(("s1", "note", "", [], "(1,1) vektörü: A(1,1) = (3,3) ⇒ özdeğer 3"),
                                  ("s2", "compute", "trace(Matrix([[2, 1], [1, 2]])) = 4", [], "iz = özdeğerler toplamı"),
                                  ("s3", "compute", "4 - 3 = 1", ["s2"], "diğer özdeğer 1 < 3"))},
                  "3", options=IR5["options"],
                  solution_text="A(1,1) = (3,3) ⇒ 3 bir özdeğer; iz 4 ⇒ diğeri 1. En büyük 3. Cevap: C", notes="özvektör tahmini + iz"))

# ----------------------------------------------------------------------------- C cells
ITEMS.append(mutate(A1, "uni-010", mutation="arithmetic_slip",
                    claimed={"kind": "value", "payload": "-2", "option": "B"},
                    steps_=steps(("s1", "compute", "Integral(log(x)/sqrt(x), x) = 2*sqrt(x)*log(x) - 2*sqrt(x)", [], "katsayı hatası"),
                                 ("s2", "compute", "(0 - 2) - 0 = -2", ["s1"], "")),
                    first_bad_step=1, solution_text="[2√x ln x − 2√x]₀¹ = −2. Cevap: B"))
ITEMS.append(mutate(A2, "uni-011", mutation="sign_flip",
                    claimed={"kind": "value", "payload": "2", "option": "E"},
                    steps_=steps(("s1", "compute", "1*4 - 2*3 = 2", [], "işaret hatası")),
                    first_bad_step=1, solution_text="det = 4 − 6 = 2. Cevap: E"))
ITEMS.append(mutate(A3, "uni-012", mutation="wrong_formula",
                    claimed={"kind": "value", "payload": "1", "option": "A"},
                    steps_=steps(("s1", "note", "", [], "1/n → 0 olduğundan taban 1'e gider; 1^∞ = 1 (belirsizlik gözden kaçtı)")),
                    first_bad_step=1, solution_text="(1 + 0)^∞ = 1. Cevap: A"))
ITEMS.append(mutate(A4, "uni-013", mutation="arithmetic_slip",
                    claimed={"kind": "value", "payload": "1/2", "option": "A"},
                    steps_=steps(("s1", "eq", "1/(k*(k + 1)) = 1/k - 1/(k + 1)", [], ""),
                                 ("s2", "compute", "Sum(1/k - 1/(k + 1), (k, 1, oo)) = 1/2", ["s1"], "ilk terim 1/2 sanıldı")),
                    first_bad_step=2, solution_text="Teleskopik toplam ilk terime eşittir: 1/2. Cevap: A"))
ITEMS.append(mutate(A5, "uni-014", mutation="wrong_option",
                    claimed={"kind": "value", "payload": "1", "option": "A"},
                    steps_=steps(("s1", "eq", "det(Matrix([[2 - t, 1], [1, 2 - t]])) = (t - 1)*(t - 3)", [], ""),
                                 ("s2", "conclude", "", ["s1"], "en küçük özdeğer alındı")),
                    first_bad_step=2, solution_text="λ = 1, 3; cevap 1. Cevap: A"))
ITEMS.append(mutate(A2, "uni-020", mutation="wrong_formula",
                    claimed={"kind": "value", "payload": "-1", "option": "B"},
                    steps_=steps(("s1", "compute", "1*4 - 2*3 = -2", [], ""),
                                 ("s2", "compute", "-2/2 = -1", ["s1"], "gereksiz ikiye bölme")),
                    first_bad_step=2, solution_text="det = −2/2 = −1. Cevap: B"))

# ----------------------------------------------------------------------------- D cells
ITEMS.append(mutate(A2, "uni-015", mutation="arithmetic_slip", cell="D",
                    claimed={"kind": "value", "payload": "-2", "option": "A"},
                    steps_=steps(("s1", "compute", "1*4 = 5", [], "yanlış"),
                                 ("s2", "compute", "2*3 = 7", [], "yanlış"),
                                 ("s3", "compute", "5 - 7 = -2", ["s1", "s2"], "")),
                    first_bad_step=1, solution_text="1·4 = 5, 2·3 = 7, 5 − 7 = −2. Cevap: A"))
ITEMS.append(mutate(A4, "uni-016", mutation="wrong_identity", cell="D",
                    claimed={"kind": "value", "payload": "1", "option": "B"},
                    steps_=steps(("s1", "eq", "1/(k*(k + 1)) = 1/k + 1/(k + 1)", [], "yanlış kısmi kesir"),
                                 ("s2", "compute", "Limit(1 - 1/(n + 1), n, oo) = 1", [], "doğru sonuca sıçrandı")),
                    first_bad_step=1, solution_text="1/(k(k+1)) = 1/k + 1/(k+1) … → 1. Cevap: B"))
ITEMS.append(mutate(A3, "uni-017", mutation="arithmetic_slip", cell="D",
                    claimed={"kind": "value", "payload": "E", "option": "C"},
                    steps_=steps(("s1", "compute", "Limit(n*log(1 + 1/n), n, oo) = 0", [], "yanlış limit"),
                                 ("s2", "conclude", "", ["s1"], "yine de e seçildi")),
                    first_bad_step=1, solution_text="n ln(1 + 1/n) → 0 … L = e. Cevap: C"))
