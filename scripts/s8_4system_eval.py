"""S8 — System comparison on (clean | empirically-perturbed) test sets.

Fills the §VI comparison bars. The set of "systems" is configurable
by passing one or more (model_id, mode) pairs:

    model_id : a key registered via register_kie_model_factory(); the
               same model can be evaluated multiple times in different
               modes if its adapter exposes them.
    mode     : "unconstrained"  — base decoder, no constraints
               "sigma"          — base + Paper 1's Sigma verifier post-hoc
               "aad"            — base + AAD constrained decoding (this paper)

A typical §VI table compares 3-4 systems, e.g.:

    DONUT, mode=unconstrained
    DONUT, mode=sigma
    DONUT, mode=aad
    LayoutLMv3, mode=aad

(The exact set is selected via --systems on the command line; the
script does not hardcode any architecture.)

Each system is evaluated on:
  (a) the clean test split, and
  (b) a perturbed copy of the test split where digit corruption is
      sampled from S3's empirical confusion matrix.

Reports F1 per field + global mean, plus paired-bootstrap 95% CIs on
delta-F1 between system pairs and McNemar's exact test on per-image
correctness.

This script depends on at least one KIE-model adapter being registered
via paper3.data.kie_model_io.register_kie_model_factory(). Off-the-shelf
adapters can wrap models like DONUT (`naver-clova-ix/donut-base`) and
LayoutLMv3 (`microsoft/layoutlmv3-base`).

Usage:
    python -m paper3.scripts.s8_4system_eval \\
        --systems donut:unconstrained,donut:sigma,donut:aad,layoutlmv3:aad \\
        --sroie /data/SROIE_Task3/test \\
        --confusion_json results/s3_cord_confusion.json \\
        --seed 0
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

from ..data.kie_model_io import get_kie_model, StubKIEModel


def parse_args():
    ap = argparse.ArgumentParser(description="S8: configurable system comparison")
    ap.add_argument("--systems", required=True,
                    help="comma-separated list of model_id:mode pairs, "
                         "e.g. 'donut:unconstrained,donut:aad,layoutlmv3:aad'")
    ap.add_argument("--checkpoints", default="",
                    help="comma-separated checkpoint paths in the same order "
                         "as --systems (or empty to use defaults)")
    ap.add_argument("--sroie", required=True)
    ap.add_argument("--confusion_json",
                    default="results/s3_cord_confusion.json")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out_json", default="results/s8_eval.json")
    return ap.parse_args()


def main():
    args = parse_args()
    model = get_kie_model()
    if isinstance(model, StubKIEModel):
        print("[s8] No KIE-model adapter is registered.")
        print("[s8] Once an adapter calls register_kie_model_factory()")
        print("     at import time, this script becomes runnable. Until")
        print("     then it cannot evaluate any system.")
        print("[s8] Off-the-shelf starting points: DONUT, LayoutLMv3.")
        sys.exit(2)
    raise NotImplementedError(
        "S8 evaluator skeleton — full implementation depends on the "
        "registered KIE-model adapter exposing predict() and "
        "decode_total_with_aad(). Stub left in place so the script "
        "compiles and tests pass; fill in the (model_id, mode) loop "
        "against the registered adapter once available."
    )


if __name__ == "__main__":
    main()
