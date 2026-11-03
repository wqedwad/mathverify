import sys
if __name__ == "__main__":
    from mathverify.certify.domain import written_definedness
    from mathverify.normalize.parse import parse_as_written
    from mathverify.certify.base import make_ctx
    from mathverify.ir import ProblemIR
    import sympy as sp
    pass
    ir = ProblemIR.from_dict({"task": {"kind": "derivative", "params": {"f": "x", "var": "x"}}, "vars": [{"name": "x", "domain": "real"}, {"name":"n","domain":"positive_integer"},{"name":"k","domain":"integer"},{"name":"r","domain":"real"}], "givens": [], "answer_shape": "expression"})
    ctx = make_ctx(ir)
    ns = ctx.ns
    for s in sys.argv[1:]:
        try:
            e = parse_as_written(s, ns)
            print(repr(s), "->", e, "|", written_definedness(s, ns))
        except Exception as ex:
            print(repr(s), "EXC", type(ex).__name__, ex)
