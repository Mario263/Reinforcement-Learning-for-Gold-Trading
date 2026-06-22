# DATASET CONFORMANCE REPORT

Paper value (from `../../researchPaper/PPO_RAW_GROUND_TRUTH.md`, with PDF page) vs current Region-II implementation. **Blocking severity**: 🔴 must fix before a faithful run · 🟠 should fix · 🟡 document-only (paper under-specified) · ⚪ acceptable/unverifiable.

| Category | Paper value (page) | Current value | Match? | Required change | Severity |
|---|---|---|---|---|---|
| Instrument | XAU/USD (p.1,5) | XAU/USD (HF ZombitX64) | ✅ | none | ⚪ |
| Data vendor | unnamed, "on request" (p.19) | HF `ZombitX64/xauusd-...-2004-2025` | ❓ unverifiable | none possible | ⚪ |
| Date range | 2017-01-01 → 2025-01-31 (p.5) | 2017-01-01 → 2025-02-01 filter | ✅ | none | ⚪ |
| Source granularity | hourly, 47,304 obs (p.5) | 15-min source (8.8M) → resampled | ⚠️ source differs | resample handles it; cannot obtain their hourly file | 🟡 |
| **Modeling frequency** | **resampled to DAILY (p.6)** | **daily (`1D`)** | ✅ | none | ⚪ |
| Resampling agg | OHLC first/max/min/last, vol sum (standard) | same | ✅ | none | ⚪ |
| Missing-data handling | forward-fill <0.1% (p.6) | dropna on resample | ⚠️ | add forward-fill of daily gaps | 🟠 |
| **Train/test split** | **calendar: train 2017–2022, test 2023–2025 (p.6)** | **70% row fraction of post-warmup frame** | ❌ | **switch to calendar split** | 🔴 |
| Split ratio | 70 / 30 (p.6) | 70 / 30 (by rows) | ⚠️ ratio ok, boundary wrong | calendar boundary 2022-12-31 | 🔴 |
| **Evaluation window** | **621-day, Jan 2 2023 → Sep 12 2024 (p.6,9)** | full 30% test (668 daily) | ❌ | **restrict eval to that window** | 🟠 |
| Feature count | 22 = 5 OHLCV + 17 ind (p.7) | 22 (5 + 17) | ✅ | none | ⚪ |
| Indicator identities | 15 enumerated + 2 unspecified (p.6,7) | 15 + **MACD line+signal** | ⚠️ | document assumption (no paper fix) | 🟡 |
| Normalization | 252-day rolling z-score (p.6, Eq.13) | 252 causal rolling z-score | ✅ | none | ⚪ |
| Normalization leakage | implied causal | causal (trailing window) | ✅ | none | ⚪ |
| Action space | {−1,0,+1} (p.7) | Discrete(3)→{−1,0,+1} | ✅ | none | ⚪ |
| Position sizing | 100% capital (p.7) | 100% capital | ✅ | none | ⚪ |
| Commission | 0.01% (p.7) | 0.0001 | ✅ | none | ⚪ |
| Spread | 0.005% (p.7) | 0.00005 | ✅ | none | ⚪ |
| Market impact | σ√(volume/ADV) (p.7) | not implemented | ❌ | add √-impact (needs ADV assumption) | 🟠 |
| Slippage | linear in size (p.7) | not implemented | ❌ | add linear slippage (needs coeff assumption) | 🟠 |
| Reward | Eq.22 α/β/γ/δ=1/2/0.5/0.1 (p.8) | identical | ✅ | none | ⚪ |
| R_portfolio formula | (Pt−Pt-1)/Pt-1·pos (p.8) | identical | ✅ | none | ⚪ |
| Sharpe annualization | unspecified | √252 | ⚠️ | document assumption | 🟡 |

## CRITICAL ITEMS (must address before the "faithful" run)
- 🔴 **Calendar split** (train 2017–2022 / test 2023–2025) — replaces row-fraction split.
- 🟠 **621-day eval window** (Jan 2 2023 → Sep 12 2024).
- 🟠 **Market impact + slippage** in the cost model (with explicitly documented ADV/coefficient assumptions, since the paper omits them).
- 🟠 **Forward-fill** missing daily bars.

## ITEMS THAT CANNOT BE MADE MORE FAITHFUL (paper under-specifies)
- 🟡 Exact 2 of 17 indicators; Sharpe annualization factor; market-impact ADV & slippage coefficients; data vendor. Each requires a **documented assumption**; no code change can resolve a gap the paper itself leaves open.

## NET CONFORMANCE (dataset layer)
- **Matches now:** 13 / 23 categories ⚪✅.
- **Closable gaps:** 4 (🔴×2 split, 🟠×2 eval-window/costs+ffill grouped).
- **Irreducible (document-only):** 5 🟡.
