"""UNI — lineer cebir: ters matris, özdeğer/özvektör, sistem çözümü, matris kuvveti, determinant."""
from common import item, mutate, steps, mc

ITEMS = []


def la(op, options=None, answer_shape="expression", **params):
    return {"task": {"kind": "linalg", "params": {"op": op, **params}}, "vars": [], "givens": [],
            "answer_shape": answer_shape, "options": options}


# ----------------------------------------------------------------------------- 001 ters matris
Q1 = "A = [[1, 2], [3, 4]] matrisinin tersi aşağıdakilerden hangisidir?"
IR1 = la("inverse", matrix="Matrix([[1,2],[3,4]])",
         options=mc("Matrix([[-2, 1], [3/2, -1/2]])", "Matrix([[4, -2], [-3, 1]])", "Matrix([[-4, 2], [3, -1]])",
                    "Matrix([[1, -2], [-3, 4]])", "Matrix([[2, -1], [-3/2, 1/2]])"))
A1 = item("uni-la-001", "A", "UNI", "lineer cebir", Q1, IR1,
          {"claimed_answer": {"kind": "expression", "payload": "Matrix([[-2, 1], [3/2, -1/2]])", "option": "A"},
           "steps": steps(("s1", "compute", "det(Matrix([[1,2],[3,4]])) = -2", [], ""),
                          ("s2", "compute", "Matrix([[4, -2], [-3, 1]])/(-2) = Matrix([[-2, 1], [3/2, -1/2]])", ["s1"], "adj/det"))},
          "Matrix([[-2, 1], [3/2, -1/2]])", options=IR1["options"], solution_text="A⁻¹ = adj(A)/det(A) = [[-2, 1], [3/2, -1/2]]. Cevap: A")
ITEMS.append(A1)
ITEMS.append(item("uni-la-006", "B", "UNI", "lineer cebir", Q1, IR1,
                  {"claimed_answer": {"kind": "expression", "payload": "Matrix([[-2, 1], [1.5, -0.5]])", "option": "A"},
                   "steps": steps(("s1", "note", "", [], "Gauss-Jordan: [A | I] → [I | A⁻¹]"),
                                  ("s2", "compute", "Matrix([[1,2],[3,4]])*Matrix([[-2, 1], [1.5, -0.5]]) = Matrix([[1,0],[0,1]])", [], "kontrol"))},
                  "Matrix([[-2, 1], [3/2, -1/2]])", options=IR1["options"],
                  solution_text="Gauss-Jordan ile [[-2, 1], [1.5, -0.5]]; A·A⁻¹ = I kontrolü. Cevap: A", notes="ondalık biçim + satır indirgeme"))

# ----------------------------------------------------------------------------- 002 özdeğerler
Q2 = "A = [[2, 1], [1, 2]] matrisinin özdeğerleri kümesi aşağıdakilerden hangisidir?"
IR2 = la("eigenvalues", matrix="Matrix([[2,1],[1,2]])", answer_shape="set",
         options=mc("{1, 3}", "{1, 2}", "{2, 3}", "{-1, 3}", "{0, 4}"))
A2 = item("uni-la-002", "A", "UNI", "lineer cebir", Q2, IR2,
          {"claimed_answer": {"kind": "set", "payload": "{1, 3}", "option": "A"},
           "steps": steps(("s1", "eq", "(2 - t)**2 - 1 = (t - 1)*(t - 3)", [], "karakteristik polinom"),
                          ("s2", "eq", "t in {1, 3}", ["s1"], ""))},
          "{1, 3}", options=IR2["options"], solution_text="(2 − λ)² − 1 = 0 ⇒ λ ∈ {1, 3}. Cevap: A")
ITEMS.append(A2)
ITEMS.append(item("uni-la-007", "B", "UNI", "lineer cebir", Q2, IR2,
                  {"claimed_answer": {"kind": "set", "payload": "{3, 1}", "option": "A"},
                   "steps": steps(("s1", "compute", "trace(Matrix([[2,1],[1,2]])) = 4", [], "λ₁ + λ₂"),
                                  ("s2", "compute", "det(Matrix([[2,1],[1,2]])) = 3", [], "λ₁λ₂"),
                                  ("s3", "note", "", ["s1", "s2"], "toplamı 4, çarpımı 3 olan sayılar: 1 ve 3"))},
                  "{1, 3}", options=IR2["options"], solution_text="İz 4, determinant 3 ⇒ {1, 3}. Cevap: A", notes="iz/determinant yolu"))

