"""RawPPO synthetic mechanics gate (Phase 4) — pure SB3/Gym env, deterministic.

Proves PnL sign, flat=0, cost-on-change-only, no accumulation, flip=2u-ends-short.
  python -m methods.rawPPo.scripts.run_synthetic_tests
"""
import numpy as np
import pandas as pd

from methods.rawPPo.src.gym_env import RawPPOEnv
from methods.shared.config import FEATURE_ORDER

BUY, HOLD, SELL = 2, 1, 0


def _run(prices, actions):
    df = pd.DataFrame({c: np.zeros(len(prices)) for c in FEATURE_ORDER})
    df["price"] = np.asarray(prices, float)
    env = RawPPOEnv(df, list(FEATURE_ORDER), random_reset=False)
    env.reset()
    rows = []
    for a in actions:
        prev = env.position
        _o, r, _t, _tr, info = env.step(a)
        rows.append({"prev": prev, "pos": info["position"], "net_ret": info["net_ret"],
                     "cost": info["cost"], "reward": r})
    return pd.DataFrame(rows)


def main():
    up, down, flat = [100, 101, 102, 103, 104, 105], [105, 104, 103, 102, 101, 100], [100] * 6
    assert (_run(up, [BUY] * 5)["net_ret"] > 0).all(), "A: long+ on up"
    assert (_run(up, [SELL] * 5)["net_ret"] < 0).all(), "A: short- on up"
    assert np.allclose(_run(up, [HOLD] * 5)["net_ret"], 0), "A: flat=0"
    assert (_run(down, [SELL] * 5)["net_ret"] > 0).all(), "B: short+ on down"
    assert (_run(down, [BUY] * 5)["net_ret"] < 0).all(), "B: long- on down"
    fl = _run(flat, [BUY, BUY, HOLD])
    assert np.allclose(fl["net_ret"].iloc[0], -fl["cost"].iloc[0]), "C: flat-mkt entry cost only"
    rep = _run(up, [BUY, BUY, BUY])
    assert rep["cost"].iloc[0] > 0 and np.allclose(rep["cost"].iloc[1:], 0), "D: cost on change only"
    assert (rep["pos"] == 1).all(), "D: no accumulation"
    flip = _run(up, [BUY, SELL])
    assert flip["pos"].iloc[1] == -1, "E: ends short"
    assert abs(flip["cost"].iloc[1] - 2 * flip["cost"].iloc[0]) < 1e-12, "E: flip=2u cost"
    print("RawPPO synthetic mechanics: 5/5 PASS (PnL sign, flat=0, cost-on-change, no-accum, flip=2u)")


if __name__ == "__main__":
    main()
