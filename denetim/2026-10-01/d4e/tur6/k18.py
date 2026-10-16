import sys
from pc import *

E = "expression"
CASES = [
    ("V1 (x sqrt(sin x))' [true]", der("x*sqrt(sin(x))"), sol("sqrt(sin(x)) + x*cos(x)/(2*sqrt(sin(x)))", E)),
    ("V2 (tan x sqrt(sin x))' [true]", der("tan(x)*sqrt(sin(x))"), sol("sqrt(sin(x))/cos(x)**2 + sin(x)/(2*sqrt(sin(x)))", E)),
    ("V3 ((1 - cos x) sqrt(sin x))' [true]", der("(1 - cos(x))*sqrt(sin(x))"), sol("sin(x)*sqrt(sin(x)) + (1 - cos(x))*cos(x)/(2*sqrt(sin(x)))", E)),
    ("V4 (x^2 sqrt(cos x))' [true]", der("x**2*sqrt(cos(x))"), sol("2*x*sqrt(cos(x)) - x**2*sin(x)/(2*sqrt(cos(x)))", E)),
    ("V5 (sin x sqrt(cos x))' [true, ctrl g!=0]", der("sin(x)*sqrt(cos(x))"), sol("cos(x)*sqrt(cos(x)) - sin(x)**2/(2*sqrt(cos(x)))", E)),
    ("V6 (sqrt(sin x)/x)' [true]", der("sqrt(sin(x))/x"), sol("cos(x)/(2*x*sqrt(sin(x))) - sqrt(sin(x))/x**2", E)),
    ("V7 (x sqrt(sin x))' wrong [false]", der("x*sqrt(sin(x))"), sol("sqrt(sin(x)) + x*cos(x)/sqrt(sin(x))", E)),
    ("V8 (e^x sqrt(cos x))' [true, ctrl]", der("exp(x)*sqrt(cos(x))"), sol("exp(x)*sqrt(cos(x)) - exp(x)*sin(x)/(2*sqrt(cos(x)))", E)),
]

if __name__ == "__main__":
    run(CASES, sys.argv[0], sys.argv[1:])
