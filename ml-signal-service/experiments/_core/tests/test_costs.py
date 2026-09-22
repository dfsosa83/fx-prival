"""Tests for experiments/_core/costs.py.

Roadmap P0.0 validation checks (ROADMAP-2026-Q4-RESEARCH.md §9 P0.0):
- cost in price terms has the correct sign for BUY vs SELL (cost always makes
  the barrier HARDER to reach, never easier).
- plus table/pip-convention sanity.
"""

import pytest

from experiments._core import costs


# ── Pip conventions ───────────────────────────────────────────────────────────

def test_to_price_eurusd_pip_is_1e4():
    assert costs.to_price("EURUSD", 1.0) == pytest.approx(1e-4)


def test_to_price_usdjpy_pip_is_1e2():
    assert costs.to_price("USDJPY", 1.0) == pytest.approx(1e-2)


def test_to_price_xauusd_pip_is_1e2():
    assert costs.to_price("XAUUSD", 1.0) == pytest.approx(1e-2)


def test_to_price_unknown_pair_raises():
    with pytest.raises(KeyError):
        costs.to_price("FAKEPAIR", 1.0)


# ── Barrier sign (the core P0.0 validation check) ────────────────────────────

def test_sell_cost_pushes_barrier_down():
    entry, atr = 1.1000, 0.0008
    base = costs.apply_cost_to_barrier(entry, atr, 1.5, "SELL", 0.0, pair="EURUSD")
    with_cost = costs.apply_cost_to_barrier(entry, atr, 1.5, "SELL", 1.2, pair="EURUSD")
    # SELL TP sits below entry; cost moves it FURTHER below (harder to reach).
    assert with_cost < base


def test_buy_cost_pushes_barrier_up():
    entry, atr = 1.1000, 0.0008
    base = costs.apply_cost_to_barrier(entry, atr, 1.5, "BUY", 0.0, pair="EURUSD")
    with_cost = costs.apply_cost_to_barrier(entry, atr, 1.5, "BUY", 1.2, pair="EURUSD")
    # BUY TP sits above entry; cost moves it FURTHER above (harder to reach).
    assert with_cost > base


def test_cost_never_makes_barrier_easier_either_direction():
    entry, atr, mult = 1.1000, 0.0008, 1.5
    for direction in ("BUY", "SELL"):
        base = costs.apply_cost_to_barrier(entry, atr, mult, direction, 0.0, pair="EURUSD")
        paid = costs.apply_cost_to_barrier(entry, atr, mult, direction, 3.0, pair="EURUSD")
        # distance from entry must be >= when cost is applied
        assert abs(paid - entry) >= abs(base - entry)
        assert abs(paid - entry) > abs(base - entry)  # strictly, for nonzero cost


def test_zero_cost_preserves_base_barrier():
    entry, atr = 1.1000, 0.0008
    assert costs.apply_cost_to_barrier(entry, atr, 1.5, "SELL", 0.0, pair="EURUSD") == pytest.approx(
        entry - 1.5 * atr
    )
    assert costs.apply_cost_to_barrier(entry, atr, 1.5, "BUY", 0.0, pair="EURUSD") == pytest.approx(
        entry + 1.5 * atr
    )


def test_pip_size_override_without_pair():
    entry, atr = 1.1000, 0.0008
    via_pair = costs.apply_cost_to_barrier(entry, atr, 1.5, "BUY", 1.2, pair="EURUSD")
    via_size = costs.apply_cost_to_barrier(entry, atr, 1.5, "BUY", 1.2, pip_size=1e-4)
    assert via_pair == pytest.approx(via_size)


def test_apply_cost_requires_pair_or_pip_size():
    with pytest.raises(ValueError):
        costs.apply_cost_to_barrier(1.1000, 0.0008, 1.5, "BUY", 1.2)


def test_invalid_direction_raises():
    with pytest.raises(ValueError):
        costs.apply_cost_to_barrier(1.1000, 0.0008, 1.5, "LONG", 1.2, pair="EURUSD")


