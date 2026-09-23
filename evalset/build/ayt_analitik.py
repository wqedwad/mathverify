"""AYT — analitik geometri: doğru/çember denklemi, uzaklık, alan."""
from common import item, mutate, steps, mc

ITEMS = []
VXY = [{"name": "x"}, {"name": "y"}]

# ----------------------------------------------------------------------------- 001 iki noktadan geçen doğru
Q1 = "A(1, 2) ve B(4, 8) noktalarından geçen doğrunun denklemi aşağıdakilerden hangisidir?"
IR1 = {"task": {"kind": "equation_of", "params": {"object": "line_points", "p1": ["1", "2"], "p2": ["4", "8"]}},
       "vars": VXY, "givens": [], "answer_shape": "equation",
       "options": mc("y = 2*x", "y = 2*x + 1", "y = x + 1", "y = 3*x - 1", "y = (x + 3)/2")}
A1 = item("ayt-ana-001", "A", "AYT", "analitik geometri", Q1, IR1,
          {"claimed_answer": {"kind": "equation", "payload": "y = 2*x", "option": "A"},
           "steps": steps(("s1", "compute", "slope(1, 2, 4, 8) = 2", [], "eğim"),
                          ("s2", "conclude", "y - 2 = 2*(x - 1)", ["s1"], "nokta-eğim"),
                          ("s3", "conclude", "y = 2*x", ["s2"], ""))},
          "y = 2*x", options=IR1["options"], solution_text="m = (8−2)/(4−1) = 2; y − 2 = 2(x − 1) ⇒ y = 2x. Cevap: A")
ITEMS.append(A1)
ITEMS.append(item("ayt-ana-006", "B", "AYT", "analitik geometri", Q1, IR1,
                  {"claimed_answer": {"kind": "equation", "payload": "y = 2*x", "option": "A"},
                   "steps": steps(("s1", "compute", "slope(1, 2, 4, 8) = 2", [], ""),
                                  ("s2", "eq", "2 = 2*1 + n", [], "y = 2x + n, (1,2) üzerinde"),
                                  ("s3", "eq", "n = 0", ["s2"], ""))},
                  "y = 2*x", options=IR1["options"],
                  solution_text="y = 2x + n; (1,2) için 2 = 2 + n ⇒ n = 0. Cevap: A", notes="eğim-kesim biçimi; n IR'da yok"))
ITEMS.append(item("ayt-ana-007", "B", "AYT", "analitik geometri", Q1, IR1,
                  {"claimed_answer": {"kind": "equation", "payload": "2*x - y = 0", "option": "A"},
                   "steps": steps(("s1", "eq", "(y - 2)/(x - 1) = (8 - 2)/(4 - 1)", [], "iki nokta formülü"),
                                  ("s2", "eq", "2*x - y = 0", ["s1"], "düzenle"))},
                  "y = 2*x", options=IR1["options"],
                  solution_text="(y − 2)/(x − 1) = 6/3 ⇒ 2x − y = 0. Cevap: A", notes="farklı denklem biçimi"))

# ----------------------------------------------------------------------------- 002 uzaklık
Q2 = "A(1, 2) ve B(4, 6) noktaları arasındaki uzaklık kaç birimdir?"
IR2 = {"task": {"kind": "evaluate", "params": {"expr": "dist(1, 2, 4, 6)"}}, "vars": [], "givens": [],
       "answer_shape": "scalar", "options": mc(3, 4, 5, 25, 7), "units": "birim"}
A2 = item("ayt-ana-002", "A", "AYT", "analitik geometri", Q2, IR2,
          {"claimed_answer": {"kind": "value", "payload": "5", "option": "C"},
           "steps": steps(("s1", "compute", "sqrt((4 - 1)**2 + (6 - 2)**2) = 5", [], "uzaklık formülü"))},
          "5", options=IR2["options"], solution_text="√(3² + 4²) = 5. Cevap: C")
