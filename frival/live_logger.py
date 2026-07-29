"""
Live session logger — captures all terminal output to a daily log file.

Usage:
  from live_logger import LiveLogger
  with LiveLogger() as log:
      print("this goes to terminal AND frival/output/logs/YYYY-MM-DD_live.log")
"""

import os
import sys
from datetime import datetime
from pathlib import Path


LOG_DIR = Path(__file__).resolve().parent / "output" / "logs"


class LiveLogger:
    """
    Context manager that tees stdout to a daily live log file.

    All print() output during the context block is written to both
    the terminal and frival/output/logs/YYYY-MM-DD_live.log.
    """

    def __init__(self):
        self.file = None
        self.original_stdout = sys.stdout

    def __enter__(self):
        os.makedirs(LOG_DIR, exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        log_path = LOG_DIR / f"{today}_live.log"

        self.file = open(log_path, "a", encoding="utf-8")
        self.file.write(f"\n{'=' * 60}\n")
        self.file.write(f"Session started: {datetime.now().isoformat()}\n")
        self.file.write(f"{'=' * 60}\n")
        self.file.flush()

        sys.stdout = _TeeOutput(self.original_stdout, self.file)
        return log_path

    def __exit__(self, *args):
        sys.stdout = self.original_stdout
        if self.file:
            self.file.write(f"{'=' * 60}\n")
            self.file.write(f"Session ended: {datetime.now().isoformat()}\n\n")
            self.file.close()


class _TeeOutput:
    """Writes to two streams simultaneously (terminal + file)."""

    def __init__(self, terminal, file):
        self.terminal = terminal
        self.file = file

    def write(self, message):
        self.terminal.write(message)
        self.file.write(message)

    def flush(self):
        self.terminal.flush()
        self.file.flush()

    def isatty(self):
        return self.terminal.isatty()