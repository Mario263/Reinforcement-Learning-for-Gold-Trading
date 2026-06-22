"""Reconstruct Nautilus net-liquidation equity from ACTUAL fills, to separate
a measurement artifact (cash-only equity) from a real fill-timing loss.

Builds position+cash from the fills, marks to market each bar (cash + pos*price),
and reports metrics. Also reports, per fill, whether the fill price equals the
SAME-bar close, the NEXT-bar close, or neither. Inference only.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "nautilus"))
import numpy as np
import pandas as pd

from rl_gold_trading.config import DataConfig, EnvConfig
from rl_gold_trading.run import prepare

CUSTOM = {"learning_rate": 0.0, "lr_schedule": lambda _: 0.0, "clip_range": lambda _: 0.2}
FEE = 0.00015
START = 100000.0


def signed_qty(side, qty):
    text = str(side).upper()
    if text in {"BUY", "ORDERSIDE.BUY", "1"} or text.endswith(".BUY"):
        return float(qty)
    if text in {"SELL", "ORDERSIDE.SELL", "2"} or text.endswith(".SELL"):
        return -float(qty)
    raise ValueError(f"Unknown order side: {side!r}")


def metrics(eq, ppy=252):
    eq = np.asarray(eq, float)
    r = eq[1:] / eq[:-1] - 1
    cum = eq[-1] / eq[0] - 1
    sharpe = (r.mean() / r.std()) * np.sqrt(ppy) if r.std() > 1e-12 else 0.0
    dd = float((eq / np.maximum.accumulate(eq) - 1).min())
    return cum, sharpe, dd


def main() -> None:
    cols, _t, eval_df, _d = prepare(DataConfig())
    from stable_baselines3 import PPO
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

    model = PPO.load(str(ROOT / "models" / "ppo_xauusd_raw"), device="cpu", custom_objects=CUSTOM)
    inst = rb.build_instrument()
    bar_type, bars, quotes = rb.build_data(inst, eval_df)
    eng = BacktestEngine(config=BacktestEngineConfig(trader_id="RC-001",
                         logging=LoggingConfig(log_level="ERROR")))
    eng.add_venue(venue=Venue("SIM"), oms_type=OmsType.NETTING, account_type=AccountType.MARGIN,
                  base_currency=USD, starting_balances=[Money(START, USD)],
                  default_leverage=Decimal(2), fee_model=MakerTakerFeeModel(), bar_execution=False)
    eng.add_instrument(inst); eng.add_data(bars); eng.add_data(quotes)
    s = RLPolicyStrategy(RLConfig(instrument_id=str(inst.id), bar_type=str(bar_type)))
    s.attach(model, {pd.Timestamp(i).normalize(): eval_df.loc[i, cols].to_numpy(np.float32)
                     for i in eval_df.index})
    eng.add_strategy(s); eng.run()

    price = eval_df["price"].to_numpy(float)
    dates = [str(pd.Timestamp(i).date()) for i in eval_df.index]
    date_to_i = {d: i for i, d in enumerate(dates)}

    # fills -> by bar date (using actual fill ts)
    fills = []
    for (fts, fpx, side, qty, _dd, _dc) in s.fills_log:
        fdate = str(pd.Timestamp(fts, tz="UTC").date())
        fills.append((date_to_i.get(fdate, -1), fpx, signed_qty(side, qty)))

    # fill price vs same-bar / next-bar close
    same = nxt = neither = 0
    for (i, fpx, _q) in fills:
        if i < 0:
            continue
        if abs(fpx - price[i]) < 1e-6:
            same += 1
        elif i + 1 < len(price) and abs(fpx - price[i + 1]) < 1e-6:
            nxt += 1
        else:
            neither += 1

    # reconstruct cash + position, mark-to-market net-liq each bar
    cash, pos = START, 0.0
    fills_by_i = {}
    for (i, fpx, sq) in fills:
        fills_by_i.setdefault(i, []).append((fpx, sq))
    netliq = []
    for i in range(len(price)):
        for (fpx, sq) in fills_by_i.get(i, []):
            cash -= sq * fpx                 # buy: cash down; sell: cash up
            cash -= abs(sq) * fpx * FEE      # fee
            pos += sq
        netliq.append(cash + pos * price[i])

    # env equity (geometric, marks every bar)
    from rl_gold_trading.envs import XAUUSDTradingEnv
    env = XAUUSDTradingEnv(eval_df, cols, EnvConfig(), random_reset=False)
    obs, _ = env.reset(); env_eq = [START]; done = False
    while not done:
        a, _ = model.predict(obs, deterministic=True)
        obs, _r, term, trunc, info = env.step(int(a))
        env_eq.append(info["equity"] * START)
        done = term or trunc

    ec, es, ed = metrics(env_eq)
    nc, ns, nd = metrics(netliq)
    cash_eq = [e for (_t, e) in s.equity_curve]
    cc, cs, cd = metrics(cash_eq)

    print("fills:", len(fills), "| fill==same-bar:", same, "| fill==next-bar:", nxt, "| neither:", neither)
    print(f"ENV (mark-to-market)          cum={ec:+.4f} sharpe={es:+.2f} maxDD={ed:+.4f}")
    print(f"NAUTILUS cash-only (reported) cum={cc:+.4f} sharpe={cs:+.2f} maxDD={cd:+.4f}")
    print(f"NAUTILUS net-liq (reconstr.)  cum={nc:+.4f} sharpe={ns:+.2f} maxDD={nd:+.4f}")


if __name__ == "__main__":
    main()
