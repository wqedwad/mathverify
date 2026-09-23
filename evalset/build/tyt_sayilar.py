"""TYT — sayılar / temel kavramlar. Original synthetic questions."""
from common import item, mutate, steps, mc

ITEMS = []

# ----------------------------------------------------------------------------- 001 OBEB
Q1 = "OBEB(84, 120) kaçtır?"
IR1 = {"task": {"kind": "evaluate", "params": {"expr": "gcd(84, 120)"}}, "vars": [], "givens": [],
       "answer_shape": "scalar", "options": mc(6, 8, 12, 24, 36)}
A1 = item("tyt-say-001", "A", "TYT", "sayılar", Q1, IR1,
          {"claimed_answer": {"kind": "value", "payload": "12", "option": "C"},
           "steps": steps(("s1", "compute", "84 = 2**2 * 3 * 7", [], "asal çarpanlar"),
                          ("s2", "compute", "120 = 2**3 * 3 * 5", [], ""),
                          ("s3", "compute", "gcd(84, 120) = 2**2 * 3", ["s1", "s2"], "ortak çarpanların en küçük üsleri"))},
          "12", options=IR1["options"], solution_text="84 = 2²·3·7, 120 = 2³·3·5; OBEB = 2²·3 = 12. Cevap: C")
ITEMS.append(A1)
ITEMS.append(item("tyt-say-007", "B", "TYT", "sayılar", Q1, IR1,
                  {"claimed_answer": {"kind": "value", "payload": "12", "option": "C"},
                   "steps": steps(("s1", "compute", "Mod(120, 84) = 36", [], "Öklid"),
                                  ("s2", "compute", "Mod(84, 36) = 12", ["s1"], ""),
                                  ("s3", "compute", "Mod(36, 12) = 0", ["s2"], "son sıfırdan farklı kalan 12"))},
                  "12", options=IR1["options"],
                  solution_text="Öklid: 120 = 84·1 + 36, 84 = 36·2 + 12, 36 = 12·3. OBEB = 12. Cevap: C",
                  notes="Öklid algoritması; kanonik olmayan yol"))

# ----------------------------------------------------------------------------- 002 diyofant
Q2 = "x ve y pozitif tam sayılar olmak üzere 3x + 5y = 41 ve x < y ise x + y kaçtır?"
IR2 = {"task": {"kind": "evaluate", "params": {"expr": "x + y"}},
       "vars": [{"name": "x", "domain": "positive_integer"}, {"name": "y", "domain": "positive_integer"}],
       "givens": ["3*x + 5*y = 41", "x < y"], "unknown_of_interest": "x + y", "answer_shape": "scalar",
       "options": mc(7, 8, 9, 10, 11)}
A2 = item("tyt-say-002", "A", "TYT", "sayılar", Q2, IR2,
          {"claimed_answer": {"kind": "value", "payload": "9", "option": "C"},
           "steps": steps(("s1", "note", "", [], "5y ≤ 41 ⇒ y ≤ 8; 41 − 5y, 3'e bölünmeli"),
                          ("s2", "note", "", [], "y = 1 → x = 12; y = 4 → x = 7; y = 7 → x = 2"),
                          ("s3", "case", "y = 7", ["s2"], "x < y sağlayan tek çift"),
                          ("s4", "eq", "x = 2", ["s3"], ""),
                          ("s5", "compute", "2 + 7 = 9", ["s3", "s4"], ""))},
          "9", options=IR2["options"],
          solution_text="41 − 5y'nin 3'e bölünmesi için y ∈ {1, 4, 7}; x < y yalnız (2, 7) ile sağlanır. x + y = 9. Cevap: C")
ITEMS.append(A2)

