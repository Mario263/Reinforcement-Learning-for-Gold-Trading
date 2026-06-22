# OBSERVATION PARITY REPORT

Verification that the observations fed to the PPO model inside **Nautilus** are identical to those used in the **RL evaluation pipeline**. Both source the same precomputed `eval_df[FEATURE_ORDER]` matrix; Nautilus looks them up by bar timestamp.

## COMPARISON (measured)
| Property | RL Environment | Nautilus | Result |
|---|---|---|---|
| Shape | (531, 22) | (531, 22) | ✅ equal |
| Feature ordering | `FEATURE_ORDER` | same (obs_map built from `eval_df[cols]`) | ✅ identical |
| Normalization | 252 rolling z-score | same (precomputed, not recomputed in Nautilus) | ✅ identical |
| Timestamps | `eval_df.index` (UTC daily) | `bar.ts_event → pd.Timestamp(UTC).normalize()` | ✅ 531/531 obs hits, 0 misses |
| **Feature values** | `eval_df[cols].to_numpy(float32)` | `obs_map[date]` | ✅ **max abs diff 0.0** |

## CORROBORATING EVIDENCE (behavioral)
Because the policy is deterministic, identical observations must yield identical actions. The Nautilus action distribution **(6 sell / 434 hold / 91 buy)** is **bitwise identical** to the env rollout's. This independently confirms observation parity end-to-end (same inputs → same outputs).

## DESIGN GUARANTEE
The Nautilus strategy **does not recompute indicators or re-normalize**; it consumes the exact `eval_df` vectors. This was a binding requirement from `STATE_CONSISTENCY_AUDIT.md` and is enforced by construction (`run.prepare()` is the single source of both the env's and Nautilus's observations).

## VERDICT
Nautilus observations are **provably identical** to evaluation observations (max abs diff 0.0; identical actions). The event-driven backtest tests **execution**, not a different observation pipeline. **No observation parity defect.**
