# ROOT CAUSE ANALYSIS — why reproduced ≠ paper

> ⚠️ **PARTIALLY SUPERSEDED (Phase 6).** This Phase-5 analysis treated the Nautilus −1.27% as "honest realistic execution exposing an optimistic env." That was **wrong**: the −1.27% was a Nautilus-harness fill-timing bug (fills at stale `close[t-1]`), now fixed → Nautilus = **+48.67%**, converging with the env. See `ROOT_CAUSE_REPORT.md`. The env-vs-*paper* discussion (paper's raw row is internally inconsistent; no implementation mismatch) still stands.

**Question (critical investigation):** why does the reproduced env report **+48.94% return / Sharpe 2.04 / −3.10% DD** vs the paper's PPO Raw **+15.39% / 0.69 / −11.22%**? Every candidate cause is evaluated with evidence and ruled IN or OUT. No speculation.

## CANDIDATE CAUSES — RANKED, WITH EVIDENCE
| Rank | Candidate | Verdict | Evidence |
|---|---|---|---|
| **1** | **Evaluation convention — optimistic same-bar fills (env)** | **PRIMARY CAUSE** | Phase-4 attribution (`forensics/attribution.py`, `NAUTILUS_VS_ENV_REPORT.md`): same policy, env fills at `close[t]` → +48.95%; 1-bar-lag fill at `close[t+1]` → **−8.76%**; event-driven Nautilus → **−1.27%**. The +48.94% is an artifact of crediting the position the `close[t]→close[t+1]` move it decided on but cannot trade at. |
| **2** | **Paper's raw baseline is internally inconsistent** | CONTRIBUTING | Paper reports raw PPO *overtrading* (turnover 450–680%, DD −11%) — inconsistent with its own β=2 reward, which suppresses trading (`../../researchPaper/result_validation.md` F4, `failure_mode_analysis.md`). The paper's 15.39% is therefore not a clean, reproducible target. |
| 3 | Transaction-cost model omits impact/slippage | MINOR | `REWARD_FORENSICS.md`: commission+spread only (per Phase-3 decision). Inflates returns slightly, but turnover is low (69 units) → effect is a few bp, not 33 pp. |
| 4 | Data vendor / source granularity differs | MINOR | `DATA_REPLICATION_FORENSICS.md`: paper's hourly vendor undisclosed; we use a public 15-min feed resampled to daily. Changes the exact prices, not the methodology. |
| — | Train/test split mismatch | **RULED OUT** | Calendar split matches paper; train max 2022-12-30 < eval min 2023-01-03 (disjoint, measured). |
| — | **Look-ahead / normalization leakage** | **RULED OUT** | `NORMALIZATION_FORENSICS.md`: full-series vs truncated-at-date z-score **max abs diff 0.0** → strictly causal. |
| — | Reward mismatch | **RULED OUT** | `REWARD_FORENSICS.md`: Eq.22 exact, weights 1/2/0.5/0.1. |
| — | Feature mismatch | **RULED OUT** | `FEATURE_REPLICATION_FORENSICS.md`: 22 features, formulas from `ta`, only MACD slots documented. |
| — | Architecture/hyperparameter mismatch | **RULED OUT** | `PPO_ARCHITECTURE_FORENSICS.md`: every stated value matches, confirmed against weights. |
| — | Incorrect action execution / sizing / trade accounting | **RULED OUT** | Phase-4 forensics: action stream identical in Nautilus; trade counts reconcile; sizing = 100% capital. |
| — | Evaluation observation mismatch | **RULED OUT** | `OBSERVATION_PARITY_REPORT.md`: env vs Nautilus obs max abs diff 0.0. |

## THE DECISIVE REFRAME
The premise "reproduced **outperforms** the paper" is **false in any tradable sense.** The env's +48.94% is an evaluation idealization. Under independent event-driven execution (Nautilus), the same frozen policy returns **−1.27%** — i.e., it is a **weak, roughly break-even-to-losing** baseline, *consistent with (or worse than)* the paper's own weak raw PPO. There is no genuine outperformance to explain away; there is an **evaluation-convention gap** that both this work and (almost certainly) the paper share, and which Nautilus exposes.

## IS THE EVALUATION CONVENTION A "MISMATCH VS PAPER"?
No. Close-to-close fills (decide on close[t], earn close[t]→close[t+1]) is the **standard convention these RL-trading papers use**, and nothing in the paper indicates otherwise. Our env matches the paper's *likely* evaluation. It is a shared idealization, not a deviation from the paper. The honest correction is **not** to change the env (that would diverge from the paper) but to **report the Nautilus number as the realistic one** — which we do.

## RETRAINING DECISION (gate)
The retraining gate requires a **verified implementation mismatch vs the paper**. After exhaustive forensics across data, features, normalization, reward, architecture, hyperparameters, evaluation, execution, and observations: **no such mismatch exists.** Every difference is either (a) a paper-side under-specification locked by a documented assumption, or (b) the shared optimistic-fill convention, or (c) the paper's own internal inconsistency.

**Decision: RETRAINING IS NOT JUSTIFIED.** Per the protocol, retraining is prohibited when no mismatch is found. The policy remains frozen.

## RECOMMENDED REPORTING POSTURE
- Report the env metrics as **idealized (optimistic-fill)** results.
- Report the **Nautilus metrics (−1.27%)** as the realistic, executable result.
- State plainly that the policy has **no robust executable edge** on daily XAU/USD, consistent with the paper's weak raw baseline once execution is honest.
