# FEATURE REPLICATION FORENSICS (Agent 3)

Per-feature verification of the 22-dimensional state (no more, no less). Source: `features.add_features` (via the `ta` library) + `normalize.rolling_zscore`. Paper §IV.B (PDF p.6–7).

State dim measured at runtime: **22** (`len(FEATURE_ORDER)==22`, asserted; obs `Box(22,)`).

## FEATURE TABLE
| # | Feature | Source (`features.py`) | Library call | Lookback | Paper p.6 |
|---|---|---|---|---|---|
| 1–5 | open, high, low, close, volume | raw OHLCV | — | — | implied (5 OHLCV) |
| 6 | sma10 | `SMAIndicator(c,10)` | ta.trend | 10 | ✅ |
| 7 | sma20 | `SMAIndicator(c,20)` | ta.trend | 20 | ✅ |
| 8 | sma50 | `SMAIndicator(c,50)` | ta.trend | 50 | ✅ |
| 9 | ema12 | `EMAIndicator(c,12)` | ta.trend | 12 | ✅ |
| 10 | ema26 | `EMAIndicator(c,26)` | ta.trend | 26 | ✅ |
| 11 | macd_line | `MACD(c,26,12,9).macd()` | ta.trend | 12/26 | ◐ (the 2 unspecified — documented) |
| 12 | macd_signal | `MACD(...).macd_signal()` | ta.trend | 9 | ◐ |
| 13 | rsi14 | `RSIIndicator(c,14)` | ta.momentum | 14 | ✅ |
| 14 | stoch_k | `StochasticOscillator(...,14,3).stoch()` | ta.momentum | 14 | ✅ |
| 15 | stoch_d | `...stoch_signal()` | ta.momentum | 14/3 | ✅ |
| 16 | boll_upper | `BollingerBands(c,20,2).bollinger_hband()` | ta.volatility | 20, 2σ | ✅ |
| 17 | boll_lower | `...bollinger_lband()` | ta.volatility | 20, 2σ | ✅ |
| 18 | atr14 | `AverageTrueRange(...,14)` | ta.volatility | 14 | ✅ |
| 19 | obv | `OnBalanceVolumeIndicator(c,v)` | ta.volume | — | ✅ |
| 20 | vwap | `VolumeWeightedAveragePrice(...,14)` | ta.volume | 14 | ✅ (window not specified in paper) |
| 21 | cci | `CCIIndicator(...,20)` | ta.trend | 20 | ✅ (20 standard) |
| 22 | williams_r | `WilliamsRIndicator(...,14)` | ta.momentum | 14 | ✅ |

## PER-FEATURE PROPERTIES
- **Formula:** delegated to the mature `ta` library (no hand-rolled indicators) → standard definitions, matching the paper's "standard mathematical formulations" (p.6).
- **Lookback:** as tabulated; all ≤ 50, consumed in warmup before the split.
- **Normalization:** every feature 252-day rolling z-score (see `NORMALIZATION_FORENSICS.md`).
- **Timestamp alignment:** indicators computed on the daily index; `price` (raw close) preserved separately for the env P&L path (`features.add_features` adds `out["price"]`).
- **NaN handling:** `dropna(subset=FEATURE_ORDER)` after indicators, and again after z-score; warmup rows removed. Runtime check: **0 NaN / 0 inf** in the eval feature matrix.

## COUNT RECONCILIATION (the only ambiguity)
Paper §IV.B says "22 indicators" but §IV.E says state = 5 OHLCV + **17** indicators (PDF p.6 vs p.7). The §IV.B enumeration yields **15** distinct indicators. The 17-reading is the internally-consistent one; the 2 unspecified indicators are taken as **MACD line + signal** (MACD referenced on p.2). This is the single documented assumption; it does not change the state dimension (22) or introduce any non-paper feature.

## VERDICT
The 22-feature state matches the paper exactly except for the 2 paper-unspecified indicator slots (resolved to MACD, documented). All formulas come from a standard library. No extra or missing features. **No feature mismatch that constitutes a defect.**
