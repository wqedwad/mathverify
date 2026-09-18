"""Turkish lexicon and number normalisation (handoff §8 "Türkçe parse notları").

Facts encoded here:
  * decimal separator is a COMMA ("3,5"), thousands separator is a DOT ("10.000") —
    parse-error source #1.
  * OBEB/EBOB = gcd, OKEK/EKOK = lcm.
  * "en az/en çok", "ardışık", "birbirinden farklı", "pozitif tam sayı" ... become IR
    constraints.
Everything is rule-based and deterministic. This is the Phase-1 lexicon used by the
type classifier and by unit tests; the full NL -> IR extraction is an F3 LLM task.
"""
from __future__ import annotations

import re
from typing import Iterable

__all__ = ["normalize_numbers_tr", "tr_to_canonical", "extract_constraints_tr",
           "classify_tr", "TR_TERMS", "TOPIC_KEYWORDS"]

# ---------------------------------------------------------------------------
# numbers
# ---------------------------------------------------------------------------
# 1.234.567,89 | 10.000 | 3,5 | 12 | 0,25
_NUM_RE = re.compile(r"(?<![\w.,])(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+,\d+|\d+(?:\.\d+)?)(?![\w])")


def _canon_one(tok: str) -> str:
    if "," in tok:                              # comma => decimal, dots => thousands
        ip, fp = tok.split(",", 1)
        return ip.replace(".", "") + "." + fp
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", tok):   # dots in groups of 3 => thousands
        return tok.replace(".", "")
    return tok                                   # "3.14" style (rare in TR) left as is


def normalize_numbers_tr(text: str) -> str:
    """Rewrite Turkish-formatted numbers into canonical dot-decimal / no-thousands form."""
    return _NUM_RE.sub(lambda m: _canon_one(m.group(1)), text)


# ---------------------------------------------------------------------------
# lexicon
# ---------------------------------------------------------------------------
TR_TERMS: dict[str, str] = {
    "obeb": "gcd", "ebob": "gcd", "okek": "lcm", "ekok": "lcm",
    "karekök": "sqrt", "küp kök": "cbrt", "mutlak değer": "Abs",
    "türev": "derivative", "integral": "integral", "limit": "limit",
    "tam sayı": "integer", "doğal sayı": "natural", "gerçek sayı": "real", "reel sayı": "real",
    "rasyonel sayı": "rational", "asal sayı": "prime", "çift sayı": "even", "tek sayı": "odd",
    "pozitif": "positive", "negatif": "negative", "sıfırdan farklı": "nonzero",
    "en az": "at least", "en çok": "at most", "en fazla": "at most", "en küçük": "minimum",
    "en büyük": "maximum", "ardışık": "consecutive", "birbirinden farklı": "distinct",
    "rakam": "digit", "basamak": "digit place", "kalan": "remainder", "bölüm": "quotient",
    "çarpan": "factor", "kat": "multiple", "kesir": "fraction", "yüzde": "percent",
    "derece": "degree", "radyan": "radian", "açı": "angle", "üçgen": "triangle",
    "çevre": "perimeter", "alan": "area", "hacim": "volume", "uzunluk": "length",
    "eğim": "slope", "teğet": "tangent", "kök": "root", "çözüm kümesi": "solution set",
    "tanım kümesi": "domain", "görüntü kümesi": "range", "değer kümesi": "codomain",
    "fonksiyon": "function", "ters fonksiyon": "inverse function", "bileşke": "composition",
    "polinom": "polynomial", "katsayı": "coefficient", "eşitsizlik": "inequality",
    "denklem": "equation", "dizi": "sequence", "seri": "series", "toplam": "sum",
    "çarpım": "product", "olasılık": "probability", "permütasyon": "permutation",
    "kombinasyon": "combination", "küme": "set", "eleman": "element", "alt küme": "subset",
    "sanal": "imaginary", "karmaşık sayı": "complex number", "matris": "matrix",
    "determinant": "determinant", "maksimum": "maximum", "minimum": "minimum",
    "artan": "increasing", "azalan": "decreasing", "yerel": "local", "mutlak": "absolute",
    "süreklilik": "continuity", "sürekli": "continuous", "logaritma": "logarithm",
    "üslü": "exponential", "köklü": "radical", "orta nokta": "midpoint", "uzaklık": "distance",
    "çember": "circle", "daire": "disk", "doğru": "line", "parabol": "parabola",
    "kaç": "how many", "kaçtır": "what is", "bulunuz": "find", "hesaplayınız": "compute",
}


