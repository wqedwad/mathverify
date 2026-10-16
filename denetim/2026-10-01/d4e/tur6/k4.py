import sys
from pc import *

E = "expression"
CASES = [
    ("O1 (sin(x)^(3/2))'' textbook [true]", der("sin(x)**(3/2)", order=2), sol("3*cos(x)**2/(4*sqrt(sin(x))) - 3*sin(x)**(3/2)/2", E)),
    ("O2 (sqrt(sin 2x))'' textbook [true]", der("sqrt(sin(2*x))", order=2), sol("-2*sqrt(sin(2*x)) - cos(2*x)**2/sin(2*x)**(3/2)", E)),
    ("O3 (x + sqrt(sin x))'' textbook [true]", der("x + sqrt(sin(x))", order=2), sol("-sqrt(sin(x))/2 - cos(x)**2/(4*sin(x)**(3/2))", E)),
    ("O4 (sqrt(sin x))''' [true]", der("sqrt(sin(x))", order=3), sol("diff(sqrt(sin(x)), x, 3)", E)),
    ("O5 (sqrt(sin x))'' at pi/2 = -1/2 [true]", der("sqrt(sin(x))", "pi/2", order=2), sol("-1/2")),
    ("O6 (sqrt(cos x))'' wrong sign [false]", der("sqrt(cos(x))", order=2), sol("sqrt(cos(x))/2 - sin(x)**2/(4*cos(x)**(3/2))", E)),
    ("O7 (sqrt(1+cos x))'' [corner fam]", der("sqrt(1 + cos(x))", order=2), sol("-cos(x)/(2*sqrt(1 + cos(x))) - sin(x)**2/(4*(1 + cos(x))**(3/2))", E)),
    ("O8 (log(sqrt(sin x)))'' = -1/(2 sin^2 x) [true, no root]", der("log(sqrt(sin(x)))", order=2), sol("-1/(2*sin(x)**2)", E)),
    ("O9 (sqrt(sin x) cos x)'' ", der("sqrt(sin(x))*cos(x)", order=2), sol("diff(sqrt(sin(x))*cos(x), x, 2)", E)),
    ("O10 (sqrt(x))'' x>0 decl ctrl", der("sqrt(x)", order=2, vars_=[XP]), sol("-1/(4*x**(3/2))", E)),
]

if __name__ == "__main__":
    run(CASES, sys.argv[0], sys.argv[1:])
