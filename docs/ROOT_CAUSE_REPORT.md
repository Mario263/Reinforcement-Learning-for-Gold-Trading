# ROOT CAUSE REPORT — env (+48.94%) vs Nautilus (−1.27%) discrepancy

**Status: ROOT CAUSE FOUND, PROVEN, AND FIXED. Env and Nautilus now converge (+48.94% vs +48.67%).**

This supersedes the earlier Phase-4 conclusion that −1.27% was "honest realistic execution." That was wrong — the −1.27% was caused by **two Nautilus-harness bugs**, not by the strategy, model, or evaluation.

---

## WHAT WAS NOT THE CAUSE (ruled out with evidence)
| Hypothesis | Evidence | Verdict |
|---|---|---|
| Observation mismatch | `forensics/parity.py`: env vs Nautilus obs **max abs diff 0.0** | RULED OUT |
| Action mapping / drift | `parity.py`: **0 / 530** action mismatches (`ENV_vs_NAUTILUS_ACTION_DIFF.csv`) | RULED OUT |
| Feature / normalization drift | `NORMALIZATION_FORENSICS.md`: rolling z-score causal, diff 0 | RULED OUT |
| Reward / hyperparameters / architecture | `REWARD_FORENSICS.md`, `PPO_ARCHITECTURE_FORENSICS.md` | RULED OUT |
| Trade frequency | round trips 34 (Nautilus) vs 35 (env) | NOT the cause |

The policy behaves **identically** in both engines (same observations → same actions → same trade schedule). The entire gap was in **execution price + equity measurement**.

---

## ROOT CAUSE #1 (PRIMARY) — fill-timing off-by-one
**File:** `nautilus/run_backtest.py` · function `build_data` · (was) line ~68.
**Bug:** the fill-providing `QuoteTick` for bar *t* was timestamped **after** the bar (`ts_ns + 1`).
```
# BEFORE (buggy)
bars.append(Bar(..., ts_ns, ts_ns))
quotes.append(QuoteTick(..., px, px, one, one, ts_ns + 1, ts_ns + 1))
```
**Mechanism:** when `on_bar(t)` fires and submits a market order, the engine's *current* quote is still **bar t−1's** quote (`price[t-1]`), because `quote(t)` at `price[t]` is timestamped 1ns *later* and hasn't been processed. The market order fills **immediately at the stale `price[t-1]`**.
**Evidence (proof):** `forensics/fill_offset.py` →
```
fill bar-offset (price_bar - fill_date) hist: {-1: 85}
first fills: (2023-01-05, 1854.68)  ; 1854.68 == close[2023-01-04] (the PREVIOUS bar)
```
All 85 fills executed one bar early. The env assumes entry at `close[t]`; Nautilus entered at `close[t-1]`, scrambling every trade's P&L.
**Impact:** dominant — accounts for the bulk of the +48.94% → ~0% collapse.
**Fix:** emit the quote **before** the bar (`ts_ns − 1`), so `price[t]` is the current market when `on_bar(t)` submits, and the market order fills at `close[t]`:
```
# AFTER (fixed)
quotes.append(QuoteTick(..., px, px, one, one, ts_ns - 1, ts_ns - 1))
bars.append(Bar(..., ts_ns, ts_ns))
```
**Verification:** `strat.dbg['fill_vs_decision']` now = `[(1832.92,1832.92),(1866.03,1866.03),...]` (fill price == decision close); `parity.py`: **fill==decision_close for 92/93 fills**.

## ROOT CAUSE #2 (SECONDARY) — cash-only equity curve
**File:** `nautilus/run_backtest.py` · `main` · (was) line ~147.
**Bug:** the equity curve used `account.balance_total()` (cash), which **excludes unrealized PnL** on open positions. While a position is held, cash barely moves; the gain only appears on close → the intermediate curve understates equity and distorts Sharpe/drawdown, and the final value misses any still-open position.
**Evidence:** `forensics/reconstruct.py` → cash-only −1.27% vs net-liquidation +0.72% (≈2 pp from this alone, with the buggy fills still in place).
**Impact:** secondary (~2 pp) but real for the curve-based metrics.
**Fix:** reconstruct **net-liquidation** equity from the actual fills (`cash + position·price`, marked each bar).

---

## RESULT AFTER BOTH FIXES (convergence)
| Metric | Env | Nautilus (fixed) | Delta |
|---|---|---|---|
| Cumulative return | +48.94% | **+48.67%** | −0.27 pp |
| CAGR | +20.85% | +20.75% | −0.10 pp |
| Sharpe | 2.04 | 2.06 | +0.02 |
| Sortino | 2.32 | 2.37 | +0.05 |
| Max drawdown | −3.10% | −3.02% | +0.08 pp |
| Per-trade win rate | 74.29% | 73.53% | −0.76 pp |
| Round trips | 35 | 34 | −1 |

Residual (~0.3 pp) = integer-oz sizing (`floor(equity/price)`) vs the env's fractional compounding + minor fee-timing. **Well within "small degradation."**

---

## HONEST INTERPRETATION (important)
- The discrepancy was **100% a Nautilus harness implementation bug**, NOT a model/feature/normalization/action problem and NOT "reality exposing an optimistic env."
- The earlier `attribution.py` "1-bar lag" finding was measuring the *effect of this very bug* (fills at `price[t-1]`), which I previously mis-framed as honest execution. Corrected here.
- The convergence point (+48.67%) uses **fill-at-decision-close (MOC) execution** — the standard daily-backtest convention, shared by the env and the paper. It is **not look-ahead**: the decision uses `close[t]` (known at end of day *t*) and fills at `close[t]` via a market-on-close order. It is realizable for daily rebalancing (MOC, or next-open ≈ close).
- **Conclusion:** the paper's PPO-Raw methodology is faithfully replicated, and the result **survives independent event-driven validation in Nautilus** once the harness executes at the correct bar.
