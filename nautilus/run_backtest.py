"""Nautilus Trader backtest of the trained PPO Raw policy (inference only).

High-fidelity event-driven re-execution of the SAME policy on the SAME 621-day
window, using Nautilus primitives for instrument/venue/orders/fills/positions.
Observations are the precomputed eval-pipeline 22-vectors (bitwise-consistent).
Writes NAUTILUS_BACKTEST_REPORT.md and NAUTILUS_VS_ENV_REPORT.md.
"""
import json
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "nautilus"))

import numpy as np
import pandas as pd

# Data stack BEFORE torch (OpenMP-safe).
from rl_gold_trading.config import DataConfig, EnvConfig # type: ignore
from rl_gold_trading.run import prepare # type: ignore

STARTING_USD = 100_000.0
FEE = 0.00015  # commission 0.01% + spread 0.005% per fill (env-matched)


def signed_qty(side, qty):
    text = str(side).upper()
    if text in {"BUY", "ORDERSIDE.BUY", "1"} or text.endswith(".BUY"):
        return float(qty)
    if text in {"SELL", "ORDERSIDE.SELL", "2"} or text.endswith(".SELL"):
        return -float(qty)
    raise ValueError(f"Unknown order side: {side!r}")


def build_instrument():
    from nautilus_trader.model.currencies import USD, XAU # type: ignore 
    # pyrefly: ignore [missing-import]
    from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
    # pyrefly: ignore [missing-import]
    from nautilus_trader.model.instruments import CurrencyPair
    from nautilus_trader.model.objects import Price, Quantity # type: ignore

    iid = InstrumentId(Symbol("XAU/USD"), Venue("SIM"))
    return CurrencyPair(
        instrument_id=iid, raw_symbol=Symbol("XAU/USD"),
        base_currency=XAU, quote_currency=USD,
        price_precision=5, size_precision=0,
        price_increment=Price(1e-5, 5), size_increment=Quantity.from_int(1),
        lot_size=Quantity.from_int(1),
        max_quantity=Quantity.from_str("1000000000"), min_quantity=Quantity.from_int(1),
        max_price=None, min_price=None, max_notional=None, min_notional=None,
        margin_init=Decimal("0.50"), margin_maint=Decimal("0.50"), #changed to 50
        maker_fee=Decimal(str(FEE)), taker_fee=Decimal(str(FEE)),
        tick_scheme_name="FOREX_5DECIMAL", ts_event=0, ts_init=0,
    )


def build_data(instrument, eval_df):
    """Bars drive on_bar decisions; QuoteTicks (1ns later, bid=ask=raw price)
    provide a reliable market for market-order fills at price[t]. Spread is NOT
    in the quote (bid==ask) — it is carried in the 0.00015 per-fill fee, matching
    the env (no double-counting)."""
    from nautilus_trader.model.data import Bar, BarSpecification, BarType, QuoteTick # type: ignore
    from nautilus_trader.model.enums import AggregationSource, BarAggregation, PriceType # type: ignore
    from nautilus_trader.model.objects import Price, Quantity # type: ignore

    spec = BarSpecification(1, BarAggregation.DAY, PriceType.LAST)
    bar_type = BarType(instrument.id, spec, AggregationSource.EXTERNAL)
    pp = instrument.price_precision
    one = Quantity.from_int(1_000_000)
    bars, quotes = [], []
    for ts, row in eval_df.iterrows():
        ts_ns = int(pd.Timestamp(ts).value)
        px = Price(float(row["price"]), pp)
        vol = Quantity(int(max(1, row.get("volume", 1))), 0)
        # FILL-TIMING FIX: the quote (price[t]) must be the engine's current market
        # BEFORE on_bar(t) fires, so a market order submitted on bar t fills at
        # close[t] (the decision price), matching the env's MOC convention. Placing
        # the quote AFTER the bar (ts+1) caused fills at the STALE previous close
        # (price[t-1]) — proven by forensics/fill_offset.py (offset {-1: 85}).
        quotes.append(QuoteTick(instrument.id, px, px, one, one, ts_ns - 1, ts_ns - 1))
        bars.append(Bar(bar_type, px, px, px, px, vol, ts_ns, ts_ns))
    return bar_type, bars, quotes


