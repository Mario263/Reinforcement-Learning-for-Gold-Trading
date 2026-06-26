# OLD CODE QUARANTINE MANIFEST (Phase 4)

Old duplicated runtime moved to `_quarantine_old_runtime/` (NOT deleted). Each item proven
unused by the kept tree before moving (no kept `methods/` file imports old `src`/NautilusPPO —
grep clean). Rollback = move back.

| Source | Destination | Reason | Replacement in methods/ | Risk |
|---|---|---|---|---|
| `src/rl_gold_trading/` | `_quarantine_old_runtime/src/` | old RawPPO runtime, fully duplicated | `methods/shared/` + `methods/rawPPo/src/` | none — not imported by kept tree |
| `train.py` | `_quarantine_old_runtime/train.py` | old entrypoint imports old src | `methods/rawPPo/scripts/train.py` | none |
| `nautilus/` | `_quarantine_old_runtime/nautilus/` | old standalone Nautilus backtest | `methods/nautilus/` | none |
| `logs/` | `_quarantine_old_runtime/logs/` | stale run logs | n/a (regenerated) | none |
| `methods/synthetic_action_pnl_test.py` | `_quarantine_old_runtime/methods_synthetic_action_pnl_test.py` | superseded (imported old src) | `methods/rawPPo/scripts/run_synthetic_tests.py` | none — exact replacement verified 5/5 |
| `methods/train_modern_split.py` | `_quarantine_old_runtime/methods_train_modern_split.py` | superseded (imported old src) | `methods/rawPPo/scripts/train.py --split modern` | none — replacement runs on GPU |

## Kept (repointed to methods/, no old-src dependency)
`methods/forensic_model_audit.py`, `methods/parity_harness.py`,
`methods/reward_component_diagnostic.py` — rewritten to import `methods.shared` + `methods.rawPPo`
+ `methods.nautilus`. Verified: parity_harness runs (action/pos match 1.0).

## Kept (required, not quarantined)
`data/` (processed CSV + raw), `models/` (used by forensics), `scripts/` (Dukascopy
download/merge data tooling), `methods/`, `README.md`, `requirements.txt`, `.venv`, `.git`.

## Note
`docs/` (old RawPPO-era reports) was already removed before this migration (git shows deletions).
The two superseded scripts were on your keep-list but are exact duplicates of new `methods/rawPPo`
scripts — quarantined (not deleted) so you can restore if you prefer the old names.
