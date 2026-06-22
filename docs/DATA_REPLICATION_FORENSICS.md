# DATA REPLICATION FORENSICS (Agent 2)

Verification that the dataset actually used in training/eval matches the paper (PDF p.5–6). Measured at runtime from `data.load_data` / `data.split_train_test` / `data.eval_window`.

## MEASURED (current code)
| Item | Paper (page) | Implementation | Match |
|---|---|---|---|
| Instrument | XAU/USD (p.5) | XAU/USD | ✅ |
| Source vendor | unnamed, "on request" (p.19) | HF `ZombitX64/xauusd-...-2004-2025` | ❓ unverifiable (paper hides vendor) |
| Source granularity | hourly, 47,304 obs (p.5) | 15-min source (8.88M rows) → resampled | ⚠️ source differs; cannot obtain paper's file |
| Modeling frequency | resampled **daily** (p.6) | `resample("1D")` | ✅ |
| Date range | 2017-01-01 → 2025-01-31 (p.5) | filter [2017-01-01, 2025-02-01) | ✅ |
| Missing-data | forward-fill <0.1% (p.6) | `.ffill()` after resample, drop non-trading days | ✅ |
| Train split | 70%, 2017→Dec 2022 (p.6) | calendar `<= 2022-12-31` → **1575 daily bars** | ✅ |
| Test split | 30%, 2023→Jan 2025 (p.6) | calendar `>= 2023-01-01` | ✅ |
| Eval window | 621-day, Jan 2 2023→Sep 12 2024 (p.6,9) | `[2023-01-02, 2024-09-12]` → **531 daily bars** | ✅ |
| OHLCV columns | O,H,L,C,V (p.5) | standardized to open/high/low/close/volume | ✅ |

## MEASURED COUNTS (this run)
- Total daily bars (2017–2025, post-feature/z-score warmup): 2106 (1575 train + 531 eval-window; remaining post-2024-09-12 test bars exist but are excluded from reporting per the paper's 621-day window).
- Train range: 2017-12-17 → 2022-12-30. Eval range: 2023-01-03 → 2024-09-12.

## DELIVERATE DIFFERENCES (documented, not hidden)
1. **Source granularity / vendor:** the paper used an unnamed hourly XAU/USD feed (47,304 obs); we use a public 15-min XAU/USD feed resampled to daily. **The modeled series (daily) matches the paper's stated modeling frequency**, but the exact prices will differ from the paper's private data. This is unavoidable (vendor undisclosed) and cannot bias the *methodology*.
2. **Daily bar count:** the paper's "N=33,113 / 14,191" are *hourly* counts (internally inconsistent with its own daily-resampling statement — flagged in `result_validation.md` F12). Our daily counts (~1575 train / 531 eval) are the correct magnitude for daily bars over these spans.

## LEAKAGE / SPLIT INTEGRITY
- Train and eval are **temporally disjoint**: train max 2022-12-30 < eval min 2023-01-03 (measured). ✅
- No forward-fill across the split boundary affecting eval (ffill is within the continuous series; the split is by date afterward). ✅

## VERDICT
The dataset **matches the paper's stated modeling design** (daily XAU/USD 2017–2025, calendar 70/30, 621-day eval). The only differences are the **undisclosed vendor/source granularity**, which the paper itself does not pin down. **No data mismatch that constitutes an implementation defect.**
