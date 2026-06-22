# PPO RAW BASELINE — REPRODUCTION REPORT (Phase 3, canonical)

Reproduction of the **PPO *without* Kalman ("PPO Raw")** baseline from Kili et al. (IJACSA 16(11) 2025). Success criterion = **methodological fidelity to the paper**, not profit. No Kalman, no DQN, no RPPO.

**Phase 3 change:** per user decision (Option B), the paper pipeline now **overwrites the main repository modules** (`src/rl_gold_trading/*`) — there is a single canonical pipeline. The earlier parallel `paper_baseline/` subpackage was removed. Costs = **commission + spread only**; reported metrics use the **paper's 621-day window** (Jan 2 2023 → Sep 12 2024).

> Final numbers: `models/ppo_raw_metrics.json` and the end of `ppo_raw_train.log`.
> Source-of-truth & conformance: `../../researchPaper/PPO_RAW_GROUND_TRUTH.md`, `PPO_PAPER_CONFORMANCE_CHECKLIST.md`, `DATASET_CONFORMANCE_REPORT.md`, `CODEBASE_FORENSIC_AUDIT.md`, `PPO_BASELINE_GAP_ANALYSIS.md`.

---

## HOW TO RUN
```bash
cd Reinforcement-Learning-for-Gold-Trading
python train.py --smoke        # fast 5k-step sanity
python train.py                # full 500k-step reproduction (train + eval on 621-day window)
python train.py --mode eval    # evaluate a saved model
```
Outputs: `models/ppo_xauusd_raw.zip` + `models/ppo_raw_metrics.json`.

## CANONICAL PIPELINE (overwritten main modules)
| Module | Paper § (PDF p.) | Fidelity point |
|---|---|---|
| `config.py` | IV (p.5–9) | all values traced to paper, page-cited per field |
| `data.py` | IV.A (p.5–6) | XAU/USD 2017→2025, **daily** resample, forward-fill, **calendar split** (train ≤2022-12-31), **621-day eval window** |
| `features.py` | IV.B (p.6–7) | **22 features = 5 OHLCV + 17 indicators** via `ta`; raw `price` preserved for P&L |
| `normalize.py` | IV.B Eq.13 (p.6) | **252-day causal rolling z-score**, per-feature, no leakage |
| `envs.py` | IV.E/F (p.7–8) | **22-dim obs**, `Discrete(3)`→{−1,0,+1}, **100% capital**, **Eq.22 reward**, commission+spread |
| `vec_env.py` | IV.B | DummyVecEnv + Monitor, **no VecNormalize** (z-score already normalizes) |
| `train.py` (pkg) | IV.G.2/H (p.9) | SB3 PPO, **[512,512,256,128] Tanh**, LR 3e-4 **linear→0**, 500k |
| `metrics.py` | V (p.15) | cumulative return, CAGR, Sharpe(√252), MaxDD, win rate (+Sortino/Calmar/Recovery/VaR) |
| `run.py` | — | orchestrator; evaluates on the 621-day window; prints paper comparison |
| `train.py` (root) | — | CLI entry |

## EXACT SPECIFICATION CHECKLIST (verified against paper)
- **State dim = 22** — `ValueError` guard in env; obs `Box(22,)`. ✓ (PDF p.7)
- **Features:** SMA10/20/50, EMA12/26, MACD line+signal, RSI14, Stoch %K/%D, Bollinger upper/lower, ATR14, OBV, VWAP, CCI, Williams %R + OHLCV. ✓ (p.6; MACD = documented resolution of the 15→17 gap)
- **Normalization:** `z=(x−μ₂₅₂)/σ₂₅₂`, trailing window only. ✓ (p.6, Eq.13)
- **Frequency:** daily resample of hourly/15-min source. ✓ (p.6)
- **Split:** calendar — train 2017→2022, eval Jan 2 2023→Sep 12 2024 (621-day). ✓ (p.6, p.9)
- **Action:** `Discrete(3)` → sell(−1)/hold(0)/buy(+1). ✓ (p.7)
- **Sizing:** 100% capital, all-or-nothing. ✓ (p.7)
- **Reward (Eq.22):** `1.0·R_port − 2.0·DD − 0.5·Cost + 0.1·Stability`; DD running-max; Stability = −|Δposition|. ✓ (p.8)
- **Costs:** commission 0.01% + spread 0.005% per unit turnover. ✓ (p.7) — market impact/slippage omitted per user decision (paper leaves ADV/coeff unspecified).
- **PPO:** clip 0.2, GAE 0.95, c₁0.5, c₂0.01, lr 3e-4 linear→0, n_steps 2048, batch 256, 10 epochs, γ0.99, 500k. ✓ (p.9; arch printed & verified)
- **Library use:** SB3 PPO (no custom PPO), Gymnasium, PyTorch, `ta` indicators, pandas/numpy. ✓
- **No Kalman / DQN / RPPO.** ✓

