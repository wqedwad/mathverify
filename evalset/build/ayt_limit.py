"""AYT — limit ve süreklilik."""
from common import item, mutate, steps, mc

ITEMS = []
VX = [{"name": "x"}]

# ----------------------------------------------------------------------------- 001 0/0 sadeleştirme
Q1 = "lim_{x→2} (x² − 4)/(x − 2) limitinin değeri kaçtır?"
IR1 = {"task": {"kind": "limit", "params": {"expr": "(x**2 - 4)/(x - 2)", "var": "x", "to": "2"}}, "vars": VX,
       "givens": [], "answer_shape": "dne_or_scalar", "options": mc(0, 2, 4, 8, "limit yoktur")}
A1 = item("ayt-lim-001", "A", "AYT", "limit", Q1, IR1,
          {"claimed_answer": {"kind": "value", "payload": "4", "option": "C"},
           "steps": steps(("s1", "eq", "(x**2 - 4)/(x - 2) = x + 2", [], "x ≠ 2 için sadeleştir"),
                          ("s2", "compute", "Limit(x + 2, x, 2) = 4", ["s1"], ""))},
          "4", options=IR1["options"], solution_text="(x−2)(x+2)/(x−2) = x + 2 → 4. Cevap: C")
ITEMS.append(A1)

# ----------------------------------------------------------------------------- 002 sin(3x)/x
Q2 = "lim_{x→0} sin(3x)/x limitinin değeri kaçtır?"
IR2 = {"task": {"kind": "limit", "params": {"expr": "sin(3*x)/x", "var": "x", "to": "0"}}, "vars": VX,
       "givens": [], "answer_shape": "dne_or_scalar", "options": mc(0, 1, 3, "1/3", "limit yoktur")}
A2 = item("ayt-lim-002", "A", "AYT", "limit", Q2, IR2,
          {"claimed_answer": {"kind": "value", "payload": "3", "option": "C"},
           "steps": steps(("s1", "eq", "sin(3*x)/x = 3*sin(3*x)/(3*x)", [], ""),
                          ("s2", "compute", "Limit(sin(3*x)/(3*x), x, 0) = 1", [], "temel limit"),
                          ("s3", "compute", "3*1 = 3", ["s1", "s2"], ""))},
          "3", options=IR2["options"], solution_text="sin(3x)/x = 3·sin(3x)/(3x) → 3·1 = 3. Cevap: C")
ITEMS.append(A2)
ITEMS.append(item("ayt-lim-007", "B", "AYT", "limit", Q2, IR2,
                  {"claimed_answer": {"kind": "value", "payload": "3", "option": "C"},
                   "steps": steps(("s1", "note", "", [], "0/0 belirsizliği: L'Hôpital"),
                                  ("s2", "compute", "diff(sin(3*x), x) = 3*cos(3*x)", [], ""),
                                  ("s3", "compute", "Limit(3*cos(3*x), x, 0) = 3", ["s2"], ""))},
                  "3", options=IR2["options"],
                  solution_text="L'Hôpital: (sin 3x)'/(x)' = 3cos 3x → 3. Cevap: C", notes="L'Hôpital; kanonik olmayan yol"))

# ----------------------------------------------------------------------------- 003 |x|/x
Q3 = "lim_{x→0} |x|/x limiti için aşağıdakilerden hangisi doğrudur?"
IR3 = {"task": {"kind": "limit", "params": {"expr": "Abs(x)/x", "var": "x", "to": "0"}}, "vars": VX,
       "givens": [], "answer_shape": "dne_or_scalar", "options": mc(-1, 0, 1, 2, "limit yoktur")}
A3 = item("ayt-lim-003", "A", "AYT", "limit", Q3, IR3,
          {"claimed_answer": {"kind": "dne", "payload": None, "option": "E"},
           "steps": steps(("s1", "compute", "Limit(Abs(x)/x, x, 0, '+') = 1", [], "sağdan"),
                          ("s2", "compute", "Limit(Abs(x)/x, x, 0, '-') = -1", [], "soldan"),
                          ("s3", "note", "", ["s1", "s2"], "tek yönlü limitler farklı ⇒ limit yoktur"))},
          "DNE", options=IR3["options"], solution_text="Sağdan 1, soldan −1; limit yoktur. Cevap: E")
