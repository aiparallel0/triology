"""fig_reliability: sigma precision by reachable-set size on CORD.

Reads runs/sigma_reliability_cord.json.
Writes paper/asyu/figures/fig_reliability.pdf.

Single-panel bar chart with precision per |T| bin; n_accept annotated above
each bar. The dip at |T| in [5,9] is the headline (single CORD miss).
"""
import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / "runs"
OUT = Path(__file__).parent / "fig_reliability.pdf"


def main():
    data = json.loads((RUNS / "sigma_reliability_cord.json").read_text())
    by_bin = data["by_T_size_bin"]
    order = ["1-1", "2-4", "5-9", "10-49", "50-199", "200-9999"]
    bins = [b for b in order if b in by_bin]

    precisions = [by_bin[b]["precision"] for b in bins]
    accepts = [by_bin[b]["n_accepted"] for b in bins]

    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    x = np.arange(len(bins))
    bars = ax.bar(x, precisions, color="#1f77b4")
    for i, (p, n) in enumerate(zip(precisions, accepts)):
        ax.annotate(f"{p:.3f}\n(n={n})", (i, p),
                    ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels([b.replace("-", "–") for b in bins])
    ax.set_xlabel(r"Reachable-set size $|T(M)|$")
    ax.set_ylabel("Accept precision")
    ax.set_ylim(0.75, 1.05)
    ax.axhline(1.0, color="gray", lw=0.5, ls="--")
    ax.grid(axis="y", alpha=0.3)
    ax.set_title(r"$\sigma$ reliability by witness-set size (CORD-v2)",
                 fontsize=10.5)
    fig.tight_layout()
    fig.savefig(OUT, bbox_inches="tight")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
