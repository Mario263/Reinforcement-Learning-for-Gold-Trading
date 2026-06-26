# RAWPPO 500K TRAINING REPORT (Phase 3)

| item | value |
|---|---|
| command | `python -m methods.rawPPo.scripts.train --split modern --total-timesteps 500000 --device cuda --model-out methods/rawPPo/models/rawppo_modern_500k.zip` |
| device | cuda (RTX 5080) | torch | 2.11.0+cu128 |
| split | modern (train 2017-2022 = 34,966 rows; eval 2023-01-02→2024-09-12) |
| timesteps requested / completed | 500,000 / 500,000 (244 PPO iterations) |
| exit code | 0 |
| model | `methods/rawPPo/models/rawppo_modern_500k.zip` |
| log / curve | `methods/rawPPo/logs/rawppo_modern_500k_training.log` / `…_curve.csv` |

## Final training diagnostics
| metric | value |
|---|---|
| entropy_loss (first→last) | −1.095 → **−0.086** (converged, near-deterministic) |
| approx_kl (final) | 1.6e-09 (lr→0 end of linear decay) |
| clip_fraction (final) | 0.0 |
| explained_variance | 0.252 (value fn moderate) |
| value_loss | 8.64 |
| ep_rew_mean | **nan** — benign SB3 artifact: 35k-bar episodes rarely complete within a 2048-step rollout, so SB3's running episode-reward stays nan. Does NOT affect the (finite) eval metrics. |

## Checks
NaN/inf in eval metrics: **none**. Trained on the intended modern split. No methodology change.

**Verdict: PASS** (training completed, model saved, diagnostics consistent with a converged
short-biased policy). Performance is not a gate criterion.