ITEMS.append(A3)

# ----------------------------------------------------------------------------- 004 sonsuzda limit
Q4 = "lim_{x→∞} (2x² + 1)/(x² − 5) limitinin değeri kaçtır?"
IR4 = {"task": {"kind": "limit", "params": {"expr": "(2*x**2 + 1)/(x**2 - 5)", "var": "x", "to": "oo"}}, "vars": VX,
       "givens": [], "answer_shape": "dne_or_scalar", "options": mc(0, 1, 2, 5, "∞")}
A4 = item("ayt-lim-004", "A", "AYT", "limit", Q4, IR4,
          {"claimed_answer": {"kind": "value", "payload": "2", "option": "C"},
           "steps": steps(("s1", "eq", "(2*x**2 + 1)/(x**2 - 5) = (2 + 1/x**2)/(1 - 5/x**2)", [], "x²'ye böl"),
                          ("s2", "compute", "Limit((2 + 1/x**2)/(1 - 5/x**2), x, oo) = 2", ["s1"], ""))},
          "2", options=IR4["options"], solution_text="Dereceler eşit; başkatsayılar oranı 2/1 = 2. Cevap: C")
ITEMS.append(A4)
ITEMS.append(item("ayt-lim-013", "B", "AYT", "limit", Q4, IR4,
                  {"claimed_answer": {"kind": "value", "payload": "2", "option": "C"},
                   "steps": steps(("s1", "note", "", [], "∞/∞: L'Hôpital iki kez"),
                                  ("s2", "compute", "diff(2*x**2 + 1, x) = 4*x", [], ""),
                                  ("s3", "compute", "diff(x**2 - 5, x) = 2*x", [], ""),
                                  ("s4", "compute", "Limit(4*x/(2*x), x, oo) = 2", ["s2", "s3"], ""))},
                  "2", options=IR4["options"],
                  solution_text="L'Hôpital: 4x/2x → 2. Cevap: C", notes="L'Hôpital; kanonik olmayan yol"))

# ----------------------------------------------------------------------------- 005 köklü
Q5 = "lim_{x→1} (√x − 1)/(x − 1) limitinin değeri kaçtır?"
IR5 = {"task": {"kind": "limit", "params": {"expr": "(sqrt(x) - 1)/(x - 1)", "var": "x", "to": "1"}}, "vars": VX,
       "givens": [], "answer_shape": "dne_or_scalar", "options": mc(0, "1/4", "1/2", 1, 2)}
A5 = item("ayt-lim-005", "A", "AYT", "limit", Q5, IR5,
          {"claimed_answer": {"kind": "value", "payload": "1/2", "option": "C"},
           "steps": steps(("s1", "eq", "(sqrt(x) - 1)/(x - 1) = 1/(sqrt(x) + 1)", [], "x − 1 = (√x−1)(√x+1)"),
                          ("s2", "compute", "Limit(1/(sqrt(x) + 1), x, 1) = 1/2", ["s1"], ""))},
          "1/2", options=IR5["options"], solution_text="x − 1 = (√x − 1)(√x + 1) ⇒ 1/(√x + 1) → 1/2. Cevap: C")
ITEMS.append(A5)
ITEMS.append(item("ayt-lim-008", "B", "AYT", "limit", Q5, IR5,
                  {"claimed_answer": {"kind": "value", "payload": "1/2", "option": "C"},
                   "steps": steps(("s1", "note", "", [], "t = √x dersek x = t², x → 1 iken t → 1"),
                                  ("s2", "eq", "(t - 1)/(t**2 - 1) = 1/(t + 1)", [], ""),
                                  ("s3", "compute", "Limit(1/(t + 1), t, 1) = 1/2", ["s2"], ""))},
                  "1/2", options=IR5["options"],
                  solution_text="t = √x: (t − 1)/(t² − 1) = 1/(t + 1) → 1/2. Cevap: C",
                  notes="değişken değiştirme; t IR'da yok → adımlar atlanır"))

