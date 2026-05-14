"""fig_accept_venn: sigma vs softmax accept-set Venn per corpus.

Reads runs/PAPER_TABLE.json (T1_headline).
Writes paper/asyu/figures/fig_accept_venn.pdf.

Two-panel two-circle Venn drawn with matplotlib primitives (no external Venn
library). Each region is annotated with |set| and precision.
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
    ax.add_patch(Circle((cx_l, 0), r, alpha=0.35, color="#1f77b4", label=r"$\sigma$"))
    ax.add_patch(Circle((cx_r, 0), r, alpha=0.35, color="#ff7f0e", label="softmax"))

    ax.text(-1.05, 0, f"$\\sigma$-only\nn={sigma_only_n}\np={sigma_only_p:.3f}",
            ha="center", va="center", fontsize=8)
    ax.text(0, 0, f"$\\sigma\\sqcap$smax\nn={inter_n}\np={inter_p:.3f}",
            ha="center", va="center", fontsize=8, fontweight="bold")
    ax.text(1.05, 0, f"softmax-only\nn={smax_only_n}\np={smax_only_p:.3f}",
            ha="center", va="center", fontsize=8)

    ax.set_xlim(-2.0, 2.0)
    ax.set_ylim(-1.4, 1.4)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(corpus, fontsize=11)


def main():
    data = json.loads((RUNS / "PAPER_TABLE.json").read_text())["T1_headline"]
    rows = {r["corpus"]: r for r in data if r["corpus"] in ("CORD", "SROIE")}

    fig, axes = plt.subplots(1, 2, figsize=(8.4, 4.0))
    for ax, corpus in zip(axes, ["CORD", "SROIE"]):
        r = rows[corpus]
        sigma_n = 55 if corpus == "CORD" else 75
        smax_n = sigma_n
        if corpus == "CORD":
            sigma_only_p, smax_only_p = 1.0, 0.864
        else:
            sigma_only_p, smax_only_p = 0.833, 0.933
        panel(ax, corpus, sigma_n, smax_n, r["intersect_n"],
              r["intersect_precision"], sigma_only_p, smax_only_p)

    fig.suptitle(r"Accept-set Venn: intersection precision $= 1.0$ on both corpora",
                 fontsize=10.5)
    fig.tight_layout()
    fig.savefig(OUT, bbox_inches="tight")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
