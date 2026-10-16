import sys
from pc import *

E = "expression"
CASES = [
    ("S1 (sqrt(sin x))'' textbook [true]", der("sqrt(sin(x))", order=2), sol("-sqrt(sin(x))/2 - cos(x)**2/(4*sin(x)**(3/2))", E)),
    ("S2 (sqrt(cos x))'' textbook [true]", der("sqrt(cos(x))", order=2), sol("-sqrt(cos(x))/2 - sin(x)**2/(4*cos(x)**(3/2))", E)),
    ("S3 (sqrt(sin x))'' wrong [false]", der("sqrt(sin(x))", order=2), sol("-sqrt(sin(x))/2", E)),
    ("S4 (sqrt(tan x))'' textbook [true]", der("sqrt(tan(x))", order=2), sol("(2*tan(x)*(tan(x)**2 + 1))/(2*sqrt(tan(x))) - (tan(x)**2 + 1)**2/(4*tan(x)**(3/2))", E)),
    ("S5 (sqrt(1 - cos x))'' ", der("sqrt(1 - cos(x))", order=2), sol("cos(x)/(2*sqrt(1 - cos(x))) - sin(x)**2/(4*(1 - cos(x))**(3/2))", E)),
    ("S6 (x^3 + sin x)^(1/2)' textbook [true]", der("sqrt(x**3 + sin(x))"), sol("(3*x**2 + cos(x))/(2*sqrt(x**3 + sin(x)))", E)),
    ("S7 (x^3 + sin x)^(1/2)' wrong [false]", der("sqrt(x**3 + sin(x))"), sol("(3*x**2 + cos(x))/sqrt(x**3 + sin(x))", E)),
    ("S8 sqrt(x - cos x)' wrong [false]", der("sqrt(x - cos(x))"), sol("(1 + sin(x))/sqrt(x - cos(x))", E)),
    ("S9 sqrt(x^2 - cos x)' textbook [true]", der("sqrt(x**2 - cos(x))"), sol("(2*x + sin(x))/(2*sqrt(x**2 - cos(x)))", E)),
    ("S10 sqrt(x^2 - cos x)' wrong [false]", der("sqrt(x**2 - cos(x))"), sol("(2*x + sin(x))/sqrt(x**2 - cos(x))", E)),
    ("S11 (sqrt(1-x^2))'' textbook [true]", der("sqrt(1 - x**2)", order=2), sol("-1/(1 - x**2)**(3/2)", E)),
    ("S12 (x sqrt(x))'' ", der("x*sqrt(x)", order=2), sol("3/(4*sqrt(x))", E)),
    ("S13 (sqrt(sin x))' wrong [false]", der("sqrt(sin(x))"), sol("cos(x)/sqrt(sin(x))", E)),
    ("S14 (sqrt(1+sin x))' textbook [true]", der("sqrt(1 + sin(x))"), sol("cos(x)/(2*sqrt(1 + sin(x)))", E)),
    ("S15 (sqrt(1+sin x))' wrong [false]", der("sqrt(1 + sin(x))"), sol("cos(x)/sqrt(1 + sin(x))", E)),
    ("S16 (|sin x|)'' = -|sin x| [true]", der("Abs(sin(x))", order=2), sol("-Abs(sin(x))", E)),
    ("S17 (sin x |sin x|)'' ", der("sin(x)*Abs(sin(x))", order=2), sol("2*cos(2*x)*Abs(sin(x))/sin(x)", E)),
]

if __name__ == "__main__":
    run(CASES, sys.argv[0], sys.argv[1:])
