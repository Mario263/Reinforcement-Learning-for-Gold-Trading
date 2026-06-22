# CODEBASE FORENSIC AUDIT

Audit of every file in `Reinforcement-Learning-for-Gold-Trading/`, assuming **nothing is correct** and judging only against the paper (`../../researchPaper/PPO_RAW_GROUND_TRUTH.md`). Two code regions exist: **(I) original upstream pipeline** (intraday strategy — NOT the paper) and **(II) paper_baseline pipeline** (built in Phase 2 — the reproduction).

Verdict legend: 🟥 contradicts paper · 🟨 partial / under-specified · 🟩 matches paper · ⬜ irrelevant to paper.

---

## REGION I — ORIGINAL UPSTREAM PIPELINE (`src/rl_gold_trading/*.py`)
**Global verdict: 🟥 NOT the paper.** This is a different strategy (intraday day-episodes, oz sizing, dollar-PnL reward, 9 features, 15-min bars, 2004 start, global VecNormalize, default PPO net). It is retained only as the untouched upstream substrate; it is **not** used for the reproduction.

| File | Purpose | Config values / hidden defaults | Paper conformance |
|---|---|---|---|
| `config.py` | DataConfig/EnvConfig/TrainConfig | resample `15min`; years 2004–2025; oz sizing 5–7.5; cost `$0.65/oz`; many penalties; timesteps 1e6 | 🟥 frequency, window, sizing, costs, reward all differ |
| `data.py` | HF load, standardize, **resample 15min**, year-split | utc parse; dropna | 🟥 15-min, year-split |
| `features.py` | **9 features** (log_return, hl_range, body, atr14, rsi14, ema_diff, volatility32, tod_sin/cos) | RSI fillna 50 | 🟥 9≠22, wrong indicators |
| `envs.py` | Intraday env, **per-day episodes**, oz position w/ equity scaling, **dollar-PnL reward + penalties** (drawdown 2.5, flip 0.15, loss-limit 75, overtrade 5, end-day bonus) | obs = 9 feat + 4 portfolio = **13 dims**; Discrete(3) 0=hold,1=long,2=short | 🟥 reward, sizing, obs-dim, episode structure, action mapping all differ |
| `vec_env.py` | DummyVecEnv + **VecNormalize** (norm_obs, **norm_reward=True**, clip_obs 10) | Monitor wrap | 🟥 global running normalization ≠ 252 rolling z-score |
| `train.py` | SB3 PPO default net | **default [64,64]** | 🟥 arch differs |
| `metrics.py` | daily-PnL stats; Sharpe ×√252 on daily PnL | — | 🟥 wrong metric basis |
| `run.py` | orchestrator (load→feat→split→train→eval) | — | ⬜ driver |
| `train.py` (root) | entry point | path insert | ⬜ |
| `models/ppo_xauusd.zip`, `vecnormalize.pkl` | pretrained intraday model | — | ⬜ not paper |

**Action:** leave Region I untouched (do not delete — it is the documented upstream baseline). It plays no role in the paper reproduction.

---

## REGION II — PAPER_BASELINE PIPELINE (`src/rl_gold_trading/paper_baseline/*.py`)
**Global verdict: 🟩 high conformance, 🟨 3 fixable gaps.** Built in Phase 2 to reproduce PPO Raw.

