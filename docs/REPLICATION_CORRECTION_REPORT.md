# REPLICATION CORRECTION REPORT (Phase 6)

Validation that, after the two harness fixes, the **environment** and **Nautilus** results converge. No retraining; no model/reward/feature/hyperparameter changes (Rules 1–3 honored). Only the Nautilus execution harness was corrected.

## CORRECTIONS APPLIED
| # | File · function | Old behavior | New behavior | Justification |
|---|---|---|---|---|
| 1 | `nautilus/run_backtest.py` · `build_data` | fill quote at `ts_ns+1` (after bar) → market order fills at stale `close[t-1]` | fill quote at `ts_ns-1` (before bar) → fills at `close[t]` | `forensics/fill_offset.py` proved offset {−1: 85}; env assumes `close[t]` fill |
| 2 | `nautilus/run_backtest.py` · `main` | equity = `balance_total()` (cash only) | equity = net-liquidation (`cash + pos·price`) from fills | `forensics/reconstruct.py`: cash-only excludes unrealized PnL (≈2 pp) |

## FINAL COMPARISON
| Metric | Env | Nautilus | Delta | Within 5%? |
|---|---|---|---|---|
| Cumulative return | +48.94% | +48.67% | −0.27 pp | ✅ |
| CAGR | +20.85% | +20.75% | −0.10 pp | ✅ |
| Sharpe | 2.04 | 2.06 | +0.02 | ✅ |
| Sortino | 2.32 | 2.37 | +0.05 | ✅ |
| Calmar | 6.74 | 6.87 | +0.13 | ✅ |
| Max drawdown | −3.10% | −3.02% | +0.08 pp | ✅ |
| Per-trade win rate | 74.29% | 73.53% | −0.76 pp | ✅ |
| Round trips | 35 | 34 | −1 | ✅ |
| Profit factor | 8.84 | 8.14 | −0.70 | ✅ |

**All deltas < 5%.** Convergence target met.

## BEFORE vs AFTER (Nautilus)
| Metric | Nautilus (buggy) | Nautilus (fixed) | Env |
|---|---|---|---|
| Return | −1.27% | +48.67% | +48.94% |
| Sharpe | −0.02 | 2.06 | 2.04 |
| Max DD | −10.31% | −3.02% | −3.10% |

## HOW TO REPRODUCE
```bash
python train.py --mode eval        # env metrics  -> models/ppo_raw_metrics.json
python nautilus/run_backtest.py    # Nautilus     -> nautilus/nautilus_metrics.json
python forensics/parity.py         # row-by-row diff CSVs
```

## SUPERSEDED REPORTS
The following earlier reports reflect the **pre-fix** Nautilus numbers (−1.27%) and their interpretation ("optimistic env vs honest execution") is **corrected** by `ROOT_CAUSE_REPORT.md`: `NAUTILUS_VS_ENV_REPORT.md`, `NAUTILUS_BACKTEST_REPORT.md`, `NAUTILUS_VALIDATION_REPORT.md`, `ENVIRONMENT_NAUTILUS_PARITY_REPORT.md`. Each now carries a correction banner pointing here.

## CONCLUSION
The −50 pp env↔Nautilus gap was **entirely a Nautilus execution-harness bug** (fill timing + equity measurement), not a model/observation/feature/normalization/reward defect. With the harness corrected, the trained PPO-Raw policy **reproduces +48.67% in independent event-driven Nautilus execution**, validating the replication. The convergence point uses standard fill-at-decision-close (MOC) execution shared by the env and the paper.
