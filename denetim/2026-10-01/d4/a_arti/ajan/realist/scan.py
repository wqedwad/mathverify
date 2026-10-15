"""Static upper-bound scan of candidate fail-closed rules over the realistic corpus.

Units: evalset (IR + reference solution), k4 (IR + recorded AI solution), textbook (89 d4e-r4 cases).
Each rule has a trigger over IR strings and/or solution strings. Output: per-rule hit lists with current verdicts.
"""
import json
import re
import sys
import collections

sys.path.insert(0, '.')
from load import load, sol_texts  # noqa: E402
from textbook import load_textbook  # noqa: E402

items, k4, verd = load()
tb = load_textbook()


def ir_strings(ir):
    """(field, text) pairs of the IR that the verifier parses."""
    out = []
    t = ir['task']
    for k, v in (t.get('params') or {}).items():
        if isinstance(v, (dict, list)):
            out.append(('param:' + k, json.dumps(v, ensure_ascii=False)))
        else:
            out.append(('param:' + k, str(v)))
    for g in ir.get('givens') or []:
        out.append(('given', str(g)))
    for f in ir.get('functions') or []:
        out.append(('function', str(f.get('expr', ''))))
        if f.get('domain'):
            out.append(('function_domain', str(f['domain'])))
    if ir.get('domain_of_discourse'):
        out.append(('discourse', str(ir['domain_of_discourse'])))
    return out


def units():
    for i, it in items.items():
        ir = it['problem_ir']
        yield dict(corpus='EV', id=i, ir=ir, sol=it['solution'], verdict=verd['evalset/' + i]['verdict'],
                   sol_ok=it['solution_is_correct'])
    for i, r in k4.items():
        ir = items[i]['problem_ir']
        lab = verd['k4/' + i].get('label') or ['?']
        yield dict(corpus='K4', id=i, ir=ir, sol=r['solution'], verdict=verd['k4/' + i]['verdict'],
                   sol_ok=(lab[0] == 'right'), ms=r.get('ms'))
    for c in tb:
        yield dict(corpus='TB', id=c['src'] + ':' + c['label'], ir=c['ir'], sol=c['sol'], verdict=c['verdict'],
                   verdict_d4e4=c['verdict_d4e4'], sol_ok=None)


# ---------- helpers ----------
CALL = re.compile(r'([A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_]+)?)\s*\(')


def calls(s):
    """list of (name, args_text) for every call in s (paren-aware)."""
    out = []
    for m in CALL.finditer(s):
        i = m.end()
        depth = 1
        j = i
        while j < len(s) and depth:
            if s[j] == '(':
                depth += 1
            elif s[j] == ')':
                depth -= 1
            j += 1
        out.append((m.group(1), s[i:j - 1]))
    return out


def top_level_split(s, sep=','):
    parts, depth, cur = [], 0, ''
    for ch in s:
        if ch in '([{':
            depth += 1
        elif ch in ')]}':
            depth -= 1
        if ch == sep and depth == 0:
            parts.append(cur)
            cur = ''
        else:
            cur += ch
    parts.append(cur)
    return parts


CONST_TOKENS = re.compile(r'\b(pi|E|oo|sqrt|log|exp|sin|cos|tan|I)\b')
IDENT = re.compile(r'\b[A-Za-z_][A-Za-z_0-9]*\b')
FUNCNAMES = {'pi', 'E', 'oo', 'sqrt', 'log', 'exp', 'sin', 'cos', 'tan', 'cot', 'sec', 'csc', 'asin', 'acos', 'atan',
             'Abs', 'Rational', 'Integer', 'Mod', 'floor', 'ceiling', 'factorial', 'binomial', 'gcd', 'lcm', 'I',
             'sinh', 'cosh', 'tanh', 'erf', 'gamma', 'Max', 'Min', 'sign', 'frac', 'Heaviside', 'root', 'cbrt'}


