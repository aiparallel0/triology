"""U5: honest per-corpus statistical rigor for the sigma/\\softmax
intersection precision (Option 1 -- pure Python stdlib only).

Operates on the corrected, LEAKAGE-FREE intersection cells:
    CORD        54 / 55   (corpus n = 200, test+validation)
    SROIE       15 / 15   (corpus n = 347)
    WildReceipt 113 / 114 (corpus n = 472)

No scipy / numpy / PyMC. The regularized incomplete beta function is
implemented from scratch (Lentz continued fraction + math.lgamma) and
used for exact-binomial tail probabilities and Beta (Jeffreys) quantiles.

Outputs:
    runs/U5_percorpus_rigor.json
    paper/asyu/numbers_percorpus_rigor.tex

Sections:
  A2  per-corpus Clopper-Pearson exact LB, Jeffreys 2.5% quantile, Wilson LB
  A3  three pooled weightings (receipt / equal-corpus / leave-one-corpus-out)
  A7  per-corpus one-sided exact-binomial TOST vs threshold 0.95
  A10 Monte-Carlo required-n for >=0.8 power at alpha=0.05 (one-sided)
  A5  within-corpus permutation test for sigma/softmax error-decorrelation,
      Stouffer (weights sqrt(n_c)) + Fisher combination -- if per-receipt
      vectors are available in the run artifacts (they are).
"""
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_JSON = ROOT / "runs/U5_percorpus_rigor.json"
OUT_TEX = ROOT / "paper/asyu/numbers_percorpus_rigor.tex"

THRESH = 0.95
ALPHA = 0.05

CORPORA = {
    "CORD":        {"k": 54,  "n": 55,  "n_corpus": 200},
    "SROIE":       {"k": 15,  "n": 15,  "n_corpus": 347},
    "WildReceipt": {"k": 113, "n": 114, "n_corpus": 472},
}

# Per-receipt artifact sources for A5 (path, list-key).
A5_SOURCES = {
    "CORD":        ("runs/MB_cord_baseline.json", "results"),
    "SROIE":       ("runs/M_baseline_softmax.json", "results"),
    "WildReceipt": ("runs/MF2_wildreceipt_softmax.json", "WildReceipt_results"),
}


# ---------------------------------------------------------------------------
# Regularized incomplete beta  I_x(a,b)  via Lentz continued fraction.
# ---------------------------------------------------------------------------
def _betacf(x, a, b):
    MAXIT, EPS, FPMIN = 300, 3.0e-12, 1.0e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        delt = d * c
        h *= delt
        if abs(delt - 1.0) < EPS:
            break
    return h


