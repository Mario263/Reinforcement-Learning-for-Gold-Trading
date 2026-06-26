"""Merge per-year Dukascopy 1H CSVs into one sorted, deduped file under data/processed/.

  python scripts/merge_dukascopy_years.py
Reads data/raw/dukascopy/XAUUSD/1H/<year>/xauusd_h1_<year>.csv (never mutates raw),
writes data/processed/xauusd_1h_2003_2026.csv. Both RawPPO and NautilusPPO read this file.
"""
import glob
from pathlib import Path

import pandas as pd

RAW = Path("data/raw/dukascopy/XAUUSD/1H")
OUT = Path("data/processed/xauusd_1h_2003_2026.csv")


def main():
    files = sorted(glob.glob(str(RAW / "*" / "xauusd_h1_*.csv")))
    files = [f for f in files if "chunks" not in f]
    if not files:
        raise SystemExit(f"no per-year files under {RAW}")
    df = pd.concat((pd.read_csv(f) for f in files), ignore_index=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = (df.dropna(subset=["timestamp", "open", "high", "low", "close"])
            .sort_values("timestamp").drop_duplicates("timestamp"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"merged {len(files)} files -> {OUT}")
    print(f"rows={len(df)}  range={df['timestamp'].min()} .. {df['timestamp'].max()}")


if __name__ == "__main__":
    main()
