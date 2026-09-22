#!/usr/bin/env python
"""Shared cost-label notebook fork builder (BUY or SELL) — ROADMAP §9 P0.1/P1.

A single direction-parameterized implementation serves every cost-adjusted-label
experiment (EXP-2026-05 SELL, EXP-2026-06 BUY, future crosses). For each
direction it forks the production notebook and applies EXACTLY ONE logic change:

    ``tp_level`` -> ``apply_cost_to_barrier(entry, atr[i], atr_tp_mult, "<DIR>",
                    cost_pips=EXP_COST_PIPS, pair=PAIR)``

Everything else (feature pipeline, split dates, purged-embargo CV, isotonic
calibration, threshold selection) stays byte-identical so the cost variable is
isolated with no confound. The script is idempotent and assertion-guarded:
if any expected source marker is missing it refuses to write a partial fork.

Usage:
    python experiments/_core/build_costlabel_fork.py SELL EXP-2026-05-EURUSD-SELL-COSTLABEL
    python experiments/_core/build_costlabel_fork.py BUY  EXP-2026-06-EURUSD-BUY-COSTLABEL
    python experiments/_core/build_costlabel_fork.py SELL EXP-2026-07-CROSSES-COSTLABEL --pair EURGBP

Deliberate non-goals (do not add here):
- no change to ``_label_rate`` / class-balance exploration helpers,
- no ATR multiplier / feature / model-family changes,
- no change to the production notebooks themselves,
- no change to ``_label`` semantics (BUY keeps its NaN-ambiguous convention).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # ml-signal-service/

DIRECTION_SPEC = {
    "SELL": {
        "src_notebook": "eurusd_sell_improved.ipynb",
        "dst_notebook": "eurusd_sell_costlabel.ipynb",
        "func": "def generate_sell_labels(",
        "tp_old": "tp_level = entry - atr[i] * atr_tp_mult   # price must FALL to this level to win",
        "title_old": "# EURUSD — Sell Model (Y₁)",
        "bundle_prefix": "sell",
        "label_col": "sell_label",
        "prob_col": "prob_sell",
        "results_var": "test_results_sell",
    },
    "BUY": {
        "src_notebook": "eurusd_buy_improved.ipynb",
        "dst_notebook": "eurusd_buy_costlabel.ipynb",
        "func": "def generate_buy_labels(",
        "tp_old": "        tp_level = entry + atr[i] * atr_tp_mult",
        "title_old": "# EURUSD — Buy Model (Y₁)",
        "bundle_prefix": "buy",
        "label_col": "buy_label",
        "prob_col": "prob_buy",
        "results_var": "test_results_buy",
    },
}


def require(source: str, marker: str, count: int = 1) -> None:
    hits = source.count(marker)
    if hits != count:
        raise AssertionError(
            f"marker {marker!r} expected {count}x in target cell, found {hits}x. "
            "Refusing to write a partially-modified fork."
        )


def build(direction: str, exp_id: str, pair: str = "EURUSD",
          atr_tp_mult: float | None = None, atr_sl_mult: float | None = None) -> Path:
    d = DIRECTION_SPEC[direction]
    pair_upper = pair.upper()
    # Cross-pair forks live under notebooks/crosses/ (e.g. EURGBP); EURUSD keeps
    # its historical path so the audited EXP-2026-05/06 forks stay byte-identical.
    if pair_upper == "EURUSD":
        out_dir = "eurusd"
        out_name = d["dst_notebook"]
    else:
        out_dir = "crosses"
        base = f"{pair_upper.lower()}_{d['bundle_prefix']}"
        # geometry redesign forks must NOT clobber the standard cost-label fork
        # (e.g. EXP-2026-09 must not overwrite EXP-2026-08's audited US30 fork).
        version = "_geom" if (atr_tp_mult or atr_sl_mult) else ""
        out_name = f"{base}_costlabel{version}.ipynb"
    src = ROOT / "notebooks" / "eurusd" / d["src_notebook"]
    dst = ROOT / "notebooks" / out_dir / out_name
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        raise FileNotFoundError(f"production notebook not found: {src}")

    nb = json.loads(src.read_text(encoding="utf-8"))

    # ── 0. Config cell: retarget PAIR (micro-change for cross-pair forks) ─────
    # Production config uses `PAIR = "EURUSD"`; data path + macro/calendar lookups
    # are all PAIR-driven, so this single edit redirects the whole pipeline.
    if pair_upper != "EURUSD":
        config_cell = None
        for cell in nb["cells"]:
            cell_src = "".join(cell.get("source", []))
            if cell.get("cell_type") == "code" and 'PAIR      = "EURUSD"' in cell_src:
                config_cell = cell
                break
        if config_cell is None:
            raise AssertionError("config cell with PAIR = \"EURUSD\" not found; "
                                 "refusing to fork a cross-pair blindly.")
        old_pair = 'PAIR      = "EURUSD"'
        new_pair = f'PAIR      = "{pair_upper}"'
        require("".join(config_cell["source"]), old_pair, 1)
        config_cell["source"] = ("".join(config_cell["source"])
                                 .replace(old_pair, new_pair, 1)
                                 .splitlines(keepends=True))

    # ── 0b. Config cell: geometry redesign (EXP-2026-09) — optional ───────────
    # Changes ONLY the ATR TP/SL multipliers in the config cell. Everything else
    # (features, split, CV, calibration, threshold rule) stays untouched, so the
    # fork is still byte-identical except the pre-registered label geometry.
    if atr_tp_mult is not None or atr_sl_mult is not None:
        config_cell = None
        for cell in nb["cells"]:
            if cell.get("cell_type") != "code":
                continue
            cell_src = "".join(cell.get("source", []))
            if cell_src.startswith("from pathlib import Path"):
                config_cell = cell
                break
        if config_cell is None:
            raise AssertionError("config cell (from pathlib import Path) not found")
        cc = "".join(config_cell["source"])
        if atr_tp_mult is not None:
            require(cc, "ATR_TP_MULT  = 1.5", 1)
            cc = cc.replace("ATR_TP_MULT  = 1.5",
                            f"ATR_TP_MULT  = {atr_tp_mult}", 1)
        if atr_sl_mult is not None:
            require(cc, "ATR_SL_MULT  = 1.0", 1)
            cc = cc.replace("ATR_SL_MULT  = 1.0",
                            f"ATR_SL_MULT  = {atr_sl_mult}", 1)
        config_cell["source"] = cc.splitlines(keepends=True)

    label_cell = save_cell = None
    for cell in nb["cells"]:
        if cell.get("cell_type") != "code":
            continue
        cell_src = "".join(cell.get("source", []))
        if d["func"] in cell_src:
            label_cell = cell
        if "joblib.dump(" in cell_src:
            save_cell = cell
    if label_cell is None or save_cell is None:
        raise RuntimeError(f"could not locate {d['func']} and/or joblib.dump cells")

    # ── 1. Label cell: import + cost-aware TP line ───────────────────────────
    src_label = "".join(label_cell.get("source", []))
    require(src_label, d["func"], 1)
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

    tp_old = d["tp_old"].strip()
    require(src_label, tp_old, 1)
    tp_new = (
        f"tp_level = apply_cost_to_barrier(\n"
        f"            entry, atr[i], atr_tp_mult, \"{direction}\",\n"
        f"            cost_pips=EXP_COST_PIPS, pair=PAIR\n"
        f"        )   # cost-adjusted barrier (Issue C)"
    )
    src_label = src_label.replace(tp_old, tp_new, 1)
    label_cell["source"] = src_label.splitlines(keepends=True)

    # ── 2. Save cell: distinct artifact + cost_pips in the bundle ────────────
    src_save = "".join(save_cell.get("source", []))
    old_path = f'model_path = MODELS_DIR / f"{{PAIR}}_{{TIMEFRAME}}_{d["bundle_prefix"]}_{{best_model_name}}.joblib"'
    new_path = f'model_path = MODELS_DIR / f"{{PAIR}}_{{TIMEFRAME}}_{d["bundle_prefix"]}_costlabel_{{best_model_name}}.joblib"'
    require(src_save, old_path, 1)
    src_save = src_save.replace(old_path, new_path, 1)
    if "cost_pips" not in src_save:
        require(src_save, '"forward_bars": FORWARD_BARS,', 1)
        src_save = src_save.replace(
            '"forward_bars": FORWARD_BARS,',
            '"forward_bars": FORWARD_BARS,\n        "cost_pips": EXP_COST_PIPS,\n        "label": "cost_adjusted_v1",',
            1,
        )
    save_cell["source"] = src_save.splitlines(keepends=True)

    # ── 3. Title markdown: annotate the variant (cosmetic) ───────────────────
    exp_tag = f"EXP-2026-06" if direction == "BUY" else "EXP-2026-05"
    title_key = d["title_old"] if pair_upper == "EURUSD" else f"# {pair_upper} — {d['bundle_prefix'].capitalize()} Model (Y₁)"
    for cell in nb["cells"]:
        if cell.get("cell_type") != "markdown":
            continue
        src_md = "".join(cell.get("source", []))
        if title_key in src_md and "cost-adjusted" not in src_md:
            src_md = src_md.replace(
                title_key,
                f"{title_key} — COST-ADJUSTED LABEL ({exp_tag})\n"
                "**Variant:** TP barrier includes round-trip friction "
                "(`experiments/_core/costs.py`). All other logic byte-identical "
                f"to `{d['src_notebook']}`.",
            )
            cell["source"] = src_md.splitlines(keepends=True)
            break

    # ── 4. Reporting cell (Issue B: block-bootstrap CI on EV/R) ──────────────
    report_cell = _report_cell_source(d, exp_id, pair_upper)
    nb["cells"].append(
        {"cell_type": "code", "execution_count": None, "metadata": {},
         "outputs": [], "source": report_cell.splitlines(keepends=True)}
    )

    dst.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"OK  wrote cost-label fork → {dst}")
    return dst


def _report_cell_source(d: dict, exp_id: str, pair: str = "EURUSD") -> str:
    """Build the sealed-test reporting cell for either direction."""
    return (
        f"# ── {exp_id} sealed-test report (block-bootstrap CI, Issue B) ────────\n"
        "import json\n"
        "from experiments._core.bootstrap import block_bootstrap_ci, default_block_length\n"
        "\n"
        f"{d['results_var']}[\"realized_r\"] = np.where(\n"
        f"    {d['results_var']}[{d['label_col']!r}] == 1, ATR_TP_MULT, -ATR_SL_MULT\n"
        ")\n"
        f"sig = {d['results_var']}[{d['results_var']}[\"signal\"] == 1].copy()\n"
        "n_signals = int(len(sig))\n"
        f"precision = float(sig[{d['label_col']!r}].mean()) if n_signals else 0.0\n"
        "recall = float(\n"
        f"    sig[{d['label_col']!r}].sum() / max(1, int({d['results_var']}[{d['label_col']!r}].sum()))\n"
        ")\n"
        f"roc_auc = float(roc_auc_score({d['results_var']}[{d['label_col']!r}], {d['results_var']}[{d['prob_col']!r}]))\n"
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
        f"REPORT_DIR = ROOT / \"experiments\" / \"{exp_id}\" / \"reports\"\n"
        "REPORT_DIR.mkdir(parents=True, exist_ok=True)\n"
        f"DIR_LABEL = {d['bundle_prefix']!r}   # 'sell' | 'buy'\n"
        "STEM = f\"{PAIR}_{DIR_LABEL}\"   # e.g. US30_sell / EURUSD_buy\n"
        "(REPORT_DIR / f\"{STEM}_test_metrics.json\").write_text(json.dumps(metrics, indent=2))\n"
        "sig.to_csv(REPORT_DIR / f\"{STEM}_test_signals.csv\", index=False)\n"
        "print(json.dumps(metrics, indent=2))\n"
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Build a cost-adjusted notebook fork.")
    ap.add_argument("direction", choices=["SELL", "BUY"], help="label direction")
    ap.add_argument("exp_id", help="experiment folder id, e.g. EXP-2026-06-EURUSD-BUY-COSTLABEL")
    ap.add_argument("--pair", default="EURUSD", help="instrument (default EURUSD)")
    ap.add_argument("--atr-tp-mult", type=float, default=None,
                    help="override ATR TP multiplier (geometry redesign)")
    ap.add_argument("--atr-sl-mult", type=float, default=None,
                    help="override ATR SL multiplier (geometry redesign)")
    args = ap.parse_args()
    build(args.direction, args.exp_id, pair=args.pair,
          atr_tp_mult=args.atr_tp_mult, atr_sl_mult=args.atr_sl_mult)


if __name__ == "__main__":
    main()