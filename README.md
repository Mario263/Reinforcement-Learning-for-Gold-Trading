
# RawPPO and NautilusPPO Gold Trading Reproduction

This repository contains a corrected research reproduction of a PPO-based gold trading system on XAUUSD 1H data.

The project contains two execution frameworks:

1. **RawPPO** — Stable-Baselines3 PPO using a custom Gymnasium-style environment.
2. **NautilusPPO** — Stable-Baselines3 PPO trained through a Nautilus-backed trading environment.

The goal is not to force both separately trained agents to produce identical returns. The goal is to ensure both frameworks use the same data, features, normalization, reward specification, action semantics, metric formulas, and accounting logic, with any remaining execution differences clearly documented.

---

## Current Status

Final corrected state:

```text
RawPPO 500k:
- Completed successfully
- Metrics finite and internally consistent
- Cumulative return: approximately -14.96%
- Sharpe: approximately -0.81
- Max drawdown: approximately -20.1%
- Profit factor: approximately 0.62
- Final equity: approximately 0.85x
- Policy distribution: short-biased

Corrected NautilusPPO 500k:
- Completed successfully after mark-to-market fix
- Metrics finite and internally consistent
- Cumulative return: approximately +6.97%
- Sharpe: approximately +0.45
- Profit factor: approximately 1.28
- Final equity: approximately $10.7M from $10M
- Policy distribution: long-biased
```

The important validation is the same-policy diagnostic:

```text
RawPPO 500k policy evaluated through both environments:
- Observation match: 1.0
- Action match: 1.0
- Position match: 1.0
- RawPPO active per-bar win rate: approximately 28.44%
- Nautilus active per-bar win rate: approximately 28.37%
- Equity divergence: approximately 3%
- Reward delta: bounded and documented
```

This confirms that both environments now agree for the same policy, with remaining differences explained by bounded execution/accounting differences.

---

## Important Correctness Fix

A real Nautilus accounting bug was found and fixed.

### Bug

The Nautilus environment previously used `portfolio.unrealized_pnl()` as the per-bar valuation source. Under a bars-only feed, open positions were not being marked to market every bar. This caused most in-market bars to report zero net return even while price moved.

Observed bug symptoms:

```text
Same policy:
- RawPPO per-bar win rate: approximately 28%
- Nautilus per-bar win rate: approximately 0.3%
- Observation/action/position match: 1.0
- Nautilus in-market net_ret == 0 on approximately 99.2% of bars
```

This degraded both metrics and the PPO reward signal during Nautilus training.

### Fix

The Nautilus environment now marks open positions to market using the current bar close/current valuation price each bar.

After the fix:

```text
Nautilus in-market net_ret == 0:
- Before: approximately 0.992
- After: approximately 0.017

Nautilus net_ret > 0:
- After: approximately 0.482
```

The first NautilusPPO 500k model trained before this fix is invalid and superseded. Only the corrected NautilusPPO model trained after the MtM fix should be used for final comparison.

---

## Locked Research Specification

These values are intentionally locked.

```python
Z_SCORE_WINDOW = 528
PERIODS_PER_YEAR = 6048
```

Meaning:

```text
Z_SCORE_WINDOW = 528:
- Used only for rolling z-score normalization
- 528 rolling bars / observations
- Each bar is 1H
- Approximately one trading month

PERIODS_PER_YEAR = 6048:
- Used only for annualized hourly metrics
- 252 trading days × 24 hourly bars
- Never used as the z-score window
```

Do not confuse these two values.

---

## Intentional Deviations from the Paper

This implementation is paper-aware but intentionally deviates in these ways:

```text
- PPO Raw only
- No Kalman filtering
- XAUUSD Forex data
- 1H bars
- No daily resampling
- 528-bar rolling z-score normalization
- 6048 periods per year for hourly metric annualization
```

These deviations are intentional and must be documented in reports.

---

## Project Structure

```text
methods/
  shared/
    config.py
    actions.py
    features.py
    normalization.py
    rewards.py
    diagnostics.py
    data_loader.py

  rawPPo/
    scripts/
      train.py
      evaluate.py
    models/
    outputs/

  nautilus/
    scripts/
      train.py
      backtest.py
    models/
    outputs/

  outputs/
    parity/
    audits/

  reports/

_quarantine_old_runtime/
  Old duplicated runtime code moved here for safety.
```

The active implementation should use the `methods/` tree. Old quarantined code must not be imported by active scripts.

---

## Feature Set

The observation pipeline uses 22 features:

```text
Open
High
Low
Close
Volume
SMA 10
SMA 20
SMA 50
EMA 12
EMA 26
MACD Line
MACD Signal
RSI 14
Stochastic %K
Stochastic %D
Bollinger Upper
Bollinger Lower
ATR 14
OBV
VWAP
CCI
Williams %R
```

