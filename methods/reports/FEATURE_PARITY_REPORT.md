# FEATURE PARITY REPORT (Phase 2)

Command: `python -m methods.parity_suite --model models/ppo_xauusd_raw.zip`
Window 2023-04-03..2023-04-28, 409 bars. CSV: `methods/outputs/parity/feature_parity.csv`.

## Architecture proof
Both frameworks import `methods.shared.features.add_features` (the **single** definition — dedup
scan confirms it exists only there). RawPPO and NautilusPPO do not compute features themselves;
they consume the shared output. Therefore feature values are **identical by construction**.

| check | result |
|---|---|
| feature count | **22** |
| feature order | unchanged (`shared.config.FEATURE_ORDER`): open, high, low, close, volume, sma10/20/50, ema12/26, macd_line, macd_signal, rsi14, stoch_k, stoch_d, boll_upper, boll_lower, atr14, obv, vwap, cci, williams_r |
| RawPPO == shared | yes (same function) — **max_abs_diff 0.0** |
| NautilusPPO == shared | yes (same function) — **max_abs_diff 0.0** |
| Kalman features | none |
| daily resampling | none (1H, Mon-Fri) |
| volume | Dukascopy **tick volume** (OBV/VWAP tick-based; documented, not real volume) |

**Verdict: PASS.** 22 features, fixed order, single shared source ⇒ exact across frameworks.
