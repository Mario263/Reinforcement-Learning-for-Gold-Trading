> ⚠️ **DAILY-ERA — SUPERSEDED.** This report describes the original **daily** pipeline. The build now runs **hourly + 5-day-week** (user-directed). Performance numbers below are daily-era and STALE pending a retrain. See [HOURLY_5DAY_DEVIATION.md](HOURLY_5DAY_DEVIATION.md).

# TRADE FORENSIC REPORT

Exact trade counts for the trained PPO Raw model on the 621-day window (2023-01-03 → 2024-09-12, 530 daily periods). All values read **directly** from the generated position series in `forensics/forensic_dump.json` (no estimation, no inference). Definitions are code-traceable to `forensics/run_forensics.py`.

## DEFINITIONS
- **Position-change event:** a step where `position[t] != position[t-1]`.
- **Turnover units:** `Σ |position[t] − position[t-1]|` (a flip counts as 2).
- **Entry:** `prev==0 → new≠0`. **Exit:** `prev≠0 → new==0`. **Flip:** `prev≠0 → new≠0, new≠prev`.
- **Round trip:** a maximal run of constant non-zero position (a flip ends one and starts another).

## EXACT COUNTS
| Quantity | Count |
|---|---|
| Position-change events | **68** |
| Turnover units (Σ\|Δpos\|) | **69** |
| Entries (flat → position) | **34** |
| &nbsp;&nbsp;• Long entries (→ +1) | **29** |
| &nbsp;&nbsp;• Short entries (→ −1) | **5** |
| Exits (position → flat) | **33** |
| Flips (long ↔ short) | **1** |
| Round trips (position segments) | **35** |

## RECONCILIATION (internal consistency)
- Turnover 69 = 68 events with one being a flip (|Δ|=2): `67·1 + 1·2 = 69`. ✅
- Entries 34 = long_entries 29 + short_entries 5. ✅
- Round trips 35 = 34 entries + 1 flip-open. Closes: 33 exits + 1 flip-close + **1 trade still open at series end** = 35. ✅
- The earlier headline "69 trades" was **turnover units**; the precise figures are **68 position changes, 35 round trips, 34 entries**.

## DIRECTIONAL BIAS
- Long entries 29 vs short entries 5 → strongly **long-biased** (consistent with the gold uptrend over the window).
- Long days 90, short days 6, flat days 434 → exposure **18.1%**.

## TRADE OUTCOMES (per round trip, equity-based incl. costs)
| Quantity | Value |
|---|---|
| Round trips | 35 |
| Winning trades | **26** |
| Losing trades | 9 |
| Trade win rate | **74.29%** |
| Profit factor (gross win / gross loss) | **8.84** |

## VERDICT
The model executed **34 entries / 35 round-trip trades** over ~21 months, overwhelmingly long, holding ~3 days on average per position and flat 82% of the time. The trade counts are internally consistent and fully reconciled. This is a **low-frequency, long-biased** policy — quantitatively confirmed, not inferred.
