"""Forensic audit of the trained RawPPO model — evidence for short bias / 77%-win-but-loss.

Reuses the verified RawPPO pipeline. Produces:
  rawPPo/diagnostics/action_probability_audit.csv   (SB3 policy probs per bar)
  rawPPo/diagnostics/round_trip_trade_audit.csv      (per round trip PnL)
  rawPPo/diagnostics/regime_split_market_stats.csv   (train vs eval market)
and prints conclusions. No tuning, no retrain.
  python -m methods.forensic_model_audit --model models/ppo_xauusd_raw.zip
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rl_gold_trading.config import DataConfig, EnvConfig, FEATURE_ORDER   # noqa: E402
from rl_gold_trading.data import load_data                                # noqa: E402
from rl_gold_trading.features import add_features                         # noqa: E402
from rl_gold_trading.normalize import rolling_zscore                      # noqa: E402
from rl_gold_trading.envs import XAUUSDTradingEnv                         # noqa: E402
from stable_baselines3 import PPO                                         # noqa: E402

DIAG = ROOT / "methods" / "rawPPo" / "diagnostics"


def _eval_window(cfg):
    feat, cols = add_features(load_data(cfg))
    fz = rolling_zscore(feat, cols)
    ev = fz.loc[(fz.index >= pd.Timestamp(cfg.eval_start, tz="UTC")) &
                (fz.index <= pd.Timestamp(cfg.eval_end, tz="UTC"))]
    return ev


def action_probs(model, obs):
    """Actual SB3 categorical probs [p_short(0), p_flat(1), p_long(2)]."""
    t = model.policy.obs_to_tensor(np.asarray(obs))[0]
    with torch.no_grad():
        p = model.policy.get_distribution(t).distribution.probs.cpu().numpy().ravel()
    return p


def run_eval(model, ev):
    env = XAUUSDTradingEnv(ev, list(FEATURE_ORDER), EnvConfig(), random_reset=False)
    obs, _ = env.reset()
    ts = ev.index
    rows, i, done = [], 0, False
    while not done:
        p = action_probs(model, obs)
        a = int(np.argmax(p))                       # deterministic == argmax
        prev = env.position
        obs, _r, term, trunc, info = env.step(a)
        rows.append({"timestamp": ts[i], "action_id": a, "target_position": info["position"],
                     "p_short": p[0], "p_flat": p[1], "p_long": p[2],
                     "position_before": prev, "position_after": info["position"],
                     "close": float(env.prices[min(env.t, env.n - 1)]), "equity": info["equity"]})
        i += 1
        done = term or trunc
    return pd.DataFrame(rows)


def round_trips(df):
    """Segment constant non-zero position runs into round trips."""
    trips, cur, entry_i = [], 0, None
    eq = df["equity"].values
    px = df["close"].values
    pos = df["position_after"].values
    ts = df["timestamp"].values
    for i in range(len(df)):
        d = int(pos[i])
        if d != cur:
            if cur != 0 and entry_i is not None:
                trips.append(_trip(cur, entry_i, i, eq, px, ts))
            entry_i = i if d != 0 else None
            cur = d
    if cur != 0 and entry_i is not None:
        trips.append(_trip(cur, entry_i, len(df) - 1, eq, px, ts))
    return pd.DataFrame(trips)


def _trip(side, i0, i1, eq, px, ts):
    eq0 = eq[i0 - 1] if i0 > 0 else eq[i0]
    ret = eq[i1] / eq0 - 1.0
    seg = px[i0:i1 + 1]
    return {"side": "short" if side < 0 else "long", "entry_time": ts[i0], "exit_time": ts[i1],
            "entry_price": px[i0], "exit_price": px[i1], "holding_bars": i1 - i0 + 1,
            "net_return_pct": ret * 100.0, "equity_after": eq[i1],
            "mfe_pct": ((seg.max() / px[i0] - 1) if side > 0 else (1 - seg.min() / px[i0])) * 100,
            "mae_pct": ((seg.min() / px[i0] - 1) if side > 0 else (1 - seg.max() / px[i0])) * 100}


def regime_stats(cfg):
    px = load_data(cfg)["close"]
    out = []
    for name, a, b in [("train", cfg.train_end, None), ("eval", cfg.eval_start, cfg.eval_end)]:
        if name == "train":
            s = px.loc[:pd.Timestamp(cfg.train_end, tz="UTC")]
        else:
            s = px.loc[pd.Timestamp(cfg.eval_start, tz="UTC"):pd.Timestamp(cfg.eval_end, tz="UTC")]
        r = s.pct_change().dropna()
        peak = s.cummax()
        out.append({"window": name, "first": s.index.min(), "last": s.index.max(), "bars": len(s),
                    "buyhold_return_pct": (s.iloc[-1] / s.iloc[0] - 1) * 100,
                    "ann_vol_pct": r.std() * np.sqrt(6048) * 100,
                    "up_bar_frac": float((r > 0).mean()), "down_bar_frac": float((r < 0).mean()),
                    "buyhold_max_dd_pct": float((s / peak - 1).min()) * 100})
    return pd.DataFrame(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="models/ppo_xauusd_raw.zip")
    args = ap.parse_args()
    DIAG.mkdir(parents=True, exist_ok=True)
    cfg = DataConfig()
    model = PPO.load(str(ROOT / args.model), device="cpu")
    ev = _eval_window(cfg)

    print(f"eval window {cfg.eval_start}..{cfg.eval_end} | bars {len(ev)}")
    df = run_eval(model, ev)
    df.to_csv(DIAG / "action_probability_audit.csv", index=False)

    # --- action / probability ---
    print("\n[ACTION DISTRIBUTION]")
    print("  argmax action counts:", df["action_id"].value_counts().to_dict(),
          "(0=short,1=flat,2=long)")
    print(f"  mean probs: short={df['p_short'].mean():.3f} flat={df['p_flat'].mean():.3f} "
          f"long={df['p_long'].mean():.3f}")
    print(f"  position fracs: short={(df['target_position']==-1).mean():.3f} "
          f"flat={(df['target_position']==0).mean():.3f} long={(df['target_position']==1).mean():.3f}")

    # --- trades ---
    tr = round_trips(df)
    tr.to_csv(DIAG / "round_trip_trade_audit.csv", index=False)
    wins, losses = tr[tr.net_return_pct > 0], tr[tr.net_return_pct <= 0]
    print("\n[TRADE PnL DISTRIBUTION]")
    print(f"  round_trips={len(tr)} win_rate={len(wins)/max(len(tr),1):.2%}")
    print(f"  avg_win={wins.net_return_pct.mean():.3f}%  avg_loss={losses.net_return_pct.mean():.3f}%  "
          f"(loss/win size ratio={abs(losses.net_return_pct.mean())/max(wins.net_return_pct.mean(),1e-9):.1f}x)")
    for side in ("long", "short"):
        s = tr[tr.side == side]
        if len(s):
            print(f"  {side}: n={len(s)} win_rate={ (s.net_return_pct>0).mean():.2%} "
                  f"total_pnl={s.net_return_pct.sum():+.1f}% worst={s.net_return_pct.min():+.2f}%")
    big = tr.nsmallest(5, "net_return_pct")[["side", "entry_time", "net_return_pct"]]
    print("  top-5 worst trades:\n" + big.to_string(index=False))

    # --- regime ---
    rg = regime_stats(cfg)
    rg.to_csv(DIAG / "regime_split_market_stats.csv", index=False)
    print("\n[REGIME SPLIT]")
    print(rg[["window", "buyhold_return_pct", "ann_vol_pct", "up_bar_frac", "buyhold_max_dd_pct"]].to_string(index=False))
    print(f"\n  diagnostics -> {DIAG}")


if __name__ == "__main__":
    main()
