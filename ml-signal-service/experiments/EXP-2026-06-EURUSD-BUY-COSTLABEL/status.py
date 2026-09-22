import json
import os
import time
from pathlib import Path

import psutil

ROOT = Path(r"C:\Users\david\OneDrive\Documents\fx-prival\ml-signal-service")
EXP = ROOT / "experiments" / "EXP-2026-06-EURUSD-BUY-COSTLABEL"
METRICS = EXP / "reports" / "test_metrics.json"
EXEC_NB = EXP / "notebooks" / "eurusd_buy_costlabel_executed.ipynb"
FORK = ROOT / "notebooks" / "eurusd" / "eurusd_buy_costlabel.ipynb"

print("=" * 62)
print("EXP-2026-06 BUY training — live status")
print("=" * 62)

# 1) is the runner process alive?
runner = None
for p in psutil.process_iter(["pid", "name", "cmdline"]):
    try:
        cmd = " ".join(p.info["cmdline"] or [])
        if "run_exp.py" in cmd and "EXP-2026-06" in cmd:
            runner = p.info["pid"]
    except (psutil.Error, TypeError):
        pass
print(f"\n[1] runner process  : {'ALIVE (pid=%s)' % runner if runner else 'NOT RUNNING'}")

# 2) kernel + worker CPU activity
kernel = None
busy = []
if runner is not None:
    try:
        rp = psutil.Process(runner)
        for k in rp.children(recursive=False):
            if "ipykernel" in " ".join(k.cmdline() or []) or "run" not in " ".join(k.cmdline() or [])[:8]:
                if "ipykernel" in " ".join(k.cmdline() or []) or k.name() == "python.exe":
                    kernel = k.pid
            for w in psutil.Process(k.pid).children(recursive=False):
                try:
                    c = w.cpu_percent(None)
                    if c and c > 1:
                        busy.append((w.pid, round(c, 1)))
                except psutil.Error:
                    pass
    except psutil.Error:
        pass

# kernel cumulative CPU is the reliable "is it working" signal
kernel_cpu = None
if kernel is not None:
    try:
        ct = psutil.Process(kernel).cpu_times()
        kernel_cpu = ct.user + ct.system
    except psutil.Error:
        pass
if kernel_cpu is not None:
    print(f"[2] kernel CPU-time  : {kernel_cpu:,.0f}s cumulative since launch "
          f"(keeps climbing = executing; flat = stalled)")
else:
    print("[2] kernel           : not found under runner")

if busy:
    print(f"    active workers  : {len(busy)} burning CPU right now")
    for pid, c in busy[:12]:
        print(f"     pid={pid} cpu={c}%")
else:
    print("    active workers  : none > 1% at this instant (normal between CV folds)")

# 3) executed-notebook progress — ONLY meaningful if written AFTER run start
if runner is not None:
    rp = psutil.Process(runner)
    run_start = rp.create_time()
    if EXEC_NB.exists() and os.stat(EXEC_NB).st_mtime > run_start:
        nb = json.loads(EXEC_NB.read_text(encoding="utf-8"))
        last = sum(1 for c in nb["cells"]
                   if c.get("cell_type") == "code" and c.get("execution_count"))
        print(f"[3] furthest cell    : {last}/45 cells (fresh copy — current run)")
    else:
        print("[3] furthest cell    : current run not finished yet (executed "
              "copy is written at the END; any file older than run start is stale)")
else:
    print("[3] furthest cell    : n/a (no runner)")

# 4) artifacts
print(f"[4] test_metrics     : {'EXISTS' if METRICS.exists() else 'not yet (written when DONE)'}")
try:
    bundles = [f for f in os.listdir(ROOT / "models_bin") if "buy_costlabel" in f]
except OSError:
    bundles = []
print(f"[5] model bundle     : {bundles if bundles else 'not yet (written when DONE)'}")

elapsed = None
print("\n[6] how to read this:")
print("    - [1] NOT RUNNING + no metrics = finished or died -> check RUN_LOG")
print("    - [2] busy workers ~100-300% = actively training")
print("    - [3] climbing toward 45 = progressing (cells 36-38 are the CV/ensemble core)")
print("    - [4] [5] appear = DONE, read test_metrics.json")