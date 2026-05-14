"""DONUT-CORD on SROIE-347 → I3 before/after F1 (cross-corpus end-task).

Paper 1 (FOCUS-Sigma) end-task validation. Cross-corpus regime: a CORD-trained Donut
on Malaysian retail receipts. Tests whether I3 subset-sum verification lifts F1 on a
public, reviewer-recognisable baseline.

Runtime target: ~2.5 min on RTX 4090.
Success: F1_sigma_strict_on_accepted - F1_bare ≥ +0.02.

SROIE schema (darentang/sroie): id, words, bboxes, ner_tags, image_path
"""
import json, os, re, time, urllib.request
from io import BytesIO
from pathlib import Path

import torch
from PIL import Image
from datasets import load_dataset
from transformers import DonutProcessor, VisionEncoderDecoderModel

CKPT = "naver-clova-ix/donut-base-finetuned-cord-v2"
SROIE_HF = os.environ.get("SROIE_HF", "darentang/sroie")
OUT = Path("runs/A_donut_cord_on_sroie.json")
OUT.parent.mkdir(parents=True, exist_ok=True)


def parse_money(s):
    if s is None: return None
    s = str(s).replace(",", "").replace("RM", "").replace("$", "").strip()
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else None


def parse_donut_total(text):
    for tag in ("<s_total.total_price>", "<s_total_price>", "<s_total>"):
        m = re.search(re.escape(tag) + r"([^<]+)", text)
        if m:
            return parse_money(m.group(1))
    return None


DROP_KW = re.compile(r"\b(total|sub.?total|cash|change|paid|balance|tendered?)\b", re.I)
TAX_KW  = re.compile(r"\b(tax|gst|sst|vat)\b", re.I)
SERV_KW = re.compile(r"\b(service)\b", re.I)
DISC_KW = re.compile(r"\b(discount|rebate)\b", re.I)


def extract_money_lines(text_lines):
    money, tau = [], 0.0
    for ln in text_lines:
        v = parse_money(ln)
        if v is None:
            continue
        if TAX_KW.search(ln) or SERV_KW.search(ln):
            tau += v
        elif DISC_KW.search(ln):
            tau -= v
        elif DROP_KW.search(ln):
            continue
        else:
            money.append(v)
    return money, tau


def I3_reachable(money_lines, tau, eps=0.02):
    kmin = 1 if abs(tau) > eps else 2
    cents = [int(round(v * 100)) for v in money_lines]
    tau_c = int(round(tau * 100))
    D = {0: 0}
    for v in cents:
        new = dict(D)
        for s, k in D.items():
            ns = s + v
            if ns not in new or new[ns] > k + 1:
                new[ns] = k + 1
        D = new
    return {(s + tau_c) / 100.0 for s, k in D.items() if k >= kmin}


def load_img(img_field):
    """Robust image loader: handles PIL.Image, dict with bytes/path, str URL/path, bytes."""
    if hasattr(img_field, "convert"):
        return img_field.convert("RGB")
    if isinstance(img_field, dict):
        if img_field.get("bytes"):
            return Image.open(BytesIO(img_field["bytes"])).convert("RGB")
        if img_field.get("path"):
            return Image.open(img_field["path"]).convert("RGB")
    if isinstance(img_field, str):
        if img_field.startswith(("http://", "https://")):
            with urllib.request.urlopen(img_field) as r:
                return Image.open(BytesIO(r.read())).convert("RGB")
        return Image.open(img_field).convert("RGB")
    if isinstance(img_field, (bytes, bytearray)):
        return Image.open(BytesIO(img_field)).convert("RGB")
    raise ValueError(f"Cannot load image from type={type(img_field).__name__}")


def y_center(b):
    """Get y-center from various bbox formats: 4-coord [x0,y0,x1,y1], 8-coord polygon, dict."""
    if isinstance(b, dict):
        return (b.get("y_min", b.get("y0", 0)) + b.get("y_max", b.get("y1", 0))) / 2
    if hasattr(b, "__len__"):
        if len(b) == 4:
            return (b[1] + b[3]) / 2
        if len(b) == 8:
            return (b[1] + b[3] + b[5] + b[7]) / 4
    return 0.0


def group_words_to_lines(words, bboxes, y_tol_frac=0.02):
    """Cluster words by y-coord into lines; returns list of joined text strings."""
    if not words:
        return []
    if not bboxes or len(bboxes) != len(words):
        return list(words)
    items = sorted(zip(words, bboxes), key=lambda wb: y_center(wb[1]))
    ys = [y_center(b) for _, b in items]
    yrange = (max(ys) - min(ys)) if len(ys) > 1 else 1.0
    tol = max(8.0, y_tol_frac * yrange)
    lines, cur, last_y = [], [], None
    for (w, b), y in zip(items, ys):
        if last_y is None or abs(y - last_y) < tol:
            cur.append(w)
            last_y = y if last_y is None else 0.5 * (last_y + y)
        else:
            lines.append(" ".join(cur)); cur = [w]; last_y = y
    if cur:
        lines.append(" ".join(cur))
    return lines


