# OBSERVATION PARITY REPORT (Phase 4)

CSV: `methods/outputs/parity/observation_parity.csv`. Window 2023-04-03..2023-04-28, 409 bars.
Both envs are constructed from the SAME shared observation frame (`prepare_window`), so the per-bar
observation vector fed to PPO is identical.

| check | result |
|---|---|
| shape | (22,) both |
| dtype | float32 both |
| feature order | identical (`FEATURE_ORDER`) |
| **observation_match_rate (sha1 hash per bar)** | **1.0000** (409/409) |
| max_abs_diff | 0.0 |
| mean_abs_diff | 0.0 |
| NaN count | 0 | inf count | 0 |
| first divergence | none |

Per-bar `obs_hash` is identical between RawPPO and NautilusPPO for every bar (CSV). Sampled rows:
first/random/last all match (hashes equal). No unexplained differences.

**Verdict: PASS** — observations are bit-identical across frameworks.
