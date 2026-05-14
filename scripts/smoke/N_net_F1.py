"""N: net-F1 / cost-sensitive deployment analysis.

Reviewer attack defended: 'sigma trades precision for coverage; net deployment
value unclear.'

Reads M (SROIE), MB (CORD), MF (WildReceipt). For each corpus computes:
  - base_F1: correct_all / n (no abstention, accept everything)
  - sigma net-F1: correct_sigma_accepted / n (rejected counted as 0)
  - softmax net-F1: same for softmax_matched accepts
  - intersect net-F1: correct in (sigma AND softmax) / n
  - union net-F1:     correct in (sigma OR  softmax) / n

Then with reject penalty lambda in {0, 0.1, 0.3, 0.5, 1.0}:
  utility(gate) = correct_accepted - lambda * rejected

The winning gate at each lambda is the deployment recommendation.

CPU only. ~5 sec.
"""
import json
from pathlib import Path

RUNS = Path("runs")
OUT = RUNS / "N_net_F1.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

INPUTS = [
    ("SROIE",      RUNS / "M_baseline_softmax.json"),
    ("CORD",       RUNS / "MB_cord_baseline.json"),
    ("WildReceipt", RUNS / "MF_wildreceipt_baseline.json"),
]
LAMBDAS = [0.0, 0.1, 0.3, 0.5, 1.0]


def analyze(path):
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    results = data.get("results", [])
    if not results:
        return None
    n = len(results)
    correct_all = sum(r.get("correct", False) for r in results)
    base_F1 = correct_all / n

    sigma_accept = [r for r in results if r.get("sigma_accept")]
    sigma_correct = sum(r.get("correct", False) for r in sigma_accept)

    # Recover softmax-matched accept set from sweep at matched coverage
    scored = [r for r in results if r.get("softmax_score") is not None]
    scored.sort(key=lambda r: -r["softmax_score"])
    k_match = len(sigma_accept)
    softmax_match = scored[:k_match] if k_match else []
    softmax_correct = sum(r.get("correct", False) for r in softmax_match)

    sigma_ids = {r["id"] for r in sigma_accept}
    softmax_ids = {r["id"] for r in softmax_match}
    union_ids = sigma_ids | softmax_ids
    intersect_ids = sigma_ids & softmax_ids
    union_correct = sum(r.get("correct", False) for r in results if r["id"] in union_ids)
    intersect_correct = sum(r.get("correct", False) for r in results if r["id"] in intersect_ids)

    gates = {
        "accept_all":  {"n_accept": n,               "n_correct": correct_all,      "n_reject": 0},
        "sigma":       {"n_accept": len(sigma_ids),  "n_correct": sigma_correct,    "n_reject": n - len(sigma_ids)},
        "softmax":     {"n_accept": len(softmax_ids),"n_correct": softmax_correct,  "n_reject": n - len(softmax_ids)},
        "intersect":   {"n_accept": len(intersect_ids), "n_correct": intersect_correct, "n_reject": n - len(intersect_ids)},
        "union":       {"n_accept": len(union_ids),  "n_correct": union_correct,    "n_reject": n - len(union_ids)},
    }
    for g in gates.values():
        g["net_F1"] = g["n_correct"] / n
        g["precision"] = g["n_correct"] / max(1, g["n_accept"])
        g["coverage"] = g["n_accept"] / n

    # Utility curve
    utility = {}
    for lam in LAMBDAS:
        scores = {name: g["n_correct"] - lam * g["n_reject"] for name, g in gates.items()}
        winner = max(scores, key=scores.get)
        utility[f"lambda={lam}"] = {"scores": scores, "winner": winner}

    return {
        "n": n,
        "base_F1": base_F1,
        "gates": gates,
        "utility_by_lambda": utility,
    }


def main():
    per_corpus = {}
    for name, path in INPUTS:
        r = analyze(path)
        if r:
            per_corpus[name] = r
        else:
            per_corpus[name] = {"available": False, "reason": f"{path.name} missing or empty"}

    summary = {
        "per_corpus": per_corpus,
        "note": (
            "net_F1 = correct_accepted / n_total (rejected counts as 0). Compare across gates. "
            "At lambda=0 (no reject penalty), the accept-all baseline (=base_F1) is hard to beat "
            "unless precision >> base_F1 on accepted set. At lambda>0, abstention has value: gates "
            "that reject confidently-wrong predictions win. The winner at each lambda is the "
            "deployment recommendation for that cost regime."
        ),
    }
    OUT.write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