def get_ner_label_names(ds):
    try:
        feat = ds.features["ner_tags"]
        if hasattr(feat, "feature") and hasattr(feat.feature, "names"):
            return feat.feature.names
    except Exception:
        pass
    return None


def get_gold_total(ex, ner_label_names):
    """Extract gold total from ner_tags (BIO) joined with words; fallback to explicit fields."""
    tags = ex.get("ner_tags", [])
    words = ex.get("words", [])
    if tags and words:
        total_text = []
        for i, t in enumerate(tags):
            if i >= len(words):
                break
            if isinstance(t, int) and ner_label_names:
                name = ner_label_names[t] if 0 <= t < len(ner_label_names) else str(t)
            else:
                name = str(t)
            if "TOTAL" in name.upper():
                total_text.append(words[i])
        if total_text:
            return parse_money("".join(total_text))
    for k in ("total", "gold_total"):
        v = ex.get(k)
        if v is not None:
            return parse_money(str(v) if not isinstance(v, dict) else str(v.get("total", "")))
    label = ex.get("label")
    if isinstance(label, dict) and "total" in label:
        return parse_money(str(label["total"]))
    return None


def main():
    processor = DonutProcessor.from_pretrained(CKPT)
    model = VisionEncoderDecoderModel.from_pretrained(CKPT, torch_dtype=torch.float16).to("cuda").eval()

    ds = load_dataset(SROIE_HF, split="test", trust_remote_code=True)
    print(f"SROIE test size: {len(ds)}")
    sample = ds[0]
    print(f"Schema keys: {list(sample.keys())[:10]}")
    ner_label_names = get_ner_label_names(ds)
    print(f"NER label names: {ner_label_names}")
    if sample.get("bboxes"):
        print(f"Sample bbox[0]: {sample['bboxes'][0]}  word[0]: {sample.get('words', [None])[0]!r}")

    results, t0 = [], time.time()
    img_load_errors = 0
    for i, ex in enumerate(ds):
        try:
            img_field = ex.get("image") or ex.get("image_path")
            img = load_img(img_field)
        except Exception as e:
            img_load_errors += 1
            if img_load_errors <= 3:
                print(f"  skip {i}: image load failed: {e}")
            continue

        px = processor(img, return_tensors="pt").pixel_values.to("cuda", dtype=torch.float16)
        dec = processor.tokenizer("<s_cord-v2>", add_special_tokens=False,
                                  return_tensors="pt").input_ids.to("cuda")
        with torch.inference_mode():
            out = model.generate(px, decoder_input_ids=dec, max_length=512, num_beams=1,
                                  early_stopping=True,
                                  pad_token_id=processor.tokenizer.pad_token_id)
        text = processor.batch_decode(out, skip_special_tokens=False)[0]
        pred = parse_donut_total(text)

        gold_total = get_gold_total(ex, ner_label_names)
        text_lines = group_words_to_lines(ex.get("words", []), ex.get("bboxes", []))
        money, tau = extract_money_lines(text_lines)
        T = I3_reachable(money, tau) if money else set()
        in_T = pred is not None and any(abs(pred - t) <= 0.02 for t in T)
        correct = (pred is not None and gold_total is not None
                   and abs(pred - gold_total) <= 0.02)

        if i == 0:
            print(f"  [sanity] pred={pred}  gold={gold_total}  |money|={len(money)}  |T|={len(T)}  tau={tau}")

        results.append({"id": ex.get("id", i), "pred": pred, "gold": gold_total,
                        "in_T": in_T, "correct": correct, "T_size": len(T),
                        "money_count": len(money), "tau": tau})
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(ds)}  elapsed={time.time()-t0:.0f}s")

    n = max(1, len(results))
    correct_bare = sum(r["correct"] for r in results)
    accepted = [r for r in results if r["in_T"]]
    correct_strict = sum(r["correct"] for r in accepted)
    parser_ok = sum(1 for r in results if r["pred"] is not None)
    gold_ok = sum(1 for r in results if r["gold"] is not None)
    summary = {
        "n": len(results),
        "img_load_errors": img_load_errors,
        "wall_sec": round(time.time() - t0, 1),
        "parser_ok_rate": parser_ok / n,
        "gold_ok_rate": gold_ok / n,
        "F1_bare": correct_bare / n,
        "accept_rate_sigma": len(accepted) / n,
        "F1_sigma_strict_on_accepted": correct_strict / max(1, len(accepted)),
        "delta_F1": (correct_strict / max(1, len(accepted))) - (correct_bare / n),
    }
    OUT.write_text(json.dumps({"summary": summary, "results": results}, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