def is_constant(expr_text):
    names = set(IDENT.findall(expr_text)) - FUNCNAMES
    return not names


def is_rational_const(expr_text):
    return re.fullmatch(r'[\s\d+\-*/().]*', expr_text) is not None and re.search(r'\d', expr_text) is not None


def has_closed_form(s):
    return re.search(r'\b(Integral|Sum|Product|Limit|integrate|limit|summation)\s*\(', s) is not None


def answer_text(sol):
    return str((sol.get('claimed_answer') or {}).get('payload', ''))


def step_texts(sol):
    return [(w, t) for w, t in sol_texts(sol) if w != 'answer']


def all_sol_texts(sol):
    return sol_texts(sol)


def task(u):
    return u['ir']['task']['kind']


def params(u):
    return u['ir']['task'].get('params') or {}


# ---------- rules ----------
RULES = collections.OrderedDict()


def rule(name):
    def deco(f):
        RULES[name] = f
        return f
    return deco


NONTABLE = r'\b(asin|acos|acot|asec|acsc|sinh|cosh|tanh|coth|sech|csch|asinh|acosh|atanh|acoth|erf|erfc|erfi|gamma|' \
           r'loggamma|lowergamma|uppergamma|atan2|arg|cot|sec|csc|LambertW|Ei|Si|Ci|li|polylog|zeta|besselj|' \
           r'beta|digamma|Heaviside|frac|sign)\s*\('


@rule('R01 constraint∩given exception -> constraint_not_applied')
def r01(u):
    ir = u['ir']
    p = params(u)
    cons = []
    if 'interval' in p:
        cons.append('interval=' + str(p['interval']))
    if ir.get('domain_of_discourse'):
        cons.append('discourse=' + str(ir['domain_of_discourse']))
    for g in ir.get('givens') or []:
        if re.search(r'[<>]', str(g)):
            cons.append('ineq_given=' + str(g))
    for v in ir.get('vars') or []:
        if v.get('domain') not in (None, 'real'):
            cons.append('var_domain=' + v['name'] + ':' + v['domain'])
    if not cons:
        return None
    # the intersection happens only when a constraint meets another condition set (a given or a definedness cut)
    other = [g for g in ir.get('givens') or [] if '=' in str(g) and not re.search(r'[<>]', str(g))]
    defn = [t for _, t in ir_strings(ir) if re.search(r'\b(log|sqrt|tan|cot)\s*\(|/', t)]
    if not (other or defn):
        return None
    irr = any(re.search(r'\b(pi|sqrt|log|E|exp)\b', c) for c in cons)
    return ('irrational_endpoint ' if irr else '') + '; '.join(cons)[:120]


@rule('R02 EVT: extremum candidates compared only exactly')
def r02(u):
    if task(u) != 'extremum':
        return None
    return 'extremum ' + str(params(u).get('f'))


@rule('R03 constant-argument jump function (floor/ceiling/sign/frac/Mod/Heaviside/%//) read only from certified sign')
def r03(u):
    hits = []
    texts = [('ir:' + w, t) for w, t in ir_strings(u['ir'])] + [('sol:' + w, t) for w, t in all_sol_texts(u['sol'])]
    for w, t in texts:
        for name, args in calls(t):
            if name in ('floor', 'ceiling', 'sign', 'frac', 'Mod', 'Heaviside', 'RoundFunction'):
                if is_constant(args):
                    kind = 'rational' if all(is_rational_const(a.replace('**', '*')) for a in top_level_split(args)) else 'IRRATIONAL'
                    hits.append(f'{w}:{name}({args[:30]})[{kind}]')
        if re.search(r'(?<![<>=!/])//(?!=)|(?<![%])%(?!=)', t):
            hits.append(f'{w}:%or//')
    return '; '.join(hits) if hits else None


