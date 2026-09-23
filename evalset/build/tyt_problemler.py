"""TYT — problemler (word problems). All questions are original/synthetic (no ÖSYM text)."""
from common import item, mutate, steps, mc

ITEMS = []

# ----------------------------------------------------------------------------- 001 tavuk/koyun
Q1 = "Bir çiftlikteki tavuk ve koyunların baş sayısı toplamı 30, ayak sayısı toplamı 88'dir. Bu çiftlikte kaç tavuk vardır?"
IR1 = {"task": {"kind": "evaluate", "params": {"expr": "a"}},
       "vars": [{"name": "a", "domain": "positive_integer"}, {"name": "b", "domain": "positive_integer"}],
       "givens": ["a + b = 30", "2*a + 4*b = 88"], "unknown_of_interest": "a", "answer_shape": "scalar",
       "options": mc(12, 14, 16, 18, 20), "sanity": ["ans > 0", "ans < 30"]}
A1 = item("tyt-prob-001", "A", "TYT", "problemler", Q1, IR1,
          {"claimed_answer": {"kind": "value", "payload": "16", "option": "C"},
           "steps": steps(("s1", "eq", "b = 30 - a", [], "baş sayısından"),
                          ("s2", "eq", "2*a + 4*(30 - a) = 88", ["s1"], "ayak sayısına yerine koy"),
                          ("s3", "eq", "-2*a + 120 = 88", ["s2"], "dağıt"),
                          ("s4", "eq", "a = 16", ["s3"], "çöz"))},
          "16", options=IR1["options"],
          solution_text="Tavuk sayısı a, koyun sayısı b olsun. a + b = 30 ve 2a + 4b = 88. b = 30 − a yazılırsa 2a + 120 − 4a = 88, −2a = −32, a = 16.\nCevap: C",
          notes="kanonik yol: yerine koyma")
ITEMS.append(A1)
ITEMS.append(item("tyt-prob-002", "B", "TYT", "problemler", Q1, IR1,
                  {"claimed_answer": {"kind": "value", "payload": "16", "option": "C"},
                   "steps": steps(("s1", "case", "a = 16", [], "C şıkkını deneyelim"),
                                  ("s2", "eq", "b = 14", ["s1"], "30 − 16"),
                                  ("s3", "compute", "2*16 + 4*14 = 88", ["s1", "s2"], "ayak sayısı tutuyor"),
                                  ("s4", "note", "", [], "diğer şıklar 88 vermez"))},
                  "16", options=IR1["options"],
                  solution_text="Şıkları deneyelim. C) 16 tavuk ise 14 koyun: 2·16 + 4·14 = 32 + 56 = 88 ✓. Cevap: C",
                  notes="şık deneme; kanonik değil"))

# ----------------------------------------------------------------------------- 003 işçi
Q3 = "Ali bir işi tek başına 6 saatte, Veli aynı işi tek başına 3 saatte bitirebilmektedir. İkisi birlikte çalışırsa bu işi kaç saatte bitirirler?"
IR3 = {"task": {"kind": "evaluate", "params": {"expr": "t"}},
       "vars": [{"name": "t", "domain": "positive_real"}],
       "givens": ["t*(1/6 + 1/3) = 1"], "unknown_of_interest": "t", "answer_shape": "scalar",
       "options": mc(1, 2, 3, 4, 5), "units": "saat", "sanity": ["ans > 0", "ans < 3"]}
A3 = item("tyt-prob-003", "A", "TYT", "problemler", Q3, IR3,
          {"claimed_answer": {"kind": "value", "payload": "2", "option": "B"},
           "steps": steps(("s1", "compute", "1/6 + 1/3 = 1/2", [], "birlikte saatte yapılan iş"),
                          ("s2", "eq", "t = 2", ["s1"], "1/(1/2)"))},
          "2", options=IR3["options"],
          solution_text="Ali saatte 1/6, Veli 1/3 iş yapar; birlikte 1/6 + 1/3 = 1/2. İş 1/(1/2) = 2 saatte biter.\nCevap: B")
ITEMS.append(A3)
ITEMS.append(item("tyt-prob-008", "B", "TYT", "problemler", Q3, IR3,
                  {"claimed_answer": {"kind": "value", "payload": "2", "option": "B"},
                   "steps": steps(("s1", "note", "", [], "İşi 6 birim alalım"),
                                  ("s2", "compute", "6/6 + 6/3 = 3", [], "birlikte saatte 3 birim"),
                                  ("s3", "compute", "6/3 = 2", ["s1", "s2"], "toplam süre"))},
                  "2", options=IR3["options"],
                  solution_text="İşi 6 birim kabul edelim. Ali saatte 1 birim, Veli 2 birim, birlikte 3 birim. 6/3 = 2 saat. Cevap: B",
                  notes="OKEK/birim yöntemi; kanonik olmayan yol"))

