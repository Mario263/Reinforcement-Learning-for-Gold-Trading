# ROOT CAUSE REPORT

Date 2026-06-25. Scope (your decision): implementation correctness + RawPPO↔NautilusPPO parity,
NOT paper metrics. Evidence = executed code/diagnostics under `methods/`. "Cannot conclude" is
used where evidence is incomplete.

## Answers to the 15 questions
1. **621-day eval but n_periods=37734?** The "621-day" string was a **stale hardcoded print**
   (`run.py:99`). The eval was correctly hourly 2020→2026 = 37,735 bars. No data contradiction —
   only the label. **FIXED** (now prints frequency + eval_rows + calendar_days). Confidence: high.
2. **Eval window wrong?** No. It is the configured 2020-01→2026-06 test split. Confidence: high.
3. **Frequency mixed/mislabeled?** Mislabeled only; data is consistently 1H. Now prints
   `frequency=HOURLY`. Confidence: high.
4. **Trained on intended range?** Yes — train 2003-06→2019-12 (99,586), eval 2020-01→2026-06
   (37,735). Verified by `prepare()` output. Confidence: high.
5. **Eval using hidden defaults?** RawPPO: no (uses config; `--csv` only overrides if given — the
   earlier `DataConfig(csv_path=args.csv)` clobber bug was fixed). NautilusPPO run scripts default
   `--csv`/`--start`/`--end` to `DataConfig` (printed, not hidden) — can be made required if you
   want strict Rule-1 enforcement. Confidence: high.
6. **Action mapping inconsistent?** No — both `{0:-1, 1:0, 2:+1}` verbatim. `action_match_rate=1.0`
   in the parity run. Confidence: high.
7. **HOLD treated as FLAT?** Yes — action 1 = target position 0 = FLAT in **both** (RawPPO's own
   semantics). Consistent, documented; not a bug. Confidence: high.
8. **PnL sign correct?** Yes. Synthetic test: long=+PnL on up, short=+PnL on down. The −42% is a
   **real bad policy** — model is 62% short during a **+164%** gold bull market ($1518→$4012).
   Confidence: high.
9. **Cost only on position changes?** Yes. Synthetic test: `flat→long` costs, `long→long` costs 0,
   `long→short` costs 2×. Not charged while holding. Confidence: high.
10. **Stability punishing exposure?** No — `stability = −|Δposition|` penalizes **changes**, not
    holding. Synthetic + reward diagnostic confirm (all-long stability sum = −0.1 = the single entry
    only). Confidence: high.
11. **Why NautilusPPO collapsed to flat?** **Reward-floor effect, proven.** Per-bar drawdown
    penalty `−β·dd` (β=2.0) is charged **every bar** a position is below its peak; flat earns ~0.
    On a 408-bar window: all-flat reward **+0.0000** vs all-long **−0.2293** (drawdown term −0.1292).
    So FLAT ≥ any sustained position → PPO converges to all-flat. This is the **inherited
    RawPPO/paper reward design**, not a NautilusPPO-specific bug (RawPPO has the same reward; its run
    found a short-biased local optimum instead — seed/dynamics). Diagnose-only per your instruction;
    reward unchanged. Confidence: high (mechanism); the seed-vs-design split for RawPPO is
    medium ("Evidence incomplete" to fully separate without seed sweeps).
12. **Different feature/normalization/accounting?** Features+normalization **identical** (verbatim
    port; observation parity max_abs_diff = 0.0; action_match 1.0). Accounting **differs by design**
    (Nautilus next-bar fills + integer-oz vs RawPPO instant close-fill) → bounded equity divergence.
    Confidence: high.
13. **Files modified:** `src/rl_gold_trading/run.py` (reporting + csv override), earlier
    `src/rl_gold_trading/data.py` (CSV-only), `config.py` (2003 split, user). New: `methods/` tools.
14. **Tests proving the fix:** `methods/synthetic_action_pnl_test.py` (5/5 pass),
    `methods/reward_component_diagnostic.py` (collapse explained), `methods/parity_harness.py`
    (action/position parity = 1.0).
15. **Remaining limitations:** the reward favors flat (inherited design — not fixed per your
    choice); NautilusPPO full-window training is slow (thread bridge); equity parity has a ~4% max
    return-path divergence from execution timing (explained, not eliminated).

## Findings table
| File | Fn | Old | New | Evidence | Impact | Conf |
|---|---|---|---|---|---|---|
| run.py | main | hardcoded "621-day" + paper-table | explicit window/freq/n_periods + assertions | eval print | reporting correctness | high |
| run.py | main | `DataConfig(csv_path=args.csv)` clobbered config with None | override only if `--csv` given | prior fix | CSV-only worked | high |
| envs.py | step | (correct) cost on turnover, stability=−turnover, r=target·ret | unchanged | synthetic 5/5 | confirms no bug | high |
| reward.py (Naut) | RewardState | (correct port) per-bar −β·dd | unchanged (diagnose only) | reward diag | explains collapse | high |

## Bottom line
RawPPO math is correct; its −42% is an explained bad policy. The NautilusPPO collapse is an
explained reward-floor effect from the ported per-bar drawdown penalty. The two systems share
features/normalization/actions exactly (parity 1.0); they differ only in execution accounting by
design.