# ----------------------------------------------------------------------------- 003 özvektör (açık uçlu)
Q3 = "A = [[2, 1], [1, 2]] matrisinin λ = 3 özdeğerine karşılık gelen bir özvektörünü bulunuz."
IR3 = la("eigenvector", matrix="Matrix([[2,1],[1,2]])", eigenvalue="3", options=None)
A3 = item("uni-la-003", "A", "UNI", "lineer cebir", Q3, IR3,
          {"claimed_answer": {"kind": "expression", "payload": "(1, 1)"},
           "steps": steps(("s1", "note", "", [], "(A − 3I)v = 0 ⇒ −x + y = 0"),
                          ("s2", "compute", "Matrix([[2,1],[1,2]])*Matrix([1, 1]) = 3*Matrix([1, 1])", [], "kontrol"))},
          "(1, 1)", solution_text="(A − 3I)v = 0 ⇒ v = (1, 1). Cevap: (1, 1)")
ITEMS.append(A3)
ITEMS.append(item("uni-la-008", "B", "UNI", "lineer cebir", Q3, IR3,
                  {"claimed_answer": {"kind": "expression", "payload": "(-2, -2)"},
                   "steps": steps(("s1", "note", "", [], "özvektörler λ = 3 için x = y doğrusu; herhangi bir katı olur"),
                                  ("s2", "compute", "Matrix([[2,1],[1,2]])*Matrix([-2, -2]) = 3*Matrix([-2, -2])", [], ""))},
                  "(1, 1)", solution_text="v = (−2, −2) de bir özvektördür. Cevap: (-2, -2)",
                  notes="kanonik olmayan özvektör; herhangi sıfırdan farklı kat kabul edilmeli"))

# ----------------------------------------------------------------------------- 004 sistem
Q4 = "x + y = 30 ve 2x + 4y = 88 sistemini matris yöntemiyle çözünüz. (x, y) çifti nedir?"
IR4 = la("solve_system", A="Matrix([[1,1],[2,4]])", b="(30, 88)",
         options=mc("(16, 14)", "(14, 16)", "(18, 12)", "(12, 18)", "(20, 10)"))
A4 = item("uni-la-004", "A", "UNI", "lineer cebir", Q4, IR4,
          {"claimed_answer": {"kind": "expression", "payload": "(16, 14)", "option": "A"},
           "steps": steps(("s1", "compute", "det(Matrix([[1,1],[2,4]])) = 2", [], ""),
                          ("s2", "compute", "Matrix([[4, -1], [-2, 1]])/2*Matrix([30, 88]) = Matrix([16, 14])", ["s1"], "A⁻¹b"))},
          "(16, 14)", options=IR4["options"], solution_text="x = A⁻¹b = (16, 14). Cevap: A")
ITEMS.append(A4)
ITEMS.append(item("uni-la-009", "B", "UNI", "lineer cebir", Q4, IR4,
                  {"claimed_answer": {"kind": "expression", "payload": "(16, 14)", "option": "A"},
                   "steps": steps(("s1", "compute", "det(Matrix([[30,1],[88,4]]))/det(Matrix([[1,1],[2,4]])) = 16", [], "Cramer x"),
                                  ("s2", "compute", "det(Matrix([[1,30],[2,88]]))/det(Matrix([[1,1],[2,4]])) = 14", [], "Cramer y"))},
                  "(16, 14)", options=IR4["options"], solution_text="Cramer: x = 32/2 = 16, y = 28/2 = 14. Cevap: A", notes="Cramer kuralı"))

