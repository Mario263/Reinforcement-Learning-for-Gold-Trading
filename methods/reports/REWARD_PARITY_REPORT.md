# REWARD PARITY REPORT (Phase 6)

CSV: `methods/outputs/parity/reward_parity.csv`. Window 409 bars, same model.
Reward formula + coefficients are the SINGLE shared source (`methods.shared.rewards.raw_ppo_reward`):

  `reward = 1.0*gross_return - 2.0*drawdown - 0.5*cost_frac + 0.1*(-turnover)`

| coefficient | value | shared? |
|---|---|---|
| alpha (return) | 1.0 | ✓ |
| beta (drawdown) | 2.0 | ✓ |
| gamma (cost) | 0.5 | ✓ |
| delta (stability) | 0.1 | ✓ |

## Comparison (≥100 matching timestamps: all 409)
| metric | value |
|---|---|
| reward_max_abs_delta (RawPPO vs Nautilus) | **0.1003** |
| formula/coeffs identical | yes (single source) |
| inputs identical | **no — by design** |

## Why a per-bar delta exists (intentional, documented — not a bug)
RawPPO computes `gross_return` from instant close-fill (`target × price_ret`); NautilusPPO computes
it from the **Nautilus equity change** with a **next-bar fill** + integer-oz quantization. So the
*inputs* (gross_return, drawdown, the bar at which a position-change's `−0.1` stability hits)
differ by the execution lag, bounded at ≈0.10 (dominated by the 0.1 stability term landing one bar
apart on a flip). The reward *math* is identical. This is the documented Nautilus execution
deviation (EXECUTION_TIMING). **Verdict: PASS** (formula parity exact; input delta explained & bounded).
