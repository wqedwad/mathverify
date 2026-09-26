from h import *
if __name__ == "__main__":
    H = ir("equation_of", {"object": "line_points", "p1": [0, 2], "p2": [5, 2]}, answer_shape="equation")
    run("h_y3_27", H, sol("y**3 = 27", "equation"), "INCORRECT", show=True)
    run("h_y2_9", H, sol("y**2 = 9", "equation"), "INCORRECT")
    run("h_expy", H, sol("exp(y) = 1", "equation"), "INCORRECT")
    run("h_sqrt", H, sol("sqrt(y) = 3", "equation"), "INCORRECT")
    run("h_yx0", H, sol("y**2 + 0*x = 4", "equation"), "INCORRECT")
    # tangent to circle centre (0,0) at (0,5): y = 5
    T = ir("equation_of", {"object": "tangent_to_circle_at_point", "center": [0, 0], "point": [0, 5]}, answer_shape="equation")
    run("tan_ok", T, sol("y = 5", "equation"), "CORRECT")
    run("tan_wrong_nonlin", T, sol("y**3 = 1", "equation"), "INCORRECT", show=True)
    # line point slope 0
    S0 = ir("equation_of", {"object": "line_point_slope", "p": [3, 4], "slope": 0}, answer_shape="equation")
    run("s0_ok", S0, sol("y = 4", "equation"), "CORRECT")
    run("s0_wrong_sq", S0, sol("y**2 = 25", "equation"), "INCORRECT")
    # perpendicular bisector of (0,0),(4,0): x = 2 (vertical) -- check vertical with y-factor
    PB = ir("equation_of", {"object": "perpendicular_bisector", "p1": [0, 0], "p2": [4, 0]}, answer_shape="equation")
    run("pb_ok", PB, sol("x = 2", "equation"), "CORRECT")
    run("pb_times_y", PB, sol("(x - 2)*(y - 1) = 0", "equation"), "INCORRECT", show=True)
    run("pb_x2", PB, sol("x**2 = 4", "equation"), "INCORRECT")
    # perpendicular bisector of (0,0),(0,4): y = 2 horizontal
    PB2 = ir("equation_of", {"object": "perpendicular_bisector", "p1": [0, 0], "p2": [0, 4]}, answer_shape="equation")
    run("pb2_ok", PB2, sol("y = 2", "equation"), "CORRECT")
    run("pb2_wrong", PB2, sol("y**2 = 1", "equation"), "INCORRECT")
    # parallel through point to y = 3: horizontal
    PP = ir("equation_of", {"object": "line_point_parallel", "p": [1, -1], "line": "y = 3"}, answer_shape="equation")
    run("pp_ok", PP, sol("y = -1", "equation"), "CORRECT")
    run("pp_wrong", PP, sol("(y - 3)**2 = 0", "equation"), "INCORRECT")
