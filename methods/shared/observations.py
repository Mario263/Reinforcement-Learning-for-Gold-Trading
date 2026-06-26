"""Observation construction (framework-neutral). Single source.

prepare(): OHLCV -> 22 features -> 528-bar causal z-score -> observation frame (22 cols + raw
`price`). Compute on the FULL series, then slice to a window (so train/eval share warmup). Both
frameworks build their 22-d observation from this identical pipeline.
"""
from typing import List, Optional, Tuple

import pandas as pd

from methods.shared.config import FEATURE_ORDER
from methods.shared.features import add_features
from methods.shared.normalization import rolling_zscore


def prepare(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    feat, cols = add_features(df)
    return rolling_zscore(feat, cols), cols


def prepare_window(df_full: pd.DataFrame, start: Optional[str] = None,
                   end: Optional[str] = None) -> Tuple[pd.DataFrame, List[str]]:
    """Prepare on the FULL frame, then slice the observation rows to [start, end]."""
    obs, cols = prepare(df_full)
    if start:
        obs = obs.loc[obs.index >= pd.Timestamp(start, tz="UTC")]
    if end:
        obs = obs.loc[obs.index <= pd.Timestamp(end, tz="UTC")]
    return obs, cols