# ----------------------------------------------------------------------------- 005 matris kuvveti
Q5 = "A = [[1, 1], [0, 1]] olduğuna göre A³ aşağıdakilerden hangisidir?"
IR5 = la("matrix_expr", expr="Matrix([[1,1],[0,1]])**3",
         options=mc("Matrix([[1, 3], [0, 1]])", "Matrix([[1, 2], [0, 1]])", "Matrix([[3, 3], [0, 3]])",
                    "Matrix([[1, 1], [0, 1]])", "Matrix([[1, 4], [0, 1]])"))
A5 = item("uni-la-005", "A", "UNI", "lineer cebir", Q5, IR5,
          {"claimed_answer": {"kind": "expression", "payload": "Matrix([[1, 3], [0, 1]])", "option": "A"},
           "steps": steps(("s1", "compute", "Matrix([[1,1],[0,1]])**2 = Matrix([[1,2],[0,1]])", [], ""),
                          ("s2", "compute", "Matrix([[1,2],[0,1]])*Matrix([[1,1],[0,1]]) = Matrix([[1,3],[0,1]])", ["s1"], ""))},
          "Matrix([[1, 3], [0, 1]])", options=IR5["options"], solution_text="A² = [[1,2],[0,1]], A³ = [[1,3],[0,1]]. Cevap: A")
ITEMS.append(A5)
ITEMS.append(item("uni-la-010", "B", "UNI", "lineer cebir", Q5, IR5,
                  {"claimed_answer": {"kind": "expression", "payload": "Matrix([[1, 3], [0, 1]])", "option": "A"},
                   "steps": steps(("s1", "note", "", [], "A = I + N, N² = 0 ⇒ Aⁿ = I + nN"),
                                  ("s2", "compute", "Matrix([[0,1],[0,0]])**2 = Matrix([[0,0],[0,0]])", [], "N nilpotent"),
                                  ("s3", "compute", "eye(2) + 3*Matrix([[0,1],[0,0]]) = Matrix([[1,3],[0,1]])", ["s1", "s2"], ""))},
                  "Matrix([[1, 3], [0, 1]])", options=IR5["options"], solution_text="Aⁿ = I + nN ⇒ A³ = [[1,3],[0,1]]. Cevap: A",
                  notes="nilpotent ayrışım; kanonik olmayan yol"))

# ----------------------------------------------------------------------------- 006 determinant 3x3 (evaluate)
Q6 = "A = [[2, 0, 1], [1, 3, 2], [1, 1, 1]] matrisinin determinantı kaçtır?"
IR6 = {"task": {"kind": "evaluate", "params": {"expr": "det(Matrix([[2,0,1],[1,3,2],[1,1,1]]))"}}, "vars": [], "givens": [],
       "answer_shape": "scalar", "options": mc(-2, -1, 0, 1, 2)}
A6 = item("uni-la-011", "A", "UNI", "lineer cebir", Q6, IR6,
          {"claimed_answer": {"kind": "value", "payload": "0", "option": "C"},
           "steps": steps(("s1", "compute", "2*(3*1 - 2*1) = 2", [], "1. satıra göre açılım"),
                          ("s2", "compute", "1*(1*1 - 3*1) = -2", [], ""),
                          ("s3", "compute", "2 - 0 + (-2) = 0", ["s1", "s2"], ""))},
          "0", options=IR6["options"], solution_text="2(3 − 2) − 0 + 1(1 − 3) = 0. Cevap: C")
ITEMS.append(A6)

# ----------------------------------------------------------------------------- C cells
ITEMS.append(mutate(A1, "uni-la-012", mutation="wrong_formula",
                    claimed={"kind": "expression", "payload": "Matrix([[4, -2], [-3, 1]])", "option": "B"},
                    steps_=steps(("s1", "compute", "Matrix([[4, -2], [-3, 1]]) = Matrix([[4, -2], [-3, 1]])", [], "ek matris; determinanta bölünmedi"),
                                 ("s2", "conclude", "", ["s1"], "")),
                    first_bad_step=2, solution_text="A⁻¹ = adj(A) = [[4, −2], [−3, 1]]. Cevap: B"))
