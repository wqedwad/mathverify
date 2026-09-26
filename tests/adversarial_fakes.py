"""Stand-ins for harness.adversarial.attack_item in tests/test_adversarial_parallel.py. A module of
its own because pool workers import the function by name."""
import multiprocessing as mp
import os
import time


def _result(it, verdict: str, timeouts: int = 0, restarts: int = 0, errors: int = 0, base: str = "CORRECT",
            rows: bool = True) -> dict:
    return {"id": it["id"], "base": base, "rows": [("x", "preserving", "CORRECT", verdict)] if rows else [],
            "seconds": 0.0, "sandbox_timeouts": timeouts, "sandbox_restarts": restarts, "sandbox_errors": errors}


def load_dependent(it) -> dict:
    """In a worker a sandbox call times out and the verdict falls to UNKNOWN; alone it holds."""
    in_worker = mp.parent_process() is not None
    return _result(it, "UNKNOWN" if in_worker else "CORRECT", timeouts=int(in_worker))


def load_independent(it) -> dict:
    """The sandbox restarts in a worker, but the rows are the same alone."""
    in_worker = mp.parent_process() is not None
    return _result(it, "CORRECT", restarts=int(in_worker))


def logged(it) -> dict:
    """Takes 0.3 s and appends (where, start, end) to the file named by ADV_FAKE_LOG; item "a"
    restarts its sandbox in a worker, so it is attacked again in the main process."""
    in_worker = mp.parent_process() is not None
    start = time.time()
    time.sleep(0.3)
    with open(os.environ["ADV_FAKE_LOG"], "a", encoding="utf-8") as f:
        f.write(f"{'worker' if in_worker else 'main'} {it['id']} {start} {time.time()}\n")
    return _result(it, "CORRECT", restarts=int(in_worker and it["id"] == "a"))


def base_only(it) -> dict:
    """No attack applies (no rows); in a worker a sandbox error turns the base verdict to UNKNOWN."""
    in_worker = mp.parent_process() is not None
    return _result(it, "CORRECT", errors=int(in_worker), base="UNKNOWN" if in_worker else "CORRECT", rows=False)


def spin(it) -> dict:
    """Keeps its sandbox busy for ten minutes: the sandbox is computing when the sweep is killed."""
    from mathverify.sandbox import get_sandbox
    get_sandbox().call("mathverify.sandbox.ops:spin", 600, timeout=900)
    return _result(it, "CORRECT")
