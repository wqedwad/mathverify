"""TYT — router'da tanımlı olup değerlendirme setinde hiç ölçülmemiş üç görev türü.

`domain_of`, `simplify_expression` ve `count_solutions` sertifika modülleri yazılmış ve birim
testleri vardı, ama sette tek bir öğeleri yoktu: raporlanan 1.000 precision bu üç tür hakkında
hiçbir şey söylemiyordu. Burada her biri için A/B/C/D hücreleri üretilir.

Ayrıca LaTeX ayrıştırma yolu buradan ölçülür. Ölçüm: 260 öğenin **sıfırı** LaTeX dalını
tetikliyordu, oysa gerçek bir modelin yazdığı çözüm ezici çoğunlukla LaTeX'tir ve o dal
kanonik ayrıştırıcıdan ayrı tokenleştirme yapar. `tyt-kap-011` iddiasını LaTeX olarak verir.
"""
from common import item, mutate, steps, mc

ITEMS = []

# ============================================================ domain_of
# ----------------------------------------------------------------------------- Q1 karekök
Q1 = "f(x) = √(x − 3) fonksiyonunun en geniş tanım kümesi aşağıdakilerden hangisidir?"
IR1 = {"task": {"kind": "domain_of", "params": {"expr": "sqrt(x - 3)", "var": "x"}},
       "vars": [{"name": "x"}], "givens": [], "answer_shape": "interval",
       "options": mc("[3, oo)", "(3, oo)", "(-oo, 3]", "[-3, oo)", "(-oo, -3]")}
A1 = item("tyt-kap-001", "A", "TYT", "fonksiyonlar", Q1, IR1,
          {"claimed_answer": {"kind": "interval", "payload": "[3, oo)", "option": "A"},
           "steps": steps(("s1", "eq", "x - 3 >= 0", [], "karekökün içi negatif olamaz"),
                          ("s2", "note", "", ["s1"], "x ≥ 3"))},
          "[3, oo)", options=IR1["options"],
          solution_text="Karekökün içi $x - 3 \\ge 0$ olmalı, yani $x \\ge 3$. Cevap: A")
ITEMS.append(A1)
ITEMS.append(item("tyt-kap-002", "B", "TYT", "fonksiyonlar", Q1, IR1,
                  {"claimed_answer": {"kind": "interval", "payload": "Interval(3, oo)", "option": "A"},
                   "steps": steps(("s1", "note", "", [], "tanımsızlık yalnız kökün içinden gelir"),
                                  ("s2", "compute", "sqrt(3 - 3) = 0", [], "uç nokta tanımlı"),
                                  ("s3", "eq", "x >= 3", [], "kalan koşul"))},
                  "[3, oo)", options=IR1["options"],
                  solution_text="Uç noktada $\\sqrt{0}=0$ tanımlı, dolayısıyla 3 dahildir: $[3,\\infty)$. Cevap: A",
                  notes="kanonik olmayan gösterim (Interval(...)) + uç nokta ayrı gerekçelendirildi"))
ITEMS.append(mutate(A1, "tyt-kap-003", mutation="endpoint_error",
                    claimed={"kind": "interval", "payload": "(3, oo)", "option": "B"},
                    steps_=steps(("s1", "eq", "x - 3 > 0", [], "kökün içi pozitif olmalı (yanlış: sıfır da olur)"),
                                 ("s2", "note", "", ["s1"], "x > 3")),
                    solution_text="Kökün içi pozitif olmalı: $x > 3$. Cevap: B"))

# ----------------------------------------------------------------------------- Q2 rasyonel
Q2 = "f(x) = 1/(x² − 4) fonksiyonunun en geniş tanım kümesi aşağıdakilerden hangisidir?"
IR2 = {"task": {"kind": "domain_of", "params": {"expr": "1/(x**2 - 4)", "var": "x"}},
       "vars": [{"name": "x"}], "givens": [], "answer_shape": "set",
       "options": mc("(-oo, -2) U (-2, 2) U (2, oo)", "(-oo, -2) U (2, oo)", "(-2, 2)",
                     "(-oo, 2) U (2, oo)", "(-oo, -2) U (-2, oo)")}