ITEMS.append(A2)
ITEMS.append(item("ayt-ana-008", "B", "AYT", "analitik geometri", Q2, IR2,
                  {"claimed_answer": {"kind": "value", "payload": "5", "option": "C"},
                   "steps": steps(("s1", "compute", "4 - 1 = 3", [], "yatay fark"),
                                  ("s2", "compute", "6 - 2 = 4", [], "düşey fark"),
                                  ("s3", "note", "", ["s1", "s2"], "3-4-5 özel dik üçgeni ⇒ hipotenüs 5"))},
                  "5", options=IR2["options"], solution_text="Farklar 3 ve 4: 3-4-5 üçgeni, uzaklık 5. Cevap: C",
                  notes="özel üçgen; formülsüz"))

# ----------------------------------------------------------------------------- 003 çember
Q3 = "Merkezi M(2, −1) ve yarıçapı 3 olan çemberin denklemi aşağıdakilerden hangisidir?"
IR3 = {"task": {"kind": "equation_of", "params": {"object": "circle_center_radius", "center": ["2", "-1"], "radius": "3"}},
       "vars": VXY, "givens": [], "answer_shape": "equation",
       "options": mc("(x - 2)**2 + (y + 1)**2 = 9", "(x + 2)**2 + (y - 1)**2 = 9", "(x - 2)**2 + (y + 1)**2 = 3",
                     "x**2 + y**2 - 4*x + 2*y + 4 = 0", "(x - 2)**2 + (y - 1)**2 = 9")}
A3 = item("ayt-ana-003", "A", "AYT", "analitik geometri", Q3, IR3,
          {"claimed_answer": {"kind": "equation", "payload": "(x - 2)**2 + (y + 1)**2 = 9", "option": "A"},
           "steps": steps(("s1", "conclude", "(x - 2)**2 + (y + 1)**2 = 3**2", [], "standart biçim"))},
          "(x - 2)**2 + (y + 1)**2 = 9", options=IR3["options"], solution_text="(x − 2)² + (y + 1)² = 9. Cevap: A")
ITEMS.append(A3)
ITEMS.append(item("ayt-ana-009", "B", "AYT", "analitik geometri", Q3, IR3,
                  {"claimed_answer": {"kind": "equation", "payload": "x**2 + y**2 - 4*x + 2*y - 4 = 0", "option": "A"},
                   "steps": steps(("s1", "conclude", "(x - 2)**2 + (y + 1)**2 = 9", [], ""),
                                  ("s2", "eq", "(x - 2)**2 + (y + 1)**2 - 9 = x**2 + y**2 - 4*x + 2*y - 4", [], "açılım"))},
                  "(x - 2)**2 + (y + 1)**2 = 9", options=IR3["options"],
                  solution_text="Açık biçim: x² + y² − 4x + 2y − 4 = 0, bu A ile aynı çemberdir. Cevap: A", notes="açık biçim"))

# ----------------------------------------------------------------------------- 004 noktanın doğruya uzaklığı
Q4 = "P(3, 4) noktasının 3x + 4y − 5 = 0 doğrusuna uzaklığı kaç birimdir?"
IR4 = {"task": {"kind": "evaluate", "params": {"expr": "point_line_dist(3, 4, 3, 4, -5)"}}, "vars": [], "givens": [],
       "answer_shape": "scalar", "options": mc(2, 3, 4, 20, 6)}
A4 = item("ayt-ana-004", "A", "AYT", "analitik geometri", Q4, IR4,
          {"claimed_answer": {"kind": "value", "payload": "4", "option": "C"},
           "steps": steps(("s1", "compute", "Abs(3*3 + 4*4 - 5) = 20", [], "pay"),
                          ("s2", "compute", "sqrt(3**2 + 4**2) = 5", [], "payda"),
                          ("s3", "compute", "20/5 = 4", ["s1", "s2"], ""))},
          "4", options=IR4["options"], solution_text="|9 + 16 − 5|/√(9 + 16) = 20/5 = 4. Cevap: C")
