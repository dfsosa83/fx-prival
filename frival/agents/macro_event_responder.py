"""
MERG — Macro Event Response Gate inference module.

Loads trained two-stage classifier bundles and provides runtime prediction
for pre-event M1 candlestick anatomy → post-release reaction direction.

Usage:
    responder = MergInference(model_dir)
    prediction = responder.predict(m1_bars_df, event_name)

Architecture:
    Stage 1 — binary reaction detector: will this event produce a move?
    Stage 2 — binary direction classifier (conditional): which way?
    Runtime composition: p_U = p_reaction * p_up, p_D = p_reaction * (1-p_up), p_N = 1-p_reaction

Integration:
    Called by signal_gate.event_risk_gate() when a HIGH-impact event is within
    EVENT_WINDOW_MIN minutes. Gate passes through if MergInference returns None
    (fail-open on any error).
"""

from __future__ import annotations

import joblib
import numpy as np
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Any

warnings.filterwarnings("ignore")


# ── Feature derivation (mirrors notebook Cell 2) ────────────────────────────

def derive_features(bars: np.ndarray) -> np.ndarray:
    """
    Derive microstructure features from 15-window M1 candlestick anatomy.

    Parameters
    ----------
    bars : np.ndarray, shape (1, 45)
        Raw features in order: [tWick15, body15, bWick15, ..., tWick1, body1, bWick1].
        45 columns: 15 windows × 3 components (tWick, body, bWick).

    Returns
    -------
    np.ndarray, shape (1, N)
        Full feature vector matching the selected feature list from training.
        N = 45 base + derived (range, body_ratio, wick_asym, body_sign, cumulative momentum).
    """
    n_windows = 15
    derived = []

    for i in range(1, n_windows + 1):
        idx = (n_windows - i) * 3  # window 15 is first, window 1 is last
        tw = bars[0, idx]       # top wick
        bd = bars[0, idx + 1]   # body (signed: negative=bearish)
        bw = bars[0, idx + 2]   # bottom wick

        total_range = tw + abs(bd) + bw + 1e-9
        derived.append(total_range)               # range_i
        derived.append(abs(bd) / total_range)     # body_ratio_i
        derived.append((tw - bw) / total_range)   # wick_asym_i
        derived.append(np.sign(bd))               # body_sign_i

    # Cumulative momentum over recent windows
    body_cols = [bars[0, (n_windows - j) * 3 + 1] for j in range(1, n_windows + 1)]
    derived.append(sum(body_cols[0:3]))    # cum_body_1_3
    derived.append(sum(body_cols[0:5]))    # cum_body_1_5
    derived.append(sum(body_cols))         # cum_body_1_15

    # Body sign agreement (fraction of last 5 bars with same sign)
    signs = [np.sign(b) for b in body_cols[0:5]]
    derived.append(abs(sum(signs)) / 5)    # body_sign_agree_1_5

    # Max wick asymmetry in recent windows
    asyms = [abs((bars[0, (n_windows - j) * 3] - bars[0, (n_windows - j) * 3 + 2]) /
                  (bars[0, (n_windows - j) * 3] + abs(bars[0, (n_windows - j) * 3 + 1]) +
                   bars[0, (n_windows - j) * 3 + 2] + 1e-9)) for j in range(1, 6)]
    derived.append(max(asyrms))             # max_wick_asym_1_5

    return np.concatenate([bars.flatten(), derived]).reshape(1, -1)


# ── Prediction dataclass ─────────────────────────────────────────────────────

@dataclass
class MergPrediction:
    """Container for MERG inference output."""
    event_name: str
    p_U: float
    p_D: float
    p_N: float
    predicted_class: str       # "U", "D", or "N"
    confidence: float          # max(p_U, p_D, p_N)
    p_reaction: float          # raw Stage 1 probability
    p_up: float                # raw Stage 2 probability (conditional)
    features_extracted: bool   # True if M1 bars were available

    @property
    def is_confident(self) -> bool:
        """Prediction exceeds confidence threshold."""
        return self.confidence >= 0.60

    @property
    def is_reaction(self) -> bool:
        """Stage 1 predicts a directional move."""
        return self.p_reaction >= 0.50


# ── Main inference class ─────────────────────────────────────────────────────

