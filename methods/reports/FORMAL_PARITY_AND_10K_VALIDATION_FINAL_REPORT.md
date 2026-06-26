# FORMAL PARITY AND 10K VALIDATION — FINAL REPORT

Date 2026-06-25. GPU: RTX 5080 (torch 2.11.0+cu128). 500k **not** run (your instruction).

1. **Migration commit:** `967a11e` (checkpoint `ac46807`).
2. **Formal parity reports created (8):** FEATURE, NORMALIZATION, OBSERVATION, ACTION, REWARD,
   POSITION_SIZING, ACCOUNTING_RECONCILIATION, METRIC_ANNUALIZATION (in `methods/reports/`).
3. **CSV artifacts:** `methods/outputs/parity/{feature,normalization,observation,action,reward}_parity.csv`,
   `methods/outputs/trades/{position_sizing_audit,trade_lifecycle_audit,pnl_reconciliation}.csv`,
   `methods/outputs/parity_suite_summary.json`.
4. Feature parity — **PASS** (22, fixed order, single shared source, max_abs_diff 0).
5. Normalization parity — **PASS** (528 bars, 0 NaN, no global scaler/lookahead, diff 0).
6. Observation parity — **PASS** (obs hash match 1.0/409).
7. Action parity — **PASS** (action & position match 1.0; no accumulation).
8. Reward parity — **PASS** (formula+coeffs identical; per-bar input delta ≤0.10, explained by Nautilus next-bar fill).
9. Position sizing — **PASS** (qty=oz, mult 1, leverage ≤0.95, no over-leverage).
10. Accounting reconciliation — **PASS** (equity-curve consistent; per-fill audit = documented follow-up).
11. Metric annualization — **PASS** (6048 hourly, isolated from 528 z-score window).
12. RawPPO 10k CLI — **PASS** (exit 0, GPU, finite; pos 0.42/0.38/0.20, cum −19.6%).
13. NautilusPPO 10k CLI — **PASS** (exit 0, GPU, finite; pos 0.29/0.33/0.38, cum −9.5%).
14. **Bugs found:** none.
15. **Fixes applied:** none for correctness (added reward-component `info` keys + removed 2 dead helpers).
16. Rerun results: parity suite + both 10k CLIs all green.
17. **Remaining risks:** per-fill accounting audit not yet done (non-blocking); metrics here are
    undertrained (10k steps) so directional only — full performance needs the 500k run.
18. **500k approval gate verdict: APPROVED_FOR_500K.**
19. **Exact next command:**
```powershell
python -m methods.rawPPo.scripts.train  --split modern --total-timesteps 500000 --device cuda --model-out methods/rawPPo/models/rawppo_modern_500k.zip
python -m methods.nautilus.scripts.train --split modern --total-timesteps 500000 --device cuda --model-out methods/nautilus/models/nautilusppo_modern_500k.zip
```

Stopping here. 500k not executed this turn.
