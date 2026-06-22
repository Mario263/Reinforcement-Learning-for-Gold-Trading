"""Attribution: is the env-vs-Nautilus gap explained by a 1-bar fill lag?

Env convention:   position[t] earns close[t] -> close[t+1]  (fill at decision close).
Nautilus (event): order on bar t fills at the NEXT price ~ close[t+1], so the
                  position effectively earns close[t+1] -> close[t+2] (1-bar lag).
We recompute cumulative return under both conventions from the SAME policy actions.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import numpy as np
from rl_gold_trading.config import DataConfig, EnvConfig
from rl_gold_trading.run import prepare


def main() -> None:
    cols, _t, eval_df, _d = prepare(DataConfig())
    from stable_baselines3 import PPO
    from rl_gold_trading.envs import XAUUSDTradingEnv
    model = PPO.load(
        str(ROOT / "models" / "ppo_xauusd_raw"), device="cpu",
        custom_objects={"learning_rate": 0.0, "lr_schedule": lambda _: 0.0,
                        "clip_range": lambda _: 0.2},
    )
    env = XAUUSDTradingEnv(eval_df, cols, EnvConfig(), random_reset=False)

    obs, _ = env.reset()
    positions, done = [], False
    while not done:
        a, _ = model.predict(obs, deterministic=True)
        obs, _r, term, trunc, info = env.step(int(a))
        positions.append(info["position"])
        done = term or trunc
    pos = np.array(positions, dtype=float)
    price = eval_df["price"].to_numpy(dtype=float)
    ret = price[1:] / price[:-1] - 1.0            # close[t]->close[t+1], len n-1
    fee = (EnvConfig().commission + EnvConfig().spread)

    # env: pos[t] earns ret[t]; cost on |Δpos|
    dpos = np.abs(np.diff(np.concatenate([[0], pos])))
    n = min(len(pos), len(ret))
    env_net = pos[:n] * ret[:n] - dpos[:n] * fee
    env_cum = float(np.prod(1 + env_net) - 1)

    # 1-bar lag: pos[t] earns ret[t+1] (fill one bar later)
    lag_net = pos[:n-1] * ret[1:n] - dpos[:n-1] * fee
    lag_cum = float(np.prod(1 + lag_net) - 1)

    def dd(x):
        eq = np.cumprod(1 + x); pk = np.maximum.accumulate(eq)
        return float((eq / pk - 1).min())

    print(f"ENV (fill@close[t])    cum={env_cum:.4f}  maxDD={dd(env_net):.4f}")
    print(f"1-BAR LAG (fill@t+1)   cum={lag_cum:.4f}  maxDD={dd(lag_net):.4f}")
    print(f"Nautilus reported      cum=-0.0127        maxDD=-0.1031")


if __name__ == "__main__":
    main()
