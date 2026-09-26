from common import *
if __name__ == "__main__":
    run("smoke_solve", ir("solve_equation", {"var": "x"}, givens=["x**2 - 5*x + 6 = 0"]), sol("set", "{2, 3}"), True)
    run("smoke_solve_missing", ir("solve_equation", {"var": "x"}, givens=["x**2 - 5*x + 6 = 0"]), sol("set", "{2}"), False)
    summary()
