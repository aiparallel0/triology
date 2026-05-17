"""paper_table: consolidate all locked Paper 1 numbers into a single LaTeX-ready table.

v3: figures are now fully data-driven from PAPER_TABLE.json (no hardcoded
constants). Each T1_headline row carries explicit sigma_acc, sigma_corr,
softmax_acc, softmax_corr fields so figures can render without knowing
corpus-specific magic numbers. T6_pareto_front merges MF2's WildReceipt
Pareto when present.
"""
import json
from pathlib import Path

RUNS = Path("runs")
OUT_JSON = RUNS / "PAPER_TABLE.json"


def load(name):
    p = RUNS / name
    if not p.exists(): return None
    try: return json.loads(p.read_text())
    except Exception: return None


def wilson_ci(k, n, z=1.96):
    if n == 0: return None
    p = k / n
    z2 = z * z
    center = (p + z2 / (2 * n)) / (1 + z2 / n)
    inner = p * (1 - p) / n + z2 / (4 * n * n)
    margin = (z / (1 + z2 / n)) * (inner ** 0.5)
    return [max(0.0, center - margin), min(1.0, center + margin)]


def build_T1_headline():
    """Per-corpus headline. v3: exposes explicit sigma_acc/softmax_acc/intersect_n
    so figures don't need hardcoded SIGMA_N dicts."""
    m  = (load("M_baseline_softmax.json")  or {}).get("summary", {})
    mb = (load("MB_cord_baseline.json")    or {}).get("summary", {})
    mf = (load("MF_wildreceipt_baseline.json") or {}).get("summary", {})
    mf2 = load("MF2_wildreceipt_softmax.json")
    t  = load("T_significance.json") or {}
    t_per = t.get("per_corpus", {})

    rows = []

    # CORD and SROIE: from M and MB baselines
    for name, src, t_src in [
        ("SROIE", m,  t_per.get("SROIE", {})),
        ("CORD",  mb, t_per.get("CORD", {})),
    ]:
        ortho = src.get("orthogonality", {})
        sigma_info = src.get("sigma", {})
        smax_info = src.get("softmax_matched_coverage", {})
        sigma_acc_raw = ortho.get("|sigma|")
        smax_acc_raw  = ortho.get("|softmax|")
        intersect_n = ortho.get("|intersect|")
        n_total = src.get("n")
        # n_correct backfills: sigma_corr = sigma_precision * sigma_acc
        sigma_acc = sigma_acc_raw if sigma_acc_raw is not None else (
            int(round((sigma_info.get("coverage", 0) or 0) * (n_total or 0)))
        )
        smax_acc = smax_acc_raw if smax_acc_raw is not None else sigma_acc
        sigma_corr = int(round((sigma_info.get("precision", 0) or 0) * sigma_acc))
        smax_corr  = int(round((smax_info.get("precision", 0) or 0) * smax_acc))
        intersect_corr = int(round(
            (ortho.get("intersect_precision", 0) or 0) * (intersect_n or 0)
        ))
        sigma_only_n = sigma_acc - (intersect_n or 0)
        sigma_only_corr = int(round(
            (ortho.get("sigma_only_precision", 0) or 0) * sigma_only_n
        ))
        smax_only_n = smax_acc - (intersect_n or 0)
        smax_only_corr = int(round(
            (ortho.get("softmax_only_precision", 0) or 0) * smax_only_n
        ))
        rows.append({
            "corpus": name,
            "backbone": "Donut",
            "n": n_total,
            "sigma_acc":  sigma_acc,
            "sigma_corr": sigma_corr,
            "sigma_coverage":  sigma_info.get("coverage"),
            "sigma_precision": sigma_info.get("precision"),
            "sigma_precision_ci": t_src.get("sigma", {}).get("wilson_95_ci") if t_src else None,
            "softmax_acc":  smax_acc,
            "softmax_corr": smax_corr,
            "softmax_coverage":  smax_info.get("coverage"),
            "softmax_precision": smax_info.get("precision"),
            "softmax_precision_ci": t_src.get("softmax_matched", {}).get("wilson_95_ci") if t_src else None,
            "intersect_n":         intersect_n,
            "intersect_corr":      intersect_corr,
            "intersect_precision": ortho.get("intersect_precision"),
            "intersect_precision_ci": t_src.get("intersect", {}).get("wilson_95_ci") if t_src else None,
            "sigma_only_n":         sigma_only_n,
            "sigma_only_corr":      sigma_only_corr,
            "sigma_only_precision": ortho.get("sigma_only_precision"),
            "sigma_only_precision_ci": t_src.get("sigma_only", {}).get("wilson_95_ci") if t_src else None,
            "softmax_only_n":         smax_only_n,
            "softmax_only_corr":      smax_only_corr,
            "softmax_only_precision": ortho.get("softmax_only_precision"),
            "mcnemar_p": t_src.get("mcnemar_paired_test", {}).get("p_value") if t_src else None,
        })

    # WildReceipt: from MF2 when present, else MF (sigma-only)
    sigma = mf.get("sigma_from_F", {})
    wr_row = {
        "corpus": "WildReceipt",
        "backbone": "LayoutLMv3",
        "n": sigma.get("n"),
        "sigma_acc": None, "sigma_corr": None,
        "sigma_coverage": sigma.get("coverage"),
        "sigma_precision": sigma.get("precision"),
        "sigma_precision_ci": None,
        "softmax_acc": None, "softmax_corr": None,
        "softmax_coverage": None, "softmax_precision": None,
        "softmax_precision_ci": None,
        "intersect_n": None, "intersect_corr": None,
        "intersect_precision": None, "intersect_precision_ci": None,
        "sigma_only_n": None, "sigma_only_corr": None,
        "sigma_only_precision": None, "sigma_only_precision_ci": None,
        "softmax_only_n": None, "softmax_only_corr": None,
        "softmax_only_precision": None,
        "mcnemar_p": None,
        "note": "softmax baseline pending",
    }
    if mf2:
        wr = mf2.get("WildReceipt", {})
        bp, cp = wr.get("b_mcnemar"), wr.get("c_mcnemar")
        mc_p = None
        if bp is not None and cp is not None:
            chi2 = ((abs(bp - cp) - 1) ** 2) / max(1, bp + cp)
            try:
                from scipy.stats import chi2 as chi2_dist
                mc_p = float(chi2_dist.sf(chi2, 1))
            except Exception:
                import math
                mc_p = math.erfc((chi2 / 2) ** 0.5)
        wr_row.update({
            "n": wr.get("n"),
            "sigma_acc":  wr["sigma_acc"], "sigma_corr": wr["sigma_corr"],
            "sigma_coverage": wr["sigma_acc"] / max(1, wr["n"]),
            "sigma_precision": wr["sigma_corr"] / max(1, wr["sigma_acc"]),
            "sigma_precision_ci": wilson_ci(wr["sigma_corr"], wr["sigma_acc"]),
            "softmax_acc":  wr["smax_acc"], "softmax_corr": wr["smax_corr"],
            "softmax_coverage": wr["smax_acc"] / max(1, wr["n"]),
            "softmax_precision": wr["smax_corr"] / max(1, wr["smax_acc"]),
            "softmax_precision_ci": wilson_ci(wr["smax_corr"], wr["smax_acc"]),
            "intersect_n": wr["int_acc"], "intersect_corr": wr["int_corr"],
            "intersect_precision": wr["int_corr"] / max(1, wr["int_acc"]),
            "intersect_precision_ci": wilson_ci(wr["int_corr"], wr["int_acc"]),
            "sigma_only_n": wr["sigonly_acc"], "sigma_only_corr": wr["sigonly_corr"],
            "sigma_only_precision": wr["sigonly_corr"] / max(1, wr["sigonly_acc"]),
            "sigma_only_precision_ci": wilson_ci(wr["sigonly_corr"], wr["sigonly_acc"]),
            "softmax_only_n": wr["smonly_acc"], "softmax_only_corr": wr["smonly_corr"],
            "softmax_only_precision": wr["smonly_corr"] / max(1, wr["smonly_acc"]),
            "mcnemar_p": mc_p,
            "note": "softmax via MF2_wildreceipt_softmax.py (LayoutLMv3)",
        })
    rows.append(wr_row)
    return rows


