# Safety and Promotion Gates

**Stage:** `A1_A3_A8_REPLAY_AND_FORWARD_DEMO_EVALUATION_DESIGN`

Promotion path (each stage requires **separate explicit authorization** to begin):

| Stage | Purpose | Evidence required to advance | Explicit non-authorization | Fail/pause condition | Artifact location |
|---|---|---|---|---|---|
| STAGE 0 | Static inventory complete | inventory documents (done) | doing anything with orders/market | inventory incomplete | `QPF-RV-2027-06-…INVENTORY/` |
| STAGE 1 | Controlled offline replay reproducibility | two identical runs → equal event records | PnL/optimization/performance | `REPLAY_REPRODUCIBILITY_PAUSE` | this experiment folder |
| STAGE 2 | Forward observation, orders disabled | complete per-cycle records over window | fills, orders, PnL, broker use | `FORWARD_OBSERVATION_PAUSE` | this experiment folder |
| STAGE 3 | Observation-quality review | all cycles complete; consistent states; provenance | demo orders | review finds defects | this experiment folder |
| STAGE 4 | Optional separately authorized demo-order **design** | clear measurement + isolation plan | placing any demo order | plan rejected | separate experiment folder |
| STAGE 5 | Optional separately authorized demo-order **pilot** | explicit authorization; bounded pilot | live trading | pilot defect/abort rule | separate experiment folder |
| STAGE 6 | Independent cost-aware and risk review | cost/risk evidence (separate track) | live trading | review fails | separate experiment folder |
| STAGE 7 | Any live-trading consideration | separate decision | — | — | separate governance decision |

## Statements

- **Advancing a stage does not prove profitability.**
- **No stage automatically authorizes the next.**
- **No demo order before Stage 4/5 explicit authorization.**
- **No live-trading consideration before Stage 7.**
- **All event data must remain segregated:** XAUUSD primary records separate from any FX replay records.
- This design stage (the one that produced this file) authorizes **none** of Stages 1–7 to run.
