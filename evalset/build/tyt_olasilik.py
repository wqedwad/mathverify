"""TYT — permütasyon / kombinasyon / olasılık; tüketici sayım ile doğrulanır."""
from common import item, mutate, steps, mc

ITEMS = []
DICE = [1, 2, 3, 4, 5, 6]


def prob(space, event, options):
    return {"task": {"kind": "probability", "params": {"space": space, "event": event}}, "vars": [], "givens": [],
            "answer_shape": "scalar", "options": options, "sanity": ["ans >= 0", "ans <= 1"]}


def cnt(space, predicate, options):
    return {"task": {"kind": "count_structures", "params": {"space": space, "predicate": predicate}}, "vars": [],
            "givens": [], "answer_shape": "count", "options": options}


# ----------------------------------------------------------------------------- 001 iki zar toplam 7
Q1 = "İki zar birlikte atılıyor. Üst yüze gelen sayıların toplamının 7 olma olasılığı kaçtır?"
IR1 = prob({"structure": "product", "sets": [DICE, DICE]}, "sum(t) == 7", mc("1/12", "1/9", "1/6", "5/36", "1/4"))
A1 = item("tyt-ola-001", "A", "TYT", "olasılık", Q1, IR1,
          {"claimed_answer": {"kind": "value", "payload": "1/6", "option": "C"},
           "steps": steps(("s1", "compute", "6*6 = 36", [], "örnek uzay"),
                          ("s2", "note", "", [], "toplamı 7 olan çiftler: (1,6),(2,5),(3,4),(4,3),(5,2),(6,1)"),
                          ("s3", "compute", "6/36 = 1/6", ["s1", "s2"], ""))},
          "1/6", options=IR1["options"], solution_text="36 durumdan 6'sı ⇒ 6/36 = 1/6. Cevap: C")
ITEMS.append(A1)
ITEMS.append(item("tyt-ola-007", "B", "TYT", "olasılık", Q1, IR1,
                  {"claimed_answer": {"kind": "value", "payload": "1/6", "option": "C"},
                   "steps": steps(("s1", "note", "", [], "ilk zar ne gelirse gelsin ikinci zar için tam bir tamamlayıcı değer vardır"),
                                  ("s2", "compute", "1/6 = 1/6", ["s1"], "ikinci zarın o değeri getirme olasılığı"))},
                  "1/6", options=IR1["options"],
                  solution_text="İlk zar ne olursa olsun ikinci zarın tamamlayıcısı tek: olasılık 1/6. Cevap: C",
                  notes="simetri argümanı; sayım yapılmadı"))

# ----------------------------------------------------------------------------- 002 sıraya dizme
Q2 = "5 kişi yan yana bir sıraya kaç farklı şekilde dizilebilir?"
IR2 = cnt({"structure": "arrangement_all", "n": 5}, "", mc(24, 60, 100, 120, 125))
A2 = item("tyt-ola-002", "A", "TYT", "olasılık", Q2, IR2,
          {"claimed_answer": {"kind": "count", "payload": 120, "option": "D"},
           "steps": steps(("s1", "compute", "factorial(5) = 120", [], "5!"))},
          "120", options=IR2["options"], solution_text="5! = 120. Cevap: D")
ITEMS.append(A2)
ITEMS.append(item("tyt-ola-008", "B", "TYT", "olasılık", Q2, IR2,
                  {"claimed_answer": {"kind": "count", "payload": 120, "option": "D"},
                   "steps": steps(("s1", "note", "", [], "ilk koltuk 5, ikinci 4, … seçenek"),
                                  ("s2", "compute", "5*4*3*2*1 = 120", ["s1"], "çarpma ilkesi"))},
                  "120", options=IR2["options"], solution_text="5·4·3·2·1 = 120. Cevap: D", notes="çarpma ilkesi"))

# ----------------------------------------------------------------------------- 003 komite
Q3 = "6 kişilik bir gruptan 3 kişilik bir komite kaç farklı şekilde seçilebilir?"
IR3 = cnt({"structure": "combination", "n": 6, "k": 3}, "", mc(15, 18, 20, 30, 120))
A3 = item("tyt-ola-003", "A", "TYT", "olasılık", Q3, IR3,
          {"claimed_answer": {"kind": "count", "payload": 20, "option": "C"},
           "steps": steps(("s1", "compute", "binomial(6, 3) = 20", [], "C(6,3)"))},
          "20", options=IR3["options"], solution_text="C(6,3) = 20. Cevap: C")
