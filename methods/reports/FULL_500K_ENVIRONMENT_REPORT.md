# FULL 500K ENVIRONMENT REPORT (Phase 1)

| item | value |
|---|---|
| Python | 3.10 (`.venv`) |
| torch | **2.11.0+cu128** |
| CUDA available | **True** |
| GPU | NVIDIA GeForce RTX 5080 Laptop GPU (16 GB) |
| stable_baselines3 | 2.9.0 |
| nautilus_trader | 1.202.0 |
| git commit | `bc2c1b0` |
| data split | **modern** (train 2017-01→2022-12, eval 2023-01-02→2024-09-12), 1H, 528 z-score, 6048 annualization |

## Training commands
```
python -m methods.rawPPo.scripts.train  --split modern --total-timesteps 500000 --device cuda --model-out methods/rawPPo/models/rawppo_modern_500k.zip
python -m methods.nautilus.scripts.train --split modern --total-timesteps 500000 --device cuda --model-out methods/nautilus/models/nautilusppo_modern_500k.zip
```
- RawPPO model → `methods/rawPPo/models/rawppo_modern_500k.zip`; log → `methods/rawPPo/logs/`.
- NautilusPPO model → `methods/nautilus/models/nautilusppo_modern_500k.zip`; log → `methods/nautilus/logs/`.

## Runtime note (honest)
RawPPO 500k on GPU ≈ 30–40 min (NN on GPU, numpy env). **NautilusPPO 500k is much slower** — the
thread-bridge processes each step through queues + Nautilus event replay (≈14× 35k-bar engine runs),
likely **several hours**. It is launched in the background and reported on completion.
