"""U3: risk-coverage -- is sigma intersection actually USEFUL?

Reviewer ask for Paper 1: "you show statistical orthogonality, but is
the sigma-softmax intersection operationally better than just
thresholding softmax?" The honest answer is a risk-coverage (selective
prediction) comparison at MATCHED coverage.

Pure CPU re-analysis of the same per-receipt accept/correct vectors
(MB_cord_baseline, M_baseline_softmax, MF2_wildreceipt_softmax). No
model inference.

For a coverage grid we compare two selective predictors:
  - softmax-alone: accept the top-c fraction by softmax score.
  - sigma-gated:    accept the top-c by softmax AND sigma-accepted
                    (sigma is the arithmetic subset-sum gate), i.e.
                    the operating curve a deployer actually gets.
At each grid point the sigma-gated coverage is read off (it is <=
softmax coverage by construction); softmax-alone is evaluated at that
SAME coverage so risk is compared like-for-like. Risk = 1 - precision
on the accepted set. AURC = mean risk over the achievable coverage
range (lower is better). Paired bootstrap (same receipt resample for
both predictors) gives a CI + one-sided p on
dAURC = AURC_softmax - AURC_sigma_gated  (>0 => sigma helps).

Writes runs/U3_risk_coverage.json, paper/asyu/numbers_riskcov.tex and
paper/asyu/riskcov_curve.tex (pgfplots coordinates, pooled).
"""
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "runs"
OUT_JSON = RUNS / "U3_risk_coverage.json"
OUT_TEX = ROOT / "paper/asyu/numbers_riskcov.tex"
OUT_CURVE = ROOT / "paper/asyu/riskcov_curve.tex"
SOURCES = [
    ("CORD",        RUNS / "MB_cord_baseline.json",        "results"),
    ("SROIE",       RUNS / "M_baseline_softmax.json",      "results"),
    ("WildReceipt", RUNS / "MF2_wildreceipt_softmax.json", "WildReceipt_results"),
]
GRID = [i / 40 for i in range(1, 41)]   # coverage fractions 0.025..1.0
B_BOOT = 4000
SEED = 0


def load_records(path, key):
    if not path.exists():
        return None
    d = json.loads(path.read_text())
    recs = d.get(key) or d.get("results") or d.get("WildReceipt_results")
    out = []
    for r in recs or []:
        s = r.get("softmax_score")
        out.append({"correct": bool(r.get("correct", False)),
                    "softmax": float(s) if s is not None else None,
                    "sigma": bool(r.get("sigma_accept", r.get("in_T", False)))})
    return [r for r in out if r["softmax"] is not None]


def curves(recs):
    n = len(recs)
    order = sorted(range(n), key=lambda i: -recs[i]["softmax"])
    pts = []
    for c in GRID:
        k = max(1, int(round(c * n)))
        top = order[:k]
        inter = [i for i in top if recs[i]["sigma"]]
        if not inter:
            continue
        cov = len(inter) / n
        risk_sig = 1.0 - sum(recs[i]["correct"] for i in inter) / len(inter)
        ksoft = max(1, int(round(cov * n)))
        soft = order[:ksoft]
        risk_soft = 1.0 - sum(recs[i]["correct"] for i in soft) / len(soft)
        pts.append((cov, risk_soft, risk_sig))
    if len(pts) < 2:
        return None
    pts.sort()
    aurc_soft = sum(p[1] for p in pts) / len(pts)
    aurc_sig = sum(p[2] for p in pts) / len(pts)
    return {"points": pts, "aurc_softmax": aurc_soft,
            "aurc_sigma_gated": aurc_sig,
            "dAURC": aurc_soft - aurc_sig}


