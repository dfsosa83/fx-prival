# H5-v2 — Snapshot Freeze Decision

**Experiment:** `QPF-RV-2026-07-H5-V2-MULTI-PAIR-USD-MOMENTUM`
**Date:** 2026-09-29

```text
decision: PAUSE_DIRECTIONAL_STATISTICAL_VIABILITY
```

---

## Exact source issue

The repository MT5 downloader
(`ml-signal-service/steps/01_download/mt5_downloader.py`) writes rows ordered
`datetime,open,high,low,close,volume` and appends **without a header** to an existing file, whereas the
existing mandatory raw file `ml-signal-service/data/raw/mt5/H1/USDJPY_H1.csv` is ordered
`open,high,low,close,volume,datetime`. Invoking the downloader would **misalign columns and corrupt
USDJPY**, so it was **not invoked**.

- `blocker`: `downloader_schema_incompatible_with_existing_usdjpy_append_would_misalign`
- `usdjpy before`: 47,152 rows, `2019-01-02 00:00:00` → `2026-07-30 14:00:00`,
  SHA256 `BF92FF4077425E9DC903A1D9D3DC5F847A8F3FED49958AA4B44CFC1C640A4CBC`
- `usdjpy after`: unchanged (no update)
- completeness threshold `2026-09-24 18:00:00`: **NOT MET**

## Consequence

- **No H5-v2 snapshot was created.** H5-v1 remains frozen but unused for screening.
- **No workaround or modified universe is authorized.** No substitution, download, or H5 statistical
  screen is authorized under this stage.

## Next step

A subsequent authorized stage would need to (a) reconcile the downloader's append schema with the
existing raw-file schema (or otherwise obtain a schema-consistent USDJPY history update), then (b)
create the v2 snapshot. Only after a successful, hash-verified v2 freeze could **one separately
authorized H5-v2 statistical screen** proceed under the unchanged H5 protocol.
