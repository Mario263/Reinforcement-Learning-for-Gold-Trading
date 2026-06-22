"""Configuration for the PPO RAW baseline reproduction.

All values traced to Kili et al., "Kalman-Enhanced Deep Reinforcement Learning
for Noise-Resilient Algorithmic Trading in Volatile Gold Markets", IJACSA 16(11),
2025. PDF page numbers are cited per field. This reproduces ONLY the
"PPO without Kalman filtering" (PPO Raw) baseline. NO Kalman / DQN / RPPO.

See ../researchPaper/PPO_RAW_GROUND_TRUTH.md and PPO_PAPER_CONFORMANCE_CHECKLIST.md.
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DataConfig:
    """Paper Section IV.A (PDF p.5-6)."""
    csv_path: Optional[str] = None
    hf_dataset: str = "ZombitX64/xauusd-gold-price-historical-data-2004-2025"
    # XAU/USD, Jan 2017 -> Jan 2025 (p.5), resampled to DAILY (p.6).
    start: str = "2017-01-01"
    end: str = "2025-02-01"          # exclusive upper bound (covers Jan 2025)
    resample_rule: str = "1D"         # "re-sampled to daily frequency" (p.6)
    # Temporal split: 70% train (2017->Dec 2022), 30% test (2023->Jan 2025) (p.6).
    train_end: str = "2022-12-31"
    test_start: str = "2023-01-01"
    # Reported metrics use the 621-day window Jan 2 2023 -> Sep 12 2024 (p.6, p.9).
    eval_start: str = "2023-01-02"
    eval_end: str = "2024-09-12"


@dataclass
class EnvConfig:
    """Paper Section IV.E / IV.F (PDF p.7-8)."""
    initial_capital: float = 1.0      # normalized equity (return-based)
    # Action {-1,0,+1}, 100% capital deployment (p.7).
    # Transaction costs (commission + spread only, per project decision) (p.7).
    commission: float = 0.0001        # 0.01% of transaction value
    spread: float = 0.00005           # 0.005% bid-ask spread
    # Eq.22 reward weights (Bayesian-optimized on validation) (p.8):
    alpha: float = 1.0                # return focus
    beta: float = 2.0                 # drawdown penalty
    gamma: float = 0.5                # transaction cost penalty
    delta: float = 0.1                # stability (penalizes position changes)


@dataclass
class TrainConfig:
    """Paper Section IV.G.2 / IV.H (PDF p.9)."""
    total_timesteps: int = 500_000    # p.9
    learning_rate: float = 3e-4       # 3e-4 with linear decay to zero (p.9)
    lr_linear_decay: bool = True
    n_steps: int = 2048               # rollout length (p.9)
    batch_size: int = 256             # minibatch (p.9)
    n_epochs: int = 10                # epochs per rollout (p.9)
    gamma: float = 0.99               # MDP discount (p.4)
    gae_lambda: float = 0.95          # GAE (p.9)
    clip_range: float = 0.2           # clip ratio (p.9)
    ent_coef: float = 0.01            # entropy coeff c2 (p.9)
    vf_coef: float = 0.5              # value coeff c1 (p.9)
    max_grad_norm: float = 0.5
    net_arch: List[int] = field(default_factory=lambda: [512, 512, 256, 128])  # p.9
    seed: int = 42
    save_dir: str = "models"


# Paper Section IV.B / IV.E (PDF p.6-7): state = 5 OHLCV + 17 indicators = 22.
# The paper enumerates 15 indicators (p.6) but specifies "17 dimensions" (p.7);
# the 2 unspecified indicators are taken as MACD line + signal (documented
# assumption; MACD is referenced on p.2). See PPO_RAW_GROUND_TRUTH.md sec.2.
FEATURE_ORDER: List[str] = [
    "open", "high", "low", "close", "volume",           # 5 raw OHLCV
    "sma10", "sma20", "sma50",                            # trend SMAs
    "ema12", "ema26",                                     # trend EMAs
    "macd_line", "macd_signal",                           # MACD (the 2 unspecified)
    "rsi14",                                              # momentum
    "stoch_k", "stoch_d",                                 # stochastic
    "boll_upper", "boll_lower",                           # volatility (Bollinger)
    "atr14",                                              # volatility (ATR)
    "obv",                                                # volume
    "vwap",                                               # volume
    "cci",                                                # market structure
    "williams_r",                                         # market structure
]
ZSCORE_WINDOW: int = 252                                  # rolling z-score (p.6, Eq.13)
assert len(FEATURE_ORDER) == 22, "State must be exactly 22 dimensions (paper p.7)."
