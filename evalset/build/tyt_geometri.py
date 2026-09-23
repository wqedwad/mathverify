"""TYT — sentetik geometri (üçgen, dörtgen); nümerik realizasyon motoruyla doğrulanır."""
from common import item, mutate, steps, mc

ITEMS = []


def geo(points, constraints, target, options):
    return {"task": {"kind": "synthetic_geometry", "params": {"points": points, "constraints": constraints, "target": target}},
            "vars": [], "givens": [], "answer_shape": "scalar", "options": options}


# ----------------------------------------------------------------------------- 001 dik üçgen hipotenüs
Q1 = "ABC dik üçgeninde m(∠B) = 90°, |AB| = 6 cm ve |BC| = 8 cm'dir. |AC| kaç cm'dir?"
IR1 = geo(["A", "B", "C"], ["dist(A,B) = 6", "dist(B,C) = 8", "angle(A,B,C) = 90"], "dist(A,C)", mc(8, 9, 10, 12, 14))
A1 = item("tyt-geo-001", "A", "TYT", "geometri", Q1, IR1,
          {"claimed_answer": {"kind": "value", "payload": "10", "option": "C"},
           "steps": steps(("s1", "compute", "6**2 + 8**2 = 100", [], "Pisagor"),
                          ("s2", "compute", "sqrt(100) = 10", ["s1"], ""))},
          "10", options=IR1["options"], solution_text="Pisagor: |AC|² = 36 + 64 = 100 ⇒ |AC| = 10. Cevap: C")
ITEMS.append(A1)
ITEMS.append(item("tyt-geo-007", "B", "TYT", "geometri", Q1, IR1,
                  {"claimed_answer": {"kind": "value", "payload": "10", "option": "C"},
                   "steps": steps(("s1", "note", "", [], "6-8-10, 3-4-5 üçgeninin 2 katı"),
                                  ("s2", "compute", "2*5 = 10", ["s1"], ""))},
                  "10", options=IR1["options"], solution_text="3-4-5 özel üçgeninin iki katı: hipotenüs 10. Cevap: C",
                  notes="özel üçgen tanıma; Pisagor yazılmadı"))

# ----------------------------------------------------------------------------- 002 ikizkenar taban açısı
Q2 = "ABC üçgeninde |AB| = |AC| ve m(∠A) = 40°'dir. m(∠B) kaç derecedir?"
IR2 = geo(["A", "B", "C"], ["dist(A,B)**2 = dist(A,C)**2", "angle(B,A,C) = 40"], "angle(A,B,C)", mc(40, 50, 60, 70, 80))
A2 = item("tyt-geo-002", "A", "TYT", "geometri", Q2, IR2,
          {"claimed_answer": {"kind": "value", "payload": "70", "option": "D"},
           "steps": steps(("s1", "note", "", [], "ikizkenar: taban açıları eşit"),
                          ("s2", "compute", "(180 - 40)/2 = 70", ["s1"], ""))},
          "70", options=IR2["options"], solution_text="Taban açıları eşit: (180 − 40)/2 = 70. Cevap: D")
ITEMS.append(A2)
ITEMS.append(item("tyt-geo-008", "B", "TYT", "geometri", Q2, IR2,
                  {"claimed_answer": {"kind": "value", "payload": "70", "option": "D"},
                   "steps": steps(("s1", "note", "", [], "A'daki dış açı 140°, taban açılarının toplamına eşit"),
                                  ("s2", "compute", "180 - 40 = 140", [], ""),
                                  ("s3", "compute", "140/2 = 70", ["s1", "s2"], ""))},
                  "70", options=IR2["options"], solution_text="Dış açı 140° = 2·m(B) ⇒ 70. Cevap: D", notes="dış açı yolu"))

# ----------------------------------------------------------------------------- 003 dikdörtgen köşegeni
Q3 = "ABCD dikdörtgeninde |AB| = 12 cm ve |BC| = 5 cm'dir. |AC| köşegeni kaç cm'dir?"
IR3 = geo(["A", "B", "C", "D"], ["dist(A,B) = 12", "dist(B,C) = 5", "perpendicular(A,B,B,C)", "parallel(A,B,D,C)",
                                 "parallel(B,C,A,D)"], "dist(A,C)", mc(11, 12, 13, 15, 17))
