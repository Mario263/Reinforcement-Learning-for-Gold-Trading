"""Controlled retrain experiment (evidence-driven, pipeline already proven correct).

Trains RawPPO on a chosen window with a TRAINING-CURVE logger (answers the 'freeze' question)
and an --ent-coef knob (proposed fix: more exploration to fight premature short-bias collapse).
Evaluates deterministically and reports the action/position distribution to compare against the
2003-split model (short=0.62). Does NOT overwrite the existing model.

  python -m methods.train_modern_split --train-start 2017-01-01 --train-end 2022-12-31 \
    --eval-start 2023-01-02 --eval-end 2024-09-12 --total-timesteps 150000 --ent-coef 0.03 \
    --tag modern_entc03
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from stable_baselines3.common.callbacks import BaseCallback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rl_gold_trading.config import DataConfig, EnvConfig, FEATURE_ORDER, TrainConfig  # noqa: E402
from rl_gold_trading.data import load_data                                            # noqa: E402
from rl_gold_trading.features import add_features                                     # noqa: E402
from rl_gold_trading.normalize import rolling_zscore                                  # noqa: E402
from rl_gold_trading.envs import XAUUSDTradingEnv                                     # noqa: E402
from rl_gold_trading.metrics import evaluate_model                                    # noqa: E402
from rl_gold_trading.train import build_model, train_model                           # noqa: E402
from rl_gold_trading.vec_env import make_env                                          # noqa: E402

DIAG = ROOT / "methods" / "rawPPo" / "diagnostics"
OUT = ROOT / "methods" / "rawPPo" / "outputs"
MODELS = ROOT / "methods" / "rawPPo" / "models"
KEYS = ["train/approx_kl", "train/clip_fraction", "train/entropy_loss",
        "train/explained_variance", "train/policy_gradient_loss", "train/value_loss",
        "train/learning_rate", "rollout/ep_rew_mean"]


class CurveLogger(BaseCallback):
    """Capture per-iteration PPO diagnostics (read at each rollout start = after last update)."""
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.rows = []
    def _on_rollout_start(self):
        v = self.model.logger.name_to_value
        if v:
            self.rows.append({"timesteps": self.num_timesteps,
                              **{k.split("/")[-1]: v.get(k) for k in KEYS}})
    def _on_step(self):
        return True
    def _on_training_end(self):
        if self.rows:
            pd.DataFrame(self.rows).to_csv(self.path, index=False)


def _prep_slices(cfg, ts, te, es, ee):
    feat, cols = add_features(load_data(cfg))
    fz = rolling_zscore(feat, cols)
    sl = lambda a, b: fz.loc[(fz.index >= pd.Timestamp(a, tz="UTC")) & (fz.index <= pd.Timestamp(b, tz="UTC"))]
    return sl(ts, te), sl(es, ee)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train-start", required=True); ap.add_argument("--train-end", required=True)
    ap.add_argument("--eval-start", required=True); ap.add_argument("--eval-end", required=True)
    ap.add_argument("--total-timesteps", type=int, default=150000)
    ap.add_argument("--ent-coef", type=float, default=None, help="override RawPPO 0.01")
    ap.add_argument("--tag", default="modern")
    args = ap.parse_args()
    for d in (DIAG, OUT, MODELS):
        d.mkdir(parents=True, exist_ok=True)

    cfg = DataConfig()
    train_df, eval_df = _prep_slices(cfg, args.train_start, args.train_end, args.eval_start, args.eval_end)
    print(f"train rows={len(train_df)} ({args.train_start}..{args.train_end}) | "
          f"eval rows={len(eval_df)} ({args.eval_start}..{args.eval_end})")
    assert len(train_df) > 1000 and len(eval_df) > 100, "slice too small"

    tcfg = TrainConfig(total_timesteps=args.total_timesteps)
    if args.ent_coef is not None:
        tcfg.ent_coef = args.ent_coef
    print(f"PPO: ent_coef={tcfg.ent_coef} (RawPPO default 0.01) | timesteps={tcfg.total_timesteps}")

    env = make_env(train_df, list(FEATURE_ORDER), EnvConfig(), random_reset=True)
    model = build_model(env, tcfg)
    curve = CurveLogger(DIAG / f"ppo_training_curve_{args.tag}.csv")
    model.learn(total_timesteps=tcfg.total_timesteps, callback=curve)
    mpath = MODELS / f"rawppo_{args.tag}.zip"
    model.save(str(mpath))

    eval_env = XAUUSDTradingEnv(eval_df, list(FEATURE_ORDER), EnvConfig(), random_reset=False)
    m = evaluate_model(model, eval_env)

    # action/position distribution on eval
    e2 = XAUUSDTradingEnv(eval_df, list(FEATURE_ORDER), EnvConfig(), random_reset=False)
    obs, _ = e2.reset(); pos, done = [], False
    while not done:
        a, _ = model.predict(obs, deterministic=True)
        obs, _r, t, tr, info = e2.step(int(a)); pos.append(info["position"]); done = t or tr
    pos = np.asarray(pos)
    dist = {"short_frac": float((pos == -1).mean()), "flat_frac": float((pos == 0).mean()),
            "long_frac": float((pos == 1).mean())}

    cpath = DIAG / f"ppo_training_curve_{args.tag}.csv"
    try:
        cdf = pd.read_csv(cpath)
    except Exception:
        cdf = pd.DataFrame()
    result = {"tag": args.tag, "train_rows": len(train_df), "eval_rows": len(eval_df),
              "ent_coef": tcfg.ent_coef, "total_timesteps": tcfg.total_timesteps,
              "position_distribution": dist, "metrics": m,
              "entropy_first": float(cdf["entropy_loss"].iloc[0]) if len(cdf) else None,
              "entropy_last": float(cdf["entropy_loss"].iloc[-1]) if len(cdf) else None}
    (OUT / f"rawppo_{args.tag}_metrics.json").write_text(json.dumps(result, indent=2, default=str))

    print("\n=== RESULT ===")
    print(f"  position dist: {dist}")
    print(f"  cumulative_return={m['cumulative_return']:+.2%}  sharpe={m['sharpe']:.2f}  "
          f"max_dd={m['max_drawdown']:.2%}")
    print(f"  entropy first->last: {result['entropy_first']} -> {result['entropy_last']}")
    print(f"  model -> {mpath}")
    print(f"  curve -> {DIAG / f'ppo_training_curve_{args.tag}.csv'}")


if __name__ == "__main__":
    main()