# ----------------------------------------------------------------------------- 003 basamak
Q3 = "İki basamaklı bir doğal sayının rakamları toplamı 11'dir. Rakamlarının yerleri değiştirildiğinde elde edilen sayı, sayının kendisinden 27 fazla olduğuna göre bu sayı kaçtır?"
IR3 = {"task": {"kind": "evaluate", "params": {"expr": "10*a + b"}},
       "vars": [{"name": "a", "domain": "integer", "constraints": ["a >= 1", "a <= 9"]},
                {"name": "b", "domain": "integer", "constraints": ["b >= 0", "b <= 9"]}],
       "givens": ["a + b = 11", "(10*b + a) - (10*a + b) = 27"], "unknown_of_interest": "10*a + b",
       "answer_shape": "scalar", "options": mc(38, 47, 56, 65, 74)}
A3 = item("tyt-say-003", "A", "TYT", "sayılar", Q3, IR3,
          {"claimed_answer": {"kind": "value", "payload": "47", "option": "B"},
           "steps": steps(("s1", "eq", "9*b - 9*a = 27", [], "ikinci koşul"),
                          ("s2", "eq", "b - a = 3", ["s1"], ""),
                          ("s3", "eq", "b = 7", ["s2"], "a + b = 11 ile"),
                          ("s4", "eq", "a = 4", ["s3"], ""),
                          ("s5", "compute", "10*4 + 7 = 47", ["s3", "s4"], ""))},
          "47", options=IR3["options"],
          solution_text="Sayı 10a + b. (10b + a) − (10a + b) = 9(b − a) = 27 ⇒ b − a = 3; a + b = 11 ⇒ b = 7, a = 4. Sayı 47. Cevap: B")
ITEMS.append(A3)
ITEMS.append(item("tyt-say-008", "B", "TYT", "sayılar", Q3, IR3,
                  {"claimed_answer": {"kind": "value", "payload": "47", "option": "B"},
                   "steps": steps(("s1", "case", "a = 4", [], "B şıkkı: 47"),
                                  ("s2", "case", "b = 7", [], ""),
                                  ("s3", "compute", "4 + 7 = 11", ["s1", "s2"], "rakamlar toplamı ✓"),
                                  ("s4", "compute", "74 - 47 = 27", ["s1", "s2"], "ters çevrilmiş fark ✓"))},
                  "47", options=IR3["options"],
                  solution_text="Şıkları kontrol edelim: 47 için 4 + 7 = 11 ✓ ve 74 − 47 = 27 ✓. Cevap: B", notes="şık deneme"))

# ----------------------------------------------------------------------------- 004 ardışık çift
Q4 = "Ardışık üç çift doğal sayının toplamı 78 olduğuna göre bu sayıların en büyüğü kaçtır?"
IR4 = {"task": {"kind": "evaluate", "params": {"expr": "n + 4"}},
       "vars": [{"name": "n", "domain": "nonneg_integer"}],
       "givens": ["Mod(n, 2) = 0", "n + (n + 2) + (n + 4) = 78"], "unknown_of_interest": "n + 4",
       "answer_shape": "scalar", "options": mc(24, 26, 28, 30, 32)}
A4 = item("tyt-say-004", "A", "TYT", "sayılar", Q4, IR4,
          {"claimed_answer": {"kind": "value", "payload": "28", "option": "C"},
           "steps": steps(("s1", "eq", "3*n + 6 = 78", [], "n, n+2, n+4"),
                          ("s2", "eq", "n = 24", ["s1"], ""),
                          ("s3", "eq", "n + 4 = 28", ["s2"], ""))},
          "28", options=IR4["options"], solution_text="n + (n+2) + (n+4) = 3n + 6 = 78 ⇒ n = 24; en büyüğü 28. Cevap: C")
