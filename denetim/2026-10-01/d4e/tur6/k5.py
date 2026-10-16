import sys
from pc import *

E = "expression"
CASES = [
    ("L1 (log sqrt(sin x))' = cot(x)/2 [true]", der("log(sqrt(sin(x)))"), sol("cot(x)/2", E)),
    ("L2 (log sqrt(cos x))' = -tan(x)/2 [true]", der("log(sqrt(cos(x)))"), sol("-tan(x)/2", E)),
    ("L3 (log sqrt(x))'' = -1/(2x^2) [true]", der("log(sqrt(x))", order=2), sol("-1/(2*x**2)", E)),
    ("L4 (log sqrt(cos x))'' = -1/(2cos^2 x) [true]", der("log(sqrt(cos(x)))", order=2), sol("-1/(2*cos(x)**2)", E)),
    ("L5 (log sqrt(1-x^2))'' [true]", der("log(sqrt(1 - x**2))", order=2), sol("-(1 + x**2)/(1 - x**2)**2", E)),
    ("L6 (log sqrt(tan x))' = 1/sin(2x) [true]", der("log(sqrt(tan(x)))"), sol("1/sin(2*x)", E)),
    ("L7 (log sqrt(sin x))'' wrong [false]", der("log(sqrt(sin(x)))", order=2), sol("-1/sin(x)**2", E)),
    ("L8 (1/sqrt(sin x))'' [true]", der("1/sqrt(sin(x))", order=2), sol("1/(2*sqrt(sin(x))) + 3*cos(x)**2/(4*sin(x)**(5/2))", E)),
    ("L9 (sqrt(sin x)+log(sin x))'' [true]", der("sqrt(sin(x)) + log(sin(x))", order=2), sol("-sqrt(sin(x))/2 - cos(x)**2/(4*sin(x)**(3/2)) - 1/sin(x)**2", E)),
    ("L10 (x sqrt(cos x))'' [true]", der("x*sqrt(cos(x))", order=2), sol("-sin(x)/sqrt(cos(x)) - x*sqrt(cos(x))/2 - x*sin(x)**2/(4*cos(x)**(3/2))", E)),
]

if __name__ == "__main__":
    run(CASES, sys.argv[0], sys.argv[1:])
