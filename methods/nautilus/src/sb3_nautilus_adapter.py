"""SB3 PPO <-> Nautilus adapter: SB3 PPO -> Gym adapter -> Nautilus-backed env/state.

The adapter is ONLY control inversion; Nautilus remains the source of truth for execution and
accounting. PPO builder comes from methods.shared.sb3 (same as RawPPO — no duplication).
"""
from typing import List, Optional

import pandas as pd
from stable_baselines3.common.monitor import Monitor

from methods.nautilus.src.nautilus_training_env import NautilusTrainingEnv
from methods.shared.sb3 import CurveLogger, build_ppo


def train(train_obs: pd.DataFrame, cols: List[str], raw_price_df: pd.DataFrame,
          total_timesteps: int, ent_coef: Optional[float] = None, device: str = "auto",
          curve_path: Optional[str] = None):
    env = Monitor(NautilusTrainingEnv(train_obs, cols, raw_price_df))
    model = build_ppo(env, ent_coef=ent_coef, device=device)
    model.learn(total_timesteps=total_timesteps,
                callback=CurveLogger(curve_path) if curve_path else None)
    env.close()
    return model