# ----------------------------------------------------------------------------- 004 sayı problemi
Q4 = "Bir sayının 3 katının 5 fazlası, aynı sayının 5 katının 7 eksiğine eşittir. Bu sayı kaçtır?"
IR4 = {"task": {"kind": "evaluate", "params": {"expr": "x"}},
       "vars": [{"name": "x", "domain": "real"}], "givens": ["3*x + 5 = 5*x - 7"],
       "unknown_of_interest": "x", "answer_shape": "scalar", "options": mc(1, 3, 6, 9, 12)}
A4 = item("tyt-prob-004", "A", "TYT", "problemler", Q4, IR4,
          {"claimed_answer": {"kind": "value", "payload": "6", "option": "C"},
           "steps": steps(("s1", "eq", "3*x + 5 = 5*x - 7", [], "denklem"),
                          ("s2", "eq", "2*x = 12", ["s1"], "düzenle"),
                          ("s3", "eq", "x = 6", ["s2"], ""))},
          "6", options=IR4["options"],
          solution_text="3x + 5 = 5x − 7 ⇒ 12 = 2x ⇒ x = 6. Cevap: C")
ITEMS.append(A4)
ITEMS.append(item("tyt-prob-021", "B", "TYT", "problemler", Q4, IR4,
                  {"claimed_answer": {"kind": "value", "payload": "6", "option": "C"},
                   "steps": steps(("s1", "case", "x = 6", [], "C şıkkını dene"),
                                  ("s2", "compute", "3*6 + 5 = 23", ["s1"], "sol taraf"),
                                  ("s3", "compute", "5*6 - 7 = 23", ["s1"], "sağ taraf"),
                                  ("s4", "note", "", ["s2", "s3"], "eşit ⇒ C"))},
                  "6", options=IR4["options"],
                  solution_text="x = 6 için 3·6 + 5 = 23 ve 5·6 − 7 = 23. Cevap: C", notes="şık deneme"))

# ----------------------------------------------------------------------------- 005 yaş
Q5 = "Bir babanın yaşı oğlunun yaşının 4 katıdır. 5 yıl sonra babanın yaşı oğlunun yaşının 3 katı olacaktır. Baba bugün kaç yaşındadır?"
IR5 = {"task": {"kind": "evaluate", "params": {"expr": "b"}},
       "vars": [{"name": "o", "domain": "positive_integer"}, {"name": "b", "domain": "positive_integer"}],
       "givens": ["b = 4*o", "b + 5 = 3*(o + 5)"], "unknown_of_interest": "b", "answer_shape": "scalar",
       "options": mc(30, 36, 40, 44, 48), "sanity": ["ans > 18"]}
A5 = item("tyt-prob-005", "A", "TYT", "problemler", Q5, IR5,
          {"claimed_answer": {"kind": "value", "payload": "40", "option": "C"},
           "steps": steps(("s1", "eq", "4*o + 5 = 3*(o + 5)", [], "b yerine 4o"),
                          ("s2", "eq", "o = 10", ["s1"], ""),
                          ("s3", "eq", "b = 40", ["s2"], "4·10"))},
          "40", options=IR5["options"],
          solution_text="Oğul o, baba 4o. 4o + 5 = 3(o + 5) ⇒ o = 10, baba 40.\nCevap: C")
ITEMS.append(A5)
ITEMS.append(item("tyt-prob-009", "B", "TYT", "problemler", Q5, IR5,
                  {"claimed_answer": {"kind": "value", "payload": "40", "option": "C"},
                   "steps": steps(("s1", "eq", "b - o = 3*o", [], "bugünkü yaş farkı"),
                                  ("s2", "eq", "b - o = 2*(o + 5)", [], "5 yıl sonraki yaş farkı"),
                                  ("s3", "eq", "3*o = 2*(o + 5)", ["s1", "s2"], "yaş farkı değişmez"),
                                  ("s4", "eq", "o = 10", ["s3"], ""),
                                  ("s5", "eq", "b = 40", ["s4"], ""))},
                  "40", options=IR5["options"],
                  solution_text="Yaş farkı sabittir. Bugün fark 3o, 5 yıl sonra fark 2(o+5). 3o = 2o + 10 ⇒ o = 10 ⇒ baba 40. Cevap: C",
                  notes="yaş farkı değişmezliği; kanonik olmayan yol"))

