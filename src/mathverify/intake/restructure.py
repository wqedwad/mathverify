"""Path (b): external free-text solutions.

Deterministic final-answer extraction only: regex over common Turkish and LaTeX answer
markers. Steps are NOT reconstructed here, so the verifier works at the answer level and the
step layer is skipped. The LLM pass that does reconstruct steps lives in
`extract/restructure_llm.py` and is driven from `pipeline.run_pipeline`.
"""
from __future__ import annotations

import re

from ..normalize.turkish import normalize_numbers_tr
from ..solution import Solution, ClaimedAnswer

_BOXED = re.compile(r"\\boxed\{((?:[^{}]|\{[^{}]*\})*)\}")
_ANSWER_LINE = re.compile(
    r"(?:cevap|sonuç|yanıt|answer|final answer|çözüm kümesi|ç\.k\.?)\s*[:=]\s*([^\n]+?)\s*(?:$|\n)",
    re.IGNORECASE)
_OPTION = re.compile(r"(?:cevap|yanıt|doğru\s+seçenek|şık|seçenek|answer)\s*[:=]?\s*\(?([A-Ea-e])\)?\s*(?:şıkkı|seçeneği)?\b",
                     re.IGNORECASE)
_OPTION_TAIL = re.compile(r"\b([A-E])\s*(?:şıkkı|seçeneği)\b")
_SET = re.compile(r"^\s*\{.*\}\s*$")
# Recovery of a final claim that the answer markers missed. Motivating measurement: for
# "x ∈ {30, 150, 210, 330}. Cevap: B" the extractor kept only the letter and threw the set
# away, so the verifier ended up checking the option against itself and called a wrong
# solution CORRECT. Only unambiguous final-claim shapes are recovered, the LAST one wins, and
# the result is marked advisory (`payload_source="recovered_text"`): it may abstain, never refute.
#
# Deliberately narrow. A first attempt recovered any `<symbol> = <token>` and was measured on
# the 260-item set: 94 recoveries, 59 of them NOT what the solver actually claimed — it picked
# up intermediate steps (`a(2) = 5`) and truncated expressions (`y = 2x + 1` -> `2x`). Only a
# SET or INTERVAL literal is unambiguous enough to recover, and only when the problem asks for
# one, which is also the shape the option letter hides behind.
_RECOVER = re.compile(
    r"(?<![\w])[A-Za-zçğıöşüÇĞİÖŞÜ]\w*\s*(?:∈|=|\bin\b)\s*"
    r"(\{[^{}]+\}|[\(\[][^()\[\]]+,[^()\[\]]+[\)\]])",
    re.IGNORECASE)
_INTERVAL = re.compile(r"^\s*[\(\[][^,]+,[^,]+[\)\]]\s*(?:U\s*[\(\[][^,]+,[^,]+[\)\]]\s*)*$")
_DNE = re.compile(r"\b(limit\s+yoktur|yoktur|mevcut\s+değildir|tanımsızdır|does\s+not\s+exist|DNE)\b", re.IGNORECASE)


def _clean(s: str) -> str:
    s = s.strip().strip(".").strip()
    s = re.sub(r"^\$+|\$+$", "", s).strip()
    s = s.replace("\\,", "").replace("\\ ", " ")
    s = re.sub(r"\\text\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\s*(birim|cm|m|kg|TL|km|saat|dakika|adet|kişi|derece)\s*$", "", s, flags=re.IGNORECASE)
    return s.strip()


def _recover_claim(t: str, answer_shape: str | None) -> str | None:
    """Last `<symbol> ∈ / = <set or interval literal>` in the text, or None.

    Used only when the answer markers produced a bare option letter, and only when the problem
    asks for a set or an interval. A recovery mistake must stay harmless, which is why the
    caller marks the result advisory (`payload_source="recovered_text"`)."""
    if answer_shape not in ("set", "interval"):
        return None
    best = None
    for m in _RECOVER.finditer(t):
        rhs = _clean(m.group(1))
        if rhs:
            best = rhs
    return best


def extract_final_answer(text: str, answer_shape: str | None = None) -> ClaimedAnswer | None:
    """Deterministic final-answer extraction; None when no marker is found.

    `answer_shape` (from the problem IR, never from the solution) disambiguates "(a, b)":
    an interval for set/interval-shaped questions, a point/vector otherwise. Without it,
    the text context decides (interval words / inequality signs), defaulting to interval."""
    if not text:
        return None
    t = normalize_numbers_tr(text)
    option = None
    m = _OPTION.search(t) or _OPTION_TAIL.search(t)
    if m:
        option = m.group(1).upper()
    payload = None
    m = _BOXED.findall(t)
    if m:
        payload = _clean(m[-1])
    else:
        m = _ANSWER_LINE.findall(t)
        if m:
            payload = _clean(m[-1])
            if re.fullmatch(r"\(?[A-Ea-e]\)?", payload or ""):
                option, payload = payload.strip("()").upper(), None
    if payload:
        m2 = re.search(r"\(\s*([A-Ea-e])\s*\)\s*$", payload)
        if m2:
            option = m2.group(1).upper()
            payload = payload[:m2.start()].strip() or None
    source = "solver"
    if payload is None and not _DNE.search(t):
        rec = _recover_claim(t, answer_shape)
        if rec is not None:
            payload, source = rec, "recovered_text"
    if payload is None and option is None:
        if _DNE.search(t):
            return ClaimedAnswer(kind="dne", payload=None, raw=text[-200:])
        return None
    if payload is None:
        return ClaimedAnswer(kind="value", payload=None, option=option, raw=text[-200:])
    if _DNE.search(payload):
        return ClaimedAnswer(kind="dne", payload=None, option=option, raw=payload)
    if _SET.match(payload):
        return ClaimedAnswer(kind="set", payload=payload, option=option, raw=payload,
                             payload_source=source)
    if _INTERVAL.match(payload):
        if answer_shape in ("interval", "set"):
            is_interval = True
        elif answer_shape in ("expression", "scalar", "equation", "count"):
            is_interval = False
        else:
            is_interval = not re.search(r"nokta|vektör|çift|koordinat|matris", t, re.IGNORECASE)
        if is_interval:
            return ClaimedAnswer(kind="interval", payload=payload, option=option, raw=payload,
                                 payload_source=source)
        return ClaimedAnswer(kind="value", payload=payload, option=option, raw=payload,
                             payload_source=source)
    return ClaimedAnswer(kind="value", payload=payload, option=option, raw=payload,
                         payload_source=source)


def restructure_deterministic(text: str, answer_shape: str | None = None) -> Solution | None:
    """`answer_shape` comes from the problem IR and resolves the "(a, b)" ambiguity
    (DECISIONS §16). It was documented as part of path (b) but the pipeline's deterministic
    fallback never forwarded it, so the rule only held inside the LLM path."""
    ca = extract_final_answer(text, answer_shape=answer_shape)
    if ca is None:
        return None
    return Solution(claimed_answer=ca, steps=[], raw_text=text, source="restructured")

