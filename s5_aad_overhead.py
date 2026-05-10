"""S6 — Expectation estimator: Δ = E[P_AAD(gold) - P_p(gold)] vs leakage ε.

Fills the §VII "Δ over expectations" placeholder. This is the
verification side of Theorem 1 (regret bound): for any unconstrained
decoder p_t and any reachability set T containing the gold value,

    P_AAD(gold | T) >= P_p(gold)

with equality iff p_t puts zero mass on infeasible tokens. The gap is
proportional to the "leakage" — the mass the unconstrained decoder
spreads onto infeasible tokens.

We simulate decoders without a trained model by parameterizing the
unconstrained next-token distribution as a (1-ε)-concentrated delta on
the gold token plus an ε-uniform background:

    p_t(σ) = (1-ε) · δ(σ = gold_t) + ε · uniform(Σ)

ε = 0 is a perfect oracle decoder (Δ = 0). ε = 1 is uniform-random
(very high Δ). The interesting range is ε ∈ [0.05, 0.30], representing
typical fine-tuned decoder calibration regimes.

For each (receipt, ε) we compute:

    P_p(gold)   = product of p_t(gold_t) for t = 1..K
    P_AAD(gold) = product of (p_t(gold_t) / sum_{σ ∈ M_t} p_t(σ))

then average over receipts → E[Δ(ε)].

Output is a Δ-vs-ε curve and the headline number at ε ≈ 0.10 (a
plausible fine-tuned-decoder calibration regime — the actual ε for
any given KIE adapter is measured empirically by S8, but at design
time ε ∈ [0.05, 0.30] is the right ballpark).
"""
from __future__ import annotations
import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Dict, List

import numpy as np

from ..data import load_corpus
from ..core.subset_sum import reachable_targets
from ..core.aad_decoder import build_mask, EOS, DEFAULT_VOCAB

RESULTS = Path("results")


def gold_str(cents: int) -> str:
    return f"{cents//100}.{cents%100:02d}"


def simulated_p_t(prefix: str, gold_token: str, eps: float,
                  vocab=DEFAULT_VOCAB) -> Dict[str, float]:
    """(1-eps) on gold_token, eps uniform over the rest of vocab."""
    V = len(vocab)
    out = {}
    if eps >= 1.0:
        u = 1.0 / V
        return {s: u for s in vocab}
    base = eps / V
    for s in vocab:
        out[s] = base
    if gold_token in out:
        out[gold_token] += (1.0 - eps)
    else:
        # gold token not in vocab — degenerate, fall through
        pass
    return out


def per_receipt_probs(items, tau, gold_cents, eps_values: List[float]
                      ) -> Dict[float, Dict[str, float]]:
    """Return {eps: {p_unconstrained, p_aad, delta}} for one receipt."""
    if not items:
        return {}
    T = reachable_targets(items, tau, k_min=1 if tau != 0 else 2)
    gs = gold_str(gold_cents) + EOS
    seq = list(gs[:-3]) + [EOS]   # tokenize: each digit / dot is a token, then EOS
    # The above is slightly off — we need token-by-token traversal that
    # matches the build_mask convention. Rewrite:
    tokens = list(gold_str(gold_cents)) + [EOS]
    out = {}
    for eps in eps_values:
        prefix = ""
        log_p_uncon = 0.0
        log_p_aad = 0.0
        valid = True
        for tok in tokens:
            p_t = simulated_p_t(prefix, tok, eps)
            # Unconstrained prob of gold token
            p_uncon = p_t.get(tok, 0.0)
            if p_uncon <= 0:
                valid = False
                break
            log_p_uncon += np.log(p_uncon)
            # AAD prob: renormalize over feasible mask
            M = build_mask(prefix, T, DEFAULT_VOCAB)
            if not M or tok not in M:
                # mask doesn't include gold — abstain (use unconstrained)
                # NB: if T is correct, M always includes the gold token
                # for a gold sequence. If it doesn't, the abstention
                # branch makes P_AAD = P_uncon at this step.
                log_p_aad += np.log(p_uncon)
            else:
                Z = sum(p_t.get(s, 0.0) for s in M)
                if Z <= 0:
                    log_p_aad += np.log(p_uncon)
                else:
                    log_p_aad += np.log(p_uncon / Z)
            # Update prefix with consumed token (skip EOS)
            if tok != EOS:
                prefix += tok
        if not valid:
            continue
        p_uncon_v = float(np.exp(log_p_uncon))
        p_aad_v = float(np.exp(log_p_aad))
        out[eps] = {
            "P_unconstrained": p_uncon_v,
            "P_AAD": p_aad_v,
            "delta": p_aad_v - p_uncon_v,
        }
    return out


def aggregate(per_receipt_results: List[Dict[float, Dict[str, float]]],
              eps_values: List[float]) -> Dict:
    out = {"n_receipts": len(per_receipt_results), "by_eps": {}}
    for eps in eps_values:
        deltas = [r[eps]["delta"] for r in per_receipt_results if eps in r]
        p_uncs = [r[eps]["P_unconstrained"] for r in per_receipt_results if eps in r]
        p_aads = [r[eps]["P_AAD"] for r in per_receipt_results if eps in r]
        if not deltas:
            continue
        out["by_eps"][f"{eps:.3f}"] = {
            "n":        len(deltas),
            "E_P_unconstrained": statistics.mean(p_uncs),
            "E_P_AAD":           statistics.mean(p_aads),
            "E_delta":           statistics.mean(deltas),
            "E_delta_min":       min(deltas),
            "E_delta_max":       max(deltas),
        }
    return out


