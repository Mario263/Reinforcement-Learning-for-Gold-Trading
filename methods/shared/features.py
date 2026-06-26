"""22-feature builder (framework-neutral). Single source — both frameworks import this.

`ta` library, params fixed by the spec. Ported from the verified RawPPO implementation.
"""
from typing import List, Tuple

import pandas as pd
from ta.momentum import RSIIndicator, StochasticOscillator, WilliamsRIndicator
from ta.trend import CCIIndicator, EMAIndicator, MACD, SMAIndicator
from ta.volatility import AverageTrueRange, BollingerBands
from ta.volume import OnBalanceVolumeIndicator, VolumeWeightedAveragePrice

from methods.shared.config import FEATURE_ORDER


def add_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    out = df.copy()
    o, h, l, c, v = out["open"], out["high"], out["low"], out["close"], out["volume"]
    out["sma10"] = SMAIndicator(c, window=10).sma_indicator()
    out["sma20"] = SMAIndicator(c, window=20).sma_indicator()
    out["sma50"] = SMAIndicator(c, window=50).sma_indicator()
    out["ema12"] = EMAIndicator(c, window=12).ema_indicator()
    out["ema26"] = EMAIndicator(c, window=26).ema_indicator()
    macd = MACD(c, window_slow=26, window_fast=12, window_sign=9)
    out["macd_line"] = macd.macd()
    out["macd_signal"] = macd.macd_signal()
    out["rsi14"] = RSIIndicator(c, window=14).rsi()
    stoch = StochasticOscillator(high=h, low=l, close=c, window=14, smooth_window=3)
    out["stoch_k"] = stoch.stoch()
    out["stoch_d"] = stoch.stoch_signal()
    boll = BollingerBands(c, window=20, window_dev=2)
    out["boll_upper"] = boll.bollinger_hband()
    out["boll_lower"] = boll.bollinger_lband()
    out["atr14"] = AverageTrueRange(high=h, low=l, close=c, window=14).average_true_range()
    out["obv"] = OnBalanceVolumeIndicator(close=c, volume=v).on_balance_volume()
    out["vwap"] = VolumeWeightedAveragePrice(high=h, low=l, close=c, volume=v,
                                             window=14).volume_weighted_average_price()
    out["cci"] = CCIIndicator(high=h, low=l, close=c, window=20).cci()
    out["williams_r"] = WilliamsRIndicator(high=h, low=l, close=c, lbp=14).williams_r()
    out["price"] = out["close"]   # raw price path for P&L (NOT one of the 22 features)
    out = out.dropna(subset=FEATURE_ORDER).copy()
    return out, list(FEATURE_ORDER)
