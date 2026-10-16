import sys
from ortak import *

TT = {"name": "t", "domain": "real"}
AP = {"name": "a", "domain": "positive_real"}
NP = {"name": "n", "domain": "positive_integer"}


def cases():
    out = []
    forms = {  # diverge for some allowed value
        "P1 t^-a (a<=1 diverges)": ("Integral(t**(-a), (t, 1, oo))", [AP, TT]),
        "P2 t^(-2/a) (a>=2 diverges)": ("Integral(t**(-2/a), (t, 1, oo))", [AP, TT]),
        "P3 1/(t^a + 1) (a<=1)": ("Integral(1/(t**a + 1), (t, 1, oo))", [AP, TT]),
        "P4 exp(-t/a)*t^a ctrl converges": ("Integral(exp(-t/a)*t**a, (t, 1, oo))", [AP, TT]),
        "P5 t^(n - 3) (n>=2 diverges)": ("Integral(t**(n - 3), (t, 1, oo))", [NP, TT]),
        "P6 1/t^(1/n) (all n diverge)": ("Integral(t**(-1/n), (t, 1, oo))", [NP, TT]),
        "P7 0+ t^(-a) (a>=1 diverges)": ("Integral(t**(-a), (t, 0, 1))", [AP, TT]),
        "P8 0+ log(t)^n/t... t^(a-2) (a<=1)": ("Integral(t**(a - 2), (t, 0, 1))", [AP, TT]),
        "P9 1/(a*t^2 + (1-a)*t)  [a=... ]": ("Integral(1/(t**2 + (a - 1)**2*t**3 + t), (t, 1, oo))", [AP, TT]),
        "P10 a/(t^(a+1/2))": ("Integral(t**(-a - S(1)/2), (t, 1, oo))", [AP, TT]),
    }
    for k, (I, vs) in forms.items():
        exp = {"CORRECT", "UNKNOWN"} if "ctrl" in k or k.startswith("P9") else NOTOK
        out.append((f"PW evaluate 0*[{k}] + 1: 1", ev1(f"0*{I} + 1", vars_=vs), sol("1"), exp, None))
    return out


if __name__ == "__main__":
    sys.exit(0 if run(cases(), sys.argv[1]) == 0 else 0)
