"""C13 extremum: an unrecognised `which` ('maximum', 'MAX') silently falls into the argmin branch.
Ground truth: max of 4-(x-1)^2 on [0,3] is 4 at x=1; the claim 3 is the argmin."""
from _r import IR, SOL, check

if __name__ == "__main__":
    E = lambda w: IR("extremum", {"f": "4 - (x - 1)**2", "var": "x", "interval": "[0, 3]", "which": w})
    check("which='maximum' claim 3", E("maximum"), SOL("value", "3"), "CORRECT")
    check("which='MAX' claim 3", E("MAX"), SOL("value", "3"), "CORRECT")
    check("which='maximum' claim 4 (right answer)", E("maximum"), SOL("value", "4"), "INCORRECT")
