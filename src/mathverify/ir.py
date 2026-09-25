"""Problem IR (handoff §5) with answer-key isolation (D2) enforced structurally.

The IR has NO gold_answer field. `ProblemIR.from_dict` raises LeakageError if any
key that smells like an answer key appears anywhere in the payload (recursively).
`domain_of_discourse` is a first-class field: it comes from the *problem*, never
from the expressions (E4).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

FORBIDDEN_KEYS = frozenset({
    "gold_answer", "gold", "answer_key", "key", "expected_answer", "expected",
    "correct_option", "correct_answer", "solution_is_correct", "first_bad_step",
    "cell", "label", "ground_truth", "truth",
})


class LeakageError(ValueError):
    """Raised when answer-key material reaches the verification pipeline."""


class MalformedIR(ValueError):
    """The problem IR does not have the documented shape (a field that must be text is a list or a
    dict, a task kind that is not text...). Measured 25 Sep 2026: a dict where an expression
    belongs reached `sympify`, which evaluated the strings inside it (code ran), and a list as the
    task kind escaped `verify` as a TypeError. The verifier abstains on it."""


def _text(v: Any, where: str, optional: bool = False) -> None:
    if v is None and optional:
        return
    if not isinstance(v, str):
        raise MalformedIR(f"{where} must be text, got {type(v).__name__}")


def _texts(v: Any, where: str) -> None:
    if not isinstance(v, list):
        raise MalformedIR(f"{where} must be a list of texts, got {type(v).__name__}")
    for i, x in enumerate(v):
        _text(x, f"{where}[{i}]")


def _check_shape(d: dict[str, Any]) -> None:
    task = d.get("task")
    if isinstance(task, dict):
        _text(task.get("kind"), "task.kind")
        if not isinstance(task.get("params", {}), dict):
            raise MalformedIR("task.params must be an object")
    elif not isinstance(task, str):
        raise MalformedIR("task must be an object or a kind")
    for k in ("givens", "sanity"):
        if k in d:
            _texts(d[k], k)
    for k in ("unknown_of_interest", "answer_shape", "units", "domain_of_discourse", "topic", "level",
              "question_en"):
        if k in d:
            _text(d[k], k, optional=True)
    for i, v in enumerate(d.get("vars", []) or []):
        if isinstance(v, dict):
            _text(v.get("name"), f"vars[{i}].name")
            _text(v.get("domain", "real"), f"vars[{i}].domain")
            _texts(v.get("constraints", []), f"vars[{i}].constraints")
        elif not isinstance(v, str):
            raise MalformedIR(f"vars[{i}] must be an object or a name")
    for i, f in enumerate(d.get("functions", []) or []):
        if not isinstance(f, dict):
            raise MalformedIR(f"functions[{i}] must be an object")
        _text(f.get("name"), f"functions[{i}].name")
        _text(f.get("expr"), f"functions[{i}].expr")
        _texts(f.get("args", ["x"]), f"functions[{i}].args")
        _texts(f.get("params", []), f"functions[{i}].params")
        _text(f.get("domain"), f"functions[{i}].domain", optional=True)
    opts = d.get("options")
    if opts is not None:
        if not isinstance(opts, dict):
            raise MalformedIR("options must be an object")
        for k, v in opts.items():
            if isinstance(v, bool) or not isinstance(v, (str, int, float)):
                raise MalformedIR(f"options[{k!r}] must be text or a number")


def _scan_forbidden(obj: Any, path: str = "") -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str) and k.lower() in FORBIDDEN_KEYS:
                raise LeakageError(
                    f"forbidden key {k!r} at {path or '<root>'} (D2 answer-key isolation)")
            _scan_forbidden(v, f"{path}.{k}" if path else str(k))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            _scan_forbidden(v, f"{path}[{i}]")


VAR_DOMAINS = {
    "real", "positive_real", "nonneg_real", "integer", "positive_integer",
    "nonneg_integer", "natural", "rational", "complex",
}

ANSWER_SHAPES = {
    "scalar", "expression", "set", "interval", "condition_on_param",
    "count", "proof", "equation", "dne_or_scalar",
}


@dataclass
class Var:
    name: str
    domain: str = "real"
    constraints: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.domain not in VAR_DOMAINS:
            raise ValueError(f"unknown var domain {self.domain!r} for {self.name}")


@dataclass
class FunctionDef:
    name: str
    expr: str
    args: list[str] = field(default_factory=lambda: ["x"])
    domain: str | None = None
    params: list[str] = field(default_factory=list)


@dataclass
class Operator:
    kind: str                       # integral | derivative | limit | sum | ...
    arg: str
    wrt: str | None = None
    bounds: list[str] | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    """Router key. `kind` selects the certificate modules; `params` are kind-specific."""
    kind: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProblemIR:
    task: Task
    vars: list[Var] = field(default_factory=list)
    givens: list[str] = field(default_factory=list)
    functions: list[FunctionDef] = field(default_factory=list)
    operators: list[Operator] = field(default_factory=list)
    unknown_of_interest: str | None = None
    answer_shape: str = "scalar"
    options: dict[str, str] | None = None
    units: str | None = None
    sanity: list[str] = field(default_factory=list)
    domain_of_discourse: str | None = None
    topic: str | None = None          # informational; router uses task.kind
    level: str | None = None          # TYT | AYT | UNI (informational)
    question_en: str | None = None    # canonical internal statement (optional)

    def __post_init__(self):
        if self.answer_shape not in ANSWER_SHAPES:
            raise ValueError(f"unknown answer_shape {self.answer_shape!r}")
        if self.options is not None:
            self.options = {str(k).upper(): str(v) for k, v in self.options.items()}

    # ------------------------------------------------------------------
    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ProblemIR":
        _scan_forbidden(d)                        # LeakageError first: it is never downgraded
        if not isinstance(d, dict):
            raise MalformedIR("the problem IR must be an object")
        _check_shape(d)
        d = dict(d)
        try:
            task = d.pop("task")
            if isinstance(task, str):
                task = {"kind": task}
            task_obj = Task(kind=task["kind"], params=dict(task.get("params", {})))
            vars_ = [Var(**v) if isinstance(v, dict) else Var(name=str(v)) for v in d.pop("vars", [])]
            funcs = [FunctionDef(**f) for f in d.pop("functions", [])]
            ops = [Operator(**o) for o in d.pop("operators", [])]
            return cls(task=task_obj, vars=vars_, functions=funcs, operators=ops, **d)
        except LeakageError:
            raise
        except (TypeError, ValueError, KeyError) as e:   # unknown field, domain, answer_shape
            raise MalformedIR(f"problem IR: {e}") from e

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    # convenience -------------------------------------------------------
    def var_names(self) -> list[str]:
        return [v.name for v in self.vars]

    def function_map(self) -> dict[str, FunctionDef]:
        return {f.name: f for f in self.functions}
