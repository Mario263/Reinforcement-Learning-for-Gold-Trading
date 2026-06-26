# ACTION PARITY REPORT (Phase 5)

CSV: `methods/outputs/parity/action_parity.csv`. Same model, same observations → same actions.
Mapping (`methods.shared.actions`, single source): `{0:-1 short, 1:0 flat, 2:+1 long}`.

| metric | value |
|---|---|
| **action_match_rate** | **1.0000** (409/409) |
| **position(target)_match_rate** | **1.0000** |
| first divergence | none |

## Transition semantics (verified in synthetic mechanics 5/5)
| current | action | target | RawPPO | NautilusPPO | match |
|---|---|---|---|---|---|
| flat | buy(2) | long | open long | BUY to long | ✓ |
| flat | sell(0) | short | open short | SELL to short | ✓ |
| flat | hold(1) | flat | none | none | ✓ |
| long | buy(2) | long | none (no accum) | none | ✓ |
| long | hold(1) | flat | close→flat | close→flat | ✓ |
| long | sell(0) | short | reverse | reverse | ✓ |
| short | sell(0) | short | none (no accum) | none | ✓ |
| short | buy(2) | long | reverse | reverse | ✓ |

Repeated same-direction actions do **not** accumulate (synthetic test D: `long→long` cost 0,
position stays +1). Action 1 = FLAT (RawPPO semantics), consistent both frameworks.

**Verdict: PASS.**
