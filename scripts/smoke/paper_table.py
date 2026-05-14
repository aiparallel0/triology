"""paper_table: consolidate all locked Paper 1 numbers into a single LaTeX-ready table.

v2: detects runs/MF2_wildreceipt_softmax.json and fills WildReceipt's
softmax/intersect/sigma-only cells when present (was None when softmax
was deferred). All figures now render three-corpus panels.
"""
import json
from pathlib import Path

RUNS = Path("runs")
OUT_JSON = RUNS / "PAPER_TABLE.json"
OUT_MD = RUNS / "PAPER_TABLE.md"
OUT_TEX = RUNS / "PAPER_TABLE.tex"


def load(name):
    p = RUNS / name
    if not p.exists(): return None
    try: return json.loads(p.read_text())
    except Exception: return None


def fmt_ci(ci, decimals=3):
    if ci is None: return "-"
    if not isinstance(ci, (list, tuple)) or len(ci) != 2: return "-"
    lo, hi = ci
    if lo is None or hi is None: return "-"
    return f"[{lo:.{decimals}f}, {hi:.{decimals}f}]"


def fmt_pct(x, decimals=1):
    if x is None: return "-"
    return f"{100*x:.{decimals}f}%"


def fmt_pct_tex(x, decimals=1):
    if x is None: return "-"
    return f"{100*x:.{decimals}f}\\%"


def wilson_ci(k, n, z=1.96):
    if n == 0: return None
    p = k / n
    z2 = z * z
    center = (p + z2 / (2 * n)) / (1 + z2 / n)
    inner = p * (1 - p) / n + z2 / (4 * n * n)
    margin = (z / (1 + z2 / n)) * (inner ** 0.5)
    return [max(0.0, center - margin), min(1.0, center + margin)]


def build_T1_headline():
    m  = (load("M_baseline_softmax.json")  or {}).get("summary", {})
    mb = (load("MB_cord_baseline.json")    or {}).get("summary", {})
    mf = (load("MF_wildreceipt_baseline.json") or {}).get("summary", {})
    mf2 = load("MF2_wildreceipt_softmax.json")
    t  = load("T_significance.json") or {}
    t_per = t.get("per_corpus", {})

    rows = []
    for name, src, t_src in [
        ("SROIE",      m,  t_per.get("SROIE", {})),
        ("CORD",       mb, t_per.get("CORD", {})),
        ("WildReceipt", mf, None),
    ]:
        if name == "WildReceipt":
            sigma = mf.get("sigma_from_F", {})
            row = {
                "corpus": name, "n": sigma.get("n"),
                "sigma_coverage": sigma.get("coverage"),
                "sigma_precision": sigma.get("precision"),
                "sigma_precision_ci": None,
                "softmax_coverage": None,
                "softmax_precision": None,
                "softmax_precision_ci": None,
                "intersect_n": None,
                "intersect_precision": None,
                "intersect_precision_ci": None,
                "sigma_only_n": None,
                "sigma_only_precision": None,
                "sigma_only_precision_ci": None,
                "softmax_only_precision": None,
                "mcnemar_p": None,
                "note": "softmax baseline pending",
            }
            if mf2:
                wr = mf2.get("WildReceipt", {})
                row.update({
                    "sigma_coverage": wr["sigma_acc"] / max(1, wr["n"]),
                    "sigma_precision": wr["sigma_corr"] / max(1, wr["sigma_acc"]),
                    "sigma_precision_ci": wilson_ci(wr["sigma_corr"], wr["sigma_acc"]),
                    "softmax_coverage": wr["smax_acc"] / max(1, wr["n"]),
                    "softmax_precision": wr["smax_corr"] / max(1, wr["smax_acc"]),
                    "softmax_precision_ci": wilson_ci(wr["smax_corr"], wr["smax_acc"]),
                    "intersect_n": wr["int_acc"],
                    "intersect_precision": wr["int_corr"] / max(1, wr["int_acc"]),
                    "intersect_precision_ci": wilson_ci(wr["int_corr"], wr["int_acc"]),
                    "sigma_only_n": wr["sigonly_acc"],
                    "sigma_only_precision": wr["sigonly_corr"] / max(1, wr["sigonly_acc"]),
                    "sigma_only_precision_ci": wilson_ci(wr["sigonly_corr"], wr["sigonly_acc"]),
                    "softmax_only_precision": wr["smonly_corr"] / max(1, wr["smonly_acc"]),
                    "mcnemar_p": None,
                    "note": "softmax via MF2_wildreceipt_softmax.py (LayoutLMv3)",
                })
            rows.append(row)
            continue

        ortho = src.get("orthogonality", {})
        rows.append({
            "corpus": name,
            "n": src.get("n"),
            "sigma_coverage":  src.get("sigma", {}).get("coverage"),
            "sigma_precision": src.get("sigma", {}).get("precision"),
            "sigma_precision_ci": t_src.get("sigma", {}).get("wilson_95_ci") if t_src else None,
            "softmax_coverage":  src.get("softmax_matched_coverage", {}).get("coverage"),
            "softmax_precision": src.get("softmax_matched_coverage", {}).get("precision"),
            "softmax_precision_ci": t_src.get("softmax_matched", {}).get("wilson_95_ci") if t_src else None,
            "intersect_n":         ortho.get("|intersect|"),
            "intersect_precision": ortho.get("intersect_precision"),
            "intersect_precision_ci": t_src.get("intersect", {}).get("wilson_95_ci") if t_src else None,
            "sigma_only_n":         ortho.get("|sigma_only|") if name == "SROIE" else None,
            "sigma_only_precision": ortho.get("sigma_only_precision"),
            "sigma_only_precision_ci": t_src.get("sigma_only", {}).get("wilson_95_ci") if t_src else None,
            "softmax_only_precision": ortho.get("softmax_only_precision"),
            "mcnemar_p": t_src.get("mcnemar_paired_test", {}).get("p_value") if t_src else None,
        })
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
    s = (load("S_pareto.json") or {}).get("per_corpus", {})
    return {
        "CORD": s.get("CORD", {}).get("pareto_front"),
        "SROIE": s.get("SROIE", {}).get("pareto_front"),
    }


def build_T7_tolerance():
    return (load("V_tolerance_sweep_cord.json") or {}).get("per_eps")


def build_T8_pooled():
    """v2: three-corpus pooled headline from MF2 output."""
    mf2 = load("MF2_wildreceipt_softmax.json")
    if not mf2: return None
    return {
        "Pooled": mf2.get("Pooled"),
        "Pooled_CIs": mf2.get("Pooled_CIs"),
        "Pooled_McNemar": mf2.get("Pooled_McNemar"),
    }


def main():
    t1 = build_T1_headline()
    t2 = build_T2_latency()
    t3 = build_T3_guard_ablation()
    t4 = build_T4_failure_modes()
    t5 = build_T5_noise()
    t6 = build_T6_pareto()
    t7 = build_T7_tolerance()
    t8 = build_T8_pooled()
    data = {"T1_headline": t1, "T2_latency": t2, "T3_guard_ablation": t3,
            "T4_failure_modes": t4, "T5_noise_sensitivity": t5,
            "T6_pareto_front": t6, "T7_tolerance_sweep": t7, "T8_pooled": t8}
    OUT_JSON.write_text(json.dumps(data, indent=2))
    print(f"Wrote {OUT_JSON.name}")
    print(json.dumps({"T1_rows": len(t1), "T8_pooled_n": t8["Pooled"]["n"] if t8 else None}, indent=2))


if __name__ == "__main__":
    main()
