"""Stand-ins for harness.adversarial.attack_item in tests/test_adversarial_parallel.py. A module of
its own because pool workers import the function by name."""
import multiprocessing as mp


def _result(it, verdict: str, timeouts: int = 0, restarts: int = 0) -> dict:
    return {"id": it["id"], "base": "CORRECT", "rows": [("x", "preserving", "CORRECT", verdict)],
            "seconds": 0.0, "sandbox_timeouts": timeouts, "sandbox_restarts": restarts}


def load_dependent(it) -> dict:
    """In a worker a sandbox call times out and the verdict falls to UNKNOWN; alone it holds."""
    in_worker = mp.parent_process() is not None
    return _result(it, "UNKNOWN" if in_worker else "CORRECT", timeouts=int(in_worker))


def load_independent(it) -> dict:
    """The sandbox restarts in a worker, but the rows are the same alone."""
    in_worker = mp.parent_process() is not None
    return _result(it, "CORRECT", restarts=int(in_worker))
