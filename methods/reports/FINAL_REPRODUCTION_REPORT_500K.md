# FINAL REPRODUCTION REPORT — 500K

Date 2026-06-25. GPU: RTX 5080 (torch 2.11.0+cu128).

## 1. Executive summary
Both frameworks completed full 500k GPU training + deterministic evaluation on the modern split.
A real **Nautilus per-bar mark-to-market accounting bug** was found via the same-policy diagnostic,
**fixed**, and NautilusPPO **re-trained**. Post-fix the two envs agree on accounting for identical
actions (action/position parity 1.0; per-bar win rates 28.4% vs 28.4%); the only remaining
difference is the bounded, intentional Nautilus execution (next-bar fill + integer-oz).

## 2. Commits
`ac46807` pre-migration · `967a11e` migration · `bc2c1b0` validation gate. (500k artifacts/reports
to be committed after this report.)

## 3. Environment / GPU
torch 2.11.0+cu128, CUDA True, RTX 5080; SB3 2.9.0; nautilus 1.202.0. Both 500k runs on `cuda`.

## 4. Data / split
Dukascopy 1H XAU/USD processed CSV (2003-2026). Modern split: train 2017-2022, eval 2023-01-02→
2024-09-12 (9,896 hourly periods). No daily resampling. No Kalman.

## 5–6. 528 / 6048
`ZSCORE_WINDOW=528` rolling bars (1 bar=1h≈1 month). `PERIODS_PER_YEAR=6048` (252×24) for hourly
annualization only. Single-defined; never conflated (SANITY_AUDIT).

## 7–8. RawPPO 500k
Train: converged (entropy −0.09), short-biased (0.61/0.38/0.008). Eval: cum **−14.96%**, Sharpe
−0.81, maxDD −20.1%, profit_factor 0.62, final_equity 0.850 — finite & consistent.

## 9–10. NautilusPPO 500k (post MtM fix)
Train: value head learns (ev +0.16), long-biased (0.003/0.47/0.52). Eval (Nautilus-derived): cum
**+6.97%**, Sharpe +0.45, **profit_factor 1.28**, final_equity $10.70M — finite & consistent.

## 11. Comparison
Separately-trained → **opposite policies** (RawPPO short, Nautilus long) from the same reward/
features; metric gaps are training-dynamics, not accounting. No bugs (no NaN/collapse/leverage/
impossible combos). (FULL_500K_RAWPPO_VS_NAUTILUSPPO_COMPARISON.)

## 12. Same-policy diagnostic
RawPPO 500k model through both envs: obs/action/position match **1.0**; per-bar win 28.44% vs
28.37%; equity-return max-diff 3% (execution). Envs agree on accounting.

## 13. Accounting / metric sanity
Both frameworks consistent & finite; 528/6048 isolated; leverage ≤0.95; fees↔trades consistent.

## 14–16. Bugs / fixes / rerun
**1 correctness bug found + fixed:** Nautilus per-bar equity not marked-to-market (bars-only feed)
→ degenerate per-bar metrics + reward. Fixed (`position.unrealized_pnl(make_price(bar.close))`);
verified (in-market net_ret==0: 0.992→0.017); NautilusPPO 500k re-trained. RawPPO unaffected.
(FULL_500K_FIX_LOG.)

## 17. Remaining risks
Per-**fill**-row export still a documented follow-up (equity-level reconciliation is consistent).
Metrics reflect specific converged policies (not performance-tuned).

## 18–19. Deviations
- **From paper:** 1H (not daily), 528-bar z-score (not 252-day), modern split, no market-impact/
  slippage, MACD-pair assumption, tick volume.
- **RawPPO:** none beyond the above (it is the SB3/Gym baseline).
- **Nautilus-specific:** next-bar fill (vs instant), integer-oz quantization, cost overlay (vs a
  Nautilus FeeModel), per-bar MtM via `position.unrealized_pnl`.

## 20. Verdict — **PASS WITH INTENTIONAL DEVIATIONS**
1H, no daily resample, no Kalman, 528 z-score, 6048 annualization, 22 features, PPO+reward settings
match RawPPO, both 500k complete, metrics finite, accounting sane (post-fix), same-policy diagnostic
understood, deviations documented. ✔ all criteria met.

## 21. Exact next commands
```powershell
# re-run / other split:
python -m methods.rawPPo.scripts.train  --split current --total-timesteps 500000 --device cuda --model-out methods/rawPPo/models/rawppo_current_500k.zip
python -m methods.nautilus.scripts.train --split current --total-timesteps 500000 --device cuda --model-out methods/nautilus/models/nautilusppo_current_500k.zip
# evaluate:
python -m methods.rawPPo.scripts.evaluate --model methods/rawPPo/models/rawppo_modern_500k.zip --split modern --device cuda
python -m methods.nautilus.scripts.backtest --model methods/nautilus/models/nautilusppo_modern_500k.zip --split modern --device cuda
```