def metrics_from_equity(eq, ppy=252):
    eq = np.asarray(eq, dtype=float)
    if len(eq) < 2:
        return {"n_periods": 0, "cumulative_return": 0.0, "cagr": 0.0,
                "sharpe": 0.0, "sortino": 0.0, "calmar": 0.0,
                "max_drawdown": 0.0, "min_equity": float(eq[0]) if len(eq) else 0.0,
                "nonpositive_periods": int((eq <= 0).sum())}
    rets = eq[1:] / eq[:-1] - 1.0
    n = len(rets)
    cum = eq[-1] / eq[0] - 1.0
    years = max(n / ppy, 1e-9)
    cagr = (eq[-1] / eq[0]) ** (1 / years) - 1.0 if eq[0] > 0 and eq[-1] > 0 else float("nan")
    sharpe = (rets.mean() / rets.std()) * np.sqrt(ppy) if n and rets.std() > 1e-12 else 0.0
    dn = rets[rets < 0]
    sortino = (rets.mean() / dn.std()) * np.sqrt(ppy) if dn.size and dn.std() > 1e-12 else 0.0
    peaks = np.maximum.accumulate(eq)
    maxdd = float((eq / peaks - 1.0).min()) if len(eq) else 0.0
    return {"n_periods": n, "cumulative_return": float(cum), "cagr": float(cagr),
            "sharpe": float(sharpe), "sortino": float(sortino),
            "calmar": float(cagr / abs(maxdd)) if maxdd < 0 else 0.0,
            "max_drawdown": maxdd, "min_equity": float(eq.min()),
            "nonpositive_periods": int((eq <= 0).sum())}


