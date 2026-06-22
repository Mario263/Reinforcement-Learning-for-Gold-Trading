"""ENV vs NAUTILUS row-by-row parity export (Phase 2/3 of the forensic directive).

Runs the SAME frozen model through (a) the RL environment and (b) Nautilus on the
same 621-day window, then aligns by date and writes diff CSVs + a root-cause summary.
Inference only. No retraining.
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "nautilus"))
OUT = Path(__file__).resolve().parent / "outputs"
OUT.mkdir(exist_ok=True)

import numpy as np
import pandas as pd

from rl_gold_trading.config import DataConfig, EnvConfig
from rl_gold_trading.run import prepare

CUSTOM = {"learning_rate": 0.0, "lr_schedule": lambda _: 0.0, "clip_range": lambda _: 0.2}


def run_env(cols, eval_df, model):
    from rl_gold_trading.envs import XAUUSDTradingEnv
    env = XAUUSDTradingEnv(eval_df, cols, EnvConfig(), random_reset=False)
    price = eval_df["price"].to_numpy(float)
    dates = [pd.Timestamp(i).date() for i in eval_df.index]
    obs, _ = env.reset()
    rows, done, t = [], False, 0
    while not done:
        a, _ = model.predict(obs, deterministic=True)
        a = int(a)
        p0 = env.prices[env.t]
        obs, _r, term, trunc, info = env.step(a)
        p1 = env.prices[min(env.t, env.n - 1)]
        rows.append({
            "date": str(dates[t]), "action": a, "position": info["position"],
            "decision_close": float(p0), "next_close": float(p1),
            "price_ret": float(p1 / p0 - 1 if p0 else 0),
            "r_port": float(info["position"] * (p1 / p0 - 1 if p0 else 0)),
            "net_ret": float(info["net_ret"]), "env_equity": float(info["equity"]),
        })
        t += 1
        done = term or trunc
    return rows


def run_nautilus(cols, eval_df, model):
    import run_backtest as rb
    from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
    from nautilus_trader.backtest.models import MakerTakerFeeModel
    from nautilus_trader.config import LoggingConfig
    from nautilus_trader.model.currencies import USD
    from nautilus_trader.model.enums import AccountType, OmsType
    from nautilus_trader.model.identifiers import Venue
    from nautilus_trader.model.objects import Money
    from decimal import Decimal
    from strategy import RLConfig, RLPolicyStrategy

    inst = rb.build_instrument()
    bar_type, bars, quotes = rb.build_data(inst, eval_df)
    eng = BacktestEngine(config=BacktestEngineConfig(trader_id="PARITY-001",
                         logging=LoggingConfig(log_level="ERROR")))
    eng.add_venue(venue=Venue("SIM"), oms_type=OmsType.NETTING, account_type=AccountType.MARGIN,
                  base_currency=USD, starting_balances=[Money(rb.STARTING_USD, USD)],
                  default_leverage=Decimal(2), fee_model=MakerTakerFeeModel(), bar_execution=False)
    eng.add_instrument(inst); eng.add_data(bars); eng.add_data(quotes)
    s = RLPolicyStrategy(RLConfig(instrument_id=str(inst.id), bar_type=str(bar_type)))
    s.attach(model, {pd.Timestamp(i).normalize(): eval_df.loc[i, cols].to_numpy(np.float32)
                     for i in eval_df.index})
    eng.add_strategy(s); eng.run()
    return s


def main() -> None:
    cols, _train, eval_df, _d = prepare(DataConfig())
    from stable_baselines3 import PPO
    model = PPO.load(str(ROOT / "models" / "ppo_xauusd_raw"), device="cpu", custom_objects=CUSTOM)

    env_rows = run_env(cols, eval_df, model)
    s = run_nautilus(cols, eval_df, model)

    # ---- align actions by date ----
    env_by_date = {r["date"]: r for r in env_rows}
    naut_actions = {d: a for (d, a, _tp, _dc) in s.action_log}
    act_diffs = 0
    with open(OUT / "ENV_vs_NAUTILUS_ACTION_DIFF.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["date", "env_action", "nautilus_action", "match"])
        for d, r in env_by_date.items():
            na = naut_actions.get(d, "MISSING")
            match = (na == r["action"])
            if not match:
                act_diffs += 1
            w.writerow([d, r["action"], na, match])

    # ---- fill-price vs env decision/next close (THE timing test) ----
    price_by_date = {r["date"]: (r["decision_close"], r["next_close"]) for r in env_rows}
    lag_hits = same_bar = 0
    with open(OUT / "ENV_vs_NAUTILUS_EXECUTION_DIFF.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["decision_date", "side", "qty", "fill_px", "env_decision_close",
                    "env_next_close", "fill==decision?", "fill==next?"])
        for (fts, fpx, side, qty, dd, dc) in s.fills_log:
            dec, nxt = price_by_date.get(dd, (np.nan, np.nan))
            eq_dec = abs(fpx - dec) < 1e-6 if dec == dec else False
            eq_nxt = abs(fpx - nxt) < 1e-6 if nxt == nxt else False
            same_bar += int(eq_dec); lag_hits += int(eq_nxt)
            w.writerow([dd, side, qty, fpx, dec, nxt, eq_dec, eq_nxt])

    # ---- PnL parity (normalized equity curves) + first divergence ----
    env_eq = np.array([100000.0] + [r["env_equity"] * 100000.0 for r in env_rows])  # scale to $100k
    naut_eq = np.array([e for (_t, e) in s.equity_curve])
    m = min(len(env_eq), len(naut_eq))
    env_ret = env_eq[1:m] / env_eq[:m-1] - 1
    naut_ret = naut_eq[1:m] / naut_eq[:m-1] - 1
    first_div = None
    with open(OUT / "ENV_vs_NAUTILUS_PNL_DIFF.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["i", "date", "env_equity_norm", "naut_equity", "abs_diff"])
        for i in range(m - 1):
            d = env_rows[i]["date"] if i < len(env_rows) else ""
            diff = abs(env_eq[i] - naut_eq[i])
            if first_div is None and abs(env_ret[i] - naut_ret[i]) > 1e-4 and i > 0:
                first_div = (i, d, float(env_ret[i]), float(naut_ret[i]))
            w.writerow([i, d, round(float(env_eq[i]), 2), round(float(naut_eq[i]), 2), round(diff, 2)])

    print("=== PARITY SUMMARY ===")
    print(f"action mismatches: {act_diffs} / {len(env_by_date)}")
    print(f"fills: {len(s.fills_log)} | fill==decision_close (same-bar): {same_bar} | "
          f"fill==next_close (1-bar lag): {lag_hits}")
    print(f"first PnL divergence: {first_div}")
    print("CSVs written to forensics/: ACTION_DIFF, EXECUTION_DIFF, PNL_DIFF")


if __name__ == "__main__":
    main()
