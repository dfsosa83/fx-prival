#!/usr/bin/env python
"""Phase 1B retrieval — XAUUSD M15 + H1 historical bars (read-only).

Chunked copy_rates_range retrieval to avoid terminal-wide-request stalls.
No login(). No settings changes. Incremental writes + SHA-256 provenance.
"""
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, ".")
import MetaTrader5 as mt5
from dotenv import load_dotenv

BASE = Path("quant-personal-fund/experiments/EXP-2026-05-INVALIDATION-REVERSAL/audits/PHASE-1B")
RAW_M15 = BASE / "data/raw/m15"
RAW_H1 = BASE / "data/raw/h1"
for d in (RAW_M15, RAW_H1):
    d.mkdir(parents=True, exist_ok=True)

load_dotenv(Path("frival/execution_bot/config/credentials.env"))
TERMINAL = os.getenv("MT5_TERMINAL_PATH") or r"C:\Program Files\FPMarkets MT5 Terminal\terminal64.exe"

START = datetime(2020, 1, 1, tzinfo=timezone.utc)
END = datetime(2026, 9, 24, tzinfo=timezone.utc)  # latest fully completed available
CHUNK_DAYS = 120
SYMBOL = "XAUUSD"


def account_state():
    info = mt5.account_info()
    pos = mt5.positions_get()
    ords = mt5.orders_get()
    return {"login": info.login, "server": info.server,
            "balance": info.balance, "equity": info.equity,
            "n_pos": len(pos) if pos is not None else None,
            "n_orders": len(ords) if ords is not None else None}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


if not mt5.initialize(path=TERMINAL):
    print(json.dumps({"fatal": f"initialize failed: {mt5.last_error()}"}))
    sys.exit(1)

pre = account_state()
log = {"login_called": False, "session_pre": pre, "chunks": [], "errors": []}
provenance = {}

try:
    for tf_name, tf_attr, outdir in [
        ("M15", mt5.TIMEFRAME_M15, RAW_M15),
        ("H1", mt5.TIMEFRAME_H1, RAW_H1),
    ]:
        tf = tf_attr
        cursor = START
        chunk_idx = 0
        while cursor < END:
            chunk_end = min(cursor + timedelta(days=CHUNK_DAYS), END)
            fname = f"XAUUSD_{tf_name}_{cursor.strftime('%Y%m%d')}_{chunk_end.strftime('%Y%m%d')}.parquet"
            fpath = outdir / fname
            if fpath.exists():
                log["chunks"].append({"tf": tf_name, "file": fname, "skipped_exists": True})
                cursor = chunk_end
                chunk_idx += 1
                continue
            rates = mt5.copy_rates_range(SYMBOL, tf, cursor, chunk_end)
            if rates is None or len(rates) == 0:
                log["chunks"].append({"tf": tf_name, "from": str(cursor), "to": str(chunk_end),
                                      "rows": 0, "error": str(mt5.last_error())})
            else:
                df = pd.DataFrame(rates)
                df["time_utc"] = pd.to_datetime(df["time"], unit="s", utc=True)
                df.to_parquet(fpath, index=False)
                log["chunks"].append({"tf": tf_name, "from": str(cursor), "to": str(chunk_end),
                                      "rows": int(len(df))})
                provenance[str(fpath.relative_to(BASE))] = sha256(fpath)
                # brief pause between chunks to avoid hammering the terminal
                time.sleep(0.3)
            cursor = chunk_end
            chunk_idx += 1
finally:
    post = account_state()
    log["session_post"] = post
    log["session_unchanged"] = {
        k: pre.get(k) == post.get(k)
        for k in ["login", "server", "balance", "equity", "n_pos", "n_orders"]
    }
    (BASE / "RETRIEVAL_LOG.json").write_text(json.dumps(log, indent=2, default=str), encoding="utf-8")
    (BASE / "RAW_PROVENANCE.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    mt5.shutdown()

print(json.dumps({
    "login_called": False,
    "session_unchanged": log["session_unchanged"],
    "chunk_count": len([c for c in log["chunks"] if not c.get("skipped_exists")]),
    "errors": log["errors"],
}, indent=2))