from h import *
def G(points, constraints, target):
    return ir("synthetic_geometry", {"points": points, "constraints": constraints, "target": target})
if __name__ == "__main__":
    g = G(["B","A","C","D"], ["dist(B,A) = 3", "dist(B,C) = 3", "dist(B,D) = 3", "angle(A,B,D) = 30", "angle(D,B,C) = 40"], "angle(A,B,C)")
    run("angle_add_70", g, sol("70"), "UNKNOWN", show=True)
    # segment problem: C between A and B -- no on_segment helper
    g2 = G(["A","B","C"], ["dist(A,B) = 5", "dist(A,C) = 2", "collinear(A,B,C)"], "dist(B,C)")
    run("segment_3", g2, sol("3"), None, show=True)
    # try on_segment helper
    g3 = ir("synthetic_geometry", {"points": ["A","B","C"], "constraints": ["dist(A,B) = 5", "dist(A,C) = 2", "on_segment(C,A,B)"], "target": "dist(B,C)"})
    run("on_segment", g3, sol("3"), None, show=True)
    # degenerate "triangle" 3-4-7 (collinear): area 0
    g4 = G(["A","B","C"], ["dist(A,B) = 3", "dist(B,C) = 4", "dist(A,C) = 7"], "area(A,B,C)")
    run("degenerate_area0", g4, sol("0"), None, show=True)
    # reflex: quadrilateral with interior angle > 180 cannot be expressed; angle() returns <= 180
    g5 = G(["A","B","C","D"], ["dist(A,B) = 4", "dist(B,C) = 4", "dist(C,D) = 4", "dist(D,A) = 4", "dist(A,C) = 4"], "angle(D,A,B)")
    run("rhombus_120", g5, sol("120"), "CORRECT", show=True)
