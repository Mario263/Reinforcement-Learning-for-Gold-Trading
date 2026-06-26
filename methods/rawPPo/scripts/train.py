"""RawPPO native training (SB3/Gym, GPU). Explicit args, no hidden defaults.

  python -m methods.rawPPo.scripts.train --split current --total-timesteps 500000 \
    --device cuda --model-out methods/rawPPo/models/rawppo_current_split.zip
"""
import argparse
import json
from pathlib import Path

from methods.rawPPo.src.evaluate_sb3 import evaluate
from methods.rawPPo.src.train_sb3 import train
from methods.shared.config import CSV_PATH, CURRENT_SPLIT, MODERN_SPLIT
from methods.shared.data_loader import load_processed
from methods.shared.observations import prepare_window
from methods.shared.validation import assert_obs, assert_windows

SPLITS = {"current": CURRENT_SPLIT, "modern": MODERN_SPLIT}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["current", "modern"], required=True)
    ap.add_argument("--total-timesteps", type=int, required=True)
    ap.add_argument("--ent-coef", type=float, default=None)
    ap.add_argument("--device", default="auto")
    ap.add_argument("--csv", default=CSV_PATH)
    ap.add_argument("--model-out", required=True)
    a = ap.parse_args()
    w = SPLITS[a.split]
    assert_windows(**w)
    full = load_processed(a.csv)
    tr, cols = prepare_window(full, w["train_start"], w["train_end"])
    ev, _ = prepare_window(full, w["eval_start"], w["eval_end"])
    assert_obs(tr, cols); assert_obs(ev, cols)
    print(f"[{a.split}] csv={a.csv}")
    print(f"  train {w['train_start']}..{w['train_end']} rows={len(tr)} | "
          f"eval {w['eval_start']}..{w['eval_end']} rows={len(ev)} | device={a.device} | ent_coef={a.ent_coef}")
    curve = str(Path(a.model_out).with_suffix("")) + "_curve.csv"
    model = train(tr, cols, a.total_timesteps, ent_coef=a.ent_coef, device=a.device, curve_path=curve)
    Path(a.model_out).parent.mkdir(parents=True, exist_ok=True)
    model.save(a.model_out)
    m = evaluate(model, ev, cols)
    mo = str(Path(a.model_out).with_suffix("")) + "_metrics.json"
    Path(mo).write_text(json.dumps(m, indent=2, default=str))
    print(f"  RESULT pos={m['position_distribution']} cum={m['cumulative_return']:+.2%} "
          f"sharpe={m['sharpe']:.2f} max_dd={m['max_drawdown']:.2%}")
    print(f"  model={a.model_out} metrics={mo} curve={curve}")


if __name__ == "__main__":
    main()
