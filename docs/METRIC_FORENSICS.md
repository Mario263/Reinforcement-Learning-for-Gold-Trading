# METRIC FORENSICS (Agent 6)

Verification of every reported metric formula and value. Source: `metrics.evaluate_model`. Values independently recomputed in `forensics/forensic_dump.json`. Window: 621-day, 530 transitions.

## FORMULAS (code-traced)
| Metric | Formula (`metrics.py`) | Units | Value |
|---|---|---|---|
| Cumulative return | `equity[-1]/equity[0] − 1` | frac | +0.4894 |
| CAGR | `(equity[-1]/equity[0])**(252/n) − 1` | frac | +0.2085 |
| Sharpe | `mean(net)/std(net)·√252` | ratio | 2.04 |
| Sortino | `mean(net)/std(net[net<0])·√252` | ratio | 2.32 |
| Calmar | `cagr/|maxDD|` | ratio | 6.74 |
| Recovery factor | `cum_return/|maxDD|` | ratio | 15.81 |
| Max drawdown | `min(equity/cummax(equity) − 1)` | frac | −0.0310 |
| VaR(95%) | `percentile(net, 5)` | frac | −0.0026 |
| Win rate | `mean(net > 0)` over all periods | frac | 0.1075 |
| Active win rate | `mean(net>0 | pos≠0)` | frac | 0.5938 |
| Turnover | `Σ|Δposition|` | units | 69 |
| Exposure | `mean(pos≠0)` | frac | 0.1811 |

## INDEPENDENT RECOMPUTE (forensic_dump.json) — all reconcile
- cumulative_return 0.4894 ✅ ; win_rate 57/530=0.1075 ✅ ; active_win 57/96=0.5938 ✅ ; turnover 69 ✅.
- Trade-level (forensic): round trips 35, trade win rate 26/35=0.7429, profit factor 8.84.

## TRADE / TURNOVER / EXPOSURE COUNTING (verified `TRADE_FORENSIC_REPORT.md`)
- Position-change events 68; turnover units 69 (one flip = 2 units); entries 34 (29 long/5 short); exits 33; flips 1; round trips 35. ✅ internally reconciled.

## WIN-RATE CRITICAL INVESTIGATION (resolved, `WIN_RATE_FORENSIC_REPORT.md`)
| Number | Formula | Numerator | Denominator | Source |
|---|---|---|---|---|
| 10.75% | `mean(net>0)` | 57 | 530 (all periods) | `metrics.py win_rate` |
| 59.38% | `mean(net>0 | pos≠0)` | 57 | 96 (in-market) | `metrics.py active_win_rate` |
Same 57 wins (all profits occur in-market; flat = 0 return). 10.75% is misleading for an 82%-flat policy; the meaningful analogs are active (59.38%) or per-trade (74.29%).

## ANNUALIZATION (documented assumption)
Sharpe/Sortino/CAGR use **252** periods/year (daily convention). The paper states no annualization factor — this is the single metric-side assumption. It does **not** affect cumulative return / drawdown / win rate.

## VERDICT
Every metric formula is standard and every reported value independently reconciles to the recorded per-step arrays. The win-rate "discrepancy" is two correctly-computed numbers over different denominators. **No metric-calculation defect.**
