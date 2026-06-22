"""Paper-faithful trading environment (Paper Section IV.E/F, PDF p.7-8).

State (p.7): exactly 22 z-scored features (5 OHLCV + 17 indicators).
Action (p.7): Discrete(3) -> {sell:-1, hold:0, buy:+1}.
Sizing (p.7): 100% capital, all-or-nothing (no leverage / fractional).
Reward (p.8, Eq.22): r = alpha*R_port - beta*DD - gamma*Cost + delta*Stability,
                     with alpha/beta/gamma/delta = 1.0/2.0/0.5/0.1.
Costs (p.7): commission 0.01% + spread 0.005% per unit turnover.

NO Kalman. PPO Raw baseline only.
"""
from typing import Dict, List, Optional, Tuple

import gymnasium as gym
import numpy as np
import pandas as pd
from gymnasium import spaces

from rl_gold_trading.config import EnvConfig

# Discrete action index -> position (paper A = {-1, 0, +1} = sell, hold, buy).
ACTION_TO_POSITION = {0: -1, 1: 0, 2: 1}


class XAUUSDTradingEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(
        self,
        df: pd.DataFrame,
        feature_cols: List[str],
        config: EnvConfig,
        random_reset: bool = True,
    ) -> None:
        super().__init__()
        if len(feature_cols) != 22:
            raise ValueError("State must be exactly 22 dimensions (paper p.7).")
        self.feature_cols = feature_cols
        self.config = config
        self.random_reset = random_reset

        self.feat = df[feature_cols].to_numpy(dtype=np.float32)
        # Use the RAW price path (real units), NOT the z-scored `close` feature.
        price_col = "price" if "price" in df.columns else "close"
        self.prices = df[price_col].to_numpy(dtype=np.float64)
        self.n = len(self.prices)
        if self.n != len(self.feat):
            raise ValueError("features and prices must align.")

        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(22,), dtype=np.float32)
        self.action_space = spaces.Discrete(3)
        self._reset_state()

    def _reset_state(self) -> None:
        self.t = 0
        self.position = 0
        self.equity = float(self.config.initial_capital)
        self.peak = self.equity

    def reset(
        self, *, seed: Optional[int] = None, options: Optional[Dict] = None
    ) -> Tuple[np.ndarray, Dict]:
        super().reset(seed=seed)
        self._reset_state()
        # Episode = forward pass over the series. Random start during training
        # decorrelates rollouts (still strictly forward in time -> no leakage).
        if self.random_reset and self.n > 64:
            self.t = int(self.np_random.integers(0, max(1, self.n // 4)))
        return self.feat[self.t].copy(), {}

    def step(self, action: int):
        cfg = self.config
        target = ACTION_TO_POSITION[int(action)]

        turnover = abs(target - self.position)                 # in {0,1,2}
        cost_frac = turnover * (cfg.commission + cfg.spread)   # commission + spread (p.7)

        p0 = self.prices[self.t]
        p1 = self.prices[self.t + 1] if self.t + 1 < self.n else p0
        price_ret = (p1 / p0) - 1.0 if p0 != 0 else 0.0

        r_port = target * price_ret                            # R_portfolio (Eq.22)
        self.equity *= (1.0 + r_port)
        self.equity *= (1.0 - cost_frac)
        self.peak = max(self.peak, self.equity)

        dd = max(0.0, (self.peak - self.equity) / self.peak) if self.peak > 0 else 0.0
        stability = -float(turnover)                           # penalize position changes

        reward = (
            cfg.alpha * r_port
            - cfg.beta * dd
            - cfg.gamma * cost_frac
            + cfg.delta * stability
        )

        net_ret = r_port - cost_frac
        self.position = target
        self.t += 1
        terminated = False
        truncated = self.t >= (self.n - 1)

        obs_idx = min(self.t, self.n - 1)
        info = {
            "equity": float(self.equity),
            "net_ret": float(net_ret),
            "position": int(self.position),
            "drawdown": float(dd),
            "cost": float(cost_frac),
        }
        return self.feat[obs_idx].copy(), float(reward), terminated, truncated, info
