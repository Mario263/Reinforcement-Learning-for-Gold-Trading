# 10K RESULT ANALYSIS (Phase 11)

| dimension | RawPPO 10k | NautilusPPO 10k | bug? |
|---|---|---|---|
| position dist (s/f/l) | 0.42/0.38/0.20 | 0.29/0.33/0.38 | no — both span 3 states, no all-flat collapse |
| cumulative return | −19.6% | −9.5% | no — undertrained (4 iters) |
| sharpe | −1.16 | −0.42 | no |
| NaN/inf | none | none | no |
| training stability | entropy −1.09, kl ~1e-4 | entropy −1.09, kl ~2e-5 | no — healthy early-training |
| value function | ev −0.02, vloss 403 | ev −0.01, vloss 754 | no — value head untrained at 4 iters (expected) |
| feature count / z-score / annualization | 22 / 528 / 6048 | same | no |
| action mapping / accumulation | correct, no accum | correct | no |
| leverage | n/a (return-based) | ≤0.95 | no |
| Nautilus used for fills/accounting | n/a | yes (equity from Nautilus) | no |
| CLI uses methods/ tree | yes | yes | no |

## Why they differ (not a bug)
Separately-trained models (different RNG draws) + Nautilus's next-bar fill / integer-oz. Same-policy
parity already shows action/position match 1.0. The metric gap is execution + training-noise, not a
defect.

## Bugs found: **NONE**
No NaN/inf, no wrong feature count, no wrong z-score/annualization, no lookahead, no global scaler,
no action mismatch, no position accumulation, no multiplier mismatch, no unintended leverage, no
accounting inconsistency, no impossible metric combo, Nautilus genuinely used, CLIs on the new tree.