A3 = item("tyt-geo-003", "A", "TYT", "geometri", Q3, IR3,
          {"claimed_answer": {"kind": "value", "payload": "13", "option": "C"},
           "steps": steps(("s1", "compute", "12**2 + 5**2 = 169", [], "ABC dik üçgeni"),
                          ("s2", "compute", "sqrt(169) = 13", ["s1"], ""))},
          "13", options=IR3["options"], solution_text="Köşegen dik üçgenin hipotenüsü: √(144 + 25) = 13. Cevap: C")
ITEMS.append(A3)
ITEMS.append(item("tyt-geo-009", "B", "TYT", "geometri", Q3, IR3,
                  {"claimed_answer": {"kind": "value", "payload": "13", "option": "C"},
                   "steps": steps(("s1", "note", "", [], "5-12-13 Pisagor üçlüsü"))},
                  "13", options=IR3["options"], solution_text="5-12-13 üçlüsü. Cevap: C", notes="üçlü tanıma"))

# ----------------------------------------------------------------------------- 004 ikizkenar yükseklik
Q4 = "ABC üçgeninde |AB| = |AC| = 10 cm, |BC| = 12 cm ve D noktası [BC]'nin orta noktasıdır. |AD| kaç cm'dir?"
IR4 = geo(["A", "B", "C", "D"], ["dist(A,B) = 10", "dist(A,C) = 10", "dist(B,C) = 12", "midpoint(D, B, C)"],
          "dist(A,D)", mc(6, 7, 8, 9, 10))
A4 = item("tyt-geo-004", "A", "TYT", "geometri", Q4, IR4,
          {"claimed_answer": {"kind": "value", "payload": "8", "option": "C"},
           "steps": steps(("s1", "note", "", [], "ikizkenarda kenarortay yüksekliktir; |BD| = 6"),
                          ("s2", "compute", "sqrt(10**2 - 6**2) = 8", ["s1"], "ABD dik üçgeni"))},
          "8", options=IR4["options"], solution_text="|BD| = 6, ABD dik: √(100 − 36) = 8. Cevap: C")
ITEMS.append(A4)
ITEMS.append(item("tyt-geo-010", "B", "TYT", "geometri", Q4, IR4,
                  {"claimed_answer": {"kind": "value", "payload": "8", "option": "C"},
                   "steps": steps(("s1", "note", "", [], "Heron: s = 16, Alan = √(16·6·6·4) = 48"),
                                  ("s2", "compute", "sqrt(16*6*6*4) = 48", [], ""),
                                  ("s3", "compute", "2*48/12 = 8", ["s2"], "Alan = |BC|·|AD|/2"))},
                  "8", options=IR4["options"], solution_text="Heron ile alan 48; 48 = 12·|AD|/2 ⇒ |AD| = 8. Cevap: C",
                  notes="alan üzerinden; kanonik olmayan yol"))

# ----------------------------------------------------------------------------- 005 alan
Q5 = "Dik kenarları 6 cm ve 8 cm olan dik üçgenin alanı kaç cm²'dir?"
IR5 = geo(["A", "B", "C"], ["dist(A,B) = 6", "dist(B,C) = 8", "angle(A,B,C) = 90"], "area(A,B,C)", mc(12, 20, 24, 30, 48))
A5 = item("tyt-geo-005", "A", "TYT", "geometri", Q5, IR5,
          {"claimed_answer": {"kind": "value", "payload": "24", "option": "C"},
           "steps": steps(("s1", "compute", "6*8/2 = 24", [], ""))},
          "24", options=IR5["options"], solution_text="Alan = 6·8/2 = 24. Cevap: C")
ITEMS.append(A5)
ITEMS.append(item("tyt-geo-011", "B", "TYT", "geometri", Q5, IR5,
                  {"claimed_answer": {"kind": "value", "payload": "24", "option": "C"},
                   "steps": steps(("s1", "note", "", [], "hipotenüs 10; Heron: s = 12"),
                                  ("s2", "compute", "sqrt(12*6*4*2) = 24", ["s1"], ""))},
                  "24", options=IR5["options"], solution_text="Heron: √(12·6·4·2) = 24. Cevap: C", notes="Heron"))

