"""Reward formula Eq.22 (framework-neutral). Single source — the FORMULA only.

  reward = ALPHA*gross_return - BETA*drawdown - GAMMA*cost_frac + DELTA*stability
  stability = -turnover_dir

Each framework feeds its own components: RawPPO from its return-based ledger, NautilusPPO from
Nautilus equity. Coefficients are fixed by the spec. (This is the neutral math, not accounting.)
"""
from methods.shared.config import ALPHA, BETA, DELTA, GAMMA


def raw_ppo_reward(*, gross_return: float, drawdown: float, cost_frac: float,
                   turnover_dir: int) -> float:
    return (ALPHA * gross_return
            - BETA * drawdown
            - GAMMA * cost_frac
            + DELTA * (-float(turnover_dir)))
