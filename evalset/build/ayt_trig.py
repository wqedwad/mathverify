"""AYT — trigonometri: periyodik çözüm kümeleri (E1), açı değerleri, derece/radyan."""
from common import item, mutate, steps, mc

ITEMS = []
VX = [{"name": "x"}]

# ----------------------------------------------------------------------------- 001 cos 2x = 1/2 on [0, 2π)
Q1 = "cos 2x = 1/2 denkleminin [0, 2π) aralığındaki çözüm kümesi aşağıdakilerden hangisidir?"
IR1 = {"task": {"kind": "trig_solve", "params": {"var": "x", "interval": "[0, 2*pi)"}}, "vars": VX,
       "givens": ["cos(2*x) = 1/2"], "answer_shape": "set",
       "options": mc("{pi/6, 5*pi/6}", "{pi/6, 5*pi/6, 7*pi/6, 11*pi/6}", "{pi/3, 5*pi/3}", "{pi/6, 11*pi/6}",
                     "{pi/3, 2*pi/3, 4*pi/3, 5*pi/3}")}
A1 = item("ayt-trig-001", "A", "AYT", "trigonometri", Q1, IR1,
          {"claimed_answer": {"kind": "set", "payload": "{pi/6, 5*pi/6, 7*pi/6, 11*pi/6}", "option": "B"},
           "steps": steps(("s1", "note", "", [], "2x ∈ [0, 4π); cos t = 1/2 ⇒ t = π/3 + 2kπ veya 5π/3 + 2kπ"),
                          ("s2", "note", "", ["s1"], "2x ∈ {π/3, 5π/3, 7π/3, 11π/3}"),
                          ("s3", "eq", "x in {pi/6, 5*pi/6, 7*pi/6, 11*pi/6}", ["s2"], "ikiye böl"))},
          "{pi/6, 5*pi/6, 7*pi/6, 11*pi/6}", options=IR1["options"],
          solution_text="2x ∈ {π/3, 5π/3, 7π/3, 11π/3} ⇒ x ∈ {π/6, 5π/6, 7π/6, 11π/6}. Cevap: B")
ITEMS.append(A1)
ITEMS.append(item("ayt-trig-005", "B", "AYT", "trigonometri", Q1, IR1,
                  {"claimed_answer": {"kind": "set", "payload": "{pi/6, 5*pi/6, 7*pi/6, 11*pi/6}", "option": "B"},
                   "steps": steps(("s1", "note", "", [], "B şıkkındaki dört değeri yerine koy"),
                                  ("s2", "compute", "cos(2*pi/6) = 1/2", [], ""),
                                  ("s3", "compute", "cos(2*5*pi/6) = 1/2", [], ""),
                                  ("s4", "compute", "cos(2*7*pi/6) = 1/2", [], ""),
                                  ("s5", "compute", "cos(2*11*pi/6) = 1/2", [], ""),
                                  ("s6", "note", "", [], "cos 2x fonksiyonunun periyodu π; [0,2π)'de 2 periyot × 2 çözüm = 4"))},
                  "{pi/6, 5*pi/6, 7*pi/6, 11*pi/6}", options=IR1["options"],
                  solution_text="Dört değer de sağlar ve periyot π olduğundan başka çözüm yoktur. Cevap: B",
                  notes="şık deneme + sayım argümanı"))
ITEMS.append(item("ayt-trig-009", "B", "AYT", "trigonometri", Q1, IR1,
                  {"claimed_answer": {"kind": "set", "payload": "{pi/6, 5*pi/6, 7*pi/6, 11*pi/6}", "option": "B"},
                   "steps": steps(("s1", "eq", "2*cos(x)**2 - 1 = 1/2", [], "cos 2x = 2cos²x − 1"),
                                  ("s2", "eq", "cos(x)**2 = 3/4", ["s1"], ""),
                                  ("s3", "eq", "x in {pi/6, 5*pi/6, 7*pi/6, 11*pi/6}", ["s2"], "cos x = ±√3/2"))},
                  "{pi/6, 5*pi/6, 7*pi/6, 11*pi/6}", options=IR1["options"],
                  solution_text="2cos²x − 1 = 1/2 ⇒ cos x = ±√3/2 ⇒ x ∈ {π/6, 5π/6, 7π/6, 11π/6}. Cevap: B",
                  notes="yarım açı özdeşliği üzerinden; kanonik olmayan yol"))