def render_curve_svg(stats: Dict, outpath: Path):
    """Δ-vs-ε curve, plus reference flag at ε=0.10."""
    by_eps = stats["by_eps"]
    if not by_eps:
        return
    eps_keys = sorted(by_eps.keys(), key=float)
    epses = [float(k) for k in eps_keys]
    deltas = [by_eps[k]["E_delta"] for k in eps_keys]

    width, height, pad = 600, 360, 60
    inner_w = width - 2 * pad
    inner_h = height - 2 * pad
    x_max = max(epses) if epses else 1.0
    y_max = max(0.001, max(deltas))

    def x_pixel(v): return pad + inner_w * (v / x_max if x_max else 0)
    def y_pixel(v): return height - pad - inner_h * (v / y_max if y_max else 0)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'font-family="serif" font-size="12">',
        f'<rect width="{width}" height="{height}" fill="white"/>',
        f'<line x1="{pad}" y1="{height-pad}" x2="{width-pad}" y2="{height-pad}" stroke="black"/>',
        f'<line x1="{pad}" y1="{pad}" x2="{pad}" y2="{height-pad}" stroke="black"/>',
        f'<text x="{width/2}" y="{height-15}" text-anchor="middle">leakage rate ε</text>',
        f'<text x="20" y="{height/2}" text-anchor="middle" '
        f'transform="rotate(-90 20 {height/2})">E[Δ] = E[P_AAD − P_p]</text>',
        f'<text x="{width/2}" y="{pad-20}" text-anchor="middle" font-weight="bold">'
        f'AAD regret bound across decoder leakage</text>',
    ]
    # Curve
    points = [(x_pixel(e), y_pixel(d)) for e, d in zip(epses, deltas)]
    path = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    parts.append(f'<path d="{path}" stroke="#1f3a93" stroke-width="2.5" fill="none"/>')
    # Markers
    for x, y in points:
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="#1f3a93"/>')
    # Axis ticks
    for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
        x = pad + inner_w * frac
        v = x_max * frac
        parts.append(f'<line x1="{x}" y1="{height-pad}" x2="{x}" y2="{height-pad+4}" stroke="black"/>')
        parts.append(f'<text x="{x}" y="{height-pad+18}" text-anchor="middle">{v:.2f}</text>')
        y = pad + inner_h * (1 - frac)
        v = y_max * frac
        parts.append(f'<line x1="{pad-4}" y1="{y}" x2="{pad}" y2="{y}" stroke="black"/>')
        parts.append(f'<text x="{pad-8}" y="{y+4}" text-anchor="end">{v:.3f}</text>')
    parts.append('</svg>')
    outpath.write_text("\n".join(parts))


def parse_args():
    ap = argparse.ArgumentParser(description="S6: Δ-over-leakage expectation curve")
    ap.add_argument("--corpus", choices=["sroie", "cord", "synthetic"],
                    default="synthetic")
    ap.add_argument("--path", default=None)
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max", type=int, default=None)
    ap.add_argument("--eps_values", type=str,
                    default="0.0,0.05,0.10,0.15,0.20,0.30,0.40,0.50",
                    help="comma-separated leakage rates to evaluate")
    ap.add_argument("--out_json", default="results/s6_expectation.json")
    ap.add_argument("--out_svg",  default="results/s6_expectation.svg")
    return ap.parse_args()


def main():
    args = parse_args()
    RESULTS.mkdir(exist_ok=True)
    eps_values = [float(x) for x in args.eps_values.split(",")]

    recs = load_corpus(args.corpus, path=args.path, n=args.n,
                       seed=args.seed, max_receipts=args.max)
    per_receipt = []
    for i, r in enumerate(recs):
        if i % 50 == 0:
            print(f"[s6] receipt {i}", file=sys.stderr)
        per_receipt.append(per_receipt_probs(
            r.items_cents(), r.tau_cents(), r.gold_total_cents, eps_values))

    stats = aggregate(per_receipt, eps_values)
    Path(args.out_json).write_text(json.dumps(stats, indent=2))
    render_curve_svg(stats, Path(args.out_svg))

    # Pretty-print headline table
    print("\nE[Δ] = E[P_AAD(gold) - P_p(gold)] across leakage rates:")
    print(f"{'ε':>8}  {'E[P_p]':>10}  {'E[P_AAD]':>10}  {'E[Δ]':>10}  {'lift':>8}")
    print("-" * 60)
    for k in sorted(stats["by_eps"].keys(), key=float):
        s = stats["by_eps"][k]
        lift = s["E_P_AAD"] / s["E_P_unconstrained"] if s["E_P_unconstrained"] > 0 else float("inf")
        print(f"{float(k):>8.3f}  {s['E_P_unconstrained']:>10.4f}  "
              f"{s['E_P_AAD']:>10.4f}  {s['E_delta']:>10.4f}  {lift:>8.2f}x")
    print(f"\n[s6] wrote {args.out_json}, {args.out_svg}", file=sys.stderr)


if __name__ == "__main__":
    main()