@rule('R04 deterministic budgets (set pieces>32, family members, value holes, parse time)')
def r04(u):
    a = answer_text(u['sol'])
    n_pieces = len(top_level_split(a.strip('{}'))) if a.strip().startswith('{') else a.count(' U ') + 1
    big = n_pieces > 32
    return f'answer pieces={n_pieces}' if big else None


@rule('R05 non-evalf_table special function in a constant sign/counterexample decision')
def r05(u):
    hits = []
    texts = [('ir:' + w, t) for w, t in ir_strings(u['ir'])] + [('sol:' + w, t) for w, t in all_sol_texts(u['sol'])]
    for w, t in texts:
        for m in re.finditer(NONTABLE, t):
            hits.append(f'{w}:{m.group(1)}')
    return '; '.join(sorted(set(hits))) if hits else None


@rule('R06 constant relational / Piecewise condition / Interval endpoint only via certified_sign')
def r06(u):
    hits = []
    texts = [('ir:' + w, t) for w, t in ir_strings(u['ir'])] + [('sol:' + w, t) for w, t in all_sol_texts(u['sol'])]
    for w, t in texts:
        if 'Piecewise' in t:
            hits.append(f'{w}:Piecewise')
        # relation between two constants (no variable) with an irrational constant
        for rel in re.finditer(r'(.+?)(<=|>=|!=|<|>)(.+)', t):
            lhs, rhs = rel.group(1), rel.group(3)
            if is_constant(lhs) and is_constant(rhs) and re.search(r'\b(pi|E|sqrt|log|exp|sin|cos|tan)\b', lhs + rhs):
                hits.append(f'{w}:const_rel_irrational')
                break
    p = params(u)
    if 'interval' in p and re.search(r'\b(pi|sqrt|log|E|exp)\b', str(p['interval'])):
        hits.append('ir:interval_irrational_endpoint')
    return '; '.join(sorted(set(hits))) if hits else None


@rule('R07 finite-domain point definedness undecidable (variable-exponent power) -> UNKNOWN not INCORRECT')
def r07(u):
    ir = u['ir']
    intvars = {v['name'] for v in ir.get('vars') or [] if 'integer' in str(v.get('domain'))}
    if task(u) in ('count_solutions', 'count_integers'):
        intvars |= set(re.findall(r'"([a-z])"', json.dumps(params(u).get('bounds', {}))))
    if not intvars or task(u) in ('limit', 'series_sum', 'closed_form', 'recurrence_term'):
        return None
    hits = []
    for w, t in ir_strings(ir):
        for m in re.finditer(r'(\([^()]*\)|[A-Za-z_0-9.]+)\s*\*\*\s*(\([^()]*\)|[A-Za-z_0-9.]+)', t):
            base, ex = m.group(1), m.group(2)
            bnames = set(IDENT.findall(base)) & intvars
            enames = set(IDENT.findall(ex)) & intvars
            if bnames and enames:
                hits.append(f'ir:{w}:{base}**{ex}')
    return '; '.join(hits) if hits else None


@rule('R08 random-point agreement never a proof (expression-shaped comparison)')
def r08(u):
    k = task(u)
    p = params(u)
    if k == 'derivative' and 'at' not in p:
        return 'derivative expression'
    if k in ('antiderivative', 'simplify_expression'):
        return k
    if k == 'evaluate' and (u['sol'].get('claimed_answer') or {}).get('kind') == 'expression':
        return 'evaluate expression'
    return None


@rule('R09 Float operand: tolerant Eq/Ne not decisive')
def r09(u):
    hits = []
    texts = [('ir:' + w, t) for w, t in ir_strings(u['ir'])] + [('sol:' + w, t) for w, t in all_sol_texts(u['sol'])]
    for w, t in texts:
        if re.search(r'(?<![\w.])\d+\.\d+', t):
            hits.append(w)
    return '; '.join(hits) if hits else None


