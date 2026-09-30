# raw_data_schema_rebuild — safe H1 CSV rebuild utility

Isolated, offline, **path-explicit** utility that rebuilds a legacy or canonical raw H1 CSV into the
frozen canonical schema:

```text
datetime,open,high,low,close,volume
```

It contains **no** production paths, symbol names, MT5/downloader/broker/network/credentials
references, and **no** automatic execution entry point. Any production use requires a separate
explicit authorization.

## The schema problem

The repository MT5 downloader writes rows in canonical order `datetime,open,high,low,close,volume`
and **appends** them with no header for an existing file. Several older raw H1 files instead store the
timestamp **last**:

```text
open,high,low,close,volume,datetime   # legacy
```

Appending canonical (datetime-first) rows into a legacy (datetime-last) file **shifts every column
silently** — a datetime string lands in the `open` column, etc. There is no exception, so the
corruption is invisible. The downloader has no schema detection, no full rebuild, no normalization, no
deduplication, and no atomic replacement.

## Accepted input schemas

Only these two headers are accepted (detected by header only):

```text
datetime,open,high,low,close,volume   # canonical
open,high,low,close,volume,datetime   # legacy
```

Every other schema (different set/order, unnamed/index columns, etc.) is rejected fail-closed.

## Why append is unsafe, and what this utility does instead

Instead of appending, the utility performs a **full rebuild**: it normalizes the entire dataset into
canonical order **by column name** (never by position), writes a **uniquely named temporary file in
the output file's parent directory**, **re-reads and validates** that candidate, records hashes, and
only then performs an **atomic `os.replace()`** onto the target. If anything fails, the original
output file is left unchanged and temporary artifacts are removed. An optional `backup_path` (same
directory, must not already exist) preserves the original before replacement.

`datetime` labels are treated as **opaque strings** (`NOT_UTC`) — never parsed, localized, or inferred.
No gaps are inferred, nothing is interpolated/resampled, and no rows are added beyond the inputs.

## Public API

```python
detect_schema(csv_path) -> "canonical" | "legacy"     # header-only; else SchemaError
read_and_normalize(csv_path) -> pandas.DataFrame      # canonical order, validated
validate_canonical_frame(frame) -> None               # raises ValidationError on any violation
merge_existing_and_new(existing, new_rows) -> DataFrame  # datetime merge; conflict-free; deduped
write_candidate_atomic(candidate, output_path, backup_path=None) -> dict  # hashes + atomic replace
sha256_file(path) -> str                              # uppercase SHA256
```

Validation rules (fail-closed): all six columns exactly once; no null/duplicate `datetime`; strictly
lexicographically ascending labels; numeric finite `open/high/low/close/volume`; `close > 0`; no
index/unnamed column. Merge requires identical overlapping rows (else `MergeConflictError`).

## Safety guarantees and limitations

- **Guarantees:** schema detection before parsing; name-based normalization; full rebuild (no append);
  temp-in-same-directory; candidate re-read/validate before replace; atomic replace; original
  preserved on any failure; optional backup refused if it already exists.
- **Limitations:** the utility has **not** been used against any real raw file and has **not**
  retrieved historical data; it does **not** download data and does **not** access MT5; it does not
  itself fetch or refresh anything. Tests are **synthetic only**.

## Tests

`test_safe_h1_csv_rebuild.py` uses only temporary directories and tiny synthetic CSVs (no MT5, no
network, no production paths, not even read-only). Run:

```text
python -m unittest -v test_safe_h1_csv_rebuild.py
```

## Authorization

Any production use — including a USDJPY historical refresh — requires **separate explicit
authorization**.
