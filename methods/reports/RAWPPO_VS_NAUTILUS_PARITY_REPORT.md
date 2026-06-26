# RawPPO vs NautilusPPO PARITY REPORT

Lean parity harness (your "lean targeted" choice) — reuses existing code, no restructure.
All numbers executed. Tools under `methods/`; ledgers under `methods/outputs/`.

## 1. Synthetic action/PnL/cost tests — `methods/synthetic_action_pnl_test.py`
**5/5 PASS.** On crafted series:
- up series: long net_ret > 0, short net_ret < 0 (PnL sign correct).
- down series: short > 0, long < 0.
- flat→flat: 0 PnL and 0 cost.
- repeated long: cost on `flat→long` only, **0 cost on `long→long`** (not charged while holding).
- flip `long→short`: cost = 2× single-unit, ends **short** (not flat, not accumulated).
→ RawPPO env accounting is correct. Ledger: `methods/outputs/synthetic_action_pnl.csv`.

## 2. Reward-component diagnostic (collapse) — `methods/reward_component_diagnostic.py`
Real NautilusPPO env, window 2023-04-03→2023-04-28 (408 bars), all-long vs all-flat:
| policy | gross | drawdown(−β·dd) | cost | stability | TOTAL |
|---|---|---|---|---|---|
| all-flat | +0.0000 | −0.0000 | −0.0000 | +0.0000 | **+0.0000** |
| all-long | −0.0000 | **−0.1292** | −0.0001 | −0.1000 | **−0.2293** |
**FLAT ≥ LONG** → reward favors doing nothing → collapse explained. The per-bar drawdown penalty
(charged every bar below peak) is the dominant term. Inherited reward design; **not changed**
(diagnose-only). Ledger: `methods/outputs/reward_component_audit.csv`.

## 3. RawPPO env vs Nautilus on the SAME model — `methods/parity_harness.py`
Model `models/ppo_xauusd_raw.zip`, window 2023-04-03→2023-04-28, 407 aligned bars:
| metric | value | target | verdict |
|---|---|---|---|
| observation max_abs_diff | 0.0 (proven) | ≤1e-6 | PASS |
| **action_match_rate** | **1.0000** | 1.0 | PASS |
| **position_match_rate** | **1.0000** | 1.0 | PASS |
| equity-return max\|diff\| | 0.0427 | explained | execution timing + integer-oz |

Identical observations → identical deterministic actions and target positions. The ~4.3% return-
path divergence is **execution mechanics**: Nautilus fills on the **next bar** (vs RawPPO instant
close-fill) and rounds to **integer ounces**; with a frequently-flipping policy the 1-bar lag
accumulates. This is the documented, intentional Nautilus deviation — not a feature/normalization/
action mismatch. Ledgers: `methods/outputs/{rawppo_ledger.csv, nautilus_ledger.csv}`.

## Verdict
- Feature / normalization / observation / action / position parity: **EXACT (1.0)**.
- Cost & PnL logic: **correct** (synthetic 5/5).
- Equity divergence: **bounded and explained** (next-bar fill + integer-oz). To tighten it, configure
  Nautilus same-bar fill or fractional sizing — a separate change, not required for correctness.
- NautilusPPO all-flat collapse: **explained** (per-bar drawdown penalty floor); reward left as the
  faithful RawPPO port per your instruction.
