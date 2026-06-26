"""RawPPO Gymnasium env (pure SB3/Gym). RawPPO accounting lives HERE (return-based, instant fill).

Observations/actions/reward-formula come from methods.shared (single source). Accounting is
RawPPO-specific and intentionally NOT shared and NOT Nautilus.
"""
from typing import Dict, List, Optional, Tuple

import gymnasium as gym
import numpy as np
import pandas as pd
from gymnasium import spaces

from methods.shared.actions import action_to_target
from methods.shared.config import COST_RATE, OBS_DIM, RAW_INITIAL_CAPITAL
from methods.shared.rewards import raw_ppo_reward


class RawPPOEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, obs_df: pd.DataFrame, feature_cols: List[str], random_reset: bool = True):
        super().__init__()
        if len(feature_cols) != OBS_DIM:
            raise ValueError(f"need {OBS_DIM} features")
        self.feat = obs_df[feature_cols].to_numpy(np.float32)
        price_col = "price" if "price" in obs_df.columns else "close"
        self.prices = obs_df[price_col].to_numpy(np.float64)
        self.n = len(self.prices)
        self.random_reset = random_reset
        self.observation_space = spaces.Box(-np.inf, np.inf, (OBS_DIM,), np.float32)
        self.action_space = spaces.Discrete(3)
        self._reset_state()

    def _reset_state(self):
        self.t, self.position = 0, 0
        self.equity = float(RAW_INITIAL_CAPITAL)
        self.peak = self.equity

    def reset(self, *, seed: Optional[int] = None, options: Optional[Dict] = None):
        super().reset(seed=seed)
        self._reset_state()
        if self.random_reset and self.n > 64:
            self.t = int(self.np_random.integers(0, max(1, self.n // 4)))
        return self.feat[self.t].copy(), {}

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        target = action_to_target(int(action))
        turnover = abs(target - self.position)
        cost_frac = turnover * COST_RATE
        p0 = self.prices[self.t]
        p1 = self.prices[self.t + 1] if self.t + 1 < self.n else p0
        price_ret = (p1 / p0) - 1.0 if p0 != 0 else 0.0
        r_port = target * price_ret
        self.equity *= (1.0 + r_port)
        self.equity *= (1.0 - cost_frac)
        self.peak = max(self.peak, self.equity)
        dd = max(0.0, (self.peak - self.equity) / self.peak) if self.peak > 0 else 0.0
        reward = raw_ppo_reward(gross_return=r_port, drawdown=dd, cost_frac=cost_frac,
                                turnover_dir=turnover)
        net_ret = r_port - cost_frac
        self.position = target
        self.t += 1
        truncated = self.t >= (self.n - 1)
        obs_idx = min(self.t, self.n - 1)
        info = {"equity": float(self.equity), "net_ret": float(net_ret),
                "position": int(self.position), "drawdown": float(dd), "cost": float(cost_frac),
                "gross_return": float(r_port), "cost_frac": float(cost_frac),
                "stability": -float(turnover)}
        return self.feat[obs_idx].copy(), float(reward), False, truncated, info
