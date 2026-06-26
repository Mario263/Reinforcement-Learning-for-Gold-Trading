# ARCHITECTURE COMPLIANCE AUDIT (Phase 1)

The new `methods/` tree, built per your structure. Verified by executed checks.

## Layout (built + GPU-tested)
```
methods/shared/    config, data_loader, features, normalization, observations, actions,
                   rewards, validation, diagnostics, sb3   ← framework-neutral single source
methods/rawPPo/src gym_env, train_sb3, evaluate_sb3, raw_metrics      ← pure SB3/Gym + RawPPO accounting
methods/rawPPo/scripts  train, evaluate, run_synthetic_tests
methods/nautilus/src    nautilus_backtest, nautilus_data_adapter, nautilus_strategy,
                        nautilus_training_env, nautilus_metrics, sb3_nautilus_adapter  ← Nautilus-backed
methods/nautilus/scripts train, backtest
```

## Compliance checks (executed)
| Requirement | Result |
|---|---|
| Shared logic defined once | `add_features`→shared/features only; `rolling_zscore`→shared/normalization only; `raw_ppo_reward`→shared/rewards only; `build_ppo`→shared/sb3 only. **No duplication.** |
| rawPPo ⟂ nautilus (independent) | `grep methods.nautilus` in rawPPo = ∅; `grep methods.rawPPo` in nautilus = ∅. **Independent.** |
| Shared output == original | shared vs `rl_gold_trading` on real data: **max_abs_diff 0.0**. |
| RawPPO pure SB3/Gym | `RawPPOEnv(gym.Env)` + SB3 PPO; no nautilus import. ✓ |
| NautilusPPO Nautilus-backed | `NautilusTrainingEnv` runs `BacktestEngine`; fills/positions/cash/PnL from Nautilus; SB3 only via the thread-bridge adapter. Verified: executes dirs {-1,0,1}, equity moves. ✓ |
| RawPPO accounting not in shared/nautilus | RawPPO return-based accounting is only in `rawPPo/src/gym_env.py`. ✓ |
| Nautilus accounting/metrics from Nautilus | `nautilus_metrics.evaluate` derives equity/positions from the Nautilus env, then shared math. ✓ |
| GPU | both frameworks train with `device=cuda` on the RTX 5080 (cu128). ✓ |
| Synthetic mechanics | rawPPo 5/5 PASS; Nautilus executes all directions. ✓ |
| compile | `compileall methods/{shared,rawPPo,nautilus}` OK. |

## Remaining (next steps — not yet done)
1. **Quarantine the OLD duplicated code** (`src/rl_gold_trading/`, `NautilusPPO/src/`) and repoint
   `train.py` + the forensic `methods/*.py` to the new `methods/` tree, so no duplication exists
   *anywhere* (currently the old trees still exist alongside the new one). Careful migration.
2. **Native 500k GPU runs** (current + modern split, both frameworks) — long-running.
3. Map remaining prescribed reports to the produced diagnostics.