class MergInference:
    """
    Macro Event Response Gate — runtime inference.

    Loads two-stage trained model bundles and provides prediction
    from pre-event M1 candlestick anatomy.

    Parameters
    ----------
    model_dir : Path
        Directory containing MERG_v1_reaction.joblib and MERG_v1_direction.joblib.
    """

    def __init__(self, model_dir: Path):
        self.model_dir = Path(model_dir)

        reaction_path = self.model_dir / "MERG_v1_reaction.joblib"
        direction_path = self.model_dir / "MERG_v1_direction.joblib"

        self._ready = False
        self._error = None

        try:
            bundle_s1 = joblib.load(reaction_path)
            bundle_s2 = joblib.load(direction_path)

            self.reaction_model = bundle_s1["model"]
            self.reaction_threshold = bundle_s1.get("threshold", 0.5)
            self.reaction_features = bundle_s1["features"]

            self.direction_model = bundle_s2["model"]
            self.direction_threshold = bundle_s2.get("threshold", 0.5)
            self.direction_features = bundle_s2["features"]

            # Validate feature list consistency
            if self.reaction_features != self.direction_features:
                raise ValueError(
                    f"Feature mismatch between stage bundles: "
                    f"{len(self.reaction_features)} vs {len(self.direction_features)}"
                )

            self.features = self.reaction_features
            self._ready = True

        except FileNotFoundError as e:
            self._error = f"Model bundle not found: {e}"
        except Exception as e:
            self._error = f"Failed to load MERG model: {e}"

    @property
    def ready(self) -> bool:
        """True if both model bundles loaded successfully."""
        return self._ready

    def predict(self, m1_bars: np.ndarray,
                event_name: str = "") -> MergPrediction:
        """
        Predict post-event reaction from pre-event M1 candlestick anatomy.

        Parameters
        ----------
        m1_bars : np.ndarray, shape (15, 4) or (1, 45)
            Last 15 M1 bars before event release.
            Format A: 15 rows × [open, high, low, close] — computes anatomy.
            Format B: 1 row × 45 columns [tWick15, body15, ... tWick1, body1, bWick1].
        event_name : str
            Event name for logging/context.

        Returns
        -------
        MergPrediction with p_U, p_D, p_N, predicted_class, confidence.
        """
        if not self._ready:
            return MergPrediction(
                event_name=event_name, p_U=0.0, p_D=0.0, p_N=1.0,
                predicted_class="N", confidence=0.0,
                p_reaction=0.0, p_up=0.0, features_extracted=False,
            )

        try:
            # Normalize input to 45-column anatomy vector
            if m1_bars.ndim == 2 and m1_bars.shape[0] == 15 and m1_bars.shape[1] == 4:
                anatomy = self._bars_to_anatomy(m1_bars)
            elif m1_bars.ndim == 2 and m1_bars.shape[1] == 45:
                anatomy = m1_bars
            else:
                raise ValueError(
                    f"Expected (15,4) OHLC or (1,45) anatomy, got {m1_bars.shape}"
                )

            # Derive full feature vector and select model features
            X_full = derive_features(anatomy)
            X_all = X_full[0]
            feature_indices = self._feature_indices()
            X_selected = X_all[feature_indices].reshape(1, -1)

            # Stage 1 — reaction probability
            p_reaction = float(
                self.reaction_model.predict_proba(X_selected)[0, 1]
            )

            # Stage 2 — direction probability (conditional)
            p_up = float(
                self.direction_model.predict_proba(X_selected)[0, 1]
            )

            # Compose
            p_U = p_reaction * p_up
            p_D = p_reaction * (1.0 - p_up)
            p_N = 1.0 - p_reaction

            probs = {"U": p_U, "D": p_D, "N": p_N}
            predicted_class = max(probs, key=probs.get)
            confidence = probs[predicted_class]

            return MergPrediction(
                event_name=event_name, p_U=p_U, p_D=p_D, p_N=p_N,
                predicted_class=predicted_class, confidence=confidence,
                p_reaction=p_reaction, p_up=p_up, features_extracted=True,
            )

        except Exception:
            # Fail-open: return neutral on any inference error
            return MergPrediction(
                event_name=event_name, p_U=0.0, p_D=0.0, p_N=1.0,
                predicted_class="N", confidence=0.0,
                p_reaction=0.0, p_up=0.0, features_extracted=False,
            )

    def _bars_to_anatomy(self, bars: np.ndarray) -> np.ndarray:
        """Convert (15, 4) OHLC bars to (1, 45) candlestick anatomy."""
        anatomy = []
        for i in range(15):
            o, h, l, c = bars[i]
            tw = h - max(o, c)       # top wick
            bd = c - o               # signed body
            bw = min(o, c) - l       # bottom wick
            anatomy.extend([tw, bd, bw])
        return np.array(anatomy).reshape(1, -1)

    def _feature_indices(self) -> np.ndarray:
        """
        Map the selected feature names to column indices in the full feature matrix.

        The full feature matrix layout:
          base: [tWick15, body15, bWick15, ..., tWick1, body1, bWick1]  (45 cols)
          derived: [range_1, body_ratio_1, wick_asym_1, body_sign_1,  (60 cols)
                    ..., cum_body_1_3, cum_body_1_5, cum_body_1_15,
                    body_sign_agree_1_5, max_wick_asym_1_5]
        Total: 45 + 60 = 105 columns.
        """
        # Build full feature name list matching derive_features() output order
        base_names = []
        for i in range(15, 0, -1):
            for comp in ["tWick", "body", "bWick"]:
                base_names.append(f"{comp}{i}")

        derived_names = []
        for i in range(1, 16):
            for suffix in ["range", "body_ratio", "wick_asym", "body_sign"]:
                derived_names.append(f"{suffix}_{i}")
        derived_names.extend([
            "cum_body_1_3", "cum_body_1_5", "cum_body_1_15",
            "body_sign_agree_1_5", "max_wick_asym_1_5",
        ])

        all_names = base_names + derived_names
        name_to_idx = {n: i for i, n in enumerate(all_names)}

        indices = []
        for feat in self.features:
            if feat in name_to_idx:
                indices.append(name_to_idx[feat])
        return np.array(indices, dtype=int)


# ── Convenience factory ──────────────────────────────────────────────────────

def load_merg(model_dir: Optional[Path] = None) -> MergInference:
    """
    Load MERG from default model directory.
    Falls back to a no-op instance if models aren't available.
    """
    if model_dir is None:
        model_dir = Path(__file__).resolve().parents[2] / "ml-signal-service" / "models_bin"

    merg = MergInference(model_dir)
    if not merg.ready:
        print(f"[MERG] Not available: {merg._error}")
    return merg