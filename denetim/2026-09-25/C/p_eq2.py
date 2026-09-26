from h import *
if __name__ == "__main__":
    # line through (0,1) and (1,3): y = 2x + 1
    L = ir("equation_of", {"object": "line_points", "p1": [0, 1], "p2": [1, 3]}, answer_shape="equation")
    run("line_ok", L, sol("y = 2*x + 1", "equation"), "CORRECT")
    run("line_scaled", L, sol("4*x - 2*y + 2 = 0", "equation"), "CORRECT")
    run("line_solved_x", L, sol("x = (y - 1)/2", "equation"), "CORRECT")
    run("line_wrong", L, sol("y = 2*x - 1", "equation"), "INCORRECT")
    # nonlinear claim with same zero set in x for generic y: (2x-y+1)*(y-5)=0 is line U horizontal line
    run("line_times_y5", L, sol("(2*x - y + 1)*(y - 5) = 0", "equation"), "INCORRECT", show=True)
    run("line_div_x3", L, sol("(2*x - y + 1)/(x - 3) = 0", "equation"), "INCORRECT", show=True)
    run("line_sq", L, sol("(2*x - y + 1)**2 = 0", "equation"), "CORRECT", show=True)
    run("two_lines", L, sol("y**2 = (2*x + 1)**2", "equation"), "INCORRECT", show=True)
    run("line_abs", L, sol("y = Abs(2*x + 1)", "equation"), "INCORRECT", show=True)
    run("line_times_x2p1", L, sol("(2*x - y + 1)*(x**2 + 1) = 0", "equation"), "CORRECT", show=True)
    run("line_or_point", L, sol("(2*x - y + 1)*((x-7)**2 + (y-7)**2) = 0", "equation"), "INCORRECT", show=True)
    run("line_sqrt", L, sol("sqrt(y - 2*x) = 1", "equation"), "CORRECT", show=True)
    run("line_exp", L, sol("exp(y) = exp(2*x + 1)", "equation"), "CORRECT", show=True)
    run("line_log_restricted", L, sol("log(y) = log(2*x + 1)", "equation"), "INCORRECT", show=True)
    # horizontal truth
    H = ir("equation_of", {"object": "line_points", "p1": [0, 2], "p2": [5, 2]}, answer_shape="equation")
    run("h_ok", H, sol("y = 2", "equation"), "CORRECT")
    run("h_sq", H, sol("y**2 = 4", "equation"), "INCORRECT", show=True)
    run("h_cube", H, sol("(y-2)**3 = 0", "equation"), "CORRECT", show=True)
    run("h_other", H, sol("(y-2)*(y-3) = 0", "equation"), "INCORRECT", show=True)
    run("h_x_factor", H, sol("x*(y-2) = 0", "equation"), "INCORRECT", show=True)
