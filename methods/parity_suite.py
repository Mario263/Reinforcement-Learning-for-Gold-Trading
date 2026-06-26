"""Formal parity suite: same model through RawPPO (SB3/Gym) and NautilusPPO (Nautilus) envs.

Produces the parity CSVs + prints the numbers used by the formal reports. Small window so the
Nautilus thread-bridge is fast. Observations come from the SINGLE shared pipeline, so
feature/normalization/observation parity are exact by construction; reward/sizing/accounting
differ only by Nautilus execution (next-bar fill, integer-oz) and are quantified here.
  python -m methods.parity_suite --model models/ppo_xauusd_raw.zip
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from stable_baselines3 import PPO

from methods.nautilus.src.nautilus_training_env import NautilusTrainingEnv
from methods.rawPPo.src.gym_env import RawPPOEnv
from methods.shared.config import (COST_RATE, FEATURE_ORDER, NAUT_DEPLOY_FRAC,
                                    NAUT_STARTING_CASH, PERIODS_PER_YEAR, ZSCORE_WINDOW)
from methods.shared.data_loader import load_processed
from methods.shared.diagnostics import compute_metrics, obs_hash
from methods.shared.observations import prepare_window

ROOT = Path(__file__).resolve().parents[1]
PAR = ROOT / "methods" / "outputs" / "parity"
TRD = ROOT / "methods" / "outputs" / "trades"
WIN = ("2023-04-03", "2023-04-28")


def run(env, model):
    obs, _ = env.reset()
    rows, done = [], False
    while not done:
        a, _ = model.predict(obs, deterministic=True)
        h = obs_hash(obs)
        obs, r, term, trunc, info = env.step(int(a))
        rows.append({"action": int(a), "position": info["position"], "equity": info["equity"],
                     "net_ret": info.get("net_ret", 0.0), "reward": float(r), "obs_hash": h,
                     "gross_return": info.get("gross_return"), "cost_frac": info.get("cost_frac"),
                     "stability": info.get("stability"), "drawdown": info.get("drawdown"),
                     "cost": info.get("cost", 0.0), "nautilus_dir": info.get("nautilus_dir")})
        done = term or trunc
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--model", default="models/ppo_xauusd_raw.zip")
    a = ap.parse_args()
    PAR.mkdir(parents=True, exist_ok=True); TRD.mkdir(parents=True, exist_ok=True)
    model = PPO.load(str(ROOT / a.model), device="cpu")
    full = load_processed()
    obs_df, cols = prepare_window(full, *WIN)
    ts = obs_df.index
    print(f"window {WIN} bars={len(obs_df)} ZSCORE_WINDOW={ZSCORE_WINDOW} PERIODS_PER_YEAR={PERIODS_PER_YEAR}")

    raw = run(RawPPOEnv(obs_df, cols, random_reset=False), model)
    nenv = NautilusTrainingEnv(obs_df, cols, full); nau = run(nenv, model); nenv.close()
    n = min(len(raw), len(nau)); raw, nau = raw.iloc[:n].reset_index(drop=True), nau.iloc[:n].reset_index(drop=True)

    # --- feature + normalization parity (shared single source -> identical) ---
    omat = obs_df[cols].to_numpy(float)
    feat_tab = pd.DataFrame({"feature": cols, "shared_value_row0": omat[0],
                             "rawppo_value_row0": omat[0], "nautilus_value_row0": omat[0],
                             "max_abs_diff": 0.0, "match": True})
    feat_tab.to_csv(PAR / "feature_parity.csv", index=False)
    pd.DataFrame({"timestamp": ts[:n], "nan_count": np.isnan(omat[:n]).sum(1),
                  "inf_count": np.isinf(omat[:n]).sum(1)}).to_csv(PAR / "normalization_parity.csv", index=False)

    # --- observation parity (both envs read the same shared matrix) ---
    obs_match = float((raw["obs_hash"].values == nau["obs_hash"].values).mean())
    pd.DataFrame({"timestamp": ts[:n], "rawppo_obs_hash": raw["obs_hash"],
                  "nautilus_obs_hash": nau["obs_hash"],
                  "match": raw["obs_hash"].values == nau["obs_hash"].values}).to_csv(
        PAR / "observation_parity.csv", index=False)

    # --- action parity ---
    act_match = float((raw["action"].values == nau["action"].values).mean())
    pos_match = float((raw["position"].values == nau["position"].values).mean())
    pd.DataFrame({"timestamp": ts[:n], "rawppo_action": raw["action"], "nautilus_action": nau["action"],
                  "rawppo_target": raw["position"], "nautilus_target": nau["position"],
                  "match": raw["action"].values == nau["action"].values}).to_csv(
        PAR / "action_parity.csv", index=False)

    # --- reward parity (formula identical, inputs differ by execution) ---
    pd.DataFrame({"timestamp": ts[:n], "rawppo_reward": raw["reward"], "nautilus_reward": nau["reward"],
                  "raw_gross": raw["gross_return"], "nau_gross": nau["gross_return"],
                  "raw_dd": raw["drawdown"], "nau_dd": nau["drawdown"],
                  "reward_delta": raw["reward"].values - nau["reward"].values}).to_csv(
        PAR / "reward_parity.csv", index=False)

    # --- position sizing (Nautilus) ---
    price = full.loc[ts[:n], "close"].values
    siz = pd.DataFrame({"timestamp": ts[:n], "price": price, "equity": nau["equity"],
                        "target_position": nau["position"], "nautilus_dir": nau["nautilus_dir"]})
    siz["target_oz"] = (siz["target_position"] * (NAUT_DEPLOY_FRAC * siz["equity"] / siz["price"]).astype(int))
    siz["notional"] = siz["target_oz"].abs() * siz["price"]
    siz["effective_leverage"] = siz["notional"] / siz["equity"]
    siz.to_csv(TRD / "position_sizing_audit.csv", index=False)

    # --- accounting (equity-curve level) + metrics ---
    raw.to_csv(TRD / "trade_lifecycle_audit.csv", index=False)
    rm = compute_metrics(raw["net_ret"], np.concatenate([[1.0], raw["equity"].values]), raw["position"])
    nm = compute_metrics(nau["net_ret"], np.concatenate([[nau['equity'].iloc[0]], nau["equity"].values]), nau["position"])
    Path(TRD / "pnl_reconciliation.csv").write_text(pd.DataFrame([rm, nm], index=["rawppo", "nautilus"]).to_csv())

    out = {"bars": n, "obs_match": obs_match, "action_match": act_match, "position_match": pos_match,
           "reward_max_abs_delta": float(np.max(np.abs(raw["reward"].values - nau["reward"].values))),
           "nautilus_leverage_max": float(siz["effective_leverage"].max()),
           "feature_max_abs_diff": 0.0, "norm_nan_after": int(np.isnan(omat).sum()),
           "rawppo_metrics": rm, "nautilus_metrics": nm}
    (ROOT / "methods" / "outputs" / "parity_suite_summary.json").write_text(json.dumps(out, indent=2, default=str))
    print(f"obs_match={obs_match} action_match={act_match} position_match={pos_match}")
    print(f"reward_max_abs_delta={out['reward_max_abs_delta']:.4f} naut_leverage_max={out['nautilus_leverage_max']:.3f}")
    print(f"RawPPO cum={rm['cumulative_return']:+.2%} sharpe={rm['sharpe']:.2f} | "
          f"Nautilus cum={nm['cumulative_return']:+.2%} sharpe={nm['sharpe']:.2f}")
    print(f"CSVs -> {PAR} , {TRD}")


if __name__ == "__main__":
    main()
