> ⚠️ **DAILY-ERA — SUPERSEDED.** This report describes the original **daily** pipeline. The build now runs **hourly + 5-day-week** (user-directed). Performance numbers below are daily-era and STALE pending a retrain. See [HOURLY_5DAY_DEVIATION.md](HOURLY_5DAY_DEVIATION.md).

# NORMALIZATION FORENSICS

Verification of the 252-day rolling z-score (PDF p.6, Eq.13). Source: `normalize.rolling_zscore`.

## FORMULA (code)
```
mu    = s.rolling(252, min_periods=252).mean()
sigma = s.rolling(252, min_periods=252).std(ddof=0)
z     = (s - mu) / sigma.replace(0, NaN)
dropna(subset=features); replace ±inf -> 0
```
Matches Eq.13: `z_t = (x_t − μ_{t-252:t}) / σ_{t-252:t}`, per-feature.

## CHECKS (measured)
| Check | Method | Result |
|---|---|---|
| Rolling window alignment | `rolling(252)` is trailing/backward | ✅ trailing |
| **Future leakage** | recompute z at test date d using only data ≤ d, compare to full-series z at d | **max abs diff 0.0** for 2023-01-15, 2023-08-23, 2024-04-15 → strictly causal, **no leakage** |
| NaN handling | `dropna(subset=features)` post-z-score | 0 NaN in eval matrix |
| Inf handling | zero-variance window → `replace(±inf, 0)` | 0 inf in eval matrix |
| Warmup | first 252 obs (+ indicator warmup) dropped before split | train starts 2017-12-17 (after ~1y warmup from 2017-01) |
| Train/inference consistency | same `rolling_zscore` fn for both; train/eval slices from one transform | **max abs diff 0.0** (eval row == full-series row) |
| Global re-fit / VecNormalize | removed | none present |

## WHY THIS RULES OUT LEAKAGE AS A CAUSE OF OUTPERFORMANCE
The leakage test is decisive: the z-score for any test date is **identical** whether computed on the full series or on data truncated at that date (diff = 0). Therefore the normalization uses **no future information**. The reproduced outperformance vs the paper is **not** caused by normalization leakage. (Root cause is analyzed in `ROOT_CAUSE_ANALYSIS.md`.)

## VERDICT
The 252-day rolling z-score is implemented exactly per the paper, is strictly causal (proven, diff 0), NaN/inf-safe, and identical between training and inference. **No normalization mismatch or leakage.**
