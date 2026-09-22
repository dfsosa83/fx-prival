#!/usr/bin/env python
"""EXP-2026-06 runner — execute the BUY cost-label notebook headlessly.

ROADMAP §9 P1. Runs the forked notebook end-to-end with nbclient, raising on
any cell error. Writes an executed copy into the experiment folder.

Reboot/OOM resilience (2026-09-21, attempt 3):
  attempt 1 (15:47Z) was killed by a machine reboot (no artifacts).
  attempt 2 died mid-cell-36 during the XGBoost fold — the notebook hardcodes
  n_jobs=-1 (8 logical / 4 physical cores) and the reboot's re-launched VS Code
  session left ~2.1 GiB free; the kernel was OOM-killed. Root cause is the
  execution environment, NOT the experiment. This runner now caps process
  parallelism (LOKY_MAX_CPU_COUNT caps joblib loky workers; OMP/OpenBLAS caps
  threads inside xgboost/lightgbm) so n_jobs=-1 cannot spawn 8x heavy fits
  again. The notebook file itself is untouched.

Exit code: 0 on success, 1 on any cell error / kernel failure.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# ── Execution-environment guardrails (attempt 3, OOM resilience) ─────────────
# Capped below the machine's logical core count because only ~2 GiB RAM was
# free during attempt 2. These are environment settings only — the notebook
# (labels/features/splits/CV) is byte-identical to production.
os.environ.setdefault("LOKY_MAX_CPU_COUNT", "4")
os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")
os.environ.setdefault("JOBLIB_MULTIPROCESSING", "0")  # deprecation-shield, no-op

import nbformat  # noqa: E402
from nbclient import NotebookClient  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]          # ml-signal-service/
FORK = ROOT / "notebooks" / "eurusd" / "eurusd_buy_costlabel.ipynb"
OUT = ROOT / "experiments" / "EXP-2026-06-EURUSD-BUY-COSTLABEL" / "notebooks" / "eurusd_buy_costlabel_executed.ipynb"

PER_CELL_TIMEOUT_S = 7200  # heavy CV cells can exceed the old 3600s cap


def main() -> int:
    if not FORK.exists():
        print(f"fork not found: {FORK}")
        return 1

    nb = nbformat.read(FORK, as_version=4)
    OUT.parent.mkdir(parents=True, exist_ok=True)

    print("env guards: LOKY_MAX_CPU_COUNT=%s OMP_NUM_THREADS=%s"
          % (os.environ.get("LOKY_MAX_CPU_COUNT"), os.environ.get("OMP_NUM_THREADS")))

    client = NotebookClient(
        nb,
        timeout=PER_CELL_TIMEOUT_S,
        kernel_name="python3",
        resources={"metadata": {"path": str(FORK.parent)}},
    )
    try:
        client.execute()
    except Exception as exc:  # noqa: BLE001 - report any cell/kernel failure
        print(f"EXECUTION_FAILED: {type(exc).__name__}: {exc}")
        nbformat.write(nb, OUT)
        return 1

    nbformat.write(nb, OUT)
    print(f"EXECUTION_OK → {OUT}")

    report = ROOT / "experiments" / "EXP-2026-06-EURUSD-BUY-COSTLABEL" / "reports" / "test_metrics.json"
    if report.exists():
        print("METRICS_FOUND")
        print(report.read_text(encoding="utf-8"))
    else:
        print("METRICS_MISSING (run failed before reporting cell or outputs empty)")
    return 0


if __name__ == "__main__":
    sys.exit(main())