A2 = item("tyt-kap-004", "A", "TYT", "fonksiyonlar", Q2, IR2,
          {"claimed_answer": {"kind": "set", "payload": "(-oo, -2) U (-2, 2) U (2, oo)", "option": "A"},
           "steps": steps(("s1", "eq", "x != -2", [], "payda sıfır olamaz"),
                          ("s2", "eq", "x != 2", [], "payda sıfır olamaz"))},
          "(-oo, -2) U (-2, 2) U (2, oo)", options=IR2["options"],
          solution_text="Payda sıfır olmamalı: $x^2 - 4 \\ne 0 \\Rightarrow x \\ne \\pm 2$. Cevap: A")
ITEMS.append(A2)
ITEMS.append(mutate(A2, "tyt-kap-005", mutation="missing_case",
                    claimed={"kind": "set", "payload": "(-oo, -2) U (2, oo)", "option": "B"},
                    steps_=steps(("s1", "eq", "x**2 - 4 > 0", [], "yanlış: payda sıfırdan farklı olmalı, pozitif değil"),
                                 ("s2", "note", "", ["s1"], "x < −2 veya x > 2")),
                    solution_text="$x^2 - 4 > 0$ olmalı, yani $x < -2$ ya da $x > 2$. Cevap: B"))
ITEMS.append(mutate(A2, "tyt-kap-006", cell="D", mutation="arithmetic_slip", first_bad_step=1,
                    steps_=steps(("s1", "compute", "(-2)**2 - 4 = -8", [], "paydayı x = −2'de hesapladım"),
                                 ("s2", "note", "", ["s1"], "her iki kök de tanım kümesinden çıkarılır")),
                    notes="cevap doğru; s1 aritmetiği yanlış (gerçek değer 0), somut hesapla çürütülür",
                    solution_text="$x=-2$ için payda $-8$ çıkıyor; $\\pm 2$ dışlanır. Cevap: A"))

# ----------------------------------------------------------------------------- Q3 logaritma
Q3 = "f(x) = ln(x − 1) fonksiyonunun en geniş tanım kümesi aşağıdakilerden hangisidir?"
IR3 = {"task": {"kind": "domain_of", "params": {"expr": "log(x - 1)", "var": "x"}},
       "vars": [{"name": "x"}], "givens": [], "answer_shape": "interval",
       "options": mc("(1, oo)", "[1, oo)", "(-oo, 1)", "(0, oo)", "(-1, oo)")}
A3 = item("tyt-kap-007", "A", "TYT", "fonksiyonlar", Q3, IR3,
          {"claimed_answer": {"kind": "interval", "payload": "(1, oo)", "option": "A"},
           "steps": steps(("s1", "eq", "x - 1 > 0", [], "logaritmanın içi pozitif olmalı"),
                          ("s2", "note", "", ["s1"], "x > 1"))},
          "(1, oo)", options=IR3["options"],
          solution_text="$\\ln$ içi pozitif olmalı: $x - 1 > 0 \\Rightarrow x > 1$. Cevap: A")
ITEMS.append(A3)
ITEMS.append(item("tyt-kap-008", "B", "TYT", "fonksiyonlar", Q3, IR3,
                  {"claimed_answer": {"kind": "interval", "payload": "Interval.open(1, oo)", "option": "A"},
                   "steps": steps(("s1", "note", "", [], "ln t yalnız t > 0 için tanımlı"),
                                  ("s2", "eq", "x > 1", [], "t = x − 1 yerine konursa"))},
                  "(1, oo)", options=IR3["options"],
                  solution_text="$t = x-1$ diyelim; $\\ln t$ için $t>0$ gerekir, yani $x>1$. Cevap: A",
                  notes="değişken değiştirme ile; kanonik olmayan Interval.open gösterimi"))
ITEMS.append(mutate(A3, "tyt-kap-009", mutation="log_domain",
                    claimed={"kind": "interval", "payload": "[1, oo)", "option": "B"},
                    steps_=steps(("s1", "eq", "x - 1 >= 0", [], "yanlış: ln 0 tanımsızdır"),
                                 ("s2", "note", "", ["s1"], "x ≥ 1")),
                    solution_text="$x - 1 \\ge 0$ olmalı: $x \\ge 1$. Cevap: B"))

# ============================================================ simplify_expression
# ----------------------------------------------------------------------------- Q4 rasyonel toplam
Q4 = "1/x + 1/(x + 1) ifadesinin tek kesir hâlindeki eşiti aşağıdakilerden hangisidir?"
IR4 = {"task": {"kind": "simplify_expression", "params": {"expr": "1/x + 1/(x + 1)"}},
       "vars": [{"name": "x"}], "givens": [], "answer_shape": "expression",
       "options": mc("(2*x + 1)/(x*(x + 1))", "(2*x + 1)/(x + 1)", "2/(2*x + 1)",
                     "(x + 1)/(x*(x + 1))", "1/(x*(x + 1))")}