# ----------------------------------------------------------------------------- 006 x ln x
Q6 = "lim_{x→0⁺} x·ln x limitinin değeri kaçtır?"
IR6 = {"task": {"kind": "limit", "params": {"expr": "x*log(x)", "var": "x", "to": "0", "side": "+"}}, "vars": VX,
       "givens": [], "answer_shape": "dne_or_scalar", "options": mc(-1, 0, 1, "-∞", "∞")}
A6 = item("ayt-lim-006", "A", "AYT", "limit", Q6, IR6,
          {"claimed_answer": {"kind": "value", "payload": "0", "option": "B"},
           "steps": steps(("s1", "eq", "x*log(x) = log(x)/(1/x)", [], "∞/∞ biçimi"),
                          ("s2", "compute", "Limit((1/x)/(-1/x**2), x, 0, '+') = 0", [], "L'Hôpital"))},
          "0", options=IR6["options"], solution_text="ln x/(1/x) için L'Hôpital: (1/x)/(−1/x²) = −x → 0. Cevap: B")
ITEMS.append(A6)

# ----------------------------------------------------------------------------- C cells
ITEMS.append(mutate(A3, "ayt-lim-009", mutation="one_sided_limit",
                    claimed={"kind": "value", "payload": "1", "option": "C"},
                    steps_=steps(("s1", "compute", "Limit(Abs(x)/x, x, 0) = 1", [], "x > 0 için |x| = x alındı; soldan bakılmadı")),
                    first_bad_step=1, solution_text="|x|/x = x/x = 1. Cevap: C"))
ITEMS.append(mutate(A4, "ayt-lim-010", mutation="wrong_formula",
                    claimed={"kind": "infinite", "payload": "oo", "option": "E"},
                    steps_=steps(("s1", "note", "", [], "pay ve payda sonsuza gider ⇒ limit sonsuz (belirsizlik gözden kaçtı)")),
                    first_bad_step=1, solution_text="x → ∞ iken pay ve payda büyür; limit ∞. Cevap: E"))
ITEMS.append(mutate(A6, "ayt-lim-014", mutation="wrong_formula",
                    claimed={"kind": "infinite", "payload": "-oo", "option": "D"},
                    steps_=steps(("s1", "note", "", [], "ln x → −∞ olduğundan çarpım da −∞ (0·∞ belirsizliği gözden kaçtı)")),
                    first_bad_step=1, solution_text="x → 0⁺ iken ln x → −∞, dolayısıyla x·ln x → −∞. Cevap: D"))
ITEMS.append(mutate(A5, "ayt-lim-011", mutation="arithmetic_slip",
                    claimed={"kind": "value", "payload": "1", "option": "D"},
                    steps_=steps(("s1", "eq", "(sqrt(x) - 1)/(x - 1) = 1/(sqrt(x) + 1)", [], ""),
                                 ("s2", "compute", "Limit(1/(sqrt(x) + 1), x, 1) = 1", ["s1"], "1/(1+1) yanlış hesaplandı")),
                    first_bad_step=2, solution_text="1/(√x + 1) → 1. Cevap: D"))

# ----------------------------------------------------------------------------- D cells
ITEMS.append(mutate(A1, "ayt-lim-012", mutation="wrong_identity", cell="D",
                    claimed={"kind": "value", "payload": "4", "option": "C"},
                    steps_=steps(("s1", "eq", "(x**2 - 4)/(x - 2) = x - 2", [], "yanlış sadeleştirme"),
                                 ("s2", "compute", "Limit(x - 2, x, 2) = 4", ["s1"], "yanlış değerlendirme; sonuç tesadüfen doğru")),
                    first_bad_step=1, solution_text="(x² − 4)/(x − 2) = x − 2 → 4. Cevap: C"))
