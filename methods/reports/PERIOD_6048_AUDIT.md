# PERIOD 6048 AUDIT (Phase 3)

What `6048` means in the code, from `grep -n 6048`. No guessing.

## Every occurrence
| File | Line | Usage |
|---|---|---|
| `src/rl_gold_trading/config.py` | 93 | **comment only** ("NOT a 1-year (6048-bar) paper-equivalent horizon") |
| `src/rl_gold_trading/metrics.py` | 9 | comment (annualization explanation) |
| `src/rl_gold_trading/metrics.py` | 20 | `def evaluate_model(..., periods_per_year: int = 6048)` — **the annualization factor** |
| `NautilusPPO/src/config.py` | — | `PERIODS_PER_YEAR = 6048` (same meaning) |
| `NautilusPPO/src/metrics.py` | — | uses `PERIODS_PER_YEAR` for annualization |

## Conclusion (evidence)
**`6048` is solely the metric annualization factor** = 252 trading days × 24 hours = hours per
trading year. It is used **only** to annualize Sharpe / Sortino / CAGR / volatility from hourly
returns (`× √6048`, `years = n/6048`).

It is **NOT**: episode length, training period, rolling sample window, backtest segment length,
or a walk-forward period (the prompt's candidate meanings — none apply; grep shows no such use).

**Consistency:** identical meaning and value in RawPPO (`metrics.py`) and NautilusPPO
(`config.PERIODS_PER_YEAR`, `metrics.py`). It is distinct from `ZSCORE_WINDOW = 528` (the
normalization lookback in bars) — the two are never conflated. See
METRIC_ANNUALIZATION_DECISION_REPORT (NautilusPPO) and NORMALIZATION_DECISION_MEMO (RawPPO).
