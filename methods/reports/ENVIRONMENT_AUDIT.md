# ENVIRONMENT AUDIT (Phase 0)

| item | value |
|---|---|
| Python | 3.10 (`.venv`) |
| torch | 2.12.1**+cpu** (CPU-only — see GPU_STATUS_REPORT.md) |
| stable_baselines3 | 2.9.0 |
| gymnasium | 1.3.0 |
| numpy / pandas | 2.2.6 / 2.3.3 |
| nautilus_trader | 1.202.0 |
| GPU hardware | NVIDIA RTX 5080 Laptop (16 GB) present; CUDA **not usable** (CPU torch) |
| cwd | `C:\Users\Abhishek Sharma\Desktop\RawPPO` |
| processed CSV | `data/processed/xauusd_1h_2003_2026.csv` — exists, 140,364 rows, 2003-05-05→2026-06-24, cols `timestamp,open,high,low,close,volume`, UTC |
| selected device | `auto` in code → currently **cpu** (no CUDA) |

## Architecture compliance (from prior verified work)
- **RawPPO is pure SB3 + Gymnasium**: `XAUUSDTradingEnv(gym.Env)` + `stable_baselines3.PPO` +
  torch; no nautilus_trader import in the train/eval path (the repo's `nautilus/` dir is separate
  aux code, not used by RawPPO training). ✓
- **NautilusPPO is Nautilus-backed**: `BacktestEngine` owns fills/positions/cash/PnL; SB3 PPO
  drives it via a thread-bridge Gym **adapter** (not a fake custom broker). Verified: orders fill,
  positions flip, equity updates from Nautilus. ✓ (NautilusPPO reports + parity_harness)

## Blocker
GPU required (Rule 4) but torch is CPU-only → see GPU_STATUS_REPORT.md for the fix. All prior
runs were CPU and remain valid for **correctness**; GPU only affects training speed.
