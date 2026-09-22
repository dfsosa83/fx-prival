#!/usr/bin/env python
"""EXP-2026-05 build script — fork EURUSD SELL notebook to a cost-adjusted label.

ROADMAP-2026-Q4-RESEARCH.md §9 P0.1:
    fork of ``eurusd_sell_improved.ipynb``; the only logic change is in
    ``generate_sell_labels``: ``tp_level`` is replaced by
    ``apply_cost_to_barrier(...)`` from ``experiments/_core/costs.py`` using
    ``ROUND_TRIP_COST_PIPS[PAIR]["ALL"]``. Everything else (feature pipeline,
    split dates, purged embargo CV, isotonic calibration, threshold selection)
    stays byte-identical so the cost variable is isolated with no confound.

This script is re-runnable and idempotent: it loads the production notebook,
applies strictly asserted string replacements, and writes the cost-label fork.
If any expected marker is missing the script errors out instead of writing a
partially-modified notebook.

Deliberate non-goals (do not add here):
- no change to ``_label_rate`` (train-window class-balance exploration helper;
  leaving it unadjusted is part of the control),
- no ATR multiplier / feature / model-family changes,
- no change to the production notebook itself.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # ml-signal-service/
SRC = ROOT / "notebooks" / "eurusd" / "eurusd_sell_improved.ipynb"
DST = ROOT / "notebooks" / "eurusd" / "eurusd_sell_costlabel.ipynb"

PAIR = "EURUSD"


def require(source: str, marker: str, count: int = 1) -> None:
    hits = source.count(marker)
    if hits != count:
        raise AssertionError(
            f"marker {marker!r} expected {count}x in target cell, found {hits}x. "
            "Refusing to write a partially-modified fork."
        )


def build() -> None:
    if not SRC.exists():
        raise FileNotFoundError(f"production notebook not found: {SRC}")

    nb = json.loads(SRC.read_text(encoding="utf-8"))

    label_cell = None
    save_cell = None
    for cell in nb["cells"]:
        src = "".join(cell.get("source", []))
        if cell.get("cell_type") == "code":
            if "def generate_sell_labels(" in src:
                label_cell = cell
            if "joblib.dump(" in src:
                save_cell = cell

    if label_cell is None or save_cell is None:
        raise RuntimeError("could not locate generate_sell_labels and/or joblib.dump cells")

    # ── 1. Label cell: import + cost-aware TP line ───────────────────────────
    src_label = "".join(label_cell.get("source", []))
    require(src_label, 'def generate_sell_labels(', 1)

    import_block = (
        "import sys\n"
        "if str(ROOT) not in sys.path:\n"
        "    sys.path.insert(0, str(ROOT))\n"
        "from experiments._core.costs import ROUND_TRIP_COST_PIPS, apply_cost_to_barrier\n"
        "EXP_COST_PIPS = ROUND_TRIP_COST_PIPS[PAIR][\"ALL\"]\n"
        "\n"
    )
    if "EXP_COST_PIPS" not in src_label:
        src_label = import_block + src_label

    old_tp = 'tp_level = entry - atr[i] * atr_tp_mult   # price must FALL to this level to win'
    new_tp = (
        'tp_level = apply_cost_to_barrier(\n'
        '            entry, atr[i], atr_tp_mult, "SELL",\n'
        '            cost_pips=EXP_COST_PIPS, pair=PAIR\n'
        '        )   # cost-adjusted barrier: price must fall further (Issue C)'
    )
    require(src_label, old_tp)
    src_label = src_label.replace(old_tp, new_tp)

    label_cell["source"] = src_label.splitlines(keepends=True)

    # ── 2. Save cell: distinct artifact name + persist cost_pips in the bundle ─
    # CRITICAL: MUST NOT overwrite the production model bundle ever.
    # Production writes EURUSD_H1_sell_<model>.joblib (used live by A1's
    # frival/main.py); the fork writes EURUSD_H1_sell_costlabel_<model>.joblib.
    src_save = "".join(save_cell.get("source", []))
    require(
        src_save,
        'model_path = MODELS_DIR / f"{PAIR}_{TIMEFRAME}_sell_{best_model_name}.joblib"',
        1,
    )
    src_save = src_save.replace(
        'model_path = MODELS_DIR / f"{PAIR}_{TIMEFRAME}_sell_{best_model_name}.joblib"',
        'model_path = MODELS_DIR / f"{PAIR}_{TIMEFRAME}_sell_costlabel_{best_model_name}.joblib"',
        1,
    )
    if "cost_pips" not in src_save:
        require(src_save, '"forward_bars": FORWARD_BARS,', 1)
        src_save = src_save.replace(
            '"forward_bars": FORWARD_BARS,',
            '"forward_bars": FORWARD_BARS,\n        "cost_pips": EXP_COST_PIPS,\n        "label": "cost_adjusted_v1",',
            1,
        )
    save_cell["source"] = src_save.splitlines(keepends=True)

    # ── 3. Title markdown: annotate the variant (cosmetic, no logic impact) ──
    for cell in nb["cells"]:
        if cell.get("cell_type") == "markdown":
            src_md = "".join(cell.get("source", []))
            if "# EURUSD — Sell Model (Y₁)" in src_md and "cost-adjusted" not in src_md:
                src_md = src_md.replace(
                    "# EURUSD — Sell Model (Y₁)",
                    "# EURUSD — Sell Model (Y₁) — COST-ADJUSTED LABEL (EXP-2026-05)\n"
                    "**Variant:** TP barrier includes round-trip friction "
                    "(`experiments/_core/costs.py`). All other logic byte-identical "
                    "to `eurusd_sell_improved.ipynb`.",
                )
                cell["source"] = src_md.splitlines(keepends=True)
                break

    # ── 4. Append sealed-test reporting cell (P0.1 outputs spec) ─────────────
    # Emits reports/test_metrics.json + reports/test_signals.csv with the
    # block-bootstrap CI on EV/R (Issue B). Runs AFTER cell 41 so it sees
    # test_results_sell / OPTIMAL_THRESHOLD / breakeven / ATR_* / FORWARD_BARS.
    report_cell_source = (
        "# ── EXP-2026-05 sealed-test report (block-bootstrap CI, Issue B) ─────\n"
        "import json\n"
        "from experiments._core.bootstrap import block_bootstrap_ci, default_block_length\n"
        "\n"
        "test_results_sell[\"realized_r\"] = np.where(\n"
        "    test_results_sell[\"sell_label\"] == 1, ATR_TP_MULT, -ATR_SL_MULT\n"
        ")\n"
        "sig = test_results_sell[test_results_sell[\"signal\"] == 1].copy()\n"
        "n_signals = int(len(sig))\n"
        "precision = float(sig[\"sell_label\"].mean()) if n_signals else 0.0\n"
        "recall = float(\n"
        "    sig[\"sell_label\"].sum() / max(1, int(test_results_sell[\"sell_label\"].sum()))\n"
        ")\n"
        "roc_auc = float(roc_auc_score(test_results_sell[\"sell_label\"], test_results_sell[\"prob_sell\"]))\n"
        "\n"
        "if n_signals >= 2:\n"
        "    gaps = sig[\"datetime\"].diff().dt.total_seconds().div(3600).dropna()\n"
        "    median_gap = float(gaps.median()) if len(gaps) else 0.0\n"
        "    block_len = default_block_length(FORWARD_BARS, median_gap)\n"
        "    ev, lo, hi = block_bootstrap_ci(sig[\"realized_r\"].values, block_length=block_len)\n"
        "else:\n"
        "    block_len, ev, lo, hi = 0, 0.0, 0.0, 0.0\n"
        "\n"
        "metrics = {\n"
        "    \"precision\": round(precision, 5),\n"
        "    \"recall\": round(recall, 5),\n"
        "    \"roc_auc\": round(roc_auc, 5),\n"
        "    \"n_signals\": n_signals,\n"
        "    \"ev_per_r\": round(ev, 5),\n"
        "    \"ev_ci_95_lo\": round(lo, 5),\n"
        "    \"ev_ci_95_hi\": round(hi, 5),\n"
        "    \"breakeven\": breakeven,\n"
        "    \"block_length_used\": block_len,\n"
        "}\n"
        "REPORT_DIR = ROOT / \"experiments\" / \"EXP-2026-05-EURUSD-SELL-COSTLABEL\" / \"reports\"\n"
        "REPORT_DIR.mkdir(parents=True, exist_ok=True)\n"
        "(REPORT_DIR / \"test_metrics.json\").write_text(json.dumps(metrics, indent=2))\n"
        "sig.to_csv(REPORT_DIR / \"test_signals.csv\", index=False)\n"
        "print(json.dumps(metrics, indent=2))\n"
    )
    nb["cells"].append(
        {"cell_type": "code", "execution_count": None, "metadata": {},
         "outputs": [], "source": report_cell_source.splitlines(keepends=True)}
    )

    DST.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"OK  wrote cost-label fork → {DST}")


if __name__ == "__main__":
    build()