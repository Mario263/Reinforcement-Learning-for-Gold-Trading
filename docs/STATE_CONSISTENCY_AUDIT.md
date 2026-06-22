# STATE CONSISTENCY AUDIT

Goal: confirm that **inference-time observations match training-time observations** (any mismatch would invalidate the evaluation). All checks run at runtime against the current code.

## CONSTRUCTION (single shared transform)
`run.py · prepare()` builds observations once:
```
feat, cols = add_features(load_data(cfg))     # 22 raw features + raw `price`
feat_z      = rolling_zscore(feat, cols)      # 252-day causal z-score (one transform)
train       = split_train_test(feat_z)[0]     # rows <= 2022-12-31
eval_df     = eval_window(feat_z)             # rows in [2023-01-02, 2024-09-12]
```
Both train and eval slices are taken from the **same `feat_z`**, so a given date's 22-vector is **identical** whether used in training or evaluation. The env reads `df[cols]` with no further transform.

## CHECKS (measured)
| Check | Requirement | Result |
|---|---|---|
| Feature ordering | `cols == FEATURE_ORDER` (fixed 22) | ✅ True |
| Feature count | exactly 22 | ✅ 22 |
| Observation shape | `(22,)` Box; eval matrix `(531, 22)` | ✅ |
| Normalization | 252-day causal z-score, same fn both splits | ✅ window=252 |
| Same-transform proof | eval row − `feat_z` row (same date) | ✅ max abs diff **0.0** |
| No global re-fit / VecNormalize | VecNormalize removed | ✅ none in pipeline |
| Missing values | no NaN in eval features | ✅ False |
| Inf values | none | ✅ False (inf→0 in `rolling_zscore`) |
| Lookback windows | indicators (≤50) + z-score (252) consumed in warmup | ✅ dropped pre-split |
| Data alignment | `feat` and `price` share the df index | ✅ env asserts equal length |
| Train/eval disjoint | no temporal overlap | ✅ train ≤ 2022-12-30 < eval ≥ 2023-01-03 |
| Raw price path | `price` preserved un-normalized for P&L | ✅ present (e.g. 1839.47) |
| dtype | env casts obs to `float32` | ✅ |

## CRITICAL NOTE — why this matters here
The **removal of VecNormalize** (Phase 3) is what makes train/eval observations identical. With VecNormalize (the original repo), training observations would be normalized by **running statistics** that differ from a fresh evaluation, causing silent feature drift. The deterministic 252-day z-score has **no internal state**, so the same date → the same vector, always.

## IMPLICATION FOR NAUTILUS (binding requirement)
To keep the Nautilus backtest **bitwise-consistent** with evaluation, the Nautilus strategy MUST consume the **same precomputed `eval_df[cols]` 22-vectors, indexed by bar timestamp** — it must **not** recompute indicators or re-normalize inside Nautilus. The forensic dump and the Nautilus harness both source observations from `run.prepare()`. (Recomputing indicators inside Nautilus would risk a different warmup/rolling-window state and break consistency.)

## VERDICT
Inference-time and training-time observations are **provably identical** (max abs diff 0.0), temporally disjoint, NaN/inf-free, correctly ordered and shaped. The evaluation is **not** invalidated by any state mismatch.
