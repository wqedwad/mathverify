from h import *
if __name__ == "__main__":
    L = ir("equation_of", {"object": "line_points", "p1": [0, 1], "p2": [1, 3]}, answer_shape="equation")
    for c, e in [("(2*x - y + 1)/(x - 3) = 0", "INCORRECT"), ("(y - 1)/x = 2", "INCORRECT"), ("sqrt(y - 2*x) = 1", None),
                 ("(y - 1)/(x - 0) = 2", "INCORRECT"), ("y - 2*x - 1 = 0", "CORRECT"), ("2*(x + 1/2) = y", "CORRECT"),
                 ("y/2 = x + 1/2", "CORRECT"), ("x/x*(y - 2*x - 1) = 0", "INCORRECT"), ("log(y - 2*x) = 0", None)]:
        run(c, L, sol(c, "equation"), e)
    C = ir("equation_of", {"object": "circle_center_radius", "center": [0, 0], "radius": "sqrt(5)"}, answer_shape="equation")
    run("c5_ok", C, sol("x**2 + y**2 = 5", "equation"), "CORRECT")
    run("c5_wrong", C, sol("x**2 + y**2 = 6", "equation"), "INCORRECT")
    run("c5_sq", C, sol("(x**2 + y**2 - 5)**2 = 0", "equation"), "CORRECT")
    C2 = ir("equation_of", {"object": "circle_center_point", "center": [1, 1], "point": [2, 3]}, answer_shape="equation")
    run("c2_ok", C2, sol("(x-1)**2 + (y-1)**2 = 5", "equation"), "CORRECT")
    run("c2_ellipse", C2, sol("(x-1)**2 + 2*(y-1)**2 = 5", "equation"), "INCORRECT")
