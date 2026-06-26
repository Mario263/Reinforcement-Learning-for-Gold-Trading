"""Forensic audit of a trained RawPPO model (repointed to methods/).

Action probabilities (SB3 policy), trade-level PnL, regime split. Uses methods.shared +
methods.rawPPo. No old src dependency.
  python -m methods.forensic_model_audit --model models/ppo_xauusd_raw.zip
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from stable_baselines3 import PPO

from methods.rawPPo.src.gym_env import RawPPOEnv
from methods.shared.config import CURRENT_SPLIT, FEATURE_ORDER
from methods.shared.data_loader import load_processed
from methods.shared.observations import prepare_window

ROOT = Path(__file__).resolve().parents[1]
DIAG = ROOT / "methods" / "rawPPo" / "diagnostics"


def action_probs(model, obs):
    t = model.policy.obs_to_tensor(np.asarray(obs))[0]
    with torch.no_grad():
        return model.policy.get_distribution(t).distribution.probs.cpu().numpy().ravel()


def run_eval(model, ev):
    env = RawPPOEnv(ev, list(FEATURE_ORDER), random_reset=False)
    obs, _ = env.reset()
    ts, rows, i, done = ev.index, [], 0, False
    while not done:
        p = action_probs(model, obs)
        a = int(np.argmax(p))
        obs, _r, term, trunc, info = env.step(a)
        rows.append({"timestamp": ts[i], "action_id": a, "target_position": info["position"],
                     "p_short": p[0], "p_flat": p[1], "p_long": p[2],
                     "close": float(env.prices[min(env.t, env.n - 1)]), "equity": info["equity"]})
        i += 1; done = term or trunc
    return pd.DataFrame(rows)


def round_trips(df):
    trips, cur, ei = [], 0, None
    eq, px, pos, ts = df["equity"].values, df["close"].values, df["target_position"].values, df["timestamp"].values
    for i in range(len(df)):
        d = int(pos[i])
        if d != cur:
            if cur != 0 and ei is not None:
                trips.append({"side": "short" if cur < 0 else "long", "entry_time": ts[ei],
                              "net_return_pct": (eq[i] / (eq[ei - 1] if ei > 0 else eq[ei]) - 1) * 100})
            ei = i if d != 0 else None; cur = d
    if cur != 0 and ei is not None:
        trips.append({"side": "short" if cur < 0 else "long", "entry_time": ts[ei],
                      "net_return_pct": (eq[len(df) - 1] / (eq[ei - 1] if ei > 0 else eq[ei]) - 1) * 100})
    return pd.DataFrame(trips)


def regime_stats():
    px = load_processed()["close"]
    out = []
    for name, a, b in [("train", "2003-01-01", CURRENT_SPLIT["train_end"]),
                       ("eval", CURRENT_SPLIT["eval_start"], CURRENT_SPLIT["eval_end"])]:
        s = px.loc[pd.Timestamp(a, tz="UTC"):pd.Timestamp(b, tz="UTC")]
        r = s.pct_change().dropna()
        out.append({"window": name, "buyhold_return_pct": (s.iloc[-1] / s.iloc[0] - 1) * 100,
                    "ann_vol_pct": r.std() * np.sqrt(6048) * 100, "up_bar_frac": float((r > 0).mean()),
                    "buyhold_max_dd_pct": float((s / s.cummax() - 1).min()) * 100})
    return pd.DataFrame(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="models/ppo_xauusd_raw.zip")
    ap.add_argument("--device", default="cpu")
    a = ap.parse_args()
    DIAG.mkdir(parents=True, exist_ok=True)
    mp = a.model if Path(a.model).is_absolute() else str(ROOT / a.model)
    model = PPO.load(mp, device=a.device)
    ev, _ = prepare_window(load_processed(), CURRENT_SPLIT["eval_start"], CURRENT_SPLIT["eval_end"])
    print(f"eval bars {len(ev)}")
    df = run_eval(model, ev); df.to_csv(DIAG / "action_probability_audit.csv", index=False)
    print("[ACTION] mean probs short=%.3f flat=%.3f long=%.3f" % (
        df["p_short"].mean(), df["p_flat"].mean(), df["p_long"].mean()))
    tr = round_trips(df); tr.to_csv(DIAG / "round_trip_trade_audit.csv", index=False)
    for side in ("long", "short"):
        s = tr[tr.side == side]
        if len(s):
            print(f"[TRADE] {side}: n={len(s)} win={(s.net_return_pct>0).mean():.0%} "
                  f"total={s.net_return_pct.sum():+.1f}% worst={s.net_return_pct.min():+.1f}%")
    rg = regime_stats(); rg.to_csv(DIAG / "regime_split_market_stats.csv", index=False)
    print("[REGIME]\n" + rg.to_string(index=False))
    print("diagnostics ->", DIAG)


if __name__ == "__main__":
    main()