def tr_to_canonical(text: str) -> str:
    """Lower-case, number-normalise and replace lexicon terms (longest match first)."""
    t = normalize_numbers_tr(text)
    low = t.lower()
    for k in sorted(TR_TERMS, key=len, reverse=True):
        low = re.sub(r"\b" + re.escape(k) + r"\w*", TR_TERMS[k], low)
    return low


# ---------------------------------------------------------------------------
# constraint patterns  (phrase -> constraint generator)
# ---------------------------------------------------------------------------
def extract_constraints_tr(text: str, var_names: Iterable[str]) -> dict[str, list[str]]:
    """Rule-based constraint extraction. Returns {"domain": [...], "constraints": [...]}.

    Only patterns whose meaning is unambiguous are encoded. Anything else is left
    to the (F3) LLM pass. `var_names` are the symbols the constraints refer to.
    """
    vs = list(var_names)
    low = normalize_numbers_tr(text).lower()
    domain: list[str] = []
    cons: list[str] = []

    def each(fmt: str) -> list[str]:
        return [fmt.format(v=v) for v in vs]

    if re.search(r"pozitif tam say", low):
        domain += ["integer"]
        cons += each("{v} > 0")
    elif re.search(r"negatif tam say", low):
        domain += ["integer"]
        cons += each("{v} < 0")
    elif re.search(r"doğal say", low):
        domain += ["integer"]
        cons += each("{v} >= 0")
    elif re.search(r"tam say", low):
        domain += ["integer"]
    elif re.search(r"pozitif (gerçek|reel) say", low):
        cons += each("{v} > 0")

    if "sıfırdan farklı" in low:
        cons += each("{v} != 0")
    if "birbirinden farklı" in low and len(vs) >= 2:
        for i in range(len(vs)):
            for j in range(i + 1, len(vs)):
                cons.append(f"{vs[i]} != {vs[j]}")
    if re.search(r"ardışık", low) and len(vs) >= 2:
        for i in range(len(vs) - 1):
            cons.append(f"{vs[i+1]} = {vs[i]} + 1")
    if re.search(r"\bçift say", low):
        cons += each("Mod({v}, 2) = 0")
    if re.search(r"\btek say", low):
        cons += each("Mod({v}, 2) = 1")
    m = re.search(r"(iki|üç|dört) basamaklı", low)
    if m:
        n = {"iki": 2, "üç": 3, "dört": 4}[m.group(1)]
        cons += each(f"{{v}} >= {10**(n-1)}") + each(f"{{v}} <= {10**n - 1}")
    if re.search(r"\brakam", low) and not m:
        cons += each("{v} >= 0") + each("{v} <= 9")
    m = re.search(r"en az (\d+(?:\.\d+)?)", low)
    if m:
        cons += each(f"{{v}} >= {m.group(1)}")
    m = re.search(r"en (?:çok|fazla) (\d+(?:\.\d+)?)", low)
    if m:
        cons += each(f"{{v}} <= {m.group(1)}")
    # de-duplicate, keep order
    seen = set()
    cons = [c for c in cons if not (c in seen or seen.add(c))]
    return {"domain": domain, "constraints": cons}


