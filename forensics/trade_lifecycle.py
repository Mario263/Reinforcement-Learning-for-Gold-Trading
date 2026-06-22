"""Phase 1-4: full trade-lifecycle + position-sizing + accounting audit.

Runs the Nautilus backtest, then reconstructs per-fill: running position, cash,
net-liquidation equity, notional, and LEVERAGE (notional/equity). Flags any
leverage breach (>1x) or negative equity — the signatures of the -$1.9M blow-up.
Writes outputs/trade_lifecycle_audit.csv. Inference only.
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "nautilus"))
OUT = Path(__file__).resolve().parent / "outputs"; OUT.mkdir(exist_ok=True)
import numpy as np, pandas as pd
from rl_gold_trading.config import DataConfig
from rl_gold_trading.run import prepare

CUSTOM = {"learning_rate": 0.0, "lr_schedule": lambda _: 0.0, "clip_range": lambda _: 0.2}
START = 100000.0
FEE = 0.00015


def signed_qty(side, qty):
    text = str(side).upper()
    if text in {"BUY", "ORDERSIDE.BUY", "1"} or text.endswith(".BUY"):
        return float(qty)
    if text in {"SELL", "ORDERSIDE.SELL", "2"} or text.endswith(".SELL"):
        return -float(qty)
    raise ValueError(f"Unknown order side: {side!r}")


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
    inst = rb.build_instrument(); bt, bars, quotes = rb.build_data(inst, eval_df)
    eng = BacktestEngine(config=BacktestEngineConfig(trader_id="LIFE-001", logging=LoggingConfig(log_level="ERROR")))
    eng.add_venue(venue=Venue("SIM"), oms_type=OmsType.NETTING, account_type=AccountType.MARGIN, base_currency=USD,
                  starting_balances=[Money(START, USD)], default_leverage=Decimal(2),
                  fee_model=MakerTakerFeeModel(), bar_execution=False)
    eng.add_instrument(inst); eng.add_data(bars); eng.add_data(quotes)
    s = RLPolicyStrategy(RLConfig(instrument_id=str(inst.id), bar_type=str(bt)))
    s.attach(model, {pd.Timestamp(i).normalize(): eval_df.loc[i, cols].to_numpy(np.float32) for i in eval_df.index})
    eng.add_strategy(s); eng.run()

    price = eval_df["price"].to_numpy(float)
    dates = [str(pd.Timestamp(i).date()) for i in eval_df.index]
    d2i = {d: i for i, d in enumerate(dates)}
    fills_by_i = {}
    for (fts, fpx, side, qty, _dd, _dc) in s.fills_log:
        fi = d2i.get(str(pd.Timestamp(fts, tz="UTC").date()))
        if fi is not None:
            fills_by_i.setdefault(fi, []).append((fpx, signed_qty(side, qty), side))

    cash, pos = START, 0.0
    rows = []
    max_lev = 0.0; min_eq = START; n_breach = 0; n_neg = 0; max_abs_pos = 0.0
    for i in range(len(price)):
        cash_before, pos_before = cash, pos
        for (fpx, sq, side) in fills_by_i.get(i, []):
            cash -= sq * fpx
            cash -= abs(sq) * fpx * FEE
            pos += sq
        eq = cash + pos * price[i]
        notional = abs(pos) * price[i]
        lev = notional / eq if eq > 0 else float("inf")
        max_lev = max(max_lev, lev if eq > 0 else 999)
        min_eq = min(min_eq, eq); max_abs_pos = max(max_abs_pos, abs(pos))
        if eq > 0 and lev > 1.01:
            n_breach += 1
        if eq < 0:
            n_neg += 1
        if i in fills_by_i:
            rows.append([dates[i], fills_by_i[i][0][2], round(pos_before, 1), round(pos, 1),
                         round(price[i], 2), round(cash, 2), round(eq, 2),
                         round(notional, 2), round(lev, 3)])

    with open(OUT / "trade_lifecycle_audit.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "side", "pos_before", "pos_after", "price", "cash", "net_liq_equity",
                    "notional", "leverage"])
        w.writerows(rows)

    print("=== LIFECYCLE / SIZING / ACCOUNTING AUDIT ===")
    print(f"fills: {len(s.fills_log)} | max |position| (units): {max_abs_pos:.0f}")
    print(f"max leverage (notional/equity): {max_lev:.2f}x   (1.0 = env's 100%-capital, no leverage)")
    print(f"min net-liq equity: ${min_eq:,.0f}   | bars with equity<0: {n_neg}   | bars with leverage>1.01: {n_breach}")
    print(f"final net-liq equity: ${(cash + pos*price[-1]):,.0f}")
    print("CSV: forensics/outputs/trade_lifecycle_audit.csv")


if __name__ == "__main__":
    main()
