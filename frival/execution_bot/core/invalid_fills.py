# -*- coding: utf-8 -*-
"""EXEC-D1 D-9 — invalid-fill exclusion manifest (migration of 2026-09-28).

The two 2026-09-28 EURUSD FIRED signals were processed by the PRE-D1 demo
simulator, which filled at the nominal entry price without a qualifying quote
touch (order_manager.py demo branch: simulated success, price = prepared price).
Evidence in execution_log.jsonl (2026-09-28T16:03:22Z and 17:03:16Z):
  - 16:00Z fill 1.13648 at the zone edge was a real quote touch, but the virtual
    bookkeeping entered at the nominal 1.13628;
  - 17:00Z fill 1.13641 while the live quote was 1.13713 (7.2 pips outside the
    entry zone [1.13661, 1.13621]) — a synthetic fill with no qualifying touch.

Neither position ever closed and no ledger record exists, so their outcomes are
unknown and must NEVER be reconstructed. D-9: both are tagged
INVALID_SYNTHETIC_FILL_NO_OUTCOME and excluded from every PnL/performance
metric. This module is the single source of that exclusion contract.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

INVALID_STATE = "INVALID_SYNTHETIC_FILL_NO_OUTCOME"

MANIFEST_PATH = Path(__file__).resolve().parents[1] / "data" / "invalid_signal_ids.json"

# Canonical default entries — never reconstructed, never counted (D-9).
DEFAULT_ENTRIES = [
    {
        "signal_id": "EURUSD_H1_SELL_2026-09-28T16:00:00Z",
        "ticket": "DEMO-1790611402310",
        "state": INVALID_STATE,
        "date": "2026-09-28",
        "reason": (
            "Pre-D1 simulator: virtual position booked at nominal entry 1.13628 "
            "while actual fill quote was 1.13648; outcome never resolved/recorded."
        ),
    },
    {
        "signal_id": "EURUSD_H1_SELL_2026-09-28T17:00:00Z",
        "ticket": "DEMO-1790614996372",
        "state": INVALID_STATE,
        "date": "2026-09-28",
        "reason": (
            "Pre-D1 simulator: synthetic instant fill at nominal 1.13641 with no "
            "qualifying zone touch; live quote 1.13713 was 7.2 pips outside the "
            "entry zone [1.13661, 1.13621]; outcome never resolved/recorded."
        ),
    },
]


def load_manifest(path=None) -> Dict[str, Dict[str, Any]]:
    """Load the exclusion manifest: {signal_id -> record}. Missing/malformed
    manifest fails SAFE: an IO/JSON error must not silently re-admit invalid
    fills, so it raises."""
    p = Path(path) if path else MANIFEST_PATH
    if not p.exists():
        raise FileNotFoundError(
            f"invalid-fill manifest not found: {p}. Metrics must not run without "
            f"the exclusion manifest (D-9)."
        )
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    entries = data.get("entries", [])
    return {e["signal_id"]: e for e in entries}


def is_excluded(signal_id: str, manifest: Dict[str, Dict[str, Any]] = None) -> bool:
    """True if the signal is tagged INVALID_SYNTHETIC_FILL_NO_OUTCOME (D-9)."""
    manifest = manifest if manifest is not None else load_manifest()
    return signal_id in manifest


def partition(records: List[Dict[str, Any]],
              manifest: Dict[str, Dict[str, Any]] = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Split lifecycle/metric records into (valid, excluded) by signal_id.

    EXEC-D1 metrics contract: all downstream PnL/performance aggregation MUST
    call this and use only `valid`. The `excluded` set is reported separately
    and never fed into performance statistics.
    """
    manifest = manifest if manifest is not None else load_manifest()
    excluded = [r for r in records if r.get("signal_id") in manifest]
    valid = [r for r in records if r.get("signal_id") not in manifest]
    return valid, excluded


def assert_no_reconstruction(closed_records: List[Dict[str, Any]],
                             manifest: Dict[str, Dict[str, Any]] = None) -> None:
    """Guard: no closed lifecycle record may exist for an invalid signal id."""
    manifest = manifest if manifest is not None else load_manifest()
    bad = [r for r in closed_records if r.get("signal_id") in manifest]
    if bad:
        raise AssertionError(
            f"reconstructed outcome detected for invalid fills: "
            f"{[r['signal_id'] for r in bad]} (D-9 violation)"
        )