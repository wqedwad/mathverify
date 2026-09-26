from common import *
import sympy as sp
from p04_solveeq import se
from p05_ineq import si

if __name__ == "__main__":
    # identities (infinitely many solutions) — claim {} must not be CORRECT
    se("(x + 1)**2 = x**2 + 2*x + 1", "{}", False, name="identity sq {}")
    se("(x**2 - 1)/(x - 1) = x + 1", "{}", False, name="identity rational {}")
    se("2*(x + 3) = 2*x + 6", "{}", False, name="identity linear {}")
    se("2*(x + 3) = 2*x + 6", "Reals", True, kind="set", name="identity linear R")
    se("2*(x + 3) = 2*x + 6", "(-oo, oo)", True, kind="interval", name="identity linear (-oo,oo)")
    se("2*(x + 3) = 2*x + 5", "{}", True, name="contradiction linear {}")
    se("x**2 - (x - 1)*(x + 1) = 1", "{}", False, name="identity x2-(x-1)(x+1)=1 {}")
    # irrational roots at exact zero of radicand
    se("sqrt(x**2 - 2*x - 1) = 0", "{1 - sqrt(2), 1 + sqrt(2)}", True, name="sqrt radicand zero")
    se("sqrt(x**2 - 2*x - 1) = 0", "{}", False, name="sqrt radicand zero {}")
    se("sqrt(x**2 - 4*x - 1) = 0", "{2 - sqrt(5), 2 + sqrt(5)}", True, name="sqrt radicand zero 2")
    se("sqrt(x**2 - 2*x - 2) + x = 1 + sqrt(3)", "{1 + sqrt(3)}", True, name="sqrt radicand zero 3")
    se("x*sqrt(x**2 - 2*x - 1) = 0", "{1 - sqrt(2), 1 + sqrt(2)}", True, name="x*sqrt radicand zero")
    # log arg exactly zero at an irrational candidate (should be excluded)
    se("(x - 1 - sqrt(3))*log(x**2 - 2*x - 2) = 0", "{-1, 3, 1 + sqrt(3)}", False, name="log arg zero extraneous")
    se("(x - 1 - sqrt(3))*log(x**2 - 2*x - 2) = 0", "{-1, 3}", True, name="log arg zero correct")
    se("(x - 1 - sqrt(3))/sqrt(x**2 - 2*x - 2) = 0", "{1 + sqrt(3)}", False, name="1/sqrt zero extraneous")
    se("(x - 1 - sqrt(3))/sqrt(x**2 - 2*x - 2) = 0", "{}", True, name="1/sqrt zero correct")
    # cube roots of negatives (real cube root in school math)
    se("cbrt(x) = -2", "{-8}", True, name="cbrt(x)=-2")
    se("x**(1/3) = -2", "{-8}", True, name="x**(1/3)=-2")
    se("cbrt(x - 1) = -1", "{0}", True, name="cbrt(x-1)=-1")
    se("x**3 = -8", "{-2}", True, name="x^3=-8")
    # inequalities with irrational endpoints that are exact zeros
    si("x**2 - 2*x - 1 <= 0", "[1 - sqrt(2), 1 + sqrt(2)]", True, name="ineq le irr")
    si("x**2 - 2*x - 1 > 0", "(-oo, 1 - sqrt(2)) U (1 + sqrt(2), oo)", True, name="ineq gt irr")
    si("x**2 - 2*x - 1 >= 0", "(-oo, 1 - sqrt(2)] U [1 + sqrt(2), oo)", True, name="ineq ge irr")
    si("x**2 - x - 1 < 0", "((1 - sqrt(5))/2, (1 + sqrt(5))/2)", True, name="golden lt")
    si("x**2 - 4*x - 1 < 0", "(2 - sqrt(5), 2 + sqrt(5))", True, name="2+-sqrt5 lt")
    si("x**2 + 2*x - 2 < 0", "(-1 - sqrt(3), -1 + sqrt(3))", True, name="-1+-sqrt3 lt")
    si("x**4 - 10*x**2 + 1 < 0", "(-sqrt(2) - sqrt(3), -sqrt(3) + sqrt(2)) U (sqrt(3) - sqrt(2), sqrt(2) + sqrt(3))", True, name="quartic lt")
    si("sqrt(x**2 - 2*x - 1) <= 1", "[1 - sqrt(3), 1 - sqrt(2)] U [1 + sqrt(2), 1 + sqrt(3)]", True, name="sqrt ineq irr")
    si("cbrt(x) < -1", "(-oo, -1)", True, name="cbrt ineq")
    summary()