@rule('R10 wordproblem layer abstains on compound/unreadable given')
def r10(u):
    if task(u) not in ('evaluate', 'solve_equation'):
        return None
    hits = []
    for g in u['ir'].get('givens') or []:
        g = str(g)
        if re.search(r'[<>]=?.*[<>]=?|\b(And|Or|Contains|in)\b|[&|∧∨∈]', g):
            hits.append('compound:' + g)
        elif re.search(r'\b[a-zA-Z]\s*\(\s*[-\d]', g) or re.search(r'\b(at|diff|Mod)\s*\(', g):
            hits.append('function_application:' + g)
    return '; '.join(hits) if hits else None


@rule('R11 hard wall-clock per verify')
def r11(u):
    ms = u.get('ms')
    if ms is None:
        return None
    return f'ms={ms:.0f}' if ms > 30000 else None


@rule('R12a d4e4-YO-1: derivative of Abs(non-polynomial u)')
def r12a(u):
    if task(u) != 'derivative':
        return None
    f = str(params(u).get('f'))
    for name, args in calls(f):
        if name == 'Abs' and re.search(r'\b(sin|cos|tan|exp|log|sqrt)\b|\*\*\s*\(?\s*\d+/\d+', args):
            return 'Abs(' + args + ')'
    return None


@rule('R12b d4e4-YO-2/YO-3: fractional power whose base zeros are a family / not classifiable, claim undefined at base zero')
def r12b(u):
    if task(u) != 'derivative':
        return None
    f = str(params(u).get('f'))
    out = []
    for name, args in calls(f):
        if name in ('sqrt', 'root', 'cbrt'):
            out.append((name, args))
    for m in re.finditer(r'\(([^()]+)\)\s*\*\*\s*\(\s*\d+\s*/\s*\d+\s*\)', f):
        out.append(('pow', m.group(1)))
    hits = []
    for name, base in out:
        names = set(IDENT.findall(base)) - FUNCNAMES
        fam = re.search(r'\b(sin|cos|tan)\b', base)
        mixed = re.search(r'\b(sin|cos|tan|exp|log)\b', base) and re.search(r'(?<![a-z(])x(?![a-z])', re.sub(r'\b(sin|cos|tan|exp|log)\([^()]*\)', '', base))
        param = bool(names - {'x'})
        if fam or mixed or param:
            hits.append(f"{name}({base})[{'family' if fam else ''}{'mixed' if mixed else ''}{'param' if param else ''}]")
    return '; '.join(hits) if hits else None


@rule('R12c d4e4-RK-1/U5 softening: derivative refuted via nan at base zero / symbolic integer exponent')
def r12c(u):
    if task(u) != 'derivative':
        return None
    f = str(params(u).get('f'))
    if re.search(r'sqrt|\*\*\s*\(?\s*\d+\s*/\s*\d+|\*\*\s*[a-z]', f):
        return 'fractional/symbolic power in f'
    return None


@rule('R13 Matrix with condition-bearing / closed-form entries held')
def r13(u):
    hits = []
    texts = [('ir:' + w, t) for w, t in ir_strings(u['ir'])] + [('sol:' + w, t) for w, t in all_sol_texts(u['sol'])]
    for w, t in texts:
        for name, args in calls(t):
            if name == 'Matrix':
                if re.search(r'/\s*\(?[a-z]|\b(sqrt|log|Integral|Sum|Limit|Product)\b|\*\*\s*0\b|\*\*\s*\(?-', args):
                    hits.append(f'{w}:Matrix({args[:40]})')
    return '; '.join(hits) if hits else None


@rule('R14 0/oo base with non-constant exponent -> zero_power convention')
def r14(u):
    hits = []
    texts = [('ir:' + w, t) for w, t in ir_strings(u['ir'])] + [('sol:' + w, t) for w, t in all_sol_texts(u['sol'])]
    for w, t in texts:
        for m in re.finditer(r'(?<![\w.)])(0|oo)\s*\*\*\s*(\(?[^,;)\s]*)', t):
            if not is_rational_const(m.group(2).strip('()') or '0'):
                hits.append(f'{w}:{m.group(0)}')
    return '; '.join(hits) if hits else None