def betai(x, a, b):
    """Regularized incomplete beta I_x(a,b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    bt = math.exp(lbeta + a * math.log(x) + b * math.log1p(-x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(x, a, b) / a
    return 1.0 - bt * _betacf(1.0 - x, b, a) / b


def beta_quantile(p, a, b):
    """Inverse of I_x(a,b) by bisection (monotone in x)."""
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if betai(mid, a, b) < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def binom_sf_ge(k, n, p):
    """P(X >= k) for X ~ Binomial(n, p) via the beta identity:
       P(X >= k) = I_p(k, n-k+1)."""
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    return betai(p, k, n - k + 1)


def binom_cdf_le(k, n, p):
    """P(X <= k) = 1 - P(X >= k+1)."""
    if k >= n:
        return 1.0
    if k < 0:
        return 0.0
    return 1.0 - binom_sf_ge(k + 1, n, p)


# ---------------------------------------------------------------------------
# Interval estimators
# ---------------------------------------------------------------------------
def clopper_pearson_lo(k, n, alpha=0.05):
    """One-sided lower confidence bound (level 1-alpha)."""
    if k == 0:
        return 0.0
    if k == n:
        return alpha ** (1.0 / n)
    # Lower bound solves P(X >= k | p=lo) = alpha  =>  lo = Beta_inv(alpha; k, n-k+1)
    return beta_quantile(alpha, k, n - k + 1)


def jeffreys_lo(k, n, alpha=0.05):
    """Jeffreys 100*alpha% quantile of Beta(k+0.5, n-k+0.5)."""
    a = k + 0.5
    b = n - k + 0.5
    return beta_quantile(alpha, a, b)


def wilson_lo(k, n, z=1.959963984540054):
    if n == 0:
        return 0.0
    p = k / n
    z2 = z * z
    center = (p + z2 / (2 * n)) / (1 + z2 / n)
    margin = (z / (1 + z2 / n)) * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))
    return max(0.0, center - margin)


# ---------------------------------------------------------------------------
# A7: one-sided exact-binomial TOST vs 0.95  (H0: p <= 0.95)
# ---------------------------------------------------------------------------
def exact_binom_test_greater(k, n, p0):
    """One-sided exact-binomial p-value for H0: p <= p0 vs H1: p > p0.
       p = P(X >= k | p0)."""
    return binom_sf_ge(k, n, p0)


# ---------------------------------------------------------------------------
# A10: Monte-Carlo required-n for >=0.8 power at alpha=0.05 (one-sided)
# ---------------------------------------------------------------------------
def required_n_mc(p_hat, p0, alpha, target_power, rng, trials=4000,
                  n_max=20000):
    if p_hat <= p0:
        return None  # not powered against the null at any n
    n = 5
    while n <= n_max:
        # Exact critical value: smallest c with P(X >= c | p0) <= alpha.
        c = n
        while c >= 0 and binom_sf_ge(c, n, p0) <= alpha:
            c -= 1
        crit = c + 1
        hits = 0
        for _ in range(trials):
            x = sum(1 for _ in range(n) if rng.random() < p_hat)
            if x >= crit:
                hits += 1
        if hits / trials >= target_power:
            return n
        n = int(n * 1.5) + 1
    return None


# ---------------------------------------------------------------------------
# A5: within-corpus permutation test for sigma/softmax error-decorrelation
# ---------------------------------------------------------------------------
def load_per_receipt(path, key):
    p = ROOT / path
    if not p.exists():
        return None
    d = json.loads(p.read_text())
    recs = d.get(key) or d.get("results") or d.get("WildReceipt_results")
    if not recs:
        return None
    out = []
    for r in recs:
        s = r.get("softmax_score")
        if s is None:
            continue
        out.append({
            "correct": bool(r.get("correct", False)),
            "softmax": float(s),
            "sigma": bool(r.get("sigma_accept", r.get("in_T", False))),
        })
    return out or None


def matched_softmax_accept(recs):
    """Matched-coverage softmax acceptance: top-k by softmax_score where
       k = number of sigma accepts (same convention as U2/T_significance)."""
    k = sum(1 for r in recs if r["sigma"])
    order = sorted(range(len(recs)), key=lambda i: -recs[i]["softmax"])
    sm = set(order[:k])
    for i, r in enumerate(recs):
        r["softmax_accept"] = i in sm
    return recs


def permutation_decorrelation_p(recs, rng, n_perm=20000):
    """One-sided permutation test that sigma's accepted-set errors are
       *decorrelated* from softmax's: statistic = precision on the sigma-
       accepted-but-softmax-rejected set (sigma's orthogonal contribution).
       Under H0 (sigma carries no signal beyond softmax) the membership
       label is exchangeable within the softmax-rejected pool; we permute
       sigma membership among softmax-rejected receipts and ask how often
       the permuted sigma-only precision >= observed.
       Small one-sided p  => sigma's extra accepts are genuinely cleaner
       (error-decorrelated)."""
    sm_rej = [r for r in recs if not r["softmax_accept"]]
    if not sm_rej:
        return None, None, None
    obs_set = [r for r in sm_rej if r["sigma"]]
    m = len(obs_set)
    if m == 0:
        return None, None, None
    obs_prec = sum(r["correct"] for r in obs_set) / m
    correct_flags = [1 if r["correct"] else 0 for r in sm_rej]
    pool = len(sm_rej)
    ge = 0
    for _ in range(n_perm):
        idx = rng.sample(range(pool), m)
        s = 0
        for j in idx:
            s += correct_flags[j]
        if s / m >= obs_prec - 1e-12:
            ge += 1
    p = (ge + 1) / (n_perm + 1)
    return obs_prec, m, p


def stouffer(pvals, weights):
    """Stouffer combination of one-sided p-values (smaller p => more
       evidence). Returns combined one-sided p."""
    # z_i = Phi^{-1}(1 - p_i)
    zs = [inv_norm_cdf(1.0 - min(max(p, 1e-15), 1 - 1e-15)) for p in pvals]
    num = sum(w * z for w, z in zip(weights, zs))
    den = math.sqrt(sum(w * w for w in weights))
    z = num / den
    return 1.0 - norm_cdf(z), z


def fisher(pvals):
    """Fisher combination: -2 sum ln p ~ chi2_{2k}."""
    stat = -2.0 * sum(math.log(min(max(p, 1e-300), 1.0)) for p in pvals)
    df = 2 * len(pvals)
    # chi2 sf via regularized upper incomplete gamma (series/CF).
    return 1.0 - chi2_cdf(stat, df), stat


# --- normal & chi2 helpers (stdlib) ---------------------------------------
def norm_cdf(x):
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


def inv_norm_cdf(p):
    # Acklam's rational approximation.
    a = [-3.969683028665376e+01, 2.209460984245205e+02,
         -2.759285104469687e+02, 1.383577518672690e+02,
         -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02,
         -1.556989798598866e+02, 6.680131188771972e+01,
         -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01,
         -2.400758277161838e+00, -2.549732539343734e+00,
         4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01,
         2.445134137142996e+00, 3.754408661907416e+00]
    pl = 0.02425
    if p < pl:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p <= 1 - pl:
        q = p - 0.5
        r = q * q
        return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
               (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)
    q = math.sqrt(-2 * math.log(1 - p))
    return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
           ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)


def _lower_gamma_reg(s, x):
    """Regularized lower incomplete gamma P(s,x)."""
    if x <= 0:
        return 0.0
    if x < s + 1.0:
        # series
        term = 1.0 / s
        summ = term
        n = 1
        while True:
            term *= x / (s + n)
            summ += term
            if abs(term) < abs(summ) * 1e-14 or n > 1000:
                break
            n += 1
        return summ * math.exp(-x + s * math.log(x) - math.lgamma(s))
    # continued fraction for upper, then complement
    FPMIN = 1e-300
    b = x + 1.0 - s
    c = 1.0 / FPMIN
    d = 1.0 / b
    h = d
    for i in range(1, 1000):
        an = -i * (i - s)
        b += 2.0
        d = an * d + b
        if abs(d) < FPMIN:
            d = FPMIN
        c = b + an / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        delt = d * c
        h *= delt
        if abs(delt - 1.0) < 1e-14:
            break
    q = math.exp(-x + s * math.log(x) - math.lgamma(s)) * h
    return 1.0 - q


def chi2_cdf(x, df):
    return _lower_gamma_reg(df / 2.0, x / 2.0)


# ---------------------------------------------------------------------------
def main():
    rng = random.Random(20260517)
    result = {
        "method": "Option 1 -- pure-stdlib per-corpus rigor",
        "threshold": THRESH,
        "alpha": ALPHA,
        "cells": CORPORA,
    }

    # ---- A2: per-corpus interval estimators -----------------------------
    a2 = {}
    for name, c in CORPORA.items():
        k, n = c["k"], c["n"]
        a2[name] = {
            "k": k, "n": n, "p_hat": k / n,
            "clopper_pearson_lo": clopper_pearson_lo(k, n, ALPHA),
            "jeffreys_lo": jeffreys_lo(k, n, ALPHA),
            "wilson_lo": wilson_lo(k, n),
        }
    result["A2_per_corpus_intervals"] = a2

    # ---- A3: three pooled weightings ------------------------------------
    K = sum(c["k"] for c in CORPORA.values())
    N = sum(c["n"] for c in CORPORA.values())
    receipt_weighted = {
        "k": K, "n": N, "p_hat": K / N,
        "wilson_lo": wilson_lo(K, N),
        "clopper_pearson_lo": clopper_pearson_lo(K, N, ALPHA),
    }
    phats = [c["k"] / c["n"] for c in CORPORA.values()]
    equal_corpus = {
        "mean_p_hat": sum(phats) / len(phats),
        "per_corpus_p_hat": {nm: c["k"] / c["n"]
                             for nm, c in CORPORA.items()},
    }
    loco = {}
    names = list(CORPORA)
    for drop in names:
        kept = [m for m in names if m != drop]
        kk = sum(CORPORA[m]["k"] for m in kept)
        nn = sum(CORPORA[m]["n"] for m in kept)
        loco[f"drop_{drop}"] = {
            "kept": kept, "k": kk, "n": nn, "p_hat": kk / nn,
            "wilson_lo": wilson_lo(kk, nn),
        }
    result["A3_pooled_weightings"] = {
        "receipt_weighted": receipt_weighted,
        "equal_corpus_weighted": equal_corpus,
        "leave_one_corpus_out": loco,
    }

    # ---- A7: per-corpus one-sided exact-binomial TOST vs 0.95 -----------
    a7 = {}
    for name, c in CORPORA.items():
        k, n = c["k"], c["n"]
        pval = exact_binom_test_greater(k, n, THRESH)
        a7[name] = {
            "k": k, "n": n, "p_hat": k / n,
            "H0": "p <= 0.95",
            "exact_binom_p": pval,
            "pass_alpha_0.05": bool(pval < ALPHA),
        }
    pooled_p = exact_binom_test_greater(K, N, THRESH)
    a7["POOLED"] = {
        "k": K, "n": N, "p_hat": K / N, "H0": "p <= 0.95",
        "exact_binom_p": pooled_p,
        "pass_alpha_0.05": bool(pooled_p < ALPHA),
    }
    individually_pass = [nm for nm in CORPORA
                         if a7[nm]["pass_alpha_0.05"]]
    underpowered = [nm for nm in CORPORA
                    if not a7[nm]["pass_alpha_0.05"]]
    result["A7_per_corpus_TOST"] = a7

    # ---- A10: Monte-Carlo required-n ------------------------------------
    a10 = {}
    for name, c in CORPORA.items():
        ph = c["k"] / c["n"]
        rn = required_n_mc(ph, THRESH, ALPHA, 0.80, rng,
                           trials=3000, n_max=20000)
        a10[name] = {
            "p_hat": ph,
            "required_n_for_0.8_power": rn,
            "note": ("p_hat at or below 0.95; not powered against the "
                     "null at any n" if rn is None else "Monte-Carlo, "
                     "3000 trials/step, exact critical value"),
        }
    result["A10_required_n_monte_carlo"] = a10

    # ---- A5: within-corpus permutation + Stouffer/Fisher ----------------
    a5 = {"available": True, "per_corpus": {}}
    pvals, weights = [], []
    missing = []
    for name, (path, key) in A5_SOURCES.items():
        recs = load_per_receipt(path, key)
        if recs is None:
            missing.append(name)
            continue
        recs = matched_softmax_accept(recs)
        # Deterministic per-corpus seed (stable paper numbers).
        seed = 20260517 + sum(ord(ch) for ch in name)
        obs_prec, m, p = permutation_decorrelation_p(
            recs, random.Random(seed), n_perm=20000)
        nc = CORPORA[name]["n_corpus"]
        a5["per_corpus"][name] = {
            "source": path,
            "n_receipts": len(recs),
            "sigma_only_set_size": m,
            "sigma_only_precision": obs_prec,
            "perm_one_sided_p": p,
            "stouffer_weight_sqrt_n": math.sqrt(nc),
        }
        if p is not None:
            pvals.append(p)
            weights.append(math.sqrt(nc))
    if missing:
        a5["missing_corpora"] = missing
    if len(pvals) >= 2:
        sp, sz = stouffer(pvals, weights)
        fp, fstat = fisher(pvals)
        a5["combined"] = {
            "stouffer_one_sided_p": sp,
            "stouffer_z": sz,
            "stouffer_weights": "sqrt(n_corpus)",
            "fisher_one_sided_p": fp,
            "fisher_stat": fstat,
            "k_corpora": len(pvals),
        }
    else:
        a5["available"] = False
        a5["note"] = ("A5: per-receipt vectors unavailable in run "
                      "artifacts; not computed")
    result["A5_permutation_decorrelation"] = a5

    # ---- verdict (no spin) ----------------------------------------------
    pass_str = (", ".join(individually_pass)
                if individually_pass else "NONE")
    under_str = (", ".join(underpowered)
                 if underpowered else "none")
    verdict = (
        "Per-corpus one-sided exact-binomial TOST vs 0.95 (H0: p<=0.95, "
        f"alpha=0.05): corpora that INDIVIDUALLY clear 0.95 = [{pass_str}]; "
        f"corpora that DO NOT individually pass (consistent with >0.95 but "
        f"underpowered at their sample size) = [{under_str}]. "
        f"Receipt-weighted pool ({K}/{N}, p_hat={K/N:.4f}) exact-binomial "
        f"p={pooled_p:.4g}, pooled "
        f"{'PASSES' if pooled_p < ALPHA else 'DOES NOT PASS'} 0.95 at "
        f"alpha=0.05. SROIE (15/15) and CORD (54/55) are small samples: "
        "their failure to individually clear 0.95 is a power limitation, "
        "not evidence against the method -- stated plainly, not softened."
    )
    result["verdict"] = verdict

    OUT_JSON.write_text(json.dumps(result, indent=2))

    # ---- LaTeX macros ----------------------------------------------------
    def f4(x):
        return "n/a" if x is None else f"{x:.4f}"

    lines = [
        "% Auto-generated by scripts/smoke/U5_percorpus_rigor.py",
        "% Option 1 per-corpus rigor (pure stdlib). Leakage-free CORD.",
        f"\\renewcommand{{\\rgCordCPlo}}{{{f4(a2['CORD']['clopper_pearson_lo'])}}}",
        f"\\renewcommand{{\\rgCordJeff}}{{{f4(a2['CORD']['jeffreys_lo'])}}}",
        f"\\renewcommand{{\\rgCordWil}}{{{f4(a2['CORD']['wilson_lo'])}}}",
        f"\\renewcommand{{\\rgSroieCPlo}}{{{f4(a2['SROIE']['clopper_pearson_lo'])}}}",
        f"\\renewcommand{{\\rgSroieJeff}}{{{f4(a2['SROIE']['jeffreys_lo'])}}}",
        f"\\renewcommand{{\\rgSroieWil}}{{{f4(a2['SROIE']['wilson_lo'])}}}",
        f"\\renewcommand{{\\rgWrCPlo}}{{{f4(a2['WildReceipt']['clopper_pearson_lo'])}}}",
        f"\\renewcommand{{\\rgWrJeff}}{{{f4(a2['WildReceipt']['jeffreys_lo'])}}}",
        f"\\renewcommand{{\\rgWrWil}}{{{f4(a2['WildReceipt']['wilson_lo'])}}}",
        f"\\renewcommand{{\\rgPoolPhat}}{{{f4(receipt_weighted['p_hat'])}}}",
        f"\\renewcommand{{\\rgPoolWil}}{{{f4(receipt_weighted['wilson_lo'])}}}",
        f"\\renewcommand{{\\rgPoolCPlo}}{{{f4(receipt_weighted['clopper_pearson_lo'])}}}",
        f"\\renewcommand{{\\rgEqualMean}}{{{f4(equal_corpus['mean_p_hat'])}}}",
        f"\\renewcommand{{\\rgLocoMinWil}}{{"
        f"{f4(min(v['wilson_lo'] for v in loco.values()))}}}",
        f"\\renewcommand{{\\rgTostCordP}}{{{a7['CORD']['exact_binom_p']:.4g}}}",
        f"\\renewcommand{{\\rgTostSroieP}}{{{a7['SROIE']['exact_binom_p']:.4g}}}",
        f"\\renewcommand{{\\rgTostWrP}}{{{a7['WildReceipt']['exact_binom_p']:.4g}}}",
        f"\\renewcommand{{\\rgTostPoolP}}{{{a7['POOLED']['exact_binom_p']:.4g}}}",
        f"\\renewcommand{{\\rgPassList}}{{{pass_str}}}",
        f"\\renewcommand{{\\rgUnderList}}{{{under_str}}}",
        f"\\renewcommand{{\\rgReqnCord}}{{"
        f"{a10['CORD']['required_n_for_0.8_power']}}}",
        f"\\renewcommand{{\\rgReqnSroie}}{{"
        f"{a10['SROIE']['required_n_for_0.8_power']}}}",
        f"\\renewcommand{{\\rgReqnWr}}{{"
        f"{a10['WildReceipt']['required_n_for_0.8_power']}}}",
    ]
    if a5.get("combined"):
        lines += [
            f"\\renewcommand{{\\rgAFiveStouffer}}{{"
            f"{a5['combined']['stouffer_one_sided_p']:.4g}}}",
            f"\\renewcommand{{\\rgAFiveFisher}}{{"
            f"{a5['combined']['fisher_one_sided_p']:.4g}}}",
            "\\renewcommand{\\rgAFiveAvail}{yes}",
        ]
    else:
        lines += [
            "\\renewcommand{\\rgAFiveStouffer}{n/a}",
            "\\renewcommand{\\rgAFiveFisher}{n/a}",
            "\\renewcommand{\\rgAFiveAvail}{no}",
        ]
    lines.append("")
    OUT_TEX.write_text("\n".join(lines))

    print(json.dumps({
        "A7": a7,
        "A10": a10,
        "A5_combined": a5.get("combined"),
        "A5_available": a5["available"],
        "verdict": verdict,
    }, indent=2))


if __name__ == "__main__":
    main()