ITEMS.append(A4)
ITEMS.append(item("tyt-say-009", "B", "TYT", "sayılar", Q4, IR4,
                  {"claimed_answer": {"kind": "value", "payload": "28", "option": "C"},
                   "steps": steps(("s1", "compute", "78/3 = 26", [], "ortadaki sayı = ortalama"),
                                  ("s2", "eq", "n + 2 = 26", ["s1"], "ortadaki sayı"),
                                  ("s3", "eq", "n + 4 = 28", ["s2"], "en büyüğü ortadakinin 2 fazlası"))},
                  "28", options=IR4["options"],
                  solution_text="Ardışık sayılarda ortadaki sayı ortalamadır: 78/3 = 26; en büyüğü 28. Cevap: C",
                  notes="ortalama/simetri argümanı; kanonik olmayan yol"))

# ----------------------------------------------------------------------------- 005 tam sayı sayımı
Q5 = "x² − 5x − 14 < 0 eşitsizliğini sağlayan kaç farklı x tam sayısı vardır?"
IR5 = {"task": {"kind": "count_integers", "params": {"var": "x"}},
       "vars": [{"name": "x", "domain": "integer"}], "givens": ["x**2 - 5*x - 14 < 0"],
       "answer_shape": "count", "options": mc(6, 7, 8, 9, 10)}
A5 = item("tyt-say-005", "A", "TYT", "sayılar", Q5, IR5,
          {"claimed_answer": {"kind": "count", "payload": 8, "option": "C"},
           "steps": steps(("s1", "eq", "x**2 - 5*x - 14 = (x - 7)*(x + 2)", [], "çarpanlara ayır"),
                          ("s2", "note", "", ["s1"], "−2 < x < 7"),
                          ("s3", "compute", "6 - (-1) + 1 = 8", ["s2"], "−1'den 6'ya"))},
          "8", options=IR5["options"], solution_text="(x − 7)(x + 2) < 0 ⇒ −2 < x < 7 ⇒ x ∈ {−1, …, 6}: 8 tam sayı. Cevap: C")
ITEMS.append(A5)

# ----------------------------------------------------------------------------- 006 modüler
Q6 = "5^100 sayısının 7 ile bölümünden kalan kaçtır?"
IR6 = {"task": {"kind": "evaluate", "params": {"expr": "Mod(5**100, 7)"}}, "vars": [], "givens": [],
       "answer_shape": "scalar", "options": mc(1, 2, 3, 4, 5), "sanity": ["ans >= 0", "ans < 7"]}
A6 = item("tyt-say-006", "A", "TYT", "sayılar", Q6, IR6,
          {"claimed_answer": {"kind": "value", "payload": "2", "option": "B"},
           "steps": steps(("s1", "compute", "Mod(5**6, 7) = 1", [], "Fermat"),
                          ("s2", "compute", "Mod(100, 6) = 4", [], ""),
                          ("s3", "compute", "Mod(5**4, 7) = 2", ["s1", "s2"], "625 = 89·7 + 2"))},
          "2", options=IR6["options"], solution_text="5⁶ ≡ 1 (mod 7); 100 = 6·16 + 4 ⇒ 5⁴ = 625 ≡ 2. Cevap: B")
ITEMS.append(A6)

# ----------------------------------------------------------------------------- C cells
ITEMS.append(mutate(A1, "tyt-say-010", mutation="arithmetic_slip",
                    claimed={"kind": "value", "payload": "24", "option": "D"},
                    steps_=steps(("s1", "compute", "84 = 2**2 * 3 * 7", [], ""),
                                 ("s2", "compute", "120 = 2**3 * 3 * 5", [], ""),
                                 ("s3", "compute", "gcd(84, 120) = 2**3 * 3", ["s1", "s2"], "en büyük üs alındı (yanlış)")),
                    first_bad_step=3, solution_text="OBEB = 2³·3 = 24. Cevap: D"))
ITEMS.append(mutate(A3, "tyt-say-011", mutation="sign_flip",
                    claimed={"kind": "value", "payload": "74", "option": "E"},
                    steps_=steps(("s1", "eq", "a + b = 11", [], ""),
                                 ("s2", "eq", "a - b = 3", [], "fark ters yazıldı"),
                                 ("s3", "eq", "a = 7", ["s1", "s2"], ""),
                                 ("s4", "eq", "10*a + b = 74", ["s3"], "")),
                    first_bad_step=2, solution_text="a − b = 3, a + b = 11 ⇒ a = 7, b = 4; sayı 74. Cevap: E"))
