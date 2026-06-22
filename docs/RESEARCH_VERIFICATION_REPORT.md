# RESEARCH VERIFICATION REPORT (Agent 1)

Re-verification of the paper, knowledge graph, and prior findings for the **PPO-only ("PPO Raw") baseline**. Sources: `Paper_81-...pdf` (re-read via `researchPaper/_extracted_text.txt`, page-cited), `../../knowledgeGraphResearchPaper/knowledge_graph.{json,md,graphml,mermaid}`, and prior forensic reports.

## PPO-RAW BASELINE REQUIREMENTS (from paper, PDF pages)
| Requirement | Paper value | Page |
|---|---|---|
| Algorithm | PPO (value head + categorical actor), **no Kalman** for the raw variant | 9, Table I |
| State | 22 = 5 OHLCV + 17 indicators | 7 |
| Normalization | 252-day rolling z-score | 6 |
| Action | {−1,0,+1} | 7 |
| Reward | Eq.22, α/β/γ/δ = 1/2/0.5/0.1 | 8 |
| Costs | commission 0.01% + spread 0.005% | 7 |
| Architecture | actor & critic [512,512,256,128] Tanh | 9 |
| Hyperparameters | clip 0.2, GAE 0.95, c₁0.5, c₂0.01, lr 3e-4 linear, 2048/256/10, γ0.99, 500k | 9 |
| Data | XAU/USD 2017→2025, daily, 70/30 calendar split, 621-day eval | 5,6 |

## NO-KALMAN VERIFICATION (executable code)
`grep -rinE "kalman|dqn|rppo|lstm|recurrent" src/ nautilus/ --include=*.py` (excluding comments/docstrings) → **0 matches in executable code** (only the paper-title string in a docstring). SB3 import audit → **only `PPO`** is imported (no DQN/A2C/SAC/TD3/DDPG). ✅ The implementation is PPO-only with no Kalman/recurrent logic.

## KNOWLEDGE-GRAPH CROSS-CHECK (PPO nodes)
All PPO-relevant KG nodes (`M_PPO`, `E22`, `E13`, `H_clip`, `H_lambda`, `H_lr`, `H_rollout`, `H_reward_w`, `F_indicators`, `D_data`) were re-checked against the paper in `PPO_RAW_GROUND_TRUTH.md` §8 and remain consistent. **No KG update required.**

## PRIOR-FINDINGS VERIFICATION
- Win-rate two-number question → resolved (`WIN_RATE_FORENSIC_REPORT.md`): same 57 wins, denominators 530 vs 96.
- Paper PPO↔RPPO swap affects only the *enhanced* rows; the **PPO Raw** target row (15.39% / 0.69 / −11.22% / 50.16%) used here is unaffected and correctly cited.
- Env's +48.94% shown (Phase 4) to be an optimistic-fill artifact (collapses to −1.27% under event-driven execution).

## DOCUMENTED PAPER-SIDE UNDER-SPECIFICATIONS (not implementation defects)
1. 2 of 17 indicators unspecified → MACD line+signal.
2. S_stability formula absent → −|Δposition|.
3. "return relative to benchmark" prose has no formula term → omitted.
4. Sharpe annualization factor unstated → √252.
5. Market-impact ADV / slippage coefficients unstated → omitted (per Phase-3 user decision; commission+spread retained).

## VERDICT
The implementation faithfully reproduces the paper's PPO-Raw **methodology**. No Kalman/DQN/RPPO present. No KG or extracted-finding contradicts a fresh read. The only gaps are paper-side under-specifications, each locked by a documented assumption. **No research-level mismatch found.**
