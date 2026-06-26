# FULL 500K RAWPPO vs NAUTILUSPPO COMPARISON (Phase 7)

Both: modern split, 500k, GPU, eval 2023-01-02→2024-09-12 (9,896 periods). **Separately trained**
(not the same model) — so policy differences are expected.

| Metric | RawPPO 500k | NautilusPPO 500k | Delta | Explanation |
|---|---|---|---|---|
| position short/flat/long | 0.61 / 0.38 / 0.008 | 0.003 / 0.47 / 0.52 | **opposite** | the two envs' execution led PPO to different optima — RawPPO short, Nautilus long |
| cumulative_return | −14.96% | +6.97% | +21.9 pp | different policies (short loses, long wins in the uptrend) |
| CAGR | −9.43% | +4.20% | | policy |
| Sharpe | −0.81 | +0.45 | | policy |
| Sortino | −0.86 | +0.41 | | policy |
| Calmar | −0.47 | +0.34 | | policy |
| max_drawdown | −20.10% | −12.46% | | policy |
| volatility | 11.48% | 10.33% | small | similar exposure |
| win_rate_all | 30.38% | 27.15% | −3.2 pp | **similar** (envs agree on accounting) |
| trade_win_rate | 62.38% | 47.33% | | policy |
| profit_factor | 0.62 | 1.28 | | policy (Nautilus profitable) |
| round_trips | 101 | 131 | | policy |
| total_turnover | 201 | 261 | | policy |
| final_equity | 0.850 (norm) | $10.70M (+7%) | | both consistent with their cum return |

## Expected differences (not bugs)
- **Separately trained policies** — RawPPO converged short-biased, NautilusPPO long-biased. This is
  the dominant cause of the metric gaps.
- Nautilus execution: next-bar fill, integer-oz, real fills/accounting (per-bar MtM corrected).

## Potential bugs — checked, NONE
No NaN/inf; no all-flat/all-one-direction collapse (both span states); no position accumulation; no
unintended leverage (≤0.95); fees consistent with trade counts (turnover ≈ 2× round trips both);
Nautilus genuinely used for fills/accounting; 528 (z-score) and 6048 (annualization) not confused.

## Key point
The frameworks produced **opposite policies** from the same reward/features — a *training-dynamics*
outcome, not an accounting discrepancy. The same-policy diagnostic (next report) proves the **envs
agree** on accounting when given identical actions (win rate 28.4% vs 28.4%).
