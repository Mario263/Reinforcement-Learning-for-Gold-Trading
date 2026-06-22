# POSITION SIZING / ACCOUNTING ROOT CAUSE (−$1.9M blow-up)

Covers directive Phases 1–4 & 7. Every claim is backed by `forensics/outputs/trade_lifecycle_audit.csv` and `forensics/trade_lifecycle.py`.

## SYMPTOM
Nautilus reported **−72.09% return, −99.6% drawdown, final equity −$1,936,255** while showing **78% win rate, PF 6.17, 37 round trips**. Negative equity + high win-rate/PF is impossible unless **sizing or accounting** is wrong.

## PHASE 2 — POSITION SIZING AUDIT (the defect)
**File:** `nautilus/strategy.py` · method `on_bar` / (old) `_account_equity`.
- Sizing rule: `units = int(equity // price)`, where `equity` was `account.balance_total()` — i.e. **cash**.
- **Cash is inflated by short-sale proceeds.** Lifecycle evidence (short entry):
  ```
  2023-02-01  SELL  pos 0→-52   cash $204,137   net_liq $102,734   leverage 0.987
  ```
  True equity is $102,734 but **cash is $204,137** (≈2×) because shorting credits proceeds.
- **Consequence:** if the model issues consecutive SHORT decisions while already short, `units = floor(204137/price)` ≈ 2× the correct size → the short **compounds each bar** (−52 → −104 → −157 …). Under the venue's leverage 50 the engine permits it. One adverse move on the oversized short drives net-liquidation **negative** → −$1.9M.

## PHASE 3 — CONTRACT SPECIFICATION AUDIT (ruled OUT)
**File:** `nautilus/run_backtest.py` · `build_instrument`.
- `CurrencyPair` XAU/USD, `size_precision=0`, `size_increment=1`, **no multiplier** (CurrencyPair has none).
- ⇒ **quantity = 1 represents 1 ounce of gold.** A $1 price move on 1 unit = **$1 PnL**. 54 units ≈ $99k notional at ~$1840.
- **No hidden 100× / contract-multiplier inflation.** Contract spec is correct — NOT the cause.

## PHASE 4 — PORTFOLIO ACCOUNTING AUDIT
- The *metrics* equity curve in `run_backtest.py` already uses **net-liquidation** (`cash + pos·price`), which is correct.
- The defect was purely that the **strategy's sizing input** used cash, not net-liq. Reconstructed accounting (`forensics/reconstruct.py`, `trade_lifecycle.py`) shows net-liq is stable (~$100k) at every short; cash is not.

## PHASE 7 — ROOT CAUSE PRIORITIZATION
| Rank | Cause | Probability | Evidence | File · method |
|---|---|---|---|---|
| 1 | **Sizing to cash (short-proceeds inflation) → short compounding** | **Proven** | lifecycle: cash $204k vs equity $102k on shorts; offset compounding | `strategy.py:on_bar/_account_equity` |
| 2 | Leverage 50 permits the oversized position | Contributing | venue `default_leverage=50` | `run_backtest.py:add_venue` |
| — | Contract multiplier / lot size | Ruled out | 1 unit = 1 oz, no multiplier | `build_instrument` |
| — | Observation / action / feature / reward | Ruled out (prior phases) | obs diff 0, actions 0/530 | — |

## THE FIX
1. **Size to NET-LIQUIDATION equity** (`cash + position·price`, self-tracked) instead of cash — stable for long/short/flat, so shorts cannot compound. (`strategy.py:_net_liq`, used in `on_bar`.)
2. **Leverage 50 → 2** (hard safety bound). (`run_backtest.py` + diagnostics.)

## VERIFICATION (post-fix, `trade_lifecycle.py`)
```
max |position|: 66 units   max leverage: 1.00x
min net-liq equity: $99,631   bars with equity<0: 0   leverage breaches: 0
final net-liq equity: $163,125
```
Leverage is bounded to **1.00×**; equity never goes negative. The blow-up is now **structurally impossible** — even a short-heavy model sizes each short to net-liq (`floor(equity/price)`), so `delta = target − cur = 0` on consecutive shorts (no compounding).
