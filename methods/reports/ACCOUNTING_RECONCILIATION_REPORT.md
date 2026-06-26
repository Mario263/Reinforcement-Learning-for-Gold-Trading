# ACCOUNTING RECONCILIATION REPORT (Phase 8)

CSVs: `methods/outputs/trades/trade_lifecycle_audit.csv`, `pnl_reconciliation.csv`. Window 409 bars.

## Source of truth
NautilusPPO equity/positions are derived from the **Nautilus** `BacktestEngine` (cash via
`account.balance_total`, unrealized via `portfolio.unrealized_pnl`, net position via
`portfolio.net_position`). The RawPPO 0.015% cost is overlaid on Nautilus fill notional.

## Equity-curve reconciliation (executed)
- Per-bar `equity`, `position`, `cost`, `net_ret` exported (`trade_lifecycle_audit.csv`).
- Metrics recomputed from the equity/positions series (`pnl_reconciliation.csv`) for both
  frameworks — internally consistent (no equity change without a position+price move; positions
  change only via actions; leverage ≤1 always; no NaN/inf).
- Impossible combinations checked: none (no "high profit factor + catastrophic equity"; win-rate,
  drawdown, final-equity mutually consistent).

## Consistency checks
| check | result |
|---|---|
| equity changes explained by position×price move + cost | ✓ |
| positions change only via actions/orders | ✓ |
| leverage ≤ 1 every bar | ✓ (max 0.950) |
| NaN/inf in equity | none |
| metrics vs equity curve | consistent |

## Limitation (honest)
Per-**fill** detail (individual order_id/fill_id/commission/cash-before-after rows) is **not**
exported here: the training env tracks Nautilus equity/position/traded-notional per bar but does
not surface the engine's per-fill cache (it disposes the engine each episode). Full per-fill
reconciliation needs a dedicated Nautilus backtest pass that reads `engine.cache.fill_reports()` /
`positions()` after `run()`. Recommended as a follow-up if fill-level audit is required; the
equity-curve-level reconciliation above is consistent.

**Verdict: PASS (equity-curve level); per-fill audit = documented follow-up.**
