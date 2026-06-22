# PPO RAW BASELINE — GAP ANALYSIS

**Goal:** reproduce the paper's **PPO *without* Kalman ("PPO Raw")** baseline (Kili et al., IJACSA 16(11) 2025) inside this repository, with reproduction *fidelity* (not profit) as the success criterion.
**Paper target (Table I/II):** Cumulative return ≈ **15.39%**, CAGR ≈ **6.00%**, Sharpe ≈ **0.69**, Max Drawdown ≈ **−11.22%**, Win rate ≈ **50.16%**.
**Hard constraints honored:** no Kalman, no DQN/RPPO, no architecture "improvements", no extra features, no reward modifications, use mature libraries (SB3/Gymnasium/PyTorch/ta), no data leakage.

---

## PHASE A — REVERSE ENGINEERING (existing repo)

Repository derives from `JonusNattapong/Reinforcement-Learning-for-Gold-Trading`. Package: `src/rl_gold_trading/`.

| File | What it does | Paper component it maps to |
|---|---|---|
| `config.py` | `DataConfig` (2004–2025, 15min, year splits), `EnvConfig` (oz sizing, $200 capital, custom penalties), `TrainConfig` (PPO hparams) | Config (partial overlap with §IV) |
| `data.py` | Loads HF dataset `ZombitX64/xauusd-...-2004-2025`, standardizes cols, **resamples to 15min**, splits by year | §IV.A data, but wrong frequency/window |
| `features.py` | Computes **9 features**: log_return, hl_range, body, atr14, rsi14, ema_diff, volatility(32), tod_sin, tod_cos | §IV.B — but only 9, not the paper's 22 |
| `envs.py` | `XAUUSDTradingEnv`: **intraday** episodes (one trading *day* each), oz-based position sizing with equity scaling, dollar-PnL reward + many bespoke penalties (drawdown 2.5, flip 0.15, loss-limit 75, overtrade 5, end-day bonus), `Discrete(3)`, obs = 9 features + 4 portfolio scalars = **13 dims** | §IV.E/F — fundamentally different env & reward |
| `vec_env.py` | `DummyVecEnv` + **`VecNormalize`** (running mean/std, `norm_reward=True`, `clip_obs=10`), Monitor wrapper, helpers | §IV.B normalization — but global running stats, NOT 252-day rolling z-score |
| `train.py` | `build_model` = SB3 `PPO("MlpPolicy")` default arch; `train_model` | §IV.G.2 PPO — default arch, not [512,512,256,128] Tanh |
| `metrics.py` | Per-day PnL stats: avg daily profit, win rate, max drawdown, Sharpe(×√252 on daily PnL), trades/day | §V metrics — different basis (intraday daily-PnL, not equity-curve return%/CAGR) |
| `run.py` | Orchestrates load→features→split→train→eval (valid/test) | driver |
| `train.py` (root) | Entry point; puts `src/` on path; calls `run.main()` | CLI |
| `models/*` | Pre-trained intraday PPO + VecNormalize stats | n/a (different strategy) |

**Data flow (existing):** HF → standardize → resample 15min → 9 features → year-split → `XAUUSDTradingEnv` (per-day episodes) → `VecNormalize` → SB3 PPO (default MLP) → per-day PnL metrics.

**Verdict:** the existing repo is a **different strategy** (intraday, oz-sized, dollar-PnL, heavily shaped reward, 13-dim obs, 15-min bars, 2004 start, global normalization, default PPO net). It shares only: SB3 PPO, Gymnasium, `Discrete(3)`, and the data source. It cannot be "tuned" into the paper baseline — the env, features, normalization, reward, and metrics all differ structurally.

---

## PHASE B — GAP TABLE (current → paper PPO Raw)

