"""
JSONL signal logger.

Writes fired and shelved signals to append-only JSONL files.
One JSON object per line, immutable audit trail.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def _month_path(timestamp: datetime) -> Path:
    """Build output path: output/signals/YYYY-MM/YYYY-MM-DD.jsonl"""
    month_dir = timestamp.strftime("%Y-%m")
    day_file  = timestamp.strftime("%Y-%m-%d.jsonl")
    return OUTPUT_DIR / "signals" / month_dir / day_file


def log_signal(
    signal: Dict[str, Any],
    output_dir: Optional[Path] = None,
) -> str:
    """
    Append a signal record to the JSONL log.

    Parameters
    ----------
    signal : dict
        Must contain at minimum: signal_id, symbol, direction, timestamp_utc,
        model.probability, final_decision.
    output_dir : Path, optional
        Override output directory.

    Returns
    -------
    str — path to the file written.
    """
    base = output_dir or OUTPUT_DIR
    ts = datetime.fromisoformat(signal["timestamp_utc"])
    filepath = base / "signals" / ts.strftime("%Y-%m") / ts.strftime("%Y-%m-%d.jsonl")

    os.makedirs(filepath.parent, exist_ok=True)

    with open(filepath, "a", encoding="utf-8") as f:
        f.write(json.dumps(signal, default=str) + "\n")

    return str(filepath)


def write_summary_report(
    run_id: str,
    summary: Dict[str, Any],
    output_dir: Optional[Path] = None,
) -> str:
    """
    Write a backtest summary report as JSON.

    Parameters
    ----------
    run_id : str
        Unique identifier for this run.
    summary : dict
        Gate summary, signal counts, date range, config snapshot.
    output_dir : Path, optional

    Returns
    -------
    str — path to the report file.
    """
    base = output_dir or OUTPUT_DIR
    report_dir = base / "reports"
    os.makedirs(report_dir, exist_ok=True)

    filename = f"backtest_{run_id}.json"
    filepath = report_dir / filename

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)

    return str(filepath)