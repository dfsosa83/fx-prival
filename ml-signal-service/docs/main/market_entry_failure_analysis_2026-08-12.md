# Market Entry Failure Analysis — Frival Execution Bot
**Date:** 2026-08-12
**Scope:** `frival/execution_bot/` (execution pipeline) and `frival/output/logs/` (Frival runtime logs)
**Data window:** 2026-07-29 → 2026-08-12 (11 live-log files), plus complete `execution_bot/data/execution_log.jsonl` (550 rows)
**Author:** Automated code+data audit

---

## 1. Executive Summary

The reported symptom — *"multiple market entry attempts have failed to execute a single successful operation"* — has **two overlapping causes** that must not be conflated:

| # | Cause | Severity | Category |
|---|---|---|---|
| **A** | The execution bot has not run in continuous (`watch_loop`) mode since **2026-08-07 15:00 UTC**. All 550 rows in `execution_log.jsonl` were written in a **single manual back-fill session on 2026-08-07 between 16:21 and 17:26 UTC** against months of accumulated JSONL history. Since that back-fill, **the bot has been idle** even though Frival itself has continued firing daily sessions. | **P0** | Operational |
| **B** | Of the 550 back-filled attempts, **316 were logically doomed** (SL=0/entry=0 validation errors) because they targeted *old-schema* signals (pre-`trade{}` block, Jan–early-Feb 2026). Another 233 were logged as `EXECUTED ticket=?` — accepted by the DEMO simulator but with a **broken ticket field** because of a since-fixed dict-key mismatch. Zero of the 550 attempts touched a real broker. | **P0** | Code |

**Bottom line:** the system has **never placed a live broker order**. Every "execution" recorded to date is a DEMO-mode simulation from a one-shot historical back-fill, and half of those simulations failed validation before even reaching the simulator. Meanwhile, Frival's live decision engine has been correctly SHELVING or BLOCKING every candidate signal since Aug 8, so no new tradeable signals have been produced for the bot to pick up.

Ten distinct defects were identified, ranked by impact in §10.

---

## 2. Evidence Base

### 2.1 execution_log.jsonl statistics (workspace file)

```
Total rows                       550
Status                           ERROR    316   (57.5%)
                                 EXECUTED 234   (42.5%)
Distinct symbols                 EURUSD   508
                                 USDCHF    26
                                 GBPUSD    16
Distinct dates                   2026-08-07   (all 550 rows)
Distinct HH:MM buckets           16:21, 16:51, 17:14, 17:26   (4 back-fill runs)
daily_pnl (every row)            0
```

Every `ERROR` row carries the same detail string:

```
Invalid SL/TP levels: ['SELL order: Stop Loss (0) should be above entry price (0)',
                       'SELL order: Take Profit (0) should be below entry price (0)']
```

233 of 234 `EXECUTED` rows carry `ticket=?` (missing broker ticket); 1 row carries `ticket=0` (see §8).

### 2.2 watcher_state.json (current on disk)

```json
{"last_signal_id": "EURUSD_H1_SELL_2026-08-07T15:00:00Z", "signals_processed": 1}
```

- `last_signal_id` is 5 days stale.
- `signals_processed = 1` while the log holds 550 rows — proof that `--once` mode never increments this counter (see §6).

### 2.3 Signal-file schema audit (`frival/output/signals/**/*.jsonl`)

Programmatic scan of every stored signal grouped by `final_decision == "FIRED"`:

| FIRED signals | Count | Notes |
|---|---|---|
| With **missing** `trade` block (old schema) | **158** | Jan through early-Feb 2026 |
| With `trade` block, zero levels | 0 | — |
| With `trade` block, valid levels | 116 | Feb 2026 onward |

Ratios into the execution log:
- 316 ERROR ÷ 158 old-schema FIRED ≈ **2.0 duplicates per signal**
- 234 EXECUTED ÷ 116 valid FIRED ≈ **2.0 duplicates per signal**

