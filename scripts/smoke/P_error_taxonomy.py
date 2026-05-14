"""P: error-type taxonomy for sigma vs softmax orthogonality.

Reviewer attack defended: 'orthogonality is statistical coincidence, not principled.'

Classifies prediction errors into types and shows sigma vs softmax catch DIFFERENT
types systematically (not just different receipts).

Error types:
  decimal_shift  pred/gold ratio in {0.01, 0.1, 10, 100} (off-by-decimal-place)
  digit_error    abs(pred - gold) < 5 (close numerically, small digit error)
  scale_error    |log10(pred/gold)| > 0.3 but not decimal-shift (10× or more off)
  sign_error     sign(pred) != sign(gold)
  completely_off otherwise
  missing_pred   pred is null

For each gate's incorrect-accepts and correct-rejects, tabulate error types.
Show sigma and softmax catch *complementary* types.

CPU only. Reads M, MB, MF.
"""
import json
import math
from collections import Counter
from pathlib import Path

RUNS = Path("runs")
OUT = RUNS / "P_error_taxonomy.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

INPUTS = [
    ("SROIE",      RUNS / "M_baseline_softmax.json"),
    ("CORD",       RUNS / "MB_cord_baseline.json"),
    ("WildReceipt", RUNS / "MF_wildreceipt_baseline.json"),
]


def classify(pred, gold):
    if pred is None:
        return "missing_pred"
    if gold is None:
        return "missing_gold"
    try:
        p, g = float(pred), float(gold)
    except (TypeError, ValueError):
        return "unparseable"
    if g == 0:
        return "scale_error" if p != 0 else "correct"
    if abs(p - g) <= 0.02:
        return "correct"
    if (p > 0) != (g > 0):
        return "sign_error"
    ratio = abs(p) / max(abs(g), 1e-9)
    log_r = math.log10(ratio) if ratio > 0 else float("inf")
    for shift in (-2, -1, 1, 2):
        if abs(log_r - shift) < 0.05:
            return "decimal_shift"
    if abs(p - g) < 5:
        return "digit_error"
    if abs(log_r) > 0.3:
        return "scale_error"
    return "completely_off"


def analyze(path):
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    results = data.get("results", [])
    if not results:
        return None

    scored = [r for r in results if r.get("softmax_score") is not None]
    scored.sort(key=lambda r: -r["softmax_score"])
    sigma_accept = [r for r in results if r.get("sigma_accept")]
    k_match = len(sigma_accept)
    softmax_match = set(r["id"] for r in scored[:k_match]) if k_match else set()
    sigma_set = set(r["id"] for r in sigma_accept)

    # Sets:
    sigma_only_accepts   = [r for r in results if r["id"] in (sigma_set - softmax_match)]
    softmax_only_accepts = [r for r in results if r["id"] in (softmax_match - sigma_set)]
    both_accepts         = [r for r in results if r["id"] in (sigma_set & softmax_match)]
    both_reject          = [r for r in results if r["id"] not in (sigma_set | softmax_match)]

    def tally(rows):
        types = Counter()
        for r in rows:
            t = classify(r.get("pred"), r.get("gold"))
            types[t] += 1
        return dict(types)

    return {
        "sigma_only_accepts": {"n": len(sigma_only_accepts), "types": tally(sigma_only_accepts)},
        "softmax_only_accepts": {"n": len(softmax_only_accepts), "types": tally(softmax_only_accepts)},
        "both_accepts": {"n": len(both_accepts), "types": tally(both_accepts)},
        "both_reject": {"n": len(both_reject), "types": tally(both_reject)},
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
            "For each receipt set (sigma_only_accepts, softmax_only_accepts, both_accepts, "
            "both_reject), classify (pred, gold) into an error-type bucket. If sigma and softmax "
            "catch DIFFERENT error types systematically, the orthogonality claim is principled. "
            "Example expected pattern: sigma_only catches decimal_shift and sign_error (arithmetic-"
            "checkable inconsistencies); softmax_only catches digit_error and completely_off (cases "
            "where the model's own probability was low). If both sets have the same error-type "
            "distribution, orthogonality is coincidence and the claim weakens."
        ),
    }
    OUT.write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
