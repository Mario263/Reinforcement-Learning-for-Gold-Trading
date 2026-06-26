"""Single source of truth for the framework-neutral XAU/USD 1H PPO spec.

Both `methods.rawPPo` (SB3/Gymnasium) and `methods.nautilus` (Nautilus-backed) import from here.
The SPEC (features, 528 z-score, 6048 annualization, reward Eq.22, costs, windows, PPO hparams)
is framework-neutral. Framework-specific *execution* params (RawPPO normalized capital vs Nautilus
real money/instrument) are in a clearly-marked section — they are NOT the shared spec.
"""
from pathlib import Path

# methods/shared/config.py -> RawPPO repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = str(REPO_ROOT / "data" / "processed" / "xauusd_1h_2003_2026.csv")
FREQUENCY = "hourly"

# --- 22-feature state (order is part of the spec) ---
FEATURE_ORDER = [
    "open", "high", "low", "close", "volume",
    "sma10", "sma20", "sma50", "ema12", "ema26",
    "macd_line", "macd_signal", "rsi14", "stoch_k", "stoch_d",
    "boll_upper", "boll_lower", "atr14", "obv", "vwap", "cci", "williams_r",
]
assert len(FEATURE_ORDER) == 22, "state must be 22 dims"
OBS_DIM = 22

# --- normalization vs annualization (NEVER conflate) ---
ZSCORE_WINDOW = 528        # rolling BARS (1 bar = 1h ~= 1 trading month)
PERIODS_PER_YEAR = 6048    # 252 trading days x 24h — HOURLY metric annualization only

# --- reward Eq.22 coefficients + transaction costs ---
ALPHA, BETA, GAMMA, DELTA = 1.0, 2.0, 0.5, 0.1
COMMISSION, SPREAD = 0.0001, 0.00005
COST_RATE = COMMISSION + SPREAD     # 0.00015 per unit of direction turnover

# --- action ids -> target position direction ---
ACTION_TO_TARGET = {0: -1, 1: 0, 2: +1}   # 0=short, 1=flat, 2=long

# --- train/eval windows ---
CURRENT_SPLIT = {"train_start": "2003-06-09", "train_end": "2019-12-31",
                 "eval_start": "2020-01-01", "eval_end": "2026-06-24"}
MODERN_SPLIT = {"train_start": "2017-01-01", "train_end": "2022-12-31",
                "eval_start": "2023-01-02", "eval_end": "2024-09-12"}

# --- PPO hyperparameters (both frameworks use SB3 PPO) ---
PPO = {"net_arch": [512, 512, 256, 128], "learning_rate": 3e-4, "n_steps": 2048,
       "batch_size": 256, "n_epochs": 10, "gamma": 0.99, "gae_lambda": 0.95,
       "clip_range": 0.2, "ent_coef": 0.01, "vf_coef": 0.5, "max_grad_norm": 0.5,
       "seed": 42, "total_timesteps": 500_000}

# === framework-specific execution params (NOT the neutral spec) ===
RAW_INITIAL_CAPITAL = 1.0            # RawPPO: return-based normalized equity
NAUT_STARTING_CASH = 10_000_000.0   # NautilusPPO: real money (XAU min-lot 1000 oz)
NAUT_DEPLOY_FRAC = 0.95
NAUT_SYMBOL, NAUT_VENUE, NAUT_BAR_SPEC = "XAU/USD", "SIM", "1-HOUR-LAST-EXTERNAL"
