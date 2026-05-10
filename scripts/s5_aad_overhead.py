"""S5 — AAD decoding-overhead microbenchmark.

Fills the §VI/§VII overhead row. Reports AAD's *added* per-decode
cost on top of an arbitrary base decoder:

    cost_AAD(r) = T_construction(r) + sum_{t=1..K} mask_build_t(r)

where K is the length of the total field (typically 4-6 tokens for
a value like "36.23" plus EOS) and `mask_build_t` is the wall-clock
time of `build_mask(prefix, T, vocab)` at step t.

What this script does NOT compute:
  * the unconstrained-decoder forward pass time
  * the sampled-token cross-entropy / argmax wall time

That is, S5 measures the cost AAD ADDS on top of whatever the base
decoder costs. The "% of base decoder latency" column in the §VI
table is therefore reported as

    overhead_pct = cost_AAD(r) / base_latency(r) * 100

with `base_latency` provided by the registered KIE-model adapter
(see paper3.data.kie_model_io). If no adapter is registered, S5
reports cost_AAD(r) in absolute milliseconds and flags the percent
column as `<base-latency-pending>`.

Usage:
    python -m paper3.scripts.s5_aad_overhead --corpus synthetic --n 500
"""
from __future__ import annotations
import argparse
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Dict, List

from ..data import load_corpus
from ..data.kie_model_io import get_kie_model, StubKIEModel
from ..core.subset_sum import reachable_targets
from ..core.aad_decoder import build_mask, EOS, DEFAULT_VOCAB
from ..core.stats import percentile

RESULTS = Path("results")


def gold_str(cents: int) -> str:
    """Format gold total as the decoder would emit it: 'D+.DD'."""
    return f"{cents//100}.{cents%100:02d}"


def measure_one(items_cents, tau_cents, gold_cents) -> Dict:
    """Return T-build time + per-step mask-build times + meta for one receipt."""
    if not items_cents:
        return None
    t0 = time.perf_counter()
    T = reachable_targets(items_cents, tau_cents,
                          k_min=1 if tau_cents != 0 else 2)
    t1 = time.perf_counter()
    T_ms = (t1 - t0) * 1000.0

    gs = gold_str(gold_cents)
    step_ms: List[float] = []
    for i in range(len(gs) + 1):
        prefix = gs[:i]
        t2 = time.perf_counter()
        _ = build_mask(prefix, T, DEFAULT_VOCAB)
        t3 = time.perf_counter()
        step_ms.append((t3 - t2) * 1000.0)

    total_ms = T_ms + sum(step_ms)
    return {
        "T_size": len(T),
        "T_construction_ms": T_ms,
        "mask_steps_ms": step_ms,
        "n_steps": len(step_ms),
        "total_ms": total_ms,
        "n_items": len(items_cents),
    }


def aggregate(per_receipt: List[Dict]) -> Dict:
    if not per_receipt:
        return {"error": "no measurements"}
    T_ms = [m["T_construction_ms"] for m in per_receipt]
    step_ms_flat = [s for m in per_receipt for s in m["mask_steps_ms"]]
    total_ms = [m["total_ms"] for m in per_receipt]

    def stats(xs):
        s = sorted(xs)
        return {
            "mean":   statistics.mean(s),
            "median": statistics.median(s),
            "p95":    percentile(s, 95),
            "p99":    percentile(s, 99),
            "max":    max(s),
        }

    return {
        "n_receipts":         len(per_receipt),
        "T_construction_ms":  stats(T_ms),
        "per_step_mask_ms":   stats(step_ms_flat),
        "per_receipt_total_ms": stats(total_ms),
        "mean_steps_per_receipt": statistics.mean(m["n_steps"] for m in per_receipt),
    }


def parse_args():
    ap = argparse.ArgumentParser(description="S5: AAD overhead microbenchmark")
    ap.add_argument("--corpus", choices=["sroie", "cord", "synthetic"],
                    default="synthetic")
    ap.add_argument("--path", default=None)
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max", type=int, default=None)
    ap.add_argument("--out_json", default="results/s5_aad_overhead.json")
    return ap.parse_args()


def main():
    args = parse_args()
    RESULTS.mkdir(exist_ok=True)

    recs = load_corpus(args.corpus, path=args.path, n=args.n,
                       seed=args.seed, max_receipts=args.max)
    measurements = []
    for r in recs:
        m = measure_one(r.items_cents(), r.tau_cents(), r.gold_total_cents)
        if m is not None:
            measurements.append(m)

    agg = aggregate(measurements)

    model = get_kie_model()
    if isinstance(model, StubKIEModel):
        agg["base_latency_status"] = (
            "No KIE-model adapter registered — overhead reported in "
            "absolute ms only. Register an adapter via "
            "paper3.data.kie_model_io.register_kie_model_factory() to "
            "report % of base-decoder latency."
        )
    else:
        try:
            prof = model.latency_profile([], None)
            agg["base_latency_ms"] = prof
            mean_base = prof.get("mean_ms", 0.0)
            if mean_base > 0:
                agg["overhead_pct_of_base"] = {
                    "mean": agg["per_receipt_total_ms"]["mean"] / mean_base * 100,
                    "p95":  agg["per_receipt_total_ms"]["p95"]  / mean_base * 100,
                }
        except NotImplementedError:
            agg["base_latency_status"] = "Adapter registered but latency_profile not implemented"

    Path(args.out_json).write_text(json.dumps(agg, indent=2))
    print(json.dumps(agg, indent=2))
    print(f"\n[s5] wrote {args.out_json}", file=sys.stderr)


if __name__ == "__main__":
    main()
