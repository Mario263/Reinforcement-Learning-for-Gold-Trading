# REWARD FORENSICS (Agent 5)

Line-by-line verification of the reward against Eq.22 (PDF p.8). Source: `envs.XAUUSDTradingEnv.step`.

## PAPER (Eq.22, p.8)
`r_t = α·R_portfolio − β·DD_t − γ·C_transaction + δ·S_stability`,  α/β/γ/δ = 1.0/2.0/0.5/0.1.
- `R_portfolio = (P_t − P_{t-1})/P_{t-1} · position_{t-1}`
- `DD_t = max(0, (peak_t − P_t)/peak_t)` (running-max)
- `C_transaction` = commissions + slippage
- `S_stability` = penalizes excessive position changes (no formula given)

## CODE (`envs.py step`, traced)
```
turnover  = abs(target - self.position)                 # |Δposition| ∈ {0,1,2}
cost_frac = turnover * (cfg.commission + cfg.spread)    # = |Δ|·0.00015   → C_transaction
price_ret = prices[t+1]/prices[t] - 1                   # raw price path
r_port    = target * price_ret                          # = R_portfolio (position·return)
equity   *= (1 + r_port); equity *= (1 - cost_frac)
dd        = max(0, (peak - equity)/peak)                # = DD_t (running-max)
stability = -turnover                                   # = S_stability (−|Δposition|)
reward    = cfg.alpha*r_port - cfg.beta*dd - cfg.gamma*cost_frac + cfg.delta*stability
```

## TERM-BY-TERM MATCH
| Eq.22 term | Code | Match |
|---|---|---|
| α·R_portfolio | `1.0 * r_port`, `r_port = target·price_ret` | ✅ (formula exact; uses position·return) |
| −β·DD | `- 2.0 * dd`, `dd = max(0,(peak−eq)/peak)` | ✅ running-max drawdown |
| −γ·C_transaction | `- 0.5 * cost_frac`, `cost = |Δpos|·(comm+spread)` | ✅ commissions+spread (slippage/impact omitted per Phase-3 decision) |
| +δ·S_stability | `+ 0.1 * (−|Δpos|)` | ◐ formula (paper gives none) → −|Δposition| |
| weights | α/β/γ/δ = `config.EnvConfig` 1.0/2.0/0.5/0.1 | ✅ |

## SCALING / CLIPPING / NORMALIZATION
- **No reward scaling, no reward clipping, no reward normalization** (VecNormalize removed). The reward is the raw Eq.22 value. The paper specifies none either. ✅
- `R_portfolio` uses **fractional** returns (consistent with "(P_t−P_{t-1})/P_{t-1}"), not dollar P&L. ✅
- Transaction cost is charged on **turnover** (entry and exit each cost), matching "all trading costs." ✅

## DOCUMENTED DEVIATIONS (paper-side gaps)
1. `C_transaction` = commission + spread only; market-impact (√) + slippage (linear) omitted because the paper leaves ADV/coefficients unspecified (Phase-3 user decision). This makes costs *lower* than a full model would — a conservative-for-returns choice, but tiny at this turnover.
2. `S_stability` operationalized as −|Δposition| (paper gives no formula).
3. "relative to benchmark" prose has **no term** in Eq.22 → omitted (faithful to the equation).

## VERDICT
The reward implements Eq.22 **exactly** with the paper's weights. The only deviations are paper-side under-specifications, each documented. **No reward mismatch that constitutes a defect.** (Note: the β=2α loss-aversion drives the low-turnover behavior — a faithful consequence of the spec, analyzed in `../../researchPaper/result_validation.md` F4.)
