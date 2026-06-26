# FULL 500K FIX LOG (Phase 10)

## Bug found (correctness) — Nautilus per-bar equity not marked-to-market
**Symptom:** same-policy diagnostic (RawPPO 500k model through both envs, 5,805 bars) gave
identical actions/positions (match 1.0) but win-rate 28.4% (RawPPO env) vs **0.29%** (Nautilus env).
**Root cause:** `nautilus_strategy.BridgeStrategy._equity()` used
`portfolio.unrealized_pnl(instrument_id)`, which with a **bars-only** feed is not updated per bar —
so an open position's value was effectively constant between trades. Measured: **in-market
`net_ret == 0` on 99.2% of bars** (open position not re-valued each bar). This degraded both:
  (a) per-bar Nautilus metrics (Sharpe / win-rate / Sortino were artifacts), and
  (b) the **training reward signal** (gross_return ≈ 0 most bars) → the NautilusPPO 500k model was
  trained on a degenerate reward.

## Smallest fix
`methods/nautilus/src/nautilus_strategy.py` `_equity(price)`: mark-to-market the open position at
the **current bar price** —
`cash + Σ position.unrealized_pnl(instrument.make_price(bar.close))`. (Also stored `self.instrument`;
`on_bar` now passes `bar.close`.) No change to features, z-score, reward coefficients, PPO hparams,
action mapping, or position sizing.

## Verification (RawPPO 500k model through the FIXED Nautilus env, 2023-Q2 window)
| metric | before fix | after fix |
|---|---|---|
| in-market `net_ret == 0` frac | 0.992 | **0.017** |
| in-market `net_ret > 0` frac | 0.001 | **0.482** (≈0.5, symmetric like RawPPO) |
| win_rate_all | ~0.3% | **21.0%** |
| sharpe | degenerate | 0.85 |

## Rerun
NautilusPPO 500k **re-trained** with the fix (the buggy model + its eval are superseded). RawPPO 500k
is **unaffected** (its own return-based MtM accounting). Re-eval + re-comparison + re-same-policy run
after the corrected training completes.
