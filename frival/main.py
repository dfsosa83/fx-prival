"""
Frival — EURUSD H1 SELL signal pipeline.

Usage:
  # Backtest
  python main.py --mode backtest --start 2026-04-01 --end 2026-04-30
  python main.py --mode backtest --start 2026-04-01 --end 2026-04-30 --no-agent

  # Live (requires MT5 running)
  python main.py --mode live
  python main.py --mode live --no-agent
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from model import compute_features, extract_model_features, load_model, predict, get_features_for_pair
from model.features import ATR_TP_MULT, ATR_SL_MULT, FORWARD_BARS
from signal_gate import apply_gates, gate_summary, BORDERLINE_THRESHOLD
from output_writer import log_signal, write_summary_report
from data import fetch_ohlcv
from live_logger import LiveLogger
from agents import evaluate_technical, evaluate_fundamental, synthesize, synthesize_borderline
from agents.context import build_context
from agents.calendar_context import build_macro_context


# ── Pair configurations ──────────────────────────────────────────────────────
MODELS_BIN = (
    Path(__file__).resolve().parents[1]
    / "ml-signal-service" / "models_bin"
)

PROMPTS_DIR = Path(__file__).resolve().parent / "agents" / "prompts"

PAIR_CONFIG = {
    "EURUSD": {
        "threshold": 0.333,
        "model_file": MODELS_BIN / "EURUSD_H1_sell_Ensemble.joblib",
        "direction": "SELL",
        "pip_multiplier": 10000,
        "entry_zone_size": 0.00020,
        "technical_prompt": None,  # uses default technical.txt
        "fundamental_prompt": None,  # uses default fundamental.txt
    },
    "GBPUSD": {
        "threshold": 0.381,
        "model_file": MODELS_BIN / "GBPUSD_H1_sell_Ensemble.joblib",
        "direction": "SELL",
        "pip_multiplier": 10000,
        "entry_zone_size": 0.00020,
        "technical_prompt": str(PROMPTS_DIR / "technical_gbpusd.txt"),
        "fundamental_prompt": str(PROMPTS_DIR / "fundamental_gbpusd.txt"),
    },
    "USDCHF": {
        "threshold": 0.365,
        "model_file": MODELS_BIN / "USDCHF_H1_sell_Ensemble.joblib",
        "direction": "SELL",
        "pip_multiplier": 10000,
        "entry_zone_size": 0.00020,
        "technical_prompt": str(PROMPTS_DIR / "technical_usdchf.txt"),
        "fundamental_prompt": str(PROMPTS_DIR / "fundamental_usdchf.txt"),
    },
    "USDCAD": {
        "threshold": 0.341,
        "model_file": MODELS_BIN / "USDCAD_H1_sell_Ensemble.joblib",
        "direction": "SELL",
        "pip_multiplier": 10000,
        "entry_zone_size": 0.00020,
        "technical_prompt": None,
        "fundamental_prompt": None,
    },
    "USDJPY": {
        "threshold": 0.367,  # placeholder — update after training
        "model_file": MODELS_BIN / "USDJPY_H1_sell_Ensemble.joblib",  # placeholder
        "direction": "SELL",  # placeholder — update after training
        "pip_multiplier": 100,     # USDJPY pips at 2nd decimal (0.01)
        "entry_zone_size": 0.02,  # 2 pips in USDJPY scale
        "technical_prompt": str(PROMPTS_DIR / "technical_usdjpy.txt"),
        "fundamental_prompt": str(PROMPTS_DIR / "fundamental_usdjpy.txt"),
    },
}


# ── MERG gate configuration ──────────────────────────────────────────────────
# Set MERG_ENABLED=true in environment. MERG_SHADOW_ONLY=true logs without blocking.
MERG_ENABLED = os.getenv("MERG_ENABLED", "false").lower() == "true"
MERG_SHADOW_ONLY = os.getenv("MERG_SHADOW_ONLY", "true").lower() == "true"
MERG_SHADOW_LOG = Path(__file__).resolve().parent / "output" / "merg_shadow.log"
MERG_EVENT_WINDOW_MIN = int(os.getenv("MERG_EVENT_WINDOW_MIN", "60"))
_merg_inference = None  # lazy-loaded MergInference instance

# Stage-1 reaction threshold (validated on sealed test: ~0.70 precision at 0.60).
# MERG is a direction-agnostic volatility veto — direction was proven to be noise.
from agents.macro_event_responder import REACTION_THRESHOLD as MERG_REACTION_THRESHOLD


def _merg_event_risk_gate(bar_dt, pair: str, probability: float) -> str:
    """
    MERG gate: check if a HIGH-impact event is approaching and, if Stage 1 is confident
    a reaction is coming (P(reaction) >= MERG_REACTION_THRESHOLD), veto the trade.

    This is a DIRECTION-AGNOSTIC volatility veto. Direction (Stage 2 M1 and H1-direction)
    was tested and found to be noise, so we block on reaction confidence alone.

    Returns:
        "PASS"  — no event, MERG disabled, or P(reaction) < threshold
        "BLOCK" — confident reaction predicted (only if not shadow_only)

    Only activates when MERG_ENABLED=true. Logs decisions to MERG_SHADOW_LOG.
    """
    global _merg_inference

    if not MERG_ENABLED:
        return "PASS"

    # Load MERG lazily (only when first needed — avoids import cost on startup)
    if _merg_inference is None:
        try:
            from agents.macro_event_responder import MergInference
            model_dir = MODELS_BIN
            _merg_inference = MergInference(model_dir)
            if _merg_inference.ready:
                print(f"[MERG] Loaded — shadow_only={MERG_SHADOW_ONLY} "
                      f"threshold={MERG_REACTION_THRESHOLD}")
            else:
                print("[MERG] Failed to load: " + str(_merg_inference._error))
        except Exception as e:
            print("[MERG] Import failed: " + str(e))
            return "PASS"

    if not _merg_inference or not _merg_inference.ready:
        return "PASS"

    # Check calendar for upcoming HIGH-impact event within window
    try:
        from agents.calendar_context import get_next_high_event
        event_name, minutes_to = get_next_high_event(bar_dt, pair, MERG_EVENT_WINDOW_MIN)
    except Exception:
        return "PASS"

    if not event_name:
        return "PASS"  # no HIGH event in window — MERG silent

    # Fetch the last 5 COMPLETED M1 bars (skip the forming bar), oldest-first.
    # Window mapping: row 0 = window 15 (t-5 min) ... row 4 = window 11 (t-1 min).
    try:
        import MetaTrader5 as mt5
        raw = mt5.copy_rates_from_pos(pair, mt5.TIMEFRAME_M1, 1, 5)
        if raw is None or len(raw) < 5:
            print("[MERG] Insufficient M1 data — pass through")
            return "PASS"
        import numpy as np
        # MT5 returns newest-first → reverse to oldest-first; columns [open, high, low, close]
        bars = np.array([[b[1], b[2], b[3], b[4]] for b in raw[::-1]], dtype=float)
    except Exception as e:
        print(f"[MERG] M1 fetch failed: {e} — pass through")
        return "PASS"

    # Run Stage-1 reaction prediction
    try:
        pred = _merg_inference.predict(bars, event_name)
    except Exception as e:
        print(f"[MERG] Inference failed: {e} — pass through")
        return "PASS"

    if not pred.features_extracted:
        return "PASS"

    blocked = pred.is_reaction   # P(reaction) >= MERG_REACTION_THRESHOLD

    # Log to shadow file
    import json as _json  # avoid shadowing global json
    os.makedirs(MERG_SHADOW_LOG.parent, exist_ok=True)
    entry = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "bar_dt": str(bar_dt),
        "pair": pair,
        "event": event_name,
        "minutes_to_event": minutes_to,
        "p_reaction": round(pred.p_reaction, 4),
        "confidence": round(pred.confidence, 4),
        "threshold": MERG_REACTION_THRESHOLD,
        "blocked": blocked,
        "shadow_only": MERG_SHADOW_ONLY,
        "effective_action": "BLOCK" if (blocked and not MERG_SHADOW_ONLY) else "PASS",
    }
    with open(MERG_SHADOW_LOG, "a", encoding="utf-8") as f:
        f.write(_json.dumps(entry, default=str) + "\n")

    if blocked:
        print(f"\n[MERG Gate] reaction predicted "
              f"(p={pred.p_reaction:.2f} >= {MERG_REACTION_THRESHOLD}) — volatility expected")
        print(f"  Event: {event_name} in {minutes_to} min")
        if MERG_SHADOW_ONLY:
            print(f"  [shadow_only — would have blocked, but letting through]")
            return "PASS"
        else:
            print(f"  [BLOCKED — signal skipped]")
            return "BLOCK"
    else:
        print(f"\n[MERG Gate] no confident reaction "
              f"(p={pred.p_reaction:.2f} < {MERG_REACTION_THRESHOLD})")

    return "PASS"


def _check_prompt_direction(pair: str, pcfg: dict):
    """Startup check: verify pair direction matches prompt file headers."""
    direction = pcfg.get("direction", "SELL")
    for key in ["technical_prompt", "fundamental_prompt"]:
        path = pcfg.get(key)
        if path is None:
            continue
        with open(path, encoding="utf-8") as f:
            first_lines = f.read(200)
        expected = f"# DIRECTION: {direction}"
        if expected not in first_lines:
            raise RuntimeError(
                f"PROMPT MISMATCH: {pair} direction is {direction} but "
                f"{path} header does not contain '{expected}'"
            )


def run_backtest(
    start_date: str,
    end_date: str,
    threshold: float = 0.306,
    source: str = "csv",
    agent_enabled: bool = True,
    borderline: bool = False,
    pair: str = "EURUSD",
) -> dict:
    """
    Run the ML pipeline over a date range.

    1. Fetch data (CSV or MT5)
    2. Compute features
    3. Run ensemble model
    4. Apply decision gates
    5. Evaluate gated signals through technical agent
    6. Log results to JSONL

    Returns summary dict.
    """
    print(f"\n=== Backtest: {pair} {start_date} -> {end_date} ===\n")

    pcfg = PAIR_CONFIG.get(pair, PAIR_CONFIG["EURUSD"])
    model_threshold = threshold if threshold != 0.306 else pcfg["threshold"]

    # ── Fetch data ────────────────────────────────────────────────────────
    if source == "csv":
        df = fetch_ohlcv(pair, "H1", source="csv")
    else:
        df = fetch_ohlcv(pair, "H1", start_date=start_date, end_date=end_date, source=source)

    # ── Compute features ──────────────────────────────────────────────────
    df_feat = compute_features(df, pair=pair)

    # Filter to target date range (preserves warm-up from full dataset)
    end_dt = pd.Timestamp(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    mask = (df_feat["datetime"] >= start_date) & (df_feat["datetime"] <= end_dt)
    df_range = df_feat[mask].copy()

    if len(df_range) == 0:
        print("No data in range. Exiting.")
        return {}

    # ── Model inference ───────────────────────────────────────────────────
    pair_features = get_features_for_pair(pair)
    df_model = extract_model_features(df_range, features=pair_features)
    bundle = load_model(str(pcfg["model_file"]))
    result = predict(bundle, df_model, threshold=model_threshold)
    df_range["probability"] = result["probability"]

    # Store per-model probabilities for agent context
    for model_name, probs in result["individual_probs"].items():
        df_range[f"prob_{model_name}"] = probs
    print(f"Model inference complete: {result['n_samples']} bars")

    # ── Apply gates ───────────────────────────────────────────────────────
    df_gated = apply_gates(df_range, threshold=model_threshold, borderline=borderline)
    summary = gate_summary(df_gated)

    # ── Log signals ───────────────────────────────────────────────────────
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    fired_count = 0
    shelved_count = 0
    borderline_fired = 0
    borderline_shelved = 0
    agent_tech_confirmed = 0
    agent_tech_rejected = 0
    agent_tech_neutral = 0
    agent_fund_confirmed = 0
    agent_fund_rejected = 0
    agent_fund_neutral = 0
    agent_errors = 0
    fund_reject_streak = 0

    for idx, row in df_gated.iterrows():

        # Only log bars that pass gates (standard or borderline)
        is_standard = row["gate_result"]
        is_borderline = row.get("gate_borderline", False)
        if not is_standard and not is_borderline:
            continue

        bar_dt = row["datetime"]
        direction = pcfg.get("direction", "SELL")
        pip_mult = pcfg.get("pip_multiplier", 10000)
        signal_id = f"{pair}_H1_{direction}_{bar_dt.strftime('%Y-%m-%dT%H:%M:%SZ')}"

        tech_result = {}
        fund_result = {}
        final_decision = "FIRED"
        final_confidence = None
        veto_reason = ""

        # ── Agent evaluation ──────────────────────────────────────────
        if agent_enabled:
            ind_probs = {}
            for mname in ["LogReg", "RandomForest", "XGBoost", "LightGBM"]:
                col = f"prob_{mname}"
                if col in df_range.columns:
                    ind_probs[mname] = float(df_range.at[idx, col])

            agent_mode = "borderline" if is_borderline else "standard"
            ctx = build_context(
                df_range.loc[idx],
                probability=float(row["probability"]),
                threshold=model_threshold,
                individual_probs=ind_probs or {"ensemble": float(row["probability"])},
                mode=agent_mode,
            )

            # Agent A — Technical
            try:
                tech_result = evaluate_technical(
                    current_price=ctx["current_price"],
                    probability=ctx["probability"],
                    threshold=model_threshold,
                    individual_probs=ctx["individual_probs"],
                    d1_context=ctx["d1_context"],
                    top_features=ctx["top_features"],
                    prompt_file=pcfg["technical_prompt"],
                    mode=agent_mode,
                )
                t_dec = tech_result.get("decision", "NEUTRAL")
                if t_dec == "CONFIRM": agent_tech_confirmed += 1
                elif t_dec == "REJECT": agent_tech_rejected += 1
                else: agent_tech_neutral += 1
            except Exception as e:
                agent_errors += 1
                tech_result = {"error": str(e)}

# Agent B — Fundamental (rate-limited)
            time.sleep(2.5)
            try:
                macro_ctx = build_macro_context(bar_dt, pair)
                fund_result = evaluate_fundamental(
                    current_price=ctx["current_price"],
                    probability=ctx["probability"],
                    currency_pair=pair,
                    prompt_file=pcfg["fundamental_prompt"],
                    calendar_context=macro_ctx,
                )
                f_dec = fund_result.get("decision", "NEUTRAL")
                if f_dec == "CONFIRM": agent_fund_confirmed += 1
                elif f_dec == "REJECT": agent_fund_rejected += 1
                else: agent_fund_neutral += 1
            except Exception as e:
                agent_errors += 1
                fund_result = {"error": str(e)}

            # Senior — coordinate both agents
            if is_borderline:
                senior = synthesize_borderline(tech_result, fund_result, fund_reject_streak)
            else:
                senior = synthesize(tech_result, fund_result, fund_reject_streak)
            final_decision = senior["final_decision"]
            final_confidence = senior.get("final_confidence")
            veto_reason = senior.get("veto_reason", "")

            # Track fundamental reject streak
            f_dec = fund_result.get("decision", "NEUTRAL")
            if f_dec == "REJECT":
                fund_reject_streak += 1
            else:
                fund_reject_streak = 0

        # ── Compute trade levels ─────────────────────────────────────
        entry_price = float(row["close"])
        bar_atr = float(row["atr_14"]) if "atr_14" in row.index else 0.0

        zone_size = pcfg.get("entry_zone_size", 0.00020)

        if direction == "BUY":
            stop_loss = round(entry_price - bar_atr * ATR_SL_MULT, 5)
            take_profit = round(entry_price + bar_atr * ATR_TP_MULT, 5)
            entry_zone = [
                round(entry_price - zone_size, 5),  # enter as low as possible
                round(entry_price + zone_size, 5),
            ]
        else:
            stop_loss = round(entry_price + bar_atr * ATR_SL_MULT, 5)
            take_profit = round(entry_price - bar_atr * ATR_TP_MULT, 5)
            entry_zone = [
                round(entry_price + zone_size, 5),  # enter as high as possible
                round(entry_price - 0.00020, 5),
            ]
        rr_ratio = round(ATR_TP_MULT / ATR_SL_MULT, 1)
        expires_at = bar_dt + pd.Timedelta(hours=FORWARD_BARS)

        signal = {
            "run_id": run_id,
            "signal_id": signal_id,
"symbol": pair,
            "direction": direction,
            "pip_multiplier": pip_mult,
            "timestamp_utc": bar_dt.isoformat(),
            "trade": {
                "entry": entry_price,
                "entry_zone": entry_zone,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "rr_ratio": rr_ratio,
                "expires_at_utc": expires_at.isoformat(),
            },
            "model": {
                "probability": round(float(row["probability"]), 4),
                "threshold": threshold,
            },
            "gates": {
                "passed_threshold": bool(row["pass_threshold"]),
                "passed_session": bool(row["pass_session"]),
                "passed_cooldown": bool(row["pass_cooldown"]),
            },
            "agents": {
                "technical": tech_result,
                "fundamental": fund_result,
            },
            "final_decision": final_decision,
            "final_confidence": final_confidence,
            "veto_reason": veto_reason,
            "gate_type": "borderline" if is_borderline else "standard",
        }
        log_signal(signal)

        if final_decision == "FIRED":
            if pcfg.get("shadow", False):
                signal["final_decision"] = "SHADOW_FIRED"
            fired_count += 1
            if is_borderline:
                borderline_fired += 1
        else:
            shelved_count += 1
            if is_borderline:
                borderline_shelved += 1

    print(f"\nSignals: {fired_count} FIRED ({borderline_fired} borderline), "
              f"{shelved_count} SHELVED ({borderline_shelved} borderline)")
    if agent_enabled:
        print(f"Agent A (Technical): {agent_tech_confirmed} confirmed, "
              f"{agent_tech_rejected} rejected, {agent_tech_neutral} neutral")
        print(f"Agent B (Fundamental): {agent_fund_confirmed} confirmed, "
              f"{agent_fund_rejected} rejected, {agent_fund_neutral} neutral")
        print(f"Errors: {agent_errors}")
        total_eval = agent_tech_confirmed + agent_tech_rejected + agent_tech_neutral
        print(f"Rejection rate (tech): {agent_tech_rejected}/{total_eval} "
              f"({round(agent_tech_rejected / max(1, total_eval) * 100, 1)}%)")

    # ── Summary report ────────────────────────────────────────────────────
    report = {
        "run_id": run_id,
        "pair": pair,
        "date_range": {"start": start_date, "end": end_date},
        "threshold": model_threshold,
        "model_file": pcfg["model_file"].name,
        "agent_enabled": agent_enabled,
        "gates": summary,
        "signals_fired": fired_count,
        "signals_shelved": shelved_count,
        "borderline_fired": borderline_fired,
        "borderline_shelved": borderline_shelved,
        "agent_stats": {
            "technical": {
                "confirmed": agent_tech_confirmed,
                "rejected": agent_tech_rejected,
                "neutral": agent_tech_neutral,
            },
            "fundamental": {
                "confirmed": agent_fund_confirmed,
                "rejected": agent_fund_rejected,
                "neutral": agent_fund_neutral,
            },
            "errors": agent_errors,
        } if agent_enabled else None,
    }

    report_path = write_summary_report(run_id, report)
    print(f"Report saved: {report_path}")

    return report


def _print_signal(signal: dict):
    """Print a fired signal to console."""
    t = signal["trade"]
    direction = signal.get("direction", "SELL")
    symbol = signal.get("symbol", "EURUSD")
    pip_mult = signal.get("pip_multiplier", 10000)
    if direction == "BUY":
        sl_pips = round((t["entry"] - t["stop_loss"]) * pip_mult, 1)
        tp_pips = round((t["take_profit"] - t["entry"]) * pip_mult, 1)
    else:
        sl_pips = round((t["stop_loss"] - t["entry"]) * pip_mult, 1)
        tp_pips = round((t["entry"] - t["take_profit"]) * pip_mult, 1)
    conf = signal.get("final_confidence") or "-"
    prob = signal["model"]["probability"]
    zone = t.get("entry_zone", [t["entry"], t["entry"]])
    expires = t.get("expires_at_utc", "-")

    print("\n" + "=" * 60)
    print(f"  SIGNAL FIRED: {symbol} {direction}")
    print(f"  Timestamp:    {signal['timestamp_utc']}")
    print(f"  Entry zone:   {zone[0]:.5f} - {zone[1]:.5f}")
    print(f"  Stop Loss:    {t['stop_loss']:.5f}  ({sl_pips:.1f} pips)")
    print(f"  Take Profit:  {t['take_profit']:.5f}  ({tp_pips:.1f} pips)")
    print(f"  R:R:          {t['rr_ratio']}")
    print(f"  Expires:      {expires}")
    print(f"  Confidence:   {conf}")
    print(f"  Probability:  {prob:.4f}")
    print("=" * 60)

    if signal["agents"].get("technical"):
        ta = signal["agents"]["technical"]
        print(f"  Agent A: {ta.get('decision','?')} ({ta.get('confidence','?')})")
    if signal["agents"].get("fundamental"):
        fa = signal["agents"]["fundamental"]
        print(f"  Agent B: {fa.get('decision','?')} ({fa.get('confidence','?')})")


def run_live(threshold: float = 0.306, agent_enabled: bool = True, borderline: bool = False, pair: str = "EURUSD"):
    """
    Run the pipeline on the current H1 bar via MT5.
    All output is saved to frival/output/logs/YYYY-MM-DD_live.log.
    """
    with LiveLogger() as log_path:
        _run_live_inner(threshold, agent_enabled, borderline, log_path, pair)


def _run_live_inner(threshold, agent_enabled, borderline, log_path, pair):
    import json
    from datetime import datetime, timezone

    pcfg = PAIR_CONFIG.get(pair, PAIR_CONFIG["EURUSD"])
    model_threshold = threshold if threshold != 0.306 else pcfg["threshold"]

    print(f"\n=== LIVE: {pair} {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC ===\n")

    # ── Fetch live data from MT5 ────────────────────────────────────────
    df = fetch_ohlcv(pair, "H1", source="mt5")
    print(f"Fetched {len(df):,} bars from MT5")

    # ── Compute features ────────────────────────────────────────────────
    df_feat = compute_features(df, pair=pair)
    latest = df_feat.iloc[-1]  # current H1 bar (just closed)
    print(f"Latest bar: {latest['datetime']}  close={latest['close']:.5f}")

    # ── Model inference (single bar) ───────────────────────────────────
    pair_features = get_features_for_pair(pair)
    df_model = extract_model_features(pd.DataFrame([latest]), features=pair_features)
    bundle = load_model(str(pcfg["model_file"]))
    result = predict(bundle, df_model)
    probability = result["probability"]

    # Per-model probs for agent context
    ind_probs = {}
    for mname in ["LogReg", "RandomForest", "XGBoost", "LightGBM"]:
        ind_probs[mname] = result["individual_probs"].get(mname, probability)

    # ── Gate check ─────────────────────────────────────────────────────
    passes_threshold = probability >= model_threshold
    passes_borderline = borderline and (BORDERLINE_THRESHOLD <= probability < model_threshold)
    hour = latest["datetime"].hour
    passes_session = ((hour >= 7) & (hour < 16)) | ((hour >= 13) & (hour < 22))
    passes_cooldown = _check_cooldown()

    gate_result = passes_threshold and passes_session and passes_cooldown
    gate_borderline = passes_borderline and passes_session and passes_cooldown

    if not gate_result and not gate_borderline:
        failed = []
        if not passes_threshold and not passes_borderline:
            failed.append(f"p={probability:.4f} < {model_threshold}")
        elif passes_borderline and not passes_cooldown:
            failed.append("cooldown")
        if not passes_session:
            failed.append("session")
        if not passes_cooldown and passes_threshold:
            failed.append("cooldown")
        gate_type = ""
    elif gate_result:
        gate_type = "standard"
    else:
        gate_type = "borderline"

    if gate_type:
        print(f"Probability: {probability:.4f}  threshold={model_threshold}")
        print(f"Gate result: PASS ({gate_type})")
    else:
        print(f"Probability: {probability:.4f}  threshold={model_threshold}")
        print(f"Gate result: BLOCK  ({'  '.join(failed)})")

    if not gate_result and not gate_borderline:
        return

    # ── MERG Gate (Macro Event Response) ─────────────────────────────────
    if MERG_ENABLED and gate_type:
        merg_result = _merg_event_risk_gate(latest["datetime"], pair, probability)
        if merg_result == "BLOCK":
            return
    # ── Agent evaluation ────────────────────────────────────────────────
    if not agent_enabled:
        signal = _build_signal(latest, probability, threshold, ind_probs, {},
                               {}, "FIRED", None, "")
        _print_signal(signal)
        log_signal(signal)
        _update_cooldown()
        print("Signal saved (no agents).")
        return

    # Build context
    from agents.context import build_context
    live_mode = "borderline" if gate_type == "borderline" else "standard"
    ctx = build_context(latest, probability, threshold, ind_probs, mode=live_mode)

    tech_result = {}
    fund_result = {}
    errors = 0

    # Agent A
    try:
        tech_result = evaluate_technical(
            current_price=ctx["current_price"],
            probability=probability, threshold=model_threshold,
            individual_probs=ind_probs,
            d1_context=ctx["d1_context"],
            top_features=ctx["top_features"],
            prompt_file=pcfg["technical_prompt"],
            mode=live_mode,
        )
    except Exception as e:
        errors += 1
        tech_result = {"error": str(e)}

    # Agent B
    time.sleep(2.5)
    try:
        macro_ctx = build_macro_context(latest["datetime"], pair)
        fund_result = evaluate_fundamental(
            current_price=ctx["current_price"],
            probability=probability,
            currency_pair=pair,
            prompt_file=pcfg["fundamental_prompt"],
            calendar_context=macro_ctx,
        )
    except Exception as e:
        errors += 1
        fund_result = {"error": str(e)}

    # Senior
    reject_streak = _get_reject_streak()
    if gate_type == "borderline":
        senior = synthesize_borderline(tech_result, fund_result, reject_streak)
    else:
        senior = synthesize(tech_result, fund_result, reject_streak)
    final_decision = senior["final_decision"]
    final_confidence = senior.get("final_confidence")
    veto_reason = senior.get("veto_reason", "")

    # Track fundamental reject streak for future sessions
    f_dec = fund_result.get("decision", "NEUTRAL")
    if f_dec == "REJECT":
        _update_reject_streak(increment=True)
    else:
        _update_reject_streak(increment=False)

    # ── Save and print ──────────────────────────────────────────────────
    signal = _build_signal(latest, probability, model_threshold, ind_probs,
                           tech_result, fund_result,
                           final_decision, final_confidence, veto_reason,
                           gate_type=gate_type, pair=pair, direction=pcfg.get("direction", "SELL"),
                           pip_multiplier=pcfg.get("pip_multiplier", 10000))
    log_signal(signal)

    is_shadow = pcfg.get("shadow", False)

    if final_decision == "FIRED":
        if is_shadow:
            signal["final_decision"] = "SHADOW_FIRED"
            final_decision = "SHADOW_FIRED"
            print(f"\n[SHADOW] Signal would have fired ({pair}) — EV unproven, suppressing.")
        else:
            _print_signal(signal)
        _update_cooldown()
    else:
        print(f"\nSignal SHELVED: {veto_reason}")

    print(f"Agents: A={tech_result.get('decision','ERR')} B={fund_result.get('decision','ERR')} -> {final_decision}")
    if errors:
        print(f"Agent errors: {errors}")


def _build_signal(latest_row, probability, threshold, ind_probs,
                  tech_result, fund_result, final_decision, final_confidence, veto_reason,
                  gate_type="standard", pair="EURUSD", direction="SELL",
                  pip_multiplier=10000, zone_size=0.00020):
    """Build the signal dict from a single bar row."""
    from datetime import datetime
    bar_dt = latest_row["datetime"]
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    entry_price = float(latest_row["close"])
    bar_atr = float(latest_row.get("atr_14", 0))

    if direction == "BUY":
        stop_loss = round(entry_price - bar_atr * ATR_SL_MULT, 5)
        take_profit = round(entry_price + bar_atr * ATR_TP_MULT, 5)
        entry_zone = [
            round(entry_price - zone_size, 5),
            round(entry_price + zone_size, 5),
        ]
    else:
        stop_loss = round(entry_price + bar_atr * ATR_SL_MULT, 5)
        take_profit = round(entry_price - bar_atr * ATR_TP_MULT, 5)
        entry_zone = [
            round(entry_price + zone_size, 5),
            round(entry_price - zone_size, 5),
        ]
    expires_at = bar_dt + pd.Timedelta(hours=FORWARD_BARS)

    return {
        "run_id": run_id,
        "signal_id": f"{pair}_H1_{direction}_{bar_dt.strftime('%Y-%m-%dT%H:%M:%SZ')}",
            "symbol": pair,
            "direction": direction,
            "pip_multiplier": pip_multiplier,
            "timestamp_utc": bar_dt.isoformat(),
        "trade": {
            "entry": entry_price,
            "entry_zone": entry_zone,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "rr_ratio": round(ATR_TP_MULT / ATR_SL_MULT, 1),
            "expires_at_utc": expires_at.isoformat(),
        },
        "model": {
            "probability": round(probability, 4),
            "threshold": threshold,
        },
        "gates": {
            "passed_threshold": probability >= threshold,
            "passed_session": True,
            "passed_cooldown": True,
        },
        "agents": {
            "technical": tech_result,
            "fundamental": fund_result,
        },
        "final_decision": final_decision,
        "final_confidence": final_confidence,
        "veto_reason": veto_reason,
        "gate_type": gate_type,
    }


COOLDOWN_FILE = Path(__file__).resolve().parent / "data" / "last_signal.json"
COOLDOWN_BARS = 4


def _check_cooldown() -> bool:
    """Check if enough bars have passed since the last FIRED signal."""
    if not COOLDOWN_FILE.exists():
        return True
    try:
        with open(COOLDOWN_FILE) as f:
            data = json.loads(f.read())
        last_ts = datetime.fromisoformat(data["timestamp_utc"])
        now = datetime.utcnow()
        hours_passed = (now - last_ts).total_seconds() / 3600
        return hours_passed >= COOLDOWN_BARS
    except Exception:
        return True


def _update_cooldown():
    """Record the current time as the last FIRED signal, reset reject streak."""
    os.makedirs(COOLDOWN_FILE.parent, exist_ok=True)
    with open(COOLDOWN_FILE, "w") as f:
        json.dump({
            "timestamp_utc": datetime.utcnow().isoformat(),
            "fundamental_reject_streak": 0,
        }, f)


def _get_reject_streak() -> int:
    """Read the current fundamental_reject_streak from last_signal.json."""
    if not COOLDOWN_FILE.exists():
        return 0
    try:
        with open(COOLDOWN_FILE) as f:
            data = json.loads(f.read())
        return data.get("fundamental_reject_streak", 0)
    except Exception:
        return 0


def _update_reject_streak(increment: bool):
    """Update the fundamental_reject_streak in last_signal.json."""
    os.makedirs(COOLDOWN_FILE.parent, exist_ok=True)
    data = {}
    if COOLDOWN_FILE.exists():
        try:
            with open(COOLDOWN_FILE) as f:
                data = json.loads(f.read())
        except Exception:
            pass
    streak = data.get("fundamental_reject_streak", 0)
    data["fundamental_reject_streak"] = streak + 1 if increment else 0
    if "timestamp_utc" not in data:
        data["timestamp_utc"] = datetime.utcnow().isoformat()
    with open(COOLDOWN_FILE, "w") as f:
        json.dump(data, f)


# ── Execution bot integration ────────────────────────────────────────────────

def execute_pending():
    """
    Run the execution bot in --once mode to process any FIRED signals
    generated by this run. Requires MT5 to be running.
    """
    import subprocess
    import sys as _sys
    exec_dir = Path(__file__).resolve().parent / "execution_bot"
    print("\n=== Executing pending signals ===\n")
    subprocess.run(
        [_sys.executable, str(exec_dir / "run.py"), "--once"],
        cwd=str(exec_dir),
    )


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Frival EURUSD H1 SELL signal pipeline")
    parser.add_argument(
        "--mode", choices=["backtest", "live"], default="backtest",
        help="Run mode"
    )
    parser.add_argument("--start", help="Start date YYYY-MM-DD (backtest only)")
    parser.add_argument("--end", help="End date YYYY-MM-DD (backtest only)")
    parser.add_argument("--threshold", type=float, default=0.306, help="Override threshold")
    parser.add_argument("--source", choices=["csv", "mt5"], default="csv", help="Data source")
    parser.add_argument("--no-agent", action="store_true", help="Skip agent evaluation (ML-only)")
    parser.add_argument("--borderline", action="store_true", help="Evaluate bars p in [0.20, 0.306) with strict agent rules")
    parser.add_argument("--symbol", default="EURUSD", help="Trading pair: EURUSD or GBPUSD")
    parser.add_argument("--all", action="store_true", help="Process all pairs (EURUSD, GBPUSD, USDCHF, USDCAD)")
    parser.add_argument("--execute", action="store_true", help="Auto-execute FIRED signals after generation")
    args = parser.parse_args()

    if args.mode == "backtest":
        if not args.start or not args.end:
            parser.error("--start and --end required for backtest mode")
        run_backtest(args.start, args.end, args.threshold,
                     source=args.source, agent_enabled=not args.no_agent,
                     borderline=args.borderline, pair=args.symbol)
    elif args.mode == "live":
        if args.all:
            for pair in ["EURUSD", "GBPUSD", "USDCHF", "USDCAD"]:
                run_live(args.threshold, agent_enabled=not args.no_agent,
                         borderline=args.borderline, pair=pair)
        else:
            run_live(args.threshold, agent_enabled=not args.no_agent,
                     borderline=args.borderline, pair=args.symbol)
        if args.execute:
            execute_pending()


if __name__ == "__main__":
    main()