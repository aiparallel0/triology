"""S8 — System comparison on a clean test set.

Evaluates one or more (model_id, mode) systems on the total-extraction
task and reports:

  * total-correctness rate per (system, mode)
  * paired-bootstrap 95% CI on the delta between each pair of systems
  * McNemar's exact test on per-receipt correctness pairs

Modes:
  unconstrained : use the adapter's `predict()` and parse the `total` field
  sigma         : `predict()` plus Paper 1's I3 verifier (rejecting
                  predictions that fall outside T(r) is counted as wrong)
  aad           : `decode_total_with_aad(image, T)` → constrained decode

Empirical-perturbation evaluation (the second column in the original
docstring) lives in the image domain and is left to a follow-up: the
adapter receives `image_path`, so corrupting the digits requires either
re-rendering the receipt or extending the adapter with a text-input
path. The `--perturb` flag is accepted for forward-compat but currently
prints a notice and runs only the clean column.

Usage:
    python -m <pkg>.scripts.s8_4system_eval \\
        --systems donut:unconstrained,donut:aad \\
        --corpus sroie --path /data/SROIE_Task3/test \\
        --seed 0
"""
from __future__ import annotations
import argparse
import json
import math
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..data import load_corpus
from ..data.kie_model_io import (
    Checkpoint, Prediction, get_kie_model, StubKIEModel,
)
from ..core.subset_sum import reachable_targets, i3_accepts
from ..core.stats import wilson_ci, fmt_proportion, paired_bootstrap_ci

RESULTS = Path("results")


# ---------------------------------------------------------------------------
# Total parsing
# ---------------------------------------------------------------------------

def _parse_total_to_cents(s: str) -> Optional[int]:
    if not s:
        return None
    cleaned = "".join(c for c in s if c.isdigit() or c == ".")
    if "." not in cleaned:
        if not cleaned.isdigit():
            return None
        return int(cleaned) * 100
    parts = cleaned.split(".")
    if len(parts) != 2:
        return None
    whole, frac = parts
    if not whole or len(frac) > 4:
        return None
    frac = (frac + "00")[:2]
    try:
        return int(whole) * 100 + int(frac)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Per-mode evaluation
# ---------------------------------------------------------------------------

def _T_for(receipt) -> set:
    items = receipt.items_cents()
    tau = receipt.tau_cents()
    if not items:
        return set()
    return reachable_targets(items, tau, k_min=1 if tau != 0 else 2)


def _eval_unconstrained(model, receipt, ckpt) -> Tuple[Optional[int], float]:
    img = receipt.meta.get("image")
    if img is None:
        return None, 0.0
    t0 = time.perf_counter()
    pred: Prediction = model.predict(img, ckpt)
    dt = (time.perf_counter() - t0) * 1000.0
    return _parse_total_to_cents(pred.fields.get("total", "")), dt


def _eval_sigma(model, receipt, ckpt) -> Tuple[Optional[int], float]:
    cents, ms = _eval_unconstrained(model, receipt, ckpt)
    if cents is None:
        return None, ms
    items = receipt.items_cents()
    tau = receipt.tau_cents()
    if not items or not i3_accepts(cents, items, tau):
        return None, ms      # sigma rejection ≡ "abstain", counted as wrong
    return cents, ms


def _eval_aad(model, receipt, ckpt) -> Tuple[Optional[int], float]:
    img = receipt.meta.get("image")
    if img is None:
        return None, 0.0
    T = _T_for(receipt)
    if not T:
        return None, 0.0
    t0 = time.perf_counter()
    text, _ = model.decode_total_with_aad(img, ckpt, T)
    dt = (time.perf_counter() - t0) * 1000.0
    return _parse_total_to_cents(text), dt


_MODE_FNS = {
    "unconstrained": _eval_unconstrained,
    "sigma":         _eval_sigma,
    "aad":           _eval_aad,
}


# ---------------------------------------------------------------------------
# McNemar exact test
# ---------------------------------------------------------------------------

def _mcnemar_p(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value on discordant pairs (b, c)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    log_pmf = lambda i: (
        math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1)
        - n * math.log(2)
    )
    p = sum(math.exp(log_pmf(i)) for i in range(k + 1))
    return min(1.0, 2 * p)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def parse_args():
    ap = argparse.ArgumentParser(description="S8: configurable system comparison")
    ap.add_argument("--systems", required=True,
                    help="comma-separated model_id:mode pairs, "
                         "e.g. 'donut:unconstrained,donut:aad'")
    ap.add_argument("--checkpoints", default="",
                    help="comma-separated checkpoint paths in the same "
                         "order as --systems (empty for adapter defaults)")
    ap.add_argument("--corpus", choices=["sroie", "cord", "synthetic"],
                    default="sroie")
    ap.add_argument("--path", default=None)
    ap.add_argument("--sroie", default=None,
                    help="alias for --corpus sroie --path <X>")
    ap.add_argument("--n", type=int, default=200,
                    help="synthetic only: number of receipts")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max", type=int, default=None,
                    help="cap real-corpus N")
    ap.add_argument("--perturb", action="store_true",
                    help="placeholder; image-domain perturbation TODO")
    ap.add_argument("--out_json", default="results/s8_eval.json")
    return ap.parse_args()


