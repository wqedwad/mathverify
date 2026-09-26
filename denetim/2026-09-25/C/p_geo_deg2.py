# tyt-geo-002 with the options written as in the exam booklet ("70°"); isosceles AB=AC, angle A = 40 -> angle B = 70
from h import *
if __name__ == "__main__":
    opts = {"A": "40°", "B": "50°", "C": "60°", "D": "70°", "E": "80°"}
    g = ir("synthetic_geometry", {"points": ["A", "B", "C"], "constraints": ["dist(A,B)**2 = dist(A,C)**2", "angle(B,A,C) = 40°"], "target": "angle(A,B,C)"}, options=opts)
    print("ground truth: (180 - 40)/2 =", (180 - 40) / 2)
    run("geo002_deg_letter_only", g, {"claimed_answer": {"kind": "value", "option": "D"}, "steps": []}, "CORRECT", show=True)
    run("geo002_deg_payload", g, {"claimed_answer": {"kind": "value", "payload": "70°", "option": "D"}, "steps": []}, "CORRECT", show=True)
    run("geo002_plain70", g, {"claimed_answer": {"kind": "value", "payload": "70", "option": "D"}, "steps": []}, "CORRECT", show=True)
