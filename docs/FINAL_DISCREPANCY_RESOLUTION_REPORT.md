# FINAL DISCREPANCY RESOLUTION REPORT

**Directive Phase 9.** Resolution of the env vs Nautilus blow-up (−$1.9M). No PPO retraining; no changes to features, reward, hyperparameters, or state space (Phase-8 constraints honored). Only the **Nautilus execution/sizing harness** was corrected.

## THE DEFECT (proven, not assumed)
Position sizing used **account cash** (`balance_total`), which is **inflated by short-sale proceeds** (lifecycle: cash $204,137 vs true equity $102,734 on a short). Combined with venue **leverage 50**, consecutive short decisions compounded the short position to a leveraged blow-up → negative net-liquidation equity (−$1.9M). Full proof: `POSITION_SIZING_ROOT_CAUSE.md`, `forensics/outputs/trade_lifecycle_audit.csv`.

## THE FIX (minimal, harness-only)
| File · method | Old | New |
|---|---|---|
| `nautilus/strategy.py` · `_net_liq` / `on_bar` / `on_order_filled` | size on `balance_total()` (cash) | size on **net-liquidation** (`cash + position·price`, self-tracked) |
| `nautilus/run_backtest.py` + diagnostics · venue | `default_leverage=50` | `default_leverage=2` |

## RESULT — env ↔ Nautilus convergence (current 63.78% model)
| Metric | Environment | Nautilus (fixed) | Delta |
|---|---|---|---|
| Cumulative return | +63.78% | **+63.15%** | −0.63 pp |
| Max drawdown | −4.04% | −4.00% | +0.04 pp |
| Round trips | 37 | 31 | −6 |
| Trade win rate | 78.38% | 77.42% | −0.96 pp |
| Profit factor | 6.17 | 6.89 | +0.72 |
| **Final equity** | ~$163,780 | **$163,125** | −0.4% |

All deltas small; the systems agree.

## BEFORE vs AFTER (Nautilus)
| Metric | Nautilus (buggy, lev 50 + cash sizing) | Nautilus (fixed) |
|---|---|---|
| Cumulative return | **−72.09%** | **+63.15%** |
| Max drawdown | −99.60% | −4.00% |
| Final equity | **−$1,936,255** | **+$163,125** |
| Max leverage | unbounded (compounding) | **1.00×** |
| Bars with equity < 0 | yes | **0** |

## ACCOUNTING CONSISTENCY (success criteria)
- Final equity mathematically consistent: $100,000 × (1 + 0.6315) ≈ $163,125 ✓
- Win rate (77.4%) + profit factor (6.89) now **agree** with a positive return ✓
- Drawdown realistic (−4.0%, matches env −4.04%) ✓
- Net-liquidation never negative; leverage bounded to 1.00× ✓
- Nautilus reconciles with the environment (Δ < 1 pp) ✓

## HOW TO REPRODUCE
```bash
python train.py --mode eval            # env  -> models/ppo_raw_metrics.json
python nautilus/run_backtest.py        # Nautilus -> nautilus/nautilus_metrics.json
python forensics/trade_lifecycle.py    # sizing/leverage/equity audit -> outputs/trade_lifecycle_audit.csv
python forensics/parity.py             # row-by-row env-vs-Nautilus diff CSVs
```

## CONCLUSION
The −$1.9M was a **position-sizing/accounting defect in the Nautilus harness** (sizing on short-inflated cash under leverage 50), **not** a PPO, feature, normalization, reward, or evaluation problem (all proven identical in prior phases). With sizing on net-liquidation equity and leverage capped at 2, Nautilus reproduces the environment's +63% and the blow-up is structurally impossible.
