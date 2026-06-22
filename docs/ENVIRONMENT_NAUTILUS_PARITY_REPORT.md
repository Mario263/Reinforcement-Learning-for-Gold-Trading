# ENVIRONMENT vs NAUTILUS PARITY REPORT

> ⚠️ **SUPERSEDED (Phase 6).** The "fill timing is inherent execution friction" conclusion was wrong — it was a **fixable harness off-by-one bug** (fills at stale `close[t-1]`). After the fix the metrics converge (env +48.94% vs Nautilus +48.67%). See `ROOT_CAUSE_REPORT.md` / `EXECUTION_PARITY_REPORT.md`. The observation/action parity (diff 0) below remains valid.

Same frozen policy, same 621-day window, same observations (parity proven, diff 0). Every metric: Environment, Nautilus, Difference, Explanation. Differences > 5% are investigated.

| Metric | Environment | Nautilus | Difference | Explanation |
|---|---|---|---|---|
| Return | +48.94% | −1.27% | −50.2 pp | **>5% — execution.** Env fills at `close[t]` (same-bar, optimistic); Nautilus fills ≈ `close[t+1]` (1-bar lag). Attribution: env +48.95% → 1-bar-lag −8.76% → Nautilus −1.27%. |
| CAGR | +20.85% | −0.60% | −21.5 pp | same cause |
| Sharpe | 2.04 | −0.02 | −2.06 | same cause |
| Sortino | 2.32 | −0.01 | −2.33 | same cause |
| Calmar | 6.74 | −0.06 | −6.80 | same cause |
| Recovery | 15.81 | −0.12 | −15.9 | same cause |
| Max drawdown | −3.10% | −10.31% | −7.2 pp | **>5% — execution.** Lagged entries enlarge adverse excursions. |
| Trade win rate | 74.29% | 41.18% | −33 pp | **>5% — execution.** Lagged fills convert many "wins" to losses. |
| Profit factor | 8.84 | 0.93 | −7.9 | same cause |
| Round trips | 35 | 34 | −1 | within noise (boundary trade open at series end) |
| Turnover | 69 units | 85 fills | ~ aligned | counting basis differs (Σ|Δpos| vs fills); integer-oz granularity |
| Exposure | 18.1% | ~18% | ~0 | identical position schedule |
| Action distribution | 6/434/91 | 6/434/91 | **0** | identical (observation parity) |
| Holding duration (avg) | 2.74 d | 2.74 d | 0 | identical |

## INVESTIGATION OF >5% DIFFERENCES
All material differences trace to **one root cause: fill timing** (`ROOT_CAUSE_ANALYSIS.md` rank 1). Proven by an offline 1-bar-lag attribution that turns +48.95% into −8.76% from the *same action sequence*. Nautilus (−1.27%) sits between env and the pure-lag model because its `ts+1` quote lets some orders fill same-bar (a blend) and sizing is integer-oz. No difference is attributable to observation, reward, feature, normalization, or accounting discrepancies (all parity-verified at diff 0).

## CONCLUSION
The two engines agree **exactly on behavior** (observations, actions, trades, exposure, holding) and diverge **only on realized P&L**, entirely due to the env's optimistic same-bar fill vs Nautilus's honest next-price fill. This is the decisive robustness result: the env's headline performance is an evaluation-convention artifact, not a tradable edge.
