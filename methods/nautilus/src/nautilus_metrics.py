"""NautilusPPO metrics — derived from NAUTILUS state (equity/positions from the env's Nautilus
fills/portfolio), fed to the shared metric formulas. No RawPPO ledger involved.
"""
from typing import Dict, List

import numpy as np

from methods.nautilus.src.nautilus_training_env import NautilusTrainingEnv
from methods.shared.diagnostics import compute_metrics


def evaluate(model, eval_obs, cols: List[str], raw_price_df) -> Dict:
    env = NautilusTrainingEnv(eval_obs, cols, raw_price_df)
    obs, _ = env.reset()
    net_rets, equity, positions = [], [env.prev_equity], []
    done = False
    while not done:
        a, _ = model.predict(obs, deterministic=True)
        obs, _r, term, trunc, info = env.step(int(a))
        if "net_ret" in info:
            net_rets.append(info["net_ret"]); equity.append(info["equity"]); positions.append(info["position"])
        done = term or trunc
    env.close()
    m = compute_metrics(net_rets, equity, positions)
    pos = np.asarray(positions)
    m["position_distribution"] = {"short_frac": float((pos == -1).mean()),
                                  "flat_frac": float((pos == 0).mean()),
                                  "long_frac": float((pos == 1).mean())}
    return m
