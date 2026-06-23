> ⚠️ **DAILY-ERA — SUPERSEDED.** This report describes the original **daily** pipeline. The build now runs **hourly + 5-day-week** (user-directed). Performance numbers below are daily-era and STALE pending a retrain. See [HOURLY_5DAY_DEVIATION.md](HOURLY_5DAY_DEVIATION.md).

# PPO RAW — RESULT DEVIATION ROOT CAUSE

**Question:** the paper-faithful PPO Raw reproduction returns **+63.78%** (Sharpe 2.13, DD −4.04%, win 78.4% per trade) vs the paper's **+15.39%** (Sharpe 0.69, DD −11.22%, win 50.16%). Why?

**Method:** evidence only. Every implementation surface (data, features, normalization, env, reward, PPO config, metrics, Nautilus) was audited in the existing `docs/` forensics and re-verified here. No metric was tuned toward the paper.

---

## THE DECISIVE NUMBERS (eval window 2023-01-03 → 2024-09-12, 531 daily bars)

| | Reproduced PPO Raw | Buy & hold gold | Paper PPO Raw |
|---|---|---|---|
| Cumulative return | **+63.78%** | **+39.09%** | +15.39% |
| Max drawdown | −4.04% | **−11.21%** | −11.22% |
| Exposure (time in market) | **18%** | 100% | ~always in-market |
| Win rate | 78.4% / trade | — | 50.16% |

Gold ran **$1,839 → $2,559 (+39%)** over the window — a strong bull regime. Source: `prepare()` on the live pipeline, `models/ppo_raw_metrics.json`.

Two anchor facts:
1. **Buy&hold DD (−11.21%) ≈ paper PPO Raw DD (−11.22%).** The paper's agent was effectively **always in market** (its 50.16% win rate is a near-coin-flip per-period figure, and it ate the full market drawdown). The reproduced agent is **flat 82% of the time** (`POLICY_BEHAVIOR_REPORT.md`) and avoids that drawdown.
2. The reproduced agent **beat buy&hold by +24pp while exposed only 18% of the time.** This is the result that required leakage scrutiny.

---

## ROOT CAUSES (ranked by evidence)

### 1. Different converged policy — DOMINANT cause. Severity: explains the gap, NOT a bug.
Same reward spec (Eq.22, α/β/γ/δ = 1/2/0.5/0.1, verified exact), **different local optimum**. The reproduced policy converged to a **cautious, long-biased, low-frequency** strategy: 18% exposure, 37 round trips, ~2.7-day average hold, riding the gold uptrend and sitting out pullbacks. The paper's agent converged near-always-in-market with mediocre per-period accuracy. PPO on a single trending asset has many valid optima; the reward (loss-averse β=2α) rewards drawdown avoidance, and *this* seed found the "sit in cash, strike selectively" basin. Evidence: `POLICY_BEHAVIOR_REPORT.md` (action dist 1.1% sell / 81.9% hold / 17% buy), `models/ppo_raw_metrics.json`.

### 2. Selectivity × favorable regime → outperforms buy&hold. Severity: amplifier.
Avoiding the −11% market drawdown alone is worth a large slice of the gap. Catching up-legs and holding cash through down-legs lets an 18%-exposure, **no-leverage** agent compound past the +39% B&H to +63%. Mechanically possible without look-ahead: the product of (1+ret) over the *specifically chosen* in-market days exceeds the full-period product. Evidence: env P&L is `target · (p_{t+1}/p_t − 1)`, all-or-nothing, no leverage (`envs.py:75-98`).

### 3. Win-rate definition. Severity: comparability, not a bug.
78.4% (per trade) vs paper 50.16% is **the same numerator, different exposure regime** — not a denominator error. A low-frequency selective agent has a high per-trade hit rate by construction; an always-in-market agent's per-period win rate sits near 50%. The all-period win rate (10.6%, flat days counted as losses) is NOT comparable for a flat-heavy policy. Evidence: `metrics.py:62-81`, three definitions all computed.

### 4. Sharpe annualization. Severity: ambiguity (paper-side).
2.13 vs 0.69. The paper **does not state its annualization factor** (`PPO_RAW_GROUND_TRUTH.md` §6). We use √252 (daily convention). A flat-heavy series has very low realized volatility (most days = exactly 0 return), which inflates the ratio. Part of the Sharpe gap is the low-vol selective profile, part is an unverifiable annualization choice. Evidence: `metrics.py:40`.

### 5. Dataset vendor + ~6-day week. Severity: second-order path difference.
Data is HF `ZombitX64/xauusd-...` (paper's vendor is **unnamed** — "available on request", `PPO_RAW_GROUND_TRUTH.md` §1). The window yields **531 daily bars** (gold trades ~6 sessions/week) vs the paper's "621-day" span ≈ ~430 bars on a 5-day week. Different vendor + bar count = a different exact return path and a different captured slice of the bull run. Not reconcilable without the paper's data.

---

## DISPROVEN causes (audited clean — NOT the explanation)

| Candidate | Verdict | Evidence |
|---|---|---|
| Look-ahead / leakage | **None.** obs[t]=feat[t]; z-score causal (252, inclusive of t, min_periods=full); indicators via `ta` (causal); action[t] earns t→t+1 (agent never sees t+1); temporal train/test split. | `normalize.py`, `features.py`, `envs.py:78-99`, `data.py:65-75` |
| VecNormalize double-normalization | **Absent.** `make_env` uses Monitor+DummyVecEnv only. Stray `models/vecnormalize.pkl` belongs to the dead old model, not the live path. | `vec_env.py`, `run.py:96` |
| Reward mismatch | Eq.22 exact, coefficients exact. | `envs.py:90-95`, `config.py:40-43` |
| Feature mismatch | Exactly 22, order asserted. | `config.py:70-85` |
| Action inversion | {0:−1, 1:0, 2:+1} correct, no inversion. | `envs.py:22` |
| Nautilus accounting | Fixed (net-liq sizing, leverage 2); env↔Nautilus Δ<1pp. | `FINAL_DISCREPANCY_RESOLUTION_REPORT.md` |

---

## RESIDUAL UNCERTAINTY (the honest limit)

**Single seed (42).** We cannot distinguish *genuine learned momentum-timing skill* from *favorable single-seed variance on one trending period* without a **multi-seed reproduction** (e.g. seeds 0–9, report mean±std). Beating buy&hold by 24pp at 18% exposure is plausible for a learned trend-timer on a strong uptrend, but a single run cannot prove it generalizes. This is the only material open item; it is a *robustness* question, not a fidelity defect.

## VERDICT

The +63.78% vs +15.39% gap is **not an implementation defect**. It is: (1) a different valid converged policy (selective/flat-heavy vs always-in-market), (2) amplified by drawdown-avoidance in a +39% bull regime, (3) reported under a different win-rate exposure regime and an unverifiable Sharpe annualization, (4) on a different (unnamed-by-paper) data vendor. The baseline is paper-faithful; the deviation is regime + policy-variance + paper-side ambiguity. **Recommended next step: multi-seed run** to bound the policy-variance component before claiming reproduction skill.
