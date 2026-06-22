# CHANGE JUSTIFICATION LOG (Phase 5)

Policy: modify only components that **demonstrably differ from the paper**; every change needs file, line, rationale, paper citation, expected impact.

## PHASE-5 CHANGES TO THE TRAINED PIPELINE: **NONE**

The Phase-5 forensics (Agents 1–6 + normalization + observation parity + root cause) found **no verified implementation mismatch vs the paper**. Per the retraining decision gate, **no code in `src/rl_gold_trading/` was modified and no retraining was performed.** The policy weights (`models/ppo_xauusd_raw.zip`) remain frozen.

| Component | Audited against | Result | Change? |
|---|---|---|---|
| Dataset/splits | paper §IV.A | match (vendor undisclosed) | none |
| 22 features | paper §IV.B | match (MACD documented) | none |
| 252 z-score | paper §IV.B, Eq.13 | match, causal (diff 0) | none |
| Reward Eq.22 | paper §IV.F | match | none |
| PPO arch/hparams | paper §IV.G.2/H | match (verified vs weights) | none |
| Metrics | paper §V | standard, reconcile | none |
| Observations (Nautilus) | eval pipeline | identical (diff 0) | none |

## NON-PIPELINE ARTIFACTS ADDED THIS PHASE (analysis only — do not affect training/weights)
| File | Purpose |
|---|---|
| `RESEARCH_VERIFICATION_REPORT.md` … `ROOT_CAUSE_ANALYSIS.md` (10 reports) | Phase-5 forensic deliverables |
| (re-ran) `forensics/run_forensics.py`, `forensics/attribution.py` | evidence regeneration (inference only) |
| `NAUTILUS_VALIDATION_REPORT.md`, `ENVIRONMENT_NAUTILUS_PARITY_REPORT.md` | robustness validation (frozen policy) |

## EXPECTED IMPACT
Zero impact on model behavior or metrics (no pipeline/weight changes). The deliverables are documentation/validation only.

## POST-PHASE-5 CHANGE (user-requested, reporting-only) — win-rate denominator
**Trigger:** user observed "Win rate 10.57%" and asked to investigate. Root cause (`ROOT_CAUSE_ANALYSIS` / `WIN_RATE_FORENSIC_REPORT`): the reported `win_rate` uses **all 530 periods** as denominator, but the policy is flat ~83% of the time (flat days have 0 return → counted non-wins). The paper's 50.16% is a **per-trade / in-market** figure (its raw agent is ~always in-market), so the comparison was apples-to-oranges. **This is not a bug, training error, or leakage** — confirmed on the current model: 56 wins; all-period 56/530=10.57%, in-market 56/91=61.54%, per-trade 29/37=78.38%.

| File | Line | Change | Rationale | Paper cite | Impact |
|---|---|---|---|---|---|
| `metrics.py` | win-rate block | add `trade_win_rate` (round-trip equity-based) + `round_trips` | standard trading win rate; paper-comparable | Table II "Win Rate" 50.16% (p.15) | reporting only; no weight/behavior change |
| `run.py` | report rows | compare **per-trade** win rate to paper; print all 3 definitions labeled | apples-to-apples vs paper | p.15 | reporting only |

**Not a policy/reward/feature/hyperparameter/dataset/normalization change.** Weights unaffected (eval re-reads the same model). Per-trade win rate **78.38% > paper 50.16%**.

**CUDA:** `src/rl_gold_trading/train.py:42` `device="cuda"` (user edit) — verified `torch.cuda.is_available()==True` (RTX 5080 Laptop GPU); training log shows "Using cuda device", ~1700 fps. No correctness impact (GPU vs CPU only affects RNG/throughput, not methodology).

## PHASE-6 CHANGE (Nautilus harness fixes — execution correctness)
Root-cause investigation of the env(+48.94%) vs Nautilus(−1.27%) gap found **two Nautilus-harness bugs** (NOT model/feature/reward/normalization — all proven identical). Fixes are to the **backtest harness only**; the trained policy and the `src/rl_gold_trading` pipeline are untouched (Rules 1–3 honored).

| File · function | Old behavior | New behavior | Justification (evidence) | Impact |
|---|---|---|---|---|
| `nautilus/run_backtest.py` · `build_data` | fill quote at `ts_ns+1` (after bar) → market order fills at stale `close[t-1]` | fill quote at `ts_ns-1` (before bar) → fills at `close[t]` | `forensics/fill_offset.py` offset {−1:85}; env assumes `close[t]` fill | Nautilus −1.27% → ~+48% |
| `nautilus/run_backtest.py` · `main` | equity = cash-only `balance_total()` | net-liquidation `cash + pos·price` from fills | `forensics/reconstruct.py` (cash-only excludes unrealized PnL, ≈2 pp) | correct equity curve / Sharpe / DD |
| `nautilus/strategy.py` | (instrumentation) added `fills_log`, `action_log` decision close | same + logging | enables row-by-row parity (`forensics/parity.py`) | none (diagnostics) |

**Result:** env +48.94% vs Nautilus **+48.67%** (Δ 0.27 pp) — converged. See `ROOT_CAUSE_REPORT.md`, `EXECUTION_PARITY_REPORT.md`, `REPLICATION_CORRECTION_REPORT.md`. No retraining.

## PHASE-7 CHANGE (Nautilus position-sizing / accounting fix — −$1.9M blow-up)
A retrained model (env +63.78%) produced a catastrophic Nautilus result (−72%, final equity **−$1.9M**). Root cause (`POSITION_SIZING_ROOT_CAUSE.md`, `forensics/outputs/trade_lifecycle_audit.csv`): position sizing used **account cash** (`balance_total`), which is **inflated by short-sale proceeds** (cash $204k vs equity $102k on shorts); under leverage 50 this **compounds consecutive shorts** to a leveraged blow-up. NOT a PPO/feature/reward/normalization issue.

| File · method | Old | New | Impact |
|---|---|---|---|
| `nautilus/strategy.py` · `_net_liq`/`on_bar`/`on_order_filled` | size on `balance_total()` (cash) | size on **net-liquidation** (`cash + pos·price`, self-tracked) | shorts can't compound |
| `nautilus/run_backtest.py` + forensics · venue | `default_leverage=50` | `default_leverage=2` | hard safety bound |

**Result:** Nautilus −72%/−$1.9M → **+63.15%/$163,125**; max leverage 1.00×; equity never < 0; converges with env +63.78% (Δ 0.63 pp). See `FINAL_DISCREPANCY_RESOLUTION_REPORT.md`. Harness-only; trained policy untouched.

## IF A MISMATCH HAD BEEN FOUND (procedure, unused)
Each correction would be logged here as: `file:line — old → new — rationale — paper page — expected metric impact`, followed by `python train.py` (retrain) and `python nautilus/run_backtest.py` (revalidate). **Not triggered**, because no mismatch was found.