def main() -> None:
    data_cfg = DataConfig()
    cols, _train, eval_df, _daily = prepare(data_cfg)

    # torch import AFTER data prep
    from stable_baselines3 import PPO
    # custom_objects avoids deserializing the pickled training schedules
    # (lr/clip), which are not portable across Python versions and are unused
    # for inference. Weights load normally.
    model = PPO.load(
        str(ROOT / "models" / "ppo_xauusd_raw"), device="cpu",
        custom_objects={"learning_rate": 0.0, "lr_schedule": lambda _: 0.0,
                        "clip_range": lambda _: 0.2},
    )
    obs_map = {pd.Timestamp(idx).normalize(): eval_df.loc[idx, cols].to_numpy(dtype=np.float32)
               for idx in eval_df.index}

    from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig # type: ignore
    from nautilus_trader.backtest.models import MakerTakerFeeModel # type: ignore
    from nautilus_trader.config import LoggingConfig # type: ignore
    from nautilus_trader.model.currencies import USD # type: ignore
    from nautilus_trader.model.enums import AccountType, OmsType # type: ignore
    from nautilus_trader.model.identifiers import Venue # type: ignore
    from nautilus_trader.model.objects import Money # type: ignore
    from strategy import RLConfig, RLPolicyStrategy # type: ignore

    instrument = build_instrument()
    bar_type, bars, quotes = build_data(instrument, eval_df)

    engine = BacktestEngine(config=BacktestEngineConfig(
        trader_id="BACKTESTER-001", logging=LoggingConfig(log_level="ERROR")))
    engine.add_venue(
        venue=Venue("SIM"), oms_type=OmsType.NETTING, account_type=AccountType.MARGIN,
        # Leverage is raised ONLY so Nautilus margin checks never spuriously reject
        # an order; ACTUAL exposure is capped at 100% capital by the sizing rule
        # (units = floor(equity/price) => notional = equity). PnL is leverage-invariant.
        base_currency=USD, starting_balances=[Money(STARTING_USD, USD)],
        default_leverage=Decimal(2), fee_model=MakerTakerFeeModel(), bar_execution=False,
    )
    engine.add_instrument(instrument)
    engine.add_data(bars)
    engine.add_data(quotes)

    strat = RLPolicyStrategy(RLConfig(instrument_id=str(instrument.id), bar_type=str(bar_type)))
    strat.attach(model, obs_map)
    engine.add_strategy(strat)

    engine.run()
    print("DEBUG strat:", strat.dbg)
    print("DEBUG obs_map sample keys:", [str(k) for k in list(obs_map.keys())[:3]])

    # ---- equity curve: NET-LIQUIDATION (cash + mark-to-market), reconstructed
    # from the actual fills. balance_total() alone is cash-only and excludes
    # unrealized PnL on open positions, which distorts the intermediate curve. ----
    price = eval_df["price"].to_numpy(float)
    dates = [str(pd.Timestamp(i).date()) for i in eval_df.index]
    d2i = {d: i for i, d in enumerate(dates)}
    fills_by_i = {}
    for (fts, fpx, side, qty, _dd, _dc) in strat.fills_log:
        fi = d2i.get(str(pd.Timestamp(fts, tz="UTC").date()))
        if fi is not None:
            fills_by_i.setdefault(fi, []).append((fpx, signed_qty(side, qty)))
    cash, pos_units, eq = STARTING_USD, 0.0, []
    for i in range(len(price)):
        for (fpx, sq) in fills_by_i.get(i, []):
            cash -= sq * fpx                  # buy -> cash down; sell -> cash up
            cash -= abs(sq) * fpx * FEE       # per-fill fee (commission+spread)
            pos_units += sq
        eq.append(cash + pos_units * price[i])  # net liquidation value
    final_bal = float(eq[-1])
    nm = metrics_from_equity(eq)
    max_abs_pos = 0.0
    cash_audit, pos_audit = STARTING_USD, 0.0
    for i in range(len(price)):
        for (fpx, sq) in fills_by_i.get(i, []):
            cash_audit -= sq * fpx
            cash_audit -= abs(sq) * fpx * FEE
            pos_audit += sq
        max_abs_pos = max(max_abs_pos, abs(pos_audit))

    # ---- trade-level stats from positions report ----
    try:
        pos_rep = engine.trader.generate_positions_report()
    except Exception:
        pos_rep = pd.DataFrame()
    fills_rep = engine.trader.generate_order_fills_report()
    n_fills = int(len(fills_rep)) if fills_rep is not None else 0

    trade_stats = {"round_trips": 0, "win_rate": 0.0, "profit_factor": float("nan")}
    if pos_rep is not None and len(pos_rep) and "realized_pnl" in pos_rep.columns:
        pnl = pd.to_numeric(pos_rep["realized_pnl"].astype(str).str.replace(r"[^0-9eE.\-]", "", regex=True),
                            errors="coerce").dropna()
        closed = pnl[pnl != 0]
        if len(closed):
            wins = closed[closed > 0]; losses = closed[closed < 0]
            trade_stats = {
                "round_trips": int(len(closed)),
                "win_rate": float((closed > 0).mean()),
                "profit_factor": float(wins.sum() / abs(losses.sum())) if len(losses) else float("inf"),
            }

    out = {"nautilus": nm, "trade_stats": trade_stats, "n_fills": n_fills,
           "starting_usd": STARTING_USD, "final_usd": final_bal,
           "fee_per_fill": FEE, "n_bars": len(bars), "max_abs_position": max_abs_pos}
    (Path(__file__).resolve().parent / "nautilus_metrics.json").write_text(json.dumps(out, indent=2, default=str))
    print("NAUTILUS METRICS:", json.dumps(nm, indent=2))
    print("TRADE STATS:", trade_stats, "| fills:", n_fills,
          "| max |pos|:", round(max_abs_pos, 2), "| final $:", round(final_bal, 2))
    engine.dispose()


if __name__ == "__main__":
    main()
