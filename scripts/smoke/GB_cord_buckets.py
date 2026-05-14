"""GB: sigma money-count bucket analysis on CORD-v2.

Mirror of G's SROIE bucket table. For each CORD receipt, count labeled
gt_parse.menu[*].price values and bucket by money_count. Report sigma
precision/coverage per bucket. Confirms bucket-conditional behavior is
consistent across labeled-amounts (CORD) and OCR-derived (SROIE) corpora.

Reads B's per-receipt sigma results. CPU only. ~5 sec.
"""
import json
from collections import defaultdict
from pathlib import Path

from datasets import load_dataset

B_OUT = Path("runs/B_donut_cord_on_cord.json")
OUT = Path("runs/GB_cord_buckets.json")
OUT.parent.mkdir(parents=True, exist_ok=True)


def parse_money(s):
    try:
        return float(str(s).replace(",", ""))
    except (TypeError, ValueError):
        return None


def money_count_from_gt(ex):
    gt = ex.get("ground_truth")
    if isinstance(gt, str):
        try: gt = json.loads(gt)
        except Exception: return None
    if not isinstance(gt, dict): return None
    gt = gt.get("gt_parse", gt) if "gt_parse" in gt else gt
    menu = gt.get("menu") or []
    if isinstance(menu, dict): menu = [menu]
    n = 0
    for m in menu:
        if isinstance(m, dict) and parse_money(m.get("price")) is not None:
            n += 1
    return n


def main():
    if not B_OUT.exists():
        OUT.write_text(json.dumps({"available": False, "reason": "B output missing"}, indent=2))
        print("B's runs/B_donut_cord_on_cord.json not found"); return
    b = json.loads(B_OUT.read_text())
    b_results = {r["id"]: r for r in b.get("results", [])}

    ds = load_dataset("naver-clova-ix/cord-v2", split="test", trust_remote_code=True)
    print(f"CORD test n={len(ds)}")

    rows = []
    for ex_idx in range(len(ds)):
        ex = ds[ex_idx]
        mc = money_count_from_gt(ex)
        if mc is None: continue
        r = b_results.get(ex_idx, {})
        rows.append({
            "id": ex_idx, "money_count": mc,
            "in_T": r.get("in_T", False),
            "correct": r.get("correct", False),
            "pred": r.get("pred"),
            "gold": r.get("gold"),
            "T_size": r.get("T_size", 0),
        })

    buckets = defaultdict(list)
    for r in rows:
        mc = r["money_count"]
        key = ("0" if mc == 0 else
               "1" if mc == 1 else
               "2-4" if mc <= 4 else
               "5-9" if mc <= 9 else ">=10")
        buckets[key].append(r)

    def summarize(rs):
        n = max(1, len(rs))
        accepted = [r for r in rs if r["in_T"]]
        correct_acc = sum(r["correct"] for r in accepted)
        T_sizes = [r["T_size"] for r in rs]
        return {
            "n": len(rs),
            "coverage_sigma": len(accepted) / n,
            "sigma_precision": correct_acc / max(1, len(accepted)) if accepted else 0.0,
            "n_accepted": len(accepted),
            "n_correct_accepted": correct_acc,
            "T_size_mean": sum(T_sizes) / n if T_sizes else 0,
            "T_size_p95": sorted(T_sizes)[int(0.95 * n)] if T_sizes and n > 1 else 0,
        }

    by_bucket = {k: summarize(v) for k, v in buckets.items()}

    summary = {
        "corpus": "CORD-v2 test",
        "source": "B's per-receipt sigma results + CORD gt_parse.menu money_count",
        "n_total": len(rows),
        "sigma_by_money_count_bucket": by_bucket,
        "interpretation": (
            "Mirror of G's SROIE bucket analysis on CORD. Compare sigma_precision per bucket "
            "across corpora: if both show precision ~1.0 on 2-9 bucket, sigma's bucket-conditional "
            "behavior is consistent across labeled and OCR regimes — strong cross-corpus claim."
        ),
    }
    OUT.write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
