"""Diagnose the NautilusPPO all-flat collapse - DO NOT change the reward (diagnose only).

Repointed to the new methods/ tree (uses methods.shared + methods.nautilus). Runs the REAL
Nautilus-backed env on a small real-data window with two fixed policies (all-long, all-flat) and
logs the per-bar reward components, showing whether the per-bar drawdown penalty makes FLAT the
reward-maximizing policy.
  python -m methods.reward_component_diagnostic
"""
from pathlib import Path

import pandas as pd

from methods.nautilus.src.nautilus_training_env import NautilusTrainingEnv
from methods.shared.data_loader import load_processed
from methods.shared.observations import prepare_window

ROOT = Path(__file__).resolve().parents[1]
WIN_START, WIN_END = "2023-04-03", "2023-04-28"


def _run(env, action):
    env.reset()
    rows, done = [], False
    while not done:
        _o, r, term, trunc, info = env.step(action)
        if "gross_return" in info:
            rows.append({k: info[k] for k in ("gross_return", "drawdown", "cost_frac", "stability")}
                        | {"reward": r, "equity": info["equity"]})
        done = term or trunc
    return pd.DataFrame(rows)


def _summ(df, name):
    terms = {"sum_gross(alpha*ret)": 1.0 * df["gross_return"].sum(),
             "sum_drawdown(-beta*dd)": -2.0 * df["drawdown"].sum(),
             "sum_cost(-gamma*cost)": -0.5 * df["cost_frac"].sum(),
             "sum_stability(+delta*stab)": 0.1 * df["stability"].sum(),
             "TOTAL_reward": df["reward"].sum()}
    print(f"\n[{name}]  bars={len(df)}")
    for k, v in terms.items():
        print(f"    {k:28s} = {v:+.4f}")
    return terms


def main():
    full = load_processed()
    obs, cols = prepare_window(full, WIN_START, WIN_END)
    env = NautilusTrainingEnv(obs, cols, full)
    print(f"window {WIN_START}..{WIN_END} | episode bars: {env.n}")
    long_df, flat_df = _run(env, 2), _run(env, 1)
    lt, ft = _summ(long_df, "ALL-LONG"), _summ(flat_df, "ALL-FLAT")
    odir = ROOT / "methods" / "outputs"
    odir.mkdir(parents=True, exist_ok=True)
    pd.concat({"all_long": long_df, "all_flat": flat_df}, names=["policy"]).to_csv(
        odir / "reward_component_audit.csv")
    print("\n=== DIAGNOSIS ===")
    print(f"  all-flat TOTAL={ft['TOTAL_reward']:+.4f}  all-long TOTAL={lt['TOTAL_reward']:+.4f}")
    print("  VERDICT:", "FLAT >= LONG -> reward favors flat -> collapse explained"
          if ft["TOTAL_reward"] >= lt["TOTAL_reward"] else "LONG > FLAT on this window")
    print(f"  ledger -> {odir / 'reward_component_audit.csv'}")


if __name__ == "__main__":
    main()
