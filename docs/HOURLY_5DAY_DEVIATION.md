# HOURLY + 5-DAY-WEEK DEVIATION (user-directed)

**Status:** ACTIVE. Two deliberate deviations from the paper, requested by the user (2026-06-23). The paper resamples to **daily**; this build runs on **hourly** bars, **Mon–Fri**. These are NOT paper-faithful and are documented as such. The PPO Raw paper-truth (`../researchPaper/PPO_RAW_GROUND_TRUTH.md`) is unchanged — only the implementation deviates.

---

## DEVIATION 1 — Hourly instead of daily

| | Paper | This build |
|---|---|---|
| Modeling frequency | Daily (§IV.A, p.6: "re-sampled to daily") | **Hourly** (1-min source → `resample("1h")`) |
| Bars (2017–2025, Mon–Fri) | ~2,000 daily | **49,690 hourly** (≈ the paper's stated 47,304 hourly obs) |
| Eval window bars | ~430–530 daily | **10,456 hourly** (Jan 2023 → Sep 2024) |

**Why the user wanted it:** keep the native hourly resolution rather than collapse to daily.
**Code:** `config.py` `resample_rule = "1h"`; `data.py` `_resample()`.

## DEVIATION 2 — 5 sessions/week (drop weekends)

The source is 1-minute XAU/USD. Weekday bar counts (raw minutes): Mon–Fri ≈ 1.3M each; **Saturday = 35** (stray), **Sunday = 1.1M** (gold's Sunday-evening session). The daily resample therefore produced a spurious **Sunday** bar → ~6 bars/week.

**Fix:** keep `index.weekday < 5` (Mon–Fri) → exactly 5 sessions/week. Verified: post-filter weekday counts are {Mon..Fri} only, zero weekend bars.
**Code:** `data.py` `_resample()` → `out = out[out.index.weekday < 5]`.

---

## FORCED DOWNSTREAM CONSTANTS (consequences of going hourly)

These are not separate features — daily→hourly makes the daily-calibrated constants wrong, so they were rescaled to preserve the paper's intent. Choices confirmed by the user.

| Constant | Was (daily) | Now (hourly) | Rationale |
|---|---|---|---|
| `ZSCORE_WINDOW` (Eq.13 z-score) | 252 (= 252 days) | **6048** | 252 trading days × 24h = 1-year window preserved |
| `periods_per_year` (Sharpe/CAGR annualization) | 252 | **6048** | same 252-trading-day basis, scaled to hourly; keeps Sharpe/CAGR comparable to the paper's daily figures |

`metrics.py:evaluate_model(periods_per_year=6048)`; `config.py:ZSCORE_WINDOW=6048`.

## WHAT DID **NOT** CHANGE (still paper-faithful)
22-feature state, feature order, reward Eq.22 (α/β/γ/δ = 1/2/0.5/0.1), action map {−1,0,+1}, 100% sizing, costs (commission 0.01% + spread 0.005%), PPO arch/hparams, 500k timesteps, calendar split dates, eval window dates. No Kalman. No leakage (z-score and indicators remain causal at hourly granularity).

---

## IMPACT — model & metrics are STALE

The saved model `models/ppo_xauusd_raw.zip` and `models/ppo_raw_metrics.json` were trained/evaluated on **daily** dynamics. The observation dimension is unchanged (22), so they load, but the policy learned daily patterns and is **invalid on hourly bars**. All daily-era performance numbers across `docs/` (e.g. +63.78%, 530 periods, Sharpe 2.13) are **superseded and pending a retrain**. No hourly metrics exist until:

```bash
python train.py            # retrain 500k timesteps on hourly Mon–Fri data
python nautilus/run_backtest.py
```

Retraining was **not** performed as part of this change (the user requested the code/doc edits and cleanups only). Until it runs, treat all reported metrics as daily-era history.

## VALIDATION (runnable check)
```bash
python -c "import sys; sys.path.insert(0,'src'); from rl_gold_trading.config import DataConfig; \
from rl_gold_trading.run import prepare; c,t,e,d=prepare(DataConfig()); \
assert (d.index.weekday<5).all(); assert d.index.to_series().diff().dropna().median().seconds==3600; \
print('hourly+5day OK', len(d), 'bars')"
```
