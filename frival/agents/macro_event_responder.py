"""
MERG — Macro Event Response Gate (Stage 1 only, reaction/volatility veto).

Loads the leak-free Stage-1 *reaction* bundle and returns P(reaction) for a given
pre-event M1 candlestick anatomy + event name.

The gate blocks a trade when `P(reaction) >= REACTION_THRESHOLD` (0.60), REGARDLESS
of direction. Direction (Stage 2 / H1-direction) was tested and found to be noise, so
MERG acts as a pure "volatility is coming → pause" veto, not a direction-aware one.

Usage:
    responder = MergInference(model_dir)
    pred = responder.predict(m1_bars_ohlc, event_name)
    if pred.is_reaction:
        ... block ...

Integration:
    Called by main._merg_event_risk_gate() when a HIGH-impact event is within
    MERG_EVENT_WINDOW_MIN minutes. Gate passes through (fail-open) on any error.
"""

from __future__ import annotations

import joblib
import numpy as np
import re
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, List

warnings.filterwarnings("ignore")


# ── Gate operating point ─────────────────────────────────────────────────────
# Validated on the sealed test set (2024-2026): at 0.60 the Stage-1 reaction model
# reached ~0.70 precision and ~15 vetoes/year. This is a fixed, tested cutoff — it is
# NOT the F1-optimal threshold (~0.28) stored in the bundle under "threshold".
REACTION_THRESHOLD = 0.60

# Stage-1 reaction bundle (leak-free, window prefix 5).
BUNDLE_NAME = "EURUSD_MERG_v2_stage1_Ensemble.joblib"

# Leak-free window prefix used at training time. Windows are anchored to the release:
#   15..11 = 5 pre-event bars | 10 = release bar | 9..1 = post-event (leaky)
WINDOW_PREFIX = 5


@dataclass
class MergPrediction:
    """Container for MERG Stage-1 inference output (reaction only)."""
    event_name: str
    p_reaction: float
    confidence: float          # == p_reaction (single model, no direction composition)
    features_extracted: bool   # True if M1 bars were available and features built

    @property
    def is_reaction(self) -> bool:
        """True if the event is predicted to produce a directional move."""
        return self.p_reaction >= REACTION_THRESHOLD


# ── Event-name normalisation ─────────────────────────────────────────────────
def normalize_event_name(name: str) -> str:
    """
    Map a calendar event name to the ExportedData.csv convention.

    Calendar names look like "Consumer Price Index (MoM) (Dec) PREL"; the dataset uses
    "Consumer Price Index". We strip parenthetical suffixes and PREL/FINAL markers.
    NOTE: this is best-effort. Many calendar names differ more substantially from the
    dataset names (renames, "s.a." vs "Annualized"), so the event one-hot often falls
    back to `evt_OTHER`. Full name-normalisation is a P1 follow-up.
    """
    if not name:
        return ""
    name = str(name).strip()
    name = re.sub(r"\s*\([^)]*\)", "", name)          # drop "(YoY)", "(Dec)", ...
    name = re.sub(r"\s*(PREL|FINAL|PRELIMINARY)\s*$", "", name, flags=re.I)
    return name.strip()


# ── Feature derivation (mirrors the Stage-1 notebook's build_features, prefix 5) ─

def anatomy_from_ohlc(bars: np.ndarray) -> Dict[int, tuple]:
    """
    Convert (5, 4) OHLC bars (oldest-first) into a {window: (tWick, body, bWick)} dict.

    Window mapping (matches ExportedData.csv):
        window 15 = bars[0] (t-5 min, oldest)
        window 14 = bars[1]
        window 13 = bars[2]
        window 12 = bars[3]
        window 11 = bars[4] (t-1 min, closest to the release)
    """
    wins = list(range(15, 15 - WINDOW_PREFIX, -1))   # [15, 14, 13, 12, 11]
    anatomy = {}
    for i, w in enumerate(wins):
        o, h, l, c = bars[i]
        anatomy[w] = (
            h - max(o, c),   # tWick (upper wick)
            c - o,           # body (signed: +bullish / -bearish)
            min(o, c) - l,   # bWick (lower wick)
        )
    return anatomy


def build_feature_dict(
    anatomy: Dict[int, tuple],
    event_name: str,
    event_top_k: List[str],
    prefix: int = WINDOW_PREFIX,
) -> Dict[str, float]:
    """
    Build the FULL 59-feature vector for the Stage-1 model (raw anatomy + derived
    ratios + cross-window aggregates + event one-hot + is_speech). The model bundle's
    `features` list selects the subset that survived training-time feature selection.

    This must mirror the notebook's build_features() EXACTLY (same ratios, same
    aggregates, same ddof=1 for body_std) or the live prediction will differ from the
    offline validation.
    """
    wins = list(range(15, 15 - prefix, -1))
    feat: Dict[str, float] = {}

    body_vals, asym_vals, range_vals = [], [], []

    for i in wins:
        t, b, bw = anatomy[i]
        rng = t + abs(b) + bw
        feat[f"tWick{i}"] = float(t)
        feat[f"body{i}"] = float(b)
        feat[f"bWick{i}"] = float(bw)
        feat[f"range_{i}"] = float(rng)
        # flat bar (range==0) → ratio defined as 0 (matches notebook .fillna(0))
        feat[f"body_ratio_{i}"] = (abs(b) / rng) if rng > 0 else 0.0
        feat[f"wick_asym_{i}"] = ((t - bw) / rng) if rng > 0 else 0.0
        body_vals.append(float(b))
        asym_vals.append(feat[f"wick_asym_{i}"])
        range_vals.append(float(rng))

    feat["body_sum"] = float(sum(body_vals))
    feat["body_mean"] = float(np.mean(body_vals))
    feat["body_abs_sum"] = float(sum(abs(b) for b in body_vals))
    feat["body_std"] = float(np.std(body_vals, ddof=1))   # pandas .std() default ddof=1
    feat["wick_asym_mean"] = float(np.mean(asym_vals))
    feat["range_sum"] = float(sum(range_vals))
    feat["range_mean"] = float(np.mean(range_vals))

    # Event one-hot (top-K + OTHER) — only events in the bundle's top-K get a column.
    norm = normalize_event_name(event_name)
    for e in event_top_k:
        feat[f"evt_{e}"] = 1.0 if norm == normalize_event_name(e) else 0.0
    feat["evt_OTHER"] = 1.0 if norm not in [normalize_event_name(e) for e in event_top_k] else 0.0

    # Speech family flag.
    feat["is_speech"] = 1.0 if re.search(r"speech|testifies", norm, re.I) else 0.0

    return feat


