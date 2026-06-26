# PPO TRAINING FREEZE DIAGNOSIS (Phase 10)

## The reported "freeze" numbers are END-OF-TRAINING artifacts
```
approx_kl = 8.7e-11   clip_fraction = 0   policy_gradient_loss = -1.1e-7
learning_rate = 1.73e-07   total_timesteps = 501760
```
RawPPO uses **linear LR decay to zero**: `lr = 3e-4 × progress_remaining` (`train.linear_schedule`).
At the final rollout `progress_remaining ≈ 0`, so **lr ≈ 1.7e-7 ≈ 0**. With `lr ≈ 0` the optimizer
step is ~0, so `approx_kl`, `clip_fraction`, and `policy_gradient_loss` are **necessarily ≈ 0**.
These are the *last iteration's* stats, not evidence the optimizer was stuck the whole run.

| symptom | benign explanation |
|---|---|
| lr = 1.73e-7 | end of linear-decay-to-zero schedule (by design) |
| approx_kl ≈ 0, clip_fraction = 0, pg_loss ≈ 0 | consequence of lr ≈ 0 at the final update |
| entropy_loss = −0.03 | policy converged to near-deterministic (short-biased) after 500k |
| explained_variance = 0.40 | value function works (moderate, **not broken**) |
| value_loss = 4.02 | finite, not diverging |

## Curve evidence (confirms the reframe) — `rawPPo/diagnostics/ppo_training_curve_modern_entc03.csv`
A fresh 150k run logged per-iteration. `approx_kl` stayed **healthy (2e-3 … 9e-3) for the entire
run** and dropped to **9e-8 only at the final iteration** (lr = 9.9e-7). So PPO *was* updating
throughout; the near-zero stats appear only when the LR schedule reaches ~0. `entropy_loss`
decayed **gradually** (−1.09 → −0.37), i.e. **no early collapse** under ent_coef 0.03.

**Verdict:** not a frozen optimizer. The concern that *is* real: the policy converged to a
**short-biased low-entropy** solution, and linear-decay-to-zero LR then **locks it in** (no
late-stage escape). Whether entropy collapsed *early* (premature convergence) needs the training
curve — captured by `methods/train_modern_split.py`'s `CurveLogger`
(`rawPPo/diagnostics/ppo_training_curve_*.csv`).

## Proposed evidence-based change (Rule 2 satisfied: data/action/reward/cost/accounting all verified)
Raise the **entropy coefficient** (`ent_coef` 0.01 → 0.03) to keep exploration alive and resist
premature collapse into the short-bias local optimum. This is the one knob targeted at the
observed failure mode; it does **not** touch reward coefficients, PnL, costs, or architecture.
Being tested now on the modern split (2017-2022 train / 2023-2024 eval) with curve logging —
results in RAWPPO_MODERN_SPLIT_REPORT.md. (Curve-evidence update appended when the run completes;
if the curve shows entropy was already healthy and only the *outcome* is short-biased, the bias is
reward-landscape-driven and the entropy bump alone will not fix it — reported honestly either way.)
