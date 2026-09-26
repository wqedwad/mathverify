from h import *
if __name__ == "__main__":
    # circle centre (1,2) radius 3: truth (x-1)^2+(y-2)^2=9
    C = ir("equation_of", {"object": "circle_center_radius", "center": [1, 2], "radius": 3}, answer_shape="equation")
    run("circ_ok", C, sol("(x-1)**2 + (y-2)**2 = 9", "equation"), "CORRECT")
    run("circ_expanded", C, sol("x**2 + y**2 - 2*x - 4*y - 4 = 0", "equation"), "CORRECT")
    run("circ_scaled", C, sol("2*x**2 + 2*y**2 - 4*x - 8*y - 8 = 0", "equation"), "CORRECT")
    run("circ_wrong_r", C, sol("(x-1)**2 + (y-2)**2 = 3", "equation"), "INCORRECT")
    # extra cubic term: not a circle
    run("circ_cubic", C, sol("(x-1)**2 + (y-2)**2 + x**3 = 9 + x**3 - x**3 + x**3", "equation"), "INCORRECT", show=True)
    run("circ_x3", C, sol("x**2 + y**2 - 2*x - 4*y - 4 + x**3 = 0", "equation"), "INCORRECT", show=True)
    run("circ_sin", C, sol("x**2 + y**2 - 2*x - 4*y - 4 + sin(x)**3 = 0", "equation"), "INCORRECT", show=True)
    run("circ_y4", C, sol("x**2 + y**2 - 2*x - 4*y - 4 + y**4 = 0", "equation"), "INCORRECT", show=True)
    run("circ_x2y2", C, sol("x**2 + y**2 - 2*x - 4*y - 4 + x**2*y**2 = 0", "equation"), "INCORRECT", show=True)
    run("circ_abs", C, sol("x**2 + y**2 - 2*x - 4*y - 4 + Abs(x*y) = 0", "equation"), "INCORRECT", show=True)
    # negative "radius^2": empty set
    C0 = ir("equation_of", {"object": "circle_center_radius", "center": [0, 0], "radius": 0}, answer_shape="equation")
    run("circ_r0_ok", C0, sol("x**2 + y**2 = 0", "equation"), "CORRECT")
    run("circ_r0_wrong", C0, sol("x**2 + y**2 = 1", "equation"), "INCORRECT")