ITEMS.append(A4)
ITEMS.append(item("ayt-ana-020", "B", "AYT", "analitik geometri", Q4, IR4,
                  {"claimed_answer": {"kind": "value", "payload": "4", "option": "C"},
                   "steps": steps(("s1", "note", "", [], "P'den doğruya dik doğrultu (3,4) yönünde; birim vektör (3/5, 4/5)"),
                                  ("s2", "compute", "(3*3 + 4*4 - 5)/5 = 4", [], "işaretli uzaklık"),
                                  ("s3", "assert", "4 > 0", ["s2"], ""))},
                  "4", options=IR4["options"], solution_text="Normal vektörle izdüşüm: (9 + 16 − 5)/5 = 4. Cevap: C",
                  notes="vektörel izdüşüm; kanonik olmayan yol"))

# ----------------------------------------------------------------------------- 005 üçgen alanı
Q5 = "Köşeleri A(0, 0), B(4, 0) ve C(0, 3) olan üçgenin alanı kaç birimkaredir?"
IR5 = {"task": {"kind": "evaluate", "params": {"expr": "tri_area(0, 0, 4, 0, 0, 3)"}}, "vars": [], "givens": [],
       "answer_shape": "scalar", "options": mc(5, 6, 7, 12, 24)}
A5 = item("ayt-ana-005", "A", "AYT", "analitik geometri", Q5, IR5,
          {"claimed_answer": {"kind": "value", "payload": "6", "option": "B"},
           "steps": steps(("s1", "note", "", [], "dik üçgen, dik kenarlar 4 ve 3"),
                          ("s2", "compute", "4*3/2 = 6", ["s1"], ""))},
          "6", options=IR5["options"], solution_text="Dik kenarlar 4 ve 3: alan 4·3/2 = 6. Cevap: B")
ITEMS.append(A5)
ITEMS.append(item("ayt-ana-010", "B", "AYT", "analitik geometri", Q5, IR5,
                  {"claimed_answer": {"kind": "value", "payload": "6", "option": "B"},
                   "steps": steps(("s1", "compute", "Abs(0*(0 - 3) + 4*(3 - 0) + 0*(0 - 0))/2 = 6", [], "determinant (ayakkabı bağı) formülü"))},
                  "6", options=IR5["options"], solution_text="Determinant formülü: |0 + 12 + 0|/2 = 6. Cevap: B", notes="determinant formülü"))

# ----------------------------------------------------------------------------- C cells
ITEMS.append(mutate(A1, "ayt-ana-011", mutation="wrong_formula",
                    claimed={"kind": "equation", "payload": "y = (x + 3)/2", "option": "E"},
                    steps_=steps(("s1", "compute", "slope(1, 2, 4, 8) = 1/2", [], "eğim ters alındı"),
                                 ("s2", "conclude", "y - 2 = (x - 1)/2", ["s1"], "")),
                    first_bad_step=1, solution_text="m = 3/6 = 1/2 ⇒ y = (x + 3)/2. Cevap: E"))
ITEMS.append(mutate(A1, "ayt-ana-021", mutation="arithmetic_slip",
                    claimed={"kind": "equation", "payload": "y = 2*x + 1", "option": "B"},
                    steps_=steps(("s1", "compute", "slope(1, 2, 4, 8) = 2", [], ""),
                                 ("s2", "eq", "2 = 2*1 + n", [], ""),
                                 ("s3", "eq", "n = 1", ["s2"], "aritmetik hata")),
                    first_bad_step=3, solution_text="n = 1 ⇒ y = 2x + 1. Cevap: B"))
ITEMS.append(mutate(A2, "ayt-ana-012", mutation="wrong_formula",
                    claimed={"kind": "value", "payload": "25", "option": "D"},
                    steps_=steps(("s1", "compute", "(4 - 1)**2 + (6 - 2)**2 = 25", [], ""),
                                 ("s2", "conclude", "", ["s1"], "karekök alınmadı")),
                    first_bad_step=2, solution_text="3² + 4² = 25. Cevap: D"))
