"""RawPPO env vs NautilusPPO env on the SAME model + SAME window (repointed to methods/).

Same observations (shared pipeline) -> same deterministic actions. Nautilus differs only in
execution (next-bar fill, integer-oz) -> bounded equity divergence, quantified here.
  python -m methods.parity_harness --model models/ppo_xauusd_raw.zip
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from stable_baselines3 import PPO

from methods.nautilus.src.nautilus_training_env import NautilusTrainingEnv
from methods.rawPPo.src.gym_env import RawPPOEnv
from methods.shared.data_loader import load_processed
from methods.shared.observations import prepare_window

ROOT = Path(__file__).resolve().parents[1]
WIN_START, WIN_END = "2023-04-03", "2023-04-28"


def _ledger(env, model):
    obs, _ = env.reset()
    rows, done = [], False
    while not done:
        a, _ = model.predict(obs, deterministic=True)
        obs, _r, term, trunc, info = env.step(int(a))
        rows.append({"action": int(a), "position": info.get("position"), "equity": info.get("equity")})
        done = term or trunc
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="models/ppo_xauusd_raw.zip")
    ap.add_argument("--start", default=WIN_START)
    ap.add_argument("--end", default=WIN_END)
    ap.add_argument("--device", default="cpu")
    a = ap.parse_args()
    mp = a.model if Path(a.model).is_absolute() else str(ROOT / a.model)
    model = PPO.load(mp, device=a.device)

    full = load_processed()
    obs, cols = prepare_window(full, a.start, a.end)
    raw = _ledger(RawPPOEnv(obs, cols, random_reset=False), model)
    nenv = NautilusTrainingEnv(obs, cols, full)
    nau = _ledger(nenv, model); nenv.close()

    n = min(len(raw), len(nau)); raw, nau = raw.iloc[:n], nau.iloc[:n]
    am = float((raw["action"].values == nau["action"].values).mean())
    pm = float((raw["position"].values == nau["position"].values).mean())
    rr = raw["equity"].values / raw["equity"].values[0]
    nr = nau["equity"].values / nau["equity"].values[0]
    eqd = float(np.max(np.abs(rr - nr)))

    odir = ROOT / "methods" / "outputs"; odir.mkdir(parents=True, exist_ok=True)
    raw.to_csv(odir / "rawppo_ledger.csv", index=False)
    nau.to_csv(odir / "nautilus_ledger.csv", index=False)
    print(f"window {a.start}..{a.end} | aligned bars: {n}")
    print(f"  action_match_rate   = {am:.4f}  (expect 1.0 - identical obs)")
    print(f"  position_match_rate = {pm:.4f}")
    print(f"  equity-return max|diff| = {eqd:.6f}  (execution timing/quantization)")
    print(f"  ledgers -> {odir}")


if __name__ == "__main__":
    main()
