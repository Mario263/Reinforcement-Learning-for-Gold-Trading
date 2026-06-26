# TRADE PnL DISTRIBUTION AUDIT (Phase 6)

Source: `methods/forensic_model_audit.py` → `rawPPo/diagnostics/round_trip_trade_audit.csv`.
Answers "77% win rate but −42% return". Model `models/ppo_xauusd_raw.zip`, eval 2020→2026.

## Result
| | round trips | win rate | total PnL | worst trade |
|---|---|---|---|---|
| **all** | 554 | 72.0% | (drives −42% equity) | — |
| **long** | 311 | 73.6% | **+25.4%** | −5.75% |
| **short** | 243 | 70.0% | **−81.0%** | **−18.05%** |

- avg_win = **+0.447%**, avg_loss = **−1.510%** → losses are **3.4× bigger** than wins.
- **Top-5 worst trades are ALL shorts:** −18.0% (2025-08), −14.4% (2022-11), −13.7% (2024-02),
  −11.2% (2020-06), −11.0% (2025-12).

## Conclusion (evidence)
The high win rate and the large loss coexist because of **negative expectancy with fat-tailed
losses on the short side**. Longs were net **+25%** (gold rose), but shorts were net **−81%** —
a few catastrophic shorts into gold rallies (each −10% to −18%) overwhelm the many small short
scalp wins. So:
- −42.20% is **caused by the short book**, not by long trades, costs, or accounting.
- This is a **valid (bad) policy outcome**, not a code bug: PnL signs, costs, and accounting are
  all verified correct (SYNTHETIC_ACTION_PNL_AUDIT, prior). The agent simply shorted a bull market.
- "Why mostly short?" → the policy learned a high-hit-rate mean-reversion short that blows up on
  trends; see REGIME_SPLIT_DIAGNOSIS.md (both train and eval were bullish, so it is not a
  train-was-bearish artifact).
