# PONYTAIL POST-MIGRATION REPORT (Phase 9)

`/ponytail-audit` + `-review` + `-debt` + `-gain` on the migrated `methods/` tree.

## Audit (dead/unused)
| Finding | Decision |
|---|---|
| `delete:` `shared/diagnostics.synthetic_ohlc` — used nowhere | **ACCEPTED (deleted)** — mechanics tests use dummy features, not this |
| `delete:` `shared/data_loader.slice_window` — superseded by `prepare_window` slicing | **ACCEPTED (deleted)** |
| `shared/diagnostics.obs_hash`, `validation.profile`, `validation.assert_fractions` — unused now | **KEEP** — used by the imminent Phase-7 parity/validation work (not speculative) |
| rest of tree | lean — shared logic single-source, frameworks independent (DEDUPLICATION_VERIFICATION) |

`net: -2 functions, -~12 lines.` Re-verified: compile OK, imports OK.

## Review (the migration diff)
Repointed 3 forensic scripts to `methods/`; quarantined old runtime + 2 superseded scripts.
No reinvented stdlib, no new deps, no speculative abstractions introduced.

## Debt ledger
`grep ponytail:` in `methods/` → markers in `shared/normalization` (causal-check note, from the
original) — benign, no rot.

## Gain
Benchmark medians only (LOC ▼80–94%, cost ▼47–77%, 3–6×) — not a per-repo claim.

## Protected (NOT changed)
feature defs/order, `ZSCORE_WINDOW=528`, `PERIODS_PER_YEAR=6048`, reward coeffs, PPO hparams,
action mapping, position sizing, Nautilus accounting ownership. None touched.