# ── Cost table consistency ────────────────────────────────────────────────────

def test_cost_table_and_pip_conventions_cover_all_measured_pairs():
    for pair in costs.MEASURED_SPREAD_PIPS:
        assert pair in costs.PIP_SIZE_PX, f"{pair} has a measured spread but no pip convention"
        assert callable(costs.cost_pips)
        assert costs.cost_pips(pair, "ALL") == costs.MEASURED_SPREAD_PIPS[pair]

def test_cost_pips_flat_and_non_negative():
    for pair in costs.MEASURED_SPREAD_PIPS:
        for session in costs.SESSIONS:
            assert costs.cost_pips(pair, session) >= costs.MEASURED_SPREAD_PIPS[pair]
            assert costs.cost_pips(pair, session) >= 0.0


def test_exp2026_08_index_cfds_configured():
    """Index CFDs must have pip conventions + measured spreads (EXP-2026-08)."""
    for pair, px_spread in [("US30", 3.2), ("US100", 0.6)]:
        assert pair in costs.PIP_SIZE_PX
        # measured spread stored in points: px / 0.01
        assert costs.MEASURED_SPREAD_PIPS[pair] == px_spread / 0.01
        assert costs.cost_pips(pair, "ALL") == px_spread / 0.01
    assert costs.PIP_SIZE_PX["US30"] == 1e-2
    assert costs.PIP_SIZE_PX["US100"] == 1e-2


def test_exp2026_07_crosses_configured():
    """The liquid-cross book pairs must have pip conventions + measured spreads."""
    for pair, pips in [("EURGBP", 4.7), ("GBPJPY", 13.6), ("EURJPY", 10.6)]:
        assert pair in costs.PIP_SIZE_PX, f"{pair} missing pip convention"
        assert costs.MEASURED_SPREAD_PIPS[pair] == pips, f"{pair} spread mismatch"
        assert costs.cost_pips(pair, "ALL") == pips
    # JPY-cross pip sizes are 3-decimal
    assert costs.PIP_SIZE_PX["GBPJPY"] == 1e-2
    assert costs.PIP_SIZE_PX["EURJPY"] == 1e-2
    assert costs.PIP_SIZE_PX["EURGBP"] == 1e-4


def test_unknown_session_raises():
    with pytest.raises(KeyError):
        costs.cost_pips("EURUSD", "MIDNIGHT")


def test_unknown_pair_cost_raises():
    with pytest.raises(KeyError):
        costs.cost_pips("FAKEPAIR")


def test_set_slippage_updates_round_trip():
    costs.set_slippage_pips("EURUSD", 0.5)
    try:
        assert costs.cost_pips("EURUSD", "ALL") == pytest.approx(1.2 + 0.5)
        # nested table stays consistent with the accessor
        assert costs.ROUND_TRIP_COST_PIPS["EURUSD"]["ALL"] == pytest.approx(1.2 + 0.5)
    finally:
        # restore so other tests are not affected by mutation
        costs.set_slippage_pips("EURUSD", 0.0)
    assert costs.cost_pips("EURUSD", "ALL") == pytest.approx(1.2)
    assert costs.ROUND_TRIP_COST_PIPS["EURUSD"]["ALL"] == pytest.approx(1.2)


def test_round_trip_table_shape_matches_roadmap():
    # dict[pair][session]: every measured pair has every session key,
    # and all values are >= the measured spread for that pair.
    for pair, sessions in costs.ROUND_TRIP_COST_PIPS.items():
        assert set(sessions) == set(costs.SESSIONS)
        for session, pips in sessions.items():
            assert pips == costs.cost_pips(pair, session)
            assert pips >= costs.MEASURED_SPREAD_PIPS[pair]


def test_set_slippage_negative_rejected():
    with pytest.raises(ValueError):
        costs.set_slippage_pips("EURUSD", -0.1)