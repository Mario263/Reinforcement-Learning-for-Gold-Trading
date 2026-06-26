"""RawPPO training — pure SB3 PPO on the RawPPO Gym env. GPU via device. Curve logging.

SB3 builder + curve logger come from methods.shared.sb3 (single source). This module only wires
the RawPPO Gym env to it.
"""
from typing import List, Optional

import pandas as pd
from stable_baselines3.common.monitor import Monitor

from methods.rawPPo.src.gym_env import RawPPOEnv
from methods.shared.sb3 import CurveLogger, build_ppo


def train(train_obs: pd.DataFrame, cols: List[str], total_timesteps: int,
          ent_coef: Optional[float] = None, device: str = "auto",
          curve_path: Optional[str] = None):
    env = Monitor(RawPPOEnv(train_obs, cols, random_reset=True))
    model = build_ppo(env, ent_coef=ent_coef, device=device)
    model.learn(total_timesteps=total_timesteps,
                callback=CurveLogger(curve_path) if curve_path else None)
    return model