A4 = item("tyt-kap-010", "A", "TYT", "polinom", Q4, IR4,
          {"claimed_answer": {"kind": "expression", "payload": "(2*x + 1)/(x*(x + 1))", "option": "A"},
           "steps": steps(("s1", "compute", "1/x + 1/(x + 1) = (2*x + 1)/(x*(x + 1))", [], "ortak payda"))},
          "(2*x + 1)/(x*(x + 1))", options=IR4["options"],
          solution_text="Ortak paydada: $\\frac{1}{x}+\\frac{1}{x+1}=\\frac{2x+1}{x(x+1)}$. Cevap: A")
ITEMS.append(A4)
ITEMS.append(item("tyt-kap-011", "B", "TYT", "polinom", Q4, IR4,
                  # LaTeX iddia: 260 öğenin hiçbiri LaTeX dalını tetiklemiyordu (ölçüldü)
                  {"claimed_answer": {"kind": "expression", "payload": "\\frac{2x+1}{x^2+x}", "option": "A"},
                   "steps": steps(("s1", "compute", "x*(x + 1) = x**2 + x", [], "paydayı açtım"),
                                  ("s2", "note", "", ["s1"], "pay 2x + 1 olarak kalır"))},
                  "(2*x + 1)/(x*(x + 1))", options=IR4["options"],
                  solution_text="Payda açılmış hâliyle $\\frac{2x+1}{x^{2}+x}$. Cevap: A",
                  notes="doğru ama kanonik olmayan gösterim; iddia LaTeX olarak verildi"))
ITEMS.append(mutate(A4, "tyt-kap-012", mutation="arithmetic_slip",
                    claimed={"kind": "expression", "payload": "2/(2*x + 1)", "option": "C"},
                    steps_=steps(("s1", "compute", "1/x + 1/(x + 1) = 2/(2*x + 1)", [], "payları ve paydaları ayrı topladım")),
                    solution_text="Payları ve paydaları toplayınca $\\frac{2}{2x+1}$. Cevap: C"))

# ----------------------------------------------------------------------------- Q5 kare farkı
Q5 = "(x + 1)² − (x − 1)² ifadesinin en sade hâli aşağıdakilerden hangisidir?"
IR5 = {"task": {"kind": "simplify_expression", "params": {"expr": "(x + 1)**2 - (x - 1)**2"}},
       "vars": [{"name": "x"}], "givens": [], "answer_shape": "expression",
       "options": mc("4*x", "2*x", "2", "4", "x**2 + 1")}
A5 = item("tyt-kap-013", "A", "TYT", "polinom", Q5, IR5,
          {"claimed_answer": {"kind": "expression", "payload": "4*x", "option": "A"},
           "steps": steps(("s1", "compute", "(x + 1)**2 - (x - 1)**2 = 4*x", [], "kare farkı"))},
          "4*x", options=IR5["options"],
          solution_text="$a^2-b^2=(a-b)(a+b)$ ile $((x+1)-(x-1))((x+1)+(x-1)) = 2\\cdot 2x = 4x$. Cevap: A")
ITEMS.append(A5)
ITEMS.append(mutate(A5, "tyt-kap-014", mutation="arithmetic_slip",
                    claimed={"kind": "expression", "payload": "2*x", "option": "B"},
                    steps_=steps(("s1", "compute", "(x + 1)**2 - (x - 1)**2 = 2*x", [], "çarpanı unuttum")),
                    solution_text="$((x+1)-(x-1))\\cdot x = 2x$. Cevap: B"))
ITEMS.append(mutate(A5, "tyt-kap-015", cell="D", mutation="wrong_identity", first_bad_step=2,
                    steps_=steps(("s1", "compute", "(x + 1)**2 - (x - 1)**2 = 4*x", [], "sonuç"),
                                 ("s2", "eq", "x**2 + 2*x + 1 = x**2 - 2*x + 1", ["s1"],
                                  "iki kareyi eşitledim (geçersiz)")),
                    notes="cevap doğru; s2 somut karşı örnekle çürütülebilir",
                    solution_text="$(x+1)^2 = (x-1)^2$ diyip farkı aldım, $4x$ buldum. Cevap: A"))

