#!/usr/bin/env python
"""EXP-2026-09 runner — US30 TP2.0/SL1.0 geometry redesign, headless execution.

ROADMAP §9. Runs the geom fork end-to-end with nbclient; environment hardening
(LOKY/OMP caps) inherited from EXP-2026-06 attempt-3 lessons. Notebook untouched.
Exit: 0 success, 1 failure.
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

ROOT = Path(__file__).resolve().parents[2]
FORK = ROOT / "notebooks" / "crosses" / "us30_sell_costlabel_geom.ipynb"
OUT = ROOT / "experiments" / "EXP-2026-09-US30-LABEL-GEOMETRY-REDESIGN" / "notebooks" / "us30_sell_costlabel_geom_executed.ipynb"
REPORT = ROOT / "experiments" / "EXP-2026-09-US30-LABEL-GEOMETRY-REDESIGN" / "reports" / "US30_sell_test_metrics.json"
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
    if REPORT.exists():
        print("METRICS_FOUND")
        print(REPORT.read_text(encoding="utf-8"))
    else:
        print("METRICS_MISSING")
    return 0


if __name__ == "__main__":
    sys.exit(main())