# 10K GPU CLI VALIDATION REPORT (Phase 10)

Both frameworks run through the **actual CLIs** (not internal helpers), modern split
(train 2017-2022 = 34,966 rows, eval 2023-01→2024-09 = 9,897 rows), `--device cuda`.
torch 2.11.0+cu128, CUDA on RTX 5080.

| | RawPPO | NautilusPPO |
|---|---|---|
| command | `python -m methods.rawPPo.scripts.train --split modern --total-timesteps 10000 --device cuda --model-out methods/rawPPo/models/rawppo_modern_10k.zip` | `python -m methods.nautilus.scripts.train --split modern --total-timesteps 10000 --device cuda --model-out methods/nautilus/models/nautilusppo_modern_10k.zip` |
| exit code | 0 | 0 |
| GPU device | RTX 5080 (`Using cuda device`) | RTX 5080 |
| timesteps | 10,000 (≈4 PPO iters) | 10,000 (≈4 iters) |
| approx_kl (final) | 6.70e-05 | 2.14e-05 |
| entropy_loss (final) | −1.090 | −1.091 |
| explained_variance | −0.022 | −0.010 |
| value_loss | 403.1 | 754.7 |
| pos short/flat/long | 0.42/0.38/0.20 | 0.29/0.33/0.38 |
| cum / sharpe / maxDD | −19.6% / −1.16 / −23.9% | −9.5% / −0.42 / — |
| NaN/inf in metrics | none | none |
| model saved | `…rawppo_modern_10k.zip` ✓ | `…nautilusppo_modern_10k.zip` ✓ |
| deterministic eval | yes (`predict(deterministic=True)`) ✓ | yes ✓ |
| metrics json | `…_metrics.json` ✓ | `…_metrics.json` ✓ |

## Reading the numbers
4 PPO iterations is barely-started training — entropy ≈ max (−1.09), explained_variance ≈ 0
(value head untrained), value_loss high. **All expected at 10k steps; none are bugs.** No NaN/inf,
no all-flat collapse (distributions span all three), both CLIs use the new `methods/` tree on GPU.

**Verdict: PASS** — both CLIs run end-to-end on GPU, finite metrics, save OK.
