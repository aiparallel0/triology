"""U2: orthogonality search done with the CORRECT statistics.

U_intersection_control.py judged orthogonality by whether three
SEPARATE bootstrap CIs (L_sigma, L_random, L_correlated) failed to
overlap. Non-overlap of independent CIs is a known over-conservative
proxy: two 95% CIs can overlap substantially while the paired
difference is significant. It never tested the difference itself.

This script tests orthogonality the right way, as a pure re-analysis
of the same per-receipt accept/correct vectors produced by
MB_cord_baseline (CORD), M_baseline_softmax (SROIE) and
MF2_wildreceipt_softmax (WildReceipt). No model inference. ~5 s CPU.

Three tests, pooled and per corpus:

  T1  PAIRED-DIFFERENCE BOOTSTRAP. For each of B resamples of the
      receipts (with replacement) recompute, on the SAME resample,
      L_sigma, L_random (a fresh random k-subset) and L_correlated (a
      fresh softmax'+noise draw at the pre-calibrated scale). Record
      d_rand = L_sigma - L_random and d_corr = L_sigma - L_correlated.
      Report the 95% CI of each difference and a one-sided bootstrap
      p = fraction of resamples with d <= 0. THIS is the decisive test
      the old script omitted.

  T2  DIRECT ERROR-DECORRELATION (no intersection arithmetic, no
      coverage confound). Restrict to the softmax-accepted set S
      (top-k by softmax, k = |sigma=1|). Let w_i = 1 if receipt i in S
      is INCORRECT (a softmax error) and r_i = 1 if sigma REJECTS i.
      Orthogonal value <=> sigma rejects exactly softmax's wrong ones,
      i.e. positive phi(r, w). Permutation test: shuffle r within S
      (B_PERM times), p = fraction of permuted |phi| >= observed phi.
      This is positive evidence that sigma's decision is informative
      about softmax's errors -- the orthogonality McNemar only implies.

  T3  Verdict combines T1 and T2 honestly: orthogonality is EARNED
      iff the paired-difference 95% CI is strictly > 0 against BOTH
      controls AND T2 phi is positive with p < 0.05; PARTIAL if it
      holds against the correlated control only; otherwise NOT EARNED.

Writes runs/U2_orthogonality.json and paper/asyu/numbers_orth.tex.
"""
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "runs"
OUT_JSON = RUNS / "U2_orthogonality.json"
OUT_TEX = ROOT / "paper/asyu/numbers_orth.tex"

SOURCES = [
    ("CORD",        RUNS / "MB_cord_baseline.json",        "results"),
    ("SROIE",       RUNS / "M_baseline_softmax.json",      "results"),
    ("WildReceipt", RUNS / "MF2_wildreceipt_softmax.json", "WildReceipt_results"),
]
B_BOOT = 4000
B_PERM = 4000
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
    return [r for r in out if r["softmax"] is not None]


def precision(recs, idxs):
    if not idxs:
        return None
    return sum(recs[i]["correct"] for i in idxs) / len(idxs)


def softmax_topk(recs, k, jitter=None):
    n = len(recs)
    if jitter is None:
        order = sorted(range(n), key=lambda i: -recs[i]["softmax"])
    else:
        order = sorted(range(n), key=lambda i: -(recs[i]["softmax"] + jitter[i]))
    return set(order[:k])


def calibrate_noise(recs, k, p_target, rng):
    """Noise scale so softmax'-top-k standalone precision ~ p_target."""
    sm_vals = [r["softmax"] for r in recs]
    spread = (max(sm_vals) - min(sm_vals)) or 1.0
    best_scale, best_gap = spread * 0.5, 1e9
    for scale in [spread * s for s in
                  (0.05, 0.1, 0.2, 0.35, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0)]:
        accs = []
        for _ in range(40):
            j = [rng.gauss(0, scale) for _ in range(len(recs))]
            pp = precision(recs, list(softmax_topk(recs, k, jitter=j)))
            if pp is not None:
                accs.append(pp)
        if accs:
            gap = abs(sum(accs) / len(accs) - p_target)
            if gap < best_gap:
                best_gap, best_scale = gap, scale
    return best_scale


