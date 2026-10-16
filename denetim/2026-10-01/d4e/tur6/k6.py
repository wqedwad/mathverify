import sys
from pc import *

E = "expression"
CASES = [
    ("N1 (exp(sqrt(sin x)))' [true]", der("exp(sqrt(sin(x)))"), sol("exp(sqrt(sin(x)))*cos(x)/(2*sqrt(sin(x)))", E)),
    ("N2 (log sqrt(1+cos x))' = -sin x/(2(1+cos x)) [true]", der("log(sqrt(1 + cos(x)))"), sol("-sin(x)/(2*(1 + cos(x)))", E)),
    ("N3 (sqrt(1+sqrt(sin x)))' [true]", der("sqrt(1 + sqrt(sin(x)))"), sol("cos(x)/(4*sqrt(sin(x))*sqrt(1 + sqrt(sin(x))))", E)),
    ("N4 (atan(sqrt(tan x)))' [true]", der("atan(sqrt(tan(x)))"), sol("(1 + tan(x)**2)/(2*sqrt(tan(x))*(1 + tan(x)))", E)),
    ("N5 (sin(sqrt(cos x)))' [true]", der("sin(sqrt(cos(x)))"), sol("-cos(sqrt(cos(x)))*sin(x)/(2*sqrt(cos(x)))", E)),
    ("N6 (sqrt(sin x)/(1+sqrt(sin x)))' [true]", der("sqrt(sin(x))/(1 + sqrt(sin(x)))"), sol("cos(x)/(2*sqrt(sin(x))*(1 + sqrt(sin(x)))**2)", E)),
    ("N7 (log sqrt(x - cos x))' [true]", der("log(sqrt(x - cos(x)))"), sol("(1 + sin(x))/(2*(x - cos(x)))", E)),
    ("N8 (log sqrt(sin x))' wrong = cot x [false]", der("log(sqrt(sin(x)))"), sol("cot(x)", E)),
    ("N9 (log sqrt(sin x))' at pi/4 = 1/2 [true]", der("log(sqrt(sin(x)))", "pi/4"), sol("1/2")),
    ("N10 (log sqrt(sin x)) tangent at pi/2: y = -log(1)?? y=0 [true]", tan("log(sqrt(sin(x)))", "pi/2"), sol("y = 0", "equation")),
    ("N11 (sqrt(sin x)^2)' = cos x [true]", der("sqrt(sin(x))**2"), sol("cos(x)", E)),
    ("N12 (log(sin(x)**(1/2)) + x)' [true]", der("log(sin(x)**(1/2)) + x"), sol("cot(x)/2 + 1", E)),
]

if __name__ == "__main__":
    run(CASES, sys.argv[0], sys.argv[1:])
