"""U4: solidify the per-corpus intersection claim with the existing
CORD / SROIE / WildReceipt data only -- no new corpus, no model.

A reviewer worry on Paper 1 is that SROIE's intersection cell is
small (n=15). The correct response is not to retreat from the claim
but to report it the way multi-corpus selective-prediction work in
this field does:

  P1 PER-CORPUS WILSON LOWER BOUND. For each corpus, the 95% Wilson
     lower bound on intersection precision -- the honest floor that
     already accounts for small n (SROIE's 15/15 does not become
     1.000, it becomes its Wilson floor). Report the min: the
     weakest corpus's guaranteed floor.

  P2 CORPUS-STRATIFIED CLUSTER BOOTSTRAP. Resample receipts WITH
     replacement WITHIN each corpus (corpus = stratum), recompute the
     pooled intersection precision, 5000 times -> a 95% CI that
     respects corpus structure rather than pretending the receipts
     are exchangeable across corpora. This is the defensible pooled
     estimate.

  P3 LEAVE-ONE-CORPUS-OUT. Drop each corpus in turn (in particular
     the small-n SROIE) and recompute the pooled intersection
     precision + Wilson LB. If the headline survives every drop, the
     claim does not rest on any single corpus -- robustness, not
     fragility.

Counts are read from runs/PAPER_TABLE.json T1_headline (the three
corpora the reviewers care about: CORD/SROIE Donut + WildReceipt
LayoutLMv3). Pure CPU. Writes runs/U4_percorpus.json and
paper/asyu/numbers_percorpus.tex.
"""
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "runs"
OUT_JSON = RUNS / "U4_percorpus.json"
OUT_TEX = ROOT / "paper/asyu/numbers_percorpus.tex"
NBOOT = 5000
Z = 1.959963984540054  # 95% two-sided


def wilson_lo(k, n):
    if n == 0:
        return float("nan")
    p = k / n
    z2 = Z * Z
    denom = 1.0 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    half = (Z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))) / denom
    return center - half


def main():
    random.seed(20240517)
    table = json.loads((RUNS / "PAPER_TABLE.json").read_text())["T1_headline"]
    order = {"CORD": 0, "SROIE": 1, "WildReceipt": 2}
    rows = sorted([r for r in table if r["corpus"] in order],
                  key=lambda r: order[r["corpus"]])

    # Per-corpus accepted intersection cell: n accepted, k correct.
    cells = {}
    for r in rows:
        n = r["intersect_n"]
        k = r["intersect_corr"]
        cells[r["corpus"]] = {"n": n, "k": k,
                              "precision": k / n if n else float("nan"),
                              "wilson_lo": round(wilson_lo(k, n), 4)}

    min_corpus = min(cells, key=lambda c: cells[c]["wilson_lo"])

    tot_n = sum(c["n"] for c in cells.values())
    tot_k = sum(c["k"] for c in cells.values())
    pooled_point = tot_k / tot_n
    pooled_wilson = wilson_lo(tot_k, tot_n)

    # P2 corpus-stratified cluster bootstrap.
    vecs = {name: [1] * c["k"] + [0] * (c["n"] - c["k"])
            for name, c in cells.items()}
    boot = []
    for _ in range(NBOOT):
        bk = bn = 0
        for v in vecs.values():
            m = len(v)
            s = 0
            for _ in range(m):
                s += v[random.randrange(m)]
            bk += s
            bn += m
        boot.append(bk / bn)
    boot.sort()
    ci_lo = boot[int(0.025 * NBOOT)]
    ci_hi = boot[int(0.975 * NBOOT)]

    # P3 leave-one-corpus-out.
    loo = {}
    for drop in cells:
        keep = [name for name in cells if name != drop]
        n = sum(cells[x]["n"] for x in keep)
        k = sum(cells[x]["k"] for x in keep)
        loo["drop_" + drop] = {"corpora_kept": keep, "n": n, "k": k,
                               "precision": round(k / n, 4),
                               "wilson_lo": round(wilson_lo(k, n), 4)}
    loo_min_wilson = min(v["wilson_lo"] for v in loo.values())

    survives = (pooled_wilson > 0.95 and loo_min_wilson > 0.95)
    out = {
        "method": ("per-corpus Wilson LB + corpus-stratified cluster "
                   "bootstrap + leave-one-corpus-out"),
        "per_corpus": cells,
        "weakest_corpus": min_corpus,
        "weakest_corpus_wilson_lo": cells[min_corpus]["wilson_lo"],
        "pooled": {"n": tot_n, "k": tot_k,
                   "precision": round(pooled_point, 4),
                   "wilson_lo": round(pooled_wilson, 4),
                   "strat_boot_ci": [round(ci_lo, 4), round(ci_hi, 4)],
                   "n_boot": NBOOT},
        "leave_one_corpus_out": loo,
        "loo_min_wilson_lo": loo_min_wilson,
        "headline_survives_every_drop": bool(survives),
        "verdict": (
            (f"Pooled intersection precision {round(pooled_point,4)} over "
             f"n={tot_n} accepted receipts across all three corpora; "
             f"corpus-stratified cluster bootstrap 95% CI "
             f"[{round(ci_lo,4)}, {round(ci_hi,4)}] and Wilson lower "
             f"bound {round(pooled_wilson,4)}. The weakest single corpus "
             f"({min_corpus}) still has a Wilson floor of "
             f"{cells[min_corpus]['wilson_lo']}, and dropping ANY corpus "
             f"(incl. small-n SROIE) leaves the pooled Wilson LB at "
             f">={loo_min_wilson}. The intersection claim does not rest "
             f"on any one corpus; it strengthens under the standard "
             f"stratified treatment."
             if survives else
             f"Pooled Wilson LB {round(pooled_wilson,4)} / leave-one-out "
             f"min {loo_min_wilson}: the per-corpus claim is genuinely "
             f"sensitive to corpus choice and must be scoped. Reported "
             f"straight.")),
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, indent=2))

    g = lambda x: f"{x:.4f}" if isinstance(x, float) else str(x)
    lines = [
        "% Auto-generated by scripts/smoke/U4_percorpus_solidify.py",
        f"\\renewcommand{{\\pcPoolPrec}}{{{g(round(pooled_point,4))}}}",
        f"\\renewcommand{{\\pcPoolN}}{{{tot_n}}}",
        f"\\renewcommand{{\\pcPoolWilson}}{{{g(round(pooled_wilson,4))}}}",
        f"\\renewcommand{{\\pcBootLo}}{{{g(round(ci_lo,4))}}}",
        f"\\renewcommand{{\\pcBootHi}}{{{g(round(ci_hi,4))}}}",
        f"\\renewcommand{{\\pcWeakCorpus}}{{{min_corpus}}}",
        f"\\renewcommand{{\\pcWeakWilson}}{{{g(cells[min_corpus]['wilson_lo'])}}}",
        f"\\renewcommand{{\\pcLooMinWilson}}{{{g(loo_min_wilson)}}}",
        f"\\renewcommand{{\\pcCordWilson}}{{{g(cells['CORD']['wilson_lo'])}}}",
        f"\\renewcommand{{\\pcSroieWilson}}{{{g(cells['SROIE']['wilson_lo'])}}}",
        f"\\renewcommand{{\\pcWrWilson}}{{{g(cells['WildReceipt']['wilson_lo'])}}}",
        f"\\renewcommand{{\\pcSurvives}}{{{'yes' if survives else 'no'}}}",
    ]
    OUT_TEX.write_text("\n".join(lines) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
