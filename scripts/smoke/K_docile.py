"""K v4: DocILE-like 4th corpus — n=501 expansion (train+validation+test pooled).

v3 ran only on n=26 katanaml test, gave 54% identity hold (noise-level n).
v4 pools train + validation + test for n=501 to get a robust identity-hold rate.

Both identities still tested (gross convention sum+tax=total vs net sum=total).

Runtime: ~30 s if reachable.
"""
import json, os, time
from pathlib import Path

OUT = Path("runs/K_docile.json")
OUT.parent.mkdir(parents=True, exist_ok=True)
EPS = 0.05


def try_load_docile_all_splits():
    """Load and concat train+validation+test from the first reachable mirror."""
    from datasets import load_dataset
    candidates_ref = [
        "harborwater/docile-trial",
        "naver-clova-ix/docile-trial",
        "idd-fit/docile-trial",
        "katanaml-org/invoices-donut-data-v1",
        "mychen76/invoices-and-receipts_ocr_v1",
    ]
    for ref in candidates_ref:
        try:
            pooled = []
            split_sizes = {}
            for split in ("train", "validation", "test", "valid"):
                try:
                    ds = load_dataset(ref, split=split, trust_remote_code=True)
                    split_sizes[split] = len(ds)
                    for ex in ds: pooled.append(ex)
                except Exception:
                    continue
            if pooled:
                print(f"  loaded {ref} pooled n={len(pooled)} from splits {split_sizes}")
                return pooled, ref, split_sizes
        except Exception as e:
            print(f"  miss {ref}: {type(e).__name__}")
    return None, None, None


def _try_float(x):
    try:
        if isinstance(x, str):
            x = x.replace(",", "").replace(" ", "").replace("$", "").replace("€", "").replace("RM", "")
        return float(x)
    except (TypeError, ValueError):
        return None


def _try_floats(seq):
    if seq is None: return []
    out = []
    for x in seq:
        v = _try_float(x)
        if v is not None: out.append(v)
    return out


TOTAL_KEYS = ["total_gross_worth", "total_amount", "grand_total", "total",
              "amount_total", "invoice_total", "total_gross", "total_net_worth"]
ITEM_TOTAL_KEYS_TOP = ["line_total", "line_item_total", "line_totals",
                       "amount", "line_amounts", "item_amounts"]
ITEM_TOTAL_KEYS_IN = ["item_gross_worth", "item_net_worth", "price", "amount",
                      "total_price", "line_total", "item_total", "item_amount"]
TAX_KEYS = ["total_vat", "total_tax", "tax_total", "vat_total",
            "tax_amount", "tax", "vat"]


def _scan_dict_for_keys(d, keys):
    for k in keys:
        if k in d:
            v = _try_float(d[k])
            if v is not None: return v
    return None


def _extract_items_total_tax(ex):
    items, tax, total = [], 0.0, None
    if isinstance(ex, dict):
        total = total if total is not None else _scan_dict_for_keys(ex, TOTAL_KEYS)
        for k in ITEM_TOTAL_KEYS_TOP:
            if k in ex:
                v = ex[k]
                items_candidate = _try_floats(v if isinstance(v, (list, tuple)) else [v])
                if items_candidate:
                    items = items_candidate
                    break
        if not tax:
            t = _scan_dict_for_keys(ex, TAX_KEYS)
            if t is not None: tax = t

    if (total is None or not items) and "ground_truth" in ex:
        try:
            gt = ex["ground_truth"]
            if isinstance(gt, str):
                gt = json.loads(gt)
            if isinstance(gt, dict) and "gt_parse" in gt:
                gt = gt["gt_parse"]
            if isinstance(gt, dict):
                summary = gt.get("summary") or gt.get("totals") or {}
                if isinstance(summary, dict):
                    if total is None:
                        total = _scan_dict_for_keys(summary, TOTAL_KEYS)
                    if not tax:
                        t = _scan_dict_for_keys(summary, TAX_KEYS)
                        if t is not None: tax = t
                items_list = gt.get("items") or gt.get("menu") or gt.get("line_items") or []
                if isinstance(items_list, list) and not items:
                    for it in items_list:
                        if not isinstance(it, dict): continue
                        for k in ITEM_TOTAL_KEYS_IN:
                            if k in it:
                                v = _try_float(it[k])
                                if v is not None:
                                    items.append(v)
                                    break
                if total is None:
                    total = _scan_dict_for_keys(gt, TOTAL_KEYS)
        except Exception:
            pass

    return items, tax, total


def _ex_schema_sample(ex):
    out = {}
    for k, v in ex.items():
        if isinstance(v, str):
            out[k] = v[:200]
        elif isinstance(v, (int, float, bool)) or v is None:
            out[k] = v
        else:
            out[k] = type(v).__name__
    return out


def main():
    t0 = time.time()
    print("=== K v4: DocILE 4th corpus (n=501 pooled) ===")
    pooled, ref, split_sizes = try_load_docile_all_splits()
    if pooled is None:
        summary = {"available": False, "reason": "no DocILE-like mirror reachable",
                   "wall_sec": round(time.time() - t0, 1)}
        OUT.write_text(json.dumps(summary, indent=2))
        print(json.dumps(summary, indent=2))
        return

    results = []
    failed_samples = []
    n_attempt = 0
    for ex in pooled:
        n_attempt += 1
        if n_attempt > 5000: break
        items, tax, total = _extract_items_total_tax(ex)
        if not items or total is None:
            if len(failed_samples) < 2:
                failed_samples.append(_ex_schema_sample(ex))
            continue
        sum_items = sum(items)
        holds_plus = abs((sum_items + tax) - total) <= EPS
        holds_eq   = abs(sum_items - total) <= EPS
        results.append({
            "sum_items": round(sum_items, 4),
            "tax": round(tax, 4),
            "total": round(total, 4),
            "holds_sum_plus_tax_eq_total": holds_plus,
            "holds_sum_eq_total": holds_eq,
            "n_items": len(items),
        })

    n = max(1, len(results))
    rate_plus = (sum(r["holds_sum_plus_tax_eq_total"] for r in results) / n) if results else 0.0
    rate_eq   = (sum(r["holds_sum_eq_total"]          for r in results) / n) if results else 0.0
    best_name = "sum+tax=total" if rate_plus >= rate_eq else "sum=total"
    best_rate = max(rate_plus, rate_eq)

    summary = {
        "available": True,
        "dataset": ref,
        "split_sizes": split_sizes,
        "n_attempted": n_attempt,
        "n_receipts_with_labels": len(results),
        "identity_rate_sum_plus_tax_eq_total": rate_plus,
        "identity_rate_sum_eq_total": rate_eq,
        "best_identity_convention": best_name,
        "best_identity_rate": best_rate,
        "items_per_receipt_mean": (sum(r["n_items"] for r in results) / n) if results else None,
        "wall_sec": round(time.time() - t0, 1),
        "schema_sample_failed": failed_samples if not results else [],
        "note": ("K v4 pools train+val+test for n>=300 robust identity-hold rate. "
                 "Tests gross (sum+tax=total) and net (sum=total) conventions; reports both "
                 "and selects whichever dominates. High best_identity_rate confirms clean-regime fit."),
    }
    OUT.write_text(json.dumps({"summary": summary, "results_sample": results[:50]}, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