The feature order must remain fixed.

---

## Reward Specification

The reward follows the locked Eq. 22-style structure:

```text
reward =
  return_coefficient * portfolio_return
  - drawdown_coefficient * drawdown_penalty
  - cost_coefficient * transaction_cost
  + stability_coefficient * stability_term
```

Locked coefficients:

```text
return coefficient = 1.0
drawdown coefficient = 2.0
cost coefficient = 0.5
stability coefficient = 0.1
```

---

## Transaction Costs

Locked cost assumptions:

```text
commission = 0.01%
spread = 0.005%
total explicit transition cost = 0.015%
```

Costs should be charged only on real position transitions:

```text
- entry
- exit
- flip
```

Costs should not be charged repeatedly when holding an unchanged position.

---

## Action Mapping

The action space is discrete:

```text
0 -> short / sell / target -1
1 -> flat / hold / target 0
2 -> long / buy / target +1
```

Required behavior:

```text
- Repeated buy while already long must not accumulate unintended exposure.
- Repeated sell while already short must not accumulate unintended exposure.
- Long-to-short flips must account for full turnover.
- Short-to-long flips must account for full turnover.
- Hold/flat behavior must match the locked action semantics.
```

---

## Why RawPPO and NautilusPPO Metrics Can Differ

Separately trained RawPPO and NautilusPPO models are not required to have identical metrics.

They may differ because:

```text
- PPO training is stochastic.
- RawPPO and NautilusPPO may converge to different local optima.
- Nautilus uses event-driven execution, orders, fills, and accounting.
- Nautilus may have bounded next-bar fill or execution timing differences.
```

The strict parity test is the same-policy diagnostic.

For the same trained policy:

```text
- Observations should match.
- Actions should match.
- Positions should match or have documented timing differences.
- Per-bar mark-to-market behavior should be comparable.
- Large unexplained metric differences are correctness bugs.
```

---

## Environment Setup

From PowerShell:

```powershell
cd "C:\Users\Abhishek Sharma\Desktop\RawPPO"
.\.venv\Scripts\activate
```

Check Python and CUDA:

```powershell
python --version
where python
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NO CUDA')"
```

Use `--device cuda` only if CUDA is available in the active environment.

If CUDA is unavailable, use:

```powershell
--device auto
```

---

## Compile Check

```powershell
python -m compileall methods
```

Expected result:

```text
Compilation succeeds without syntax errors.
```

---

## Evaluate RawPPO 500k Model

CPU-safe / automatic device selection:

```powershell
python -m methods.rawPPo.scripts.evaluate --split modern --model methods/rawPPo/models/rawppo_modern_500k.zip --device auto --out methods/rawPPo/outputs/metrics/rawppo_modern_500k_eval.json
```

CUDA form, only if CUDA is available:

```powershell
python -m methods.rawPPo.scripts.evaluate --split modern --model methods/rawPPo/models/rawppo_modern_500k.zip --device cuda --out methods/rawPPo/outputs/metrics/rawppo_modern_500k_eval.json
```

---

## Evaluate Corrected NautilusPPO 500k Model

The Nautilus evaluation command may be called `backtest`, not `evaluate`, depending on the local CLI.

CPU-safe / automatic device selection:

```powershell
python -m methods.nautilus.scripts.backtest --split modern --model methods/nautilus/models/nautilusppo_modern_500k_mtm_fixed.zip --device auto --out methods/nautilus/outputs/metrics/nautilusppo_modern_500k_mtm_fixed_eval.json
```

CUDA form, only if CUDA is available:

```powershell
python -m methods.nautilus.scripts.backtest --split modern --model methods/nautilus/models/nautilusppo_modern_500k_mtm_fixed.zip --device cuda --out methods/nautilus/outputs/metrics/nautilusppo_modern_500k_mtm_fixed_eval.json
```

Check the exact local flags first:

```powershell
python -m methods.nautilus.scripts.backtest --help
```

---

## Same-Policy Parity Diagnostic

Run RawPPO 500k policy through both environments:

```powershell
python -m methods.parity_suite --model methods/rawPPo/models/rawppo_modern_500k.zip
```

Expected result:

```text
obs_match = 1.0
action_match = 1.0
position_match = 1.0
reward delta bounded
leverage capped
same-policy logs similar
```

This is the primary proof that RawPPO and NautilusPPO environments agree for identical decisions.

---

## Optional RawPPO 500k Training Rerun

Do not rerun RawPPO unless an audit proves a RawPPO correctness bug.

CPU-safe / automatic device selection:

```powershell
python -m methods.rawPPo.scripts.train --split modern --total-timesteps 500000 --device auto --model-out methods/rawPPo/models/rawppo_modern_500k.zip
```

CUDA form:

```powershell
python -m methods.rawPPo.scripts.train --split modern --total-timesteps 500000 --device cuda --model-out methods/rawPPo/models/rawppo_modern_500k.zip
```

---

## Optional Corrected NautilusPPO 500k Training Rerun

Only rerun corrected NautilusPPO if the corrected model is missing, invalid, or intentionally being regenerated.

CPU-safe / automatic device selection:

```powershell
python -m methods.nautilus.scripts.train --split modern --total-timesteps 500000 --device auto --model-out methods/nautilus/models/nautilusppo_modern_500k_mtm_fixed.zip
```

CUDA form:

```powershell
python -m methods.nautilus.scripts.train --split modern --total-timesteps 500000 --device cuda --model-out methods/nautilus/models/nautilusppo_modern_500k_mtm_fixed.zip
```

---

## Recommended Manual Validation Sequence

Run this sequence after activating the virtual environment:

```powershell
cd "C:\Users\Abhishek Sharma\Desktop\RawPPO"
.\.venv\Scripts\activate

python -m compileall methods

python -m methods.rawPPo.scripts.evaluate --split modern --model methods/rawPPo/models/rawppo_modern_500k.zip --device auto --out methods/rawPPo/outputs/metrics/rawppo_modern_500k_eval.json

python -m methods.nautilus.scripts.backtest --split modern --model methods/nautilus/models/nautilusppo_modern_500k_mtm_fixed.zip --device auto --out methods/nautilus/outputs/metrics/nautilusppo_modern_500k_mtm_fixed_eval.json

python -m methods.parity_suite --model methods/rawPPo/models/rawppo_modern_500k.zip
```

Use `--device cuda` only after confirming CUDA is available.

---

## Reports

Important reports produced during the final run include:

```text
PRE_500K_CHECKPOINT_REPORT.md
FULL_500K_ENVIRONMENT_REPORT.md
PER_FILL_ACCOUNTING_AUDIT_PRE_500K.md
RAWPPO_500K_TRAINING_REPORT.md
RAWPPO_500K_EVALUATION_REPORT.md
NAUTILUSPPO_500K_TRAINING_REPORT.md
NAUTILUSPPO_500K_EVALUATION_REPORT.md
FULL_500K_FIX_LOG.md
FULL_500K_SAME_POLICY_DIAGNOSTIC.md
FULL_500K_ACCOUNTING_AND_METRIC_SANITY_AUDIT.md
FULL_500K_RAWPPO_VS_CORRECTED_NAUTILUSPPO_COMPARISON.md
FINAL_REPRODUCTION_REPORT_500K.md
NEXT_RUN_COMMANDS.md
```

Depending on local organization, these may be under:

```text
methods/reports/
methods/outputs/
```

---

## Final Verdict

Current final verdict:

```text
PASS WITH INTENTIONAL DEVIATIONS
```

Reason:

```text
- RawPPO 500k completed.
- Corrected NautilusPPO 500k completed.
- Metrics are finite and internally consistent.
- Nautilus MtM accounting bug was found and fixed.
- Same-policy diagnostic passes after fix.
- Z_SCORE_WINDOW = 528 is preserved for normalization.
- PERIODS_PER_YEAR = 6048 is preserved for hourly annualization.
- 22-feature observation pipeline is preserved.
- No Kalman path is active.
- No daily resampling is active.
- Remaining differences are documented and bounded.
```

---

## Important Warning

Do not treat RawPPO’s negative result as an automatic implementation bug.

RawPPO 500k produced a short-biased unprofitable policy. Corrected NautilusPPO 500k produced a long-biased profitable policy. This is a policy/training outcome difference between separately trained agents.

The environment parity proof is the same-policy diagnostic, not equality of separately trained model returns.

---

## Optional Performance Ablation

Performance tuning must be done only after the correctness baseline is locked.

Create a separate branch:

```powershell
git checkout -b performance-ablation-after-correctness-lock
```

Potential ablations:

```text
- multiple random seeds
- lower drawdown penalty
- different entropy coefficient
- longer training
- walk-forward validation
- reward scaling study
```

Ablation results must not replace the locked baseline reproduction.

---

## Git Checkpoints

Known checkpoint sequence:

```text
ac46807  checkpoint
967a11e  methods-tree migration
bc2c1b0  validation gate
91a30ff  500k results + Nautilus MtM fix
```

Use local `git log --oneline` to confirm current history.

---

## Clean Working Tree Check

Before new experiments:

```powershell
git status
```

Recommended state:

```text
nothing to commit, working tree clean
```

Do not start ablations or reruns from a dirty working tree.
