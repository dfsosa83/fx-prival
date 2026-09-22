#!/usr/bin/env python
"""EXP-2026-08 runner — execute the US30 SELL cost-label notebook headlessly.

ROADMAP-2026-Q4 §9 P1 (equity-index pilot). Runs the forked notebook end-to-end
with nbclient, raising on any cell error. Writes an executed copy into the
experiment folder.

Resilience (carried over from EXP-2026-06 attempt-3 hardening): caps joblib/loky
workers and thread pools so `n_jobs=-1` cannot spawn 8 heavy fits. The notebook
file is untouched — environment only.

Exit code: 0 on success, 1 on any cell error / kernel failure.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "4")
os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")

import nbformat  # noqa: E402
from nbclient import NotebookClient  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]          # ml-signal-service/
FORK = ROOT / "notebooks" / "crosses" / "us30_sell_costlabel.ipynb"
OUT = ROOT / "experiments" / "EXP-2026-08-EQUITY-INDEX-COSTLABEL" / "notebooks" / "us30_sell_costlabel_executed.ipynb"
PER_CELL_TIMEOUT_S = 7200


def main() -> int:
    if not FORK.exists():
        print(f"fork not found: {FORK}")
        return 1

    nb = nbformat.read(FORK, as_version=4)
    OUT.parent.mkdir(parents=True, exist_ok=True)

    print("env guards: LOKY=%s OMP=%s"
          % (os.environ.get("LOKY_MAX_CPU_COUNT"), os.environ.get("OMP_NUM_THREADS")))

    client = NotebookClient(
        nb, timeout=PER_CELL_TIMEOUT_S, kernel_name="python3",
        resources={"metadata": {"path": str(FORK.parent)}},
    )
    try:
        client.execute()
    except Exception as exc:  # noqa: BLE001
        print(f"EXECUTION_FAILED: {type(exc).__name__}: {exc}")
        nbformat.write(nb, OUT)
        return 1

    nbformat.write(nb, OUT)
    print(f"EXECUTION_OK -> {OUT}")

    report = ROOT / "experiments" / "EXP-2026-08-EQUITY-INDEX-COSTLABEL" / "reports" / "US30_sell_test_metrics.json"
    if report.exists():
        print("METRICS_FOUND")
        print(report.read_text(encoding="utf-8"))
    else:
        print("METRICS_MISSING")
    return 0


if __name__ == "__main__":
    sys.exit(main())