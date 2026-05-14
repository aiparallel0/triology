"""S: Pareto frontier of (precision, coverage) across signals and corpora.

Reviewer attack defended: 'your sigma operating point is arbitrary; softmax 
beats it; what is the value of sigma?'

For each corpus, builds the Pareto frontier of (precision, coverage) attainable by:
  - sigma alone (single point, from M/MB/MF)
  - softmax at multiple thresholds (sweep from M/MB/MF)
  - sigma AND softmax (sigma's accept set restricted to softmax-top-k for varying k)
  - sigma OR  softmax (union)

Reports the *Pareto-dominant* signal at each precision tier. If sigma+softmax 
conjunction is on the Pareto front (i.e., no single signal achieves the same 
(precision, coverage) point), the conjunction is the contribution.

CPU only. Reads M, MB, MF.
"""
import json
from pathlib import Path

RUNS = Path("runs")
OUT = RUNS / "S_pareto.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

INPUTS = [
    ("SROIE",      RUNS / "M_baseline_softmax.json"),
    ("CORD",       RUNS / "MB_cord_baseline.json"),
    ("WildReceipt", RUNS / "MF_wildreceipt_baseline.json"),
]


def pareto_front(points):
    """Given list of (coverage, precision, label) points, return the Pareto front
    where we maximize both coverage and precision."""
    pts = sorted(points, key=lambda p: (-p[1], -p[0]))  # descending precision, then coverage
    front = []
    max_cov_so_far = -1.0
    for cov, prec, lbl in pts:
        if cov > max_cov_so_far + 1e-9:
            front.append({"coverage": cov, "precision": prec, "label": lbl})
            max_cov_so_far = cov
    return front


def analyze(path):
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    summary = data.get("summary", {})
    results = data.get("results", [])
    if not results:
        return None
    n = len(results)

    points = []  # (coverage, precision, label)

    # sigma alone (single point from summary)
    s = summary.get("sigma", {})
    if s.get("coverage") is not None:
        points.append((s["coverage"], s["precision"], "sigma"))

    # softmax sweep
    for entry in summary.get("softmax_threshold_sweep", []):
        points.append((entry["coverage"], entry["precision"], f"softmax_k={entry['k']}"))

    # sigma AND softmax at various softmax-top-k
    sigma_ids = {r["id"] for r in results if r.get("sigma_accept")}
    scored = [r for r in results if r.get("softmax_score") is not None]
    scored.sort(key=lambda r: -r["softmax_score"])
    for k_frac in (0.05, 0.10, 0.20, 0.30, 0.50, 0.70, 1.0):
        k = int(round(k_frac * len(scored)))
        if k == 0: continue
        softmax_topk = set(r["id"] for r in scored[:k])
        joint = sigma_ids & softmax_topk
        if not joint: continue
        joint_correct = sum(r.get("correct", False) for r in results if r["id"] in joint)
        cov = len(joint) / n
        prec = joint_correct / max(1, len(joint))
        points.append((cov, prec, f"sigma_AND_softmax_k={k}"))

    # sigma OR softmax at various softmax-top-k
    for k_frac in (0.05, 0.10, 0.20, 0.30, 0.50, 0.70, 1.0):
        k = int(round(k_frac * len(scored)))
        if k == 0: continue
        softmax_topk = set(r["id"] for r in scored[:k])
        joint = sigma_ids | softmax_topk
        if not joint: continue
        joint_correct = sum(r.get("correct", False) for r in results if r["id"] in joint)
        cov = len(joint) / n
        prec = joint_correct / max(1, len(joint))
        points.append((cov, prec, f"sigma_OR_softmax_k={k}"))

    front = pareto_front(points)
    # Count how many Pareto-front points are sigma-involving
    sigma_on_front = sum(1 for p in front if "sigma" in p["label"])
    sigma_only_on_front = sum(1 for p in front if p["label"] == "sigma")
    softmax_only_on_front = sum(1 for p in front if p["label"].startswith("softmax_k"))

    return {
        "n_points": len(points),
        "n_pareto_front": len(front),
        "sigma_on_front": sigma_on_front,
        "sigma_alone_on_front": sigma_only_on_front > 0,
        "softmax_alone_on_front_count": softmax_only_on_front,
        "pareto_front": front,
    }


def main():
    per_corpus = {}
    for name, path in INPUTS:
        r = analyze(path)
        if r:
            per_corpus[name] = r
        else:
            per_corpus[name] = {"available": False, "reason": f"{path.name} missing"}

    summary = {
        "per_corpus": per_corpus,
        "note": (
            "Pareto front maximizes (coverage, precision). A signal is 'on the front' iff no other "
            "signal at the same precision achieves higher coverage. The contribution is justified if "
            "sigma-involving points (sigma alone OR sigma AND/OR softmax) appear on the Pareto front; "
            "if only softmax sweep points appear, sigma adds no value. If sigma AND softmax dominates "
            "all single-signal points at high precision, the conjunction is the operationally useful gate."
        ),
    }
    OUT.write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
