> ⚠️ **DAILY-ERA — SUPERSEDED.** This report describes the original **daily** pipeline. The build now runs **hourly + 5-day-week** (user-directed). Performance numbers below are daily-era and STALE pending a retrain. See [HOURLY_5DAY_DEVIATION.md](HOURLY_5DAY_DEVIATION.md).

# PPO PAPER CONFORMANCE CHECKLIST

State of the Region-II reproduction vs paper. ☑ = conformant now · ☐ = gap (fix before "faithful" run) · ◐ = paper under-specified (document-only, cannot be made exact).

> **Gate:** training may not begin until all ☐ are resolved or explicitly re-classified to ◐ with a documented assumption (your approval required).

## Dataset
☑ Instrument XAU/USD · ☑ date range 2017–2025 · ◐ vendor unverifiable

## Date Range
☑ 2017-01-01 → 2025-01-31

## Frequency
☑ **Daily** (paper "re-sampled to daily frequency", p.6)

## Resampling
☑ OHLC aggregation to `1D` · ☐ **forward-fill missing daily bars** (currently dropna)

## Train/Test Split
☐ **Calendar split** train 2017–2022 / test 2023–2025 (currently 70% row fraction) — 🔴
☐ **Eval restricted to 621-day window** Jan 2 2023 → Sep 12 2024 — 🟠

## Feature Count
☑ Exactly 22 (5 OHLCV + 17 indicators)

## Indicator Definitions
☑ 15 enumerated (SMA10/20/50, EMA12/26, RSI14, Stoch%K/%D, Boll20±2σ, ATR14, OBV, VWAP, CCI, WilliamsR)
◐ The 2 indicators completing 17 are **unspecified** in the paper → using **MACD line + signal** (documented assumption)

## Normalization
☑ Rolling 252-day z-score, causal, per-feature, no leakage (Eq.13)

## Action Space
☑ Discrete(3) → {−1, 0, +1} = sell/hold/buy

## Reward
☑ Eq.22 with α=1.0, β=2.0, γ=0.5, δ=0.1 · ☑ R_portfolio = position·return · ☑ DD running-max
◐ S_stability formula absent → using −|Δposition| (documented) · ◐ "relative to benchmark" prose has no formula term → omitted (faithful to Eq.22)

## PPO Architecture
☑ Actor & critic [512,512,256,128], Tanh hidden, softmax actor / linear critic (verified by printing policy)

## Hyperparameters
☑ clip 0.2 · ☑ GAE 0.95 · ☑ c₁ 0.5 · ☑ c₂ 0.01 · ☑ lr 3e-4 linear→0 · ☑ rollout 2048 · ☑ minibatch 256 · ☑ epochs 10 · ☑ γ 0.99 · ☑ 500,000 timesteps
◐ curriculum "progressive difficulty" mechanism unspecified → not implemented (documented)

## Evaluation Metrics
☑ cumulative return, CAGR, Sharpe, max drawdown, win rate (+ Sortino/Calmar/Recovery/VaR computable)
◐ Sharpe annualization factor unspecified → √252 (documented)

## Transaction Costs
☑ commission 0.01% · ☑ spread 0.005%
☐ **market impact σ√(volume/ADV)** (not implemented) — 🟠 (needs ADV assumption)
☐ **linear slippage** (not implemented) — 🟠 (needs coefficient assumption)

## No Kalman
☑ Confirmed — no Kalman/DQN/RPPO anywhere in Region II

---

## SUMMARY
- ☑ conformant: **22 items**
- ☐ gaps to close: **5** → calendar split, 621-day eval window, market impact, slippage, forward-fill
- ◐ document-only (paper under-specified): **6** → 2 indicators, S_stability formula, benchmark term, Sharpe factor, ADV, curriculum

**Current conformance score (closable items only): 22 / 27 ≈ 81%.** Reaching ~100% of *closable* items requires the 5 ☐ fixes. The 6 ◐ items are bounded by the paper itself and will be locked with documented assumptions.