@rule('R15 complex discourse keeps NO_VALUE/convention conditions')
def r15(u):
    d = str(u['ir'].get('domain_of_discourse') or '')
    vd = [v.get('domain') for v in u['ir'].get('vars') or []]
    if re.search(r'complex|ℂ|C\b', d) or 'complex' in vd:
        return d or 'complex var'
    return None


@rule('R16 total function of ±oo / AccumBounds outside limit tasks -> NO_VALUE')
def r16(u):
    if task(u) == 'limit':
        return None
    hits = []
    texts = [('ir:' + w, t) for w, t in ir_strings(u['ir'])] + [('sol:' + w, t) for w, t in all_sol_texts(u['sol'])]
    for w, t in texts:
        for name, args in calls(t):
            if name in ('sin', 'cos', 'tan', 'floor', 'ceiling', 'sign', 'frac', 'Mod') and re.search(r'\boo\b', args) \
                    and not has_closed_form(args):
                hits.append(f'{w}:{name}({args[:30]})')
        if 'AccumBounds' in t:
            hits.append(f'{w}:AccumBounds')
    return '; '.join(hits) if hits else None


@rule('R17 Sum/Product bound non-linear or non-integer -> region not built')
def r17(u):
    hits = []
    texts = [('ir:' + w, t) for w, t in ir_strings(u['ir'])] + [('sol:' + w, t) for w, t in all_sol_texts(u['sol'])]
    p = params(u)
    if task(u) == 'series_sum':
        texts.append(('ir:bounds', f"Sum(t, (k, {p.get('lo')}, {p.get('hi')}))"))
    for w, t in texts:
        for name, args in calls(t):
            if name in ('Sum', 'Product', 'summation'):
                parts = top_level_split(args)
                if len(parts) >= 2:
                    lim = parts[1].strip().strip('()')
                    bp = top_level_split(lim)
                    for b in bp[1:]:
                        b = b.strip()
                        if re.search(r'\*\*|[a-z]\s*\*\s*[a-z]|/', b) and b not in ('oo',):
                            hits.append(f'{w}:bound {b}')
    return '; '.join(hits) if hits else None


DECIDING = ('floor', 'ceiling', 'Mod', 'Max', 'Min', 'Piecewise', 'Interval', 'at', 'subs', 'simplify', 'expand',
            'factor', 'Matrix', 'Ne', 'Eq', 'Lt', 'Gt', 'Le', 'Ge', 'Contains', 'sign', 'frac', 'det', 'trace')


@rule('R18 closed Integral/Sum/Product/Limit inside a deciding node or wrapper (strict) / as a relation side (wide)')
def r18(u):
    strict, wide = [], []
    texts = [('ir:' + w, t) for w, t in ir_strings(u['ir'])] + [('sol:' + w, t) for w, t in all_sol_texts(u['sol'])]
    for w, t in texts:
        for name, args in calls(t):
            if name in DECIDING and has_closed_form(args):
                strict.append(f'{w}:{name}(..{"Integral" if "Integral" in args else "Limit" if "Limit" in args else "Sum"}..)')
        for m in re.finditer(r'(<=|>=|!=|==|<|>|(?<![<>!=])=(?!=))', t):
            pass
        sides = re.split(r'<=|>=|!=|==|<|>|(?<![<>!=])=(?!=)', t)
        if len(sides) >= 2 and any(has_closed_form(s) for s in sides):
            wide.append(w)
    if not (strict or wide):
        return None
    return ('STRICT ' + '; '.join(sorted(set(strict))) if strict else 'wide_only') + (f' | wide={len(wide)}' if wide else '')


