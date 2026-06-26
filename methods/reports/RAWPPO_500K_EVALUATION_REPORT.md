# RAWPPO 500K EVALUATION REPORT (Phase 4)

Command: `python -m methods.rawPPo.scripts.evaluate --model methods/rawPPo/models/rawppo_modern_500k.zip --split modern --device cuda`
Deterministic. Eval 2023-01-02 → 2024-09-12, **9,896 hourly periods**. Metrics:
`methods/rawPPo/outputs/metrics/rawppo_modern_500k_eval.json`.

| metric | value |
|---|---|
| cumulative_return | **−14.96%** |
| CAGR | −9.43% |
| Sharpe | −0.81 |
| Sortino | −0.86 |
| Calmar | −0.47 |
| max_drawdown | −20.10% |
| volatility (ann.) | 11.48% |
| win_rate_all_periods | 30.38% |
| trade_win_rate (round trips) | 62.38% |
| profit_factor | 0.62 |
| round_trips | 101 |
| total_turnover | 201 |
| final_equity | 0.8504 |
| position dist (short/flat/long) | 0.610 / 0.382 / 0.008 |
| NaN / inf | none / none |

## Consistency
final_equity 0.850 = 1 + (−0.1496) ✓. turnover 201 ≈ 2×101 round trips ✓. profit_factor 0.62 < 1
⇒ losing, consistent with −15% and the fat-tail short pattern (62% of trades win but losses are
larger — shorting a rising 2023-24 gold market). Win-rate_all 30% < trade_win 62% because ~38% of
bars are flat (counted non-win). **Internally consistent; all finite.**

**Verdict: PASS** (valid, explainable evaluation; performance not a gate criterion).
