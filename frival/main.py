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
from datetime import datetime
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


# ── Pair configurations ──────────────────────────────────────────────────────
MODELS_BIN = (
    Path(__file__).resolve().parents[1]
    / "ml-signal-service" / "models_bin"
)

PROMPTS_DIR = Path(__file__).resolve().parent / "agents" / "prompts"

PAIR_CONFIG = {
    "EURUSD": {
        "threshold": 0.306,
        "model_file": MODELS_BIN / "EURUSD_H1_sell_Ensemble.joblib",
        "direction": "SELL",
        "technical_prompt": None,  # uses default technical.txt
        "fundamental_prompt": None,  # uses default fundamental.txt
    },
    "GBPUSD": {
        "threshold": 0.367,
        "model_file": MODELS_BIN / "GBPUSD_H1_sell_Ensemble.joblib",
        "direction": "SELL",
        "technical_prompt": str(PROMPTS_DIR / "technical_gbpusd.txt"),
        "fundamental_prompt": str(PROMPTS_DIR / "fundamental_gbpusd.txt"),
    },
    "USDCHF": {
        "threshold": 0.359,
        "model_file": MODELS_BIN / "USDCHF_H1_buy_Ensemble.joblib",
        "direction": "BUY",
        "technical_prompt": str(PROMPTS_DIR / "technical_usdchf.txt"),
        "fundamental_prompt": str(PROMPTS_DIR / "fundamental_usdchf.txt"),
    },
}


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
    df_feat = compute_features(df)

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

    for idx, row in df_gated.iterrows():

        # Only log bars that pass gates (standard or borderline)
        is_standard = row["gate_result"]
        is_borderline = row.get("gate_borderline", False)
        if not is_standard and not is_borderline:
            continue

        bar_dt = row["datetime"]
        direction = pcfg.get("direction", "SELL")
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

            ctx = build_context(
                df_range.loc[idx],
                probability=float(row["probability"]),
                threshold=model_threshold,
                individual_probs=ind_probs or {"ensemble": float(row["probability"])},
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
                )
                t_dec = tech_result.get("decision", "NEUTRAL")
                if t_dec == "CONFIRM": agent_tech_confirmed += 1
                elif t_dec == "REJECT": agent_tech_rejected += 1
                else: agent_tech_neutral += 1
            except Exception as e:
                agent_errors += 1
                tech_result = {"error": str(e)}

            # Agent B — Fundamental (rate-limited)
            time.sleep(2.5)  # Perplexity rate limit: ~25 req/min
            try:
                fund_result = evaluate_fundamental(
                    current_price=ctx["current_price"],
                    probability=ctx["probability"],
                    currency_pair=pair,
                    prompt_file=pcfg["fundamental_prompt"],
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
                senior = synthesize_borderline(tech_result, fund_result)
            else:
                senior = synthesize(tech_result, fund_result)
            final_decision = senior["final_decision"]
            final_confidence = senior.get("final_confidence")
            veto_reason = senior.get("veto_reason", "")

        # ── Compute trade levels ─────────────────────────────────────
        entry_price = float(row["close"])
        bar_atr = float(row["atr_14"]) if "atr_14" in row.index else 0.0

        if direction == "BUY":
            stop_loss = round(entry_price - bar_atr * ATR_SL_MULT, 5)
            take_profit = round(entry_price + bar_atr * ATR_TP_MULT, 5)
            entry_zone = [
                round(entry_price - 0.00020, 5),  # enter as low as possible
                round(entry_price + 0.00020, 5),
            ]
        else:
            stop_loss = round(entry_price + bar_atr * ATR_SL_MULT, 5)
            take_profit = round(entry_price - bar_atr * ATR_TP_MULT, 5)
            entry_zone = [
                round(entry_price + 0.00020, 5),  # enter as high as possible
                round(entry_price - 0.00020, 5),
            ]
        rr_ratio = round(ATR_TP_MULT / ATR_SL_MULT, 1)
        expires_at = bar_dt + pd.Timedelta(hours=FORWARD_BARS)

        signal = {
            "run_id": run_id,
            "signal_id": signal_id,
            "symbol": pair,
            "direction": direction,
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
    if direction == "BUY":
        sl_pips = round((t["entry"] - t["stop_loss"]) * 10000, 1)
        tp_pips = round((t["take_profit"] - t["entry"]) * 10000, 1)
    else:
        sl_pips = round((t["stop_loss"] - t["entry"]) * 10000, 1)
        tp_pips = round((t["entry"] - t["take_profit"]) * 10000, 1)
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
    df_feat = compute_features(df)
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
    ctx = build_context(latest, probability, threshold, ind_probs)

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
        )
    except Exception as e:
        errors += 1
        tech_result = {"error": str(e)}

    # Agent B
    time.sleep(2.5)
    try:
        fund_result = evaluate_fundamental(
            current_price=ctx["current_price"],
            probability=probability,
            currency_pair=pair,
            prompt_file=pcfg["fundamental_prompt"],
        )
    except Exception as e:
        errors += 1
        fund_result = {"error": str(e)}

    # Senior
    if gate_type == "borderline":
        senior = synthesize_borderline(tech_result, fund_result)
    else:
        senior = synthesize(tech_result, fund_result)
    final_decision = senior["final_decision"]
    final_confidence = senior.get("final_confidence")
    veto_reason = senior.get("veto_reason", "")

    # ── Save and print ──────────────────────────────────────────────────
    signal = _build_signal(latest, probability, model_threshold, ind_probs,
                           tech_result, fund_result,
                           final_decision, final_confidence, veto_reason,
                           gate_type=gate_type, pair=pair, direction=pcfg.get("direction", "SELL"))
    log_signal(signal)

    if final_decision == "FIRED":
        _print_signal(signal)
        _update_cooldown()
    else:
        print(f"\nSignal SHELVED: {veto_reason}")

    print(f"Agents: A={tech_result.get('decision','ERR')} B={fund_result.get('decision','ERR')} -> {final_decision}")
    if errors:
        print(f"Agent errors: {errors}")


def _build_signal(latest_row, probability, threshold, ind_probs,
                  tech_result, fund_result, final_decision, final_confidence, veto_reason,
                  gate_type="standard", pair="EURUSD", direction="SELL"):
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
            round(entry_price - 0.00020, 5),
            round(entry_price + 0.00020, 5),
        ]
    else:
        stop_loss = round(entry_price + bar_atr * ATR_SL_MULT, 5)
        take_profit = round(entry_price - bar_atr * ATR_TP_MULT, 5)
        entry_zone = [
            round(entry_price + 0.00020, 5),
            round(entry_price - 0.00020, 5),
        ]
    expires_at = bar_dt + pd.Timedelta(hours=FORWARD_BARS)

    return {
        "run_id": run_id,
        "signal_id": f"{pair}_H1_{direction}_{bar_dt.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "symbol": pair,
        "direction": direction,
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
    """Record the current time as the last FIRED signal."""
    os.makedirs(COOLDOWN_FILE.parent, exist_ok=True)
    with open(COOLDOWN_FILE, "w") as f:
        json.dump({"timestamp_utc": datetime.utcnow().isoformat()}, f)


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
    args = parser.parse_args()

    if args.mode == "backtest":
        if not args.start or not args.end:
            parser.error("--start and --end required for backtest mode")
        run_backtest(args.start, args.end, args.threshold,
                     source=args.source, agent_enabled=not args.no_agent,
                     borderline=args.borderline, pair=args.symbol)
    elif args.mode == "live":
        run_live(args.threshold, agent_enabled=not args.no_agent,
                 borderline=args.borderline, pair=args.symbol)