# ----------------------------------------------------------------------------- 006 hız
Q6 = "Bir araç 240 km'lik bir yolu saatte 80 km hızla gidip aynı yolu saatte 60 km hızla geri dönmüştür. Gidiş-dönüş toplam kaç saat sürmüştür?"
IR6 = {"task": {"kind": "evaluate", "params": {"expr": "240/80 + 240/60"}}, "vars": [], "givens": [],
       "answer_shape": "scalar", "options": mc(6, 7, 8, 9, 10), "units": "saat"}
A6 = item("tyt-prob-006", "A", "TYT", "problemler", Q6, IR6,
          {"claimed_answer": {"kind": "value", "payload": "7", "option": "B"},
           "steps": steps(("s1", "compute", "240/80 = 3", [], "gidiş"),
                          ("s2", "compute", "240/60 = 4", [], "dönüş"),
                          ("s3", "compute", "3 + 4 = 7", ["s1", "s2"], ""))},
          "7", options=IR6["options"], solution_text="Gidiş 240/80 = 3 saat, dönüş 240/60 = 4 saat, toplam 7 saat. Cevap: B")
ITEMS.append(A6)
ITEMS.append(item("tyt-prob-010", "B", "TYT", "problemler", Q6, IR6,
                  {"claimed_answer": {"kind": "value", "payload": "7", "option": "B"},
                   "steps": steps(("s1", "compute", "2*80*60/(80 + 60) = 480/7", [], "ortalama hız (harmonik)"),
                                  ("s2", "compute", "480/(480/7) = 7", ["s1"], "toplam yol / ortalama hız"))},
                  "7", options=IR6["options"],
                  solution_text="Ortalama hız = 2·80·60/(80+60) = 480/7 km/sa. Toplam yol 480 km ⇒ 480/(480/7) = 7 saat. Cevap: B",
                  notes="harmonik ortalama; kanonik olmayan yol"))

# ----------------------------------------------------------------------------- 007 kâr
Q7 = "Bir satıcı bir malı %20 kârla 360 TL'ye satmıştır. Satıcı bu malı kaç TL'ye almıştır?"
IR7 = {"task": {"kind": "evaluate", "params": {"expr": "x"}}, "vars": [{"name": "x", "domain": "positive_real"}],
       "givens": ["x*(1 + 20/100) = 360"], "unknown_of_interest": "x", "answer_shape": "scalar",
       "options": mc(288, 296, 300, 320, 340), "units": "TL"}
A7 = item("tyt-prob-007", "A", "TYT", "problemler", Q7, IR7,
          {"claimed_answer": {"kind": "value", "payload": "300", "option": "C"},
           "steps": steps(("s1", "eq", "x*120/100 = 360", [], "%20 kâr"),
                          ("s2", "eq", "x = 300", ["s1"], ""))},
          "300", options=IR7["options"], solution_text="Alış x ise 1,2x = 360 ⇒ x = 300. Cevap: C")
ITEMS.append(A7)
ITEMS.append(item("tyt-prob-011", "B", "TYT", "problemler", Q7, IR7,
                  {"claimed_answer": {"kind": "value", "payload": "300", "option": "C"},
                   "steps": steps(("s1", "note", "", [], "360 TL, alış fiyatının %120'sidir"),
                                  ("s2", "compute", "360*5/6 = 300", [], "%100 = 360·(100/120)"))},
                  "300", options=IR7["options"],
                  solution_text="360 TL alışın %120'si; %100'ü 360·5/6 = 300 TL. Cevap: C", notes="oran yolu"))

# ----------------------------------------------------------------------------- C cells (mutations)
ITEMS.append(mutate(A1, "tyt-prob-012", mutation="wrong_option",
                    claimed={"kind": "value", "payload": "16", "option": "D"},
                    steps_=A1["solution"]["steps"] + steps(("s5", "conclude", "", ["s4"], "D şıkkı")),
                    first_bad_step=5, notes="doğru değer, yanlış şık işaretlendi",
                    solution_text="… a = 16.\nCevap: D"))
