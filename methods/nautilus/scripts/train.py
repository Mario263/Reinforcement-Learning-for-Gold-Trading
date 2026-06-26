"""NautilusPPO native training: SB3 PPO -> Gym adapter -> Nautilus-backed env (GPU).

  python -m methods.nautilus.scripts.train --split modern --total-timesteps 100000 \
    --device cuda --model-out methods/nautilus/models/nautilusppo_modern_split.zip
NOTE: the thread-bridge makes Nautilus training much slower than RawPPO. Start small.
"""
import argparse
import json
from pathlib import Path

from methods.nautilus.src.nautilus_metrics import evaluate
from methods.nautilus.src.sb3_nautilus_adapter import train
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
    print(f"[nautilus {a.split}] train rows={len(tr)} eval rows={len(ev)} device={a.device} "
          f"ent_coef={a.ent_coef} (thread-bridge: slow)")
    curve = str(Path(a.model_out).with_suffix("")) + "_curve.csv"
    model = train(tr, cols, full, a.total_timesteps, ent_coef=a.ent_coef, device=a.device, curve_path=curve)
    Path(a.model_out).parent.mkdir(parents=True, exist_ok=True)
    model.save(a.model_out)
    m = evaluate(model, ev, cols, full)            # metrics from NAUTILUS state
    mo = str(Path(a.model_out).with_suffix("")) + "_metrics.json"
    Path(mo).write_text(json.dumps(m, indent=2, default=str))
    print(f"  RESULT pos={m['position_distribution']} cum={m['cumulative_return']:+.2%} "
          f"sharpe={m['sharpe']:.2f}")
    print(f"  model={a.model_out} metrics={mo}")


if __name__ == "__main__":
    main()
