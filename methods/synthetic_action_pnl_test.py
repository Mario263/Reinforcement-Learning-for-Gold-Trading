"""Deterministic action/PnL/cost tests for the RawPPO trading env (no PPO, no real data).

Proves, on crafted price series, that: long earns +PnL on up moves (short the opposite),
flat earns 0 before costs, cost is charged ONLY on position changes, and a long->short flip
trades 2 units and ends short (not flat, not accumulated). Run:
  python -m methods.synthetic_action_pnl_test
Exports methods/outputs/synthetic_action_pnl.csv. Asserts every expectation.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rl_gold_trading.config import FEATURE_ORDER, EnvConfig          # noqa: E402
from rl_gold_trading.envs import XAUUSDTradingEnv                    # noqa: E402

BUY, HOLD, SELL = 2, 1, 0  # action ids -> target {+1, 0, -1}


def _env(prices):
    df = pd.DataFrame({c: np.zeros(len(prices)) for c in FEATURE_ORDER})
    df["price"] = np.asarray(prices, float)
    return XAUUSDTradingEnv(df, list(FEATURE_ORDER), EnvConfig(), random_reset=False)


def _run(prices, actions):
    env = _env(prices)
    env.reset()
    rows = []
    for a in actions:
        prev = env.position
        _o, r, _t, _tr, info = env.step(a)
        rows.append({"price_t": float(env.prices[env.t - 1]), "action": a,
                     "prev_pos": prev, "pos_after": info["position"],
                     "net_ret": info["net_ret"], "cost": info["cost"],
                     "equity": info["equity"], "reward": r})
    return pd.DataFrame(rows)


def main():
    up = [100, 101, 102, 103, 104, 105]
    down = [105, 104, 103, 102, 101, 100]
    flat = [100, 100, 100, 100, 100, 100]
    out, rng = [], None

    # Test 1 - up series: long profits, short loses, flat ~0 (pre-cost on first step)
    L = _run(up, [BUY] * 5)
    assert (L["net_ret"] > 0).all(), "long should profit on up series"
    S = _run(up, [SELL] * 5)
    assert (S["net_ret"] < 0).all(), "short should lose on up series"
    F = _run(up, [HOLD] * 5)
    assert np.allclose(F["net_ret"], 0) and np.allclose(F["cost"], 0), "flat->flat = 0 pnl & 0 cost"
    out += [("up_long", L), ("up_short", S), ("up_flat", F)]

    # Test 2 - down series: short profits, long loses
    assert (_run(down, [SELL] * 5)["net_ret"] > 0).all(), "short should profit on down series"
    assert (_run(down, [BUY] * 5)["net_ret"] < 0).all(), "long should lose on down series"

    # Test 3 - flat series: any position has 0 price-pnl; cost only when position changes
    fl = _run(flat, [BUY, BUY, HOLD])
    assert np.allclose(fl["net_ret"].iloc[0], -fl["cost"].iloc[0])  # entry cost only
    out += [("flat_series", fl)]

    # Test 4 - repeated same position: cost only on flat->long, none on long->long
    rep = _run(up, [BUY, BUY, BUY])
    assert rep["cost"].iloc[0] > 0, "flat->long should cost"
    assert np.allclose(rep["cost"].iloc[1:], 0), "long->long must NOT cost"
    out += [("repeat_long", rep)]

    # Test 5 - flip long->short: trade 2 units, end short (not flat, not accumulated)
    flip = _run(up, [BUY, SELL])
    assert flip["pos_after"].iloc[1] == -1, "after flip position must be SHORT (-1)"
    cost_entry = flip["cost"].iloc[0]            # flat->long: turnover 1
    cost_flip = flip["cost"].iloc[1]             # long->short: turnover 2
    assert abs(cost_flip - 2 * cost_entry) < 1e-12, "flip cost must be 2x a single-unit cost"
    out += [("flip", flip)]

    odir = ROOT / "methods" / "outputs"
    odir.mkdir(parents=True, exist_ok=True)
    pd.concat({k: v for k, v in out}, names=["case"]).to_csv(odir / "synthetic_action_pnl.csv")
    print("SYNTHETIC ACTION/PNL TESTS PASSED (5/5)")
    print(f"  long/short PnL signs correct; flat=0; cost on-change only; flip=2u, ends short")
    print(f"  ledger -> {odir / 'synthetic_action_pnl.csv'}")


if __name__ == "__main__":
    main()
