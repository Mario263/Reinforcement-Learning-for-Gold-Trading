"""Neutral SB3 PPO builder + curve logger (used by BOTH frameworks — single source, no dup).

This is framework-neutral SB3 glue: both RawPPO and NautilusPPO learn with the same SB3 PPO and
the same spec hyperparameters (methods.shared.config.PPO). It does NOT touch accounting.
"""
from pathlib import Path

import pandas as pd
import torch.nn as nn
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback

from methods.shared.config import PPO as H

CURVE_KEYS = ["train/approx_kl", "train/clip_fraction", "train/entropy_loss",
              "train/explained_variance", "train/policy_gradient_loss", "train/value_loss",
              "train/learning_rate", "rollout/ep_rew_mean"]


def linear_schedule(initial: float):
    def f(progress_remaining: float) -> float:
        return initial * progress_remaining
    return f


class CurveLogger(BaseCallback):
    """Per-iteration PPO diagnostics (read at each rollout start = after the last update)."""
    def __init__(self, path):
        super().__init__(); self.path = path; self.rows = []

    def _on_rollout_start(self):
        v = self.model.logger.name_to_value
        if v:
            self.rows.append({"timesteps": self.num_timesteps,
                              **{k.split("/")[-1]: v.get(k) for k in CURVE_KEYS}})

    def _on_step(self):
        return True

    def _on_training_end(self):
        if self.rows:
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(self.rows).to_csv(self.path, index=False)


def build_ppo(env, ent_coef=None, device: str = "auto") -> PPO:
    return PPO("MlpPolicy", env,
               learning_rate=linear_schedule(H["learning_rate"]),
               n_steps=H["n_steps"], batch_size=H["batch_size"], n_epochs=H["n_epochs"],
               gamma=H["gamma"], gae_lambda=H["gae_lambda"], clip_range=H["clip_range"],
               ent_coef=H["ent_coef"] if ent_coef is None else ent_coef, vf_coef=H["vf_coef"],
               max_grad_norm=H["max_grad_norm"], seed=H["seed"], device=device, verbose=1,
               policy_kwargs=dict(net_arch=dict(pi=list(H["net_arch"]), vf=list(H["net_arch"])),
                                  activation_fn=nn.Tanh))
