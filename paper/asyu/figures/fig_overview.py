"""fig_overview: headline orthogonality bar chart for ASYU paper.

Reads runs/PAPER_TABLE.json (T1_headline).
Writes paper/asyu/figures/fig_overview.pdf.

Two panels (CORD, SROIE). Bars: sigma / softmax-matched / sigma ⊓ softmax /
sigma-only. The intersection bar is visually emphasised (darker fill,
hatching, bold annotation) since it carries the headline finding.
"""
import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / "runs"
OUT = Path(__file__).parent / "fig_overview.pdf"


def n_only(sigma_n, intersect_n):
    if sigma_n is None or intersect_n is None: return None
    return sigma_n - intersect_n


def main():
    data = json.loads((RUNS / "PAPER_TABLE.json").read_text())["T1_headline"]
    data = [r for r in data if r["corpus"] in ("CORD", "SROIE")]

    sigma_n_by_corpus = {"CORD": 55, "SROIE": 75}

    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.4), sharey=True)
    labels = [r"$\sigma$", "softmax\n(matched)",
              r"$\sigma\sqcap$softmax", r"$\sigma$-only"]
    colors = ["#1f77b4", "#ff7f0e", "#1a5e1a", "#d62728"]  # intersect = darker green
    hatches = ["", "", "//", ""]
    edges = ["black", "black", "black", "black"]
    edge_widths = [0.5, 0.5, 1.5, 0.5]

    for ax, row in zip(axes, data):
        sigma_n = sigma_n_by_corpus[row["corpus"]]
        sigma_only_n = n_only(sigma_n, row["intersect_n"])
        vals = [
            row["sigma_precision"], row["softmax_precision"],
            row["intersect_precision"], row["sigma_only_precision"],
        ]
        ns = [sigma_n, sigma_n, row["intersect_n"], sigma_only_n]

        x = np.arange(len(labels))
        ax.bar(x, [v if v is not None else 0 for v in vals],
               color=colors, hatch=hatches, edgecolor=edges, linewidth=edge_widths)
        for i, (v, n) in enumerate(zip(vals, ns)):
            if v is None: continue
            fontweight = "bold" if i == 2 else "normal"
            ax.annotate(f"{v:.3f}\n(n={n})", (i, v),
                        ha="center", va="bottom", fontsize=8,
                        fontweight=fontweight)

        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=9)
        ax.set_title(f"{row['corpus']}  (n={row['n']})", fontsize=11)
        ax.set_ylim(0.70, 1.05)
        ax.axhline(1.0, color="gray", lw=0.5, ls="--")
        ax.grid(axis="y", alpha=0.3)

    axes[0].set_ylabel("Accept precision")
    fig.suptitle(
        r"$\sigma$ is softmax-orthogonal: $\sigma\sqcap$softmax precision $=1.0$ on both corpora (hatched bars)",
        fontsize=10.5,
    )
    fig.tight_layout()
    fig.savefig(OUT, bbox_inches="tight")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
