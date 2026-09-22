#!/usr/bin/env python
"""EXP-2026-05 runner — execute the cost-label notebook headlessly.

ROADMAP §9 P0.1. Runs the forked notebook end-to-end with nbclient, raising on
any cell error so a failed/timed-out run never leaves a "green" appearance.
Writes an executed copy (with outputs) back into the experiment folder.

Use:
    python experiments/EXP-2026-05-EURUSD-SELL-COSTLABEL/run_exp.py

Exit code: 0 on success, 1 on any cell error / kernel failure.
"""

from __future__ import annotations

import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[2]          # ml-signal-service/
FORK = ROOT / "notebooks" / "eurusd" / "eurusd_sell_costlabel.ipynb"
OUT = ROOT / "experiments" / "EXP-2026-05-EURUSD-SELL-COSTLABEL" / "notebooks" / "eurusd_sell_costlabel_executed.ipynb"


def main() -> int:
    if not FORK.exists():
        print(f"fork not found: {FORK}")
        return 1

    nb = nbformat.read(FORK, as_version=4)
    OUT.parent.mkdir(parents=True, exist_ok=True)

    client = NotebookClient(
        nb,
        timeout=3600,           # per-cell cap; H1 training is heavy
        kernel_name="python3",
        resources={"metadata": {"path": str(FORK.parent)}},
    )
    try:
        client.execute()
    except Exception as exc:  # noqa: BLE001 - report any cell/kernel failure
        print(f"EXECUTION_FAILED: {type(exc).__name__}: {exc}")
        nbformat.write(nb, OUT)  # keep partial progress + error traceback
        return 1

    nbformat.write(nb, OUT)
    print(f"EXECUTION_OK → {OUT}")

    # Surface the sealed-test report produced by the last cell if present
    report = ROOT / "experiments" / "EXP-2026-05-EURUSD-SELL-COSTLABEL" / "reports" / "test_metrics.json"
    if report.exists():
        print("METRICS_FOUND")
        print(report.read_text(encoding="utf-8"))
    else:
        print("METRICS_MISSING (run failed before reporting cell or outputs empty)")
    return 0


if __name__ == "__main__":
    sys.exit(main())