| # | Dimension | Current implementation | Paper PPO Raw | Required change | Risk | Validation |
|---|---|---|---|---|---|---|
| G1 | Data window | 2004–2025 | **2017-01 → 2025-01** (8y) | Filter years | Low | row count/date range check |
| G2 | Frequency | 15-min resample | **Daily** resample (§IV.A) | Resample `1D` | Low | ~2000 daily bars |
| G3 | Split | year-based 2004-21/22-23/24-25 | **70/30 temporal** (train 2017-2022, test 2023-2025) | Reimplement split | Low | sizes ≈70/30 |
| G4 | Features | 9 custom | **22 = 5 OHLCV + 17 indicators** (SMA10/20/50, EMA12/26, MACD line/signal, RSI14, Stoch %K/%D, Boll up/low, ATR14, OBV, VWAP, CCI, Williams %R) | New feature module via `ta` | Med | obs_dim == 22 |
| G5 | Normalization | `VecNormalize` global running stats + norm_reward | **252-day rolling z-score**, causal, per-feature, no leakage (Eq.13) | New normalizer; **drop VecNormalize** | High | no future leakage; manual recompute spot-check |
| G6 | Env episode | intraday (one day) | **continuous** pass over series (portfolio equity) | New env | High | episode length ≈ series length |
| G7 | Action mapping | Discrete(3): 0 hold,1 long,2 short | **Discrete(3) → {−1,0,+1}** sell/hold/buy | Keep Discrete(3), remap | Low | action→position map test |
| G8 | Position sizing | oz 5–7.5, equity-scaled | **100% capital**, all-or-nothing | New env logic | Med | notional == equity |
| G9 | Reward | dollar PnL − many bespoke penalties | **Eq.22:** 1.0·R_port − 2.0·DD − 0.5·Cost + 0.1·Stability | New reward | High | unit test of each term |
| G10 | Costs | $0.65/oz | **commission 0.01% + spread 0.005% = 0.015%** of traded notional | New cost model | Med | cost == 0.00015·|Δpos| |
| G11 | PPO arch | SB3 default [64,64] Tanh | **[512,512,256,128] Tanh** actor+critic | `policy_kwargs` | Low | print policy (verified ✓) |
| G12 | LR schedule | constant 3e-4 | **3e-4 linear decay → 0** | LR schedule fn | Low | callback log |
| G13 | Timesteps | 1,000,000 | **500,000** | set 500k | Low | config |
| G14 | Metrics | daily-PnL stats | **cum return %, CAGR, Sharpe(√252), MaxDD %, win %** on equity curve | New evaluator | Med | recompute from equity series |
| G15 | Obs contents | 13 (9 feat + 4 portfolio) | **exactly 22** (features only; Phase C mandate) | obs = 22 features | Low | Box shape (22,) |

**Confirmed already-correct (no change):** `Discrete(3)` action space; γ=0.99; gae_lambda=0.95; clip=0.2; ent_coef=0.01; vf_coef=0.5; n_steps=2048; batch=256; SB3 PPO library usage. (`TrainConfig` already holds most PPO hparams.)

---

## IMPLEMENTATION DECISION (documented for auditability)

The existing strategy modules are a **different, working baseline** and are *not* destroyed. The paper baseline is added as an **isolated subpackage** `src/rl_gold_trading/paper_baseline/`, reusing mature infrastructure (SB3 PPO, Gymnasium, `ta`). This:
- preserves the upstream intraday baseline for reference,
- keeps the paper reproduction self-contained and inspectable,
- avoids entangling the two reward/feature/normalization regimes.

New modules:
- `paper_baseline/data_paper.py` — G1/G2/G3
- `paper_baseline/features_paper.py` — G4 (via `ta`)
- `paper_baseline/normalize_paper.py` — G5 (252 rolling z-score, causal)
- `paper_baseline/env_paper.py` — G6/G7/G8/G9/G10/G15 (22-dim, Eq.22, 100% capital, costs)
- `paper_baseline/ppo_raw.py` — G11/G12/G13 (SB3 PPO, paper arch/hparams)
- `paper_baseline/evaluate_paper.py` — G14 (return/CAGR/Sharpe/MaxDD/win)
- `paper_baseline/run_ppo_raw.py` — orchestrator + report

**No Kalman anywhere.** This is the raw-input baseline only.

---

## FIDELITY CAVEATS (known, from `../../researchPaper/result_validation.md`)
- The paper's exact data vendor/timezone and Sharpe **annualization factor** are unstated; we use the repo's HF XAU/USD source and √252 daily annualization (paper-consistent with daily resampling). Absolute numbers may differ; the goal is *reasonable* reproduction of the PPO Raw regime (low Sharpe ≈0.7, ~15% return, ~−11% drawdown, ~50% win rate), not digit-exact match.
- Paper reward "return relative to benchmark" is implemented as raw portfolio return (benchmark term omitted to avoid an information channel; documented). All other Eq.22 terms implemented verbatim.
- Single-seed run mirrors the paper (which appears single-seed). Seed fixed for reproducibility.