ITEMS.append(mutate(A4, "tyt-say-012", mutation="arithmetic_slip",
                    claimed={"kind": "value", "payload": "30", "option": "D"},
                    steps_=steps(("s1", "eq", "3*n = 78", [], "6 unutuldu"),
                                 ("s2", "eq", "n = 26", ["s1"], ""),
                                 ("s3", "eq", "n + 4 = 30", ["s2"], "")),
                    first_bad_step=1, solution_text="3n = 78 ⇒ n = 26 ⇒ en büyüğü 30. Cevap: D"))
ITEMS.append(mutate(A5, "tyt-say-013", mutation="endpoint_error",
                    claimed={"kind": "count", "payload": 10, "option": "E"},
                    steps_=steps(("s1", "eq", "x**2 - 5*x - 14 = (x - 7)*(x + 2)", [], ""),
                                 ("s2", "note", "", ["s1"], "−2 ≤ x ≤ 7 (uç noktalar yanlışlıkla dahil)"),
                                 ("s3", "compute", "7 - (-2) + 1 = 10", ["s2"], "")),
                    first_bad_step=2, solution_text="−2 ≤ x ≤ 7 aralığında 10 tam sayı vardır. Cevap: E"))

# ----------------------------------------------------------------------------- D cells
ITEMS.append(mutate(A6, "tyt-say-014", mutation="arithmetic_slip", cell="D",
                    claimed={"kind": "value", "payload": "2", "option": "B"},
                    steps_=steps(("s1", "compute", "Mod(5**6, 7) = 1", [], ""),
                                 ("s2", "compute", "Mod(100, 6) = 2", [], "yanlış kalan"),
                                 ("s3", "compute", "Mod(5**2, 7) = 2", ["s1", "s2"], "25 mod 7 aslında 4; iki hata birbirini götürdü")),
                    first_bad_step=2, solution_text="100 ≡ 2 (mod 6) ⇒ 5² = 25 ≡ 2 (mod 7). Cevap: B"))
ITEMS.append(mutate(A4, "tyt-say-016", mutation="arithmetic_slip", cell="D",
                    claimed={"kind": "value", "payload": "28", "option": "C"},
                    steps_=steps(("s1", "eq", "3*n + 6 = 78", [], ""),
                                 ("s2", "eq", "3*n = 74", ["s1"], "çıkarma hatası"),
                                 ("s3", "eq", "n = 24", ["s2"], "74/3 yanlış bölündü; iki hata birbirini götürdü"),
                                 ("s4", "eq", "n + 4 = 28", ["s3"], "")),
                    first_bad_step=2, solution_text="3n = 74 ⇒ n = 24 ⇒ en büyüğü 28. Cevap: C"))
ITEMS.append(mutate(A2, "tyt-say-015", mutation="wrong_identity", cell="D",
                    claimed={"kind": "value", "payload": "9", "option": "C"},
                    steps_=steps(("s1", "eq", "Mod(y, 3) = 2", [], "41 ≡ 2 (mod 3) ve 5 ≡ 2 ⇒ y ≡ 2 (hatalı çıkarım; doğrusu y ≡ 1)"),
                                 ("s2", "case", "y = 7", [], "deneme"),
                                 ("s3", "compute", "41 - 5*7 = 6", ["s2"], ""),
                                 ("s4", "eq", "x = 2", ["s2", "s3"], ""),
                                 ("s5", "compute", "2 + 7 = 9", ["s2", "s4"], "")),
                    first_bad_step=1, solution_text="y ≡ 2 (mod 3) olmalı; y = 7 alınırsa x = 2, x + y = 9. Cevap: C"))