ITEMS.append(mutate(A1, "tyt-prob-013", mutation="arithmetic_slip",
                    claimed={"kind": "value", "payload": "14", "option": "B"},
                    steps_=steps(("s1", "eq", "b = 30 - a", [], ""),
                                 ("s2", "eq", "2*a + 4*(30 - a) = 88", ["s1"], ""),
                                 ("s3", "eq", "-2*a + 120 = 88", ["s2"], ""),
                                 ("s4", "eq", "a = 14", ["s3"], "−2a = −28 (aritmetik hata)")),
                    first_bad_step=4, solution_text="… −2a + 120 = 88 ⇒ −2a = −28 ⇒ a = 14.\nCevap: B"))
ITEMS.append(mutate(A3, "tyt-prob-014", mutation="wrong_formula",
                    claimed={"kind": "value", "payload": "3", "option": "C"},
                    steps_=steps(("s1", "eq", "t = 6 - 3", [], "süre farkı (yanlış model)"),
                                 ("s2", "eq", "t = 3", ["s1"], "")),
                    first_bad_step=1, solution_text="Birlikte 6 − 3 = 3 saatte bitirirler. Cevap: C"))
ITEMS.append(mutate(A4, "tyt-prob-015", mutation="sign_flip",
                    claimed={"kind": "value", "payload": "1", "option": "A"},
                    steps_=steps(("s1", "eq", "3*x + 5 = 5*x - 7", [], ""),
                                 ("s2", "eq", "2*x = 2", ["s1"], "işaret hatası: 7 − 5"),
                                 ("s3", "eq", "x = 1", ["s2"], "")),
                    first_bad_step=2, solution_text="3x + 5 = 5x − 7 ⇒ 2x = 2 ⇒ x = 1. Cevap: A"))
ITEMS.append(mutate(A5, "tyt-prob-016", mutation="wrong_formula",
                    claimed={"kind": "value", "payload": "30", "option": "A"},
                    steps_=steps(("s1", "eq", "4*o + 5 = 3*(o + 5)", [], ""),
                                 ("s2", "eq", "o = 10", ["s1"], ""),
                                 ("s3", "eq", "b = 3*10", ["s2"], "yanlış çarpan (bugünkü kat 4)")),
                    first_bad_step=3, solution_text="o = 10 ⇒ baba 3·10 = 30. Cevap: A"))
ITEMS.append(mutate(A7, "tyt-prob-017", mutation="unit_error",
                    claimed={"kind": "value", "payload": "288", "option": "A"},
                    steps_=steps(("s1", "eq", "x = 360*(1 - 20/100)", [], "satıştan %20 düş (yanlış)"),
                                 ("s2", "eq", "x = 288", ["s1"], "")),
                    first_bad_step=1, solution_text="Alış = 360 − %20 = 288 TL. Cevap: A"))

# ----------------------------------------------------------------------------- D cells (right answer, invalid step)
ITEMS.append(mutate(A1, "tyt-prob-018", mutation="wrong_identity", cell="D",
                    claimed={"kind": "value", "payload": "16", "option": "C"},
                    steps_=steps(("s1", "eq", "a - b = 2", [], "iki denklemi taraf tarafa çıkardım (geçersiz çıkarım)"),
                                 ("s2", "eq", "2*a = 32", ["s1"], "a + b = 30 ile topla"),
                                 ("s3", "eq", "a = 16", ["s2"], "")),
                    first_bad_step=1,
                    notes="s1 doğru ama gerekçesiz (taraf tarafa çıkarma a − b = 2 vermez); deterministik reddedici için beklenen: kaçırılır",
                    solution_text="Denklemleri çıkarınca a − b = 2; toplayınca 2a = 32, a = 16. Cevap: C"))
ITEMS.append(mutate(A3, "tyt-prob-019", mutation="arithmetic_slip", cell="D",
                    claimed={"kind": "value", "payload": "2", "option": "B"},
                    steps_=steps(("s1", "compute", "1/6 + 1/3 = 3/9", [], "paydaları topladım (yanlış)"),
                                 ("s2", "eq", "t = 2", ["s1"], "6/3 (ikinci hata ilkini götürüyor)")),
                    first_bad_step=1, solution_text="1/6 + 1/3 = 3/9; t = 6/3 = 2. Cevap: B"))
ITEMS.append(mutate(A6, "tyt-prob-020", mutation="arithmetic_slip", cell="D",
                    claimed={"kind": "value", "payload": "7", "option": "B"},
                    steps_=steps(("s1", "compute", "240/80 = 4", [], "yanlış bölme"),
                                 ("s2", "compute", "240/60 = 3", [], "yanlış bölme"),
                                 ("s3", "compute", "4 + 3 = 7", ["s1", "s2"], "")),
                    first_bad_step=1, solution_text="240/80 = 4, 240/60 = 3, toplam 7. Cevap: B"))