@rule('R19 keyword-argument call in claim/step text')
def r19(u):
    hits = []
    texts = [('ir:' + w, t) for w, t in ir_strings(u['ir'])] + [('sol:' + w, t) for w, t in all_sol_texts(u['sol'])]
    for w, t in texts:
        depth = 0
        for i, ch in enumerate(t):
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
            elif ch == '=' and depth > 0:
                prev = t[i - 1] if i else ''
                nxt = t[i + 1] if i + 1 < len(t) else ''
                if prev not in '<>!=' and nxt != '=' and re.search(r'[A-Za-z_]\w*\s*$', t[:i]):
                    hits.append(f'{w}:{t[max(0, i - 8):i + 5]}')
                    break
    return '; '.join(hits) if hits else None


@rule('R20 declared d/dv symbol + LaTeX d-fraction')
def r20(u):
    names = {v['name'] for v in u['ir'].get('vars') or []}
    dn = {n for n in names if n == 'd' or (n.startswith('d') and len(n) <= 3)}
    latex = [w for w, t in all_sol_texts(u['sol']) if re.search(r'\\[dt]?frac\s*\{\s*(\\mathrm\{)?d', t)]
    if dn and latex:
        return f'vars {dn} + latex {latex}'
    if dn:
        return f'declared {dn} (no LaTeX d-fraction)'
    return None


@rule('R21 domain/given text collapsing to constant or multi-piece list')
def r21(u):
    hits = []
    for w, t in ir_strings(u['ir']):
        if w in ('function_domain', 'given', 'discourse'):
            if re.search(r'\\notin|∉|not in|\\in|∈', t):
                hits.append(f'{w}:membership:{t}')
            if len(top_level_split(t)) > 1 and re.search(r'[\[(].*,.*[\])]|\{', t):
                hits.append(f'{w}:list:{t}')
    return '; '.join(hits) if hits else None


@rule('R22 trig family index named in givens / >=2 family parameters in claim')
def r22(u):
    a = answer_text(u['sol'])
    fam = set(re.findall(r'\b([kmn]\d?|[kmn]_\d)\b', a)) - {'n'} if task(u) != 'trig_solve' else set(re.findall(r'\b([kmnt]\d?)\b', a))
    if task(u) != 'trig_solve' or not fam:
        return None
    given_names = set()
    for g in u['ir'].get('givens') or []:
        given_names |= set(IDENT.findall(str(g)))
    out = []
    if fam & given_names:
        out.append('index named in givens ' + str(fam & given_names))
    if len(fam) >= 2:
        out.append('>=2 family params ' + str(fam))
    return '; '.join(out) if out else None


@rule('R23 claimed answer computes gcd/lcm or the target operation (floor, Mod, ...)')
def r23(u):
    a = answer_text(u['sol'])
    m = re.search(r'\b(gcd|lcm|floor|ceiling|Mod|factorial|binomial|det|trace|Integral|Sum|Limit|diff|at)\s*\(', a)
    return 'answer contains ' + m.group(1) if m else None


@rule('R24 relation-shaped claim with non-bare-variable side (as_set not used)')
def r24(u):
    a = answer_text(u['sol'])
    if task(u) in ('equation_of', 'tangent_line'):
        return None
    if a.lstrip().startswith(('Piecewise', 'Matrix')) or not re.search(r'<|>|(?<![<>!=])=(?!=)|\b(Eq|Ne|And|Or|Contains)\(|\\in|∈', a):
        return None
    var = (params(u).get('var') or 'x')
    sides = re.split(r'<=|>=|<|>|(?<![<>!=])=(?!=)', a)
    bare = all(s.strip() == var or is_constant(s) for s in sides)
    return ('bare-variable relation ' if bare else 'NON-BARE relation ') + a[:60]


