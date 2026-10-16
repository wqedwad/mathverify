"""Round 6 of d4e (16 Oct 2026): the textbook derivatives round 4 lost (the attack on round 4, its coverage lens:
`d4/saldiri/d4e4/ret-kapsama`, kept here as k3..k6, k18 with their helper pc.py) and the controls of the reading that
restores them: a zero of a root's base that is no point of the comparison region (off f's domain, or an end of it) is
no kink. Each case is (label, ir, solution, accepted verdicts, accepted step statuses); see ../sonda.py, group O."""
import importlib

OK = {"CORRECT"}
NOTOK = {"INCORRECT", "UNKNOWN"}
NOTNO = {"CORRECT", "UNKNOWN"}
UNK = {"UNKNOWN"}
X = {"name": "x", "domain": "real"}

# CORRECT on a0a0829 (before round 4) and true: CORRECT again (measured, r6/out/k6_a0a0829.txt)
RESTORED = {"S1", "S2", "S4", "O1", "O2", "O3", "O8", "L1", "L2", "L4", "L6", "L9", "L10", "N1", "N2", "N5", "N12", "V1",
            "V2", "V3", "V6"}
# CORRECT before and after (controls), or gained by round 4
KEPT = {"S9", "S11", "S12", "S14", "O10", "L3", "L5", "L8", "N11", "V4", "V5", "V8"}


def _expect(label):
    key = label.split()[0]
    if "[false]" in label:
        return NOTOK
    if key in RESTORED or key in KEPT:
        return OK
    return NOTNO


def _der(f, order=None, vars_=None):
    p = {"f": f, "var": "x"}
    if order:
        p["order"] = order
    return {"task": {"kind": "derivative", "params": p}, "vars": list(vars_ or [X]), "givens": [],
            "answer_shape": "expression"}


def _sol(p):
    return {"claimed_answer": {"kind": "expression", "payload": p}, "steps": []}


def controls():
    """The kinks inside f's domain still read as before; the ends and the points off it are no kinks."""
    out = []
    out.append(("C1 |sin x|' = cos x sign(sin x): a value at the corners k*pi (convention)", _der("Abs(sin(x))"),
                _sol("cos(x)*sign(sin(x))"), UNK, None))
    out.append(("C2 |sin x|' = cos x sin x/|sin x| [true]", _der("Abs(sin(x))"), _sol("cos(x)*sin(x)/Abs(sin(x))"), OK,
                None))
    out.append(("C3 (sin x)**(3/2)' = 3 sqrt(sin x) cos x/2: a value at the ends [true]", _der("sin(x)**(3/2)"),
                _sol("3*sqrt(sin(x))*cos(x)/2"), OK, None))
    out.append(("C4 (sqrt(sin x))' + 0/(x - pi): no value at the end pi [true]", _der("sqrt(sin(x))"),
                _sol("cos(x)/(2*sqrt(sin(x))) + 0/(x - pi)"), OK, None))
    out.append(("C5 (log sqrt(sin x))' = cot x/2 + 0*log(-sin x): no value anywhere on the domain",
                _der("log(sqrt(sin(x)))"), _sol("cot(x)/2 + 0*log(-sin(x))"), NOTOK, None))
    out.append(("C6 (x sqrt(sin x))' wrong on the domain", _der("x*sqrt(sin(x))"),
                _sol("sqrt(sin(x)) + x*cos(x)/sqrt(sin(x))"), NOTOK, None))
    out.append(("C7 (sqrt(1 + sin x))' [true, touching zeros in the domain: corners]", _der("sqrt(1 + sin(x))"),
                _sol("cos(x)/(2*sqrt(1 + sin(x)))"), OK, None))
    out.append(("C8 (sqrt(1 + sin x))' with a value at the corners (convention)", _der("sqrt(1 + sin(x))"),
                _sol("cos(x)/(2*sqrt(1 + sin(x)) + 1 - sign(1 + sin(x)))"), NOTOK, None))
    out.append(("C9 (sqrt(sin(x)**2*(x - cos x)))' : touching family n*pi, n >= 1 (no claim value there)",
                _der("x**2 + 0*sqrt(sin(x)**2*(x - cos(x)))"), _sol("2*x + 0*cot(x)"), NOTOK, None))
    out.append(("C10 (sqrt(cos x))'' wrong sign [false]", _der("sqrt(cos(x))", 2),
                _sol("sqrt(cos(x))/2 - sin(x)**2/(4*cos(x)**(3/2))"), NOTOK, None))
    return out


def cases():
    out = []
    for m in ("k3", "k4", "k5", "k6", "k18"):
        for label, q, s in importlib.import_module(m).CASES:
            out.append((f"{m}: {label}", q, s, _expect(label), None))
    return out + controls()
