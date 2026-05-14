"""fig_pareto: coverage-precision Pareto frontier per corpus.

Reads runs/PAPER_TABLE.json (T6_pareto_front).
Writes paper/asyu/figures/fig_pareto.pdf.

Two panels (CORD, SROIE). Points labelled by signal (sigma, softmax_k=..., etc.).
"""
import json
from pathlib import Path
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / "runs"
OUT = Path(__file__).parent / "fig_pareto.pdf"


def short_label(lbl):
    if lbl == "sigma": return r"$\sigma$"
    if "AND" in lbl: return r"$\sigma\sqcap$smax"
    if "OR" in lbl: return r"$\sigma\sqcup$smax"
    if lbl.startswith("softmax_k"): return f"smax k={lbl.split('=')[1]}"
    return lbl


def main():
    fronts = json.loads((RUNS / "PAPER_TABLE.json").read_text())["T6_pareto_front"]

    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.6), sharey=True)
    for ax, corpus in zip(axes, ["CORD", "SROIE"]):
        front = fronts[corpus]
        xs = [pt["coverage"] for pt in front]
        ys = [pt["precision"] for pt in front]
        ax.plot(xs, ys, "o-", color="#1f77b4", markersize=5, linewidth=1)
        for pt in front:
            lbl = short_label(pt["label"])
            ax.annotate(lbl, (pt["coverage"], pt["precision"]),
                        textcoords="offset points", xytext=(4, 4),
                        fontsize=7)
        ax.set_xlabel("Coverage")
        ax.set_title(corpus)
        ax.set_xlim(0, 1.05)
        ax.set_ylim(0.65, 1.03)
        ax.axhline(1.0, color="gray", lw=0.5, ls="--")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("Precision")
    fig.suptitle("Coverage–precision Pareto frontier", fontsize=10.5)
    fig.tight_layout()
    fig.savefig(OUT, bbox_inches="tight")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