ITEMS.append(mutate(A2, "uni-la-013", mutation="arithmetic_slip",
                    claimed={"kind": "set", "payload": "{1, 2}", "option": "B"},
                    steps_=steps(("s1", "eq", "(2 - t)**2 - 1 = (t - 1)*(t - 2)", [], "yanlış çarpanlara ayırma")),
                    first_bad_step=1, solution_text="(t − 1)(t − 2) = 0 ⇒ {1, 2}. Cevap: B"))
ITEMS.append(mutate(A3, "uni-la-014", mutation="sign_flip",
                    claimed={"kind": "expression", "payload": "(1, -1)"},
                    steps_=steps(("s1", "note", "", [], "λ = 1'in özvektörü alındı")),
                    first_bad_step=1, solution_text="v = (1, −1). Cevap: (1, -1)"))
ITEMS.append(mutate(A4, "uni-la-015", mutation="wrong_option",
                    claimed={"kind": "expression", "payload": "(14, 16)", "option": "B"},
                    steps_=steps(("s1", "compute", "det(Matrix([[1,1],[2,4]])) = 2", [], ""),
                                 ("s2", "note", "", [], "x ve y yer değiştirildi")),
                    first_bad_step=2, solution_text="(x, y) = (14, 16). Cevap: B"))
ITEMS.append(mutate(A5, "uni-la-016", mutation="off_by_one",
                    claimed={"kind": "expression", "payload": "Matrix([[1, 2], [0, 1]])", "option": "B"},
                    steps_=steps(("s1", "compute", "Matrix([[1,1],[0,1]])**2 = Matrix([[1,2],[0,1]])", [], "A² hesaplandı, A³ sanıldı"),
                                 ("s2", "conclude", "", ["s1"], "")),
                    first_bad_step=2, solution_text="A³ = [[1,2],[0,1]]. Cevap: B"))
ITEMS.append(mutate(A6, "uni-la-017", mutation="sign_flip",
                    claimed={"kind": "value", "payload": "4", "option": "E"},
                    steps_=steps(("s1", "compute", "2*(3*1 - 2*1) = 2", [], ""),
                                 ("s2", "compute", "1*(1*1 - 3*1) = -2", [], ""),
                                 ("s3", "compute", "2 - (-2) = 4", ["s1", "s2"], "kofaktör işareti yanlış")),
                    first_bad_step=3, solution_text="2 + 2 = 4. Cevap: E"))

# ----------------------------------------------------------------------------- D cells
ITEMS.append(mutate(A4, "uni-la-018", mutation="arithmetic_slip", cell="D",
                    claimed={"kind": "expression", "payload": "(16, 14)", "option": "A"},
                    steps_=steps(("s1", "compute", "det(Matrix([[1,1],[2,4]])) = 3", [], "determinant yanlış"),
                                 ("s2", "conclude", "(16, 14)", [], "şıklardan kontrolle")),
                    first_bad_step=1, solution_text="det = 3 … (16, 14). Cevap: A"))
ITEMS.append(mutate(A6, "uni-la-019", mutation="arithmetic_slip", cell="D",
                    claimed={"kind": "value", "payload": "0", "option": "C"},
                    steps_=steps(("s1", "compute", "2*(3*1 - 2*1) = 4", [], "yanlış"),
                                 ("s2", "compute", "1*(1*1 - 3*1) = -4", [], "yanlış"),
                                 ("s3", "compute", "4 - 4 = 0", ["s1", "s2"], "hatalar birbirini götürdü")),
                    first_bad_step=1, solution_text="4 − 4 = 0. Cevap: C"))
ITEMS.append(mutate(A5, "uni-la-020", mutation="wrong_identity", cell="D",
                    claimed={"kind": "expression", "payload": "Matrix([[1, 3], [0, 1]])", "option": "A"},
                    steps_=steps(("s1", "compute", "Matrix([[1,1],[0,1]])**2 = Matrix([[1,2],[0,2]])", [], "yanlış kare"),
                                 ("s2", "conclude", "Matrix([[1, 3], [0, 1]])", [], "yine de doğru şık")),
                    first_bad_step=1, solution_text="A² = [[1,2],[0,2]] … A³ = [[1,3],[0,1]]. Cevap: A"))
