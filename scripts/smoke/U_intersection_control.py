"""U: is the sigma-softmax intersection lift REAL or a mechanical artefact?

Reviewer attack defended (the strongest one against Paper 1):
  "Intersecting any two better-than-random gates with imperfectly
   correlated errors always raises precision and drops coverage. Your
   0.988 vs 0.948 headline could be that generic effect, not evidence
   of sigma-softmax orthogonality."

This is a pure re-analysis of the per-receipt accept/correct vectors
already produced by M_baseline_softmax (SROIE), MB_cord_baseline
(CORD), and MF2_wildreceipt_softmax (WildReceipt). No model inference.

For each corpus and pooled we compute the intersection lift
  L = P(sigma & softmax) - P(softmax at matched coverage)
and compare it against two controls at the SAME coverage:

  (A) RANDOM gate: a gate that accepts a uniformly random subset of
      size |sigma_accept|. It carries no information, so its errors are
      independent of correctness; E[L_random] ~ 0. This isolates the
      pure coverage-reduction effect. If L_sigma >> L_random the lift
      is not merely "intersecting shrinks coverage".

  (B) CORRELATED good gate: softmax' = softmax_score + Gaussian noise,
      with the noise scale calibrated per corpus so softmax' has the
      SAME standalone precision as sigma. softmax' is a second gate of
      sigma-equal quality but built FROM softmax (non-independent), so
      intersecting it with softmax cannot add orthogonal information;
      E[L_corr] ~ 0. If L_sigma >> L_corr the lift comes from sigma's
      errors being decorrelated from softmax's, i.e. genuine
      orthogonality, not "any second decent gate".

Bootstrap 95% CIs (B=2000) on every lift. Verdict: orthogonality is
earned iff the L_sigma CI lies strictly above both control CIs.

Writes runs/U_intersection_control.json and
paper/asyu/numbers_control.tex. Pure CPU, ~5 sec.
"""
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "runs"
OUT_JSON = RUNS / "U_intersection_control.json"
OUT_TEX = ROOT / "paper/asyu/numbers_control.tex"

SOURCES = [
    ("CORD",        RUNS / "MB_cord_baseline.json",       "results"),
    ("SROIE",       RUNS / "M_baseline_softmax.json",     "results"),
    ("WildReceipt", RUNS / "MF2_wildreceipt_softmax.json", "WildReceipt_results"),
]
B_BOOT = 2000
N_RANDOM = 1000
N_CORR = 1000
SEED = 0


def load_records(path, key):
    if not path.exists():
        return None
    d = json.loads(path.read_text())
    recs = d.get(key) or d.get("results") or d.get("WildReceipt_results")
    out = []
    for r in recs or []:
        s = r.get("softmax_score")
        out.append({
            "correct": bool(r.get("correct", False)),
            "softmax": float(s) if s is not None else None,
            "sigma": bool(r.get("sigma_accept", r.get("in_T", False))),
        })
    # keep only receipts with a usable softmax score (needed for the gate)
    return [r for r in out if r["softmax"] is not None]


def precision(recs, idxs):
    if not idxs:
        return None
    return sum(recs[i]["correct"] for i in idxs) / len(idxs)


def softmax_topk(recs, k, jitter=None, rng=None):
    """Indices of the top-k receipts by softmax (optionally noised)."""
    n = len(recs)
    if jitter is None:
        order = sorted(range(n), key=lambda i: -recs[i]["softmax"])
    else:
        order = sorted(range(n), key=lambda i: -(recs[i]["softmax"] + jitter[i]))
    return set(order[:k])


