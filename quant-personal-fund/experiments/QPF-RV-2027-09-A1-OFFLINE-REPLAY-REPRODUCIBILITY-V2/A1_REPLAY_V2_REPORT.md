# A1 Formal Offline Reproducibility Report (V2)

**Stage:** `A1_CONTROLLED_OFFLINE_REPLAY_REPRODUCIBILITY_CHECK_V2`
**Experiment:** `QPF-RV-2027-09-A1-OFFLINE-REPLAY-REPRODUCIBILITY-V2`
**Date:** 2026-09-30

## Result

```text
REPLAY_REPRODUCIBILITY_PASS
```

---

## 1. Purpose and strict offline boundary

Run the frozen A1 workflow twice on identical local XAUUSD fixtures with the approved fixture-only
runner and compare complete normalized event-record sequences. Boundary: `OFFLINE_REPLAY`,
`ORDERS_DISABLED`, `NO_BROKER_CONNECTION`, `NO_MT5_IMPORT_OR_INITIALIZATION`, `NO_NETWORK`,
`NO_EXTERNAL_DATA`, `NO_VIRTUAL_FILL`, `NO_PNL`. No PnL/performance computed.

## 2. Path-hash inventory

| Artifact | SHA256 |
|---|---|
| `quant-personal-fund/tools/a1_offline_runner/a1_offline_runner.py` | `36E80FC2C85B9BE52C762C215AD58397D9CB13F472033F690C2A876171979FA3` |
| `frival/gold_rules/engine.py` | `9653AE906D30583493A49A478CA123B6A190AC16B93B3FD4F9A2CCDD4B2357E8` |
| `frival/gold_rules/bias.py` | `106999937CFC810C88E58DCCF9476EC63FF998D2CDF08A4BFE43DCD259F8362F` |
| `frival/gold_rules/levels.py` | `63442EBBADAF059B816E49F9FDB28D71471CA4E7C5C98C8C3FE997674E0E49D5` |
| `frival/gold_rules/tests/fixtures/XAUUSD_M15.csv` | `574A38DC501821106FB5CA32E43F61CEACCEDBC31E281470B70B0D2665D28FBB` |
| `frival/gold_rules/tests/fixtures/XAUUSD_M30.csv` | `9345E3D33DE2391A2FDED8B2BC49FC5DD1F2E071C24B30D195D5D7910A55566F` |
| `frival/gold_rules/tests/fixtures/XAUUSD_H1.csv` | `81E51BBF9C720BBA96E5AB4A5B0C98EE483B14A84D0B8AE57C5526B2170B7521` |

Imported module paths are the pure A1 modules only (`engine.py`, `bias.py`, `levels.py` under
`frival/gold_rules/`) plus stdlib/pandas.

## 3. Isolation-guard result

`forbidden_import_scan()` over the runner and its direct pure-module imports → **no hits**
(no MT5/broker/execution/order/demo-ledger/network/subprocess/env).

## 4. Run statuses and record counts

- **Run 1:** completed normally; **807** event records; **0** errors.
- **Run 2:** completed normally; **807** event records; **0** errors.

## 5. Field checks

- Required-field completeness: **all required fields present or explicit `null`** in both runs.
- Prohibited-field absence: **no** `order_id`/`fill_price`/`fill_time`/`realized_pnl`/
  `unrealized_pnl`/`account_balance`/`position_size`/`broker_response` present.

## 6. Canonical comparison

- Record count equal: **true** (807 = 807).
- Key sets equal: **true**.
- Ordered normalized records equal: **true** (event-ID run prefix stripped per the runner interface).
- Canonical serialization SHA256 (run 1) = `DC11FF41788E946C9FCB37C66A04184CFC77288F603459CAEAB7E869A0DBBF81`.
- Canonical serialization SHA256 (run 2) = `DC11FF41788E946C9FCB37C66A04184CFC77288F603459CAEAB7E869A0DBBF81`.
- **Exact equality: PASS.**

## 7. Cleanup result

Both runs used fresh temporary directories outside the repository; both were removed after comparison
(cleanup confirmed).

## 8. Prohibition attestation

No MT5/broker/network/environment/credential access; no orders/virtual fills/PnL/performance/trading;
no repository file modified except the four permitted stage artifacts; fixtures read-only.

## 9. Final decision

```text
REPLAY_REPRODUCIBILITY_PASS
```

## 10. Next authorization consequence

A separate authorization may design and set up A1 **orders-disabled** forward observation only. No
broker connection, demo order, virtual fill, PnL analysis or trading is authorized.
