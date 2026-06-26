# DEDUPLICATION VERIFICATION REPORT (Phase 6)

Post-quarantine scan (executed). Active tree = `methods/` only.

| Check | Result |
|---|---|
| `add_features` defined | once — `methods/shared/features.py` |
| `rolling_zscore` defined | once — `methods/shared/normalization.py` |
| `raw_ppo_reward` defined | once — `methods/shared/rewards.py` |
| `build_ppo` defined | once — `methods/shared/sb3.py` |
| metric annualization (`compute_metrics`) | once — `methods/shared/diagnostics.py` |
| `ZSCORE_WINDOW = 528` | once — `methods/shared/config.py:26` |
| `PERIODS_PER_YEAR = 6048` | once — `methods/shared/config.py:27` |
| imports of old runtime (`rl_gold_trading`, NautilusPPO, `_quarantine_*`) | **NONE — self-contained** |
| `rawPPo` imports `nautilus` | none (independent) |
| `nautilus` imports `rawPPo` | none (independent) |
| both import `shared` | yes |

**Verdict:** no duplicated framework-neutral logic anywhere in the active tree; `shared/` is the
single source; `rawPPo/` and `nautilus/` are independent. The constants 528 and 6048 are defined
once and imported, never re-declared.
