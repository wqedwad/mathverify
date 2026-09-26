from common import *
from mathverify.verifier import verify
if __name__ == "__main__":
    for g, b in [(["0.1*x + 0.2*y = 0.3"], {"x": ["-5", "5"], "y": ["-5", "5"]}),
                 (["x/10 + y/10 = 3/10"], {"x": ["0", "3"], "y": ["0", "3"]}),
                 (["sqrt(x) + sqrt(y) = sqrt(18)"], {"x": ["0", "18"], "y": ["0", "18"]}),
                 (["1/x + 1/y = 1/6"], {"x": ["1", "50"], "y": ["1", "50"]}),
                 (["1/x + 1/y + 1/z = 1"], {"x": ["1", "10"], "y": ["1", "10"], "z": ["1", "10"]}),
                 (["cbrt(x) <= 1"], {"x": ["-5", "5"]})]:
        vs = [{"name": k, "domain": "integer"} for k in b]
        r = verify(ir("count_solutions", {"bounds": b}, vars_=vs, givens=g, shape="count"), sol("count", 0))
        for l in r.layers:
            if l.layer == "certify.counting":
                print(g, l.evidence)
