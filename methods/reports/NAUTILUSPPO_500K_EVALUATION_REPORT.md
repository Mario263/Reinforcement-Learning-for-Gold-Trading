# NAUTILUSPPO 500K EVALUATION REPORT (Phase 6) — corrected (post MtM fix)

Command: `python -m methods.nautilus.scripts.backtest --model methods/nautilus/models/nautilusppo_modern_500k.zip --split modern --device cuda`
Deterministic, Nautilus-derived metrics (per-bar MtM corrected). Eval 2023-01-02→2024-09-12,
**9,896 periods**. File: `methods/nautilus/outputs/metrics/nautilusppo_modern_500k_eval.json`.

| metric | value |
|---|---|
| cumulative_return | **+6.97%** |
| CAGR | +4.20% |
| Sharpe | +0.45 |
| Sortino | +0.41 |
| Calmar | +0.34 |
| max_drawdown | −12.46% |
| volatility (ann.) | 10.33% |
| win_rate_all_periods | 27.15% |
| trade_win_rate (round trips) | 47.33% |
| **profit_factor** | **1.28** (>1 → profitable) |
| round_trips | 131 |
| total_turnover | 261 |
| final_equity | $10,696,559 (start $10,000,000) |
| position dist (short/flat/long) | 0.003 / 0.474 / 0.524 |
| NaN / inf | none / none |

## Consistency (all sane after the fix)
final_equity 10.70M = 10M × (1 + 0.0697) ✓. turnover 261 ≈ 2×131 round trips ✓. profit_factor 1.28
> 1, positive Sharpe, +7% — a long-biased policy profiting in the rising 2023-24 gold market.
win_rate_all 27% now matches RawPPO-scale (the buggy run's 0.7% is gone). **All finite, consistent.**

**Verdict: PASS** — valid Nautilus-derived evaluation with corrected per-bar accounting.
