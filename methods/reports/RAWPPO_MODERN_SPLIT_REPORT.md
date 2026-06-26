# RAWPPO MODERN SPLIT REPORT (Phase 8) — fix experiment

Goal: test whether the short bias is inevitable, and whether raising `ent_coef` (0.01→0.03)
helps. Train 2017-2022 / eval 2023-2024, 150k steps. Models/curves under `methods/rawPPo/`.

## Results
| run | train | eval | ent_coef | steps | short / flat / long | cum.ret | sharpe | max_dd | trade_wr | round_trips |
|---|---|---|---|---|---|---|---|---|---|---|
| **baseline (existing)** | 2003-2019 | 2020-2026 | 0.01 | 500k | **0.62 / 0.01 / 0.37** | −42.2% | −0.40 | −54.0% | 77% | 554 |
| **fix (ent 0.03)** | 2017-2022 | 2023-2024 | 0.03 | 150k | **0.33 / 0.08 / 0.60** | −5.1% | −0.17 | −21.6% | 26% | 214 |
| control (ent 0.01) | 2017-2022 | 2023-2024 | 0.01 | 150k | **PENDING** | — | — | — | — | — |

## What is established
- **The short bias is NOT structural.** A different config produces a **long-biased** policy
  (60% long). So the 0.62-short result is a *training-dynamics* outcome, not an inevitable
  property of the env/reward. (Answers Q7/Q10 directionally.)
- **Losses dropped ~8×** (−42% → −5%) and max DD more than halved — though on a *different,
  shorter* eval window, so this is **not** a clean return comparison.
- **Entropy stayed healthy** with ent_coef 0.03: curve `entropy_loss` −1.09 → −0.37 (gradual, no
  early collapse). `approx_kl` 2e-3…9e-3 throughout, →9e-8 only at the final lr≈0 iteration.

## Honest confounds (cannot attribute to entropy alone yet)
The fix run changed **four** things vs baseline: train window (2017-2022 vs 2003-2019), eval
window (2023-24 vs 2020-26), ent_coef (0.03 vs 0.01), and steps (150k vs 500k). The **control**
(modern split, ent_coef 0.01, same steps/eval) isolates the entropy effect:
- if control is also long-biased → the flip came from the **modern data**, not entropy;
- if control reverts to short-biased → **ent_coef is the lever**.
Result appended on completion.

## Recommendation (pending control)
Do **not** yet change canonical `TrainConfig.ent_coef`. Decide after the control isolates cause.
Either way, the canonical reward/PnL/cost/action logic stays unchanged (verified correct).
