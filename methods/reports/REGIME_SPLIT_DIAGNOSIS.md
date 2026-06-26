# REGIME SPLIT DIAGNOSIS (Phase 7)

Source: `methods/forensic_model_audit.py` → `rawPPo/diagnostics/regime_split_market_stats.csv`.
Market-only (buy & hold) stats, no model.

| window | period | buy&hold return | ann. vol | up-bar frac | buy&hold max DD |
|---|---|---|---|---|---|
| **train** | 2003-06 → 2019-12 | **+345.8%** | 17.8% | 0.504 | −45.2% |
| **eval** | 2020-01 → 2026-06 | **+169.8%** | 18.1% | 0.512 | −27.3% |

## Conclusion (evidence)
- **Both train and eval are strong BULL regimes** (gold +346% then +170%), similar volatility and
  up-bar fraction. The eval period is *not* an unusual regime relative to training.
- Therefore the short bias is **NOT explained by a bearish training regime** — the model learned to
  short despite training on a +346% uptrend. This points the cause at the **policy / reward
  landscape**, not a train/eval regime mismatch.
- A persistent short-biased policy is *expected to lose* in a +170% eval (confirmed by the trade
  audit: short book −81%). But since training was also bullish, a correctly-learning agent should
  have favored long. That it did not is evidence of premature convergence to a local optimum —
  examined in PPO_TRAINING_FREEZE_DIAGNOSIS.md and tested by the modern-split retrain
  (RAWPPO_MODERN_SPLIT_REPORT.md).
