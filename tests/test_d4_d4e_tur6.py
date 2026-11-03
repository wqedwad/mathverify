"""Fourth audit, part d4e, round 6 (16 Oct 2026): the textbook derivatives round 4 lost. Read as kinks, the families of
zeros of a root's base that are no part of the comparison region (off f's domain: log(sqrt(sin(x))) at k*pi; or its
ends: sqrt(sin(x)) at k*pi, where sin(x) changes sign) left them undecided; a finite zero off the region's interior was
skipped already. Each assertion below failed on 7993139 (d315974 merged with wip/birlesik-a) unless marked a control."""
import sympy as sp

from mathverify.verifier import verify

X = {"name": "x", "domain": "real"}
E = "expression"


def _v(f, claim, order=None):
    p = {"f": f, "var": "x"}
    if order:
        p["order"] = order
    q = {"task": {"kind": "derivative", "params": p}, "vars": [X], "givens": [], "answer_shape": "expression"}
    return verify(q, {"claimed_answer": {"kind": E, "payload": claim}, "steps": []}).verdict


def test_textbook_root_derivatives_restored():
    assert _v("log(sqrt(sin(x)))", "cot(x)/2") == "CORRECT"                      # zeros off the domain
    assert _v("log(sqrt(cos(x)))", "-tan(x)/2") == "CORRECT"
    assert _v("log(sqrt(1 + cos(x)))", "-sin(x)/(2*(1 + cos(x)))") == "CORRECT"
    assert _v("x*sqrt(sin(x))", "sqrt(sin(x)) + x*cos(x)/(2*sqrt(sin(x)))") == "CORRECT"   # zeros at the ends
    assert _v("exp(sqrt(sin(x)))", "exp(sqrt(sin(x)))*cos(x)/(2*sqrt(sin(x)))") == "CORRECT"
    assert _v("sin(sqrt(cos(x)))", "-cos(sqrt(cos(x)))*sin(x)/(2*sqrt(cos(x)))") == "CORRECT"
    assert _v("sqrt(sin(x))", "-sqrt(sin(x))/2 - cos(x)**2/(4*sin(x)**(3/2))", 2) == "CORRECT"
    assert _v("log(sqrt(sin(x)))", "-1/(2*sin(x)**2)", 2) == "CORRECT"
    # controls: wrong claims, a value at the ends, the corners inside the domain, a touching family
    assert _v("x*sqrt(sin(x))", "sqrt(sin(x)) + x*cos(x)/sqrt(sin(x))") == "INCORRECT"
    assert _v("log(sqrt(sin(x)))", "cot(x)") == "INCORRECT"
    assert _v("sin(x)**(3/2)", "3*sqrt(sin(x))*cos(x)/2") == "CORRECT"
    assert _v("Abs(sin(x))", "cos(x)*sign(sin(x))") == "UNKNOWN"
    assert _v("sqrt(1 + sin(x))", "cos(x)/(2*sqrt(1 + sin(x)))") == "CORRECT"
    assert _v("sqrt(1 + sin(x))", "cos(x)/(2*sqrt(1 + sin(x)) + 1 - sign(1 + sin(x)))") != "CORRECT"
    assert _v("x**2 + 0*sqrt(sin(x)**2*(x - cos(x)))", "2*x + 0*cot(x)") != "CORRECT"


def test_family_off_the_comparison_region_is_no_kink():
    from mathverify.certify import calculus as C
    x = sp.Symbol("x", real=True)
    g = sp.sin(x)
    f = x * sp.sqrt(g)
    common = (x, 1, sp.S.Reals, sp.sqrt(g) + x * sp.cos(x) / (2 * sp.sqrt(g)), [sp.Ne(sp.sqrt(g), 0)], set(), [g >= 0])
    off = C.kink_reading(f, *common, loose=[g >= 0])
    assert off["families"] == [] and not off["reasons"]
    kept = C.kink_reading(f, *common)                                  # control: the region's conditions not given
    assert kept["families"] and "kink_undecided" in kept["reasons"]
    # control: a touching family stays (sin(x)**2*(x - cos(x)) >= 0 at n*pi, g' = 0 there)
    h = sp.sin(x) ** 2 * (x - sp.cos(x))
    touch = C.kink_reading(sp.sqrt(h), x, 1, sp.S.Reals, sp.S.Zero, [], set(), [h >= 0], loose=[h >= 0])
    assert touch["families"]
