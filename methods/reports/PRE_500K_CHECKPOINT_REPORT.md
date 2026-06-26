# PRE-500K CHECKPOINT REPORT (Phase 0)

| item | value |
|---|---|
| migration commit | `967a11e` |
| **validation-gate commit** | **`bc2c1b0`** "Complete formal parity and 10k GPU validation gate" |
| files committed | 8 parity reports, 10k validation reports, gate reports, `parity_suite.py`, env reward-info additions |
| CSV artifacts | gitignored (`methods/outputs/` under data? no — `outputs/` is committed code dir, but the CSVs are regenerable; kept in working tree) |
| model/log artifacts | `models/` gitignored; logs under `methods/*/logs` regenerable |

## Rollback
- `git checkout bc2c1b0` (this gate) / `git checkout 967a11e` (migration) / `git checkout ac46807` (pre-migration).
- Quarantined old code under `_quarantine_old_runtime/` (restore by moving back).
