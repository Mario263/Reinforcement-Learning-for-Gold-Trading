"""RawPPO evaluation (SB3/Gym). Explicit args.

  python -m methods.rawPPo.scripts.evaluate --model methods/rawPPo/models/rawppo_current_split.zip \
    --split current --device cuda
"""
import argparse
import json

from stable_baselines3 import PPO

from methods.rawPPo.src.evaluate_sb3 import evaluate
from methods.shared.config import CSV_PATH, CURRENT_SPLIT, MODERN_SPLIT
from methods.shared.data_loader import load_processed
from methods.shared.observations import prepare_window
from methods.shared.validation import assert_obs

SPLITS = {"current": CURRENT_SPLIT, "modern": MODERN_SPLIT}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--split", choices=["current", "modern"], required=True)
    ap.add_argument("--device", default="auto")
    ap.add_argument("--csv", default=CSV_PATH)
    a = ap.parse_args()
    w = SPLITS[a.split]
    full = load_processed(a.csv)
    ev, cols = prepare_window(full, w["eval_start"], w["eval_end"])
    assert_obs(ev, cols)
    print(f"eval {w['eval_start']}..{w['eval_end']} rows={len(ev)} frequency=HOURLY")
    model = PPO.load(a.model, device=a.device)
    m = evaluate(model, ev, cols)
    print(json.dumps(m, indent=2, default=str))


if __name__ == "__main__":
    main()