# ----------------------------------------------------------------------------- 002 genel çözüm sin x = 1/2
Q2 = "sin x = 1/2 denkleminin çözüm kümesi aşağıdakilerden hangisidir? (k ∈ Z)"
IR2 = {"task": {"kind": "trig_solve", "params": {"var": "x"}}, "vars": VX, "givens": ["sin(x) = 1/2"],
       "answer_shape": "set",
       "options": mc("{pi/6 + 2*k*pi}", "{pi/6 + 2*k*pi, 5*pi/6 + 2*k*pi}", "{pi/6 + k*pi}",
                     "{pi/6 + k*pi, 5*pi/6 + k*pi}", "{pi/3 + 2*k*pi, 2*pi/3 + 2*k*pi}")}
A2 = item("ayt-trig-002", "A", "AYT", "trigonometri", Q2, IR2,
          {"claimed_answer": {"kind": "set", "payload": "{pi/6 + 2*k*pi, 5*pi/6 + 2*k*pi}", "option": "B"},
           "steps": steps(("s1", "compute", "sin(pi/6) = 1/2", [], "temel açı"),
                          ("s2", "note", "", ["s1"], "sin(π − π/6) = sin(5π/6) = 1/2; periyot 2π"))},
          "{pi/6 + 2*k*pi, 5*pi/6 + 2*k*pi}", options=IR2["options"],
          solution_text="x = π/6 + 2kπ veya x = 5π/6 + 2kπ. Cevap: B")
ITEMS.append(A2)
ITEMS.append(item("ayt-trig-006", "B", "AYT", "trigonometri", Q2, IR2,
                  {"claimed_answer": {"kind": "set", "payload": "{pi/6 + 2*k*pi, 5*pi/6 + 2*k*pi}", "option": "B"},
                   "steps": steps(("s1", "note", "", [], "birim çemberde y = 1/2 doğrusu çemberi iki noktada keser"),
                                  ("s2", "compute", "sin(pi/6) = 1/2", [], "I. bölge"),
                                  ("s3", "compute", "sin(5*pi/6) = 1/2", [], "II. bölge"),
                                  ("s4", "note", "", ["s2", "s3"], "her tam turda tekrar: +2kπ"))},
                  "{pi/6 + 2*k*pi, 5*pi/6 + 2*k*pi}", options=IR2["options"],
                  solution_text="Birim çemberde iki kesişim: π/6 ve 5π/6, her turda tekrar. Cevap: B", notes="birim çember argümanı"))

# ----------------------------------------------------------------------------- 003 sin 75°
Q3 = "sin 75° değeri aşağıdakilerden hangisidir?"
IR3 = {"task": {"kind": "evaluate", "params": {"expr": "sin(75°)"}}, "vars": [], "givens": [], "answer_shape": "scalar",
       "options": mc("(sqrt(6) + sqrt(2))/4", "(sqrt(6) - sqrt(2))/4", "sqrt(3)/2", "(sqrt(2) + 1)/2", "sqrt(2)/2")}
A3 = item("ayt-trig-003", "A", "AYT", "trigonometri", Q3, IR3,
          {"claimed_answer": {"kind": "value", "payload": "(sqrt(6) + sqrt(2))/4", "option": "A"},
           "steps": steps(("s1", "eq", "sin(75°) = sin(45°)*cos(30°) + cos(45°)*sin(30°)", [], "toplam formülü"),
                          ("s2", "compute", "sin(45°)*cos(30°) + cos(45°)*sin(30°) = (sqrt(6) + sqrt(2))/4", ["s1"], ""))},
          "(sqrt(6) + sqrt(2))/4", options=IR3["options"],
          solution_text="sin(45° + 30°) = (√2/2)(√3/2) + (√2/2)(1/2) = (√6 + √2)/4. Cevap: A")
ITEMS.append(A3)
ITEMS.append(item("ayt-trig-007", "B", "AYT", "trigonometri", Q3, IR3,
                  {"claimed_answer": {"kind": "value", "payload": "(sqrt(6) + sqrt(2))/4", "option": "A"},
                   "steps": steps(("s1", "eq", "sin(75°) = sin(135° - 60°)", [], "fark formülü"),
                                  ("s2", "compute", "sin(135°)*cos(60°) - cos(135°)*sin(60°) = (sqrt(6) + sqrt(2))/4", ["s1"], ""))},
                  "(sqrt(6) + sqrt(2))/4", options=IR3["options"],
                  solution_text="sin(135° − 60°) = (√2/2)(1/2) − (−√2/2)(√3/2) = (√2 + √6)/4. Cevap: A",
                  notes="135° − 60° ayrışımı; kanonik olmayan yol"))
