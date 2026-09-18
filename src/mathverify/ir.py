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
        _scan_forbidden(d)
        d = dict(d)
        task = d.pop("task")
        if isinstance(task, str):
            task = {"kind": task}
        task_obj = Task(kind=task["kind"], params=dict(task.get("params", {})))
        vars_ = [Var(**v) if isinstance(v, dict) else Var(name=str(v)) for v in d.pop("vars", [])]
        funcs = [FunctionDef(**f) for f in d.pop("functions", [])]
        ops = [Operator(**o) for o in d.pop("operators", [])]
        return cls(task=task_obj, vars=vars_, functions=funcs, operators=ops, **d)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    # convenience -------------------------------------------------------
    def var_names(self) -> list[str]:
        return [v.name for v in self.vars]

    def function_map(self) -> dict[str, FunctionDef]:
        return {f.name: f for f in self.functions}
