"""Phase-4 forensic rollout (NO retraining; inference only).

Reproduces the EXACT evaluation pipeline (rl_gold_trading.run.prepare + the same
XAUUSDTradingEnv deterministic rollout used by metrics.evaluate_model), records
every per-step quantity, and derives all audit numbers DIRECTLY from the
generated trades. Output: forensics/forensic_dump.json (+ console summary).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import numpy as np

from rl_gold_trading.config import DataConfig, EnvConfig
from rl_gold_trading.run import prepare


def main() -> None:
    data_cfg = DataConfig()
    env_cfg = EnvConfig()
    cols, _train, eval_df, _daily = prepare(data_cfg)

    # torch-dependent imports AFTER data prep (OpenMP-safe order).
    from stable_baselines3 import PPO
    from rl_gold_trading.envs import XAUUSDTradingEnv

    model = PPO.load(
        str(ROOT / "models" / "ppo_xauusd_raw"), device="cpu",
        custom_objects={"learning_rate": 0.0, "lr_schedule": lambda _: 0.0,
                        "clip_range": lambda _: 0.2},
    )
    env = XAUUSDTradingEnv(eval_df, cols, env_cfg, random_reset=False)

    obs, _ = env.reset()
    dates = [d for d in eval_df.index]
    rec = {k: [] for k in ["action", "position", "prev_position", "price",
                           "price_ret", "r_port", "cost", "net_ret", "equity", "drawdown"]}
    equity_path = [env.equity]
    prev_pos = 0
    done = False
    step = 0
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        action = int(action)
        p0 = env.prices[env.t]
        obs, _r, term, trunc, info = env.step(action)
        rec["action"].append(action)
        rec["position"].append(info["position"])
        rec["prev_position"].append(prev_pos)
        rec["price"].append(float(p0))
        # recompute price_ret/r_port for transparency (matches env math)
        p1 = env.prices[min(env.t, env.n - 1)]
        pr = (p1 / p0 - 1.0) if p0 != 0 else 0.0
        rec["price_ret"].append(float(pr))
        rec["r_port"].append(float(info["position"] * pr))
        rec["cost"].append(float(info["cost"]))
        rec["net_ret"].append(float(info["net_ret"]))
        rec["equity"].append(float(info["equity"]))
        rec["drawdown"].append(float(info["drawdown"]))
        equity_path.append(float(info["equity"]))
        prev_pos = info["position"]
        step += 1
        done = term or trunc

    pos = np.array(rec["position"])
    prevp = np.array(rec["prev_position"])
    act = np.array(rec["action"])
    net = np.array(rec["net_ret"], dtype=float)
    equity = np.array(equity_path, dtype=float)  # len n+1
    n = len(pos)

    # ---- Action distribution (raw policy outputs) ----
    action_dist = {f"action_{a}": int((act == a).sum()) for a in (0, 1, 2)}
    # mapping: 0->sell(-1), 1->hold(0), 2->buy(+1)

    # ---- Position distribution (resulting positions) ----
    long_days = int((pos == 1).sum()); flat_days = int((pos == 0).sum()); short_days = int((pos == -1).sum())

    # ---- Win-rate denominators ----
    wins_all = int((net > 0).sum())
    in_market = pos != 0
    wins_active = int((net[in_market] > 0).sum())
    win_rate_all = wins_all / n
    win_rate_active = wins_active / int(in_market.sum()) if in_market.any() else 0.0

    # ---- Trade forensics (position-change events) ----
    changed = pos != prevp
    pos_change_events = int(changed.sum())
    entries = int(((prevp == 0) & (pos != 0)).sum())
    exits = int(((prevp != 0) & (pos == 0)).sum())
    flips = int(((prevp != 0) & (pos != 0) & (pos != prevp)).sum())
    long_entries = int(((prevp == 0) & (pos == 1)).sum())
    short_entries = int(((prevp == 0) & (pos == -1)).sum())
    turnover_units = int(np.abs(pos - prevp).sum())

    # ---- Round trips + per-trade P&L via equity (entry->exit), incl. costs ----
    trades = []  # each: (entry_step, exit_step, direction, ret)
    cur_dir = 0
    entry_idx = None
    for t in range(n):
        d = pos[t]
        if d != cur_dir:
            # close previous open trade at boundary (equity index t = before step t)
            if cur_dir != 0 and entry_idx is not None:
                ret = equity[t] / equity[entry_idx] - 1.0
                trades.append({"entry": entry_idx, "exit": t, "dir": int(cur_dir), "ret": float(ret)})
            # open new trade if direction nonzero
            if d != 0:
                entry_idx = t            # equity index just before holding starts
            else:
                entry_idx = None
            cur_dir = d
    # close trailing open trade at series end
    if cur_dir != 0 and entry_idx is not None:
        ret = equity[n] / equity[entry_idx] - 1.0
        trades.append({"entry": entry_idx, "exit": n, "dir": int(cur_dir), "ret": float(ret)})

    round_trips = len(trades)
    trade_rets = np.array([tr["ret"] for tr in trades], dtype=float)
    trade_win_rate = float((trade_rets > 0).mean()) if round_trips else 0.0
    gross_win = float(trade_rets[trade_rets > 0].sum()) if round_trips else 0.0
    gross_loss = float(-trade_rets[trade_rets < 0].sum()) if round_trips else 0.0
    profit_factor = (gross_win / gross_loss) if gross_loss > 1e-12 else float("inf")

    # ---- Holding-duration runs (maximal constant-position runs) ----
    def runs(values):
        out = []
        if len(values) == 0:
            return out
        cur = values[0]; length = 1
        for v in values[1:]:
            if v == cur:
                length += 1
            else:
                out.append((int(cur), int(length))); cur = v; length = 1
        out.append((int(cur), int(length)))
        return out

    rr = runs(pos.tolist())
    hold_runs = [L for (v, L) in rr if v == 0]
    long_runs = [L for (v, L) in rr if v == 1]
    short_runs = [L for (v, L) in rr if v == -1]
    inmarket_runs = [L for (v, L) in rr if v != 0]

    def stats(x):
        return {"count": len(x), "avg": float(np.mean(x)) if x else 0.0,
                "max": int(max(x)) if x else 0, "min": int(min(x)) if x else 0}

    exposure = float(in_market.mean())

    dump = {
        "n_periods": n,
        "date_range": [str(dates[0].date()), str(dates[-1].date())],
        "action_distribution": action_dist,
        "position_days": {"long": long_days, "flat": flat_days, "short": short_days},
        "exposure_fraction": exposure,
        "win_rate": {
            "wins_all": wins_all, "total_periods": n, "win_rate_all": win_rate_all,
            "wins_active": wins_active, "active_periods": int(in_market.sum()),
            "win_rate_active": win_rate_active,
            "trade_win_rate": trade_win_rate, "round_trips": round_trips,
        },
        "trade_forensics": {
            "position_change_events": pos_change_events, "turnover_units": turnover_units,
            "entries": entries, "exits": exits, "flips": flips,
            "long_entries": long_entries, "short_entries": short_entries,
            "round_trips": round_trips,
        },
        "profit_factor": profit_factor,
        "holding_durations": {
            "hold_flat_runs": stats(hold_runs), "long_runs": stats(long_runs),
            "short_runs": stats(short_runs), "in_market_runs": stats(inmarket_runs),
        },
        "trades": trades,
        "final_equity": float(equity[-1]),
        "cumulative_return": float(equity[-1] / equity[0] - 1.0),
    }
    out_dir = Path(__file__).resolve().parent / "outputs"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "forensic_dump.json"
    out_path.write_text(json.dumps(dump, indent=2))

    # console summary
    print("date range:", dump["date_range"], "| periods:", n)
    print("action dist (0=sell,1=hold,2=buy):", action_dist)
    print("position days L/F/S:", long_days, flat_days, short_days, "| exposure:", round(exposure, 4))
    print(f"win_rate_all = {wins_all}/{n} = {win_rate_all:.4f}")
    print(f"win_rate_active = {wins_active}/{int(in_market.sum())} = {win_rate_active:.4f}")
    print(f"trade_win_rate = {(trade_rets>0).sum()}/{round_trips} = {trade_win_rate:.4f}")
    print("trade forensics:", dump["trade_forensics"])
    print("profit_factor:", profit_factor)
    print("holding runs:", {k: dump["holding_durations"][k] for k in dump["holding_durations"]})
    print("saved:", out_path)


if __name__ == "__main__":
    main()
