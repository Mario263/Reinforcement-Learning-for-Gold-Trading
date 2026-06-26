# CURRENT RUN CONFIGURATION AUDIT (Phase 1)

From executed pipeline (`run.py` prepare + eval, 2026-06-25). No hidden defaults — RawPPO uses
`DataConfig` (csv-only, no fallback) and prints the window/frequency explicitly.

| field | value |
|---|---|
| csv_path | `data/processed/xauusd_1h_2003_2026.csv` (resolved to repo root; CSV-only, no HF fallback) |
| raw range | 2003-05-05 → 2026-06-24 (137,940 bars after Mon-Fri + ffill) |
| frequency | HOURLY (1 bar = 1h), `resample_rule="1h"`, no daily resample |
| normalization | 528-bar rolling z-score (**bars**, causal, per-feature, no global scaler) |
| obs_dim / feature_order | 22 / `config.FEATURE_ORDER` (saved; identical RawPPO↔Nautilus) |
| train | 2003-06-09 → 2019-12-31, **99,586 rows** |
| eval | 2020-01-01 → 2026-06-24, **37,735 rows** (cal_days 2365 ≈ 6.5y) |
| timezone | UTC throughout |
| duplicates / NaN / inf | deduped on load; post-warmup NaN=0, inf→0 (normalize) |

## Hard-fail checks
- frequency explicit: **PASS** (printed HOURLY).
- normalization units clear: **PASS** (bars, documented).
- feature_order saved: **PASS**.
- eval_rows match range: **PASS** (`assert n_periods == eval_rows-1` in run.py).
- hidden defaults: **none** (csv-only; `--csv` overrides only if given).

Saved alongside: `rawPPo/diagnostics/action_probability_audit.csv` (per-bar obs-driven actions),
`regime_split_market_stats.csv`.
