"""Mutation check of part d4c of the fourth audit's fixes (1 Oct 2026): each mutation removes one guard of the
exact zero and the numeric evidence (`certify.calculus` certificates and enclosure, `equiv.forms`,
`steps.deterministic._integrals_refute`, `equiv.random_point`, the sandbox ops; `certify.series`: nsum
alone). Round 3 (7 Oct 2026) adds the extremum's direction (E), a definite integral's value only with a
certificate (Y), random points off the grid and signs at two precisions (P), the declared tolerance (T),
outward rounding (V), the special functions' domains (A), end singularities (B) and the cell budget (C); its
mutations run tests/test_d4_d4c_tur3.py. Round 4 (8 Oct 2026, Q) adds the analytic cell (YO-A), the exact
difference at every point (YO-B), points inside the domain (YO-C), real primitives (KK-1), the tolerance path's
claims (SG-1), reversed ranges (KK-2) and the odd-root convention (BİRLEŞİK-1); its mutations run
tests/test_d4_d4c_tur4.py. The machinery (throwaway clones of the committed HEAD, exit codes,
clean-up) is the one of denetim/2026-09-26/mutasyon.py; only the list of mutations is new.

    .venv/bin/python denetim/2026-10-01/d4c/mutasyon.py [-j N] [--list] [name ...]

Kept out of pyflakes and pytest like the rest of denetim/. No string here may name a document.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("mutasyon_0926", HERE.parents[1] / "2026-09-26" / "mutasyon.py")
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

CAL = "src/mathverify/certify/calculus.py"
FRM = "src/mathverify/equiv/forms.py"
DET = "src/mathverify/steps/deterministic.py"
RP = "src/mathverify/equiv/random_point.py"
OPS = "src/mathverify/sandbox/ops.py"
NUM = "src/mathverify/equiv/numeric.py"
ENC = "src/mathverify/certify/enclosure.py"
SER = "src/mathverify/certify/series.py"
EXT = "src/mathverify/certify/extremum.py"
EQV = "src/mathverify/equiv/__init__.py"
ALG = "src/mathverify/certify/algebra.py"
DOM = "src/mathverify/certify/domain.py"
T = "tests/test_d4_d4c_sayisal.py"
T3 = "tests/test_d4_d4c_tur3.py"
T4 = "tests/test_parca4_parametreli_bicim.py"
T5 = "tests/test_d4_d4c_tur4.py"

MUTATIONS = [
    ("Z05 mutlak integrallenebilirlik varsayılır", CAL,
     "    if f.has(*_JUMPY):\n        return False\n    pts = _bad_points(f, var, lo, hi, timeout)\n",
     "    return True\n    pts = _bad_points(f, var, lo, hi, timeout)\n", T),
    ("Z06 yerel üsler yalnız 0 ve 1/2", CAL,
     "_LOCAL_EXPONENTS = (S.Zero, S.Half, sp.Rational(2, 3), sp.Rational(3, 4), sp.Rational(4, 5), sp.Rational(9, 10))\n",
     "_LOCAL_EXPONENTS = (S.Zero, S.Half)\n", T),
    ("Z07 kuyruk sınırı aranmaz", CAL,
     "        if end in (sp.oo, -sp.oo) and not any(\n",
     "        if False and not any(\n", T),
    ("Z08 tek simetri yerine çift simetri", CAL,
     "f.xreplace({var: mirror}), -f, timeout=timeout)", "f.xreplace({var: mirror}), f, timeout=timeout)", T),
    ("Z09 ilkel içte tanımsız olabilir", CAL,
     "    if bad_F is None or any(x_ != p and x_ != q for x_ in bad_F):\n",
     "    if bad_F is None:\n", T),
    ("Z10 ilkelin türevi denetlenmez", CAL,
     "    if not rs.ok or rs.value != 0:\n        return None\n    bad_F",
     "    if not rs.ok:\n        return None\n    bad_F", T),
    ("Z11 manuel ilkel denenmez", OPS,
     '    for kw in ({}, {"manual": True}):\n', '    for kw in ({},):\n', T),
    ("Z12 derin sonda yok", CAL,
     "    if cls.get(\"kind\") != \"UNKNOWN\" or \"symbolic_numeric_disagreement\" not in (cls.get(\"flags\") or []):\n        return None\n",
     "    return None\n", T),
    ("Z13 Abs/sign kırılmalarında bölünmez", CAL,
     "    cuts = _switch_points(f, var, lo, hi, timeout) if _nonsmooth(f) else []\n",
     "    cuts = []\n", T),
    ("Z15 evalf bitleri okunmaz", FRM,
     "    if bits is not None and bits < _MIN_BITS:\n        return None\n", "", T),
    ("Z17 evalf'in sıfırı ya da bitsiz sıfırı eşitlik sayılır (eski hâl)", RP,
     "        c = _exact_counterexample(a, b, syms, pt, budget)\n        if isinstance(c, dict):\n            return {\"point\"",
     "        v = sp.N(dp, 30)\n        if v == 0 or (getattr(v, \"_prec\", 0) or 0) < 50:\n            continue\n"
     "        c = _exact_counterexample(a, b, syms, pt, budget)\n        if isinstance(c, dict):\n            return {\"point\"", T),
    ("Z18 karar verilemeyen nokta sayılmaz", RP,
     "        unsure += c is None\n    return None, unsure\n", "    return None, unsure\n", T),
    ("Z19 terim sınırı yok", RP,
     "        if _terms_at(a, syms, pt) > _EVAL_TERMS or _terms_at(b, syms, pt) > _EVAL_TERMS:\n",
     "        if False:\n", T),
    ("Z20 değerlendirme süresi sınırsız", RP,
     "        if spent[0] > _EVAL_BUDGET:\n            ev[\"evaluation_time_budget\"] = True    # the points left",
     "        if False:\n            ev[\"evaluation_time_budget\"] = True    # the points left", T),
    ("Z24 simetrikleştirilmiş integralde mutlak integrallenebilirlik aranmaz", CAL,
     "        if v is not None and not _absolutely_integrable(f, var, a, b, timeout):\n",
     "        if False:\n", T),
    ("Z25 açı toplamında |Nd| < 1 aranmaz", NUM,
     "            return bool(abs(n * total) < 1)\n", "            return True\n", T),
    ("Z26 açı toplamı kesin sıfır sınamasında yok", NUM,
     "    if _angle_sum_is_zero(d) or _exp_generator_is_zero(d):\n", "    if _exp_generator_is_zero(d):\n", T),
    ("Z27 üstel üreteç kesin sıfır sınamasında yok", NUM,
     "    if _angle_sum_is_zero(d) or _exp_generator_is_zero(d):\n", "    if _angle_sum_is_zero(d):\n", T),
    # the rigorous enclosure (review of d4c, 2 Oct 2026)
    ("R01 hücrede aralık değeri yerine orta nokta", ENC,
     "    box = {var: _hull(l, r)}\n",
     "    box = {var: (L + R) / 2}\n", T),
    ("R02 Taylor kalanı düşer", ENC,
     "        second = h * iv_eval(f, {var: (L + R) / 2}) + d2 * h * h * h / 24\n",
     "        second = h * iv_eval(f, {var: (L + R) / 2})\n", T),
    ("R03 ikili olmayan uç parçası sayılmaz", ENC,
     "        edge = [iv.mpf([0, 1]) * cell(lo_, hi_, None) for lo_, hi_ in (ia, ib) if hi_ > lo_]\n",
     "        edge = []\n", T),
    ("R07 tek integralli adım zarfsız reddedilir", DET,
     "        return integral_excludes(n.function, var, a, b, other, timeout=ctx.timeout)[0]\n",
     "        return True\n", T),
    ("R09 iki integralli adımda aralık değeri yerine orta nokta", DET,
     "        env[n] = mp.iv.mpf([enc[0], enc[1]])\n", "        env[n] = mp.iv.mpf((enc[0] + enc[1]) / 2)\n", T),
    ("Z28 aşkın sayıların açı toplamı denenmez", NUM,
     "        elif not _one_in_an_exponential(z):\n            return False\n", "        else:\n            return False\n", T),
    ("Z29 kök içi çarpanlarına ayrılmaz", NUM,
     "                         lambda n: sp.factor(sp.together(n.base)) ** n.exp)\n",
     "                         lambda n: n)\n", T),
    # sibling paths of the enclosure (6 Oct 2026)
    ("S01 nsum tek başına seriyi reddeder", SER,
     '        ev["method"] = "numeric_only"\n',
     '        ev["method"] = "numeric_only"\n'
     "        if num_equal(claimed, num_val, rel_tol=1e-15)[0] is False:\n            return False, ev\n", T),
    # --- round 3: the attack on round 2 (7 Oct 2026) -----------------------------------------------------
    # YO-2: SymPy's value only with a certificate
    ("Y01 sertifika yokken SymPy'nin değeri alınır", CAL,
     '            ev["certificate"] = cev\n            if cval is not None:\n',
     '            ev["certificate"] = cev\n'
     '            if cval is None and rs.ok and isinstance(rs.value, sp.Basic) and not rs.value.has(sp.Integral):\n'
     '                cval = rs.value\n'
     '            if cval is not None:\n', T3),
    ("Y02 kareleme tek başına kabul eder", CAL,
     '                if not no:\n                    return unknown(LAYER, "no_certified_value", t.ms, ev, flags=["no_certified_value"])\n'
     '                ok = False\n',
     '                if not no and converged and num_equal(claimed, val, rel_tol=1e-20)[0]:\n'
     '                    ok = True\n'
     '                elif not no:\n                    return unknown(LAYER, "no_certified_value", t.ms, ev, flags=["no_certified_value"])\n'
     '                else:\n                    ok = False\n', T),
    ("Y03 SymPy'nin farklı değeri kanıtsız reddeder", CAL,
     '                if not no:\n                    return unknown(LAYER, "no_certified_value", t.ms, ev, flags=["no_certified_value"])\n',
     '                if not no and not (rs.ok and isinstance(rs.value, sp.Basic) and not rs.value.has(sp.Integral)\n'
     '                                   and answers_equivalent(claimed, rs.value, shape="scalar")[0] is False):\n'
     '                    return unknown(LAYER, "no_certified_value", t.ms, ev, flags=["no_certified_value"])\n', T),
    ("Y04 sertifika denenmez", CAL,
     '            cval, cev = certified_integral_value(integrand, var, a, b, timeout=ctx.timeout * 1.5)\n'
     '            ev["certificate"] = cev\n',
     '            cval, cev = None, {}\n            ev["certificate"] = cev\n', T3),
    ("Y05 sayının çeliştiği kanıt da karar verir", CAL,
     '                if converged and certified_sign(cval, timeout=ctx.timeout) != 0 and \\\n',
     '                if False and \\\n', T3),
    ("Y08 kanıtla çelişen kareleme zarfla sınanmaz", CAL,
     " is False and \\\n                        not integral_excludes(integrand, var, a, b, val, timeout=ctx.timeout * 1.5)[0]:\n",
     " is False:\n", T3),
    ("Y06 checked_forms integralde SymPy'nin değerini alır", FRM,
     "                if cval is None:\n                    raise UnverifiedForm(f\"{n}: no certified value ({cev.get('reason')})\")\n",
     "                if cval is None:\n                    cval = n.doit()\n", T3),
    ("Y07 checked_forms sertifikanın sıfır olmayan değerini almaz", FRM,
     "                reps[key] = cval\n                continue\n",
     "                if cval != 0:\n                    raise UnverifiedForm(\"nonzero\")\n                reps[key] = cval\n                continue\n", T4),
    # YO-1: the extremum's direction
    ("E01 yön 40 basamaktan okunur", EXT,
     "        s_ = certified_sign(sp.sympify(fa) - sp.sympify(fb))\n",
     "        s_ = 1 if na > nb else -1 if na < nb else None\n", T3),
    ("E02 kararsız aday EVT'yi kapatmaz", EXT,
     "    if bound is None and complete and closed and not undecided and not superlevel:\n",
     "    if bound is None and complete and closed and not superlevel:\n", T3),
    ("E03 boş olmayan üst küme EVT'yi kapatmaz", EXT,
     "    if bound is None and complete and closed and not undecided and not superlevel:\n",
     "    if bound is None and complete and closed and not undecided:\n", T3),
    # YO-3: random points off the grid, SymPy's equals
    ("P01 özdeşlik örnekleri ızgarada", RP,
     "    pts = sample_points(domains, n, seed, off_grid=True)\n", "    pts = sample_points(domains, n, seed)\n", T3),
    ("P02 irrasyonel yoklama yok", RP,
     "        vals = _special_values(domains[s_], far=far, irrational=True)\n",
     "        vals = _special_values(domains[s_], far=far)\n", T3),
    ("P03 SymPy equals False çatışması yok sayılır", EQV,
     '    if okR is True and (sev.get("equals") or {}).get("value") is False \\\n',
     '    if False and (sev.get("equals") or {}).get("value") is False \\\n', T3),
    ("P04 kaymasız örnekler", RP,
     "            v = _sample_one(dom, rng, shift=(i >= _RATIONAL_POINTS) if off_grid else None)\n",
     "            v = _sample_one(dom, rng, shift=False if off_grid else None)\n", T3),
    ("P06 SymPy equals'ın tek False'u yeter", EQV,
     "    return bool(r.ok and r.value is True)\n\n\ndef _equation_equivalent(",
     "    return True\n\n\ndef _equation_equivalent(", T3),
    ("P05 işaret ikinci hassasiyette denetlenmez", NUM,
     '    if parts is not None and "value" in (parts[2], parts[3]) and not _stands_higher(e, parts):\n',
     '    if False:\n', T3),
    # YO-4, RK-E, RK-F: the declared tolerance
    ("T01 göreli toleransın üst sınırı yok", NUM,
     "    if not isinstance(t, sp.Rational) or t <= 0 or (relative and t >= 1):\n",
     "    if not isinstance(t, sp.Rational) or t <= 0:\n", T3),
    ("T02 sıfır ya da negatif tolerans okunur", NUM,
     "    if not isinstance(t, sp.Rational) or t <= 0 or (relative and t >= 1):\n",
     "    if not isinstance(t, sp.Rational) or (relative and t >= 1):\n", T3),
    ("T03 v = 0'da göreli tolerans karar verir", NUM,
     "    sv = certified_sign(v, timeout=timeout)\n    if sv not in (1, -1):\n        return None\n",
     "    sv = certified_sign(v, timeout=timeout)\n    if sv is None or sv == NONREAL:\n        return None\n", T3),
    ("T09 sıfırda eşit değerler eşit sayılmaz", NUM,
     "                    if absd == 0 or (abs_tol is not None and absd <= mp.mpf(abs_tol)):\n",
     "                    if abs_tol is not None and absd <= mp.mpf(abs_tol):\n", T3),
    ("T10 iddia değerin kendisiyse de v = 0 karar vermez", NUM,
     "    if sd == 0:\n        return True                           # the claim is the value\n",
     "", T3),
    ("T04 merdivende ölçek max(|a|, |b|)", NUM,
     "                rel = absd / abs(vb)\n", "                rel = _rel_diff(va, vb)\n", T3),
    ("T05 kesin değerde tolerans merdivende", NUM,
     "        if exact_a and exact_b:\n            r = within_rel_tol(a, b, rel_tol)\n",
     "        if False:\n            r = within_rel_tol(a, b, rel_tol)\n", T3),
    ("T06 zarfta pencere iddiaya göre", CAL,
     "            lo_v, hi_v = (C / (1 + T), C / (1 - T)) if c[0] > 0 else (C / (1 - T), C / (1 + T))\n",
     "            lo_v, hi_v = (C - T * C, C + T * C) if c[0] > 0 else (C + T * C, C - T * C)\n", T3),
    ("T07 evaluate bozuk toleransı okur", ALG,
     "    if bad_rel or bad_abs:\n", "    if False:\n", T3),
    ("T08 belirli integral bozuk toleransı okur", CAL,
     "            if bad_tol:\n                return unknown(LAYER, \"malformed_tolerance\"",
     "            if False:\n                return unknown(LAYER, \"malformed_tolerance\"", T3),
    # YO-5: outward rounding
    ("V01 uç negatifliği yuvarlanır", ENC,
     "    return mp.make_mpf(mp.libmp.mpf_neg(v._mpf_))\n", "    return -v\n", T3),
    ("V02 Float noktası yuvarlanır", ENC,
     "        return iv.mpf(mp.make_mpf(v._mpf_))     # the Float's own binary value, exactly (mp.mpf would round it)\n",
     "        return iv.mpf(mp.mpf(v._mpf_))\n", T3),
    # RK-A: the special functions' domains
    ("A01 erf tanınmaz", DOM,
     "                sp.erf, sp.erfc, sp.erfi, sp.Si, sp.Shi, sp.fresnels, sp.fresnelc)\n",
     "                sp.erfc, sp.erfi, sp.Si, sp.Shi, sp.fresnels, sp.fresnelc)\n", T3),
    ("A02 Ci koşulsuz", DOM,
     "        add(node.args[0] > 0)                    # complex for x < 0 (a log term), -oo at 0\n",
     "        pass\n", T3),
    ("A03 polylog koşulsuz", DOM,
     "            add(z <= 1)                          # real for z <= 1, complex past 1\n", "            pass\n", T3),
    # RK-B: end singularities
    ("B01 kaldırılabilir tekillik kuralı yok", ENC,
     "                ends[here] = (_removable(f, var, end), _weights(f, var, end))\n",
     "                ends[here] = (None, _weights(f, var, end))\n", T3),
    ("B02 ağırlık kuralı yok", ENC,
     "                ends[here] = (_removable(f, var, end), _weights(f, var, end))\n",
     "                ends[here] = (_removable(f, var, end), [])\n", T3),
    ("B03 P'nin uçta sıfırlığı aranmaz", ENC,
     "            if not all(sp.simplify(sp.diff(P, var, j).subs(var, c)) == 0 for j in range(k)):\n",
     "            if False:\n", T3),
    ("B04 log ağırlığı işaret değiştirebilir", ENC,
     "        if not _ends(H)[1] < 1:\n            return None\n", "", T3),
    # RK-C: the enclosure's budget
    ("C01 güvenlik durdurucusu kısmi zarf verir", ENC,
     "                # have refuted undecided (attack on d4c round 2, RK-C). Past the safety stop, no enclosure\n"
     "                return None\n",
     "                # have refuted undecided (attack on d4c round 2, RK-C). Past the safety stop, no enclosure\n"
     "                break\n", T3),
    # round 4. YO-A: Taylor bounds only on a cell proved analytic, read as written
    ("Q01 kesirli kuvvet 0'da analitik sayılır", ENC,
     "            if an and not lo > 0:\n                raise NotAnalytic(\"a fractional power of a base that may be 0\")\n",
     "", T5),
    ("Q02 gerçel kuvvet 0'da analitik sayılır", ENC,
     "        if an and not lo > 0:\n            raise NotAnalytic(\"a real power of a base that may be 0\")\n", "", T5),
    ("Q03 Max/Min analitik sayılır", ENC,
     "            if an:\n                raise NotAnalytic(\"Max/Min\")\n", "", T5),
    ("Q04 Abs 0'da analitik sayılır", ENC, "        if an:\n            _off_zero(x, \"the argument of Abs\")\n", "", T5),
    ("Q05 sign 0'da analitik sayılır", ENC, "        if an:\n            _off_zero(x, \"the argument of sign\")\n", "", T5),
    ("Q06 asin/acos uçta analitik sayılır", ENC,
     "        if an and not (-1 < lo and hi < 1):\n            raise NotAnalytic(\"asin/acos at -1 or 1\")\n", "", T5),
    ("Q07 ara değerin sınırlılığı aranmaz", ENC, "    return _bounded(v) if analytic else v\n", "    return v\n", T5),
    ("Q08 Taylor sınırı analitik kanıtsız", ENC, "    if d2f is None or not smooth:\n", "    if d2f is None:\n", T5),
    ("Q09 uç kuralında P analitik kanıtsız", ENC, "                        iv_eval(P, side, analytic=True)\n", "", T5),
    ("Q10 ayrık kesişimde uç kuralı seçilir", ENC,
     "    return _hull(lo_, hi_) if lo_ <= hi_ else _hull(min(a1, a2), max(b1, b2))\n",
     "    return _hull(lo_, hi_) if lo_ <= hi_ else u\n", T5),
    ("Q11 sınırsız hücre önce bölünmez", ENC,
     "            k = sum(1 for _, _, c_ in cells if not finite(c_)) or max(1, len(cells) // 8)\n",
     "            k = max(1, len(cells) // 8)\n", T5),
    ("Q34 uçtaki kutup sonsuza dek bölünür", ENC,
     "                if not l < m < r or (not finite(c) and r - l < finest):\n", "                if not l < m < r:\n", T5),
    ("Q12 atan sınırsız argümanda tanımsız", ENC,
     "        return _monotone(mp.atan, x, limits=(lambda: -mp.pi / 2, lambda: mp.pi / 2))\n",
     "        return _monotone(mp.atan, x)\n", T5),
    ("Q13 tanh sınırsız argümanda tanımsız", ENC,
     "        return _monotone(mp.tanh, x, limits=(lambda: mp.mpf(-1), lambda: mp.mpf(1)))\n",
     "        return _monotone(mp.tanh, x)\n", T5),
    # KK-2: a reversed range
    ("Q14 ters sınırda pencere çevrilmemiş toplamla", ENC,
     "            clo, chi = (slo, shi) if sign > 0 else (_neg(shi), _neg(slo))\n", "            clo, chi = slo, shi\n", T5),
    # BİRLEŞİK-1: the odd-root convention of a fractional power
    ("Q15 tek kök geleneği sertifikayı durdurur", CAL,
     "            continue                                  # the fractional power rule below holds it\n",
     "            return None\n", T5),
    ("Q16 tek kök geleneği her taban için kabul", CAL,
     "                and c.args[0] in fractional:\n", "                and True:\n", T5),
    # KK-1: real primitives
    ("Q17 log(u) u < 0'da çevrilmez", CAL, "            logs[n] = sp.log(-n.args[0])\n", "            pass\n", T5),
    ("Q18 exp_polar'ın her katı indirilir", CAL, "        if not k.is_Integer:\n            return None\n", "", T5),
    ("Q19 gerçel ilkel denenmez", CAL, "            R = _real_primitive(F, var, p, q)\n", "            R = None\n", T5),
    ("Q20 polylog(1, z) türevde açılmaz", CAL,
     "    dF = rd.value.replace(lambda n: isinstance(n, sp.polylog) and n.args[0] == 1, lambda n: -sp.log(1 - n.args[1]))\n",
     "    dF = rd.value\n", T5),
    # SG-1: the tolerance path's claims
    ("Q21 toleransta sayı olmayan iddia okunur", NUM,
     "    if not (is_number_expr(c) and is_number_expr(v)):\n        return None\n", "", T5),
    ("Q22 karmaşık iddia reddedilmez", NUM,
     "        if si in (1, -1) and certified_sign(si * im_c - t * sv * v, timeout=timeout) == 1:\n            return False\n",
     "        if si in (1, -1) and certified_sign(si * im_c - t * sv * v, timeout=timeout) == 1:\n            return None\n", T5),
    ("Q23 karmaşık iddia sanal kısmı küçükken de reddedilir", NUM,
     "        if si in (1, -1) and certified_sign(si * im_c - t * sv * v, timeout=timeout) == 1:\n",
     "        if si in (1, -1):\n", T5),
    ("Q24 sonsuz iddia zarfla reddedilmez", CAL,
     "    if c is not None and not (mp.isfinite(c[0]) and mp.isfinite(c[1])):\n", "    if False:\n", T5),
    ("Q25 karmaşık iddia zarfla reddedilmez", CAL, "        im = _imaginary_part(claimed)\n", "        im = None\n", T5),
    ("Q26 karmaşık iddia zarfta sanal kısmı küçükken de reddedilir", CAL,
     "                if certified_sign(si * im_c - t_ * B) == 1:\n", "                if True:\n", T5),
    # YO-B: the exact difference at every point; the equals conflict on the antiderivative path
    ("Q27 kalan noktalarda kesin fark okunmaz", RP,
     "        witness, undecided = _nonzero_elsewhere(ae - be, syms, pts[_RATIONAL_POINTS:] + probes, a, b, budget)\n",
     "        witness, undecided = None, False\n", T5),
    ("Q28 yoklamalarda kesin fark okunmaz", RP,
     "        witness, undecided = _nonzero_elsewhere(ae - be, syms, pts[_RATIONAL_POINTS:] + probes, a, b, budget)\n",
     "        witness, undecided = _nonzero_elsewhere(ae - be, syms, pts[_RATIONAL_POINTS:], a, b, budget)\n", T5),
    ("Q29 okunamayan noktalar karar verdirir", RP,
     "        if undecided:\n            ev[\"reason\"] = \"difference_at_the_other_points_not_read\"\n            return None, ev\n",
     "", T5),
    ("Q35 kalan noktalarda işaret evalf'ten", RP,
     "            if constant_sign(dp) is None:\n                continue\n",
     "            if dp.evalf(30) == 0:\n                continue\n", T5),
    ("Q30 ilkelde equals çatışması yok", CAL,
     "        if ok is True and agreed_on == S.Reals and _equals_false_stands(dF, integrand):\n", "        if False:\n", T5),
    ("Q31 geniş alandaki uyum çatışmaya bakılmadan", CAL,
     "                ok, agreed_on = True, wide\n", "                ok = True\n", T5),
    # YO-C: points inside the domain
    ("Q32 alan dışına düşen nokta kullanılır", RP, "        q = _inside(iv, rng, shift)\n", "        q = q\n", T5),
    ("Q33 içerideki nokta ızgarada", RP, "        frac += rng.choice(_SHIFTS) / (10 * (m + 1))\n", "", T5),
]

if __name__ == "__main__":
    base.MUTATIONS = MUTATIONS
    sys.exit(base.main())
