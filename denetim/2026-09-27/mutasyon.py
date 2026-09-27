"""Mutation check of the three fixes of 27 Sep 2026 (DECISIONS §60): the pytest Lean warm-up (L),
the calibration's order and its running score (K), and the appending stage logs of the cloud setup
script (B). The machinery (throwaway clones of the committed HEAD, exit codes, clean-up) is the one
of denetim/2026-09-26/mutasyon.py; only the list of mutations is new.

    .venv/bin/python denetim/2026-09-27/mutasyon.py [-j N] [--list] [name ...]

Kept out of pyflakes and pytest like the rest of denetim/. No string here may name a document.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("mutasyon_0926", HERE.parent / "2026-09-26" / "mutasyon.py")
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

WARM, CONF = "tests/lean_warmup.py", "tests/conftest.py"
CAL, RULES, VER = "harness/calibrate.py", "src/mathverify/fuse/rules.py", "src/mathverify/verifier.py"
SETUP = "scripts/cloud/setup_env.sh"
TW, TF, TC = "tests/test_lean_warmup.py", "tests/test_f6_robustness.py", "tests/test_cloud_scripts.py"

MUTATIONS = [
    # --- Lean warm-up before the first Lean test (B6)
    ("L01 conftest yüklemiyor", CONF, "from lean_warmup import pytest_runtestloop", "import lean_warmup", TW),
    ("L02 açılış bütçesi 300 s", WARM, "BOOT_TIMEOUT = 900.0", "BOOT_TIMEOUT = 300.0", TW),
    ("L03 istemci kapanmıyor", WARM, "        if client is not None:\n            client.close()\n", "        pass\n", TW),
    ("L04 her oturumda ısınma", WARM, " or not any(map(needs_lean, session.items)):", ":", TW),
    ("L05 --collect-only'de ısınma", WARM, "session.config.option.collectonly or ", "", TW),
    ("L06 lean fikstürü tanınmıyor", WARM, 'LEAN_FIXTURES = frozenset({"lean"})', "LEAN_FIXTURES = frozenset()", TW),
    ("L07 _lean yardımcısı tanınmıyor", WARM, 'LEAN_HELPERS = frozenset({"_lean"})', "LEAN_HELPERS = frozenset()", TW),
    ("L08 istisna oturumu düşürür", WARM,
     "    except Exception as e:  # noqa: BLE001  (an absent toolchain is an outcome, not a crash)\n"
     "        return False, time.monotonic() - t0, f\"{type(e).__name__}: {e}\"\n", "", TW),
    ("L09 kanca testleri koşturmaz", WARM, "    return None                 # the default loop runs the tests",
     "    return True", TW),
    ("L10 temiz olmayan sonda hazır sayılır", WARM, "return r.clean, time.monotonic() - t0",
     "return True, time.monotonic() - t0", TW),
    # --- calibration: order and the running score (T4 and its side finding)
    ("K01 ağırlıklar küme sırasıyla", CAL, "    for s in sorted(counts):\n        c = counts[s]\n",
     "    for s, c in counts.items():\n", TF),
    ("K02 eşit ağırlıkta ada göre sıra yok", CAL, 'key=lambda kv: (-abs(kv[1]["weight"]), kv[0])',
     'key=lambda kv: -abs(kv[1]["weight"])', TF),
    ("K03 çalışma anı ek bayrakları görmez", RULES, '    sigs.update(f"flag:{f}" for f in extra_flags)\n', "", TF),
    ("K04 fuse ek bayrakları geçirmez", RULES, "calibrated_score(layers, calib, extra_flags or ())",
     "calibrated_score(layers, calib)", TF),
    ("K05 doğrulayıcı ek bayrakları geçirmez", VER, "fuse(layers, extra_flags=extra_flags)", "fuse(layers)", TF),
    ("K06 harness soldan toplar", CAL, "    return math.fsum(terms)\n",
     "    z = 0.0\n    for t in terms:\n        z += t\n    return z\n", TF),
    ("K07 çalışma anı soldan toplar", RULES, "    return math.fsum(terms)\n",
     "    z = 0.0\n    for t in terms:\n        z += t\n    return z\n", TF),
    # --- setup_env.sh stage logs (B3)
    ("B01 aşama günlüğünün üzerine yazılır", SETUP, '{ stage_header "$*"; "$@"; } >>"$slog" 2>&1',
     '{ stage_header "$*"; "$@"; } >"$slog" 2>&1', TC),
    ("B02 atlanan aşama üzerine yazar", SETUP, 'echo "skipped: $2"; } >>"$LOGDIR/$1.log"',
     'echo "skipped: $2"; } >"$LOGDIR/$1.log"', TC),
    ("B03 alıntı bütün günlükten", SETUP, 'tail -c +"$start" "$slog" 2>/dev/null | tail -n 25',
     'tail -n 25 "$slog" 2>/dev/null', TC),
    ("B04 koşu başlığı yok", SETUP, '{ stage_header "$*"; "$@"; } >>"$slog" 2>&1', '{ "$@"; } >>"$slog" 2>&1', TC),
]

if __name__ == "__main__":
    base.MUTATIONS = MUTATIONS
    sys.exit(base.main())
