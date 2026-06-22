# POLICY BEHAVIOR REPORT

Direct inspection of PPO Raw behavior on the 621-day window (530 daily periods), from `forensics/forensic_dump.json`. Inference only.

## ACTION DISTRIBUTION (raw policy outputs, deterministic)
| Action index | Meaning | Count | % |
|---|---|---|---|
| 0 | sell (−1) | 6 | 1.1% |
| 1 | hold (0) | 434 | 81.9% |
| 2 | buy (+1) | 90 | 17.0% |

The policy **predominantly outputs HOLD**, with a BUY minority and almost no SELL.

## RESULTING POSITION EXPOSURE
| State | Days | % |
|---|---|---|
| Long (+1) | 90 | 17.0% |
| Flat (0) | 434 | 81.9% |
| Short (−1) | 6 | 1.1% |
| **In-market (exposure)** | **96** | **18.1%** |

Capital utilization: 100% of equity when in-market (all-or-nothing, paper §IV.E), 0% when flat → **time-averaged exposure ≈ 18%**.

## HOLDING DURATIONS (consecutive constant-position runs, in trading days)
| Run type | Count | Avg | Max | Min |
|---|---|---|---|---|
| Flat (hold cash) | 34 | 12.76 | 65 | 1 |
| Long | 30 | 3.00 | 14 | 1 |
| Short | 5 | 1.20 | 2 | 1 |
| In-market (long+short) | 35 | 2.74 | 14 | 1 |

- **Average holding time (in-market):** 2.74 days. **Longest:** 14 days. **Shortest:** 1 day.
- **Longest cash spell:** 65 consecutive flat days.
- **Number of consecutive-hold runs:** 34 (flat segments). **Consecutive-long runs:** 30. **Consecutive-short runs:** 5.

## TRADE FREQUENCY
- 34 entries over 530 trading days ≈ **1 new trade every ~15.6 trading days**.
- 35 round trips; average trade duration ≈ **2.74 days**.

## BEHAVIORAL CHARACTERIZATION (evidence-based, not inferred)
- **Long-biased trend follower:** 29 long vs 5 short entries; long days 90 vs short 6 — tracks the gold uptrend.
- **Low turnover / high selectivity:** flat 82% of the time; this is the **converged** behavior under the paper's β=2α loss-averse reward (documented in `../../researchPaper/result_validation.md` F4), reproduced faithfully — **not** tuned.
- **Short positions are rare and brief** (avg 1.2 days, max 2) — the policy is reluctant to short a rising market.

## VERDICT
The PPO Raw policy behaves as a **cautious, long-biased, low-frequency** agent. This is internally coherent and is the expected converged outcome of the specified reward; nothing in the behavior indicates a broken policy (e.g., it is not stuck on a single action — it produces all three actions, enters/exits 35 times, and varies holding length 1–14 days).
