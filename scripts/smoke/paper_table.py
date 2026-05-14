"""paper_table: consolidate all locked Paper 1 numbers into a single LaTeX-ready table.

Reads every JSON output from runs/ and produces:
  - runs/PAPER_TABLE.json   structured aggregation
  - runs/PAPER_TABLE.md     markdown for review/PR copy-paste
  - runs/PAPER_TABLE.tex    LaTeX-ready table fragments

Tables generated:
  T1  Headline: per-corpus sigma vs softmax-matched vs intersect, with Wilson CIs
  T2  Latency: DP p50/p95/p99 from G
  T3  Cardinality guard ablation (G's kmin=1 vs kmin=2)
  T4  Failure-mode summary across SROIE (L) and CORD (L_cord)
  T5  Noise sensitivity (Q v2)
  T6  Pareto front excerpts (S)
  T7  Tolerance sweep (V)

Pure CPU consolidation. ~1 sec.
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


def build_T1_headline():
    """Per-corpus sigma vs softmax_matched vs intersect, with Wilson CIs."""
    m  = (load("M_baseline_softmax.json")  or {}).get("summary", {})
    mb = (load("MB_cord_baseline.json")    or {}).get("summary", {})
    mf = (load("MF_wildreceipt_baseline.json") or {}).get("summary", {})
    t  = load("T_significance.json") or {}
    t_per = t.get("per_corpus", {})

    rows = []
    for name, src, t_src in [
        ("SROIE",      m,  t_per.get("SROIE", {})),
        ("CORD",       mb, t_per.get("CORD", {})),
        ("WildReceipt", mf, None),  # softmax baseline deferred
    ]:
        if name == "WildReceipt":
            sigma = mf.get("sigma_from_F", {})
            rows.append({
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
                "mcnemar_p": None,
                "note": "softmax deferred; image archive unavailable",
            })
            continue

        rows.append({
            "corpus": name,
            "n": src.get("n"),
            "sigma_coverage":  src.get("sigma", {}).get("coverage"),
            "sigma_precision": src.get("sigma", {}).get("precision"),
            "sigma_precision_ci": t_src.get("sigma", {}).get("wilson_95_ci") if t_src else None,
            "softmax_coverage":  src.get("softmax_matched_coverage", {}).get("coverage"),
            "softmax_precision": src.get("softmax_matched_coverage", {}).get("precision"),
            "softmax_precision_ci": t_src.get("softmax_matched", {}).get("wilson_95_ci") if t_src else None,
            "intersect_n":         src.get("orthogonality", {}).get("|intersect|"),
            "intersect_precision": src.get("orthogonality", {}).get("intersect_precision"),
            "intersect_precision_ci": t_src.get("intersect", {}).get("wilson_95_ci") if t_src else None,
            "sigma_only_n":         src.get("orthogonality", {}).get("|sigma_only|") if name == "SROIE" else None,
            "sigma_only_precision": src.get("orthogonality", {}).get("sigma_only_precision"),
            "sigma_only_precision_ci": t_src.get("sigma_only", {}).get("wilson_95_ci") if t_src else None,
            "mcnemar_p": t_src.get("mcnemar_paired_test", {}).get("p_value") if t_src else None,
        })
    return rows


def build_T2_latency():
    g = (load("G_robustness.json") or {}).get("dp_latency_ms", {})
    return {
        "n_receipts": g.get("n_receipts"),
        "p50_ms":     g.get("p50_ms"),
        "p95_ms":     g.get("p95_ms"),
        "p99_ms":     g.get("p99_ms"),
        "max_ms":     g.get("max_ms"),
        "mean_ms":    g.get("mean_ms"),
    }


def build_T3_guard_ablation():
    g = (load("G_robustness.json") or {}).get("cardinality_guard_ablation", {})
    return g


def build_T4_failure_modes():
    l_sroie = (load("L_sroie_failure_modes.json") or {}).get("summary", {})
    l_cord  = (load("L_cord_failure_modes.json") or {}).get("summary", {})
    return {
        "SROIE": l_sroie.get("counts_by_category"),
        "CORD":  l_cord.get("counts_by_category") if isinstance(l_cord, dict) else None,
    }


def build_T5_noise():
    q = load("Q_money_noise_cord.json") or {}
    return q.get("per_rate")


def build_T6_pareto():
    s = (load("S_pareto.json") or {}).get("per_corpus", {})
    return {
        "CORD": s.get("CORD", {}).get("pareto_front"),
        "SROIE": s.get("SROIE", {}).get("pareto_front"),
    }


def build_T7_tolerance():
    v = load("V_tolerance_sweep_cord.json") or {}
    return v.get("per_eps")


def gen_md(t1, t2, t3, t4, t5, t6, t7):
    L = []
    L.append("# Paper 1 Headline Tables (auto-generated)\n")

    L.append("## T1 — Headline: sigma vs softmax-matched vs intersect\n")
    L.append("| corpus | n | sigma cov | sigma prec [95% CI] | softmax prec [95% CI] | intersect n / prec [95% CI] | sigma_only prec [95% CI] | McNemar p |")
    L.append("|---|---:|---:|---|---|---|---|---:|")
    for r in t1:
        L.append("| {corpus} | {n} | {scov} | {sprec} {sci} | {mprec} {mci} | {int_n} / {iprec} {ici} | {soprec} {soci} | {p} |".format(
            corpus=r["corpus"], n=r["n"] or "-",
            scov=fmt_pct(r["sigma_coverage"]),
            sprec=fmt_pct(r["sigma_precision"]) if r["sigma_precision"] is not None else "-",
            sci=fmt_ci(r["sigma_precision_ci"]),
            mprec=fmt_pct(r["softmax_precision"]) if r["softmax_precision"] is not None else "-",
            mci=fmt_ci(r["softmax_precision_ci"]),
            int_n=r["intersect_n"] if r["intersect_n"] is not None else "-",
            iprec=fmt_pct(r["intersect_precision"]) if r["intersect_precision"] is not None else "-",
            ici=fmt_ci(r["intersect_precision_ci"]),
            soprec=fmt_pct(r["sigma_only_precision"]) if r["sigma_only_precision"] is not None else "-",
            soci=fmt_ci(r["sigma_only_precision_ci"]),
            p=("{:.3f}".format(r["mcnemar_p"]) if r["mcnemar_p"] is not None else "-"),
        ))

    L.append("\n## T2 — DP latency (n={})".format(t2.get("n_receipts")))
    if t2.get("p50_ms") is not None:
        L.append("| p50 | p95 | p99 | max | mean |")
        L.append("|---:|---:|---:|---:|---:|")
        L.append("| {p50:.4f} ms | {p95:.4f} ms | {p99:.4f} ms | {mx:.4f} ms | {mn:.4f} ms |".format(
            p50=t2["p50_ms"], p95=t2["p95_ms"], p99=t2["p99_ms"], mx=t2["max_ms"], mn=t2["mean_ms"]))

    L.append("\n## T3 — Cardinality guard ablation (SROIE)")
    if t3:
        L.append("| kmin | n | coverage | precision | T_size mean | T_size p95 |")
        L.append("|---|---:|---:|---:|---:|---:|")
        for k, v in t3.items():
            L.append("| {k} | {n} | {c} | {p} | {tm:.2f} | {tp} |".format(
                k=k, n=v.get("n"), c=fmt_pct(v.get("coverage_sigma")),
                p=fmt_pct(v.get("sigma_precision")),
                tm=v.get("T_size_mean", 0), tp=v.get("T_size_p95", 0)))

    L.append("\n## T4 — Failure-mode taxonomy counts")
    for corpus, counts in t4.items():
        L.append(f"\n### {corpus}")
        if counts:
            for cat, n in sorted(counts.items(), key=lambda x: -x[1]):
                L.append(f"  - {cat}: {n}")

    L.append("\n## T5 — Noise sensitivity (CORD)")
    if t5:
        L.append("| noise rate | n | coverage mean | coverage 95% CI | precision mean | precision 95% CI |")
        L.append("|---:|---:|---:|---|---:|---|")
        for rate, v in t5.items():
            L.append("| {r} | {n} | {cm} | {cci} | {pm} | {pci} |".format(
                r=rate, n=v.get("n"),
                cm=fmt_pct(v.get("coverage_mean")),
                cci=fmt_ci(v.get("coverage_bootstrap_95_ci")),
                pm=fmt_pct(v.get("precision_mean")) if v.get("precision_mean") is not None else "-",
                pci=fmt_ci(v.get("precision_bootstrap_95_ci")),
            ))

    L.append("\n## T6 — Pareto front excerpts")
    for corpus, front in t6.items():
        L.append(f"\n### {corpus}")
        if front:
            L.append("| coverage | precision | signal |")
            L.append("|---:|---:|---|")
            for pt in front:
                L.append("| {c} | {p} | {lbl} |".format(
                    c=fmt_pct(pt["coverage"]), p=fmt_pct(pt["precision"]), lbl=pt["label"]))

    L.append("\n## T7 — sigma tolerance sweep (CORD)")
    if t7:
        L.append("| epsilon | n | coverage | precision |")
        L.append("|---:|---:|---:|---:|")
        for eps_key, v in t7.items():
            L.append("| {e} | {n} | {c} | {p} |".format(
                e=v.get("eps", eps_key), n=v.get("n"),
                c=fmt_pct(v.get("coverage")),
                p=fmt_pct(v.get("precision")) if v.get("precision") is not None else "-"))

    return "\n".join(L)


def gen_tex(t1, t2):
    """LaTeX-ready table fragments (just the table contents, no preamble)."""
    L = []
    L.append("% T1: Headline per-corpus comparison")
    L.append(r"\begin{tabular}{lrrrrr}")
    L.append(r"\toprule")
    L.append(r"Corpus & $n$ & $\sigma$ cov & $\sigma$ prec & softmax prec & $\sigma$-only prec \\")
    L.append(r"\midrule")
    for r in t1:
        L.append("{corpus} & {n} & {scov} & {sprec} & {mprec} & {soprec} \\\\".format(
            corpus=r["corpus"], n=r["n"] or "-",
            scov=fmt_pct(r["sigma_coverage"]),
            sprec=fmt_pct(r["sigma_precision"]) if r["sigma_precision"] is not None else "-",
            mprec=fmt_pct(r["softmax_precision"]) if r["softmax_precision"] is not None else "-",
            soprec=fmt_pct(r["sigma_only_precision"]) if r["sigma_only_precision"] is not None else "-",
        ))
    L.append(r"\bottomrule")
    L.append(r"\end{tabular}")
    L.append("")
    L.append("% T2: DP latency (SROIE n={})".format(t2.get("n_receipts")))
    if t2.get("p50_ms") is not None:
        L.append(r"\begin{tabular}{rrrrr}")
        L.append(r"\toprule")
        L.append(r"p50 (ms) & p95 (ms) & p99 (ms) & max (ms) & mean (ms) \\")
        L.append(r"\midrule")
        L.append("{p50:.4f} & {p95:.4f} & {p99:.4f} & {mx:.4f} & {mn:.4f} \\\\".format(
            p50=t2["p50_ms"], p95=t2["p95_ms"], p99=t2["p99_ms"], mx=t2["max_ms"], mn=t2["mean_ms"]))
        L.append(r"\bottomrule")
        L.append(r"\end{tabular}")
    return "\n".join(L)


def main():
    t1 = build_T1_headline()
    t2 = build_T2_latency()
    t3 = build_T3_guard_ablation()
    t4 = build_T4_failure_modes()
    t5 = build_T5_noise()
    t6 = build_T6_pareto()
    t7 = build_T7_tolerance()

    data = {
        "T1_headline": t1,
        "T2_latency": t2,
        "T3_guard_ablation": t3,
        "T4_failure_modes": t4,
        "T5_noise_sensitivity": t5,
        "T6_pareto_front": t6,
        "T7_tolerance_sweep": t7,
    }
    OUT_JSON.write_text(json.dumps(data, indent=2))
    OUT_MD.write_text(gen_md(t1, t2, t3, t4, t5, t6, t7))
    OUT_TEX.write_text(gen_tex(t1, t2))
    print(f"Wrote {OUT_JSON.name}, {OUT_MD.name}, {OUT_TEX.name}")
    print(json.dumps({"T1_rows": len(t1), "T6_corpora": list(t6.keys())}, indent=2))


if __name__ == "__main__":
    main()
