# PER-FILL ACCOUNTING AUDIT (PRE-500K, Phase 2)

Shortest practical audit on existing artifacts (`methods/outputs/trades/trade_lifecycle_audit.csv`
= 408-bar ledger; `position_sizing_audit.csv`). Executed checks:

| check | result |
|---|---|
| NaN equity | none |
| NaN reward / fees | none |
| cost charged WITHOUT a position change | **0** (cost only on changes) |
| position changes vs cost-rows | 11 changes ↔ 12 cost-rows (incl. bar-0 entry) — consistent |
| impossible leverage | none — max **0.95**, none > 1.001 |
| negative/invalid equity | none |
| duplicate/zero-qty issues | none observed at equity level |

**Result: PASS (equity/position level).** No correctness bug → proceeding to 500k (the gate already
deemed per-fill non-blocking).

## Documented limitation (unchanged)
True per-**fill** rows (order_id/fill_id/commission/cash-before-after) require a dedicated Nautilus
backtest reading `engine.cache` after `run()` — the training env disposes the engine per episode.
This is a recommended follow-up; it does not affect training correctness (fills/positions/cash are
Nautilus-owned during the run; the equity-level reconciliation above is consistent).
