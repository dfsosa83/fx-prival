"""Safe H1 raw-CSV schema rebuild utility (isolated, path-explicit, offline).

Rebuilds a legacy or canonical raw H1 CSV into the frozen canonical schema:

    datetime,open,high,low,close,volume

This module is generic and path-explicit. It contains NO production paths, NO
symbol names, NO MT5/downloader/broker/network/credentials/environment access,
and NO automatic execution entry point. Any production use requires a separate
explicit authorization.

Datetime labels are treated as OPAQUE strings (NOT_UTC): never parsed,
localized, or inferred.
"""
from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

CANONICAL_COLUMNS = ["datetime", "open", "high", "low", "close", "volume"]
LEGACY_COLUMNS = ["open", "high", "low", "close", "volume", "datetime"]
_NUMERIC_COLUMNS = ["open", "high", "low", "close", "volume"]
_SCHEMA_CANONICAL = "canonical"
_SCHEMA_LEGACY = "legacy"


class SchemaError(Exception):
    """Unsupported or malformed input schema."""


class ValidationError(Exception):
    """Canonical-frame validation failure."""


class MergeConflictError(Exception):
    """Two rows share a datetime but differ in one or more fields."""


class BackupError(Exception):
    """Backup path invalid, out of directory, or already existing."""


class WriteValidationError(Exception):
    """Candidate write/re-read/replace failed."""


