# NAUTILUS vs RL-ENVIRONMENT COMPARISON

> ⚠️ **SUPERSEDED (Phase 6).** The −1.27% Nautilus figure and the "optimistic env vs honest execution" interpretation below were caused by a **Nautilus-harness fill-timing bug** (orders filled at the stale `close[t-1]`), now fixed. After the fix, Nautilus = **+48.67%**, converging with the env (+48.94%). See `ROOT_CAUSE_REPORT.md` and `REPLICATION_CORRECTION_REPORT.md`. The observation/action parity findings below remain valid.

Same trained policy, same window (621 days), same observations. The RL environment (`metrics.evaluate_model`) is an idealized vectorized backtest; Nautilus is an event-driven backtest. Any delta > 5% is explained below.

## SIDE-BY-SIDE
| Metric | RL Environment | Nautilus | Delta | >5%? |
|---|---|---|---|---|
| Cumulative return | **+48.94%** | **−1.27%** | −50.2 pp | ✅ explained |
| CAGR | +20.85% | −0.60% | −21.5 pp | ✅ explained |
| Sharpe | 2.04 | −0.02 | −2.06 | ✅ explained |
| Sortino | 2.32 | −0.01 | −2.33 | ✅ explained |
| Calmar | 6.74 | −0.06 | −6.80 | ✅ explained |
| Recovery factor | 15.81 | −0.12 | −15.9 | ✅ explained |
| Max drawdown | −3.10% | −10.31% | −7.2 pp worse | ✅ explained |
| Round trips | 35 | 34 | −1 | within noise |
| Trade win rate (per round trip) | 74.29% | 41.18% | −33 pp | ✅ explained |
| Profit factor | 8.84 | 0.93 | −7.9 | ✅ explained |
| Turnover (fills / changes) | 69 units | 85 fills | ~ aligned | within noise |
| Exposure | 18.1% | ~18% | ~0 | ✅ |
| Action distribution | 6/434/91 | 6/434/91 | **0** | identical |
| Holding duration (avg) | 2.74 d | ~2.74 d | ~0 | identical |

## ROOT-CAUSE: ONE-BAR EXECUTION LAG (quantified attribution)
The **action stream is identical** (verified bitwise). The entire P&L gap comes from **when fills occur**:
- **RL env:** the position decided on bar *t* (using `close[t]`) is credited the `close[t] → close[t+1]` return — i.e., it fills at the *same close it used to decide*. Mildly optimistic / look-ahead-adjacent.
- **Nautilus:** an order submitted on bar *t* fills at the **next available price ≈ `close[t+1]`** (daily bars have no intrabar prices). Honest event-driven execution.

Offline attribution (`forensics/attribution.py`), same actions, lag the fill by one bar:
| Convention | Cumulative | Max DD |
|---|---|---|
| Env (fill @ `close[t]`) | **+48.95%** | −3.10% |
| 1-bar lag (fill @ `close[t+1]`) | **−8.76%** | −18.26% |
| Nautilus (event-driven) | **−1.27%** | −10.31% |

The env's +48.95% **collapses to negative** the instant fills are lagged by a single bar. This proves the env's return is an **execution-timing artifact**, not a tradable edge: the policy's apparent skill lives entirely in the `close[t]→close[t+1]` move it cannot actually capture (it only learns of that move *at* `close[t]`).

## WHY NAUTILUS (−1.27%) SITS BETWEEN ENV (+48.95%) AND PURE LAG (−8.76%)
- **Quote at `ts+1` (price[t]):** some orders fill same-bar at `close[t]` (optimistic), others at the next bar (lagged) — a blend, so Nautilus is less negative than the pure 1-bar-lag model.
- **Integer-oz sizing** (`floor`) vs the env's fractional compounding — minor.
- **Fee timing** (per-fill cash deduction vs per-step fractional) — minor.
These second-order effects (<a few pp) account for the −1.27% vs −8.76% difference; the **first-order driver is unambiguously the fill lag**.

## INTERPRETATION
1. The policy **runs correctly** in Nautilus — identical observations and actions confirm the model and pipeline are sound (this validates the trained policy *mechanically*).
2. The policy's **reported profitability does not survive** high-fidelity execution. On daily XAU/USD bars, with realistic next-price fills, it is **flat-to-negative** (−1.3%).
3. This is consistent with, and strengthens, the Phase-1/Phase-3 conclusion that the env's headline numbers are optimistic; here the optimism is pinned to a **specific, quantified mechanism (same-bar fills)**, not hand-waving.

## CAVEATS
- Daily bars cannot distinguish `open[t+1]` from `close[t+1]`; a real desk deciding at the daily close would likely fill near `open[t+1] ≈ close[t]`, so the *true* executable return is somewhere between Nautilus (−1.3%) and env (+49%) — but the **sign of the edge is not robust**, which is the decision-relevant finding.
- Single seed / single model; the conclusion is about *this* trained policy's executability, not about PPO in general.
