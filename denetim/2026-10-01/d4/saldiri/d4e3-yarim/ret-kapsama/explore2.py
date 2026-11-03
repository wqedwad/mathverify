import sys
if __name__ == "__main__":
    import sympy as sp
    from mathverify.certify.base import make_ctx
    from mathverify.ir import ProblemIR
    from mathverify.normalize.parse import parse_expr_str
    ir = ProblemIR.from_dict({"task": {"kind": "derivative", "params": {"f": "x", "var": "x"}}, "vars": [{"name": "x", "domain": "real"}], "givens": [], "answer_shape": "expression"})
    ctx = make_ctx(ir)
    for s in sys.argv[1:]:
        e = parse_expr_str(s, ctx.ns)
        print(repr(s), "->", e, "| d/dx:", sp.diff(e, ctx.sym("x")))
