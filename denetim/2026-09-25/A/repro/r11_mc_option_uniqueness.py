"""evaluate + options: z3 'exactly one option is satisfiable' certifies a value the givens do not determine."""
from _r import show
if __name__ == "__main__":
    sols = [(a, b) for a in range(1, 42) for b in range(1, 42) if 3*a + 5*b == 41]
    print("GT: positive integer solutions of 3a+5b=41:", sols, "-> a+b in", sorted({a + b for a, b in sols}), "(not determined)")
    ir = {"task": {"kind": "evaluate", "params": {"expr": "a + b"}}, "vars": [{"name": "a", "domain": "positive_integer"}, {"name": "b", "domain": "positive_integer"}],
          "givens": ["3*a + 5*b = 41"], "options": {"A": "9", "B": "10", "C": "12"}}
    show("a+b = 9 (option A)", ir, {"claimed_answer": {"kind": "value", "payload": "9", "option": "A"}, "steps": []}, False)
