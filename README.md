# PPO Raw Baseline — XAU/USD (Paper Reproduction)

This repository has been transformed into a **faithful reproduction of the "PPO without Kalman filtering" (PPO Raw) baseline** from:

> Kili, Raouyane, Rachdi, Bellafkih. *Kalman-Enhanced Deep Reinforcement Learning for Noise-Resilient Algorithmic Trading in Volatile Gold Markets.* IJACSA 16(11), 2025.

It reproduces **only** the PPO Raw baseline (no Kalman, no DQN, no RPPO). The paper — not this codebase's original strategy — is the source of truth. See [docs/PPO_RAW_REPRODUCTION_REPORT.md](docs/PPO_RAW_REPRODUCTION_REPORT.md) and [../researchPaper/PPO_RAW_GROUND_TRUTH.md](../researchPaper/PPO_RAW_GROUND_TRUTH.md).

> ⚠️ **USER-DIRECTED DEVIATIONS FROM PAPER (active):** the pipeline now runs on **HOURLY** bars (the paper resamples to daily) and **5 sessions/week** (weekends dropped, Mon–Fri). The z-score window and metric annualization are scaled to keep their 1-year / 252-trading-day meaning (6048 hourly bars). Full record: [docs/HOURLY_5DAY_DEVIATION.md](docs/HOURLY_5DAY_DEVIATION.md). **The saved model + metrics are daily-era and STALE — a retrain is required before any hourly metrics are valid.**

> **Env ↔ Nautilus validated (Phase 6):** the RL-environment result (+48.94%) was independently reproduced in an event-driven **Nautilus Trader** backtest (**+48.67%**, Δ < 0.3 pp) after fixing a harness fill-timing bug. See [docs/ROOT_CAUSE_REPORT.md](docs/ROOT_CAUSE_REPORT.md) and [docs/REPLICATION_CORRECTION_REPORT.md](docs/REPLICATION_CORRECTION_REPORT.md).

## Methodology (paper values, except the two flagged deviations)
- **Data:** XAU/USD, 2017-01 → 2025-01, **resampled to HOURLY** OHLCV, **Mon–Fri only** (⚠️ deviation: paper uses daily; §IV.A). Source is 1-min → 1h.
- **State:** exactly **22 features** = 5 raw OHLCV + 17 technical indicators (SMA 10/20/50, EMA 12/26, MACD line+signal, RSI 14, Stochastic %K/%D, Bollinger 20±2σ, ATR 14, OBV, VWAP, CCI, Williams %R), computed with the `ta` library (§IV.B).
- **Normalization:** **6048-bar (1-year) causal rolling z-score** (§IV.B, Eq.13; paper's 252-day window scaled to hourly).
- **Split:** calendar — train 2017→2022; reported metrics on the window Jan 2 2023 → Sep 12 2024 (§IV.A), now ~10,456 hourly bars.
- **Action:** `Discrete(3)` → {sell −1, hold 0, buy +1}; **100% capital** (§IV.E).
- **Reward (Eq.22):** `1.0·Return − 2.0·Drawdown − 0.5·Cost + 0.1·Stability` (§IV.F).
- **Costs:** commission 0.01% + spread 0.005% (§IV.E).
- **Agent:** Stable-Baselines3 **PPO**, actor & critic `[512,512,256,128]` Tanh, clip 0.2, GAE 0.95, c₁0.5, c₂0.01, lr 3e-4 **linear decay**, n_steps 2048, batch 256, 10 epochs, γ 0.99, **500,000 timesteps** (§IV.G.2/H).

## Install
```bash
pip install stable-baselines3 gymnasium torch pandas numpy ta datasets
```

## Run
```bash
python train.py --smoke      # fast 5k-step sanity check
python train.py              # full 500k-step reproduction (train + eval)
python train.py --mode eval  # evaluate a saved model on the eval window (retrain first — daily model is stale)
```
Outputs: `models/ppo_xauusd_raw.zip`, `models/ppo_raw_metrics.json`.

## Paper PPO Raw target (Table I/II)
| Cumulative return | CAGR | Sharpe | Max drawdown | Win rate |
|---|---|---|---|---|
| 15.39% | 6.00% | 0.69 | −11.22% | 50.16% |

## Nautilus event-driven backtest
```bash
python nautilus/run_backtest.py    # -> nautilus/nautilus_metrics.json
python forensics/parity.py         # env-vs-Nautilus row-by-row diff CSVs
```

## Project structure
```
train.py                 # CLI entry point (train / eval)
src/rl_gold_trading/      # the paper-faithful PPO Raw pipeline
  config.py    data.py    features.py   normalize.py
  envs.py      vec_env.py train.py      metrics.py    run.py
nautilus/                 # event-driven Nautilus Trader backtest harness
  strategy.py            # RLPolicyStrategy (inference only)
  run_backtest.py        # instrument/venue/data/run + metrics
forensics/                # verification & parity scripts
  parity.py reconstruct.py fill_offset.py run_forensics.py attribution.py
  outputs/               # generated CSVs + JSON dumps
docs/                     # all audit / forensic / replication reports (30+)
models/                   # trained model + metrics JSON
logs/                     # training / install logs
```
Doc index: see `docs/` — start with `ROOT_CAUSE_REPORT.md`, `REPLICATION_CORRECTION_REPORT.md`, `PPO_RAW_REPRODUCTION_REPORT.md`, `PPO_PAPER_CONFORMANCE_CHECKLIST.md`.

## Notes
- This reproduces the paper's raw baseline faithfully; trade frequency is an **output**, never tuned.
- Documented paper-side under-specifications (2 of 17 indicators, S_stability formula, Sharpe annualization, market-impact/slippage parameters, data vendor) are listed in `docs/PPO_PAPER_CONFORMANCE_CHECKLIST.md`.
- Derived from `JonusNattapong/Reinforcement-Learning-for-Gold-Trading` (the original intraday strategy was replaced). MIT License. Research/educational use only; trading involves risk.
