"""Raw OHLCV DataFrame -> Nautilus Bars (post-warmup timestamps, aligned 1:1 with observations)."""
import pandas as pd
from nautilus_trader.persistence.wranglers import BarDataWrangler


def df_to_bars(df: pd.DataFrame, bar_type, instrument):
    data = df[["open", "high", "low", "close", "volume"]].copy()
    return BarDataWrangler(bar_type, instrument).process(data)
