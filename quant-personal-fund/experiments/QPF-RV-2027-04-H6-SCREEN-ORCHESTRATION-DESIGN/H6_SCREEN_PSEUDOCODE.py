"""H6 screen orchestration — implementation pseudocode (NON-EXECUTABLE).

Pseudocode-style signatures + docstrings ONLY. No real paths, no data-access
imports, no execution entry point, and no market computation. This file is a
design artifact, not a runnable screen.

Frozen H6 rules: N in {12,24,48}; M in {2,4,8}; H in {4,8,24}; event classes
FAILED_UPWARD_BREAKOUT / FAILED_DOWNWARD_BREAKOUT.
FX and XAUUSD are SEPARATE strata and are never pooled, ranked together, or
jointly BH-corrected. Labels are NOT_UTC. No PnL, no trading. Sealed is used
only to confirm selected configurations.
"""


def verify_snapshot_hash(snapshot_path, expected_sha256):
    """Verify a snapshot SHA256 BEFORE parsing. Return ok/actual hash.
    No market calculation; hash/format check only."""
    ...


def load_and_validate_snapshot(snapshot_path):
    """Load one single-instrument snapshot with comment="#" and validate its
    schema (internal_index_k, timestamp_label_internal, <instrument>_close),
    index 1..T, monotonic labels (NOT_UTC), finite positive closes. No
    cross-instrument alignment. Fail closed on any violation."""
    ...


def make_h6_splits(T, embargo_bars=30):
    """Return train/validation/sealed ordinal bounds with 30-bar embargoes.
    Embargo bars never enter any feature/event/control/outcome. Train is
    descriptive only; validation performs selection; sealed confirms."""
    ...


def rolling_range(close, N):
    """U_t(N)=max(close[t-N..t-1]); L_t(N)=min(close[t-N..t-1]) (close-only)."""
    ...


def find_failed_breakout_events(close, N, M, event_class):
    """Detect failed breakouts (strict inequalities); event index e = t + k* is
    the FIRST strict re-entry into the prior range. One event per class."""
    ...


def deduplicate_event_intervals(events):
    """Process breakout starts ascending; after event e search only after e;
    ties keep the earlier breakout start; never delete by future outcome."""
    ...


def assign_events_to_segment(events, splits):
    """Assign an event only if breakout start t, the whole invalidation interval
    [t+1,t+M], confirmation e, and full outcome through e+H are all inside one
    segment, using no embargo bars."""
    ...


def build_deterministic_controls(close, segment_bounds, events, N, M, H, event_class):
    """Deterministic same-segment controls matched by (e - segment_start) mod H
    phase; eligible non-event bars; all eligible controls used (no downsampling).
    No randomness, no propensity model."""
    ...


def compute_future_log_outcome(close, event_index, H):
    """y_e(H)=log(close[e+H]/close[e]); statistical target only (never PnL)."""
    ...


def make_event_control_table(close, events, controls, H, event_class):
    """Aligned event/control outcome table with z = ExpectedSign * y and a group
    indicator."""
    ...


def hac_event_control_test(y_event, y_control, H):
    """Intercept-plus-event-indicator regression with HAC/Newey-West maxlags=H-1
    (two-sided). Return Delta, SE, t, p, counts, aligned mean, aligned difference,
    hit rate. No PnL/return interpretation."""
    ...


def nonoverlap_event_control_robustness(close, events, controls, H, event_class):
    """Deterministic non-overlapping subset (earliest kept; subsequent starts
    within next H-1 bars excluded). Return counts, aligned difference, hit rate."""
    ...


def evaluate_h6_specification(close, instrument, N, M, H, event_class, splits):
    """Collect the frozen statistics for one instrument/N/M/H/class on a segment.
    Single-instrument only; no pooling with other instruments."""
    ...


def apply_bh_within_stratum(records, stratum, fdr_q=0.10):
    """Benjamini-Hochberg FDR within ONE stratum family (FX=324 or XAUUSD=54).
    Null p-values stay in the table with null rank/q and are excluded from the
    numeric ranking. Families are never combined."""
    ...


def find_h6_validation_survivors(validation_grid, stratum):
    """Survivor = bound configuration (instrument, N, M, H) where BOTH event
    classes satisfy the frozen eight checks (>=30 events, >=200 controls,
    favorable delta, positive aligned mean, positive aligned delta, HAC p<0.05,
    BH q<=0.10, favorable non-overlap sign). Within-stratum only."""
    ...


def rank_h6_configurations(survivors, max_selected=3):
    """Rank survivors within a stratum by the frozen order; select at most three."""
    ...


def confirm_h6_on_sealed(close, selected_configs, splits, stratum):
    """Re-test each frozen configuration once on sealed (both classes, same
    rules; no BH reranking). Sealed is confirmatory only and never selects."""
    ...


def make_stratum_decision(selected_configs, sealed_confirmation, integrity_ok, stratum):
    """Return APPROVE/REJECT/PAUSE for one stratum. Approval requires >=1 selected
    configuration passing sealed. A failure in one stratum never affects the
    other. No PnL/trading conclusion."""
    ...


def make_global_h6_summary(fx_decision, xauusd_decision):
    """Combine the two independent stratum decisions into a descriptive summary.
    FX and XAUUSD stay separate; no pooled test, ranking, or BH correction."""
    ...
