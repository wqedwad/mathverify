from h import *
if __name__ == "__main__":
    for vars_ in ([], [{"name": "k", "domain": "integer"}], [{"name": "k", "domain": "positive_integer"}], [{"name": "k", "domain": "nonneg_integer"}]):
        tag = vars_[0]["domain"] if vars_ else "none"
        run(f"kk_{tag}", ir("series_sum", {"term": "k/k", "var": "k", "lo": -1, "hi": 1}, vars=vars_), sol("3"), "UNKNOWN", show=True)
        # natural: sum_{k=0}^{4} (k**2 - k)/(k*(k-1))... undefined at 0 and 1
        run(f"k0_{tag}", ir("series_sum", {"term": "(k**2+k)/k", "var": "k", "lo": 0, "hi": 4}, vars=vars_), sol("15"), "UNKNOWN", show=True)
