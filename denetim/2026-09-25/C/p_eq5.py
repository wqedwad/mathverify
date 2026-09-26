from h import *
if __name__ == "__main__":
    L = ir("equation_of", {"object": "line_points", "p1": [0, 1], "p2": [1, 3]}, answer_shape="equation")
    for i, c in enumerate(["Abs(2*x - y + 1) + Abs(y - 3) = 0", "(2*x - y + 1)**2 + (y - 3)**2 = 0",
                           "(2*x - y + 1)*(y**2 - 9) = 0", "(2*x - y + 1)/(y - 3) = 0", "(2*x - y + 1)*sqrt(y) = 0",
                           "(2*x - y + 1)*(y - 3)**2 = 0", "(2*x - y + 1)*exp(y) = 0", "(2*x - y + 1)*sin(y) = 0",
                           "(2*x - y + 1)*floor(y) = 0", "2*x - y + 1 + 0*y**2 = 0", "y = 2*x + 1 + x**2 - x**2",
                           "(y - 2*x - 1)*(x**2 + y**2 + 1) = 0", "y*(2*x - y + 1) = 0", "(2*x - y + 1)*Abs(y - 3) = 0",
                           "x*(2*x - y + 1) = 0", "(2*x-y+1)*(2*x-y+2) = 0"]):
        r = run(f"lf_{i}", L, sol(c, "equation"), None)
        print("     claim:", c)
