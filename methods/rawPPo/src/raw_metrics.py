"""RawPPO metrics: run the RawPPO Gym ledger, feed it to the shared metric formulas.

RawPPO accounting (equity/positions) is the source; the MATH is shared (no duplication).
"""
from typing import Dict, Tuple

from methods.shared.diagnostics import compute_metrics


def evaluate_policy(model, env) -> Tuple[Dict, Dict]:
    obs, _ = env.reset()
    net_rets, equity, positions = [], [env.equity], []
    done = False
    while not done:
        a, _ = model.predict(obs, deterministic=True)
        obs, _r, term, trunc, info = env.step(int(a))
        net_rets.append(info["net_ret"]); equity.append(info["equity"]); positions.append(info["position"])
        done = term or trunc
    return compute_metrics(net_rets, equity, positions), {
        "net_rets": net_rets, "equity": equity, "positions": positions}
