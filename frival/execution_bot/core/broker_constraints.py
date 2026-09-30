# -*- coding: utf-8 -*-
"""EXEC-D1 broker-constraint gate — CORRECTED MT5 property mapping (offline).

Mandatory corrections applied (2026-09-28, offline; no MT5 runtime call):
  1. The symbol-metadata API for the installed SDK (`MetaTrader5 5.0.4874`,
     pinned repo `MetaTrader5>=5.0.45`) is **`mt5.symbol_info(symbol)`**.
     `symbol_info_get` does NOT exist in this build and the project defines no
     wrapper of that name, so nothing in this package references it.
  2. The REAL SymbolInfo field names (verified by introspecting the installed
     kit's SymbolInfo record at the module level, WITHOUT connecting):
       trade_stops_level   - minimum stop/pending order distance (stops level)
       trade_freeze_level  - freeze level (SL/TP modification freeze threshold)
       filling_mode        - permitted filling modes
       expiration_mode     - permitted expiration (time-in-force) modes
       order_mode          - permitted order types (incl. pending order types)
       order_gtc_mode      - GTC time-in-force ordering modes (related)
  3. `margin_stop`, `margin_freeze` and `fill_mode` are INVALID assumed names.
     They are NOT present in the installed kit's SymbolInfo record and are NOT
     internal aliases mapped anywhere in this codebase. The gate never reads
     them; it reads `trade_stops_level` / `trade_freeze_level` directly.
     `margin_initial` / `margin_maintenance` are real margin fields but are not
     execution gates and are not used as such.

Fail-closed contract (unchanged):
  - `enabled` must be False in demo/paper (EXEC-D1 scope). It only becomes True
    as part of a FUTURE, explicitly approved MT5 integration.
  - When enabled, missing, malformed (non-numeric / negative) or otherwise
    unsupported required metadata BLOCKS the operation. No default is invented.
  - Synthetic tests verify the mapping, ordering and fail-closed behavior of
    this module; they do NOT verify broker-specific runtime values/semantics.
    Live validation requires a separate explicit authorization.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

# Runtime probe --------------------------------------------------------------
_MT5_IMPORT_AVAILABLE = None


def _import_mt5():
    global _MT5_IMPORT_AVAILABLE
    if _MT5_IMPORT_AVAILABLE is None:
        try:
            import MetaTrader5  # noqa: F401  (module import only; NO initialize)
            _MT5_IMPORT_AVAILABLE = True
        except Exception as exc:  # ModuleNotFoundError and friends
            _MT5_IMPORT_AVAILABLE = repr(exc)
    return _MT5_IMPORT_AVAILABLE


def mt5_import_status() -> str:
    """'AVAILABLE' | 'UNAVAILABLE: <reason>' — never connects to a terminal."""
    status = _import_mt5()
    return "AVAILABLE" if status is True else f"UNAVAILABLE: {status}"


def symbol_api_name(module=None) -> str:
    """Return the verified symbol-metadata API name used by this package.

    The installed/documented call is `symbol_info`. Internally we PREFER that
    name and treat any other spelling (e.g. `symbol_info_get`) as invalid for
    this codebase unless a clearly defined project wrapper exists (it does
    not). Never connects; module-level inspection only.
    """
    if module is not None:
        if hasattr(module, "symbol_info"):
            return "symbol_info"
        return "<absent: symbol_info not found in provided module>"
    status = _import_mt5()
    if status is True:
        import MetaTrader5  # module import only (no terminal)
        if hasattr(MetaTrader5, "symbol_info"):
            return "symbol_info"
    return "<verification required at connect time>"


UNVERIFIED = "UNVERIFIED"
AVAILABLE = "AVAILABLE"
UNAVAILABLE = "UNAVAILABLE"

# ── Corrected field mapping (verified against installed MetaTrader5 5.0.4874) ─

# REAL, documented SymbolInfo fields relevant to pending-order constraints.
REAL_SYMBOL_FIELDS = frozenset({
    "trade_stops_level",      # minimum stop distance
    "trade_freeze_level",     # freeze level
    "filling_mode",           # permitted filling modes
    "expiration_mode",        # permitted expiration modes
    "order_mode",             # permitted order types
    "order_gtc_mode",         # GTC time-in-force ordering
    "margin_initial",         # REAL but not an execution gate
    "margin_maintenance",     # REAL but not an execution gate
    "point", "digits", "volume_min", "volume_max",
})

# Assumed names that are NOT real MT5 SymbolInfo fields in this kit and are NOT
# internal aliases mapped to a real field by this codebase. The gate never
# reads them.
INVALID_ASSUMED_FIELDS = frozenset({
    "margin_stop",     # absent from SymbolInfo; no alias mapping defined
    "margin_freeze",   # absent from SymbolInfo; freeze = trade_freeze_level
    "fill_mode",       # absent from SymbolInfo; filling = filling_mode
})

BROKER_CONSTRAINT_UNVERIFIED = "BROKER_CONSTRAINT_UNVERIFIED"
BROKER_CONSTRAINT_MALFORMED = "BROKER_CONSTRAINT_MALFORMED"
FREEZE_UNVERIFIED = "FREEZE_UNVERIFIED"
MIN_STOP_VIOLATION = "MIN_STOP_DISTANCE_VIOLATION"
ORDER_TYPE_NOT_EMITTABLE = "ORDER_TYPE_NOT_EMITTABLE"
OK = "OK"


@dataclass
class Evaluation:
    ok: bool
    code: str
    detail: str = ""
    mode: str = "demo_skipped"


def field_classification(name: str) -> str:
    """Classify a property name per the corrected MT5 field audit.

    Returns REAL_SYMBOL_FIELD | NOT_AN_MT5_FIELD | UNVERIFIED. `margin_stop`,
    `margin_freeze` and `fill_mode` classify as NOT_AN_MT5_FIELD because they
    are neither fields of the installed SymbolInfo record nor internal aliases
    mapped to a real field. `filling_mode` / `expiration_mode` classify as
    REAL_SYMBOL_FIELD.
    """
    if name in REAL_SYMBOL_FIELDS:
        return "REAL_SYMBOL_FIELD"
    if name in INVALID_ASSUMED_FIELDS:
        return "NOT_AN_MT5_FIELD"
    return "UNVERIFIED"


def introspect_symbol_info_fields(symbol_info: Any) -> Dict[str, str]:
    """Introspect actual field names of a live SymbolInfo record.

    Returns {field: AVAILABLE} for every field actually present; a field listed
    in REAL_SYMBOL_FIELDS that is absent is recorded as UNAVAILABLE. Nothing is
    invented: unknown keys are reported as present/absent as observed.
    """
    result: Dict[str, str] = {}
    if symbol_info is None:
        return {name: UNAVAILABLE for name in REAL_SYMBOL_FIELDS}
    try:
        present = set(symbol_info._fields)
    except Exception:
        present = {n for n in REAL_SYMBOL_FIELDS
                   if getattr(symbol_info, n, None) is not None}
    if not present:
        return {name: UNVERIFIED for name in REAL_SYMBOL_FIELDS}
    for name in sorted(REAL_SYMBOL_FIELDS | set(present)):
        result[name] = AVAILABLE if name in present else UNAVAILABLE
    return result


class BrokerConstraintGate:
    """Fail-safe pending-order constraint gate (corrected MT5 field mapping).

    Reads ONLY the real SymbolInfo fields `trade_stops_level` and
    `trade_freeze_level` (plus the documented `filling_mode` /
    `expiration_mode` / `order_mode` are recorded, not gate inputs). It never
    reads `margin_stop`, `margin_freeze` or `fill_mode`. If a required property
    is missing or malformed the gate BLOCKS; no default is invented.
    """

    REQUIRED_FOR_STOP = ("trade_stops_level",)

    def __init__(self, *,
                 enabled: bool = False,
                 symbol_info_provider: Optional[Callable[[str], Any]] = None,
                 freeze_level_provider: Optional[Callable[[], Any]] = None):
        self.enabled = enabled
        self.symbol_info_provider = symbol_info_provider
        self.freeze_level_provider = freeze_level_provider
        self._probe_path = mt5_import_status()

    @staticmethod
    def _as_number(value, field: str):
        """Return float(value) or raise for malformed metadata."""
        try:
            f = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"{field} malformed: {type(value).__name__} not numeric"
            ) from exc
        if f < 0:
            raise ValueError(f"{field} malformed: negative value {f}")
        return f

    def evaluate(self, *, order_type: str, trigger_level: float,
                 executable_quote: float, symbol: str,
                 points_per_unit: float = 100000.0) -> Evaluation:
        """Returns OK (pass) or a BLOCK code. Only SELL_STOP/BUY_STOP reach
        this gate (lifecycle enforces); any other order_type is rejected here.

        `points_per_unit` converts the price difference into broker POINTS (the
        smallest price unit: 100000 for 5-digit EURUSD) because MT5 reports
        stops levels in points, not 4-digit pips.
        """
        if not self.enabled:
            return Evaluation(ok=True, code=OK,
                              detail=f"gate disabled (demo/paper); probe={self._probe_path}",
                              mode="demo_skipped")

        if order_type not in ("SELL_STOP", "BUY_STOP"):
            return Evaluation(ok=False, code=ORDER_TYPE_NOT_EMITTABLE,
                              detail=f"{order_type} not permitted by EXEC-D1",
                              mode="mt5_gate")

        if self.symbol_info_provider is None:
            return Evaluation(ok=False, code=BROKER_CONSTRAINT_UNVERIFIED,
                              detail="no symbol_info provider configured; cannot verify min-stop.",
                              mode="mt5_gate")

        try:
            si = self.symbol_info_provider(symbol)
        except Exception as exc:
            self._last_detail = f"symbol_info_provider raised: {exc!r}"
            si = None
        if si is None:
            return Evaluation(ok=False, code=BROKER_CONSTRAINT_UNVERIFIED,
                              detail="symbol_info unavailable; min-stop distance unverified.",
                              mode="mt5_gate")

        # Minimum stop distance: real field trade_stops_level (NOT margin_stop).
        stops_level = getattr(si, "trade_stops_level", None)
        if stops_level is None:
            return Evaluation(ok=False, code=BROKER_CONSTRAINT_UNVERIFIED,
                              detail="symbol_info.trade_stops_level is absent; min-stop unverified.",
                              mode="mt5_gate")
        try:
            stops_level_f = self._as_number(stops_level, "trade_stops_level")
        except ValueError as exc:
            return Evaluation(ok=False, code=BROKER_CONSTRAINT_MALFORMED,
                              detail=str(exc), mode="mt5_gate")

        # Freeze level: real field trade_freeze_level (NOT margin_freeze).
        # Account-level provider kept as an optional secondary source.
        freeze = getattr(si, "trade_freeze_level", None)
        if freeze is None and self.freeze_level_provider is not None:
            try:
                freeze = self.freeze_level_provider()
            except Exception:
                freeze = None
        if freeze is None:
            return Evaluation(ok=False, code=FREEZE_UNVERIFIED,
                              detail="symbol_info.trade_freeze_level not available; freeze unverified.",
                              mode="mt5_gate")
        try:
            self._as_number(freeze, "trade_freeze_level")
        except ValueError as exc:
            return Evaluation(ok=False, code=BROKER_CONSTRAINT_MALFORMED,
                              detail=str(exc), mode="mt5_gate")

        if stops_level_f > 0:
            distance_points = abs(executable_quote - trigger_level) * points_per_unit
            if distance_points < stops_level_f:
                return Evaluation(ok=False, code=MIN_STOP_VIOLATION,
                                  detail=(
                                      f"trigger level {trigger_level} within min stop "
                                      f"distance ({stops_level_f} pts); distance "
                                      f"{distance_points:.2f} pts."
                                  ),
                                  mode="mt5_gate")
        return Evaluation(ok=True, code=OK,
                          detail="real symbol fields trade_stops_level / "
                                 "trade_freeze_level verified",
                          mode="mt5_gate")


def documented_property_map() -> Dict[str, Dict[str, str]]:
    """Human-readable map for reports: field -> (meaning, classification)."""
    import_flavor = mt5_import_status()
    out: Dict[str, Dict[str, str]] = {}
    meaning = {
        "trade_stops_level": "minimum stop distance (verified on installed SDK)",
        "trade_freeze_level": "freeze level (SL/TP modification freeze threshold)",
        "filling_mode": "permitted filling modes",
        "expiration_mode": "permitted expiration (time-in-force) modes",
        "order_mode": "permitted order types (incl. pending order types)",
        "order_gtc_mode": "GTC time-in-force ordering",
        "margin_initial": "initial margin (not an execution gate)",
        "margin_maintenance": "maintenance margin (not an execution gate)",
    }
    for name in sorted(REAL_SYMBOL_FIELDS):
        out[name] = {
            "meaning": meaning.get(name, "real symbol-info field"),
            "verification": AVAILABLE if "AVAILABLE" in import_flavor else UNAVAILABLE,
            "classification": field_classification(name),
        }
    for name in sorted(INVALID_ASSUMED_FIELDS):
        out[name] = {
            "meaning": "NOT an MT5 SymbolInfo field in the installed kit and NOT "
                       "an internal alias mapped to a real field; never read",
            "verification": UNAVAILABLE,
            "classification": field_classification(name),
        }
    return out