# ---------------------------------------------------------------------------
# type classifier (keyword scoring)
# ---------------------------------------------------------------------------
TOPIC_KEYWORDS: dict[str, list[str]] = {
    "limit": ["limit", "lim ", "lim_", "→", "yaklaş"],
    "türev": ["türev", "teğet", "eğim", "maksimum", "minimum", "ekstremum", "artan", "azalan",
              "yerel", "en büyük değer", "en küçük değer", "hız değiş", "f'("],
    "integral": ["integral", "∫", "ilkel", "dx", "altında kalan alan", "eğri"],
    "trigonometri": ["sin", "cos", "tan", "cot", "radyan", "trigonometri", "sinüs", "kosinüs", "°"],
    "logaritma": ["log", "ln", "logaritma"],
    "olasılık": ["olasılı", "zar", "madeni para", "torba", "rastgele", "seçil"],
    "permütasyon-kombinasyon": ["kaç farklı", "sıralan", "permütasyon", "kombinasyon", "seçim",
                                "kaç şekilde", "kaç türlü"],
    "problemler": ["yaş", "işçi", "havuz", "musluk", "hız", "yol", "km", "saat", "kâr", "kar ",
                   "zarar", "fiyat", "tl", "karışım", "yüzde", "%", "maliyet", "indirim",
                   "toplam", "kişi", "öğrenci", "elma", "top", "bilet", "ücret"],
    "sayılar": ["obeb", "okek", "ebob", "ekok", "bölünebil", "asal", "rakam", "basamak",
                "tam sayı", "doğal sayı", "kalan", "tam bölen", "çarpan", "ardışık"],
    "eşitsizlik": ["eşitsizli", "çözüm aralığı", "en geniş", "aralığı", "<", ">", "≤", "≥"],
    "fonksiyonlar": ["fonksiyon", "f(x)", "g(x)", "ters", "bileşke", "f∘g", "fog", "f(g"],
    "polinom": ["polinom", "p(x)", "derece", "katsay", "kalan", "çarpanlarına"],
    "analitik geometri": ["doğrunun denklemi", "noktasından geçen", "noktalarından geçen", "eğimi", "uzaklığ",
                          "çemberin", "koordinat", "orta nokta", "eksen", "merkez", "yarıçap", "analitik"],
    "geometri": ["üçgen", "dörtgen", "kare", "dikdörtgen", "yamuk", "paralelkenar", "çevre",
                 "alan", "hacim", "küp", "silindir", "koni", "küre", "açı", "kenar", "köşegen"],
    "kümeler": ["küme", "eleman", "alt küme", "∩", "∪", "kesişim", "birleşim"],
    "denklem": ["denklem", "çözüm kümesi", "kökler", "çözümü", "denklemini sağlayan"],
    "mutlak değer-köklü": ["mutlak", "|x", "karekök", "√", "köklü"],
    "diziler-seriler": ["dizi", "terim", "aritmetik", "geometrik", "genel terim", "toplamı"],
    "karmaşık sayılar": ["karmaşık", "sanal", "i²", "i^2", "z ="],
    "lineer cebir": ["matris", "determinant", "vektör", "özdeğer", "lineer"],
}

# operator-like tokens are decisive on their own
_WEIGHT = {"sin": 4, "cos": 4, "tan": 4, "cot": 4, "∫": 5, "lim ": 5, "lim_": 5, "log": 4, "ln": 3,
           "f'(": 5, "dx": 3, "°": 3, "radyan": 4, "türev": 5, "integral": 5, "limit": 5}

_PRIORITY = ["limit", "integral", "türev", "trigonometri", "logaritma", "lineer cebir",
             "analitik geometri", "olasılık", "permütasyon-kombinasyon", "kümeler",
             "karmaşık sayılar", "diziler-seriler", "polinom", "fonksiyonlar", "eşitsizlik",
             "mutlak değer-köklü", "sayılar", "problemler", "geometri", "denklem"]


def classify_tr(text: str) -> tuple[str, dict[str, int]]:
    """Return (best_topic, scores). Deterministic keyword scoring with fixed tie-break."""
    low = text.lower()
    scores: dict[str, int] = {}
    for topic, kws in TOPIC_KEYWORDS.items():
        sc = 0
        for kw in kws:
            n = low.count(kw)
            if n:
                sc += n * _WEIGHT.get(kw, max(1, len(kw) // 5 + 1))   # longer phrases / operators weigh more
        if sc:
            scores[topic] = sc
    if not scores:
        return "bilinmiyor", scores
    # generic topics (equation/inequality/function/set) lose to a specific topic that has
    # operator-level evidence (score >= 4: e.g. an explicit sin/cos/∫/lim/log)
    specific = {t: s for t, s in scores.items() if t not in _GENERIC and s >= 4}
    pool = specific if specific else scores
    best = max(pool.values())
    for t in _PRIORITY:
        if pool.get(t) == best:
            return t, scores
    return max(pool, key=pool.get), scores  # pragma: no cover


_GENERIC = {"denklem", "eşitsizlik", "fonksiyonlar", "kümeler"}
