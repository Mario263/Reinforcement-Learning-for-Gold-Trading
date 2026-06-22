"""PPO RAW baseline reproduction orchestrator (Kili et al., IJACSA 16(11), 2025).

Pipeline (Paper Section IV):
  daily XAU/USD 2017-2025 -> 22 features -> 252-day rolling z-score
  -> calendar split (train 2017-2022) -> PPO RAW (SB3, paper arch/hparams, 500k)
  -> evaluate on the 621-day window (Jan 2 2023 -> Sep 12 2024).

NO Kalman / DQN / RPPO. PPO Raw only.
"""
import argparse
import json
import os
from typing import Optional

# Import data stack (datasets/pyarrow) BEFORE torch to avoid an OpenMP init clash.
from rl_gold_trading.config import DataConfig, EnvConfig, TrainConfig
from rl_gold_trading.data import eval_window, load_data, split_train_test
from rl_gold_trading.features import add_features
from rl_gold_trading.normalize import rolling_zscore

# Paper PPO Raw reference (Table I/II, PDF p.15).
PAPER_TARGET = {
    "cumulative_return": 0.1539,
    "cagr": 0.0600,
    "sharpe": 0.69,
    "max_drawdown": -0.1122,
    "win_rate": 0.5016,
}


def prepare(data_cfg: DataConfig):
    daily = load_data(data_cfg)
    feat, cols = add_features(daily)
    feat_z = rolling_zscore(feat, cols)        # 252-day causal z-score (drops warmup)
    train, _test = split_train_test(feat_z, data_cfg)
    eval_df = eval_window(feat_z, data_cfg)    # 621-day reported window
    return cols, train, eval_df, daily


def _parse(argv):
    ap = argparse.ArgumentParser(description="PPO RAW baseline (no Kalman).")
    ap.add_argument("--mode", choices=["train", "eval", "train_eval"], default="train_eval")
    ap.add_argument("--timesteps", type=int, default=None)
    ap.add_argument("--csv", default=os.environ.get("XAUUSD_CSV"))
    ap.add_argument("--save-dir", default="models")
    ap.add_argument("--smoke", action="store_true", help="Fast 5k-step sanity run.")
    return ap.parse_args(argv)


def main(args: Optional[argparse.Namespace] = None) -> None:
    args = args if args is not None else _parse(None)
    data_cfg = DataConfig(csv_path=args.csv)
    env_cfg = EnvConfig()
    train_cfg = TrainConfig(save_dir=args.save_dir)
    if args.smoke:
        train_cfg.total_timesteps = 5000
    if args.timesteps is not None:
        train_cfg.total_timesteps = args.timesteps

    print("[1/5] Data -> 22 features -> 252 z-score -> calendar split + 621-day eval...")
    cols, train_df, eval_df, daily = prepare(data_cfg)
    print(f"      daily bars: {len(daily)} | train: {len(train_df)} | eval(621d): {len(eval_df)} | obs_dim: {len(cols)}")
    print(f"      train: {train_df.index.min().date()} -> {train_df.index.max().date()}")
    print(f"      eval : {eval_df.index.min().date()} -> {eval_df.index.max().date()}")

    # torch-dependent imports AFTER data prep.
    from rl_gold_trading.envs import XAUUSDTradingEnv
    from rl_gold_trading.metrics import evaluate_model
    from rl_gold_trading.train import build_model, train_model
    from rl_gold_trading.vec_env import make_env
    from stable_baselines3 import PPO

    model_path = os.path.join(train_cfg.save_dir, "ppo_xauusd_raw")

    if args.mode in ("train", "train_eval"):
        print("[2/5] Build PPO RAW (SB3 [512,512,256,128] Tanh) + train...")
        train_env = make_env(train_df, cols, env_cfg, random_reset=True)
        model = build_model(train_env, train_cfg)
        print(f"[3/5] Training {train_cfg.total_timesteps} timesteps...")
        model = train_model(model, train_cfg)
        os.makedirs(train_cfg.save_dir, exist_ok=True)
        model.save(model_path)
    else:
        print("[2/5] Loading saved model...")
        model = PPO.load(
            model_path, device="cpu",
            custom_objects={"learning_rate": 0.0, "lr_schedule": lambda _: 0.0,
                            "clip_range": lambda _: 0.2},
        )

    if args.mode == "train":
        print(f"Saved: {model_path}.zip")
        return

    print("[4/5] Evaluate on 621-day out-of-sample window (deterministic)...")
    eval_env = XAUUSDTradingEnv(eval_df, cols, env_cfg, random_reset=False)
    m = evaluate_model(model, eval_env)

    print("[5/5] Reproduction report (PPO Raw vs paper)")
    rows = [
        ("Cumulative return", m["cumulative_return"], PAPER_TARGET["cumulative_return"], "%"),
        ("CAGR", m["cagr"], PAPER_TARGET["cagr"], "%"),
        ("Sharpe", m["sharpe"], PAPER_TARGET["sharpe"], ""),
        ("Max drawdown", m["max_drawdown"], PAPER_TARGET["max_drawdown"], "%"),
        # Paper-comparable win rate = per-trade (paper's raw agent is ~always
        # in-market, so its 50.16% is a per-trade/in-market figure, NOT all-period).
        ("Win rate (per trade)", m["trade_win_rate"], PAPER_TARGET["win_rate"], "%"),
    ]
    print(f"\n{'Metric':<22}{'Reproduced':>14}{'Paper PPO Raw':>16}")
    print("-" * 52)
    for name, got, paper, unit in rows:
        if unit == "%":
            print(f"{name:<22}{got*100:>13.2f}%{paper*100:>15.2f}%")
        else:
            print(f"{name:<22}{got:>14.2f}{paper:>16.2f}")
    print("-" * 52)
    print("Win-rate definitions (same wins, different denominators):")
    print(f"  per trade   = {m['trade_win_rate']:.2%}  ({m['round_trips']} round trips)   <- paper-comparable")
    print(f"  in-market   = {m['active_win_rate']:.2%}  (profitable in-market days / in-market days)")
    print(f"  all periods = {m['win_rate']:.2%}  (flat days counted as non-wins; exposure {1-m['flat_frac']:.0%})")
    print(f"Sortino {m['sortino']:.2f} | Calmar {m['calmar']:.2f} | Recovery {m['recovery_factor']:.2f} "
          f"| VaR95 {m['var_95']*100:.2f}%")
    print(f"n_periods={m['n_periods']} turnover={m['total_turnover']} "
          f"long={m['long_frac']:.2f} flat={m['flat_frac']:.2f} short={m['short_frac']:.2f}")

    os.makedirs(train_cfg.save_dir, exist_ok=True)
    with open(os.path.join(train_cfg.save_dir, "ppo_raw_metrics.json"), "w") as f:
        json.dump({"reproduced": m, "paper_target": PAPER_TARGET,
                   "timesteps": train_cfg.total_timesteps,
                   "eval_window": [data_cfg.eval_start, data_cfg.eval_end]}, f, indent=2)
    print(f"\nSaved metrics: {os.path.join(train_cfg.save_dir, 'ppo_raw_metrics.json')}")


if __name__ == "__main__":
    main()
