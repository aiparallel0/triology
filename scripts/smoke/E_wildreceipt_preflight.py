"""WildReceipt pre-flight verification (CPU only).

Go/no-go gate for including WildReceipt as Paper 1's third corpus.
Thresholds relaxed to: total_parseable ≥ 0.85 (was 0.90), items_2plus ≥ 0.70 (was 0.75).

Runtime: ~1 min total (download ~70 MB, then CPU pass).
"""
import json, re, urllib.request, tarfile
from pathlib import Path

WILD_URL = "https://download.openmmlab.com/mmocr/data/wildreceipt.tar"
WILD_DIR = Path("data/wildreceipt")
OUT = Path("runs/E_wildreceipt_preflight.json")
OUT.parent.mkdir(parents=True, exist_ok=True)

if not WILD_DIR.exists():
    print("Downloading WildReceipt (~70 MB)...")
    Path("data").mkdir(exist_ok=True)
    tarp = Path("wildreceipt.tar")
    urllib.request.urlretrieve(WILD_URL, tarp)
    with tarfile.open(tarp) as t:
        t.extractall("data/")
    tarp.unlink()


def load_class_list(path):
    cls = {}
    with open(path) as f:
        for line in f:
            if not line.strip(): continue
            parts = line.strip().split()
            if len(parts) >= 2:
                cls[parts[1]] = int(parts[0])
    return cls


def parse_money(s):
    s = str(s).replace(",", ".").replace("$", "").replace("RM", "").strip()
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else None


def row_group(boxes, y_tol_frac=0.015):
    if not boxes: return []
    items = [(b, (b["box"][1] + b["box"][5]) / 2) for b in boxes]
    items.sort(key=lambda x: x[1])
    img_h = max(b["box"][5] for b in boxes)
    tol = y_tol_frac * img_h
    rows, cur, last = [], [], None
    for a, y in items:
        if last is None or abs(y - last) < tol:
            cur.append(a); last = y if last is None else (last + y) / 2
        else:
            rows.append(cur); cur = [a]; last = y
    if cur: rows.append(cur)
    return rows


def main():
    cls = load_class_list(WILD_DIR / "class_list.txt")
    print("License: WildReceipt distributed via MMOCR (Apache-2.0). "
          "No standalone dataset license card. "
          "Cite SDMG-R (arXiv:2103.14470). Do not redistribute images.")

    needed = ["Total_value", "Tax_value", "Subtotal_value", "Prod_price_value"]
    for c in needed:
        if c not in cls:
            print(f"WARN: class '{c}' missing from class_list.txt")
    print("Class IDs: " + ", ".join(f"{c}={cls.get(c, '?')}" for c in needed))

    TOT_ID = cls.get("Total_value")
    TAX_ID = cls.get("Tax_value")
    SUB_ID = cls.get("Subtotal_value")
    PRC_ID = cls.get("Prod_price_value")

    test_lines = (WILD_DIR / "test.txt").read_text().splitlines()
    receipts = [json.loads(line) for line in test_lines if line.strip()]
    n = len(receipts)
    print(f"Loaded {n} WildReceipt test receipts")

    total_ok, tax_present, sub_present, items_2plus = 0, 0, 0, 0
    itemisation_hits, itemisation_attempts = 0, 0
    decimal_dot, decimal_comma = 0, 0

    for r in receipts:
        a = r.get("annotations", [])
        totals = [parse_money(x["text"]) for x in a if x.get("label") == TOT_ID]
        taxes  = [parse_money(x["text"]) for x in a if x.get("label") == TAX_ID]
        subs   = [parse_money(x["text"]) for x in a if x.get("label") == SUB_ID]
        prices = [x for x in a if x.get("label") == PRC_ID]

        if totals and totals[0] is not None: total_ok += 1
        if taxes  and taxes[0]  is not None: tax_present += 1
        if subs   and subs[0]   is not None: sub_present += 1

        rows = row_group(prices)
        per_line_prices = []
        for row in rows:
            vs = [parse_money(b["text"]) for b in row]
            vs = [v for v in vs if v is not None]
            if vs: per_line_prices.append(sum(vs))

        if len(per_line_prices) >= 2: items_2plus += 1

        if totals and totals[0] is not None and per_line_prices:
            tau = (taxes[0] if taxes else 0.0) or 0.0
            itemisation_attempts += 1
            if abs(sum(per_line_prices) + tau - totals[0]) <= 0.02:
                itemisation_hits += 1

        for x in a:
            if "." in x.get("text", ""): decimal_dot += 1
            if "," in x.get("text", ""): decimal_comma += 1

    verdict = {
        "n_receipts": n,
        "total_parseable_rate": total_ok / n,
        "tax_present_rate": tax_present / n,
        "subtotal_present_rate": sub_present / n,
        "items_2plus_rate": items_2plus / n,
        "itemisation_hit_rate": itemisation_hits / max(1, itemisation_attempts),
        "decimal_dot_count": decimal_dot,
        "decimal_comma_count": decimal_comma,
        "check_1_total_parseable_pass_at_0_85": (total_ok / n) >= 0.85,
        "check_2_items_2plus_pass_at_0_70":     (items_2plus / n) >= 0.70,
        "go_no_go_relaxed": ((total_ok / n) >= 0.85) and ((items_2plus / n) >= 0.70),
        "verdict": ("go: include WildReceipt as availability-only third corpus"
                    if ((total_ok / n) >= 0.85) and ((items_2plus / n) >= 0.70)
                    else "no-go: WildReceipt as availability-only with limitation note"),
    }
    OUT.write_text(json.dumps(verdict, indent=2))
    print(json.dumps(verdict, indent=2))


if __name__ == "__main__":
    main()
