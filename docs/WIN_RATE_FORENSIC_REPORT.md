# WIN-RATE FORENSIC REPORT

**Scope:** explain the `10.75%` vs `59.38%` win-rate figures for the trained PPO Raw model. All numbers are read **directly** from a deterministic inference rollout of the saved model on the 621-day window (`forensics/run_forensics.py` → `forensics/forensic_dump.json`). No retraining, no assumptions.

Rollout: model `models/ppo_xauusd_raw.zip`, window **2023-01-03 → 2024-09-12**, **530 daily periods**.

---

## EXACT CODE PATH (`src/rl_gold_trading/metrics.py`)
```python
win_rate = float((net_rets > 0).mean())                       # line: all-period
in_market = pos != 0
active_win_rate = float((net_rets[in_market] > 0).mean())     # line: in-market only
```
- `net_rets[t]` = `info["net_ret"]` from `envs.py` = `r_port - cost_frac`, where `r_port = target_position * price_ret` and `cost_frac = |Δposition|·(0.0001+0.00005)`.
- `pos[t]` = `info["position"]` = the position **held over step t** (the action's target).
- A **flat** step (`position==0`, no turnover) has `net_ret == 0` → **not** `> 0` → never a "win".

## THE TWO NUMBERS (measured)
| Quantity | Value | Numerator | Denominator |
|---|---|---|---|
| `win_rate` (all-period) | **10.75%** | 57 winning periods | **530** (all periods) |
| `active_win_rate` (in-market) | **59.38%** | 57 winning periods | **96** (periods with position ≠ 0) |
| `trade_win_rate` (per round-trip) | **74.29%** | 26 winning trades | **35** (round trips) |

Winning periods = 57 in **both** win-rate rows, because all profits occur on in-market days (flat days contribute exactly 0). Only the **denominator** changes.

## ANSWERS TO THE 7 REQUIRED QUESTIONS
1. **What does 10.75% represent?** The fraction of **all 530 daily periods** whose net strategy return was strictly positive (57/530). Because the agent is flat 434/530 days (those days = 0 return), the figure is mechanically capped near the in-market fraction (~18%).
2. **What does 59.38% represent?** The fraction of **in-market periods** (position ≠ 0; 96 days) that were profitable (57/96).
3. **Same denominator?** **No.** 530 vs 96.
4. **Is one over all periods?** Yes — `10.75%` uses all 530 periods.
5. **Is one only during active positions?** Yes — `59.38%` uses only the 96 position≠0 periods.
6. **Which corresponds to the paper?** The paper's PPO-Raw win rate is **50.16%** with **no stated formula** (`../../researchPaper/PPO_RAW_GROUND_TRUTH.md` §6). The paper's raw agent is reported as **overtrading** (almost always in-market), so its all-period and active win rates would nearly coincide. For *our* undertrading agent the **all-period 10.75% is NOT a valid comparison** to the paper's 50.16% (it mostly measures how rarely we trade). The comparable analogs are **active win rate (59.38%)** or **per-trade win rate (74.29%)**.
7. **Which is actually meaningful?** For a low-turnover policy, **all-period win rate is misleading** — it is dominated by flat zeros and conflates "how often profitable" with "how often in the market." The **meaningful** measures are **active win rate** (per in-market bar) and **trade win rate** (per round trip). The Nautilus backtest will report trade-level win rate (per closed position) as the primary, event-driven figure.

## VERDICT
Both numbers are **correctly computed and mutually consistent** (same 57 wins, different denominators). They are **not** in conflict — they answer different questions. The `10.75%` headline is a true-but-misleading artifact of an 82%-flat policy; it should **not** be compared to the paper's 50.16%. Use **active (59.38%)** or **per-trade (74.29%)** for any paper comparison, and the Nautilus per-trade win rate as the cross-check.