# ============================================================ count_solutions
# ----------------------------------------------------------------------------- Q6 x + y = 10
Q6 = "x + y = 10 denklemini sağlayan kaç farklı (x, y) pozitif tam sayı ikilisi vardır?"
IR6 = {"task": {"kind": "count_solutions", "params": {"bounds": {"x": ["1", "10"], "y": ["1", "10"]}}},
       "vars": [{"name": "x", "domain": "positive_integer"}, {"name": "y", "domain": "positive_integer"}],
       "givens": ["x + y = 10"], "answer_shape": "count", "options": mc(8, 9, 10, 11, 12)}
A6 = item("tyt-kap-016", "A", "TYT", "denklem", Q6, IR6,
          {"claimed_answer": {"kind": "count", "payload": 9, "option": "B"},
           "steps": steps(("s1", "eq", "y = 10 - x", [], "y'yi çektim"),
                          ("s2", "note", "", ["s1"], "x = 1..9 için y = 9..1 pozitif: 9 ikili"))},
          "9", options=IR6["options"],
          solution_text="$y = 10 - x$; $x$ 1'den 9'a kadar pozitif değerler alır, 9 ikili. Cevap: B")
ITEMS.append(A6)
ITEMS.append(item("tyt-kap-017", "B", "TYT", "denklem", Q6, IR6,
                  {"claimed_answer": {"kind": "count", "payload": 9, "option": "B"},
                   "steps": steps(("s1", "eq", "x >= 1", [], "pozitiflik"),
                                  ("s2", "eq", "x <= 9", [], "y ≥ 1 olmasından"),
                                  ("s3", "compute", "9 - 1 + 1 = 9", ["s1", "s2"], "tam sayı sayımı"))},
                  "9", options=IR6["options"],
                  solution_text="$1 \\le x \\le 9$ aralığında $9-1+1 = 9$ tam sayı var. Cevap: B",
                  notes="aralık sayımı yöntemi (kanonik olmayan)"))
ITEMS.append(mutate(A6, "tyt-kap-018", mutation="off_by_one",
                    claimed={"kind": "count", "payload": 11, "option": "D"},
                    steps_=steps(("s1", "eq", "y = 10 - x", [], ""),
                                 ("s2", "note", "", ["s1"], "x = 0..10 dedim (yanlış: pozitif olmalı)")),
                    solution_text="$x$ 0'dan 10'a kadar 11 değer alır. Cevap: D"))

# ----------------------------------------------------------------------------- Q7 2x + 3y = 12
Q7 = "2x + 3y = 12 denklemini sağlayan kaç farklı (x, y) negatif olmayan tam sayı ikilisi vardır?"
IR7 = {"task": {"kind": "count_solutions", "params": {"bounds": {"x": ["0", "12"], "y": ["0", "12"]}}},
       "vars": [{"name": "x", "domain": "nonneg_integer"}, {"name": "y", "domain": "nonneg_integer"}],
       "givens": ["2*x + 3*y = 12"], "answer_shape": "count", "options": mc(2, 3, 4, 5, 6)}
B7 = item("tyt-kap-019", "B", "TYT", "denklem", Q7, IR7,
          {"claimed_answer": {"kind": "count", "payload": 3, "option": "B"},
           "steps": steps(("s1", "note", "", [], "2x = 12 − 3y çift olmalı, yani y çift"),
                          ("s2", "note", "", ["s1"], "y ∈ {0, 2, 4} ⇒ x ∈ {6, 3, 0}"))},
          "3", options=IR7["options"],
          solution_text="$2x = 12-3y$ çift olmalı, dolayısıyla $y$ çift: $y\\in\\{0,2,4\\}$, 3 ikili. Cevap: B",
          notes="parite argümanı (kanonik olmayan)")
ITEMS.append(B7)
ITEMS.append(mutate(B7, "tyt-kap-020", cell="D", mutation="missing_case", first_bad_step=1,
                    steps_=steps(("s1", "eq", "y = 4", [], "y'yi tek bir değere sabitledim (geçersiz)"),
                                 ("s2", "note", "", ["s1"], "yine de y = 0, 2, 4 sayıldı: 3 ikili")),
                    notes="cevap doğru; s1 öncüllerden çıkmayan ve karşı örnekle çürütülebilen bir iddia",
                    solution_text="$y = 4$ alıp sonra $y=0,2,4$ saydım: 3 ikili. Cevap: B"))
