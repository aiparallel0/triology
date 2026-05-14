"""K: DocILE 4th corpus — additive in-distribution validation of I3 (labeled-amounts regime).

DocILE is a CC BY-NC invoice corpus with labeled per-line totals and grand totals.
This adds a 4th in-distribution test to corroborate B (CORD) and F (WildReceipt) by
showing receipt-arithmetic identity holds at high rate on independently-labeled data.
The I3 method is UNCHANGED; this is additive validation, not a replacement for SROIE.

Robustness: tries multiple HF mirrors. If none reach, writes a 'not available' summary
and exits 0 (this is bonus validation, not a blocker).

Runtime: ~30-60 s if dataset reachable; <1 s if not.
"""
import json, os, time
from pathlib import Path

OUT = Path("runs/K_docile.json")
OUT.parent.mkdir(parents=True, exist_ok=True)


def try_load_docile():
    from datasets import load_dataset
    candidates = [
        ("harborwater/docile-trial", "test"),
        ("naver-clova-ix/docile-trial", "test"),
        ("idd-fit/docile-trial", "test"),
        ("katanaml-org/invoices-donut-data-v1", "test"),
        ("katanaml-org/invoices-donut-data-v1", "validation"),
        ("mychen76/invoices-and-receipts_ocr_v1", "test"),
        ("mychen76/invoices-and-receipts_ocr_v1", "valid"),
    ]
    for ref, split in candidates:
        try:
            ds = load_dataset(ref, split=split, trust_remote_code=True)
            print(f"  loaded {ref} split={split} n={len(ds)}")
            return ds, ref, split
        except Exception as e:
            print(f"  miss {ref} [{split}]: {type(e).__name__}")
    return None, None, None


def _try_float(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _try_floats(seq):
    if seq is None:
        return []
    out = []
    for x in seq:
        v = _try_float(x)
        if v is not None:
            out.append(v)
    return out


def _extract_items_total_tax(ex):
    """Schema-flex extractor: tries several common invoice-label key sets."""
    total_keys = ["total_amount", "grand_total", "total", "amount_total", "invoice_total"]
    item_keys = ["line_total", "line_item_total", "line_totals", "amount", "line_amounts", "item_amounts"]
    tax_keys = ["tax_total", "tax_amount", "tax", "vat", "vat_total"]

    total = None
    for k in total_keys:
        if k in ex:
            total = _try_float(ex[k])
            if total is not None: break

    items = []
    for k in item_keys:
        if k in ex:
            items = _try_floats(ex[k] if isinstance(ex[k], (list, tuple)) else [ex[k]])
            if items: break

    tax = 0.0
    for k in tax_keys:
        if k in ex:
            v = _try_float(ex[k])
            if v is not None:
                tax = v
                break

    # ground_truth json (Donut-style)
    if (total is None or not items) and "ground_truth" in ex:
        try:
            gt = ex["ground_truth"]
            if isinstance(gt, str):
                gt = json.loads(gt)
            if isinstance(gt, dict):
                if total is None:
                    for k in total_keys:
                        if k in gt:
                            total = _try_float(gt[k])
                            if total is not None: break
                if not items:
                    for k in item_keys:
                        if k in gt:
                            v = gt[k]
                            if isinstance(v, (list, tuple)):
                                items = _try_floats(v)
                            if items: break
                if tax == 0.0:
                    for k in tax_keys:
                        if k in gt:
                            v = _try_float(gt[k])
                            if v is not None:
                                tax = v
                                break
        except Exception:
            pass

    return items, tax, total


def main():
    t0 = time.time()
    print("=== K: DocILE 4th corpus (graceful) ===")
    ds, ref, split = try_load_docile()
    if ds is None:
        summary = {
            "available": False,
            "reason": "no DocILE-like mirror reachable",
            "wall_sec": round(time.time() - t0, 1),
            "note": ("K is bonus validation. If unavailable, the 3-corpus story (SROIE+CORD+WildReceipt) "
                     "plus G's robustness + H's bucket AUROC remain the empirical backbone."),
        }
        OUT.write_text(json.dumps(summary, indent=2))
        print(json.dumps(summary, indent=2))
        return

    results = []
    n_attempt = 0
    for ex in ds:
        n_attempt += 1
        if n_attempt > 2000:  # cap for runtime
            break
        items, tax, total = _extract_items_total_tax(ex)
        if not items or total is None:
            continue
        sum_items = sum(items)
        identity_holds = abs((sum_items + tax) - total) <= 0.05
        results.append({"sum_items": sum_items, "tax": tax, "total": total,
                        "identity_holds": identity_holds, "n_items": len(items)})

    n = max(1, len(results))
    summary = {
        "available": True,
        "dataset": ref,
        "split": split,
        "n_attempted": n_attempt,
        "n_receipts_with_labels": len(results),
        "identity_holds_rate": sum(r["identity_holds"] for r in results) / n if results else None,
        "items_per_receipt_mean": (sum(r["n_items"] for r in results) / n) if results else None,
        "wall_sec": round(time.time() - t0, 1),
        "note": ("K validates that DocILE's labeled per-line amounts satisfy receipt-arithmetic at high rate. "
                 "A high identity_holds_rate confirms DocILE is a clean-regime corpus: when a sigma is "
                 "deployed with an in-domain extractor, sigma_precision should approach 1.0 here too. "
                 "This is additive validation of I3, not a replacement for SROIE's harder OCR-driven case."),
    }
    OUT.write_text(json.dumps({"summary": summary, "results_sample": results[:50]}, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