ITEMS.append(A3)
ITEMS.append(item("tyt-ola-009", "B", "TYT", "olasılık", Q3, IR3,
                  {"claimed_answer": {"kind": "count", "payload": 20, "option": "C"},
                   "steps": steps(("s1", "compute", "binomial(5, 2) + binomial(5, 3) = 20", [], "Pascal özdeşliği"))},
                  "20", options=IR3["options"], solution_text="Pascal: C(5,2) + C(5,3) = 10 + 10 = 20. Cevap: C",
                  notes="Pascal özdeşliği"))

# ----------------------------------------------------------------------------- 004 üç basamaklı sayı
Q4 = "{1, 2, 3, 4, 5} rakamlarıyla rakamları birbirinden farklı üç basamaklı kaç sayı yazılabilir?"
IR4 = cnt({"structure": "permutation", "elements": [1, 2, 3, 4, 5], "k": 3}, "", mc(10, 30, 60, 100, 125))
A4 = item("tyt-ola-004", "A", "TYT", "olasılık", Q4, IR4,
          {"claimed_answer": {"kind": "count", "payload": 60, "option": "C"},
           "steps": steps(("s1", "compute", "5*4*3 = 60", [], "P(5,3)"))},
          "60", options=IR4["options"], solution_text="P(5,3) = 5·4·3 = 60. Cevap: C")
ITEMS.append(A4)
ITEMS.append(item("tyt-ola-010", "B", "TYT", "olasılık", Q4, IR4,
                  {"claimed_answer": {"kind": "count", "payload": 60, "option": "C"},
                   "steps": steps(("s1", "compute", "binomial(5, 3) = 10", [], "rakam kümesi seçimi"),
                                  ("s2", "compute", "factorial(3) = 6", [], "her küme için sıralama"),
                                  ("s3", "compute", "10*6 = 60", ["s1", "s2"], ""))},
                  "60", options=IR4["options"], solution_text="C(5,3)·3! = 10·6 = 60. Cevap: C", notes="kombinasyon·sıralama"))

# ----------------------------------------------------------------------------- 005 torba
Q5 = "Bir torbada 3 kırmızı ve 2 mavi top vardır. Aynı anda çekilen 2 topun ikisinin de kırmızı olma olasılığı kaçtır?"
IR5 = prob({"structure": "combination", "elements": ["k1", "k2", "k3", "m1", "m2"], "k": 2},
           "all(x[0] == 'k' for x in t)", mc("1/5", "3/10", "9/25", "1/2", "3/5"))
A5 = item("tyt-ola-005", "A", "TYT", "olasılık", Q5, IR5,
          {"claimed_answer": {"kind": "value", "payload": "3/10", "option": "B"},
           "steps": steps(("s1", "compute", "binomial(3, 2) = 3", [], "iki kırmızı seçimi"),
                          ("s2", "compute", "binomial(5, 2) = 10", [], "tüm seçimler"),
                          ("s3", "compute", "3/10 = 3/10", ["s1", "s2"], ""))},
          "3/10", options=IR5["options"], solution_text="C(3,2)/C(5,2) = 3/10. Cevap: B")
ITEMS.append(A5)
ITEMS.append(item("tyt-ola-011", "B", "TYT", "olasılık", Q5, IR5,
                  {"claimed_answer": {"kind": "value", "payload": "3/10", "option": "B"},
                   "steps": steps(("s1", "compute", "(3/5)*(2/4) = 3/10", [], "ardışık çekim: iadesiz"))},
                  "3/10", options=IR5["options"], solution_text="Ardışık: (3/5)·(2/4) = 3/10. Cevap: B", notes="ardışık çekim"))

# ----------------------------------------------------------------------------- 006 madeni para
Q6 = "Bir madeni para 3 kez atılıyor. En az 2 kez tura gelme olasılığı kaçtır?"
IR6 = prob({"structure": "sequence", "elements": ["T", "Y"], "k": 3}, "t.count('T') >= 2", mc("1/8", "3/8", "1/2", "5/8", "7/8"))
A6 = item("tyt-ola-006", "A", "TYT", "olasılık", Q6, IR6,
          {"claimed_answer": {"kind": "value", "payload": "1/2", "option": "C"},
           "steps": steps(("s1", "compute", "binomial(3, 2) + binomial(3, 3) = 4", [], "2 veya 3 tura"),
                          ("s2", "compute", "4/8 = 1/2", ["s1"], ""))},
          "1/2", options=IR6["options"], solution_text="(C(3,2) + C(3,3))/8 = 4/8 = 1/2. Cevap: C")