def build_T2_latency():
    g = (load("G_robustness.json") or {}).get("dp_latency_ms", {})
    return {k: g.get(k) for k in ("n_receipts","p50_ms","p95_ms","p99_ms","max_ms","mean_ms")}


def build_T3_guard_ablation():
    return (load("G_robustness.json") or {}).get("cardinality_guard_ablation", {})


def build_T4_failure_modes():
    l_sroie = (load("L_sroie_failure_modes.json") or {}).get("summary", {})
    l_cord  = (load("L_cord_failure_modes.json") or {}).get("summary", {})
    return {
        "SROIE": l_sroie.get("counts_by_category"),
        "CORD":  l_cord.get("counts_by_category") if isinstance(l_cord, dict) else None,
    }


def build_T5_noise():
    return (load("Q_money_noise_cord.json") or {}).get("per_rate")


def build_T6_pareto():
    """v3: merges MF2's WildReceipt Pareto if present."""
    s = (load("S_pareto.json") or {}).get("per_corpus", {})
    mf2 = load("MF2_wildreceipt_softmax.json") or {}
    out = {
        "CORD":  (s.get("CORD") or {}).get("pareto_front"),
        "SROIE": (s.get("SROIE") or {}).get("pareto_front"),
        "WildReceipt": mf2.get("WildReceipt_pareto_front"),
    }
    return out


