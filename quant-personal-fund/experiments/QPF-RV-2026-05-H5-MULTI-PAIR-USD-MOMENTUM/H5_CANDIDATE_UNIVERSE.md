# H5 — Candidate Universe

**Stage:** `H5_MULTI_PAIR_USD_MOMENTUM_VOLATILITY_DESIGN`

---

## USD confirmation basket (five pairs)

```text
EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD
```

USD-oriented **sign convention** so that positive always means **USD strengthening**:

\[
m_{EURUSD,t}^{(L)}=-r_{EURUSD,t}^{(L)},\quad
m_{GBPUSD,t}^{(L)}=-r_{GBPUSD,t}^{(L)},\quad
m_{USDJPY,t}^{(L)}=+r_{USDJPY,t}^{(L)},\quad
m_{USDCHF,t}^{(L)}=+r_{USDCHF,t}^{(L)},\quad
m_{USDCAD,t}^{(L)}=+r_{USDCAD,t}^{(L)}.
\]

USD-strength confirmation count:

\[
C_t^{(L)}=\sum_{j=1}^{5}\mathbf{1}\{m_{j,t}^{(L)}>0\},\qquad
C_{t,\mathrm{weak}}^{(L)}=\sum_{j=1}^{5}\mathbf{1}\{m_{j,t}^{(L)}<0\}.
\]

Later H5 evaluation uses only the **strict timestamp intersection** across all instruments required
by a tested specification. Labels are internal ordinal labels only, **`NOT_UTC`**; no UTC, session,
calendar, broker-time, or market-close meaning is inferred.

## Target-pair panel (H5-v1, seven targets)

```text
EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD
```

Every target must be evaluated **separately**; do **not** pool target outcomes into one unlabelled
aggregate.

## Dependency control

- A target may also be a basket member.
- Each target is reported two pre-declared ways:
  1. **Target-included** confirmation basket.
  2. **Target-excluded** confirmation basket.
- The **target-excluded** basket is the **primary** evidence for selection and multiplicity control
  (it prevents the target's own past movement from mechanically dominating the confirmation signal).
- **Target-included output is a secondary diagnostic only** and can **never** select a candidate.
- No pair may be added, substituted, removed, reoriented, or reweighted after market results are seen.
- **USDJPY is a required H5-v1 basket member and target.** If USDJPY or any required basket member is
  unavailable, invalid, or lacks sufficient strict common H1 history for the multiseries snapshot, the
  H5-v1 freeze must **stop with a data-integrity PAUSE** — it may not be silently omitted,
  substituted, or reweighted.

## Cross and gold restriction

- **EURGBP is excluded** (does not directly contain USD).
- **XAUUSD is excluded** (different market structure, volatility profile, and cost model; requires a
  separate experiment family).
- **AUDUSD and NZDUSD are targets, but not confirmation-basket members** in H5-v1.
