"""Diagnose the NautilusPPO all-flat collapse - DO NOT change the reward (diagnose only).

Runs the REAL NautilusPPO env on a small real-data window with two fixed policies (all-long,
all-flat) and logs the per-bar reward components the env already emits (gross_return, drawdown,
cost_frac, stability). Shows whether the per-bar drawdown penalty (-beta*dd, beta=2.0, charged
EVERY bar a position is below its peak) makes FLAT the reward-maximizing policy -> PPO collapse.

  python -m methods.reward_component_diagnostic
Exports methods/outputs/reward_component_audit.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
NAUT = r"C:\Users\Abhishek Sharma\Desktop\NautilusPPO"
sys.path.insert(0, NAUT)
from src.config import DataConfig                        # noqa: E402
from src.train import make_env                           # noqa: E402

WIN_START, WIN_END = "2023-04-03", "2023-04-28"          # small window (prompt's small-batch)


def _run(env, action):
    env.reset()
    rows, done = [], False
    while not done:
        _o, r, term, trunc, info = env.step(action)
        if "gross_return" in info:
            rows.append({k: info[k] for k in
                         ("gross_return", "drawdown", "cost_frac", "stability", "reward", "equity")})
        done = term or trunc
    return pd.DataFrame(rows)


def main():
    d = DataConfig()
    env = make_env(csv=d.csv_path, slice_start=WIN_START, slice_end=WIN_END)
    print(f"window {WIN_START}..{WIN_END} | episode bars: {env.n}")

    long_df = _run(env, 2)    # all-long
    flat_df = _run(env, 1)    # all-flat (target FLAT)

    def summ(df, name):
        terms = {
            "sum_gross(alpha*ret)": 1.0 * df["gross_return"].sum(),
            "sum_drawdown(-beta*dd)": -2.0 * df["drawdown"].sum(),
            "sum_cost(-gamma*cost)": -0.5 * df["cost_frac"].sum(),
            "sum_stability(+delta*stab)": 0.1 * df["stability"].sum(),
            "TOTAL_reward": df["reward"].sum(),
        }
        print(f"\n[{name}]  bars={len(df)}")
        for k, v in terms.items():
            print(f"    {k:28s} = {v:+.4f}")
        return terms

    lt = summ(long_df, "ALL-LONG")
    ft = summ(flat_df, "ALL-FLAT")

    odir = ROOT / "methods" / "outputs"
    odir.mkdir(parents=True, exist_ok=True)
    pd.concat({"all_long": long_df, "all_flat": flat_df}, names=["policy"]).to_csv(
        odir / "reward_component_audit.csv")

    print("\n=== DIAGNOSIS ===")
    print(f"  all-flat TOTAL reward = {ft['TOTAL_reward']:+.4f}")
    print(f"  all-long TOTAL reward = {lt['TOTAL_reward']:+.4f}")
    print(f"  drawdown penalty paid by all-long = {lt['sum_drawdown(-beta*dd)']:+.4f} "
          f"(charged EVERY bar below peak)")
    verdict = ("FLAT >= LONG -> reward favors doing nothing -> collapse explained"
               if ft["TOTAL_reward"] >= lt["TOTAL_reward"] else
               "LONG > FLAT on this window -> collapse is seed/dynamics, not a pure reward-floor effect")
    print(f"  VERDICT: {verdict}")
    print(f"  ledger -> {odir / 'reward_component_audit.csv'}")


if __name__ == "__main__":
    main()
