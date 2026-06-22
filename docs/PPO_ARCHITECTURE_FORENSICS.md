# PPO ARCHITECTURE FORENSICS (Agent 4)

Verification of the PPO architecture and hyperparameters against the paper (PDF p.9). Sources: `train.build_model`, `config.TrainConfig`. Architecture independently confirmed by loading the saved model and printing the policy.

## HYPERPARAMETER TABLE
| Item | Paper (p.9) | Code (`config.TrainConfig` / `train.py`) | Verified value (saved model) | Match |
|---|---|---|---|---|
| Actor arch | [512,512,256,128] | `net_arch.pi` | Linear512→512→256→128 | ✅ |
| Critic arch | [512,512,256,128] | `net_arch.vf` | Linear512→512→256→128 | ✅ |
| Hidden activation | Tanh | `activation_fn=nn.Tanh` | Tanh ×4 | ✅ |
| Actor head | softmax (categorical) | SB3 MlpPolicy Discrete | action_net→3 | ✅ |
| Critic head | linear value | SB3 value_net | value_net→1 | ✅ |
| Optimizer | (Adam, SB3 default) | SB3 default Adam | Adam | ✅ |
| Learning rate | 3e-4 linear→0 | `linear_schedule(3e-4)` | lr(1.0)=3e-4, lr(0.0)=0 | ✅ |
| Rollout (n_steps) | 2048 | `n_steps=2048` | 2048 | ✅ |
| Batch size | 256 | `batch_size=256` | 256 | ✅ |
| Epochs | 10 | `n_epochs=10` | 10 | ✅ |
| Entropy coeff c₂ | 0.01 | `ent_coef=0.01` | 0.01 | ✅ |
| GAE λ | 0.95 | `gae_lambda=0.95` | 0.95 | ✅ |
| Clip range | 0.2 | `clip_range=0.2` | clip(1.0)=0.2 | ✅ |
| Value coeff c₁ | 0.5 | `vf_coef=0.5` | 0.5 | ✅ |
| Discount γ | 0.99 (p.4) | `gamma=0.99` | 0.99 | ✅ |
| Total timesteps | 500,000 | `total_timesteps=500000` | metrics.json timesteps=500000 | ✅ |
| Library | (PPO) | SB3 `PPO("MlpPolicy")` | — | ✅ no custom PPO |

(Saved-model verification printed in Phase 3: pi/vf each `[Linear512,Tanh,Linear512,Tanh,Linear256,Tanh,Linear128,Tanh]`, action_net→3, value_net→1; gamma 0.99, gae 0.95, clip 0.2, ent 0.01, vf 0.5, n_steps 2048, batch 256, n_epochs 10, lr 3e-4→0.)

## NOT SPECIFIED BY PAPER (SB3 defaults retained, documented)
- Adam β₁/β₂/eps, `max_grad_norm` (0.5), advantage normalization (SB3 default on). The paper does not specify these; SB3 defaults are standard and not in conflict with any stated value.

## VERDICT
Every architecture/hyperparameter value stated in the paper is matched **exactly**, and independently confirmed against the trained weights. PPO is provided by Stable-Baselines3 (mature library; no custom PPO). **No architecture/hyperparameter mismatch.**