ITEMS.append(A6)

# ----------------------------------------------------------------------------- C cells
ITEMS.append(mutate(A1, "tyt-ola-012", mutation="missing_case",
                    claimed={"kind": "value", "payload": "1/12", "option": "A"},
                    steps_=steps(("s1", "note", "", [], "(1,6),(2,5),(3,4) — sıralı çiftler tek sayıldı"),
                                 ("s2", "compute", "3/36 = 1/12", ["s1"], "")),
                    first_bad_step=1, solution_text="3 çift ⇒ 3/36 = 1/12. Cevap: A"))
ITEMS.append(mutate(A2, "tyt-ola-013", mutation="wrong_formula",
                    claimed={"kind": "count", "payload": 25, "option": "E"},
                    steps_=steps(("s1", "compute", "5*5 = 25", [], "her koltuk için 5 seçenek (tekrar)")),
                    first_bad_step=1, solution_text="5·5 = 25. Cevap: E"))
ITEMS.append(mutate(A3, "tyt-ola-014", mutation="wrong_formula",
                    claimed={"kind": "count", "payload": 120, "option": "E"},
                    steps_=steps(("s1", "compute", "6*5*4 = 120", [], "sıra önemliymiş gibi (permütasyon)")),
                    first_bad_step=1, solution_text="6·5·4 = 120. Cevap: E"))
ITEMS.append(mutate(A4, "tyt-ola-015", mutation="wrong_formula",
                    claimed={"kind": "count", "payload": 125, "option": "E"},
                    steps_=steps(("s1", "compute", "5**3 = 125", [], "rakam tekrarı yasağı unutuldu")),
                    first_bad_step=1, solution_text="5³ = 125. Cevap: E"))
ITEMS.append(mutate(A5, "tyt-ola-016", mutation="wrong_formula",
                    claimed={"kind": "value", "payload": "9/25", "option": "C"},
                    steps_=steps(("s1", "compute", "(3/5)*(3/5) = 9/25", [], "iadeli çekim gibi hesaplandı")),
                    first_bad_step=1, solution_text="(3/5)·(3/5) = 9/25. Cevap: C"))
ITEMS.append(mutate(A6, "tyt-ola-017", mutation="missing_case",
                    claimed={"kind": "value", "payload": "3/8", "option": "B"},
                    steps_=steps(("s1", "compute", "binomial(3, 2)/8 = 3/8", [], "tam 2 tura alındı, 3 tura unutuldu")),
                    first_bad_step=1, solution_text="C(3,2)/8 = 3/8. Cevap: B"))

# ----------------------------------------------------------------------------- D cells
ITEMS.append(mutate(A2, "tyt-ola-018", mutation="arithmetic_slip", cell="D",
                    claimed={"kind": "count", "payload": 120, "option": "D"},
                    steps_=steps(("s1", "compute", "factorial(4) = 120", [], "4! yazıldı; değeri de yanlış")),
                    first_bad_step=1, solution_text="4! = 120. Cevap: D"))
ITEMS.append(mutate(A3, "tyt-ola-019", mutation="arithmetic_slip", cell="D",
                    claimed={"kind": "count", "payload": 20, "option": "C"},
                    steps_=steps(("s1", "compute", "6*5*4 = 20", [], "permütasyon yazıldı, sonuç kombinasyon çıktı")),
                    first_bad_step=1, solution_text="6·5·4 = 20. Cevap: C"))
ITEMS.append(mutate(A1, "tyt-ola-020", mutation="arithmetic_slip", cell="D",
                    claimed={"kind": "value", "payload": "1/6", "option": "C"},
                    steps_=steps(("s1", "compute", "6*6 = 36", [], ""),
                                 ("s2", "note", "", [], "toplamı 7 olan 5 durum"),
                                 ("s3", "compute", "5/36 = 1/6", ["s1", "s2"], "yanlış sadeleştirme; sonuç doğru")),
                    first_bad_step=3, solution_text="5/36 = 1/6. Cevap: C"))
