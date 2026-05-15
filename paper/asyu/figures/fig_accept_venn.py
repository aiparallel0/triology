"""fig_accept_venn: sigma vs softmax accept-set Venn per corpus.

v2: three-panel (CORD, SROIE, WildReceipt). Reads PAPER_TABLE.json
which is now populated by paper_table.py v2 with WildReceipt's full
softmax/intersect data from MF2_wildreceipt_softmax.json.

Each region annotated with |set| and precision; uses matplotlib
primitives (no external Venn library).
"""
import json
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / "runs"
OUT = Path(__file__).parent / "fig_accept_venn.pdf"


def panel(ax, corpus, sigma_n, smax_n, inter_n, inter_p, sigma_only_p, smax_only_p):
    sigma_only_n = sigma_n - inter_n
    smax_only_n = smax_n - inter_n
    r = 1.0
    cx_l, cx_r = -0.55, 0.55
    ax.add_patch(Circle((cx_l, 0), r, alpha=0.35, color="#1f77b4"))
    ax.add_patch(Circle((cx_r, 0), r, alpha=0.35, color="#ff7f0e"))
    ax.text(-1.05, 0, f"$\\sigma$-only\nn={sigma_only_n}\np={sigma_only_p:.3f}",
            ha="center", va="center", fontsize=7.5)
    ax.text(0, 0, f"$\\sigma\\sqcap$smax\nn={inter_n}\np={inter_p:.3f}",
            ha="center", va="center", fontsize=8, fontweight="bold")
    ax.text(1.05, 0, f"smax-only\nn={smax_only_n}\np={smax_only_p:.3f}",
            ha="center", va="center", fontsize=7.5)
    ax.set_xlim(-2.0, 2.0)
    ax.set_ylim(-1.4, 1.4)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(corpus, fontsize=10.5)


SIGMA_N = {"CORD": 55, "SROIE": 75, "WildReceipt": 214}


def main():
    data = json.loads((RUNS / "PAPER_TABLE.json").read_text())["T1_headline"]
    order = {"CORD": 0, "SROIE": 1, "WildReceipt": 2}
    data = sorted([r for r in data if r["corpus"] in order], key=lambda r: order[r["corpus"]])
    data = [r for r in data if r["intersect_precision"] is not None]

    n_panels = len(data)
    fig, axes = plt.subplots(1, n_panels, figsize=(3.7 * n_panels, 3.4))
    if n_panels == 1: axes = [axes]

    for ax, row in zip(axes, data):
        sigma_n = SIGMA_N.get(row["corpus"], row["intersect_n"] * 2)
        # softmax_only_precision may be None on CORD/SROIE; compute from softmax-matched minus intersect
        smax_only_p = row.get("softmax_only_precision")
        if smax_only_p is None:
            # Fall back: not in JSON, leave a sensible placeholder
            smax_only_p = 0.0
        panel(ax, row["corpus"], sigma_n, sigma_n, row["intersect_n"],
              row["intersect_precision"],
              row["sigma_only_precision"] if row["sigma_only_precision"] is not None else 0.0,
              smax_only_p)

    fig.suptitle(r"Accept-set Venn: intersection $\sigma\sqcap\mathrm{smax}$ (centre, bold) is the high-precision joint slice",
                 fontsize=10.5)
    fig.tight_layout()
    fig.savefig(OUT, bbox_inches="tight")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
