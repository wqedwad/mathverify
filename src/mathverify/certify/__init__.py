"""L3 certificates: each module tests the *given claim* (handoff §4.1, "kontrol eden hesap").

`verify(ir, solution, ctx) -> LayerResult` for every module. All CAS calls go through the
sandbox. A `fail` from a certificate is hard evidence (veto); a `pass` is hard positive
evidence; `unknown` carries no weight.
"""
from . import (algebra, calculus, counting, domain, extremum, limits, trig, wordproblem, geometry,
               geometry_numeric, combinatorics, series, linalg)

MODULES = {
    "certify.algebra": algebra,
    "certify.calculus": calculus,
    "certify.counting": counting,
    "certify.domain": domain,
    "certify.extremum": extremum,
    "certify.limits": limits,
    "certify.trig": trig,
    "certify.wordproblem": wordproblem,
    "certify.geometry": geometry,
    # F2
    "certify.geometry_numeric": geometry_numeric,
    "certify.combinatorics": combinatorics,
    "certify.series": series,
    "certify.linalg": linalg,
}

__all__ = ["MODULES"] + list(MODULES)
