"""K v2: DocILE-like 4th corpus — additive in-distribution validation of I3 identity.

v2 fixes katanaml-org/invoices-donut-data-v1 schema (Donut-format ground_truth JSON with
gt_parse.{header, items, summary}). Adds a sample-on-fail diagnostic so future schema
mismatches are debuggable from the JSON output.

Robustness: tries multiple HF mirrors. If none reach OR no records parse, writes a
'not available' summary and exits 0 (this is bonus validation, not a blocker).

The I3 method is UNCHANGED. Identity holds when sum(items) + tax ≈ total (within 0.05).

Runtime: ~30 s if a dataset reaches; <1 s if not.
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

    # Direct top-level keys (DocILE-trial style)
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

    # Donut-format ground_truth JSON (katanaml, mychen76, etc.)
    if (total is None or not items) and "ground_truth" in ex:
        try:
            gt = ex["ground_truth"]
            if isinstance(gt, str):
                gt = json.loads(gt)
            # katanaml format: {"gt_parse": {"header": {...}, "items": [...], "summary": {...}}}
            if isinstance(gt, dict) and "gt_parse" in gt:
                gt = gt["gt_parse"]
            if isinstance(gt, dict):
                # Summary: total + tax
                summary = gt.get("summary") or gt.get("totals") or {}
                if isinstance(summary, dict):
                    if total is None:
                        total = _scan_dict_for_keys(summary, TOTAL_KEYS)
                    if not tax:
                        t = _scan_dict_for_keys(summary, TAX_KEYS)
                        if t is not None: tax = t
                # Items list
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
                # Sometimes total is in gt directly
                if total is None:
                    total = _scan_dict_for_keys(gt, TOTAL_KEYS)
        except Exception:
            pass

    return items, tax, total


def _ex_schema_sample(ex):
    """Compact diagnostic dump of an example's schema (for debugging missed schemas)."""
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
    print("=== K v2: DocILE 4th corpus (graceful + sample-on-fail) ===")
    ds, ref, split = try_load_docile()
    if ds is None:
        summary = {
            "available": False,
            "reason": "no DocILE-like mirror reachable",
            "wall_sec": round(time.time() - t0, 1),
        }
        OUT.write_text(json.dumps(summary, indent=2))
        print(json.dumps(summary, indent=2))
        return

    results = []
    failed_samples = []
    n_attempt = 0
    for ex in ds:
        n_attempt += 1
        if n_attempt > 2000: break
        items, tax, total = _extract_items_total_tax(ex)
        if not items or total is None:
            if len(failed_samples) < 2:
                failed_samples.append(_ex_schema_sample(ex))
            continue
        sum_items = sum(items)
        identity_holds = abs((sum_items + tax) - total) <= 0.05
        results.append({"sum_items": round(sum_items, 4), "tax": round(tax, 4),
                        "total": round(total, 4), "identity_holds": identity_holds,
                        "n_items": len(items)})

    n = max(1, len(results))
    summary = {
        "available": True,
        "dataset": ref,
        "split": split,
        "n_attempted": n_attempt,
        "n_receipts_with_labels": len(results),
        "identity_holds_rate": (sum(r["identity_holds"] for r in results) / n) if results else None,
        "items_per_receipt_mean": (sum(r["n_items"] for r in results) / n) if results else None,
        "wall_sec": round(time.time() - t0, 1),
        "schema_sample_failed": failed_samples if not results else [],
        "note": ("K validates that the chosen invoice/receipt corpus's labeled per-line amounts "
                 "satisfy receipt-arithmetic identity at high rate. A high identity_holds_rate means "
                 "the corpus is in the clean-regime, like CORD/WildReceipt; sigma_precision should "
                 "approach 1.0 here too once an in-domain extractor is added. If schema_sample_failed "
                 "is non-empty, the loader saw records but extractor keys did not match the corpus's schema."),
    }
    OUT.write_text(json.dumps({"summary": summary, "results_sample": results[:50]}, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
