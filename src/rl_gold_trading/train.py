"""PPO RAW model builder (Paper Section IV.G.2 / IV.H, PDF p.9).

Stable-Baselines3 PPO (mature library; NO custom PPO). Architecture:
actor & critic = [512, 512, 256, 128] with Tanh, softmax actor / linear critic.
Learning rate 3e-4 with LINEAR decay to zero.
"""
import torch.nn as nn
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv

# pyrefly: ignore [missing-import]
from rl_gold_trading.config import TrainConfig


def linear_schedule(initial: float):
    """SB3 schedule: progress_remaining goes 1 -> 0 over training (p.9)."""
    def f(progress_remaining: float) -> float:
        return initial * progress_remaining
    return f


def build_model(train_env: DummyVecEnv, cfg: TrainConfig) -> PPO:
    policy_kwargs = dict(
        net_arch=dict(pi=list(cfg.net_arch), vf=list(cfg.net_arch)),
        activation_fn=nn.Tanh,
    )
    lr = linear_schedule(cfg.learning_rate) if cfg.lr_linear_decay else cfg.learning_rate
    return PPO(
        "MlpPolicy",
        train_env,
        learning_rate=lr,
        n_steps=cfg.n_steps,
        batch_size=cfg.batch_size,
        n_epochs=cfg.n_epochs,
        gamma=cfg.gamma,
        gae_lambda=cfg.gae_lambda,
        clip_range=cfg.clip_range,
        ent_coef=cfg.ent_coef,
        vf_coef=cfg.vf_coef,
        max_grad_norm=cfg.max_grad_norm,
        policy_kwargs=policy_kwargs,
        seed=cfg.seed,
        device="cuda",
        verbose=1,
    )


def train_model(model: PPO, cfg: TrainConfig) -> PPO:
    model.learn(total_timesteps=cfg.total_timesteps)
    return model
