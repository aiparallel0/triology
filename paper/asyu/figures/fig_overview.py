"""fig_overview: headline orthogonality bar chart for ASYU paper.

v2: three-panel (CORD, SROIE, WildReceipt). Reads PAPER_TABLE.json
which is now populated by paper_table.py v2 with WildReceipt's full
softmax/intersect data from MF2_wildreceipt_softmax.json.

The intersection bar is visually emphasised (darker fill, hatching,
bold annotation) since it carries the headline finding.
"""
import json
from pathlib import Path
import matplotlib
matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rcParams['ps.fonttype'] = 42
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / "runs"
OUT = Path(__file__).parent / "fig_overview.pdf"


def eval_total(row):
    """Receipts evaluated. JSON 'n' is authoritative when present;
    WildReceipt has n=null, so recover it from accept-count / coverage."""
    if row.get("n") is not None:
        return row["n"]
    cov = row.get("sigma_coverage")
    if row.get("sigma_acc") is not None and cov:
        return round(row["sigma_acc"] / cov)
    return None


def main():
    data = json.loads((RUNS / "PAPER_TABLE.json").read_text())["T1_headline"]
    # Order: CORD, SROIE, WildReceipt
    order = {"CORD": 0, "SROIE": 1, "WildReceipt": 2}
    data = sorted([r for r in data if r["corpus"] in order], key=lambda r: order[r["corpus"]])
    data = [r for r in data if r["intersect_precision"] is not None]

    n_panels = len(data)
    fig, axes = plt.subplots(1, n_panels, figsize=(3.7 * n_panels, 3.4), sharey=True)
    if n_panels == 1: axes = [axes]

    labels = [r"$\sigma$", "softmax\n(matched)",
              r"$\sigma\sqcap$smax", r"$\sigma$-only"]
    colors = ["#1f77b4", "#ff7f0e", "#1a5e1a", "#d62728"]
    hatches = ["", "", "//", ""]
    edges = ["black", "black", "black", "black"]
    edge_widths = [0.5, 0.5, 1.5, 0.5]

    for ax, row in zip(axes, data):
        # All counts come straight from PAPER_TABLE.json (internally
        # consistent); no hardcoded per-corpus table.
        sigma_n = row["sigma_acc"]
        sigma_only_n = row["sigma_only_n"]
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
                        ha="center", va="bottom", fontsize=7.5,
                        fontweight=fontweight)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=8)
        ax.set_title(f"{row['corpus']}  (n={eval_total(row)})", fontsize=10.5)
        ax.set_ylim(0.70, 1.06)
        ax.axhline(1.0, color="gray", lw=0.5, ls="--")
        ax.grid(axis="y", alpha=0.3)

    axes[0].set_ylabel("Accept precision")
    fig.suptitle(
        "Intersection σ⊓softmax (hatched, bold) exceeds both single-gate bars on all three corpora",
        fontsize=10.5,
    )
    fig.tight_layout()
    fig.savefig(OUT, bbox_inches="tight")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
