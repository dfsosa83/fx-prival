# MT5 `initialize` Failure Diagnosis — `(-2, 'Invalid "login" argument')`

**Date:** 2026-09-28 (offline-only diagnostic task).
**Constraints honored:** no MT5 runtime function was called (no `initialize`,
`login`, `shutdown`, `account_info`, `terminal_info`, `symbol_info`, or any
other MetaTrader5 API function); no order/position/deal access; no terminal or
process started/stopped/config; no probe retry; no credential printed, copied,
saved, or exposed; `frival/execution_bot/config/credentials.env` read **in
memory** for structural validation only.
**Engineers note:** this documents the configuration-level diagnosis; the root
cause hypotheses below are labeled hypotheses, not conclusions.

## 1. Environment-variable names read by the connection code

| Purpose | Variables read (in priority order) |
|---|---|
| MT5 terminal path | `MT5_PATH` (explicit; used in both attempts), `MT5_TERMINAL_PATH` (present in the file but **empty**) |
| Login | `MT5_LOGIN` |
| Password | `MT5_PASSWORD` |
| Server | `MT5_SERVER` |

## 2. Login value — structural status (booleans / types / lengths only)

| Property | Status |
|---|---|
| Variable exists | **True** |
| Non-empty (raw) | **True** |
| Non-empty (normalized) | **True** |
| Raw type category | **`str`** |
| Leading whitespace present | False |
| Trailing whitespace present | False |
| Surrounding quotes present | False |
| Consists only of ASCII digits | **True** |
| Character count | **7** (count only) |
| Convertible to `int` | True |
| Resulting integer positive | **True** |
| **Was it converted to `int` before `mt5.initialize(...)` in the two attempts?** | **NO.** Both attempts passed `login` as the raw `str`. |

No digit sequence, prefix, suffix, or hash is printed anywhere in this report.

## 3. Password and server

Password: variable **exists, non-empty**, no leading/trailing whitespace, no
surrounding quotes (booleans). Never printed.
Server: variable **exists, non-empty**, no whitespace/quotes (booleans). The
value corresponds to the previously documented demo server name
(`FPMarketsSC-Demo`) already treated as project (non-secret) configuration in
earlier reports; it is not reprinted here.

## 4. Terminal path

| Property | Status |
|---|---|
| Explicitly configured (`MT5_PATH`) | True, non-empty |
| File exists on disk | **True** |
| Filename is `terminal64.exe` | **True** |
| Passed as string (normalized) | True (raw `str` from env, OS-path validated) |
| `MT5_TERMINAL_PATH` | key exists but **empty** |

The terminal was never launched/modified; only `Path`-level checks were made.

## 5. The `mt5.initialize(...)` invocation

- Argument names and Python types in the two failed attempts:
  `path=<str>`, `login=<str>` (❌ should be `int`), `password=<str>`, `server=<str>`.
  No malformed keyword, duplicate argument, `None`, or misparsed value.
- **Corrected code (`tools/mt5_metadata_validate.py` + `tools/mt5_config.py`,
  offline, not executed):** `login=<int>` (validated positive integer),
  `password=<str>`, `server=<str>`, `path=<str>`; invalid configuration now
  fails **before** any `initialize` call with `STOPPED_INVALID_CONFIG`.
- Signature comparison (offline artifact, installed SDK `MetaTrader5 5.0.4874`,
  wrapper is a compiled C builtin — `from ._core import *`):
  `initialize([path],[server="SERVER"],[login=LOGIN],[password="PASSWORD"])`,
  and error table `RES_E_INVALID_PARAMS = -2  # invalid arguments/parameters`.
  Note the documentation convention: `[login=LOGIN]` (unquoted → numeric
  account) vs `[server="SERVER"]`/`[password="PASSWORD"]` (quoted strings).
- Project-wide pattern (read-only grep): production code calls
  `mt5.initialize(path=...)` **path-only everywhere** (`core/mt5_connector.py`,
  `gold_rules/run_gold_rules.py`, `data/fetcher.py`,
  `dashboard/backend/portfolio.py`) — i.e., it attaches to an already-running,
  already-logged-in terminal; login/password are never passed in the live
  pattern.

## 6. Package / interpreter consistency

