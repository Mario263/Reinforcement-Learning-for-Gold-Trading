# NAUTILUS TRADER BACKTEST REPORT

> ⚠️ **SUPERSEDED (Phase 6).** The −1.27% result here reflects a **fill-timing bug** (fills at stale `close[t-1]`) since fixed. Corrected Nautilus result = **+48.67%** (converges with env +48.94%). See `ROOT_CAUSE_REPORT.md` / `REPLICATION_CORRECTION_REPORT.md`.

Event-driven re-execution of the **trained PPO Raw policy** (inference only, `PPO.load`) inside Nautilus Trader 1.202.0, on the SAME 621-day window (2023-01-03 → 2024-09-12). Observations are the **precomputed eval-pipeline 22-vectors** (bitwise-consistent — `STATE_CONSISTENCY_AUDIT.md`). No retraining, no weight changes.

Harness: `nautilus/strategy.py` (RLPolicyStrategy), `nautilus/run_backtest.py`. Outputs: `nautilus/nautilus_metrics.json`.

## EXECUTION MODEL (documented)
- **Instrument:** `XAU/USD.SIM` `CurrencyPair`, price precision 5, size precision 0 (integer oz).
- **Venue:** SIM, MARGIN account, NETTING OMS, base USD, starting balance **$100,000**, `MakerTakerFeeModel`.
- **Fee:** maker=taker = **0.00015 per fill** = commission 0.01% + spread 0.005% (env-matched; spread carried in the fee, quotes are bid=ask so no double-count).
- **Fills:** market orders fill against **QuoteTicks** (bid=ask=raw close). `bar_execution=False` (bar-based fills left orders unfilled — see "Edge cases").
- **Sizing:** 100% capital, all-or-nothing → `units = floor(equity / price)`. Leverage raised only to prevent spurious margin rejections; real exposure capped at 100% by sizing (PnL is leverage-invariant).
- **Decision→fill timing:** order decided on bar *t* (using `close[t]`) fills at the **next available price ≈ `close[t+1]`** — an honest 1-bar execution lag (daily data has no intrabar prices). This differs from the RL env, which assumes a same-bar fill at `close[t]`.

## RESULTS (event-driven)
| Metric | Value |
|---|---|
| Total fills | **85** |
| Round trips | **34** |
| Long/Short/Flat days | 90 / 6 / 435 (action stream identical to env: 91 buy / 6 sell / 434 hold) |
| Exposure (in-market) | ~18% |
| Turnover (position-change fills) | 85 |
| Average holding period | ~2.7 days (action stream identical to env; see `POLICY_BEHAVIOR_REPORT.md`) |
| Trade win rate (per round trip) | **41.18%** (14/34) |
| Profit factor | **0.93** (losing) |
| Cumulative return | **−1.27%** |
| CAGR | **−0.60%** |
| Sharpe | **−0.02** |
| Sortino | **−0.01** |
| Calmar | **−0.06** |
| Recovery factor | **−0.12** |
| Max drawdown | **−10.31%** |
| Final equity | $98,731.32 (from $100,000) |

## TRADE DURATION / DISTRIBUTION
The policy's **action stream is bitwise-identical** to the evaluation pipeline (verified: 6 sell / 434 hold / 91 buy, 531/531 obs hits). Therefore holding-duration and long/short distributions match `POLICY_BEHAVIOR_REPORT.md` (in-market avg 2.74 d, max 14 d; long-biased 29 long vs 5 short entries). What differs is **realized P&L per trade**, not the trade pattern: under lagged fills, trade win rate drops from 74.29% (env, idealized) to **41.18%** (event-driven), and profit factor from 8.84 to **0.93**.

## EDGE CASES HANDLED (documented)
| Case | Handling |
|---|---|
| Cold start / insufficient history | obs precomputed over the whole window; no in-Nautilus warmup needed |
| Missing bar / date not in obs map | strategy holds (no order) — observed 0 misses (531/531 hit) |
| Feature NaN | `np.isfinite` guard → hold |
| Inference failure | try/except around `predict` → hold |
| Order rejection (min qty/notional) | instrument limits relaxed (min_qty 1, no notional cap); 0 rejections observed |
| Margin rejection | leverage raised so margin never binds; sizing caps real exposure at 100% |
| Bar-based fills not matching | switched to quote-driven fills (`bar_execution=False`); 85/85 orders filled |
| Position desync | net position read from `portfolio.net_position` each bar (source of truth) |
| Weekend/holiday gaps | daily bars already exclude non-trading days |
| Timezone drift | bar ts (UTC ns) → `pd.Timestamp(...,tz=UTC).normalize()` matches obs-map keys exactly |
| Duplicate bars | none (deduped upstream in `data.py`) |

## VERDICT
The trained policy **executes correctly and identically** inside Nautilus at the action level (same observations → same actions → same trade pattern, 34 round trips vs env's 35). However, its **profitability does not survive event-driven execution**: the env's +48.94% becomes **−1.27%** once fills occur at the next available price instead of the same close used to decide. The policy has **no executable edge** on daily XAU/USD bars. See `NAUTILUS_VS_ENV_REPORT.md` for the full delta attribution.
