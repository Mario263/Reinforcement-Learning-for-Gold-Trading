"""528-bar causal rolling z-score (framework-neutral). Single source.

W = ZSCORE_WINDOW = 528 rolling BARS (1 bar = 1h ~= 1 month). Causal (trailing window incl. t),
per-feature, no global scaler, no look-ahead. Ported verbatim from the verified RawPPO version.
"""
import numpy as np
import pandas as pd

from methods.shared.config import ZSCORE_WINDOW


def rolling_zscore(df: pd.DataFrame, feature_cols, window: int = ZSCORE_WINDOW) -> pd.DataFrame:
    out = df.copy()
    for col in feature_cols:
        s = out[col].astype(float)
        mu = s.rolling(window, min_periods=window).mean()
        sigma = s.rolling(window, min_periods=window).std(ddof=0)
        out[col] = (s - mu) / sigma.replace(0.0, np.nan)
    out = out.dropna(subset=list(feature_cols)).copy()
    out[list(feature_cols)] = out[list(feature_cols)].replace([np.inf, -np.inf], 0.0)
    return out