def build_T7_tolerance():
    return (load("V_tolerance_sweep_cord.json") or {}).get("per_eps")


def build_T8_pooled(rows=None):
    """Recompute pooled cells from the (leakage-free) per-corpus headline
    rows so the pooled row stays consistent with the canonical CORD
    test+validation evaluation. Falls back to the stale MF2 cache only if
    rows are unavailable."""
    if rows is None:
        rows = build_T1_headline()
    if not rows:
        mf2 = load("MF2_wildreceipt_softmax.json")
        if not mf2:
            return None
        return {
            "Pooled": mf2.get("Pooled"),
            "Pooled_CIs": mf2.get("Pooled_CIs"),
            "Pooled_McNemar": mf2.get("Pooled_McNemar"),
        }

    def s(key):
        return sum(int(r.get(key) or 0) for r in rows)

    n_total = s("n")
    sigma_acc = s("sigma_acc")
    sigma_corr = s("sigma_corr")
    smax_acc = s("softmax_acc")
    smax_corr = s("softmax_corr")
    int_acc = s("intersect_n")
    int_corr = s("intersect_corr")
    sigonly_acc = s("sigma_only_n")
    sigonly_corr = s("sigma_only_corr")
    smonly_acc = s("softmax_only_n")
    smonly_corr = s("softmax_only_corr")

    pooled = {
        "n": n_total,
        "sigma_acc": sigma_acc,
        "sigma_corr": sigma_corr,
        "smax_acc": smax_acc,
        "smax_corr": smax_corr,
        "int_acc": int_acc,
        "int_corr": int_corr,
        "sigonly_acc": sigonly_acc,
        "sigonly_corr": sigonly_corr,
        "smonly_acc": smonly_acc,
        "smonly_corr": smonly_corr,
        # discordant proxy (sigma-only vs softmax-only correct counts),
        # same convention as the prior MF2 pooled cache.
        "b_mcnemar": sigonly_corr,
        "c_mcnemar": smonly_corr,
    }

    def rnd(ci):
        return None if ci is None else [round(ci[0], 3), round(ci[1], 3)]

    pooled_cis = {
        "sigma": rnd(wilson_ci(sigma_corr, sigma_acc)),
        "smax": rnd(wilson_ci(smax_corr, smax_acc)),
        "int": rnd(wilson_ci(int_corr, int_acc)),
        "sigonly": rnd(wilson_ci(sigonly_corr, sigonly_acc)),
        "smonly": rnd(wilson_ci(smonly_corr, smonly_acc)),
    }

    b, c = sigonly_corr, smonly_corr
    if (b + c) > 0:
        chi2 = (abs(b - c) - 1) ** 2 / (b + c) if (b + c) > 0 else 0.0
        try:
            from scipy.stats import chi2 as _chi2
            p_value = float(1 - _chi2.cdf(chi2, 1))
        except Exception:
            import math
            p_value = math.erfc((chi2 ** 0.5) / (2 ** 0.5))
    else:
        chi2, p_value = 0.0, 1.0
    pooled_mcnemar = {
        "b": b, "c": c,
        "chi2": round(chi2, 4),
        "p_value": round(p_value, 4),
    }

    return {
        "Pooled": pooled,
        "Pooled_CIs": pooled_cis,
        "Pooled_McNemar": pooled_mcnemar,
    }


def main():
    t1 = build_T1_headline()
    data = {
        "T1_headline":          t1,
        "T2_latency":           build_T2_latency(),
        "T3_guard_ablation":    build_T3_guard_ablation(),
        "T4_failure_modes":     build_T4_failure_modes(),
        "T5_noise_sensitivity": build_T5_noise(),
        "T6_pareto_front":      build_T6_pareto(),
        "T7_tolerance_sweep":   build_T7_tolerance(),
        "T8_pooled":            build_T8_pooled(t1),
    }
    OUT_JSON.write_text(json.dumps(data, indent=2))
    summary = {
        "T1_rows": len(data["T1_headline"]),
        "T6_corpora_with_pareto": [c for c, v in data["T6_pareto_front"].items() if v],
        "T8_pooled_n": data["T8_pooled"]["Pooled"]["n"] if data["T8_pooled"] else None,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