def analyse(recs, rng):
    base = curves(recs)
    if base is None:
        return {"blocker": "too few achievable coverage points"}
    n = len(recs)
    diffs = []
    for _ in range(B_BOOT):
        sub = [recs[rng.randrange(n)] for _ in range(n)]
        c = curves(sub)
        if c is not None:
            diffs.append(c["dAURC"])
    diffs.sort()

    def q(a, p):
        return a[min(len(a) - 1, int(p * len(a)))] if a else float("nan")

    ci = [q(diffs, 0.025), q(diffs, 0.975)]
    p_one = (sum(1 for x in diffs if x <= 0) / len(diffs)
             if diffs else float("nan"))
    return {
        "n": n,
        "aurc_softmax": base["aurc_softmax"],
        "aurc_sigma_gated": base["aurc_sigma_gated"],
        "dAURC_mean": base["dAURC"],
        "dAURC_ci": ci,
        "p_sigma_not_better": p_one,
        "dominates": (not math.isnan(ci[0])) and ci[0] > 0,
        "points": base["points"],
    }


def main():
    per_corpus, pooled = {}, []
    for name, path, key in SOURCES:
        recs = load_records(path, key)
        if recs is None:
            per_corpus[name] = {"blocker": f"missing {path.name}"}
            continue
        pooled.extend(recs)
        per_corpus[name] = analyse(recs, random.Random(SEED + hash(name) % 997))
    pooled_res = analyse(pooled, random.Random(SEED + 7)) if pooled else None

    powered = [k for k, v in per_corpus.items()
               if isinstance(v, dict) and v.get("dominates")]
    out = {"per_corpus": {k: {kk: vv for kk, vv in v.items() if kk != "points"}
                          if isinstance(v, dict) else v
                          for k, v in per_corpus.items()},
           "pooled": ({k: vv for k, vv in pooled_res.items() if k != "points"}
                      if pooled_res else None),
           "method": "matched-coverage risk-coverage; paired bootstrap on "
                     "dAURC = AURC_softmax - AURC_sigma_gated."}
    if pooled_res and "dAURC_mean" in pooled_res:
        out["verdict"] = (
            f"Pooled AURC: softmax-alone={pooled_res['aurc_softmax']:.3f} vs "
            f"sigma-gated={pooled_res['aurc_sigma_gated']:.3f}; "
            f"dAURC={pooled_res['dAURC_mean']:.3f} "
            f"CI{[round(x,3) for x in pooled_res['dAURC_ci']]} "
            f"p={pooled_res['p_sigma_not_better']:.3f}. "
            f"sigma-gating {'DOMINATES' if pooled_res['dominates'] else 'does NOT dominate'} "
            f"softmax-alone at matched coverage. "
            f"Per-corpus dominance on: {', '.join(powered) or 'NONE individually'}.")

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, indent=2))

    if pooled_res and "dAURC_mean" in pooled_res:
        fmtp = lambda p: (f"{p:.4f}" if 0 < p < 0.001 else f"{p:.3f}")
        OUT_TEX.parent.mkdir(parents=True, exist_ok=True)
        OUT_TEX.write_text(
            f"\\renewcommand{{\\rcAURCsoft}}{{{pooled_res['aurc_softmax']:.3f}}}\n"
            f"\\renewcommand{{\\rcAURCsig}}{{{pooled_res['aurc_sigma_gated']:.3f}}}\n"
            f"\\renewcommand{{\\rcAURCd}}{{{pooled_res['dAURC_mean']:.3f}}}\n"
            f"\\renewcommand{{\\rcAURCdLo}}{{{pooled_res['dAURC_ci'][0]:.3f}}}\n"
            f"\\renewcommand{{\\rcAURCdHi}}{{{pooled_res['dAURC_ci'][1]:.3f}}}\n"
            f"\\renewcommand{{\\rcAURCp}}{{{fmtp(pooled_res['p_sigma_not_better'])}}}\n"
            f"\\renewcommand{{\\rcEarned}}{{{'DOMINATES' if pooled_res['dominates'] else 'NO'}}}\n"
        )
        soft = " ".join(f"({c:.3f},{rs:.3f})" for c, rs, _ in pooled_res["points"])
        sig = " ".join(f"({c:.3f},{rg:.3f})" for c, _, rg in pooled_res["points"])
        OUT_CURVE.write_text(
            "% pooled risk-coverage coordinates (auto-generated)\n"
            f"\\newcommand{{\\rcCurveSoft}}{{{soft}}}\n"
            f"\\newcommand{{\\rcCurveSig}}{{{sig}}}\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
