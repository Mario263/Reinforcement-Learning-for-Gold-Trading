"""Processed-CSV loader + window slicing (framework-neutral). Single source.

CSV-ONLY (no fallback). 1H, Mon-Fri (5-day week), UTC. Ported from the verified RawPPO loader.
"""
from pathlib import Path
from typing import Optional

import pandas as pd

from methods.shared.config import CSV_PATH


def load_processed(csv_path: Optional[str] = None) -> pd.DataFrame:
    path = Path(csv_path or CSV_PATH)
    if not path.exists():
        raise FileNotFoundError(f"processed CSV not found: {path}")
    raw = pd.read_csv(path)
    cols = {c.lower(): c for c in raw.columns}
    dcol = next((cols[k] for k in ("timestamp", "datetime", "time", "date", "gmt time")
                 if k in cols), None)
    if dcol is None:
        raise ValueError(f"no datetime column in {list(raw.columns)}")
    rename = {dcol: "datetime"}
    for c in ("open", "high", "low", "close", "volume"):
        if c in cols:
            rename[cols[c]] = c
    raw = raw.rename(columns=rename)
    raw["datetime"] = pd.to_datetime(raw["datetime"], utc=True, errors="coerce")
    raw = raw.dropna(subset=["datetime", "open", "high", "low", "close"])
    for c in ("open", "high", "low", "close", "volume"):
        if c in raw.columns:
            raw[c] = pd.to_numeric(raw[c], errors="coerce")
    if "volume" not in raw.columns:
        raw["volume"] = 0.0
    raw = (raw.dropna(subset=["open", "high", "low", "close"])
              .sort_values("datetime").drop_duplicates("datetime").set_index("datetime"))
    df = raw[["open", "high", "low", "close", "volume"]]
    # resample to 1h, keep Mon-Fri, ffill sparse gaps
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    out = df.resample("1h").agg(agg).dropna(subset=["open", "high", "low", "close"], how="all")
    out = out[out.index.weekday < 5]
    out[["open", "high", "low", "close"]] = out[["open", "high", "low", "close"]].ffill()
    out["volume"] = out["volume"].fillna(0.0)
    return out.dropna(subset=["open", "high", "low", "close"])