@rule('R25 PRE-RK-5 softening: claim containing the unknown -> UNKNOWN not INCORRECT')
def r25(u):
    a = answer_text(u['sol'])
    var = params(u).get('var')
    if task(u) in ('equation_of', 'tangent_line', 'derivative', 'antiderivative', 'simplify_expression', 'closed_form',
                   'domain_of'):
        return None
    names = set(IDENT.findall(a)) - FUNCNAMES - {'k', 'U', 'Interval', 'open', 'Union', 'Matrix', 'C', 'None'}
    unknowns = {var} if var else {v['name'] for v in u['ir'].get('vars') or [] if v['name'] not in (u['ir'].get('functions') and sum((f.get('params') or [] for f in u['ir']['functions']), []) or [])}
    names &= (unknowns | {'x', 'y'})
    if names:
        return 'answer names ' + ','.join(sorted(names))
    return None


@rule('R26 PRE-RK-4: params.equation/inequality as step premise')
def r26(u):
    p = params(u)
    if task(u) in ('solve_equation', 'solve_inequality') and (p.get('equation') or p.get('inequality')):
        return 'params.' + ('equation' if p.get('equation') else 'inequality')
    return None


@rule('R27 D4F2B-YO-1: unreadable as-written step text not treated as convention')
def r27(u):
    hits = [w for w, t in step_texts(u['sol']) if re.search(r'\\|\bU\b|dir=|\bin\b|!', t) and '!=' not in t]
    return '; '.join(hits) if hits else None


@rule('R28 mc.consistency vetoes only when option is read in the answer type')
def r28(u):
    o = u['ir'].get('options') or {}
    hits = []
    for k, v in o.items():
        v = str(v)
        if re.search(r'\d,\d', v) and not re.search(r'[(\[{]', v):
            hits.append(f'{k}:decimal_comma')
        elif re.search(r'^\s*\(.*,.*\)\s*$', v) and task(u) not in ('solve_inequality', 'domain_of'):
            hits.append(f'{k}:tuple')
        elif re.search(r'[<>]|\\in|∈|\bx\s*=', v) and task(u) not in ('equation_of', 'tangent_line'):
            hits.append(f'{k}:relation')
        elif re.search(r'[a-zçğıöşü]{4,}', v) and not re.search(r'Matrix|sqrt|log|exp|sin|cos|tan|open|Interval', v):
            hits.append(f'{k}:text')
    return '; '.join(hits) if hits else None


def run():
    res = collections.OrderedDict()
    for name, f in RULES.items():
        res[name] = []
    for u in units():
        for name, f in RULES.items():
            try:
                h = f(u)
            except Exception as e:  # noqa: BLE001
                h = 'SCAN_ERROR ' + repr(e)
            if h:
                res[name].append(dict(corpus=u['corpus'], id=u['id'], verdict=u['verdict'], sol_ok=u.get('sol_ok'),
                                      d4e4=u.get('verdict_d4e4'), why=h))
    return res


if __name__ == '__main__':
    res = run()
    summary = {}
    for name, hits in res.items():
        c = collections.Counter((h['corpus'], h['verdict']) for h in hits)
        ids = {k: sorted({h['id'] for h in hits if h['corpus'] == k}) for k in ('EV', 'K4', 'TB')}
        summary[name] = dict(EV=len(ids['EV']), K4=len(ids['K4']), TB=len(ids['TB']),
                             by_verdict={f'{a}:{b}': n for (a, b), n in sorted(c.items())})
        print(f"\n=== {name}\n  EV={len(ids['EV'])} K4={len(ids['K4'])} TB={len(ids['TB'])}  {dict(sorted(c.items()))}")
        shown = collections.Counter()
        for h in hits:
            key = (h['corpus'], h['why'][:70])
            shown[key] += 1
        for (corp, why), n in sorted(shown.items())[:14]:
            print(f'    {corp} x{n}: {why}')
    json.dump(dict(summary=summary, hits=res), open('scan_out.json', 'w'), ensure_ascii=False, indent=1)
