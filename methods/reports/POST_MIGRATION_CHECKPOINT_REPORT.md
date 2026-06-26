# POST-MIGRATION CHECKPOINT REPORT (Phase 0)

| item | value |
|---|---|
| pre-migration checkpoint commit | `ac46807` (new methods/ tree) |
| **migration commit** | **`967a11e`** "Complete methods-tree migration and quarantine old runtime" |
| files committed | old-runtime deletions (src/, train.py, nautilus/, logs/, docs/), `.gitignore` update |
| gitignored (local-only) | `data/`, `_quarantine_old_runtime/`, `models/`, `.venv/`, `__pycache__/` |
| quarantined paths | `_quarantine_old_runtime/{src, train.py, nautilus, logs, methods_synthetic_action_pnl_test.py, methods_train_modern_split.py}` |

## Rollback instructions
- Code: `git checkout ac46807` (pre-migration) or `git revert 967a11e`.
- Quarantined files: still on disk under `_quarantine_old_runtime/` — move back to restore.
- The migration only **moved** old code (never deleted); methods/ is the active tree.
