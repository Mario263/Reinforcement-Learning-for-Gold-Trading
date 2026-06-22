import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "nautilus"))
import numpy as np, pandas as pd
from rl_gold_trading.config import DataConfig
from rl_gold_trading.run import prepare
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

CUSTOM = {"learning_rate": 0.0, "lr_schedule": lambda _: 0.0, "clip_range": lambda _: 0.2}
model = PPO.load(str(ROOT / "models" / "ppo_xauusd_raw"), device="cpu", custom_objects=CUSTOM)
inst = rb.build_instrument(); bt, bars, quotes = rb.build_data(inst, eval_df)
eng = BacktestEngine(config=BacktestEngineConfig(trader_id="DBG-001", logging=LoggingConfig(log_level="ERROR")))
eng.add_venue(venue=Venue("SIM"), oms_type=OmsType.NETTING, account_type=AccountType.MARGIN, base_currency=USD,
              starting_balances=[Money(100000, USD)], default_leverage=Decimal(2),
              fee_model=MakerTakerFeeModel(), bar_execution=False)
eng.add_instrument(inst); eng.add_data(bars); eng.add_data(quotes)
s = RLPolicyStrategy(RLConfig(instrument_id=str(inst.id), bar_type=str(bt)))
s.attach(model, {pd.Timestamp(i).normalize(): eval_df.loc[i, cols].to_numpy(np.float32) for i in eval_df.index})
eng.add_strategy(s); eng.run()

price = eval_df["price"].to_numpy(float); dates = [str(pd.Timestamp(i).date()) for i in eval_df.index]
d2i = {d: i for i, d in enumerate(dates)}; pr = np.round(price, 2)
off = {}
for (fts, fpx, side, qty, _dd, _dc) in s.fills_log:
    fi = d2i.get(str(pd.Timestamp(fts, tz="UTC").date()), -1)
    js = np.where(np.abs(pr - round(fpx, 2)) < 0.005)[0]
    if len(js):
        j = js[np.argmin(np.abs(js - fi))]; off[int(j - fi)] = off.get(int(j - fi), 0) + 1
    else:
        off["nomatch"] = off.get("nomatch", 0) + 1
print("fill bar-offset (price_bar - fill_date) hist:", dict(sorted(off.items(), key=lambda x: str(x[0]))))
print("first 6 fills (fill_date, px):", [(str(pd.Timestamp(f[0], tz="UTC").date()), round(f[1], 2)) for f in s.fills_log[:6]])
print("first 8 closes:", [(dates[i], round(price[i], 2)) for i in range(8)])
