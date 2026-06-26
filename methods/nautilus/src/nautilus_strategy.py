"""Bridge strategy: SB3 (pull) drives a Nautilus backtest (push) via two queues.

Nautilus owns fills/positions/cash/PnL. Each bar: report Nautilus state on obs_q, block on act_q,
then map action -> target direction and submit a market order on a direction change only.
"""
from queue import Queue

from nautilus_trader.model.currencies import USD
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.objects import Quantity
from nautilus_trader.trading.strategy import Strategy

from methods.shared.actions import action_to_target

STOP = "__STOP__"


class BridgeStrategy(Strategy):
    def __init__(self, bar_type, instrument, venue, obs_q: Queue, act_q: Queue, deploy_frac: float):
        super().__init__()
        self.bt = bar_type
        self.instrument_id = instrument.id
        self.venue = venue
        self.obs_q, self.act_q = obs_q, act_q
        self.deploy_frac = float(deploy_frac)
        self._i, self._pending_notional, self._aborted = -1, 0.0, False

    def on_start(self):
        self.subscribe_bars(self.bt)

    def on_order_filled(self, event):
        self._pending_notional += float(event.last_qty) * float(event.last_px)

    def _equity(self) -> float:
        cash = self.portfolio.account(self.venue).balance_total(USD).as_double()
        up = self.portfolio.unrealized_pnl(self.instrument_id)
        return cash + (up.as_double() if up is not None else 0.0)

    def _net_dir(self) -> int:
        net = float(self.portfolio.net_position(self.instrument_id))
        return 1 if net > 0 else (-1 if net < 0 else 0)

    def on_bar(self, bar):
        self._i += 1
        if self._aborted:
            return
        price = float(bar.close)
        self.obs_q.put({"index": self._i, "equity": self._equity(), "dir": self._net_dir(),
                        "traded_notional": self._pending_notional, "price": price})
        self._pending_notional = 0.0
        action = self.act_q.get()
        if action == STOP:
            self._aborted = True
            return
        target_dir = action_to_target(action)
        cur_dir = self._net_dir()
        if target_dir != cur_dir:
            equity = self._equity()
            target_oz = int(target_dir * int(self.deploy_frac * equity / price))
            cur_oz = int(float(self.portfolio.net_position(self.instrument_id)))
            delta = target_oz - cur_oz
            if delta != 0:
                side = OrderSide.BUY if delta > 0 else OrderSide.SELL
                self.submit_order(self.order_factory.market(
                    self.instrument_id, side, Quantity.from_int(abs(delta))))
