"""Gymnasium env where NAUTILUS is the simulator (thread-bridge adapter).

Nautilus BacktestEngine.run() is push-based (no public per-bar step), so it runs in a background
thread and BridgeStrategy.on_bar exchanges obs/action with this env via queues. Nautilus owns
replay/fills/positions/cash/PnL. This env only serves the shared 528-z-scored observation and
computes the shared reward (Eq.22) from Nautilus equity. The RawPPO 0.015% cost is overlaid on
Nautilus fill notional (the FX instrument has no such fee model).
"""
import threading
from queue import Queue
from typing import List

import gymnasium as gym
import numpy as np
import pandas as pd
from gymnasium import spaces

from methods.nautilus.src.nautilus_backtest import bar_type, make_instrument, new_engine
from methods.nautilus.src.nautilus_data_adapter import df_to_bars
from methods.nautilus.src.nautilus_strategy import STOP, BridgeStrategy
from methods.shared.actions import action_to_target
from methods.shared.config import COST_RATE, NAUT_DEPLOY_FRAC, NAUT_STARTING_CASH, OBS_DIM
from methods.shared.rewards import raw_ppo_reward

DONE = "__DONE__"


class NautilusTrainingEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, obs_df: pd.DataFrame, feature_cols: List[str], raw_price_df: pd.DataFrame):
        super().__init__()
        if len(feature_cols) != OBS_DIM:
            raise ValueError(f"need {OBS_DIM} features")
        self.obs_matrix = obs_df[feature_cols].to_numpy(np.float32)
        self.bars_df = raw_price_df.loc[obs_df.index, ["open", "high", "low", "close", "volume"]]
        self.n = len(self.obs_matrix)
        self.observation_space = spaces.Box(-np.inf, np.inf, (OBS_DIM,), np.float32)
        self.action_space = spaces.Discrete(3)
        self.instrument = make_instrument()
        self.bar_type = bar_type(self.instrument)
        self._thread = self._engine = self._strat = None
        self.obs_q = self.act_q = None

    def _run_engine(self):
        try:
            self._engine.run()
        finally:
            self.obs_q.put(DONE)

    def _abort_and_join(self):
        if self._thread is not None and self._thread.is_alive():
            self.act_q.put(STOP)
            while True:
                try:
                    if self.obs_q.get(timeout=10) is DONE:
                        break
                except Exception:
                    break
            self._thread.join(timeout=10)
        if self._engine is not None:
            self._engine.dispose()

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self._abort_and_join()
        self.obs_q, self.act_q = Queue(), Queue()
        self._engine = new_engine(self.instrument, NAUT_STARTING_CASH)
        self._engine.add_data(df_to_bars(self.bars_df, self.bar_type, self.instrument))
        self._strat = BridgeStrategy(self.bar_type, self.instrument, self.instrument.id.venue,
                                     self.obs_q, self.act_q, NAUT_DEPLOY_FRAC)
        self._engine.add_strategy(self._strat)
        self._thread = threading.Thread(target=self._run_engine, daemon=True)
        self._thread.start()
        first = self.obs_q.get()
        self._cur = first
        self.prev_equity = first["equity"]
        self.prev_dir = 0
        self.cum_cost = 0.0
        self.peak = first["equity"]
        return self.obs_matrix[first["index"]].copy(), {}

    def step(self, action: int):
        target_dir = action_to_target(int(action))
        turn = abs(target_dir - self.prev_dir)
        self.act_q.put(int(action))
        nxt = self.obs_q.get()
        if nxt is DONE:
            idx = min(self._cur["index"], self.n - 1)
            return (self.obs_matrix[idx].copy(), 0.0, False, True,
                    {"terminal": True, "equity": self.prev_equity, "position": self.prev_dir})
        cost = float(nxt["traded_notional"]) * COST_RATE
        self.cum_cost += cost
        net_equity = nxt["equity"] - self.cum_cost
        self.peak = max(self.peak, net_equity)
        gross_return = ((net_equity - self.prev_equity) + cost) / self.prev_equity if self.prev_equity else 0.0
        cost_frac = (cost / self.prev_equity) if self.prev_equity else 0.0
        dd = max(0.0, (self.peak - net_equity) / self.peak) if self.peak > 0 else 0.0
        reward = raw_ppo_reward(gross_return=gross_return, drawdown=dd, cost_frac=cost_frac,
                                turnover_dir=turn)
        net_ret = (net_equity / self.prev_equity - 1.0) if self.prev_equity else 0.0
        self.prev_equity, self.prev_dir, self._cur = net_equity, target_dir, nxt
        truncated = nxt["index"] >= self.n - 1
        info = {"equity": net_equity, "net_ret": net_ret, "position": target_dir,
                "nautilus_dir": nxt["dir"], "cost": cost, "drawdown": dd}
        return self.obs_matrix[nxt["index"]].copy(), float(reward), False, truncated, info

    def close(self):
        self._abort_and_join()
