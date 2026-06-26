# NORMALIZATION PARITY REPORT (Phase 3)

Single source: `methods.shared.normalization.rolling_zscore` (only definition). CSV:
`methods/outputs/parity/normalization_parity.csv`. Window 2023-04-03..2023-04-28, 409 obs rows.

| property | value |
|---|---|
| `ZSCORE_WINDOW` | **528** rolling bars/observations |
| unit | bars (1 bar = 1H) ≈ one trading month |
| mean/std | `rolling(528, min_periods=528)`, `std(ddof=0)` |
| zero-std handling | `sigma.replace(0, NaN)` → row dropped |
| ±inf handling | `replace(±inf, 0)` |
| global scaler / MinMax / full-dataset StandardScaler | **none** |
| lookahead | none (trailing window incl. t) |
| daily resampling | none |
| warmup / first valid | first `W-1`=527 rows dropped; obs computed on FULL series then sliced (same warmup for train+eval) |
| NaN after warmup | **0** (verified: `np.isnan(obs).sum() == 0`) |

RawPPO == shared and NautilusPPO == shared (both consume the shared z-scored frame) → **max_abs_diff 0.0**.

**Verdict: PASS.** 528-bar causal z-score, single source, identical across frameworks, no NaN/lookahead/global-scaler.
