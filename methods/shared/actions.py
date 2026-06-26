"""Action mapping (framework-neutral). Single source.

SB3 Discrete(3) -> target position direction: {0:-1 short, 1:0 flat, 2:+1 long}.
NOTE: action 1 targets FLAT (RawPPO semantics), not "maintain position".
"""
from methods.shared.config import ACTION_TO_TARGET


def action_to_target(action: int) -> int:
    return ACTION_TO_TARGET[int(action)]


def turnover(prev_dir: int, target_dir: int) -> int:
    """Direction change magnitude in {0,1,2} (= |target - prev|)."""
    return abs(int(target_dir) - int(prev_dir))