## CRITICAL BUG FOUND & FIXED DURING PHASE 3
The z-score normalizes **all 22 features including `close`**. The env initially used the normalized `close` as its **price path**, producing impossible single-bar returns (≈1788%) and a −15981% drawdown. **Fix:** `features.py` preserves a raw `price` column; `envs.py` uses `price` (real units) for P&L while the normalized `close` remains in the 22-dim observation. Post-fix drawdowns are realistic. (See `CODEBASE_FORENSIC_AUDIT.md`.)

## PAPER TARGET (Table I/II, PPO Raw, PDF p.15)
| Metric | Paper |
|---|---|
| Cumulative return | 15.39% |
| CAGR | 6.00% |
| Sharpe | 0.69 |
| Max drawdown | −11.22% |
| Win rate | 50.16% |

## FINAL RESULTS (500k timesteps, seed 42, 621-day window = 530 daily bars, 2023-01-03 → 2024-09-12)
| Metric | Reproduced | Paper PPO Raw | Note |
|---|---|---|---|
| Cumulative return | **48.94%** | 15.39% | higher (long-biased in the gold uptrend) |
| CAGR | **20.85%** | 6.00% | higher |
| Sharpe | **2.04** | 0.69 | higher (low-vol policy) |
| Max drawdown | **−3.10%** | −11.22% | milder (undertrading) |
| Win rate (flat=loss) | **10.75%** | 50.16% | distorted by 82% flat |
| Win rate (in-market) | **59.38%** | — | diagnostic |
| Sortino / Calmar / Recovery | 2.32 / 6.74 / 15.81 | 1.08 / 0.53 / 1.36 | — |
| VaR(95%) | −0.26% | −0.90% | — |
| Position mix | flat 81.9%, long 17.0%, short 1.1% | — | **low-turnover** |
| Turnover | 69 (530 periods) | "450–680%" (paper) | paper raw *overtrades*; ours undertrades |

(`models/ppo_raw_metrics.json`.)

### Interpretation (honest)
The pipeline is now **maximally conformant to the paper's literal specification** (calendar split, 621-day window, daily frequency, 22-feature state, 252 z-score, Eq.22 with α/β/γ/δ=1/2/0.5/0.1, exact PPO arch/hparams, commission+spread). Yet the numbers **do not match** the paper's reported PPO Raw row, for a structural reason already identified in Phase-1 analysis and now **empirically reconfirmed**:

- Under the literal **Eq.22 reward (β=2α)**, the converged agent is **loss-averse and low-turnover** (82% flat, long-biased), giving small drawdown and an inflated Sharpe (2.04). It does *not* overtrade.
- The paper's **reported** PPO Raw, by contrast, **overtrades** (turnover 450–680%, drawdown −11.22%, win 50%). That behavior is **inconsistent with the paper's own stated β=2 reward**, which — as faithfully implemented here — suppresses trading rather than encouraging it.
- Therefore a *faithful* reproduction cannot simultaneously match (a) the paper's stated reward and (b) the paper's reported raw behavior — they contradict each other. We honored (a) the explicit specification; the divergence from (b) is a property of the paper, not an implementation error.

Per the directive, **trade frequency was treated as an output and never tuned**; β was not adjusted to force the agent toward the paper's turnover or its 15.39%/50.16% figures. This is a faithful reproduction of the paper's *method*; the gap to the paper's *reported numbers* is itself a finding (see `../../researchPaper/result_validation.md` and `failure_mode_analysis.md`, F4).

## FIDELITY CAVEATS (paper-side under-specifications, documented not fabricated)
1. Exact 2 of 17 indicators unspecified → MACD line+signal.
2. S_stability has no formula → −|Δposition|.
3. "return relative to benchmark" prose has no term in Eq.22 → omitted (faithful to the formula).
4. Sharpe annualization factor unstated → √252 (daily convention).
5. Market-impact ADV / slippage coefficients unstated → those cost terms omitted (per user decision; commission+spread retained).
6. Data vendor unnamed → repo's HF XAU/USD source (daily-resampled).
Single seed (42), mirroring the paper's apparent single-run tables. The reproduction inherits the paper's own documented reward pathology by design (faithful reproduction, not correction).
