# EVALUATION PIPELINE AUDIT

Trace of `model output → action → position → trade → PnL → metric → report`, with the exact source file/function/variable/formula/units for every metric. Verified by code inspection of the current repo + the forensic rollout (`forensics/forensic_dump.json`).

## DATA FLOW WITH SOURCES
| Stage | File · function | Variable | Formula / logic | Units |
|---|---|---|---|---|
| Data load | `data.py` · `load_data` | daily OHLCV | resample `1D`, ffill | price |
| Features | `features.py` · `add_features` | 22 cols + `price` | `ta` indicators on raw close; `price`=raw close | mixed |
| Normalize | `normalize.py` · `rolling_zscore` | 22 z-cols | `z=(x−μ₂₅₂)/σ₂₅₂` causal | σ-units |
| Eval slice | `data.py` · `eval_window` | `eval_df` | rows in [2023-01-02, 2024-09-12] | — |
| Model output | `metrics.py` · `evaluate_model` | `action` | `model.predict(obs, deterministic=True)` | {0,1,2} |
| Action→position | `envs.py` · `ACTION_TO_POSITION` | `target` | 0→−1, 1→0, 2→+1 | position |
| Cost | `envs.py` · `step` | `cost_frac` | `|target−position|·(commission+spread)` = `|Δ|·0.00015` | fraction |
| Price return | `envs.py` · `step` | `price_ret` | `prices[t+1]/prices[t]−1` (raw `price`) | fraction |
| Portfolio return | `envs.py` · `step` | `r_port` | `target · price_ret` | fraction |
| Equity | `envs.py` · `step` | `equity` | `equity·(1+r_port)·(1−cost_frac)` | normalized |
| Net step return | `envs.py` · `step` | `net_ret` | `r_port − cost_frac` | fraction |
| Drawdown | `envs.py` · `step` | `dd` | `max(0,(peak−equity)/peak)` | fraction |

## METRIC DEFINITIONS (`metrics.py · evaluate_model`)
| Metric | Variable | Formula | Units | Measured |
|---|---|---|---|---|
| Cumulative return | `cumulative_return` | `equity[-1]/equity[0]−1` | fraction | 0.4894 |
| CAGR | `cagr` | `(equity[-1]/equity[0])^(252/n)−1` | fraction | 0.2085 |
| Sharpe | `sharpe` | `mean(net)/std(net)·√252` | ratio | 2.04 |
| Sortino | `sortino` | `mean(net)/std(net[net<0])·√252` | ratio | 2.32 |
| Calmar | `calmar` | `cagr/|maxDD|` | ratio | 6.74 |
| Recovery | `recovery_factor` | `cum_return/|maxDD|` | ratio | 15.81 |
| Max drawdown | `max_drawdown` | `min(equity/cummax(equity)−1)` | fraction | −0.0310 |
| VaR(95%) | `var_95` | `percentile(net, 5)` | fraction | −0.0026 |
| Win rate | `win_rate` | `mean(net>0)` over all periods | fraction | 0.1075 |
| Active win rate | `active_win_rate` | `mean(net>0 | pos≠0)` | fraction | 0.5938 |
| Turnover | `total_turnover` | `Σ|Δposition|` | units | 69 |
| Long/flat/short frac | `*_frac` | `mean(pos==±1/0)` | fraction | 0.17/0.82/0.011 |

## REPORT GENERATION (`run.py · main`)
Prints the comparison table and writes `models/ppo_raw_metrics.json` (keys: `reproduced`, `paper_target`, `timesteps`, `eval_window`).

## VALIDATION CHECKS (independent recompute, `forensic_dump.json`)
- `cumulative_return` from forensic equity path = **0.4894** → matches `metrics.json` (0.48941). ✅
- `win_rate` 57/530 = **0.1075** → matches. ✅
- `active_win_rate` 57/96 = **0.5938** → matches. ✅
- `turnover` Σ|Δpos| = **69** → matches. ✅
- Equity recursion reproduced step-by-step from `(1+r_port)(1−cost)` → identical final equity. ✅

## FINDINGS
- The pipeline is internally consistent; every reported metric is reproducible from the recorded per-step arrays.
- **Determinism:** `model.predict(deterministic=True)` → reproducible actions; single deterministic pass (no seeds affecting eval).
- **One definitional caveat (already flagged):** `win_rate` over all periods is misleading for a flat-heavy policy (see `WIN_RATE_FORENSIC_REPORT.md`).
- **Annualization:** Sharpe/Sortino use √252 (documented assumption; paper unspecified).
- No fabricated or orphan metrics found; every number in the report maps to a `metrics.py` variable.
