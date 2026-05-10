"""S1 — |T(r)| distribution on a corpus.

Fills the §I, §II, §III placeholder `[ |T| p95 ]` (3 occurrences).

For each receipt, computes T(r) — the subset-sum reachability set with
tau offset — and reports the distribution of |T| (mean / median / p95
/ p99 / max) plus a CDF in SVG.

Latency is also reported for the T-construction step alone, providing
the headline number for §III's complexity bound (independent of, but
consistent with, Paper 1's Table I latency).

Usage:
    python -m paper3.scripts.s1_T_distribution --corpus synthetic --n 500
    python -m paper3.scripts.s1_T_distribution --corpus sroie --path /data/sroie/test
    python -m paper3.scripts.s1_T_distribution --corpus cord --path /data/cord/test

Outputs:
    results/s1_T_distribution.json   stats per corpus
    results/s1_T_distribution.svg    CDF figure
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
from ..core.subset_sum import reachable_targets
from ..core.stats import percentile

RESULTS = Path("results")


def compute_T_stats(receipts) -> Dict:
    """Walk receipts, compute |T(r)| and T-construction time per receipt."""
    sizes: List[int] = []
    times_ms: List[float] = []
    n_receipts = 0
    n_gold_in_T = 0  # how often the gold itself lies in T (Paper 1 reach rate)
    for r in receipts:
        items = r.items_cents()
        tau = r.tau_cents()
        if not items:
            continue
        n_receipts += 1
        t0 = time.perf_counter()
        T = reachable_targets(items, tau, k_min=1 if tau != 0 else 2)
        t1 = time.perf_counter()
        sizes.append(len(T))
        times_ms.append((t1 - t0) * 1000)
        # Reachability of gold (Paper 1 §VI Table II's I3 column)
        if any(abs(t - r.gold_total_cents) <= 2 for t in T):
            n_gold_in_T += 1

    if not sizes:
        return {"error": "no receipts produced any T"}

    sizes_sorted = sorted(sizes)
    times_sorted = sorted(times_ms)
    return {
        "n_receipts": n_receipts,
        "T_size": {
            "mean":   statistics.mean(sizes),
            "median": statistics.median(sizes),
            "p95":    percentile(sizes_sorted, 95),
            "p99":    percentile(sizes_sorted, 99),
            "max":    max(sizes),
            "min":    min(sizes),
        },
        "T_construction_ms": {
            "mean":   statistics.mean(times_ms),
            "median": statistics.median(times_ms),
            "p95":    percentile(times_sorted, 95),
            "p99":    percentile(times_sorted, 99),
            "max":    max(times_ms),
        },
        "gold_in_T_rate": n_gold_in_T / n_receipts,
        # Histogram bins for the SVG renderer
        "_sizes": sizes,
    }


def render_cdf_svg(per_corpus_sizes: Dict[str, List[int]], outpath: Path):
    """Hand-rolled SVG: |T| CDF, one curve per corpus. matplotlib-free."""
    if not per_corpus_sizes:
        return
    # All sizes for axis range
    all_sizes = [s for sizes in per_corpus_sizes.values() for s in sizes]
    if not all_sizes:
        return
    x_max = max(all_sizes)
    width, height, pad = 600, 360, 60
    inner_w = width - 2 * pad
    inner_h = height - 2 * pad

    # Color cycle (IEEE-figure-friendly, distinguishable in greyscale)
    colors = ["#1f3a93", "#c0392b", "#16a085", "#8e44ad"]

    def x_pixel(v): return pad + inner_w * (v / x_max if x_max else 0)
    def y_pixel(p): return height - pad - inner_h * p

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'font-family="serif" font-size="12">',
        # background
        f'<rect width="{width}" height="{height}" fill="white"/>',
        # axes
        f'<line x1="{pad}" y1="{height-pad}" x2="{width-pad}" y2="{height-pad}" stroke="black"/>',
        f'<line x1="{pad}" y1="{pad}" x2="{pad}" y2="{height-pad}" stroke="black"/>',
        f'<text x="{width/2}" y="{height-15}" text-anchor="middle">|T(r)|</text>',
        f'<text x="20" y="{height/2}" text-anchor="middle" '
        f'transform="rotate(-90 20 {height/2})">CDF</text>',
        f'<text x="{width/2}" y="{pad-20}" text-anchor="middle" font-weight="bold">'
        f'Reachability set size CDF</text>',
    ]
    # y-axis ticks (0, 0.5, 1.0)
    for p in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = y_pixel(p)
        parts.append(f'<line x1="{pad-4}" y1="{y}" x2="{pad}" y2="{y}" stroke="black"/>')
        parts.append(f'<text x="{pad-10}" y="{y+4}" text-anchor="end">{p:.2f}</text>')

    # x-axis ticks
    for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
        x = pad + inner_w * frac
        v = round(x_max * frac)
        parts.append(f'<line x1="{x}" y1="{height-pad}" x2="{x}" y2="{height-pad+4}" stroke="black"/>')
        parts.append(f'<text x="{x}" y="{height-pad+18}" text-anchor="middle">{v}</text>')

    # CDF curves
    legend_y = pad + 10
    for i, (name, sizes) in enumerate(per_corpus_sizes.items()):
        if not sizes:
            continue
        sizes_sorted = sorted(sizes)
        n = len(sizes_sorted)
        points = []
        for j, s in enumerate(sizes_sorted):
            points.append((x_pixel(s), y_pixel((j + 1) / n)))
        path = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        c = colors[i % len(colors)]
        parts.append(f'<path d="{path}" stroke="{c}" stroke-width="2" fill="none"/>')
        # Legend
        parts.append(
            f'<rect x="{width-pad-110}" y="{legend_y-8}" width="14" height="10" '
            f'fill="{c}"/>'
        )
        parts.append(
            f'<text x="{width-pad-90}" y="{legend_y}">{name} (n={n})</text>'
        )
        legend_y += 18

    parts.append('</svg>')
    outpath.write_text("\n".join(parts))


def parse_args():
    ap = argparse.ArgumentParser(description="S1: |T(r)| distribution")
    ap.add_argument("--corpus", choices=["sroie", "cord", "synthetic", "all"],
                    default="synthetic")
    ap.add_argument("--path", default=None,
                    help="Corpus root (sroie, cord). Multiple paths "
                         "with --corpus all: e.g. --sroie /a --cord /b")
    ap.add_argument("--sroie", default=None, help="SROIE root for --corpus all")
    ap.add_argument("--cord",  default=None, help="CORD root for --corpus all")
    ap.add_argument("--n",      type=int, default=500,  help="synthetic n")
    ap.add_argument("--seed",   type=int, default=0,    help="synthetic seed")
    ap.add_argument("--max",    type=int, default=None, help="cap real-corpus N")
    ap.add_argument("--out_json", default="results/s1_T_distribution.json")
    ap.add_argument("--out_svg",  default="results/s1_T_distribution.svg")
    return ap.parse_args()


def main():
    args = parse_args()
    RESULTS.mkdir(exist_ok=True)
    out: Dict[str, Dict] = {}
    sizes_per_corpus: Dict[str, List[int]] = {}

    corpora = []
    if args.corpus == "all":
        corpora.append(("synthetic_sroie_like", "synthetic", None,
                        {"profile": "sroie_like"}))
        corpora.append(("synthetic_cord_like", "synthetic", None,
                        {"profile": "cord_like"}))
        if args.sroie:
            corpora.append(("sroie", "sroie", args.sroie, {}))
        if args.cord:
            corpora.append(("cord", "cord", args.cord, {}))
    elif args.corpus == "synthetic":
        corpora.append(("synthetic", "synthetic", None, {}))
    else:
        corpora.append((args.corpus, args.corpus, args.path, {}))

    for label, name, path, extra in corpora:
        print(f"[s1] processing {label}...", file=sys.stderr)
        recs = load_corpus(name, path=path, n=args.n, seed=args.seed,
                           max_receipts=args.max, **extra)
        stats = compute_T_stats(recs)
        sizes_per_corpus[label] = stats.pop("_sizes", [])
        out[label] = stats
        print(f"  n={stats.get('n_receipts')}  "
              f"|T| p95={stats.get('T_size',{}).get('p95'):.0f}  "
              f"reach={stats.get('gold_in_T_rate'):.3f}", file=sys.stderr)

    Path(args.out_json).write_text(json.dumps(out, indent=2))
    render_cdf_svg(sizes_per_corpus, Path(args.out_svg))
    print(f"[s1] wrote {args.out_json} and {args.out_svg}", file=sys.stderr)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
