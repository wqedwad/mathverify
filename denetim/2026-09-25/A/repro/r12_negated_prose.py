"""_sanitize_payload drops trailing prose tokens, including a negation: '5 değil' ('not 5') is verified as 5."""
from _r import show
if __name__ == "__main__":
    print("GT: 2 + 3 = 5; the claim '5 değil' / '5 olamaz' asserts the answer is NOT 5")
    for p in ["5 değil", "5 olamaz"]:
        show(f"claim {p!r}", {"task": {"kind": "evaluate", "params": {"expr": "2 + 3"}}, "vars": [], "givens": []},
             {"claimed_answer": {"kind": "value", "payload": p}, "steps": []}, False)
