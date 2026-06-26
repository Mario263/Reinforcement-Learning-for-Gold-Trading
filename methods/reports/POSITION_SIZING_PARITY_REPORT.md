# POSITION SIZING PARITY REPORT (Phase 7)

CSV: `methods/outputs/trades/position_sizing_audit.csv`. High-risk area — verified.

## Instrument (Nautilus `default_fx_ccy("XAU/USD")`, inspected)
| property | value |
|---|---|
| quantity unit | **ounces of gold** |
| **quantity = 1 means** | **1 oz**; notional = `1 × price`; multiplier = 1 (no 100× contract) |
| price precision / size precision | 5 / 0 (integer oz) |
| min quantity | 1000 oz |
| 1-pt PnL on qty=1 | $1 (10-pt → $10, 100-pt → $100) |

## Sizing (both frameworks, target {-1,0,+1})
| param | RawPPO | NautilusPPO |
|---|---|---|
| starting capital | 1.0 (normalized, return-based) | $10,000,000 |
| target allocation | 100% directional | `deploy_frac=0.95` → `int(0.95·equity/price)` oz |
| leverage | none (return = dir × price_ret) | notional ≈ 0.95·equity |

## Measured (409-bar run)
| metric | value |
|---|---|
| **effective_leverage max** | **0.950** (= deploy_frac) |
| over-leverage detected | **no** (≤1 every bar) |
| multiplier mismatch | none (multiplier 1) |
| notional | ≈ 0.95 × equity on directional bars |

Nautilus exposure (≈95% of equity, no leverage) matches RawPPO's intended ≈100% directional
exposure, minus the deliberate 5% headroom + integer-oz rounding (negligible on $10M).

**Verdict: PASS** — no unintended leverage, quantity semantics understood (oz, mult 1), exposure
matches intent.
