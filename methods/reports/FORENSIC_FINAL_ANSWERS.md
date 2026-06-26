# FORENSIC FINAL ANSWERS

Every answer is backed by an executed diagnostic under `methods/`. Scope: correctness + parity,
not paper metrics.

| # | Question | Answer (evidence) |
|---|---|---|
| 1 | Code bug or bad policy under this split? | **Bad policy, not a code bug.** Mapping/PnL/cost/accounting/parity all verified correct; the −42% is the short book losing in a bull market. (TRADE_PNL, SYNTHETIC, parity 1.0) |
| 2 | Action mapping correct? | **Yes** — `{0:-1,1:0,2:+1}`, SB3 probs match position fracs, deterministic=argmax, identical RawPPO↔Nautilus. (ACTION_DISTRIBUTION) |
| 3 | PnL sign correct? | **Yes** — synthetic: long=+ on up, short=+ on down, flat=0. (SYNTHETIC_ACTION_PNL) |
| 4 | Costs only on position change? | **Yes** — `flat→long` costs, `long→long`=0, flip=2×. Not charged while holding. (SYNTHETIC + envs.py) |
| 5 | Reward punishes exposure? | **No** — stability = −\|Δposition\| (changes, not holding). But the per-bar drawdown penalty does discourage holding through dips. (REWARD_COMPONENT, prior) |
| 6 | High trade win rate, negative return — why? | **Negative expectancy, fat-tail short losses.** avg_loss 3.4× avg_win; long book +25%, short book −81%; top-5 worst all shorts (−11% to −18%). (TRADE_PNL) |
| 7 | Why mostly short (0.62)? | Genuine learned mean-reversion short (p_short=0.62). Both train+eval are bullish, so it's a **policy/reward-landscape** local optimum, not regime mismatch. (ACTION_DISTRIBUTION, REGIME_SPLIT) |
| 8 | Why flat_frac ≈ 0? | Policy mean p_flat = 0.014 — it almost never *wants* flat (≈99% exposure). Real intent, not a bug. (ACTION_DISTRIBUTION) |
| 9 | Why PPO updates near-frozen? | **Not frozen** — lr=1.7e-7 is the end of linear-decay-to-zero; final-iteration kl/clip/pg≈0 follow from lr≈0. Real issue = early convergence to low-entropy short bias, locked in by decay. (PPO_TRAINING_FREEZE) |
| 10 | Does the modern split reduce short bias? | **PENDING** — modern-split retrain (2017-2022/2023-2024, ent_coef 0.03) running; result appended to RAWPPO_MODERN_SPLIT_REPORT.md. |
| 11 | Does Nautilus match RawPPO on the same model? | **Yes** — action_match=1.0, position_match=1.0; equity diff ~4% from next-bar fills + integer-oz (documented). (RAWPPO_VS_NAUTILUS_PARITY) |
| 12 | What was changed? | run.py reporting (window/freq/n_periods + assertions, earlier); CSV-only loader + csv-override fix (earlier). New forensics under `methods/`. Proposed fix (ent_coef 0.01→0.03) under test — NOT yet applied to the canonical config. |
| 13 | What remains unresolved? | Whether the entropy bump / modern data actually reduces the short bias (test running). The reward's per-bar drawdown penalty favoring scalps over trend-holding is a design property, left unchanged per your earlier instruction. |

## One-line verdict
The −42.20% is a **valid bad policy** (short book blows up in a bull market), **not an
implementation defect**. The pipeline (data/features/normalization/actions/cost/accounting/metrics)
is verified correct and RawPPO↔Nautilus parity is exact on actions/positions. The open lever is
training dynamics (premature short-bias convergence), now being tested via the modern-split +
higher-entropy retrain.