def sha256_file(path: Path) -> str:
    """Return the uppercase SHA256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def _assert_valid_datetime_labels(dt: pd.Series) -> None:
    """Reject invalid datetime labels WITHOUT parsing or altering them.

    Invalid: null/NaN; empty string; whitespace-only; literal "nan"/"NaN"
    (case-insensitive, after stripping). Opaque non-empty labels are untouched.
    Must be called BEFORE any astype(str) conversion so a null label cannot be
    masked into the string "nan".
    """
    if dt.isna().any():
        raise ValidationError("null datetime label")
    stripped = dt.astype(str).str.strip()
    if (stripped == "").any():
        raise ValidationError("empty/whitespace datetime label")
    if stripped.str.lower().eq("nan").any():
        raise ValidationError("literal 'nan' datetime label")


def detect_schema(csv_path: Path) -> str:
    """Detect the input schema from the HEADER ONLY.

    Returns "canonical" or "legacy"; raises SchemaError for any other header
    (including unnamed/index columns or a different column set/order).
    """
    with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
        header = f.readline().strip()
    columns = [c.strip() for c in header.split(",")]
    if columns == CANONICAL_COLUMNS:
        return _SCHEMA_CANONICAL
    if columns == LEGACY_COLUMNS:
        return _SCHEMA_LEGACY
    raise SchemaError(f"unsupported schema: {columns}")


def read_and_normalize(csv_path: Path) -> pd.DataFrame:
    """Read a CSV (after schema detection) and return a validated canonical frame.

    Normalization reorders columns BY NAME (never by position); datetime is kept
    as an opaque string; numeric columns are coerced and validated.
    """
    schema = detect_schema(csv_path)                 # header check BEFORE pandas read
    frame = pd.read_csv(csv_path)
    columns = list(frame.columns)
    if any(str(c).startswith("Unnamed") for c in columns) or "index" in columns:
        raise SchemaError(f"unexpected index/unnamed column: {columns}")
    if len(columns) != len(CANONICAL_COLUMNS) or set(columns) != set(CANONICAL_COLUMNS):
        raise SchemaError(f"unexpected columns: {columns}")
    frame = frame[CANONICAL_COLUMNS].copy()          # by name
    _assert_valid_datetime_labels(frame["datetime"])  # BEFORE astype(str)
    frame["datetime"] = frame["datetime"].astype(str)
    for c in _NUMERIC_COLUMNS:
        frame[c] = pd.to_numeric(frame[c], errors="coerce")
    _ = schema                                       # schema influences only accepted order
    validate_canonical_frame(frame)
    return frame


def validate_canonical_frame(frame: pd.DataFrame) -> None:
    """Validate a canonical frame; raise ValidationError on any violation."""
    if list(frame.columns) != CANONICAL_COLUMNS:
        raise ValidationError(f"column order/content invalid: {list(frame.columns)}")
    if len(frame) == 0:
        raise ValidationError("empty frame")
    dt = frame["datetime"]
    _assert_valid_datetime_labels(dt)
    if dt.duplicated().any():
        raise ValidationError("duplicate datetime")
    if not dt.is_monotonic_increasing:
        raise ValidationError("datetime not strictly lexicographically ascending")
    for c in _NUMERIC_COLUMNS:
        v = pd.to_numeric(frame[c], errors="coerce")
        if v.isna().any():
            raise ValidationError(f"non-numeric/null values in '{c}'")
        if not np.isfinite(v.to_numpy(dtype=float)).all():
            raise ValidationError(f"non-finite values in '{c}'")
    if not (frame["close"].to_numpy(dtype=float) > 0).all():
        raise ValidationError("non-positive close")


def _normalized_copy(frame: pd.DataFrame, name: str) -> pd.DataFrame:
    if set(frame.columns) != set(CANONICAL_COLUMNS):
        raise ValidationError(f"{name}: unexpected columns {list(frame.columns)}")
    out = frame[CANONICAL_COLUMNS].copy()
    _assert_valid_datetime_labels(out["datetime"])
    out["datetime"] = out["datetime"].astype(str)
    for c in _NUMERIC_COLUMNS:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    validate_canonical_frame(out)
    return out


def merge_existing_and_new(existing: pd.DataFrame, new_rows: pd.DataFrame) -> pd.DataFrame:
    """Merge two canonical frames by exact datetime; conflict-free, deduplicated.

    Identical overlapping datetimes are deduplicated; conflicting ones raise
    MergeConflictError. No gaps are inferred and no rows are added beyond the
    inputs.
    """
    old = _normalized_copy(existing, "existing")
    new = _normalized_copy(new_rows, "new_rows")
    combined = pd.concat([old, new], ignore_index=True)
    for ts, group in combined.groupby("datetime", sort=False):
        if len(group) > 1:
            first = group.iloc[0]
            for _, row in group.iloc[1:].iterrows():
                for c in CANONICAL_COLUMNS:
                    if row[c] != first[c]:
                        raise MergeConflictError(f"conflict at datetime {ts!r} column '{c}'")
    merged = (combined.drop_duplicates(subset=["datetime"])
              .sort_values("datetime", kind="mergesort")
              .reset_index(drop=True))
    validate_canonical_frame(merged)
    return merged


def write_candidate_atomic(candidate: pd.DataFrame, output_path: Path,
                           backup_path: Optional[Path] = None) -> dict:
    """Write a canonical candidate and atomically replace the output file.

    Writes a unique temporary file in the OUTPUT's parent directory, re-reads and
    validates it, records hashes, optionally preserves the original at
    backup_path (same directory), and only then uses os.replace(). On any failure
    the original output file is left unchanged and temporary artifacts removed.
    """
    output_path = Path(output_path)
    validate_canonical_frame(candidate)
    parent = output_path.parent
    if not parent.exists():
        raise WriteValidationError("output parent directory does not exist")

    backup_path = Path(backup_path) if backup_path is not None else None
    if backup_path is not None:
        if backup_path.parent.resolve() != parent.resolve():
            raise BackupError("backup_path must be in the same directory as output_path")
        if backup_path.exists():
            raise BackupError("backup_path already exists")

    original_sha = sha256_file(output_path) if output_path.exists() else None

    fd, tmp_name = tempfile.mkstemp(dir=str(parent), suffix=".tmp")
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        candidate.to_csv(tmp_path, index=False, columns=CANONICAL_COLUMNS)
        reread = read_and_normalize(tmp_path)
        validate_canonical_frame(reread)
        candidate_sha = sha256_file(tmp_path)
    except Exception as exc:                       # candidate invalid -> abort
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise WriteValidationError(f"candidate validation failed: {exc}") from exc

    backup_sha = None
    try:
        if backup_path is not None and output_path.exists():
            os.replace(output_path, backup_path)
            backup_sha = sha256_file(backup_path)
        os.replace(tmp_path, output_path)
    except Exception as exc:
        # best-effort restore so the original output is never lost
        if backup_path is not None and backup_path.exists() and not output_path.exists():
            try:
                os.replace(backup_path, output_path)
            except OSError:
                pass
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise WriteValidationError(f"atomic replace failed: {exc}") from exc

    return {"original_sha256": original_sha, "backup_sha256": backup_sha,
            "candidate_sha256": candidate_sha, "output_path": str(output_path)}
