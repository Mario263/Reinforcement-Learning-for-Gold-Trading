# FULL 500K SAME-POLICY DIAGNOSTIC (Phase 8)

One policy (**RawPPO 500k model**) run through **both** envs on the same window
(2023-01-02→2023-12-31, 5,805 bars), post MtM fix. Isolates environment differences from training.
CSVs: `methods/outputs/parity/full_500k_same_policy_{actions,positions,equity,rewards}.csv`.

| metric | value |
|---|---|
| observation hash match | **1.0000** |
| **action match rate** | **1.0000** |
| **position match rate** | **1.0000** |
| equity-return max\|diff\| | 0.0297 (~3%) |
| equity-return mean\|diff\| | 0.0113 (~1.1%) |
| reward max\|diff\| | 0.0664 |
| RawPPO env cum / win | −7.26% / **28.44%** |
| Nautilus env cum / win | −5.40% / **28.37%** |
| first divergence (action/position) | none |

## Reading
- Identical observations → identical actions & positions in both envs (parity exact at 500k scale).
- **Per-bar win rates now match (28.44% vs 28.37%)** — the MtM fix removed the earlier degenerate
  0.3% Nautilus win rate. The envs now agree on accounting for identical actions.
- Residual equity-return divergence (~3% max, ~1% mean) and cum gap (−7.26% vs −5.40%) are the
  documented, bounded Nautilus execution effects: **next-bar fill** + **integer-oz** + MtM at
  Nautilus bar prices vs RawPPO instant close-fill. Not a defect.

**Verdict: PASS** — same policy → same decisions in both frameworks; per-bar accounting agrees;
only the intentional execution difference remains, and it is bounded and explained.
