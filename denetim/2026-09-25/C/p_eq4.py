from h import *
if __name__ == "__main__":
    V = ir("equation_of", {"object": "line_point_slope", "p": [3, 4], "slope": "oo"}, answer_shape="equation")
    run("slope_oo_x3", V, sol("x = 3", "equation"), None, show=True)
    run("slope_oo_y4", V, sol("y = 4", "equation"), "INCORRECT", show=True)
    run("slope_oo_xy", V, sol("x = y", "equation"), "INCORRECT", show=True)
    # perpendicular to vertical line x = 2 through (1, 5): y = 5
    PV = ir("equation_of", {"object": "line_point_perpendicular", "p": [1, 5], "line": "x = 2"}, answer_shape="equation")
    run("perp_vert_ok", PV, sol("y = 5", "equation"), "CORRECT")
    run("perp_vert_wrong", PV, sol("(y - 7)**3 = 0", "equation"), "INCORRECT")
    # circle diameter (0,0)-(4,0): (x-2)^2 + y^2 = 4
    D = ir("equation_of", {"object": "circle_diameter", "p1": [0, 0], "p2": [4, 0]}, answer_shape="equation")
    run("diam_ok", D, sol("x**2 - 4*x + y**2 = 0", "equation"), "CORRECT")
    run("diam_wrong", D, sol("x**2 - 4*x + y**2 = 4", "equation"), "INCORRECT")
    run("diam_x4", D, sol("x**2 - 4*x + y**2 + x**4 = 0", "equation"), "INCORRECT", show=True)
    run("diam_semi", D, sol("y = sqrt(4 - (x-2)**2)", "equation"), "INCORRECT")
    # circle claim in a line task and vice versa
    L = ir("equation_of", {"object": "line_points", "p1": [0, 1], "p2": [1, 3]}, answer_shape="equation")
    run("line_claim_circle", L, sol("x**2 + y**2 = 1", "equation"), "INCORRECT")
    C = ir("equation_of", {"object": "circle_center_radius", "center": [0, 0], "radius": 1}, answer_shape="equation")
    run("circle_claim_line", C, sol("y = x", "equation"), "INCORRECT")
    run("circle_claim_value", C, sol("1"), None, show=True)
    run("circle_claim_eq_true", C, sol("x = x", "equation"), "INCORRECT", show=True)
    # radius negative / symbolic
    Cn = ir("equation_of", {"object": "circle_center_radius", "center": [0, 0], "radius": -2}, answer_shape="equation")
    run("circle_neg_r", Cn, sol("x**2 + y**2 = 4", "equation"), None, show=True)
    # imaginary radius claims: x^2+y^2 = -4 vs truth r = 2*I
    Ci = ir("equation_of", {"object": "circle_center_radius", "center": [0, 0], "radius": "2*I"}, answer_shape="equation")
    run("circle_imag_r", Ci, sol("x**2 + y**2 = -4", "equation"), None, show=True)
    # claimed circle with r^2 negative vs real circle
    run("circle_claim_neg_r2", C, sol("x**2 + y**2 = -1", "equation"), "INCORRECT")