ITEMS.append(item("ayt-trig-019", "B", "AYT", "trigonometri", Q3, IR3,
                  {"claimed_answer": {"kind": "value", "payload": "sqrt(2 + sqrt(3))/2", "option": "A"},
                   "steps": steps(("s1", "eq", "sin(75°)**2 = (1 - cos(150°))/2", [], "yarım açı"),
                                  ("s2", "compute", "(1 - cos(150°))/2 = (2 + sqrt(3))/4", ["s1"], ""),
                                  ("s3", "eq", "sin(75°) = sqrt(2 + sqrt(3))/2", ["s2"], "pozitif kök"))},
                  "(sqrt(6) + sqrt(2))/4", options=IR3["options"],
                  solution_text="Yarım açı: sin²75° = (1 − cos 150°)/2 = (2 + √3)/4 ⇒ sin 75° = √(2 + √3)/2 = (√6 + √2)/4. Cevap: A",
                  notes="eşdeğer ama farklı biçim (iç içe kök): sadeleştirme testi"))

# ----------------------------------------------------------------------------- 004 tan x = √3 on [0, π)
Q4 = "tan x = √3 denkleminin [0, π) aralığındaki çözümü kaçtır?"
IR4 = {"task": {"kind": "trig_solve", "params": {"var": "x", "interval": "[0, pi)"}}, "vars": VX,
       "givens": ["tan(x) = sqrt(3)"], "answer_shape": "set", "options": mc("pi/6", "pi/3", "2*pi/3", "pi/4", "5*pi/6")}
A4 = item("ayt-trig-004", "A", "AYT", "trigonometri", Q4, IR4,
          {"claimed_answer": {"kind": "value", "payload": "pi/3", "option": "B"},
           "steps": steps(("s1", "compute", "tan(pi/3) = sqrt(3)", [], ""),
                          ("s2", "note", "", [], "tan periyodu π; [0, π)'de tek çözüm"))},
          "{pi/3}", options=IR4["options"], solution_text="tan(π/3) = √3 ve periyot π. Cevap: B")
ITEMS.append(A4)
ITEMS.append(item("ayt-trig-008", "B", "AYT", "trigonometri", Q4, IR4,
                  {"claimed_answer": {"kind": "value", "payload": "60°", "option": "B"},
                   "steps": steps(("s1", "note", "", [], "30-60-90 üçgeni: karşı/komşu = √3 ⇒ açı 60°"),
                                  ("s2", "compute", "60° = pi/3", [], "radyana çevir"),
                                  ("s3", "note", "", [], "[0, π)'de tan yalnız I. bölgede pozitif"))},
                  "{pi/3}", options=IR4["options"],
                  solution_text="Özel üçgenden 60° = π/3; aralıkta tan yalnız I. bölgede pozitif. Cevap: B",
                  notes="derece cinsinden cevap; eşdeğerlik testi"))

# ----------------------------------------------------------------------------- C cells
ITEMS.append(mutate(A1, "ayt-trig-010", mutation="missing_case",
                    claimed={"kind": "set", "payload": "{pi/6, 5*pi/6}", "option": "A"},
                    steps_=steps(("s1", "note", "", [], "2x = π/3 veya 5π/3"),
                                 ("s2", "eq", "x in {pi/6, 5*pi/6}", ["s1"], "2x için [0, 4π) yerine [0, 2π) alındı"),
                                 ("s3", "conclude", "", ["s2"], "")),
                    first_bad_step=2, solution_text="2x = π/3, 5π/3 ⇒ x = π/6, 5π/6. Cevap: A"))
ITEMS.append(mutate(A1, "ayt-trig-014", mutation="degree_radian",
                    claimed={"kind": "set", "payload": "{30, 150, 210, 330}", "option": "B"},
                    steps_=steps(("s1", "note", "", [], "2x = 60, 300, 420, 660 (derece)"),
                                 ("s2", "eq", "x in {30, 150, 210, 330}", ["s1"], "derece işareti olmadan yazıldı; aralık radyan")),
                    first_bad_step=2, solution_text="x ∈ {30, 150, 210, 330}. Cevap: B"))
ITEMS.append(mutate(A1, "ayt-trig-020", mutation="wrong_formula",
                    claimed={"kind": "set", "payload": "{pi/3, 5*pi/3}", "option": "C"},
                    steps_=steps(("s1", "eq", "x in {pi/3, 5*pi/3}", [], "2x yerine x çözüldü"),
                                 ("s2", "conclude", "", ["s1"], "")),
                    first_bad_step=1, solution_text="cos x = 1/2 ⇒ x ∈ {π/3, 5π/3}. Cevap: C"))
