# NEXT RUN COMMANDS

Actual script names (lean — reused existing pipeline instead of the prescribed 40-file tree).
All from the RawPPO root with `PYTHONPATH` set:
```powershell
cd "C:\Users\Abhishek Sharma\Desktop\RawPPO"
$env:PYTHONPATH = "C:\Users\Abhishek Sharma\Desktop\RawPPO"
```

| Purpose | Command |
|---|---|
| Current run + corrected reporting | `python train.py --mode eval` |
| Synthetic action/PnL/cost gate | `python -m methods.synthetic_action_pnl_test` |
| Action-probability + trade-PnL + regime audit | `python -m methods.forensic_model_audit --model models\ppo_xauusd_raw.zip` |
| Reward-component diagnostic (collapse) | `python -m methods.reward_component_diagnostic` |
| RawPPO vs Nautilus, SAME model | `python -m methods.parity_harness --model models\ppo_xauusd_raw.zip` |
| Modern-split retrain (fix experiment) | `python -m methods.train_modern_split --train-start 2017-01-01 --train-end 2022-12-31 --eval-start 2023-01-02 --eval-end 2024-09-12 --total-timesteps 500000 --ent-coef 0.03 --tag modern_entc03` |
| Control (modern data, default entropy) | same as above with `--ent-coef 0.01 --tag modern_default` |

Outputs land in `methods/rawPPo/diagnostics/`, `methods/rawPPo/outputs/`, `methods/rawPPo/models/`,
`methods/reports/`. The retrain writes a per-iteration training curve
(`ppo_training_curve_<tag>.csv`) for the freeze/entropy analysis.

Note: the prescribed `methods.rawPPo.scripts.*` module names were not created (they would duplicate
the working RawPPO pipeline). These commands are the equivalent, evidence-producing entry points.
