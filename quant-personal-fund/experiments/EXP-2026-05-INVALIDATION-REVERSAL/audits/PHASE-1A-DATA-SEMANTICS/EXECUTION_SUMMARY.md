# EXECUTION SUMMARY — PHASE-1A-DATA-SEMANTICS

**Experiment:** EXP-2026-05-INVALIDATION-REVERSAL  
**Audit:** PHASE-1A-DATA-SEMANTICS  
**Date:** 2026-09-24  
**Status:** COMPLETE — read-only; no Phase 1 strategy work occurred.

---

## 1. Verdicts

| Item | Verdict |
|---|---|
| **Spread units** | **GO** — points; `spread_price = spread_points × point` (verified vs live tick across 3 symbols) |
| **Timezone** | **GO** — UTC-aligned bar timestamps (100% of sample) |
| **Rollover/maintenance** | **GO (observed)** — XAUUSD ~23:45→01:00 UTC daily; **corrects the manifest's ~21–22 UTC candidate** |
| **Calendar** | **HOLD** — FX sessions observed 24/5; holiday/early-close calendar needs broker confirmation |
| **FX contract specs** | **HOLD** — not exposed by terminal API; XAUUSD 100 oz/lot from prior pre-flight; FX sizes need broker |

---

## 2. Key Findings

### Spread units (resolved)
- Live tick spread = `spread_field × point` for all three symbols:
  - XAUUSD: 19 pts × 0.01 = $0.19 (live 0.1900) ✓
  - EURUSD: 11–12 pts × 1e-5 = 0.00011–0.00012 (live 0.00012) ✓
  - GBPUSD: 13–17 pts × 1e-5 = 0.00013–0.00017 (live 0.00017) ✓
- **Bar spread is a per-bar snapshot**, not constant: XAUUSD 19–34 pts, EURUSD 11–67, GBPUSD 11–156 (mode vs max ranges). Using a constant spread would be wrong; per-bar `S` is the correct proxy.

### Timezone (resolved)
- 100% of M15 bar timestamps align to quarter-hour boundaries in UTC for all three symbols.

### Rollover (resolved, corrected)
- XAUUSD daily maintenance window observed as **23:45 → 01:00 UTC** (1.25h), repeated 3 consecutive days. **Not 21–22 UTC** as the manifest candidate assumed.

### Calendar (partially resolved)
- EURUSD/GBPUSD: continuous 24/5 (no intraday gaps in sample).
- XAUUSD: ~23h/day with maintenance window.
- Holidays/early-close: **not exposed** by terminal — broker confirmation required.

### FX contracts (partially resolved)
- volume_min/step confirmed (0.01; max 20 XAUUSD / 50 FX).
- Contract size not exposed (API null). XAUUSD 100 oz/lot from prior live pre-flight; FX sizes unresolved.

---

## 3. Exact Read-Only API Calls Used

| Call | Purpose | Mutating? |
|---|---|---|
| `mt5.initialize(path=TERMINAL)` | Attach to active terminal (no login) | No |
| `mt5.account_info()` | Session state before/after | No |
| `mt5.positions_get()` | Position count | No |
| `mt5.orders_get()` | Order count | No |
| `mt5.symbol_info(sym)` | point, digits, spread, volume, path | No |
| `mt5.symbol_info_tick(sym)` | live bid/ask | No |
| `mt5.copy_rates_range(sym, TIMEFRAME_M15, start, end)` | 5-day M15 OHLC+spread sample | No |
| `mt5.shutdown()` | Detach | No |

**`mt5.login()` was NOT called.** No terminal settings, symbol settings, account, or process was modified.

---

## 4. Sample Sizes and Ranges

| Symbol | Bars | UTC range |
|---|---|---|
| XAUUSD | 346 | 2026-09-21 01:00 → 09-24 18:15 |
| EURUSD | 362 | 2026-09-21 00:00 → 09-24 18:15 |
| GBPUSD | 362 | 2026-09-21 00:00 → 09-24 18:15 |

---

## 5. Session-Preservation Verification

| Field | Before | After | Unchanged |
|---|---|---|---|
| login | 7409623 | 7409623 | ✓ |
| server | FPMarketsSC-Demo | FPMarketsSC-Demo | ✓ |
| balance | 5000.05 | 5000.05 | ✓ |
| equity | 5000.05 | 5000.05 | ✓ |
| positions | 0 | 0 | ✓ |
| orders | 0 | 0 | ✓ |

---

## 6. Manifest Impact (finding only — manifest not edited)

The frozen manifest's `no_rollover.maintenance_window` candidate `~21-22 UTC` is **contradicted** by the observed `23:45–01:00 UTC` window. This is recorded as an audit finding. **No manifest edit was made** (frozen manifest requires approval to change).

---

## 7. Confirmation: No Phase 1 Strategy Work Occurred

- ✅ No historical strategy/backtest run
- ✅ No signal generation, episode identification, counts, or performance scoring
- ✅ No EV / PF / win-rate / drawdown / PnL computation
- ✅ No orders, no login(), no account changes
- ✅ No changes under `frival/`
- ✅ No manifest, test, workflow, or broker/terminal settings modified
- ✅ No strategy engine created

---

## 8. Next Step (blocked on approval)

Awaiting explicit approval for either:
1. **Updating the frozen manifest** to the observed 23:45–01:00 UTC maintenance window (and recording the audit evidence), or
2. Proceeding to Phase 1 data retrieval / historical analysis with this audit's findings incorporated.

**Stopped.** No further action without your explicit approval.