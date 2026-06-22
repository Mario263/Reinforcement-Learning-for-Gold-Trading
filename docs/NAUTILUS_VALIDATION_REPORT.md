# NAUTILUS VALIDATION REPORT (robustness, frozen policy)

> ⚠️ **SUPERSEDED (Phase 6).** Conclusion "no executable edge / −1.27%" was driven by a **fill-timing harness bug**, now fixed. Corrected result: Nautilus **+48.67%**, converging with the env. See `ROOT_CAUSE_REPORT.md` / `REPLICATION_CORRECTION_REPORT.md`.

Independent event-driven robustness validation of the **frozen** PPO Raw policy (weights unchanged, deterministic inference) in Nautilus Trader 1.202.0. Window: 621-day (2023-01-03 → 2024-09-12). Harness: `nautilus/strategy.py`, `nautilus/run_backtest.py`. Observation parity proven (`OBSERVATION_PARITY_REPORT.md`, diff 0).

## EXECUTION MODEL (documented)
Instrument `XAU/USD.SIM` CurrencyPair (prec 5, int oz); SIM venue, MARGIN/NETTING, $100k start, `MakerTakerFeeModel` taker=maker=**0.00015/fill** (commission+spread); fills via QuoteTicks (bid=ask=raw close), `bar_execution=False`; sizing 100% capital `floor(equity/price)`; honest **1-bar fill lag** (order on bar t fills ≈ `close[t+1]`).

## VALIDATION METRICS
| Metric | Value |
|---|---|
| Total trades (fills) | 85 |
| Round trips | 34 |
| Long trades (entries) | 29 |
| Short trades (entries) | 5 |
| Exposure (in-market) | ~18% |
| Win rate (per round trip) | 41.18% |
| Active win rate (in-market bars) | mirrors env stream; per-trade analog = 41.18% |
| Sharpe | −0.02 |
| Sortino | −0.01 |
| Calmar | −0.06 |
| Recovery factor | −0.12 |
| Max drawdown | −10.31% |
| CAGR | −0.60% |
| Return | −1.27% |
| Turnover | 85 fills (≈ env's 69 turnover units; difference is integer-fill granularity) |
| Holding duration | in-market avg 2.74 d, max 14 d (action stream identical to env) |
| Final equity | $98,731.32 |

## ROBUSTNESS FINDING
- The frozen policy **executes faithfully** (531/531 obs hits; action distribution 6/434/91 identical to the env; 34 round trips vs env's 35).
- Its **performance does not survive** event-driven execution: the env's +48.94% becomes **−1.27%** (full attribution in `NAUTILUS_VS_ENV_REPORT.md` / `ENVIRONMENT_NAUTILUS_PARITY_REPORT.md`).
- Edge cases (cold start, missing/NaN obs, inference failure, order/margin rejection, weekend gaps, timezone, position desync) handled and documented in `NAUTILUS_BACKTEST_REPORT.md`.

## VERDICT
The policy is **robust as code** (deterministic, reproducible, parity-verified) but **not robust as a strategy**: there is no executable edge on daily XAU/USD once fills are realistic. Weights were never altered.