| File | Purpose | Key values | Paper conformance |
|---|---|---|---|
| `config_paper.py` | all paper configs | resample `1D`; 2017-01→2025-02; train_fraction 0.70; commission 0.0001; spread 0.00005; α/β/γ/δ=1/2/0.5/0.1; PPO clip 0.2/GAE 0.95/c1 0.5/c2 0.01/lr 3e-4 linear/2048/256/10/γ0.99/500k; net [512,512,256,128]; FEATURE_ORDER=22; ZSCORE_WINDOW 252 | 🟩 mostly; 🟨 `train_fraction` (row fraction, not calendar dates) |
| `data_paper.py` | HF load → filter 2017-2025 → **resample 1D** → temporal_split | utc parse; dropna on resample (**no forward-fill**) | 🟩 daily, range; 🟨 split is **row-fraction** not calendar; 🟨 no forward-fill |
| `features_paper.py` | 22 features via `ta` | 5 OHLCV + SMA10/20/50, EMA12/26, **MACD line+signal**, RSI14, Stoch%K/%D, Boll up/low, ATR14, OBV, VWAP(14), CCI(20), WilliamsR(14) | 🟩 15 enumerated match; 🟨 **MACD line+signal = the 2 unspecified indicators (documented assumption)** |
| `normalize_paper.py` | **252 rolling z-score**, causal, per-feature | min_periods=252; drop warmup; inf→0 | 🟩 matches Eq.13, no leakage |
| `env_paper.py` | 22-dim obs; Discrete(3)→{−1,0,+1}; 100% capital; **Eq.22 reward**; costs commission+spread | DD running-max; stability=−\|Δpos\|; cost=\|Δpos\|·(comm+spread) | 🟩 reward weights/formula, action, sizing; 🟨 **costs omit sqrt market-impact + linear slippage** (paper params unspecified) |
| `ppo_raw.py` | SB3 PPO, paper arch + linear LR | policy_kwargs net_arch pi/vf=[512,512,256,128] Tanh; lr linear→0; seed 42 | 🟩 verified exact (printed policy) |
| `evaluate_paper.py` | metrics: cum/CAGR/Sharpe(√252)/MaxDD/win + diagnostics | deterministic single pass | 🟩 metric set; 🟨 Sharpe annualization √252 is an assumption (paper unspecified) |
| `run_ppo_raw.py` | orchestrator + paper comparison | prepare_data→train→eval→report | 🟩; 🟨 inherits row-fraction split |
| `train_ppo_raw_baseline.py` (root) | entry point | — | 🟩 |
| `eval_ppo_raw_diag.py`, `count_trades.py` (root) | diagnostics | data-before-torch import order (segfault fix) | ⬜ analysis only |

---

## DATA FLOW (Region II, as-built)
```
HF ZombitX64 (15min, 2004-2025)
  → filter 2017-01..2025-02  → resample 1D OHLCV
  → ta: 22 features (5 OHLCV + 17 indicators)
  → 252-day causal rolling z-score (drop ~252+ warmup)
  → temporal_split(0.70)  [ROW FRACTION — gap vs calendar]
  → PaperTradingEnv (22 obs, Discrete3→{-1,0,1}, 100% cap, Eq.22, comm+spread)
  → SB3 PPO [512,512,256,128] Tanh, paper hparams, 500k
  → deterministic eval on test → metrics
```

## ASSUMPTIONS & HIDDEN DEFAULTS FOUND
1. **Split = 70% of post-warmup rows** (config_paper `train_fraction`), not the paper's calendar `2017–2022 / 2023–2025`. → conformance gap.
2. **No forward-fill** of missing daily bars (paper forward-fills <0.1%). → minor gap.
3. **MACD line+signal** chosen as the 2 indicators to reach 17 (paper under-specifies). → documented assumption.
4. **Costs = commission+spread only**; market-impact (√) and slippage (linear) omitted because ADV/slippage coefficients are unspecified in the paper. → partial gap.
5. **Sharpe annualization = √252** (paper gives no factor). → unavoidable assumption.
6. **Eval over full 30% test (668 daily)**, not the paper's exact 621-day window (Jan 2 2023–Sep 12 2024). → conformance gap.
7. **Reward "relative to benchmark"** omitted (no formula term). → faithful to Eq.22 formula, documented.
8. **S_stability = −|Δposition|** (paper gives no formula). → documented operationalization.

## CONCLUSION
Region I is irrelevant and untouched. Region II already reproduces the paper at high fidelity; the **closable gaps** for Phase 3 are: calendar split (#1), 621-day eval window (#6), market-impact+slippage costs (#4), and forward-fill (#2). Items #3, #5, #7, #8 are **paper-side under-specifications** that can only be resolved by documented assumption, not by "more faithful" code.