def analyse(recs, rng):
    n = len(recs)
    sigma_idx = {i for i in range(n) if recs[i]["sigma"]}
    k = len(sigma_idx)
    if k == 0 or k == n:
        return None
    sm_idx = softmax_topk(recs, k)

    p_sm_matched = precision(recs, list(sm_idx))
    inter = sigma_idx & sm_idx
    p_sigma_inter = precision(recs, list(inter))
    p_sigma_alone = precision(recs, list(sigma_idx))
    if p_sigma_inter is None or p_sm_matched is None:
        return None
    L_sigma = p_sigma_inter - p_sm_matched

    # ---- Control A: random gate at matched coverage ----
    randL = []
    allidx = list(range(n))
    for _ in range(N_RANDOM):
        rg = set(rng.sample(allidx, k))
        ri = rg & sm_idx
        pr = precision(recs, list(ri))
        if pr is not None:
            randL.append(pr - p_sm_matched)
    randL.sort()

    # ---- Control B: correlated good gate (softmax' calibrated to
    #      sigma's standalone precision) ----
    sm_vals = [r["softmax"] for r in recs]
    spread = (max(sm_vals) - min(sm_vals)) or 1.0
    # find a noise scale so softmax'-top-k standalone precision ~ p_sigma_alone
    best_scale, best_gap = spread * 0.5, 1e9
    for scale in [spread * s for s in (0.05, 0.1, 0.2, 0.35, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0)]:
        accs = []
        for _ in range(40):
            j = [rng.gauss(0, scale) for _ in range(n)]
            gi = softmax_topk(recs, k, jitter=j)
            pp = precision(recs, list(gi))
            if pp is not None:
                accs.append(pp)
        if accs:
            mean_acc = sum(accs) / len(accs)
            gap = abs(mean_acc - p_sigma_alone)
            if gap < best_gap:
                best_gap, best_scale = gap, scale
    corrL = []
    for _ in range(N_CORR):
        j = [rng.gauss(0, best_scale) for _ in range(n)]
        gi = softmax_topk(recs, k, jitter=j)
        ci = gi & sm_idx
        pc = precision(recs, list(ci))
        if pc is not None:
            corrL.append(pc - p_sm_matched)
    corrL.sort()

    # ---- Bootstrap CI on the observed sigma lift ----
    bootL = []
    for _ in range(B_BOOT):
        samp = [rng.randrange(n) for _ in range(n)]
        sub = [recs[i] for i in samp]
        si = {i for i in range(n) if sub[i]["sigma"]}
        kk = len(si)
        if kk == 0 or kk == n:
            continue
        smi = softmax_topk(sub, kk)
        pm = precision(sub, list(smi))
        pii = precision(sub, list(si & smi))
        if pm is not None and pii is not None:
            bootL.append(pii - pm)
    bootL.sort()

    def ci(a):
        if not a:
            return (float("nan"), float("nan"))
        return (a[int(0.025 * len(a))], a[int(0.975 * len(a))])

    sig_lo, sig_hi = ci(bootL)
    rnd_lo, rnd_hi = ci(randL)
    cor_lo, cor_hi = ci(corrL)
    earned = (not math.isnan(sig_lo)) and sig_lo > rnd_hi and sig_lo > cor_hi

    return {
        "n": n, "k_sigma": k, "n_intersection": len(inter),
        "p_sigma_alone": p_sigma_alone,
        "p_softmax_matched": p_sm_matched,
        "p_sigma_inter": p_sigma_inter,
        "L_sigma": L_sigma,
        "L_sigma_CI": [sig_lo, sig_hi],
        "L_random_mean": sum(randL) / len(randL) if randL else float("nan"),
        "L_random_CI": [rnd_lo, rnd_hi],
        "L_correlated_mean": sum(corrL) / len(corrL) if corrL else float("nan"),
        "L_correlated_CI": [cor_lo, cor_hi],
        "corr_gate_noise_scale": best_scale,
        "orthogonality_earned": earned,
    }


def main():
    rng = random.Random(SEED)
    per_corpus = {}
    pooled = []
    for name, path, key in SOURCES:
        recs = load_records(path, key)
        if recs is None:
            per_corpus[name] = {"implemented": False,
                                "blocker": f"missing {path.name}; run its baseline script"}
            continue
        pooled.extend(recs)
        res = analyse(recs, random.Random(SEED + hash(name) % 1000))
        per_corpus[name] = res if res else {"blocker": "degenerate (k=0 or k=n)"}

    pooled_res = analyse(pooled, random.Random(SEED + 7)) if pooled else None

    out = {
        "per_corpus": per_corpus,
        "pooled": pooled_res,
        "method": (
            "L = P(sigma & softmax) - P(softmax @ matched coverage). "
            "Control A = random gate (no info) @ matched coverage; "
            "Control B = softmax'+noise calibrated to sigma's standalone "
            "precision (a second good but softmax-derived gate). "
            "Orthogonality earned iff L_sigma 95% CI lies strictly above "
            "both control CIs."),
    }
    earned_corpora = [k for k, v in per_corpus.items()
                      if isinstance(v, dict) and v.get("orthogonality_earned")]
    out["verdict"] = (
        f"sigma lift exceeds BOTH the random-gate and the "
        f"correlated-good-gate controls on: {', '.join(earned_corpora) or 'NONE'}. "
        + (f"Pooled L_sigma={pooled_res['L_sigma']:.3f} "
           f"CI{[round(x,3) for x in pooled_res['L_sigma_CI']]} vs "
           f"random CI{[round(x,3) for x in pooled_res['L_random_CI']]} and "
           f"correlated CI{[round(x,3) for x in pooled_res['L_correlated_CI']]}."
           if pooled_res else ""))

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, indent=2))

    if pooled_res:
        OUT_TEX.parent.mkdir(parents=True, exist_ok=True)
        OUT_TEX.write_text(
            f"\\renewcommand{{\\ctrlLsigma}}{{{pooled_res['L_sigma']:.3f}}}\n"
            f"\\renewcommand{{\\ctrlLsigmaLo}}{{{pooled_res['L_sigma_CI'][0]:.3f}}}\n"
            f"\\renewcommand{{\\ctrlLsigmaHi}}{{{pooled_res['L_sigma_CI'][1]:.3f}}}\n"
            f"\\renewcommand{{\\ctrlLrand}}{{{pooled_res['L_random_mean']:.3f}}}\n"
            f"\\renewcommand{{\\ctrlLrandHi}}{{{pooled_res['L_random_CI'][1]:.3f}}}\n"
            f"\\renewcommand{{\\ctrlLcorr}}{{{pooled_res['L_correlated_mean']:.3f}}}\n"
            f"\\renewcommand{{\\ctrlLcorrHi}}{{{pooled_res['L_correlated_CI'][1]:.3f}}}\n"
        )
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