| Item | Value (no credentials) |
|---|---|
| Installed SDK | `MetaTrader5 5.0.4874` |
| SDK location | `C:\Users\david\anaconda3\lib\site-packages\MetaTrader5` (wheel tag `cp39-win_amd64`, i.e., `_core.cp39-win_amd64.pyd`) |
| Python used by the probe | Anaconda Python 3.9.21 (Windows 64-bit) |
| Consistency | **Consistent** — the cp39 wheel matches the 3.9 interpreter. |

## 7. Ranked plausible remaining causes (HYPOTHESES, not conclusions)

1. **H1 (most probable)** — `login` was passed as a **string** in both attempts;
   the SDK C-core documents/validates `login` as the numeric account argument
   and returns `RES_E_INVALID_PARAMS (-2)` → `'Invalid "login" argument'` for a
   type/format mismatch. This is the only argument whose documented form is a
   bare numeric literal, and the failure is systematic (identical across two
   different credential files).
2. **H2 (plausible)** — With `path+login+password+server` passed together, the
   launch/attach semantics may additionally require an already-logged-in
   terminal or a specific config-binding; project code never passes credentials
   to `initialize` (path-only attach), so this launch pattern is unproven in
   this codebase.
3. **H3 (lower)** — The numeric account is valid but the demo server/account
   pairing in the environment differs from what the SDK resolves; auth-type
   problems normally surface as auth errors (e.g., `-6`), so this is less
   consistent with `-2`.
4. **H4 (low)** — Minor SDK-build mismatch (`5.0.4874` vs repo pin `>=5.0.45`)
   in the `initialize` argument schema.
5. **H5 (low)** — Terminal profile/saved-config conflict affecting the launch
   path with supplied credentials.

## 8. Is a further single read-only initialization attempt justified?

**Conditionally yes.** The code-level defect (login passed as `str` vs `int`)
is now corrected, offline-validated by 15 new unit tests, and fail-closed: no
`initialize` call will be attempted with invalid configuration. A further
**single read-only attempt is justified only under a new, separate explicit
authorization**, after the operator also verifies H2/H3 conditions (terminal
logged-in state, account/server pairing, and that the project's operational
pattern of attaching to an already-running logged-in terminal is acceptable for
the validation instead of passing credentials).

## 10. Resolution (authorized offline fix + verified path-only attach)

**Applied (2026-09-28, authorized):** the probe was corrected to the project's
production pattern — `mt5.initialize(path=...)` **only**; login/password/server
are never passed to the SDK. `tools/mt5_config.build_initialize_args` now
returns `{"path": str}` exclusively; the credential validators remain as
optional environment-structure utilities. Tests updated and extended
(path-only builder contract, credentials ignored by the builder, validator
rejection set, secret-free errors): **Ran 81 tests … OK**.

**Verified end-to-end (operator-run pre-checks + single attempt):**
- Pre-check 1 PASS: `terminal64.exe` exists and is running (OS-level).
- Pre-check 2 PASS: window-title (masked) shows the terminal connected to
  `FPMarketsSC-Demo` with exactly the configured account (single numeric run).
- Single path-only attempt: `mt5.initialize(path=<configured>)` → **success**;
  library shutdown → **success**. No retries, no credentials passed, no
  secrets recorded.

**Conclusion:** the recurring `(-2,'Invalid "login" argument')` is explained by
passing the login (as a string) to `initialize` — a launch-with-credentials
pattern the SDK rejects at argument level (`RES_E_INVALID_PARAMS`). Attaching
path-only to the already-logged-in demo terminal (the project's operational
pattern) works. H1 is confirmed in practice; H2/H3-H5 are no longer relevant to
the connection path.

## 9. Confirmation statements

- **No MT5 runtime function was called** during this diagnostic task; only
  module-level imports, docstring/attribute introspection, source reads, and
  in-memory structural checks of the credentials file.
- **No credential was exposed.** Reports use booleans, type names, and lengths;
  the credential-membership audit over all artifacts remained clean.
- No order/position/workflow activation or strategy change occurred.
- Files changed/added under `frival/execution_bot/` only:
  `tools/mt5_config.py` (new), `tools/mt5_metadata_validate.py` (config
  fail-fast + login-as-int), `tests/test_exec_delta1.py` (+15 config tests),
  `reports/mt5_initialize_login_diagnosis.md` (this report). Test evidence:
  **Ran 81 tests … OK** (was 66; +15 new).