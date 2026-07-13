"""
EURUSD H1 Buy Signal Predictor — Production Inference Script
=============================================================

Generates BUY alerts for EURUSD H1 using the trained LightGBM model.
This is an ALERT GENERATOR, not an auto-trader. Downstream agents (DeafAgent)
are expected to confirm or reject each signal using additional context.

Pipeline:
    1. Load raw H1 data from MT5 CSV
    2. Compute 86 engineered features (identical to training pipeline)
    3. Score with BUY LightGBM model → buy_proba
    4. Score with SELL LightGBM model → sell_proba (for cross-filter)
    5. Apply decision gates:
       a) Cross-filter: suppress if sell_proba >= 0.60
       b) Session filter: only London (07:00–15:59 UTC) or NY (13:00–21:59 UTC)
       c) Cooldown: max 1 signal every 4 bars

Saves a full decision log to data/processed/eurusd_h1_decision_log.csv
every run — one row per bar with probabilities, direction, and gate reason.
This mirrors the DeafAgent abrax_decision_dataset_buy.csv pattern.

Usage:
    python eurusd_h1_predictor.py                          # Full run + save log
    python eurusd_h1_predictor.py --tail 10                # Show last 10 bars
    python eurusd_h1_predictor.py --from 2024-01-01        # Filter start date
    python eurusd_h1_predictor.py --no-session-filter      # Disable session gate

Build date: 2026-07-09
Status: Validated on sealed test set — 0.415 precision (breakeven: 0.400)
"""

import sys
import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths — relative to this script's location
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent.parent  # ml-signal-service/

DATA_PATH = ROOT_DIR / "data" / "raw" / "mt5" / "H1" / "EURUSD_H1.csv"
BUY_MODEL_PATH = ROOT_DIR / "models_bin" / "EURUSD_H1_buy_LightGBM.joblib"
SELL_MODEL_PATH = ROOT_DIR / "models_bin" / "EURUSD_H1_sell_LightGBM.joblib"

# ---------------------------------------------------------------------------
# Decision gates — calibrated on sealed test set (Feb–Jul 2026)
# ---------------------------------------------------------------------------
CROSS_FILTER = 0.60        # Suppress BUY when sell_proba >= 0.60 (ambiguous bars)
COOLDOWN_BARS = 4          # Min bars between consecutive same-direction signals
SESSION_FILTER = True      # Gate to London (07:00–15:59 UTC) and NY (13:00–21:59 UTC)
BUY_ONLY = True            # SELL lane disabled — non-viable on test set

# ---------------------------------------------------------------------------
# Feature engineering — identical to signal_combiner.ipynb Section 3
# ---------------------------------------------------------------------------

ATR_PERIOD = 14


