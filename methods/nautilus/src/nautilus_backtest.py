"""Nautilus instrument + venue + engine factory. Nautilus owns execution/accounting.

XAU/USD via default_fx_ccy (qty = oz, min lot 1000, integer), NETTING + MARGIN, USD. Bars MUST be
LAST price type (BID -> 'no market', verified).
"""
from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.config import LoggingConfig
from nautilus_trader.model.currencies import USD
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import AccountType, OmsType
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.model.objects import Money
from nautilus_trader.test_kit.providers import TestInstrumentProvider

from methods.shared.config import NAUT_BAR_SPEC, NAUT_STARTING_CASH, NAUT_SYMBOL, NAUT_VENUE


def make_instrument():
    return TestInstrumentProvider.default_fx_ccy(NAUT_SYMBOL, venue=Venue(NAUT_VENUE))


def bar_type(instrument) -> BarType:
    return BarType.from_str(f"{instrument.id}-{NAUT_BAR_SPEC}")


def new_engine(instrument, starting_cash: float = NAUT_STARTING_CASH) -> BacktestEngine:
    eng = BacktestEngine(BacktestEngineConfig(
        trader_id="NAUTPPO-001", logging=LoggingConfig(bypass_logging=True)))
    eng.add_venue(Venue(NAUT_VENUE), OmsType.NETTING, AccountType.MARGIN,
                  starting_balances=[Money(starting_cash, USD)], base_currency=USD)
    eng.add_instrument(instrument)
    return eng