def main():
    args = parse_args()
    RESULTS.mkdir(exist_ok=True)

    if args.perturb:
        print("[s8] --perturb is a placeholder; running clean-only column. "
              "Image-domain perturbation requires extending the adapter with "
              "a text-input path or a corrupted-image renderer.",
              file=sys.stderr)

    model = get_kie_model()
    if isinstance(model, StubKIEModel):
        print("[s8] No KIE-model adapter is registered.")
        print("[s8] Import an adapter (e.g. paper3.adapters.donut) before "
              "invoking this script.")
        sys.exit(2)

    # Parse systems
    systems: List[Tuple[str, str]] = []
    for spec in args.systems.split(","):
        if ":" not in spec:
            raise SystemExit(f"--systems entry malformed (need model:mode): {spec!r}")
        m, mode = spec.split(":", 1)
        if mode not in _MODE_FNS:
            raise SystemExit(f"unknown mode {mode!r}; expected one of {list(_MODE_FNS)}")
        systems.append((m.strip(), mode.strip()))

    ckpt_paths = [c.strip() for c in args.checkpoints.split(",")] if args.checkpoints else []
    while len(ckpt_paths) < len(systems):
        ckpt_paths.append("")
    checkpoints: List[Optional[Checkpoint]] = [
        Checkpoint(path=p) if p else None for p in ckpt_paths
    ]

    # Load corpus
    path = args.path or args.sroie
    if args.corpus == "synthetic":
        receipts = load_corpus("synthetic", n=args.n, seed=args.seed)
    else:
        if not path:
            raise SystemExit(f"--corpus {args.corpus} requires --path")
        receipts = load_corpus(args.corpus, path=path,
                               max_receipts=args.max, seed=args.seed)
    print(f"[s8] {len(receipts)} receipts loaded from {args.corpus}",
          file=sys.stderr)

    # Evaluate each system on each receipt; record per-receipt correctness
    correctness: Dict[str, List[int]] = {}    # sys_label -> 0/1 per receipt
    latencies: Dict[str, List[float]] = {}
    for (mid, mode), ckpt in zip(systems, checkpoints):
        label = f"{mid}:{mode}"
        eval_fn = _MODE_FNS[mode]
        c_arr: List[int] = []
        l_arr: List[float] = []
        for r in receipts:
            try:
                pred_cents, ms = eval_fn(model, r, ckpt)
            except Exception as e:
                print(f"[s8] {label} failed on {r.receipt_id}: {e}",
                      file=sys.stderr)
                pred_cents, ms = None, 0.0
            ok = int(pred_cents is not None and abs(pred_cents - r.gold_total_cents) <= 2)
            c_arr.append(ok)
            l_arr.append(ms)
        correctness[label] = c_arr
        latencies[label] = l_arr
        print(f"[s8] {label}: {sum(c_arr)}/{len(c_arr)} correct "
              f"(mean {1000*sum(l_arr)/max(1,len(l_arr))/1000:.1f}ms)",
              file=sys.stderr)

    # Aggregate
    out: Dict = {
        "n_receipts": len(receipts),
        "corpus": args.corpus,
        "systems": [],
        "pairwise": [],
    }
    for label, arr in correctness.items():
        n = len(arr)
        k = sum(arr)
        lo, hi = wilson_ci(k, n)
        out["systems"].append({
            "label": label,
            "correct": k,
            "n": n,
            "accuracy": k / n if n else 0.0,
            "ci_low": lo, "ci_high": hi,
            "fmt": fmt_proportion(k, n),
            "mean_latency_ms": sum(latencies[label]) / max(1, n),
        })

    # Pairwise: paired bootstrap on (acc_a - acc_b), McNemar exact
    labels = list(correctness.keys())
    for i in range(len(labels)):
        for j in range(i + 1, len(labels)):
            a, b = labels[i], labels[j]
            ca, cb = correctness[a], correctness[b]
            n = len(ca)
            delta = (sum(ca) - sum(cb)) / n if n else 0.0
            lo, hi = paired_bootstrap_ci(ca, cb, n_resamples=1000, seed=args.seed)
            b_count = sum(1 for x, y in zip(ca, cb) if x and not y)
            c_count = sum(1 for x, y in zip(ca, cb) if y and not x)
            p = _mcnemar_p(b_count, c_count)
            out["pairwise"].append({
                "a": a, "b": b,
                "delta_accuracy": delta,
                "ci_low": lo, "ci_high": hi,
                "mcnemar_b": b_count, "mcnemar_c": c_count,
                "mcnemar_p": p,
            })

    Path(args.out_json).write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    print(f"\n[s8] wrote {args.out_json}", file=sys.stderr)


if __name__ == "__main__":
    main()