# ── Main inference class ─────────────────────────────────────────────────────

class MergInference:
    """
    MERG Stage-1 reaction detector — runtime inference.

    Loads the leak-free reaction bundle and exposes a single predict() that returns
    P(reaction). There is no direction composition: the veto is on reaction confidence
    alone (direction was proven to be unpredictable).

    Parameters
    ----------
    model_dir : Path
        Directory containing the Stage-1 reaction bundle.
    """

    def __init__(self, model_dir: Path):
        self.model_dir = Path(model_dir)
        self._ready = False
        self._error = None

        try:
            bundle = joblib.load(self.model_dir / BUNDLE_NAME)

            self.model = bundle["model"]
            self.features: List[str] = bundle["features"]
            self.event_top_k: List[str] = bundle["event_top_k"]
            self.window_prefix: int = int(bundle.get("window_prefix", WINDOW_PREFIX))

            # Validate that every selected feature can actually be built by this module.
            buildable = self._buildable_names()
            missing = [f for f in self.features if f not in buildable]
            if missing:
                raise ValueError(f"Bundle features not buildable at runtime: {missing}")

            self._ready = True

        except FileNotFoundError as e:
            self._error = f"Model bundle not found: {e}"
        except Exception as e:
            self._error = f"Failed to load MERG model: {e}"

    @property
    def ready(self) -> bool:
        return self._ready

    def _buildable_names(self) -> set:
        """All feature names this module can construct (anatomy + derived + event + flag)."""
        wins = list(range(15, 15 - self.window_prefix, -1))
        names = set()
        for i in wins:
            names.update([f"tWick{i}", f"body{i}", f"bWick{i}",
                          f"range_{i}", f"body_ratio_{i}", f"wick_asym_{i}"])
        names.update([
            "body_sum", "body_mean", "body_abs_sum", "body_std",
            "wick_asym_mean", "range_sum", "range_mean", "is_speech",
        ])
        for e in self.event_top_k:
            names.add(f"evt_{e}")
        names.add("evt_OTHER")
        return names

    def predict(self, m1_bars: np.ndarray, event_name: str = "") -> MergPrediction:
        """
        Predict P(reaction) from pre-event M1 bars.

        Parameters
        ----------
        m1_bars : np.ndarray, shape (5, 4)
            5 most recent COMPLETED M1 bars, oldest-first, columns [open, high, low, close].
            row 0 = window 15 (t-5 min), row 4 = window 11 (t-1 min).
        event_name : str
            Calendar event name (will be normalised to the dataset convention).

        Returns
        -------
        MergPrediction with p_reaction, confidence, features_extracted.
        """
        if not self._ready:
            return MergPrediction(
                event_name=event_name, p_reaction=0.0, confidence=0.0,
                features_extracted=False,
            )

        try:
            bars = np.asarray(m1_bars, dtype=float)
            if bars.ndim != 2 or bars.shape[0] < self.window_prefix or bars.shape[1] != 4:
                raise ValueError(
                    f"Expected ({self.window_prefix}, 4) OHLC bars, got {bars.shape}"
                )

            anatomy = anatomy_from_ohlc(bars[-self.window_prefix:])  # take last 5 (most recent)
            feat = build_feature_dict(anatomy, event_name, self.event_top_k, self.window_prefix)

            # Select features in the EXACT order the bundle expects.
            X = np.array([[feat[f] for f in self.features]], dtype=float)

            p_reaction = float(self.model.predict_proba(X)[0, 1])

            return MergPrediction(
                event_name=event_name, p_reaction=p_reaction, confidence=p_reaction,
                features_extracted=True,
            )

        except Exception:
            # Fail-open: neutral on any inference error.
            return MergPrediction(
                event_name=event_name, p_reaction=0.0, confidence=0.0,
                features_extracted=False,
            )


# ── Convenience factory ──────────────────────────────────────────────────────

def load_merg(model_dir: Optional[Path] = None) -> MergInference:
    """Load MERG from the default model directory (fail-open if unavailable)."""
    if model_dir is None:
        model_dir = Path(__file__).resolve().parents[2] / "ml-signal-service" / "models_bin"

    merg = MergInference(model_dir)
    if not merg.ready:
        print(f"[MERG] Not available: {merg._error}")
    return merg
