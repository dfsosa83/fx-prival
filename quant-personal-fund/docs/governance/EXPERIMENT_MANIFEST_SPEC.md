# Experiment Manifest Specification

Every experiment must be pre-registered with a manifest before any code is written against the test set. The manifest is a YAML file stored at `experiments/{experiment_id}/experiment.yaml`.

## Required Fields

### `experiment`
| Field | Type | Description |
|---|---|---|
| `id` | string | Unique experiment ID, e.g. `EXP-2026-01-TREND-BASELINE` |
| `status` | string | One of: `preregistered`, `in_progress`, `completed`, `closed` |
| `created` | date | Date of pre-registration (YYYY-MM-DD) |
| `researcher` | string | Name or identifier of the researcher |

### `hypothesis`
| Field | Type | Description |
|---|---|---|
| `economic_mechanism` | string | The economic rationale for why the signal should work |
| `falsifiable_claim` | string | A specific, testable claim that can be proven false |
| `why_existing_results_do_not_already_reject_it` | string | Citation of the falsification ledger entries that are NOT contradicted by this experiment |

### `universe`
| Field | Type | Description |
|---|---|---|
| `instruments` | list[string] | List of instrument tickers |
| `data_source` | string | Source of market data |
| `frequency` | string | Data frequency: `daily`, `weekly`, `monthly` |
| `date_range` | object | `start` and `end` dates for the full dataset |

### `signal`
| Field | Type | Description |
|---|---|---|
| `definition` | string | Mathematical or algorithmic definition of the signal |
| `directionality` | string | `long_only`, `short_only`, or `long_short` |
| `holding_horizon` | string | Expected holding period |
| `rebalance_frequency` | string | How often positions are re-evaluated |
| `parameters` | object | Frozen parameter values (key-value pairs) |

### `cost_model`
| Field | Type | Description |
|---|---|---|
| `spread_source` | string | Source and date of spread measurements |
| `slippage_assumption` | string | Assumed slippage in basis points or pips |
| `commission` | string | Commission structure |
| `financing` | string | Swap/financing rate assumptions |
| `session_conditioning` | string | Whether costs vary by session |

### `portfolio`
| Field | Type | Description |
|---|---|---|
| `construction_method` | string | e.g. `inverse_volatility`, `risk_parity`, `equal_weight` |
| `risk_budget` | object | Risk budget allocation across sleeves or instruments |
| `vol_target` | number | Annualized volatility target (e.g. 0.10 for 10%) |
| `constraints` | object | Position limits, concentration limits, leverage caps |

### `validation`
| Field | Type | Description |
|---|---|---|
| `train_window` | string | Training period date range |
| `validation_window` | string | Validation period date range (if applicable) |
| `sealed_test_window` | string | Sealed test period — scored exactly once |
| `embargo_rule` | string | Purge/embargo period between train and test |
| `bootstrap_method` | string | `moving_block` |
| `bootstrap_resamples` | integer | Number of bootstrap resamples (e.g. 1000) |

### `metrics`
| Field | Type | Description |
|---|---|---|
| `primary_metric` | string | e.g. `net_ev_per_r`, `sharpe_ratio` |
| `secondary_metrics` | list[string] | Additional metrics to report |
| `minimum_sample_size` | integer | Minimum number of trades/periods required for valid inference |

### `decision_gate`
| Field | Type | Description |
|---|---|---|
| `go` | string | Conditions for GO (e.g. `ev_per_r > 0 AND ci_lo > -0.05 AND n >= 30`) |
| `hold` | string | Conditions for HOLD |
| `stop` | string | Conditions for STOP |

### `robustness`
| Field | Type | Description |
|---|---|---|
| `checks` | list[string] | Mandatory checks: `remove_top_trades`, `year_by_year`, `quarter_by_quarter`, `regime_split`, `cost_stress`, `parameter_stability`, `concentration_analysis`, `unconditional_baseline` |

### `inputs`
| Field | Type | Description |
|---|---|---|
| `data_manifests` | list[string] | References to `data/raw/manifests/*.yaml` files |
| `config_snapshot` | string | Git commit hash at time of pre-registration |
| `inputs_hash` | string | SHA256 of frozen parameters + data manifest references (computed at pre-registration) |

### `non_goals`
| Field | Type | Description |
|---|---|---|
| `non_goals` | list[string] | What this experiment explicitly does NOT test |

## Validation Rules

1. `inputs_hash` must be computed before any code touches the sealed test set.
2. The experiment runner must verify `inputs_hash` matches the frozen parameters before scoring.
3. Mismatch → abort with error; do not score.
4. The sealed test window must not overlap with any training or validation window.
5. All dates must be chronological: train < validation < test (where applicable).
6. `bootstrap_resamples` must be ≥ 1000 for primary inference.
7. `minimum_sample_size` must be ≥ 30 for any GO decision.

## Lifecycle

```
preregistered → in_progress → completed → closed
```

- `preregistered`: Manifest filed. No code written against test set.
- `in_progress`: Implementation underway. Test set still sealed.
- `completed`: One-shot scoring complete. Robustness checks applied. Verdict recorded.
- `closed`: Final state. May be GO, HOLD, or STOP. Manifest and reports are immutable.