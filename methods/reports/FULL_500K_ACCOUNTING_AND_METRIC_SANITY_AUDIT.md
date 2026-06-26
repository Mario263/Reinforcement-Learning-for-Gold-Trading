# FULL 500K ACCOUNTING AND METRIC SANITY AUDIT (Phase 9)

| check | RawPPO 500k | NautilusPPO 500k (fixed) |
|---|---|---|
| NaN equity | none | none |
| infinite equity | none | none |
| negative/invalid equity | none (>0) | none (>0) |
| impossible leverage | n/a (return-based) | ≤0.95, none >1 |
| position changes w/o action | none | none (orders only on direction change) |
| fees without trades | none | none |
| trades without position change | none | none |
| profit_factor vs gross P/L | consistent (0.62 ⇒ losing) | consistent (1.28 ⇒ winning) |
| win_rate vs trades | consistent | consistent (post MtM fix) |
| final_equity vs cum_return | 0.850 = 1−0.1496 ✓ | $10.70M = 10M×1.0697 ✓ |
| max_drawdown from equity curve | yes | yes |
| CAGR period basis | n/9896 over the eval span | same |
| Sharpe/Sortino use PERIODS_PER_YEAR | **6048** | **6048** |
| z-score uses ZSCORE_WINDOW | **528** | **528** |

## Explicit isolation proof
- **528 was NOT used for metric annualization** — `compute_metrics` annualizes with `√6048` /
  `years=n/6048`; 528 appears only in `rolling_zscore`.
- **6048 was NOT used for z-score** — `rolling_zscore(window=528)`; 6048 appears only in metrics.
- (Single definitions in `shared/config.py`; DEDUPLICATION_VERIFICATION_REPORT.)

## Impossible combinations
None found. (No "profit_factor>1 with catastrophic equity"; no "high win-rate with impossible PnL";
every equity change traces to position×price move + cost.)

**Verdict: PASS** — both frameworks' accounting and metrics are internally consistent and finite.
