"""S7 — Joint AAD training-grid harness.

Fills §VI's 3x3 ablation table over (init, lambda_struct):

    init           in {scratch, warm_start, freeze_partial}
    lambda_struct  in {0.1, 1.0, 10.0}

This script does NOT train the model itself. It calls into the
registered KIE-model adapter (see paper3.data.kie_model_io) and
runs `model.train(config)` for each of the 9 configurations. Each
training run typically takes ~24 hours on a single A100 with an
off-the-shelf KIE backbone (DONUT, LayoutLMv3); the full grid is
the headline 9-day GPU budget.

If no KIE-model adapter is registered, S7 prints what it WOULD do
(the 9 configs) and exits with code 2. To run for real, write an
adapter satisfying KIEModelInterface and call
register_kie_model_factory() at import time.

Usage:
    python -m paper3.scripts.s7_aad_train_grid \\
        --sroie /data/SROIE_Task3 \\
        --output_dir results/checkpoints \\
        --seed 42

    # Dry run (no adapter required):
    python -m paper3.scripts.s7_aad_train_grid \\
        --sroie /data/SROIE_Task3 --dry_run
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

from ..data.kie_model_io import (
    TrainConfig, Checkpoint, get_kie_model, StubKIEModel
)


INITS = ["scratch", "warm_start", "freeze_partial"]
LAMBDAS = [0.1, 1.0, 10.0]


def parse_args():
    ap = argparse.ArgumentParser(description="S7: 3x3 AAD training grid")
    ap.add_argument("--sroie", required=True, help="SROIE Task-3 root")
    ap.add_argument("--output_dir", default="results/checkpoints")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--inits", default=",".join(INITS),
                    help="comma-separated subset of " + str(INITS))
    ap.add_argument("--lambdas", default=",".join(str(l) for l in LAMBDAS))
    ap.add_argument("--dry_run", action="store_true",
                    help="print configs that would run, then exit")
    return ap.parse_args()


def main():
    args = parse_args()
    model = get_kie_model()
    if isinstance(model, StubKIEModel):
        print("[s7] No KIE-model adapter is registered.")
        print("[s7] Write an adapter satisfying KIEModelInterface (see")
        print("     paper3.data.kie_model_io for the contract) and call")
        print("     register_kie_model_factory() at import time.")
        print("[s7] Off-the-shelf starting points: DONUT, LayoutLMv3.")
        if not args.dry_run:
            sys.exit(2)

    inits = args.inits.split(",")
    lambdas = [float(x) for x in args.lambdas.split(",")]
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    grid_results: Dict[str, Dict] = {}
    for init in inits:
        for lam in lambdas:
            cfg = TrainConfig(
                init=init,
                lambda_struct=lam,
                seed=args.seed,
                output_dir=args.output_dir,
                extra={"sroie_root": args.sroie},
            )
            print(f"[s7] cell: {cfg.cell_name()}")
            if args.dry_run:
                grid_results[cfg.cell_name()] = {"status": "dry_run"}
                continue
            try:
                ckpt = model.train(cfg)
                grid_results[cfg.cell_name()] = {
                    "status":   "trained",
                    "ckpt_path": ckpt.path,
                    "metrics":  ckpt.train_metrics,
                }
            except NotImplementedError as e:
                grid_results[cfg.cell_name()] = {
                    "status": "deferred",
                    "reason": str(e),
                }

    out_path = Path("results/s7_aad_train_grid.json")
    out_path.write_text(json.dumps(grid_results, indent=2))
    print(f"[s7] wrote {out_path}")


if __name__ == "__main__":
    main()
