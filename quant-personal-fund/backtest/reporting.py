"""
Report generation for backtest experiments.

Produces reproducible experiment artifacts: JSON metrics, CSV time series,
and a human-readable summary. All outputs include provenance information
(metadata hash, timestamps) to enable reproducibility verification.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import pandas as pd


def generate_report(
    result,                    # PortfolioResult
    metrics: Dict[str, Any],
    dataset_meta,              # DatasetMetadata
    output_dir: str,
    experiment_id: str = "",
) -> str:
    """
    Write a complete, reproducible experiment artifact.

    Creates:
        report.json   — Metrics, metadata, provenance.
        nav.csv       — Daily gross and net NAV.
        returns.csv   — Daily gross and net returns.
        positions.csv — Daily per-instrument positions.
        costs.csv     — Daily transaction and holding costs.
        turnover.csv  — Daily turnover.
        exposures.csv — Daily gross and net exposure.
        summary.md    — Human-readable summary (if experiment_id provided).

    Args:
        result: PortfolioResult from portfolio.accounting.
        metrics: Dict from risk.metrics.performance_summary.
        dataset_meta: DatasetMetadata from data.pipelines.dataset.
        output_dir: Directory to write artifacts to.
        experiment_id: Optional experiment ID for the summary.

    Returns:
        Path to the output directory.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Time series CSVs
    result.nav.to_csv(out / "nav.csv", float_format="%.8f")
    result.returns.to_csv(out / "returns.csv", float_format="%.8f")
    result.positions.to_csv(out / "positions.csv", float_format="%.6f")
    result.costs.to_csv(out / "costs.csv", float_format="%.8f")
    result.turnover.to_frame("turnover").to_csv(out / "turnover.csv", float_format="%.6f")
    result.exposures.to_csv(out / "exposures.csv", float_format="%.6f")

    # Clean infinities from metrics for JSON serialization
    clean_metrics = {}
    for k, v in metrics.items():
        if isinstance(v, float):
            if v == float("inf"):
                clean_metrics[k] = "inf"
            elif v == float("-inf"):
                clean_metrics[k] = "-inf"
            else:
                clean_metrics[k] = v
        else:
            clean_metrics[k] = v

    # Report JSON
    report = {
        "experiment_id": experiment_id,
        "metrics": clean_metrics,
        "dataset": {
            "dataset_id": dataset_meta.dataset_id,
            "instruments": dataset_meta.instruments,
            "date_range_start": dataset_meta.date_range_start,
            "date_range_end": dataset_meta.date_range_end,
            "inputs_hash": dataset_meta.inputs_hash,
            "validation_errors": dataset_meta.validation_errors,
        },
        "generated_at": datetime.now().isoformat(),
    }
    with open(out / "report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)

    # Human-readable summary
    if experiment_id:
        _write_summary(out / "summary.md", experiment_id, clean_metrics, dataset_meta)

    return str(out)


def _write_summary(
    path: Path,
    experiment_id: str,
    metrics: Dict[str, Any],
    dataset_meta,
) -> None:
    """Write a human-readable markdown summary."""
    lines = [
        f"# {experiment_id} — Backtest Summary",
        f"",
        f"**Generated:** {datetime.now().isoformat()}",
        f"**Dataset:** {dataset_meta.dataset_id}",
        f"**Period:** {dataset_meta.date_range_start} to {dataset_meta.date_range_end}",
        f"**Instruments:** {len(dataset_meta.instruments)}",
        f"**Inputs hash:** {dataset_meta.inputs_hash}",
        f"",
        f"## Performance Metrics",
        f"",
        f"| Metric | Value |",
        f"|---|---|",
    ]

    metric_order = [
        ("annualized_return", "Annualized Return"),
        ("annualized_volatility", "Annualized Volatility"),
        ("cumulative_return", "Cumulative Return"),
        ("sharpe_ratio", "Sharpe Ratio"),
        ("sortino_ratio", "Sortino Ratio"),
        ("calmar_ratio", "Calmar Ratio"),
        ("max_drawdown", "Max Drawdown"),
        ("var_95_daily", "Daily VaR (95%)"),
        ("expected_shortfall_95", "Expected Shortfall (95%)"),
        ("total_cost", "Total Cost"),
        ("cost_to_gross_pnl", "Cost / Gross PnL"),
        ("annualized_turnover", "Annualized Turnover"),
        ("n_days", "Trading Days"),
    ]

    for key, label in metric_order:
        val = metrics.get(key, "N/A")
        if isinstance(val, float):
            if abs(val) < 0.0001 and val != 0:
                val_str = f"{val:.6f}"
            else:
                val_str = f"{val:.4f}"
        else:
            val_str = str(val)
        lines.append(f"| {label} | {val_str} |")

    lines.extend([
        f"",
        f"## Data Quality",
        f"",
        f"- Validation errors: {dataset_meta.validation_errors}",
        f"- Validation warnings: {dataset_meta.total_validation_warnings}",
    ])

    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")