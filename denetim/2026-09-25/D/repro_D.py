import os, sys; sys.path.insert(0, os.environ.get("MV_SRC", str(__import__("pathlib").Path(__file__).resolve().parents[3] / "src")))
from mathverify.verifier import verify

def v(ir, sol):
    r = verify(ir, sol)
    return f"{r.verdict} {r.confidence} flags={r.flags}"

IR1 = {"task":{"kind":"evaluate","params":{"expr":"a"}},"vars":[{"name":"a","domain":"positive_integer"},{"name":"b","domain":"positive_integer"}],
       "givens":["a + b = 30","2*a + 4*b = 88"],"answer_shape":"scalar"}
if __name__ == "__main__":
    print("F1 control      ", v(IR1, {"claimed_answer":{"kind":"value","payload":"16"},"steps":[{"id":"s1","kind":"eq","claim":"a = 20","from":[]}]}))
    print("F1 null claim   ", v(IR1, {"claimed_answer":{"kind":"value","payload":"16"},"steps":[{"id":"s1","kind":"eq","claim":"a = 20","from":[]},{"id":"s2","kind":"eq","claim":None,"from":[]}]}))
    print("F1 from=5       ", v(IR1, {"claimed_answer":{"kind":"value","payload":"16"},"steps":[{"id":"s1","kind":"eq","claim":"a = 20","from":[]},{"id":"s2","kind":"note","claim":"x","from":5}]}))
    print("F2 and          ", v(IR1, {"claimed_answer":{"kind":"value","payload":"16"},"steps":[{"id":"s1","kind":"eq","claim":"a = 20 and a = 16","from":[]}]}))
    IRe = {"task":{"kind":"evaluate","params":{"expr":"x"}},"vars":[{"name":"x"}],"givens":["2*x = 7"],"answer_shape":"scalar"}
    print("F2 value '0 or 7/2'", v(IRe, {"claimed_answer":{"kind":"value","payload":"0 or 7/2"},"steps":[]}))
    IRc = {"task":{"kind":"count_integers","params":{"var":"x"}},"vars":[{"name":"x","domain":"integer"}],"givens":["Abs(x - 3) < 2"],"answer_shape":"count"}
    print("F3 count '3'       ", v(IRc, {"claimed_answer":{"kind":"count","payload":"3"},"steps":[]}))
    print("F3 count len('abc')", v(IRc, {"claimed_answer":{"kind":"count","payload":"len('abc')"},"steps":[]}))   # harmless builtin call
    print("F3 count ceiling   ", v(IRc, {"claimed_answer":{"kind":"count","payload":"ceiling(5/2)"},"steps":[]}))
    print("F3 count '3 or 4'  ", v(IRc, {"claimed_answer":{"kind":"count","payload":"3 or 4"},"steps":[]}))
    IRs = {"task":{"kind":"solve_equation","params":{"var":"x"}},"vars":[{"name":"x"}],"givens":["x**2 - 5*x + 6 = 0"],"answer_shape":"set"}
    print("F5 {x}             ", v(IRs, {"claimed_answer":{"kind":"set","payload":"{x}"},"steps":[]}))
    print("F5 x               ", v(IRs, {"claimed_answer":{"kind":"set","payload":"x"},"steps":[]}))
    print("F6 '3,5'           ", v(IRe, {"claimed_answer":{"kind":"value","payload":"3,5"},"steps":[]}))
    IRm = {"task":{"kind":"evaluate","params":{"expr":"x"}},"vars":[{"name":"x"}],"givens":["2*x = 7"],"answer_shape":"scalar","options":{"A":"3","B":"7/2","C":"4","D":"2","E":"1"}}
    for opt in ["B", "(B)", "B)", "B şıkkı", "b", "B, C", "F", "A"]:
        print(f"MC option {opt!r:10}", v(IRm, {"claimed_answer":{"kind":"value","payload":"7/2","option":opt},"steps":[]}))
    from mathverify.equiv import exact_integer
    for p in ["3", "__import__('os').getpid()*0+3", "3 or 4", "ceiling(5/2)", "7/2", "3.0", 3, True]:
        print("exact_integer", repr(p), "->", repr(exact_integer(p)))
