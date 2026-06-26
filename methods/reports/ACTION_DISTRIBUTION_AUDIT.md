# ACTION DISTRIBUTION AUDIT (Phase 2)

Source: `methods/forensic_model_audit.py` → `rawPPo/diagnostics/action_probability_audit.csv`.
Probabilities are the **actual SB3 Categorical policy** (`policy.get_distribution(obs).distribution.probs`),
not a guess. Model: `models/ppo_xauusd_raw.zip`, eval 2020-01→2026-06 (37,735 bars).

## Result
| | short (id 0) | flat (id 1) | long (id 2) |
|---|---|---|---|
| argmax action count | 23,511 | 407 | 13,816 |
| **mean probability** | **0.622** | **0.014** | **0.364** |
| target-position frac | 0.623 | 0.011 | 0.366 |

## Conclusions (evidence)
- **The model genuinely outputs short ~62%.** The policy *probabilities* (not just `predict`)
  put mean 0.62 mass on short. This is a real learned bias, **not an action-mapping bug**.
- **Mapping is correct & consistent:** deterministic prediction = argmax of these probs (by
  construction), and position fracs match the probs. Mapping `{0:-1, 1:0, 2:+1}` is identical in
  RawPPO and NautilusPPO (parity action_match = 1.0, prior report).
- **Flat is genuinely almost never chosen** (mean p_flat = 0.014). The policy almost always wants
  to be in-market — consistent with exposure_frac ≈ 99%.
- No train/eval or RawPPO/Nautilus mapping mismatch (verified).

So `short_frac=0.62` is the model's real intent. *Why* it is short-biased and loses → see
TRADE_PNL_DISTRIBUTION_AUDIT.md and REGIME_SPLIT_DIAGNOSIS.md.
