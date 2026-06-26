# METRIC ANNUALIZATION REPORT (Phase 9)

`PERIODS_PER_YEAR = 6048` (`methods/shared/config.py`, single definition). Metrics:
`methods.shared.diagnostics.compute_metrics` (single source, used by both frameworks).

## Proof 6048 is correct and isolated
- 1 bar = 1H; no daily resample (`data_loader` resamples to `1h`, Mon-Fri).
- 252 trading days × 24 hourly bars = **6048** hourly observations/year.
- `compute_metrics` annualizes with `√6048` (Sharpe/Sortino/vol) and `years = n/6048` (CAGR).
- 6048 is used **only** for annualized metrics; **528** is used **only** for the z-score window.
  They are never conflated (grep: each defined once, distinct).
- `PERIODS_PER_YEAR` is **not** 528 and **not** 60.

## Metrics (parity-suite window, 409 bars, same model — illustrative)
| metric | input freq | annualized? | RawPPO | NautilusPPO |
|---|---|---|---|---|
| cumulative_return | hourly | no | +3.13% | +2.37% |
| sharpe | hourly | √6048 | 2.99 | 5.59 |
| max_drawdown | hourly | no | (in CSV) | (in CSV) |
| (full set: CAGR, sortino, calmar, recovery, volatility, var95, win rates, profit_factor, turnover, exposure, fractions, final_equity) | hourly | per formula | `pnl_reconciliation.csv` | `pnl_reconciliation.csv` |

Both frameworks feed their OWN equity/positions (RawPPO ledger / Nautilus state) into the SAME
formula with 6048 → differences are execution-driven (documented), not annualization-driven.
Nautilus metrics are derived from Nautilus state (not RawPPO ledger).

**Verdict: PASS** — 6048 hourly annualization, isolated from the 528 z-score window, single source.
