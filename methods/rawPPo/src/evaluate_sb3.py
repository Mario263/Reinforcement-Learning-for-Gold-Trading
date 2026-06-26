"""RawPPO deterministic evaluation (SB3/Gym) -> metrics + position distribution."""
from typing import Dict, List

import numpy as np
import pandas as pd

from methods.rawPPo.src.gym_env import RawPPOEnv
from methods.rawPPo.src.raw_metrics import evaluate_policy


def evaluate(model, eval_obs: pd.DataFrame, cols: List[str]) -> Dict:
    env = RawPPOEnv(eval_obs, cols, random_reset=False)
    metrics, ledger = evaluate_policy(model, env)
    pos = np.asarray(ledger["positions"])
    metrics["position_distribution"] = {
        "short_frac": float((pos == -1).mean()), "flat_frac": float((pos == 0).mean()),
        "long_frac": float((pos == 1).mean())}
    return metrics