ITEMS.append(mutate(A2, "ayt-trig-011", mutation="wrong_formula",
                    claimed={"kind": "set", "payload": "{pi/6 + k*pi, 5*pi/6 + k*pi}", "option": "D"},
                    steps_=steps(("s1", "compute", "sin(pi/6) = 1/2", [], ""),
                                 ("s2", "note", "", [], "periyot π alındı (sinüsün periyodu 2π)")),
                    first_bad_step=2, solution_text="x = π/6 + kπ veya 5π/6 + kπ. Cevap: D"))
ITEMS.append(mutate(A2, "ayt-trig-015", mutation="missing_case",
                    claimed={"kind": "set", "payload": "{pi/6 + 2*k*pi}", "option": "A"},
                    steps_=steps(("s1", "compute", "sin(pi/6) = 1/2", [], ""),
                                 ("s2", "note", "", [], "II. bölge unutuldu")),
                    first_bad_step=2, solution_text="x = π/6 + 2kπ. Cevap: A"))
ITEMS.append(mutate(A3, "ayt-trig-012", mutation="sign_flip",
                    claimed={"kind": "value", "payload": "(sqrt(6) - sqrt(2))/4", "option": "B"},
                    steps_=steps(("s1", "eq", "sin(75°) = sin(45° - 30°)", [], "75 = 45 − 30 (yanlış)"),
                                 ("s2", "compute", "sin(45°)*cos(30°) - cos(45°)*sin(30°) = (sqrt(6) - sqrt(2))/4", ["s1"], "")),
                    first_bad_step=1, solution_text="sin(45° − 30°) = (√6 − √2)/4. Cevap: B"))
ITEMS.append(mutate(A4, "ayt-trig-013", mutation="wrong_formula",
                    claimed={"kind": "value", "payload": "2*pi/3", "option": "C"},
                    steps_=steps(("s1", "compute", "tan(2*pi/3) = sqrt(3)", [], "II. bölgede tan negatif; işaret hatası")),
                    first_bad_step=1, solution_text="tan(2π/3) = √3. Cevap: C"))

# ----------------------------------------------------------------------------- D cells
ITEMS.append(mutate(A3, "ayt-trig-016", mutation="wrong_identity", cell="D",
                    claimed={"kind": "value", "payload": "(sqrt(6) + sqrt(2))/4", "option": "A"},
                    steps_=steps(("s1", "compute", "sin(75°) = sin(15°)", [], "yanlış ilişki (kullanılmadı)"),
                                 ("s2", "compute", "sin(45°)*cos(30°) + cos(45°)*sin(30°) = (sqrt(6) + sqrt(2))/4", [], "")),
                    first_bad_step=1, solution_text="sin 75° = sin 15° … = (√6 + √2)/4. Cevap: A"))
ITEMS.append(mutate(A4, "ayt-trig-017", mutation="degree_radian", cell="D",
                    claimed={"kind": "value", "payload": "pi/3", "option": "B"},
                    steps_=steps(("s1", "compute", "tan(pi/3) = sqrt(3)", [], ""),
                                 ("s2", "compute", "60° = pi/2", [], "yanlış dönüşüm; şık yine doğru seçildi")),
                    first_bad_step=2, solution_text="tan 60° = √3, 60° = π/2 … Cevap: B"))
ITEMS.append(mutate(A1, "ayt-trig-018", mutation="arithmetic_slip", cell="D",
                    claimed={"kind": "set", "payload": "{pi/6, 5*pi/6, 7*pi/6, 11*pi/6}", "option": "B"},
                    steps_=steps(("s1", "compute", "cos(pi/6) = 1/2", [], "yanlış değer (cos π/6 = √3/2)"),
                                 ("s2", "note", "", [], "2x = π/3 + 2kπ veya 5π/3 + 2kπ"),
                                 ("s3", "eq", "x in {pi/6, 5*pi/6, 7*pi/6, 11*pi/6}", ["s2"], "")),
                    first_bad_step=1, solution_text="cos π/6 = 1/2 … x ∈ {π/6, 5π/6, 7π/6, 11π/6}. Cevap: B"))
ITEMS.append(mutate(A2, "ayt-trig-021", mutation="wrong_identity", cell="D",
                    claimed={"kind": "set", "payload": "{pi/6 + 2*k*pi, 5*pi/6 + 2*k*pi}", "option": "B"},
                    steps_=steps(("s1", "eq", "sin(x) = cos(x - pi/2)", [], "doğru"),
                                 ("s2", "eq", "sin(x) = cos(x + pi/2)", [], "yanlış özdeşlik"),
                                 ("s3", "compute", "sin(pi/6) = 1/2", [], ""),
                                 ("s4", "note", "", [], "5π/6 ve periyot 2π")),
                    first_bad_step=2, solution_text="sin x = cos(x + π/2) … x = π/6 + 2kπ, 5π/6 + 2kπ. Cevap: B"))