# ----------------------------------------------------------------------------- 006 iç açılar
Q6 = "ABC üçgeninde m(∠A) = 50° ve m(∠B) = 60°'dir. m(∠C) kaç derecedir?"
IR6 = geo(["A", "B", "C"], ["angle(B,A,C) = 50", "angle(A,B,C) = 60"], "angle(A,C,B)", mc(60, 65, 70, 75, 80))
A6 = item("tyt-geo-006", "A", "TYT", "geometri", Q6, IR6,
          {"claimed_answer": {"kind": "value", "payload": "70", "option": "C"},
           "steps": steps(("s1", "compute", "180 - 50 - 60 = 70", [], "iç açılar toplamı"))},
          "70", options=IR6["options"], solution_text="180 − 50 − 60 = 70. Cevap: C")
ITEMS.append(A6)

# ----------------------------------------------------------------------------- C cells
ITEMS.append(mutate(A1, "tyt-geo-012", mutation="wrong_formula",
                    claimed={"kind": "value", "payload": "14", "option": "E"},
                    steps_=steps(("s1", "compute", "6 + 8 = 14", [], "kenarlar toplandı")),
                    first_bad_step=1, solution_text="|AC| = 6 + 8 = 14. Cevap: E"))
ITEMS.append(mutate(A2, "tyt-geo-013", mutation="wrong_formula",
                    claimed={"kind": "value", "payload": "40", "option": "A"},
                    steps_=steps(("s1", "note", "", [], "ikizkenar üçgende tüm açılar eşit sanıldı")),
                    first_bad_step=1, solution_text="Taban açısı 40°. Cevap: A"))
ITEMS.append(mutate(A3, "tyt-geo-014", mutation="wrong_formula",
                    claimed={"kind": "value", "payload": "17", "option": "E"},
                    steps_=steps(("s1", "compute", "12 + 5 = 17", [], "")),
                    first_bad_step=1, solution_text="Köşegen 12 + 5 = 17. Cevap: E"))
ITEMS.append(mutate(A4, "tyt-geo-015", mutation="arithmetic_slip",
                    claimed={"kind": "value", "payload": "6", "option": "A"},
                    steps_=steps(("s1", "note", "", [], "|BD| = 6"),
                                 ("s2", "compute", "sqrt(10**2 - 8**2) = 6", ["s1"], "yanlış kenar kullanıldı")),
                    first_bad_step=2, solution_text="√(100 − 64) = 6. Cevap: A"))
ITEMS.append(mutate(A5, "tyt-geo-016", mutation="wrong_formula",
                    claimed={"kind": "value", "payload": "48", "option": "E"},
                    steps_=steps(("s1", "compute", "6*8 = 48", [], "ikiye bölünmedi"),
                                 ("s2", "conclude", "", ["s1"], "")),
                    first_bad_step=2, solution_text="Alan = 6·8 = 48. Cevap: E"))
ITEMS.append(mutate(A6, "tyt-geo-017", mutation="arithmetic_slip",
                    claimed={"kind": "value", "payload": "60", "option": "A"},
                    steps_=steps(("s1", "compute", "180 - 50 - 60 = 60", [], "aritmetik hata")),
                    first_bad_step=1, solution_text="180 − 110 = 60. Cevap: A"))

# ----------------------------------------------------------------------------- D cells
ITEMS.append(mutate(A1, "tyt-geo-018", mutation="arithmetic_slip", cell="D",
                    claimed={"kind": "value", "payload": "10", "option": "C"},
                    steps_=steps(("s1", "compute", "6**2 + 8**2 = 90", [], "yanlış toplam"),
                                 ("s2", "compute", "sqrt(90) = 10", ["s1"], "yanlış kök; sonuç doğru")),
                    first_bad_step=1, solution_text="36 + 64 = 90, √90 = 10. Cevap: C"))
ITEMS.append(mutate(A5, "tyt-geo-019", mutation="arithmetic_slip", cell="D",
                    claimed={"kind": "value", "payload": "24", "option": "C"},
                    steps_=steps(("s1", "compute", "6*8 = 24", [], "çarpım yanlış; /2 unutuldu; hatalar götürdü"),
                                 ("s2", "conclude", "", ["s1"], "")),
                    first_bad_step=1, solution_text="6·8 = 24. Cevap: C"))
ITEMS.append(mutate(A6, "tyt-geo-020", mutation="arithmetic_slip", cell="D",
                    claimed={"kind": "value", "payload": "70", "option": "C"},
                    steps_=steps(("s1", "compute", "50 + 60 = 120", [], "yanlış toplama"),
                                 ("s2", "compute", "180 - 120 = 70", ["s1"], "yanlış çıkarma; sonuç doğru")),
                    first_bad_step=1, solution_text="50 + 60 = 120, 180 − 120 = 70. Cevap: C"))