The 2× multiplier is explained by the four back-fill invocations in §2.1 combined with the lack of in-batch dedupe in [`read_new_signals`](frival/execution_bot/signal_watcher.py#L41-L98) (see §5).

### 2.4 Live-logs summary (`frival/output/logs/*.log`)

- 11 files, 3,734 total lines, dated 2026-07-29 → 2026-08-12.
- Recent sessions (Aug 11 and Aug 12) all end in `Signal SHELVED` (agents rejected) or `Gate result: BLOCK (session)`.
- **No `FIRED` signal has appeared in the live logs since 2026-08-07 15:00 UTC.**
- The MT5 connection succeeds every session: `[mt5] Logged in to FPMarketsSC-Live (account 81486396)`.

This confirms Frival's decision layer is healthy; the drought of new trades is a *legitimate* outcome of agent gating, not a bot bug.

---

## 3. Root Cause #1 — Zero-Level Signals Bypass to OrderManager

### 3.1 Data flow

```
JSONL signal (Jan 2026, no `trade` block)
        │
        ▼
read_new_signals()                       ← filter added AFTER back-fill
   ├─ final_decision == "FIRED" ✔
   ├─ trade.get("entry",0) == 0 → skip   ← would catch it TODAY
   └─ (during Aug-7 back-fill this
       branch did not exist yet)
        │
        ▼
handle_signal()                          — frival/execution_bot/order_bot.py:174
   entry      = trade.get("entry")      or signal.get("entry_price") or 0
   stop_loss  = trade.get("stop_loss")  or signal.get("stop_loss")   or 0
   take_profit= trade.get("take_profit")or signal.get("take_profit") or 0
        │  all three fall through to 0
        ▼
OrderManager.execute_order({entry_price:0, stop_loss:0, take_profit:0})
        │
        ▼
_prepare_order()                         — order_manager.py:167
   if entry_price is not None:           ← 0 is not None → True
       if is_price_within_tolerance(current, 0, tol=5pip):
           ...market branch...           ← False (|1.15-0| ≫ 5 pip)
       else:
           order_type = 'PENDING'
           price      = entry_price      ← price = 0
   validate_sl_tp_levels('sell', 0, 0, 0)
        │
        ▼
OrderValidationError:
   "SELL order: Stop Loss (0) should be above entry price (0)"
        │
        ▼
OrderBot.handle_signal ⇒ status=ERROR    — order_bot.py:206
```

### 3.2 Why the guard is insufficient

Even with the *current* skip in `read_new_signals` (frival/execution_bot/signal_watcher.py:93-96), `handle_signal` **still contains the falsy-fallback pattern** that would produce `entry=0` if a caller (e.g. `--once` mode or a future direct invocation) fed it a raw old-schema dict. The safety net is one layer thin.

### 3.3 Impact

- 316 ERROR rows (57.5% of every attempt on record).
- 0 real broker damage — the failure occurs during *validation*, before order-send.
- **Not a live-money risk today**, but a latent bug: any future consumer that skips `read_new_signals` (e.g. a REST endpoint that posts a stale signal) will trigger the same path and log confusing “SL(0)” errors.

---

## 4. Root Cause #2 — Back-Fill Masquerading as Live Execution

### 4.1 Timeline

| Timestamp (UTC) | Event | Source |
|---|---|---|
| 2026-08-07 15:00 | Last real live cycle recorded in `watcher_state.json` | watcher_state.json |
| 2026-08-07 16:21 | Back-fill run #1 (manual `python run.py --once`) | execution_log.jsonl |
| 2026-08-07 16:51 | Back-fill run #2 | execution_log.jsonl |
| 2026-08-07 17:14 | Back-fill run #3 | execution_log.jsonl |
| 2026-08-07 17:26 | Back-fill run #4 | execution_log.jsonl |
| 2026-08-08 → 2026-08-12 | Frival live sessions ran normally (11 files, 3,734 lines) — all SHELVED / BLOCKED, 0 FIRED | output/logs/*.log |
| 2026-08-12 (today) | Bot has **not** been running in `watch_loop` mode | watcher_state.json unchanged since Aug 7 |

### 4.2 Why the operator likely believes "trades are failing"

Because the back-fill produced 316 loud red `ERROR` lines and 234 `EXECUTED ticket=?` lines all within the same 65-minute window, the log *appears* to show hundreds of failed live orders. In reality:

1. All 550 rows are historical replay — none corresponded to a *live* Frival tick.
2. Even the 234 “EXECUTED” rows never left the DEMO simulator (`DEMO_MODE=true` in `credentials.env`).
3. Between Aug 8 and Aug 12 there have been **zero attempts** because (a) the bot's `watch_loop` isn't running, and (b) Frival has not produced a `FIRED` signal in that window.

### 4.3 Impact

- **Operational**: the perceived “live pipeline” is dark.
- **Diagnostic noise**: any real error after Aug 7 would be buried in the back-fill flood.

---

## 5. Root Cause #3 — Duplicate Processing in `read_new_signals`

`read_new_signals` scans `SIGNALS_DIR.glob("**/*.jsonl")` and appends every FIRED entry that passes filters to `signals[]`. It filters against `last_signal_id` *once at entry*, but **does not deduplicate against signals already collected in the current call**.

Frival's `output_writer.py` occasionally rewrites the *same* signal to a JSONL (e.g. after agent-second-pass or on session restart), and the signal folder is organized by month, so the same `signal_id` can appear:

- Multiple times in the same month file (rerun/replay).
- Duplicated across a month folder and a stale copy elsewhere (none observed today but structurally possible).

**Observation:** every distinct old-schema `signal_id` shows up **exactly twice** in `execution_log.jsonl`, and every valid `signal_id` also shows up twice. Combined with 4 back-fill runs (and `last_signal_id` moving forward between them), the 2× multiplier is consistent with each signal being seen once in an early run and once in a later run — or once as an in-file duplicate.

### Impact

- Wasted broker round-trips (live) or wasted validation cycles (demo).
- Real-money risk in live mode: **two identical entries for one signal** could double position size if the Gate-3 duplicate-position check hasn't propagated (there is a race window before MT5 reflects the first fill).

---

## 6. Root Cause #4 — `--once` Mode Bugs

`frival/execution_bot/run.py:120-136`:

```python
if args.once:
    state = load_state()
    last_id = state.get("last_signal_id")
    signals = read_new_signals(last_id)
    for sig in signals:
        bot.handle_signal(sig)                                       # ← no validate_signal()
        state["last_signal_id"] = sig.get("signal_id", "")
    state["signals_processed"] = state.get("signals_processed", 0)   # ← BUG: no increment
    save_state(state)
```

Two defects here:

**6.1 Counter never increments.** `signals_processed` is set to itself. This is why `watcher_state.json` says `1` after 550 executions.

**6.2 `validate_signal()` is bypassed.** The full validator (which enforces `entry != 0`, `stop_loss != 0`, `take_profit != 0`, non-empty symbol/direction, non-expired) lives only inside `watch_loop` (frival/execution_bot/signal_watcher.py:139-155). `--once` mode goes straight to `bot.handle_signal(sig)`. This is precisely how the 158 old-schema signals reached `OrderManager` on 2026-08-07 despite the "missing trade block" being trivially detectable.

### Impact

- Silent state corruption: forensic tooling reading `signals_processed` will report **1** while thousands may have been attempted.
- Validation defense-in-depth broken exactly along the code path most likely to be used by ops (bulk back-fill).

---

## 7. Root Cause #5 — Config / Code Drift

### 7.1 Timezone key mismatch

- `settings.yaml` (line 11): `mt5.timezone: America/Panama`
- `core/mt5_connector.py`: reads `self.config.get_mt5_config().get('market_timezone', 'Asia/Qatar')`

The key `market_timezone` is never populated. The connector silently falls back to `Asia/Qatar`. Any code path that later reads the connector's TZ (session-hour gates, log timestamping, calendar look-ahead) will be off by 8 hours.

### 7.2 `orders.deviation_points` never propagated

`settings.yaml`: `orders.deviation_points: 5`
`core/order_manager.py`: uses hard-coded `deviation = order_params.get('deviation', 30)` when composing the MT5 request. The YAML value is dead code.

### 7.3 Shadow config vs. inline comment

`settings.yaml` lines 22-31:

```yaml
EURUSD:  shadow: false          # LIVE — EV positive
GBPUSD:  shadow: false          # shadow — EV negative, monitoring only
USDCHF:  shadow: false          # shadow — EV negative, monitoring only
```

The values say **all three pairs are live**, but the comments say GBPUSD and USDCHF are shadow-only. `order_bot.handle_signal` at gate 2 only reads the flag (`if pair_cfg.get('shadow', False): reject`). Therefore GBPUSD and USDCHF have been **fully allowed to trade in DEMO mode**, and would be allowed to trade in LIVE mode too the moment `DEMO_MODE=false` is set.

**This is the single most dangerous drift** — 16 GBPUSD and 26 USDCHF "executions" recorded in the log confirm the config is being read as live-allowed. In a real live-mode switch, the operator would silently open positions on pairs believed to be shadow-monitored.

### 7.4 Emergency-stop path

`settings.yaml`: `stop_file: ../frival/data/emergency_stop.txt`
This resolves relative to the process CWD, not to `execution_bot/config/`. If the operator runs the bot from a different CWD (e.g. VS Code integrated terminal at the workspace root), the stop file will not be found and emergency-stop is silently disarmed.

---

## 8. Root Cause #6 — `ticket=?` Mystery in EXECUTED Log Rows

Current `_send_order()` (`order_manager.py:507-515`) returns:

```python
return {
    'success': True,
    'retcode': mt5.TRADE_RETCODE_DONE,
    'order': 0,
    'deal':  0,
    ...
}
```

Current `OrderBot.handle_signal` (`order_bot.py:207-211`) reads:

```python
ticket = result.get("order", "?")     # → 0 in demo
self._log(signal, "EXECUTED", f"ticket={ticket}")  # → "ticket=0"
```

So the *current* code would log `ticket=0`. Yet 233 of 234 EXECUTED rows show `ticket=?` and only **1** shows `ticket=0`. The most likely explanation: the demo return dict on 2026-08-07 used a *different key* (e.g. `order_id` or was missing `order`); the file was later refactored to use `order`, so runs after the refactor produce `ticket=0`. The lone `ticket=0` entry was written by the last of the four back-fill runs, after the refactor merged.

### Impact

- Log entries are historically ambiguous — you cannot tell from `ticket=?` whether a real ticket existed.
- **Latent risk**: in live mode, if any code path returns `success=True` without an `order` key (e.g. partial-fill retry), operators will see `ticket=?` and may treat it as failure or duplicate the request. There is no invariant enforcing "success ⇒ order present".

---

## 9. Runtime Risk Gaps (not observed but present in code)

| # | Gap | Location | Consequence |
|---|---|---|---|
| 9.1 | `_calculate_daily_pnl` only reads `mt5.history_deals_get` — realized P&L only. Floating equity swing on open positions is ignored. | `order_bot.py` | Daily-loss stop can be blown past `-$50` by an open drawdown before it triggers. |
| 9.2 | `is_market_open` only checks `symbol_info.trade_mode != DISABLED`. It does not check weekend, holiday, or session-hour. FPMarkets keeps `trade_mode = FULL` on weekends. | `mt5_connector.py` | Weekend/off-hours signals can pass to `order_send`; broker rejects, log records ERROR, but the guard should have caught it earlier. |
| 9.3 | MT5 connection has retry only at *initial* `connect()`. There is no reconnect logic if the terminal disconnects mid-run. | `mt5_connector.py` | Silent stall — `watch_loop` keeps polling signals but every `order_send` fails. |
| 9.4 | Position sizing has undocumented `signal_tier` multipliers (weak 0.5×, normal 1.0×, strong 1.5×, golden 2.0×). Frival's JSONL does not currently emit a `signal_tier` field, so all sizing defaults to 1.0× — but a schema drift would silently 2× position size. | `order_manager.py::_calculate_position_size` | Config drift risk. Should be documented in `README.md`. |
| 9.5 | No dedupe of `last_signal_id` when Frival replays the same session (e.g. process restart). Combined with §5, worst case is one signal opening two positions in the sub-second race window. | `signal_watcher.py`, `order_bot.py` gate 3 | Real live risk. Consider a persisted "already-executed-signal-ids" set. |

---

## 10. Proposed Fixes (Prioritized)

### P0 — Fix immediately, before any live-mode toggle

**F1. Restore validation defense-in-depth in `--once` mode**
`frival/execution_bot/run.py` around line 128:
```python
from signal_watcher import read_new_signals, load_state, save_state, validate_signal
...
for sig in signals:
    err = validate_signal(sig)
    if err:
        print(f"[--once] SKIP {sig.get('signal_id')}: {err}")
        state["last_signal_id"] = sig.get("signal_id", "")
        continue
    bot.handle_signal(sig)
    state["last_signal_id"] = sig.get("signal_id", "")
    state["signals_processed"] = state.get("signals_processed", 0) + 1
```

**F2. Reject zero-level orders inside `handle_signal`**
`frival/execution_bot/order_bot.py` immediately after extracting `entry / stop_loss / take_profit`:
```python
if not entry or not stop_loss or not take_profit:
    self._log(signal, "SKIPPED", f"zero levels e={entry} sl={stop_loss} tp={take_profit}")
    self.signals_rejected += 1
    return True
```
This closes the last defect-in-depth gap even if `read_new_signals` is bypassed.

**F3. Enforce `order` invariant on success**
`frival/execution_bot/order_bot.py:209`:
```python
ticket = result.get("order")
if ticket is None:
    self._log(signal, "FAILED", "success=True but no order id returned")
    return True
```

**F4. Deduplicate the signal batch**
`frival/execution_bot/signal_watcher.py::read_new_signals`, at the end:
```python
seen, deduped = set(), []
for s in signals:
    sid = s.get("signal_id")
    if sid and sid not in seen:
        seen.add(sid); deduped.append(s)
return deduped
```

### P1 — Fix within the day

**F5. Resolve the shadow-config contradiction.** Either flip `GBPUSD.shadow` and `USDCHF.shadow` to `true` (matching the inline comments), or update the comments to reflect the *decision* that both pairs are live. Do this *before* any live toggle.

**F6. Fix the timezone key.** Rename `mt5.timezone` → `mt5.market_timezone` in `settings.yaml` OR update `mt5_connector.py` to read `timezone`. Pick one and grep the tree to confirm no other caller.

**F7. Propagate `deviation_points`.** In `order_manager.py::_send_order`, read from `self.config.get_orders_config().get('deviation_points', 30)` instead of the hard-coded 30.

**F8. Anchor the emergency-stop path.** In `settings.yaml`, make `stop_file` an absolute path anchored to the workspace root, or resolve it in `config_manager.py` relative to `Path(settings_file).resolve().parents[N]`.

### P2 — Fix this week

**F9. Add a session-hour + weekend gate.** In `mt5_connector.is_market_open`, check `datetime.now(UTC).weekday() < 5` and the pair's session window.

**F10. Persist an "already-executed" set.** Extend `watcher_state.json` to `{"last_signal_id": ..., "signals_processed": N, "executed_ids": [...]}` (bounded to last N ids). Guard `handle_signal` against re-firing an id already in the set.

**F11. Floating P&L in daily-loss gate.** Update `_calculate_daily_pnl` to add `sum(pos.profit for pos in mt5.positions_get())`.

**F12. Add a reconnect loop.** In `watch_loop`, if any tick fails with `mt5.last_error()` indicating disconnection, call `mt5_connector.connect()` before continuing.

---

## 11. Verification Plan

For each fix, the acceptance criterion:

| Fix | Test |
|---|---|
| F1 | Rerun `python run.py --once` against a synthetic JSONL containing one old-schema signal. Expect: log line `[--once] SKIP ...: missing trade block`, no OrderManager call, `signals_processed` incremented in state. |
| F2 | Manually invoke `bot.handle_signal({...trade: {entry:0, stop_loss:0, take_profit:0}...})`. Expect: log entry `SKIPPED zero levels`, no OrderManager exception. |
| F3 | Monkey-patch `_send_order` to return `{'success': True}` (no `order`). Expect: `FAILED` log entry, position count unchanged. |
| F4 | Feed a signals directory containing the same signal_id in two JSONL files. Expect: only one call to `handle_signal`. |
| F5 | `grep -r shadow settings.yaml` and confirm flag ↔ comment agreement. Start bot in DEMO, feed a GBPUSD signal; expect the intended behavior (either logged as shadow-blocked or logged as executed). |
| F6 | Add `print(connector.timezone)` at bot start; expect `America/Panama` (or the chosen value), not `Asia/Qatar`. |
| F7 | With `deviation_points: 5`, inspect the `mt5.order_send` request dict via logger; expect `deviation=5`. |
| F8 | Create emergency-stop file, start bot from workspace root and from `execution_bot/`; both must halt. |
| F9 | Run `--once` at Saturday 12:00 UTC on any tradeable-symbol signal. Expect: gate rejects with `market closed`. |
| F10 | Send the same signal to two `--once` runs. Expect: second run logs `DUPLICATE` and does not call OrderManager. |
| F11 | Open a losing DEMO position, run `_calculate_daily_pnl` — expect negative value equal to floating loss. |
| F12 | Kill MT5 terminal mid-run; expect `[reconnect] attempting reconnection`, and after restart, next signal executes normally. |

---

## 12. Immediate Operational Action Items

Independently of code fixes, these operational steps are needed **now**:

1. **Truncate or archive `execution_log.jsonl`** to remove the 2026-08-07 back-fill noise. Suggested: move to `execution_log.jsonl.backfill.2026-08-07` and start clean.
2. **Reset `watcher_state.json`** to `{"last_signal_id": "EURUSD_H1_SELL_2026-08-12T00:00:00Z", "signals_processed": 0}` (or the most recent legitimate `signal_id` from live logs) so the next `watch_loop` start doesn't rescan history.
3. **Decide the shadow policy** for GBPUSD and USDCHF and commit it to `settings.yaml`. If shadow was intended (per the code comments), flip both flags to `true` before restarting.
4. **Start `watch_loop` on a persistent host** (nssm service, systemd, or a supervised terminal), because `--once` is diagnostically dangerous per §6 and cannot replace continuous monitoring.
5. **Wait for a live FIRED signal.** Given Frival has produced zero FIRED signals since Aug 7 (all SHELVED/BLOCKED), the true test of the pipeline is the *next* real fire. When it comes, one clean row should appear in `execution_log.jsonl`. If it doesn't — that is when to investigate broker-side rejection.

---

## Appendix A — Files inspected

| File | Purpose | Result |
|---|---|---|
| [frival/execution_bot/run.py](frival/execution_bot/run.py) | Entry point, `--once` mode | Bugs: F1 |
| [frival/execution_bot/order_bot.py](frival/execution_bot/order_bot.py) | Gates + orchestration | Bugs: F2, F3 |
| [frival/execution_bot/signal_watcher.py](frival/execution_bot/signal_watcher.py) | Watches JSONL, validates | Bugs: F4 |
| [frival/execution_bot/core/order_manager.py](frival/execution_bot/core/order_manager.py) | Prepares + sends orders | Bugs: F7, latent 9.4 |
| [frival/execution_bot/core/mt5_connector.py](frival/execution_bot/core/mt5_connector.py) | MT5 client wrapper | Bugs: F6, 9.2, 9.3 |
| [frival/execution_bot/core/config_manager.py](frival/execution_bot/core/config_manager.py) | Config + credentials loader | OK |
| [frival/execution_bot/config/settings.yaml](frival/execution_bot/config/settings.yaml) | Trading + risk config | Bugs: F5, F6, F7, F8 |
| [frival/execution_bot/data/execution_log.jsonl](frival/execution_bot/data/execution_log.jsonl) | Runtime execution log | 550 rows, all back-fill |
| [frival/execution_bot/data/watcher_state.json](frival/execution_bot/data/watcher_state.json) | Watcher state | Stale, counter=1 |
| [frival/output/logs/*.log](frival/output/logs/) | Frival live-decision logs | Healthy; 0 FIRED since Aug 7 |
| [frival/output/signals/2026-*/*.jsonl](frival/output/signals/) | Frival signal history | 158 old-schema FIRED, 116 valid FIRED |

## Appendix B — Reproduce the audit

From workspace root (`c:\Users\david\OneDrive\Documents\fx-prival`):

```bash
cd frival
# 1. Log statistics
grep -oE '"status": *"[A-Z]+"' execution_bot/data/execution_log.jsonl | sort | uniq -c
grep -oE '"symbol": *"[A-Z]+"' execution_bot/data/execution_log.jsonl | sort | uniq -c
grep -oE '"timestamp_utc": *"[^"]+"' execution_bot/data/execution_log.jsonl | cut -d'T' -f2 | cut -d':' -f1-2 | sort -u

# 2. Signal schema audit (Python)
python -c "
import json, glob
totals = {'missing_trade':0, 'zero_levels':0, 'valid':0}
for f in sorted(glob.glob('output/signals/2026-*/**.jsonl')):
    for line in open(f, encoding='utf-8'):
        if not line.strip(): continue
        d = json.loads(line)
        if d.get('final_decision') != 'FIRED': continue
        t = d.get('trade')
        if not t: totals['missing_trade'] += 1
        elif t.get('entry',0)==0 or t.get('stop_loss',0)==0: totals['zero_levels'] += 1
        else: totals['valid'] += 1
print(totals)
"
```

---

*End of report.*
