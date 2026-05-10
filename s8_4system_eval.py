"""S2 — Cross-corpus identity availability table.

Fills §IV (entire section) plus the §I/§II reachability rate citations.

For each identity in {I1, I2, I3, I4, I5} and each corpus, reports:

    availability rate   = fraction of receipts where the identity *can*
                          fire (lexical or structural prereqs met)

    soundness rate      = conditional on availability, fraction of
                          receipts where the identity *accepts the
                          gold total* (Paper 1's Proposition 1 claim)

    Wilson 95% CI       = (lower, upper) for both rates

The output table mirrors Table II of Paper 1 in shape and is the data
fixture for §IV's table:

    Identity | SROIE Task-3 (n=347) | CORD-v2 (n=100)
    ---------+----------------------+------------------
    I1       | 38.3% [33.4, 43.5]   |  0.0% [0.0, 3.7]
    I2       | 62.7% [57.6, 67.7]   | 12.4% [7.0, 19.8]
    I3       | 100.0% [98.9, 100.0] | 87.6% [80.2, 93.0]
    I4       | <synthetic / TBD>    | <synthetic / TBD>
    I5       | <synthetic / TBD>    | <synthetic / TBD>

Real-corpus runs use --corpus sroie + --corpus cord (or --corpus all).

Usage:
    python -m paper3.scripts.s2_I_coverage --corpus all \\
        --sroie /data/sroie/test --cord /data/cord/test
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

from ..data import load_corpus
from ..core.identities import (
    IDENTITY_NAMES, is_available, is_accepted,
    DEFAULT_TAX_RATE,
    i5_rule_digit_pool, i5_rule_position_aligned,
)
from ..core.stats import wilson_ci, fmt_proportion

RESULTS = Path("results")

I5_RULES = {
    "digit_pool":      i5_rule_digit_pool,
    "position_aligned": i5_rule_position_aligned,
}


def measure(receipts, i5_rule_name: str = "digit_pool") -> Dict:
    """Compute per-identity availability + soundness on the receipts."""
    from ..core.identities import _ACCEPT_FNS  # noqa
    receipts = list(receipts)  # we iterate twice
    n = len(receipts)

    out = {"n": n, "by_identity": {}}
    for ident in IDENTITY_NAMES:
        avail_count = 0
        accept_gold_count = 0
        for r in receipts:
            avail = is_available(ident, r)
            if avail:
                avail_count += 1
                if ident == "I5":
                    rule = I5_RULES[i5_rule_name]
                    from ..core.identities import i5_accepts
                    accepted = i5_accepts(r, r.gold_total_cents, rule=rule)
                else:
                    accepted = is_accepted(ident, r, r.gold_total_cents)
                if accepted:
                    accept_gold_count += 1
        avail_rate = avail_count / n if n else 0
        avail_lo, avail_hi = wilson_ci(avail_count, n)
        if avail_count:
            sound_rate = accept_gold_count / avail_count
            sound_lo, sound_hi = wilson_ci(accept_gold_count, avail_count)
        else:
            sound_rate = float("nan")
            sound_lo = sound_hi = float("nan")
        out["by_identity"][ident] = {
            "availability": {
                "count": avail_count,
                "rate":  avail_rate,
                "ci_low":  avail_lo,
                "ci_high": avail_hi,
                "fmt":   fmt_proportion(avail_count, n),
            },
            "soundness_given_avail": {
                "count": accept_gold_count,
                "rate":  sound_rate,
                "ci_low":  sound_lo,
                "ci_high": sound_hi,
                "fmt":   fmt_proportion(accept_gold_count, avail_count) if avail_count else "n/a",
            },
        }
    return out


def render_table(per_corpus: Dict[str, Dict]) -> str:
    """Markdown-ish text table — drops straight into a §IV draft."""
    corpora = list(per_corpus.keys())
    lines = []
    head = ["Identity"] + [f"{c} (n={per_corpus[c]['n']})" for c in corpora]
    widths = [max(8, max(len(h) for h in head[i:i+1])) for i in range(len(head))]
    # Header
    lines.append("Cross-corpus identity availability (Wilson 95% CIs)")
    lines.append("=" * 60)
    lines.append("  ".join(h.ljust(w) for h, w in zip(head, [10] + [25] * len(corpora))))
    lines.append("-" * 60)
    for ident in IDENTITY_NAMES:
        row = [ident]
        for c in corpora:
            row.append(per_corpus[c]["by_identity"][ident]["availability"]["fmt"])
        lines.append("  ".join(c.ljust(w) for c, w in zip(row, [10] + [25] * len(corpora))))
    lines.append("")
    lines.append("Soundness given availability:")
    lines.append("-" * 60)
    for ident in IDENTITY_NAMES:
        row = [ident]
        for c in corpora:
            row.append(per_corpus[c]["by_identity"][ident]["soundness_given_avail"]["fmt"])
        lines.append("  ".join(c.ljust(w) for c, w in zip(row, [10] + [25] * len(corpora))))
    return "\n".join(lines)


def parse_args():
    ap = argparse.ArgumentParser(description="S2: identity-coverage table")
    ap.add_argument("--corpus", choices=["sroie", "cord", "synthetic", "all"],
                    default="synthetic")
    ap.add_argument("--path", default=None)
    ap.add_argument("--sroie", default=None)
    ap.add_argument("--cord",  default=None)
    ap.add_argument("--n",     type=int, default=500)
    ap.add_argument("--seed",  type=int, default=0)
    ap.add_argument("--max",   type=int, default=None)
    ap.add_argument("--i5_rule", choices=list(I5_RULES.keys()),
                    default="digit_pool",
                    help="I5 rule to use (D3 not yet locked)")
    ap.add_argument("--out_json", default="results/s2_I_coverage.json")
    ap.add_argument("--out_txt",  default="results/s2_I_coverage.txt")
    return ap.parse_args()


def main():
    args = parse_args()
    RESULTS.mkdir(exist_ok=True)

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

    per_corpus = {}
    for label, name, path, extra in corpora:
        print(f"[s2] processing {label}...", file=sys.stderr)
        recs = load_corpus(name, path=path, n=args.n, seed=args.seed,
                           max_receipts=args.max, **extra)
        per_corpus[label] = measure(recs, i5_rule_name=args.i5_rule)
        per_corpus[label]["i5_rule"] = args.i5_rule
        per_corpus[label]["i4_rate"] = DEFAULT_TAX_RATE

    Path(args.out_json).write_text(json.dumps(per_corpus, indent=2))
    table = render_table(per_corpus)
    Path(args.out_txt).write_text(table)
    print(table)
    print(f"\n[s2] wrote {args.out_json}, {args.out_txt}", file=sys.stderr)


if __name__ == "__main__":
    main()
