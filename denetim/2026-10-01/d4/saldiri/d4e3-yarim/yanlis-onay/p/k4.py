import sympy as sp
if __name__ == "__main__":
    from mathverify.certify.domain import written_definedness, definedness_conditions
    from mathverify.normalize.parse import parse_as_written
    from mathverify.certify import base
    import inspect
    fn = [n for n, o in inspect.getmembers(base) if inspect.isfunction(o) and "Ctx(ir=ir" in inspect.getsource(o)]
    print(fn)
    from mathverify.ir import ProblemIR
    raw = {"task": {"kind": "limit", "params": {"expr": "Abs(x)/x", "var": "x", "to": "0"}}, "vars": [{"name": "x", "domain": "real"}, {"name": "t", "domain": "real"}],
           "givens": [], "answer_shape": "scalar"}
    ir = ProblemIR.from_dict(raw)
    ctx = getattr(base, fn[0])(ir)
    ns = ctx.ns
    for s in ("0*Integral(1/t, (t, x, 1))", "x + 0*Integral(1/t, (t, x, 1)) > 0", "0*Integral(1/t, (t, x, 1)) >= 0",
              "x + 0*Integral(exp(-x*t), (t, 0, oo))", "x + 0*Integral(1/t, (t, 1, oo))", "x + 0*Integral(1/sqrt(t), (t, x, 1)) > -1"):
        e = parse_as_written(s, ns)
        print(repr(s), "->", e, "|", definedness_conditions(e, None), "|", written_definedness(s, ns))
