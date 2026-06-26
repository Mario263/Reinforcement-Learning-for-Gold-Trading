# POST-QUARANTINE SMOKE TEST REPORT (Phase 5)

All executed after quarantining old runtime. `PYTHONPATH` = RawPPO root. GPU = RTX 5080 (cu128).

| Test | Command | Result |
|---|---|---|
| compile | `compileall methods` | OK |
| rawPPo synthetic mechanics | `-m methods.rawPPo.scripts.run_synthetic_tests` | **5/5 PASS** (PnL sign, flat=0, cost-on-change, no-accum, flip=2u) |
| cross-framework parity (repointed) | `-m methods.parity_harness --model models/ppo_xauusd_raw.zip` | action_match **1.0**, position_match **1.0**, equity-diff 4.3% (execution timing) |
| RawPPO small GPU train+eval | inline, train 2022 (5,830) → eval 2023-H1 (2,873), 8k steps, `cuda` | ran; metrics finite; pos 0.51/0.07/0.42; cum −8.4% |
| NautilusPPO small GPU train+eval | inline, same window, 3k steps, `cuda` | ran; metrics finite (from Nautilus state); pos 0.34/0.26/0.40; cum −2.3% |

## Observations
- GPU used (`Using cuda device`) for both frameworks; RTX 5080.
- No NaN/inf; no all-flat collapse; sane position distributions.
- Negative returns = undertraining (8k/3k vs 500k) on a hard window — expected, not a defect.
- Migration preserved behavior: parity result identical to pre-quarantine (1.0 / 1.0 / 4.3%).

**Verdict: PASS.** The quarantine did not break any entrypoint; both frameworks run end-to-end on
the clean `methods/` tree on GPU.
