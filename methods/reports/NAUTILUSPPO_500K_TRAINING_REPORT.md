# NAUTILUSPPO 500K TRAINING REPORT (Phase 5) — corrected (post MtM fix)

| item | value |
|---|---|
| command | `python -m methods.nautilus.scripts.train --split modern --total-timesteps 500000 --device cuda --model-out methods/nautilus/models/nautilusppo_modern_500k.zip` |
| device | cuda (RTX 5080) | torch | 2.11.0+cu128 |
| accounting | **corrected** — per-bar mark-to-market (FULL_500K_FIX_LOG.md) |
| timesteps | 500,000 / 244 iters | exit | 0 |
| simulator | Nautilus `BacktestEngine` (thread-bridge); fills/positions/cash/PnL Nautilus-owned |

## Final training diagnostics (corrected)
| metric | buggy run | **corrected run** |
|---|---|---|
| entropy_loss first→last | −1.095 → −0.134 | −1.095 → **−0.066** |
| explained_variance | **−0.43** (value head failing) | **+0.16** (value head learns) |
| value_loss | 77.9 | **4.09** |
| position dist (s/f/l) | 0.27 / 0.71 / 0.016 | **0.003 / 0.47 / 0.524** |

With a correct per-bar reward signal the value function learns (ev −0.43 → +0.16) and the policy
converges **long-biased** (52% long) instead of the flat collapse the broken reward produced.

**Verdict: PASS** — completed on GPU via the Nautilus-backed env with corrected accounting; valid
reward signal; converged sensibly. (Performance is not a gate criterion.)
