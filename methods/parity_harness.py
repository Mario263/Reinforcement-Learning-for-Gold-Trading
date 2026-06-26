"""RawPPO env vs NautilusPPO (Nautilus) on the SAME model + SAME window.

Same observations (already proven bit-identical) -> same deterministic actions. Nautilus differs
only in execution (next-bar fill, integer-oz) -> bounded equity divergence, quantified here.
  python -m methods.parity_harness --model models/ppo_xauusd_raw.zip
Exports methods/outputs/{rawppo_ledger.csv, nautilus_ledger.csv} + prints a parity summary.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))                 # RawPPO -> rl_gold_trading
sys.path.insert(0, r"C:\Users\Abhishek Sharma\Desktop\NautilusPPO")  # NautilusPPO -> src
from stable_baselines3 import PPO                                     # noqa: E402

WIN_START, WIN_END = "2023-04-03", "2023-04-28"


def rawppo_ledger(model, start, end):
    from rl_gold_trading.config import DataConfig, EnvConfig, FEATURE_ORDER
    from rl_gold_trading.data import load_data
    from rl_gold_trading.features import add_features
    from rl_gold_trading.normalize import rolling_zscore
    from rl_gold_trading.envs import XAUUSDTradingEnv
    feat, cols = add_features(load_data(DataConfig()))
    fz = rolling_zscore(feat, cols)
    win = fz.loc[(fz.index >= pd.Timestamp(start, tz="UTC")) & (fz.index < pd.Timestamp(end, tz="UTC"))]
    env = XAUUSDTradingEnv(win, list(FEATURE_ORDER), EnvConfig(), random_reset=False)
    obs, _ = env.reset(); rows, done = [], False
    while not done:
        a, _ = model.predict(obs, deterministic=True)
        obs, _r, term, trunc, info = env.step(int(a))
        rows.append({"action": int(a), "position": info["position"], "equity": info["equity"]})
        done = term or trunc
    return pd.DataFrame(rows)


def nautilus_ledger(model, start, end):
    from src.config import DataConfig
    from src.train import make_env
    env = make_env(csv=DataConfig().csv_path, slice_start=start, slice_end=end)
    obs, _ = env.reset(); rows, done = [], False
    while not done:
        a, _ = model.predict(obs, deterministic=True)
        obs, _r, term, trunc, info = env.step(int(a))
        rows.append({"action": int(a), "position": info.get("position"), "equity": info.get("equity")})
        done = term or trunc
    env.close()
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="models/ppo_xauusd_raw.zip")
    ap.add_argument("--start", default=WIN_START)
    ap.add_argument("--end", default=WIN_END)
    args = ap.parse_args()
    model = PPO.load(str(ROOT / args.model) if not Path(args.model).is_absolute() else args.model,
                     device="cpu")

    raw = rawppo_ledger(model, args.start, args.end)
    nau = nautilus_ledger(model, args.start, args.end)
    n = min(len(raw), len(nau))
    raw, nau = raw.iloc[:n], nau.iloc[:n]

    action_match = float((raw["action"].values == nau["action"].values).mean())
    pos_match = float((raw["position"].values == nau["position"].values).mean())
    raw_ret = raw["equity"].values / raw["equity"].values[0]
    nau_ret = nau["equity"].values / nau["equity"].values[0]
    eq_max_abs = float(np.max(np.abs(raw_ret - nau_ret)))

    odir = ROOT / "methods" / "outputs"; odir.mkdir(parents=True, exist_ok=True)
    raw.to_csv(odir / "rawppo_ledger.csv", index=False)
    nau.to_csv(odir / "nautilus_ledger.csv", index=False)

    print(f"window {args.start}..{args.end} | aligned bars: {n}")
    print(f"  action_match_rate   = {action_match:.4f}  (expect 1.0 - identical obs)")
    print(f"  position_match_rate = {pos_match:.4f}")
    print(f"  equity-return max|diff| = {eq_max_abs:.6f}  (return-normalized; >0 = execution timing/quantization)")
    print(f"  ledgers -> {odir}")


if __name__ == "__main__":
    main()