ITEMS.append(mutate(A3, "ayt-ana-013", mutation="sign_flip",
                    claimed={"kind": "equation", "payload": "(x + 2)**2 + (y - 1)**2 = 9", "option": "B"},
                    steps_=steps(("s1", "conclude", "(x + 2)**2 + (y - 1)**2 = 9", [], "merkez işaretleri ters")),
                    first_bad_step=1, solution_text="(x + 2)² + (y − 1)² = 9. Cevap: B"))
ITEMS.append(mutate(A3, "ayt-ana-016", mutation="wrong_formula",
                    claimed={"kind": "equation", "payload": "(x - 2)**2 + (y + 1)**2 = 3", "option": "C"},
                    steps_=steps(("s1", "conclude", "(x - 2)**2 + (y + 1)**2 = 3", [], "yarıçapın karesi alınmadı")),
                    first_bad_step=1, solution_text="(x − 2)² + (y + 1)² = 3. Cevap: C"))
ITEMS.append(mutate(A4, "ayt-ana-014", mutation="wrong_formula",
                    claimed={"kind": "value", "payload": "20", "option": "D"},
                    steps_=steps(("s1", "compute", "Abs(3*3 + 4*4 - 5) = 20", [], ""),
                                 ("s2", "conclude", "", ["s1"], "paydaya bölünmedi")),
                    first_bad_step=2, solution_text="|9 + 16 − 5| = 20. Cevap: D"))
ITEMS.append(mutate(A5, "ayt-ana-015", mutation="wrong_formula",
                    claimed={"kind": "value", "payload": "12", "option": "D"},
                    steps_=steps(("s1", "compute", "4*3 = 12", [], ""),
                                 ("s2", "conclude", "", ["s1"], "ikiye bölünmedi")),
                    first_bad_step=2, solution_text="4·3 = 12. Cevap: D"))
ITEMS.append(mutate(A5, "ayt-ana-022", mutation="arithmetic_slip",
                    claimed={"kind": "value", "payload": "7", "option": "C"},
                    steps_=steps(("s1", "compute", "4*3/2 = 7", [], "aritmetik hata")),
                    first_bad_step=1, solution_text="4·3/2 = 7. Cevap: C"))

# ----------------------------------------------------------------------------- D cells
ITEMS.append(mutate(A2, "ayt-ana-017", mutation="arithmetic_slip", cell="D",
                    claimed={"kind": "value", "payload": "5", "option": "C"},
                    steps_=steps(("s1", "compute", "4 - 1 = 4", [], "yanlış"),
                                 ("s2", "compute", "6 - 2 = 3", [], "yanlış"),
                                 ("s3", "compute", "sqrt(4**2 + 3**2) = 5", ["s1", "s2"], "")),
                    first_bad_step=1, solution_text="Farklar 4 ve 3 ⇒ √(16 + 9) = 5. Cevap: C"))
ITEMS.append(mutate(A4, "ayt-ana-018", mutation="arithmetic_slip", cell="D",
                    claimed={"kind": "value", "payload": "4", "option": "C"},
                    steps_=steps(("s1", "compute", "3*3 + 4*4 - 5 = 25", [], "yanlış toplama"),
                                 ("s2", "compute", "sqrt(3**2 + 4**2) = 5", [], ""),
                                 ("s3", "compute", "25/5 = 4", ["s1", "s2"], "yanlış bölme; sonuç tesadüfen doğru")),
                    first_bad_step=1, solution_text="25/5 = 4. Cevap: C"))
ITEMS.append(mutate(A1, "ayt-ana-019", mutation="arithmetic_slip", cell="D",
                    claimed={"kind": "equation", "payload": "y = 2*x", "option": "A"},
                    steps_=steps(("s1", "compute", "slope(1, 2, 4, 8) = 3", [], "eğim yanlış"),
                                 ("s2", "conclude", "y = 2*x", [], "şık yine A seçildi")),
                    first_bad_step=1, solution_text="m = 3 … y = 2x. Cevap: A"))
