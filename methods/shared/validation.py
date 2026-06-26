"""Dataset / observation / window validation (framework-neutral). Fail loud, no hidden defaults."""
import numpy as np
import pandas as pd

from methods.shared.config import OBS_DIM


def profile(df: pd.DataFrame) -> dict:
    return {"rows": int(len(df)), "first": str(df.index.min()), "last": str(df.index.max()),
            "columns": list(df.columns),
            "duplicate_timestamp_count": int(df.index.duplicated().sum()),
            "nan_count": int(df.isna().sum().sum())}


def assert_windows(train_start, train_end, eval_start, eval_end):
    ts, te = pd.Timestamp(train_start), pd.Timestamp(train_end)
    es, ee = pd.Timestamp(eval_start), pd.Timestamp(eval_end)
    assert ts < te, f"train_start {ts} !< train_end {te}"
    assert es < ee, f"eval_start {es} !< eval_end {ee}"
    assert te <= es, f"train/eval overlap: train_end {te} > eval_start {es}"


def assert_obs(obs_df, feature_cols):
    assert len(feature_cols) == OBS_DIM, f"obs_dim {len(feature_cols)} != {OBS_DIM}"
    m = obs_df[feature_cols].to_numpy(float)
    assert m.shape[1] == OBS_DIM, f"obs matrix has {m.shape[1]} cols"
    assert not np.isnan(m).any(), "NaN in observation matrix after warmup"
    assert not np.isinf(m).any(), "inf in observation matrix"
    return {"obs_rows": int(m.shape[0]), "obs_dim": int(m.shape[1])}


def assert_fractions(long_frac, flat_frac, short_frac):
    s = long_frac + flat_frac + short_frac
    assert abs(s - 1.0) < 1e-6, f"position fractions sum {s} != 1"
    for f in (long_frac, flat_frac, short_frac):
        assert 0.0 <= f <= 1.0, f"fraction {f} out of [0,1]"