def quantile(sorted_a, q):
    if not sorted_a:
        return float("nan")
    return sorted_a[min(len(sorted_a) - 1, int(q * len(sorted_a)))]


def phi_coefficient(pairs):
    """phi for 2x2 of (r, w) over a list of (r_i, w_i) in {0,1}."""
    a = b = c = d = 0
    for r, w in pairs:
        if r and w:
            a += 1
        elif r and not w:
            b += 1
        elif (not r) and w:
            c += 1
        else:
            d += 1
    num = a * d - b * c
    den = math.sqrt((a + b) * (c + d) * (a + c) * (b + d))
    return (num / den) if den > 0 else 0.0, (a, b, c, d)


def analyse(recs, rng):
    n = len(recs)
    sigma_idx = {i for i in range(n) if recs[i]["sigma"]}
    k = len(sigma_idx)
    if k == 0 or k == n:
        return {"blocker": "degenerate (k=0 or k=n)"}

    sm_idx = softmax_topk(recs, k)
    p_sm = precision(recs, list(sm_idx))
    p_sig_alone = precision(recs, list(sigma_idx))
    p_sig_inter = precision(recs, list(sigma_idx & sm_idx))
    if p_sm is None or p_sig_inter is None:
        return {"blocker": "empty intersection or matched set"}
    L_sigma_obs = p_sig_inter - p_sm

    scale = calibrate_noise(recs, k, p_sig_alone, rng)

    # ---- T1: paired-difference bootstrap ----
    d_rand, d_corr, l_sigma_b = [], [], []
    for _ in range(B_BOOT):
        samp = [rng.randrange(n) for _ in range(n)]
        sub = [recs[i] for i in samp]
        si = {i for i in range(n) if sub[i]["sigma"]}
        kk = len(si)
        if kk == 0 or kk == n:
            continue
        smi = softmax_topk(sub, kk)
        pm = precision(sub, list(smi))
        ps = precision(sub, list(si & smi))
        if pm is None or ps is None:
            continue
        Ls = ps - pm
        rg = set(rng.sample(range(n), kk))
        pr = precision(sub, list(rg & smi))
        j = [rng.gauss(0, scale) for _ in range(n)]
        gi = softmax_topk(sub, kk, jitter=j)
        pc = precision(sub, list(gi & smi))
        if pr is None or pc is None:
            continue
        l_sigma_b.append(Ls)
        d_rand.append(Ls - (pr - pm))
        d_corr.append(Ls - (pc - pm))
    d_rand.sort()
    d_corr.sort()
    l_sigma_b.sort()

    def summarise(diffs):
        if not diffs:
            return {"mean": float("nan"), "ci": [float("nan"), float("nan")],
                    "p_one_sided": float("nan")}
        mean = sum(diffs) / len(diffs)
        p = sum(1 for x in diffs if x <= 0) / len(diffs)
        return {"mean": mean,
                "ci": [quantile(diffs, 0.025), quantile(diffs, 0.975)],
                "p_one_sided": p}

    t1_rand = summarise(d_rand)
    t1_corr = summarise(d_corr)
    beats_rand = (not math.isnan(t1_rand["ci"][0])) and t1_rand["ci"][0] > 0
    beats_corr = (not math.isnan(t1_corr["ci"][0])) and t1_corr["ci"][0] > 0

    # ---- T2: direct error-decorrelation within softmax-accepted set ----
    S = sorted(sm_idx)
    pairs = [(0 if i in sigma_idx else 1,            # r = sigma REJECTS
              0 if recs[i]["correct"] else 1)        # w = softmax error
             for i in S]
    phi_obs, abcd = phi_coefficient(pairs)
    rs = [r for r, _ in pairs]
    ws = [w for _, w in pairs]
    ge = 0
    for _ in range(B_PERM):
        perm = rs[:]
        rng.shuffle(perm)
        pphi, _ = phi_coefficient(list(zip(perm, ws)))
        if abs(pphi) >= abs(phi_obs):
            ge += 1
    phi_p = (ge + 1) / (B_PERM + 1)

    return {
        "n": n, "k_sigma": k, "n_intersection": len(sigma_idx & sm_idx),
        "p_sigma_alone": p_sig_alone, "p_softmax_matched": p_sm,
        "p_sigma_inter": p_sig_inter, "L_sigma": L_sigma_obs,
        "L_sigma_CI": [quantile(l_sigma_b, 0.025), quantile(l_sigma_b, 0.975)],
        "corr_gate_noise_scale": scale,
        "T1_paired_diff": {"vs_random": t1_rand, "vs_correlated": t1_corr},
        "T2_decorrelation": {
            "phi": phi_obs, "perm_p": phi_p,
            "table_sigmaRej_softmaxErr": {
                "rej_err": abcd[0], "rej_ok": abcd[1],
                "keep_err": abcd[2], "keep_ok": abcd[3]},
            "n_in_softmax_accepted": len(S)},
        "earned": ("EARNED" if (beats_rand and beats_corr
                                and phi_obs > 0 and phi_p < 0.05)
                   else "PARTIAL" if beats_corr
                   else "NOT_EARNED"),
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

    out = {"per_corpus": per_corpus, "pooled": pooled_res,
           "method": ("Paired-difference bootstrap (T1) + direct "
                      "error-decorrelation phi with permutation p (T2). "
                      "Replaces the non-overlap-of-separate-CIs proxy.")}
    if pooled_res and "earned" in pooled_res:
        t1 = pooled_res["T1_paired_diff"]
        out["verdict"] = (
            f"POOLED orthogonality: {pooled_res['earned']}. "
            f"d(sigma-random)={t1['vs_random']['mean']:.3f} "
            f"CI{[round(x,3) for x in t1['vs_random']['ci']]} "
            f"p={t1['vs_random']['p_one_sided']:.3f}; "
            f"d(sigma-correlated)={t1['vs_correlated']['mean']:.3f} "
            f"CI{[round(x,3) for x in t1['vs_correlated']['ci']]} "
            f"p={t1['vs_correlated']['p_one_sided']:.3f}; "
            f"decorrelation phi={pooled_res['T2_decorrelation']['phi']:.3f} "
            f"perm_p={pooled_res['T2_decorrelation']['perm_p']:.3f}.")

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, indent=2))

    if pooled_res and "earned" in pooled_res:
        t1 = pooled_res["T1_paired_diff"]
        d2 = pooled_res["T2_decorrelation"]
        fmtp = lambda p: (f"{p:.4f}" if 0 < p < 0.001 else f"{p:.3f}")
        OUT_TEX.parent.mkdir(parents=True, exist_ok=True)
        OUT_TEX.write_text(
            f"\\renewcommand{{\\orthEarned}}{{{pooled_res['earned']}}}\n"
            f"\\renewcommand{{\\orthDrand}}{{{t1['vs_random']['mean']:.3f}}}\n"
            f"\\renewcommand{{\\orthDrandLo}}{{{t1['vs_random']['ci'][0]:.3f}}}\n"
            f"\\renewcommand{{\\orthDrandHi}}{{{t1['vs_random']['ci'][1]:.3f}}}\n"
            f"\\renewcommand{{\\orthDrandP}}{{{fmtp(t1['vs_random']['p_one_sided'])}}}\n"
            f"\\renewcommand{{\\orthDcorr}}{{{t1['vs_correlated']['mean']:.3f}}}\n"
            f"\\renewcommand{{\\orthDcorrLo}}{{{t1['vs_correlated']['ci'][0]:.3f}}}\n"
            f"\\renewcommand{{\\orthDcorrHi}}{{{t1['vs_correlated']['ci'][1]:.3f}}}\n"
            f"\\renewcommand{{\\orthDcorrP}}{{{fmtp(t1['vs_correlated']['p_one_sided'])}}}\n"
            f"\\renewcommand{{\\orthPhi}}{{{d2['phi']:.3f}}}\n"
            f"\\renewcommand{{\\orthPhiP}}{{{fmtp(d2['perm_p'])}}}\n"
        )
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
