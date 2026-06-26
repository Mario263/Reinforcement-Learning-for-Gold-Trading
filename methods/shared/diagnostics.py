"""Diagnostic utilities (framework-neutral): metric formulas, obs hashing, synthetic series.

`compute_metrics` is the neutral metric MATH (Sharpe/Sortino/etc.) fed by each framework's own
equity/positions — RawPPO from its ledger, NautilusPPO from Nautilus state. It does NOT compute
accounting; it only turns an equity/position series into metrics.
"""
import hashlib
from typing import Dict, Sequence

import numpy as np

from methods.shared.config import PERIODS_PER_YEAR


def obs_hash(obs) -> str:
    return hashlib.sha1(np.asarray(obs, dtype=np.float64).tobytes()).hexdigest()[:16]


def compute_metrics(net_rets: Sequence[float], equity: Sequence[float],
                    positions: Sequence[int],
                    periods_per_year: int = PERIODS_PER_YEAR) -> Dict[str, float]:
    net_rets = np.asarray(net_rets, float)
    equity = np.asarray(equity, float)            # length n+1 (incl. starting equity)
    n = len(net_rets)
    if n == 0 or len(equity) < 2:
        return {"n_periods": 0}
    cum = equity[-1] / equity[0] - 1.0
    years = max(n / periods_per_year, 1e-9)
    cagr = (equity[-1] / equity[0]) ** (1.0 / years) - 1.0
    std = net_rets.std(ddof=0)
    sharpe = (net_rets.mean() / std) * np.sqrt(periods_per_year) if std > 1e-12 else 0.0
    dn = net_rets[net_rets < 0]
    dstd = dn.std(ddof=0) if dn.size else 0.0
    sortino = (net_rets.mean() / dstd) * np.sqrt(periods_per_year) if dstd > 1e-12 else 0.0
    peaks = np.maximum.accumulate(equity)
    max_dd = float((equity / peaks - 1.0).min())
    calmar = (cagr / abs(max_dd)) if max_dd < 0 else 0.0
    recovery = (cum / abs(max_dd)) if max_dd < 0 else 0.0
    pos = np.asarray(positions)
    in_mkt = pos != 0
    turn = int(np.sum(np.abs(np.diff(np.concatenate([[0], pos])))))
    # per-trade win rate (constant non-zero runs)
    trs, cur, ei = [], 0, None
    for t in range(n):
        d = int(pos[t])
        if d != cur:
            if cur != 0 and ei is not None:
                trs.append(equity[t] / equity[ei] - 1.0)
            ei = t if d != 0 else None
            cur = d
    if cur != 0 and ei is not None:
        trs.append(equity[n] / equity[ei] - 1.0)
    trs = np.asarray(trs, float)
    rt = int(len(trs))
    wins, losses = trs[trs > 0].sum(), -trs[trs < 0].sum()
    return {
        "n_periods": int(n), "cumulative_return": float(cum), "cagr": float(cagr),
        "sharpe": float(sharpe), "sortino": float(sortino), "calmar": float(calmar),
        "recovery_factor": float(recovery), "max_drawdown": max_dd,
        "volatility": float(std * np.sqrt(periods_per_year)),
        "var_95": float(np.percentile(net_rets, 5)), "final_equity": float(equity[-1]),
        "total_turnover": turn, "round_trips": rt,
        "win_rate_all_periods": float((net_rets > 0).mean()),
        "win_rate_in_market": float((net_rets[in_mkt] > 0).mean()) if in_mkt.any() else 0.0,
        "trade_win_rate_round_trips": float((trs > 0).mean()) if rt else 0.0,
        "profit_factor": float(wins / losses) if losses > 1e-12 else 0.0,
        "long_frac": float((pos == 1).mean()), "flat_frac": float((pos == 0).mean()),
        "short_frac": float((pos == -1).mean()),
    }
