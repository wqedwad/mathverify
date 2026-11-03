"""Which currently-CORRECT expression-shaped verdicts would need random-point agreement (D4C-T4-PI rule)?

Pure SymPy replica of the verifier's symbolic path: sym_equal = structural, then zero_test_battery
(the same eight canonicalisers as sandbox.ops.zero_test_battery), then sympy `equals`. Symbols real=True
as in certify.base.Ctx. Non-smooth comparisons (Abs/sign/Piecewise/Max/Min) go to the per-cell symbolic
proof, not to random-point agreement, and are reported separately.
"""
import json
import sys

import sympy as sp

sys.path.insert(0, '.')


def battery(d):
    for fn in (lambda e: sp.simplify(e), lambda e: sp.cancel(sp.together(e)), lambda e: sp.expand(e),
               lambda e: sp.trigsimp(e), lambda e: sp.radsimp(e),
               lambda e: sp.powsimp(sp.expand_log(e, force=False)), lambda e: sp.logcombine(e),
               lambda e: sp.expand_trig(e)):
        try:
            r = fn(d)
            if r == 0 or (r.is_number and r.is_zero):
                return True
        except Exception:  # noqa: BLE001
            continue
    return False


def classical(e):
    e = e.replace(lambda z: isinstance(z, sp.DiracDelta), lambda z: sp.S.Zero)
    return e.replace(lambda z: isinstance(z, sp.Heaviside), lambda z: (1 + sp.sign(z.args[0])) / 2)


NONSMOOTH = (sp.Abs, sp.sign, sp.Piecewise, sp.Max, sp.Min, sp.floor, sp.ceiling)


def P(s, names):
    ns = {n: sp.Symbol(n, real=True) for n in names}
    ns['E'] = sp.E
    s = s.replace('\\frac{2x+1}{x^2+x}', '(2*x+1)/(x**2+x)')
    return sp.parse_expr(s, local_dict=ns)


def classify(kind, f, claim, names, var='x'):
    x = sp.Symbol(var, real=True)
    fe = P(f, names)
    ce = P(claim, names)
    if kind == 'derivative':
        truth = classical(sp.diff(fe, x))
        other = ce
    elif kind == 'antiderivative':
        ce = ce.subs(sp.Symbol('C', real=True), 0)
        truth = fe
        other = classical(sp.diff(ce, x))
        if sp.simplify(other - truth) == 0:
            return 'symbolic(residual)'
    else:  # simplify / evaluate expression
        truth = fe
        other = ce
    if other.has(*NONSMOOTH) or truth.has(*NONSMOOTH):
        return 'nonsmooth->cell_proof(symbolic)'
    if other == truth or sp.expand(other - truth) == 0:
        return 'symbolic(structural)'
    if battery(other - truth):
        return 'symbolic(battery)'
    try:
        eq = other.equals(truth)
    except Exception:  # noqa: BLE001
        eq = None
    return 'sympy_equals(numeric-assisted)' if eq else 'RANDOM_POINT_NEEDED'


if __name__ == '__main__':
    from load import load
    from textbook import load_textbook
    items, k4, verd = load()
    out = []
    seen = {}
    for corp, src in (('EV', items), ('K4', k4)):
        for i, it in src.items():
            ir = items[i]['problem_ir']
            k = ir['task']['kind']
            p = ir['task']['params']
            sol = it['solution']
            v = verd[('evalset/' if corp == 'EV' else 'k4/') + i]['verdict']
            if v != 'CORRECT':
                continue
            if k == 'derivative' and 'at' not in p:
                key = (k, p['f'], sol['claimed_answer']['payload'])
            elif k == 'antiderivative':
                key = (k, p['integrand'], sol['claimed_answer']['payload'])
            elif k == 'simplify_expression':
                key = (k, p['expr'], sol['claimed_answer']['payload'])
            else:
                continue
            names = [vv['name'] for vv in ir['vars']] or ['x']
            if key not in seen:
                try:
                    seen[key] = classify(key[0], key[1], key[2], names)
                except Exception as e:  # noqa: BLE001
                    seen[key] = 'ERROR ' + repr(e)[:80]
            out.append((corp, i, key[0], key[2], seen[key]))
    for c in load_textbook():
        if c['verdict'] != 'CORRECT':
            continue
        t = c['ir']['task']
        if t['kind'] == 'derivative' and 'at' not in t['params'] and not t['params'].get('order'):
            kind, f = 'derivative', t['params']['f']
        elif t['kind'] == 'derivative' and t['params'].get('order'):
            kind, f = 'derivative2', t['params']['f']
        elif t['kind'] == 'antiderivative':
            kind, f = 'antiderivative', t['params']['integrand']
        else:
            continue
        names = [vv['name'] for vv in c['ir']['vars']]
        claim = c['sol']['claimed_answer']['payload']
        try:
            if kind == 'derivative2':
                x = sp.Symbol('x', real=True)
                r = classify('simplify', str(sp.diff(P(f, names), x, 2)), claim, names)
            else:
                r = classify(kind, f, claim, names)
        except Exception as e:  # noqa: BLE001
            r = 'ERROR ' + repr(e)[:80]
        out.append(('TB', c['label'], kind, claim, r))
    for row in out:
        print(' | '.join(map(str, row)))
    json.dump(out, open('probe_rp_out.json', 'w'), ensure_ascii=False, indent=1)