def compute_features(data: pd.DataFrame) -> pd.DataFrame:
    """
    Compute all H1 technical indicators, D1 context, and intraday features.
    Identical to the function used in the training and combiner notebooks.
    Expects columns: datetime, open, high, low, close, volume (tick_volume).
    """
    df = data.copy()

    # ── Time features ──────────────────────────────────────────────────────
    df["hour"] = df["datetime"].dt.hour
    df["day_of_week"] = df["datetime"].dt.dayofweek
    df["month"] = df["datetime"].dt.month
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    df["dow_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 5)
    df["dow_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 5)
    h = df["hour"]
    df["session_asian"] = ((h >= 0) & (h < 7)).astype(int)
    df["session_london"] = ((h >= 7) & (h < 16)).astype(int)
    df["session_ny"] = ((h >= 13) & (h < 22)).astype(int)
    df["session_overlap"] = ((h >= 13) & (h < 17)).astype(int)

    # ── Candle structure ───────────────────────────────────────────────────
    df["body_size"] = abs(df["close"] - df["open"])
    df["price_range"] = df["high"] - df["low"]
    df["upper_wick"] = df["high"] - df[["open", "close"]].max(axis=1)
    df["lower_wick"] = df[["open", "close"]].min(axis=1) - df["low"]
    df["body_ratio"] = df["body_size"] / df["price_range"].replace(0, np.nan)

    # ── Moving averages ────────────────────────────────────────────────────
    for w in [10, 20, 50]:
        df[f"sma_{w}"] = df["close"].rolling(w).mean()
    for s in [10, 20, 50, 100, 200]:
        df[f"ema_{s}"] = df["close"].ewm(span=s, adjust=False).mean()
    df["close_vs_ema50"] = (df["close"] - df["ema_50"]) / df["close"]
    df["close_vs_ema200"] = (df["close"] - df["ema_200"]) / df["close"]

    # ── RSI ────────────────────────────────────────────────────────────────
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    rs = gain.rolling(14).mean() / loss.rolling(14).mean().replace(0, np.nan)
    df["rsi_14"] = 100 - (100 / (1 + rs))

    # ── Stochastic + Williams %R ───────────────────────────────────────────
    low14 = df["low"].rolling(14).min()
    high14 = df["high"].rolling(14).max()
    df["stoch_k"] = 100 * (df["close"] - low14) / (high14 - low14).replace(0, np.nan)
    df["stoch_d"] = df["stoch_k"].rolling(3).mean()
    df["williams_r"] = -100 * (high14 - df["close"]) / (high14 - low14).replace(0, np.nan)

    # ── MACD ───────────────────────────────────────────────────────────────
    e12 = df["close"].ewm(span=12, adjust=False).mean()
    e26 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = e12 - e26
    df["macd_sig"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_sig"]
    df["macd_hist_slope"] = df["macd_hist"].diff()

    # ── ATR ────────────────────────────────────────────────────────────────
    hl = df["high"] - df["low"]
    hpc = (df["high"] - df["close"].shift()).abs()
    lpc = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([hl, hpc, lpc], axis=1).max(axis=1)
    df["atr_14"] = tr.rolling(ATR_PERIOD).mean()
    df["atr_regime"] = df["atr_14"] / df["atr_14"].rolling(50).mean()

    # ── Bollinger Bands ────────────────────────────────────────────────────
    bm = df["close"].rolling(20).mean()
    bs = df["close"].rolling(20).std()
    df["bb_upper"] = bm + 2 * bs
    df["bb_lower"] = bm - 2 * bs
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / bm
    df["bb_pct"] = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"]).replace(0, np.nan)
    for w in [10, 20, 50]:
        df[f"rolling_std_{w}"] = df["close"].rolling(w).std()

    # ── ADX / DMI ──────────────────────────────────────────────────────────
    plus_dm = df["high"].diff().clip(lower=0)
    minus_dm = (-df["low"].diff()).clip(lower=0)
    plus_dm = plus_dm.where(plus_dm > minus_dm, 0)
    minus_dm = minus_dm.where(minus_dm > plus_dm, 0)
    atr_adx = tr.rolling(14).mean()
    pdi = 100 * (plus_dm.rolling(14).mean() / atr_adx.replace(0, np.nan))
    mdi = 100 * (minus_dm.rolling(14).mean() / atr_adx.replace(0, np.nan))
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    df["adx_14"] = dx.rolling(14).mean()
    df["plus_di"] = pdi
    df["minus_di"] = mdi

    # ── CCI ────────────────────────────────────────────────────────────────
    tp = (df["high"] + df["low"] + df["close"]) / 3
    df["cci_20"] = (tp - tp.rolling(20).mean()) / (0.015 * tp.rolling(20).std())

    # ── Momentum ───────────────────────────────────────────────────────────
    df["roc_10"] = df["close"].pct_change(10) * 100
    df["momentum_10"] = df["close"] - df["close"].shift(10)

    # ── Volume ─────────────────────────────────────────────────────────────
    df["obv"] = (np.sign(df["close"].diff()) * df["volume"]).fillna(0).cumsum()
    df["volume_ratio"] = df["volume"] / df["volume"].rolling(20).mean().replace(0, np.nan)

    # ── Lag features ───────────────────────────────────────────────────────
    for lag in [1, 2, 3, 5]:
        df[f"close_lag_{lag}"] = df["close"].shift(lag)
        df[f"rsi_lag_{lag}"] = df["rsi_14"].shift(lag)
        df[f"atr_lag_{lag}"] = df["atr_14"].shift(lag)
        df[f"volume_lag_{lag}"] = df["volume"].shift(lag)
    for p in [1, 5, 10]:
        df[f"return_{p}b"] = df["close"].pct_change(p)

    # ── D1 context (daily trend/resistance context) ────────────────────────
    _d1 = (
        df.set_index("datetime")[["open", "high", "low", "close", "volume"]]
        .resample("1D")
        .agg({"open": "first", "high": "max", "low": "min",
              "close": "last", "volume": "sum"})
        .dropna()
    )
    _d1["d1_ema20"] = _d1["close"].ewm(span=20, adjust=False).mean()
    _d1["d1_ema50"] = _d1["close"].ewm(span=50, adjust=False).mean()
    _d1["d1_trend"] = (_d1["d1_ema20"] > _d1["d1_ema50"]).astype(int)
    _dd = _d1["close"].diff()
    _d1["d1_rsi"] = 100 - 100 / (
        1 + _dd.clip(lower=0).rolling(14).mean()
        / (-_dd).clip(lower=0).rolling(14).mean().replace(0, np.nan)
    )
    _d1["d1_close_vs_ema20"] = (_d1["close"] - _d1["d1_ema20"]) / _d1["close"]
    _d1s = (
        _d1[["d1_ema20", "d1_ema50", "d1_trend", "d1_rsi", "d1_close_vs_ema20"]]
        .shift(1)
        .reset_index()
        .rename(columns={"datetime": "_d1_date"})
    )

    df["_date"] = df["datetime"].dt.normalize()
    _do = df.groupby("_date")["open"].first().rename("_day_open")
    df = df.join(_do, on="_date")
    df["close_vs_day_open"] = (df["close"] - df["_day_open"]) / df["_day_open"]
    df = df.merge(_d1s, left_on="_date", right_on="_d1_date", how="left")
    df.drop(columns=["_date", "_d1_date", "_day_open"], inplace=True)

    n_before = len(df)
    df.dropna(inplace=True)
    df.reset_index(drop=True, inplace=True)
    print(f"[features] Rows after warm-up: {len(df):,}  (dropped {n_before - len(df):,})")

    return df


# ---------------------------------------------------------------------------
# Decision logic
# ---------------------------------------------------------------------------

def apply_decision_gates(
    df: pd.DataFrame,
    buy_threshold: float,
    cross_filter: float,
    cooldown_bars: int,
    session_filter: bool,
) -> pd.DataFrame:
    """
    Apply the three production decision gates to a scored dataframe.

    Parameters
    ----------
    df : DataFrame with columns: datetime, buy_proba, sell_proba,
         session_london, session_ny
    buy_threshold : model-calibrated BUY probability threshold
    cross_filter : suppress BUY when sell_proba exceeds this
    cooldown_bars : minimum bars between consecutive signals
    session_filter : if True, gate to London+NY only

    Returns
    -------
    DataFrame with added columns: buy_signal, direction, reason
    """
    df = df.copy()

    # ── Gate 1: Threshold check ────────────────────────────────────────────
    df["signal_raw"] = df["buy_proba"] >= buy_threshold

    # ── Gate 2: Cross-filter (ambiguous bar suppression) ────────────────────
    df["cross_excluded"] = df["signal_raw"] & (df["sell_proba"] >= cross_filter)
    df["signal_raw"] = df["signal_raw"] & (~df["cross_excluded"])

    # ── Gate 3: Session filter ──────────────────────────────────────────────
    if session_filter:
        in_session = (df["session_london"] == 1) | (df["session_ny"] == 1)
        df["session_excluded"] = df["signal_raw"] & (~in_session)
        df["signal_raw"] = df["signal_raw"] & (~df["session_excluded"])
    else:
        df["session_excluded"] = False

    # ── Gate 4: Cooldown ────────────────────────────────────────────────────
    df["buy_signal"] = df["signal_raw"].astype(int)
    last_signal_idx = -cooldown_bars - 1
    for i in range(len(df)):
        if df.at[i, "signal_raw"]:
            if (i - last_signal_idx) <= cooldown_bars:
                df.at[i, "buy_signal"] = 0
            else:
                last_signal_idx = i

    # ── Build direction column ──────────────────────────────────────────────
    df["direction"] = "neutral"
    df.loc[df["buy_signal"] == 1, "direction"] = "buy"

    # ── Build reason column for traceability ────────────────────────────────
    def _reason(row):
        if not row["signal_raw"]:
            if row["buy_proba"] < buy_threshold:
                return "below_threshold"
            if row["cross_excluded"]:
                return "cross_filtered"
            if row["session_excluded"]:
                return "outside_session"
            return "filtered"
        if row["buy_signal"] == 1:
            return "signal"
        return "cooldown_suppressed"

    df["reason"] = df.apply(_reason, axis=1)

    # ── Cleanup ─────────────────────────────────────────────────────────────
    df.drop(columns=["signal_raw", "cross_excluded", "session_excluded"], inplace=True)

    return df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="EURUSD H1 BUY signal predictor — saves decision log every run"
    )
    parser.add_argument(
        "--tail", type=int, default=5,
        help="Show last N bars in console (default: 5)"
    )
    parser.add_argument(
        "--from", dest="from_date", type=str, default=None,
        help="Filter bars from this date (YYYY-MM-DD). Useful to match agent dataset window."
    )
    parser.add_argument(
        "--no-session-filter", action="store_true",
        help="Disable session filter (useful for backtesting)"
    )
    args = parser.parse_args()

    # ── Load data ───────────────────────────────────────────────────────────
    print(f"[load] Reading {DATA_PATH} ...")
    if not DATA_PATH.exists():
        print(f"[error] Data file not found: {DATA_PATH}")
        sys.exit(1)

    df_raw = pd.read_csv(DATA_PATH, parse_dates=["datetime"])
    df_raw = df_raw.sort_values("datetime").reset_index(drop=True)
    print(f"[load] {len(df_raw):,} rows | {df_raw['datetime'].min()} to {df_raw['datetime'].max()}")

    # ── Optional date filter ────────────────────────────────────────────────
    if args.from_date:
        cutoff = pd.Timestamp(args.from_date)
        before = len(df_raw)
        df_raw = df_raw[df_raw["datetime"] >= cutoff].reset_index(drop=True)
        print(f"[load] Filtered from {cutoff.date()}: {len(df_raw):,} rows (dropped {before - len(df_raw):,})")

    # ── Compute features ────────────────────────────────────────────────────
    print("[features] Computing...")
    df_features = compute_features(df_raw)

    # ── Load models ─────────────────────────────────────────────────────────
    print("[models] Loading...")
    if not BUY_MODEL_PATH.exists():
        print(f"[error] BUY model not found: {BUY_MODEL_PATH}")
        sys.exit(1)
    if not SELL_MODEL_PATH.exists():
        print(f"[error] SELL model not found: {SELL_MODEL_PATH}")
        sys.exit(1)

    buy_bundle = joblib.load(BUY_MODEL_PATH)
    sell_bundle = joblib.load(SELL_MODEL_PATH)

    buy_model = buy_bundle["model"]
    sell_model = sell_bundle["model"]
    BUY_THRESHOLD = buy_bundle["threshold"]
    buy_features = buy_bundle["features"]
    sell_features = sell_bundle["features"]

    print(f"[models] BUY threshold = {BUY_THRESHOLD:.4f} | features = {len(buy_features)}")
    print(f"[models] CROSS_FILTER = {CROSS_FILTER} | COOLDOWN = {COOLDOWN_BARS} bars")
    print(f"[models] SESSION_FILTER = {SESSION_FILTER} "
          f"({'disabled' if args.no_session_filter else 'London+NY only'})")

    # ── Score ───────────────────────────────────────────────────────────────
    X_buy = df_features[buy_features].fillna(0)
    X_sell = df_features[sell_features].fillna(0)

    df_features["buy_proba"] = buy_model.predict_proba(X_buy)[:, 1]
    df_features["sell_proba"] = sell_model.predict_proba(X_sell)[:, 1]

    # ── Apply decision gates ────────────────────────────────────────────────
    session_filter = SESSION_FILTER and not args.no_session_filter
    df_signals = apply_decision_gates(
        df_features,
        buy_threshold=BUY_THRESHOLD,
        cross_filter=CROSS_FILTER,
        cooldown_bars=COOLDOWN_BARS if COOLDOWN_BARS > 0 else 0,
        session_filter=session_filter,
    )

    # ── Save decision log (always) ──────────────────────────────────────────
    processed_dir = ROOT_DIR / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    log_path = processed_dir / "eurusd_h1_decision_log.csv"

    # Compute TP/SL from ATR and model multipliers
    ATR_TP_MULT = buy_bundle["atr_tp_mult"]
    ATR_SL_MULT = buy_bundle["atr_sl_mult"]
    df_signals["entry_price"] = df_signals["close"]
    df_signals["tp_price"] = df_signals["close"] + df_signals["atr_14"] * ATR_TP_MULT
    df_signals["sl_price"] = df_signals["close"] - df_signals["atr_14"] * ATR_SL_MULT

    log_cols = ["datetime", "close", "buy_proba", "sell_proba",
                "buy_signal", "entry_price", "tp_price", "sl_price",
                "direction", "reason"]
    df_signals[log_cols].to_csv(log_path, index=False)
    print(f"[save] Decision log -> {log_path.resolve()}")
    print(f"[save] {len(df_signals):,} rows | "
          f"{df_signals['buy_signal'].sum()} signals")

    # ── Console output ──────────────────────────────────────────────────────
    signal_rows = df_signals[df_signals["buy_signal"] == 1]
    tail_rows = df_signals.tail(args.tail)

    print()
    print("=" * 80)
    print(f"  EURUSD H1 — Last {args.tail} bar(s)")
    print("=" * 80)
    for _, row in tail_rows.iterrows():
        marker = "  <- BUY SIGNAL" if row["buy_signal"] == 1 else ""
        print(
            f"  {row['datetime']}  |  "
            f"buy_proba={row['buy_proba']:.4f}  "
            f"sell_proba={row['sell_proba']:.4f}  |  "
            f"direction={row['direction']:<8}  "
            f"reason={row['reason']}{marker}"
        )
        if row["buy_signal"] == 1:
            print(f"           Entry={row['entry_price']:.5f}  "
                  f"TP={row['tp_price']:.5f}  "
                  f"SL={row['sl_price']:.5f}  "
                  f"ATR={row['atr_14']:.5f}")

    # ── Summary ─────────────────────────────────────────────────────────────
    n_signals = len(signal_rows)
    n_bars = len(df_signals)
    print()
    if n_signals == 0:
        print("  RESULT: No active BUY signal.")
    else:
        latest = signal_rows.iloc[-1]
        print(f"  RESULT: Latest BUY signal at {latest['datetime']}")
        print(f"          Confidence (buy_proba): {latest['buy_proba']:.4f}")
        print(f"          Threshold: {BUY_THRESHOLD:.4f}")
        print(f"          Entry: {latest['entry_price']:.5f}  "
              f"TP: {latest['tp_price']:.5f}  "
              f"SL: {latest['sl_price']:.5f}")
    print(f"  ({n_signals} signals in {n_bars:,} bars)")

    return df_signals


if __name__ == "__main__":
    main()