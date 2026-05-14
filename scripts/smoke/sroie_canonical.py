"""Canonical SROIE Task-3 test set fetcher + Task-1 OCR loader.

Produces <data_path>/test/img/<stem>.jpg × 347 + <data_path>/test/entities/<stem>.{txt,json} × 347.
Additionally, load_sroie_ocr_lines() pulls Task-1 OCR (words + bboxes per image)
from darentang/sroie HF mirror and groups by y-coord into per-line text.

Dependencies: urllib (stdlib), zipfile (stdlib), certifi (optional), huggingface_hub,
pyarrow, PIL, datasets (for Task-1 OCR helper).
"""
import ast, hashlib, io, json, logging, ssl, urllib.error, urllib.request, zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)
TASK3_TEST_COUNT = 347

RRC_IMAGES = "https://rrc.cvc.uab.es/downloads/SROIE_test_images_task_3.zip"
RRC_GT     = "https://rrc.cvc.uab.es/downloads/SROIE_test_gt_task_3.zip"
HF_REPO    = "Metric-AI/icdar_sroie"
HF_REV     = "main"
DARENTANG  = "darentang/sroie"  # Task-1 OCR source

_IMAGE_COLS  = ("image", "img", "image_bytes", "receipt_image", "jpg")
_STEM_COLS   = ("file_name", "filename", "id", "image_id", "receipt_id", "stem")
_GT_JSON_COLS = ("ground_truth", "gt_parse", "label", "text")
_FIELD_KEYS  = ("company", "date", "address", "total")


def _ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def _download(url, dst, timeout=60.0):
    dst.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "focus-sigma/1.0"})
    with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as r, dst.open("wb") as out:
        while chunk := r.read(65536):
            out.write(chunk)


def _try_rrc(workdir):
    img_zip, gt_zip = workdir / "rrc_img.zip", workdir / "rrc_gt.zip"
    extract = workdir / "rrc"
    try:
        _download(RRC_IMAGES, img_zip); _download(RRC_GT, gt_zip)
    except (urllib.error.URLError, TimeoutError, OSError, ssl.SSLError) as exc:
        log.warning("RRC primary failed (%s); trying HF fallback.", exc); return None
    extract.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(img_zip) as zf: zf.extractall(extract)
    with zipfile.ZipFile(gt_zip)  as zf: zf.extractall(extract)
    return extract


def _place_files(src_root, dst, glob_pat, marker, *, is_entity):
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    for p in src_root.rglob(glob_pat):
        if not p.is_file() or marker not in p.parts: continue
        if is_entity:
            try: head = p.read_text(errors="ignore").lstrip()[:1]
            except OSError: continue
            if head != "{": continue
        target = dst / p.name
        if not target.exists(): p.replace(target)
        n += 1
    return n


def _extract_stem(row, idx):
    for col in _STEM_COLS:
        v = row.get(col)
        if v and str(v).strip():
            stem = str(v).strip()
            return stem.rsplit(".", 1)[0] if "." in stem else stem
    img = row.get("image")
    if isinstance(img, dict):
        path = img.get("path")
        if isinstance(path, str) and path.strip():
            return Path(path).stem
    return f"X{idx:08d}"


def _extract_image_bytes(row):
    for col in _IMAGE_COLS:
        v = row.get(col)
        if v is None: continue
        if isinstance(v, dict):
            raw = v.get("bytes")
            if isinstance(raw, (bytes, bytearray)):
                raw_b = bytes(raw)
                if raw_b[:3] == b"\xff\xd8\xff": return raw_b
                try:
                    import PIL.Image
                    img = PIL.Image.open(io.BytesIO(raw_b)).convert("RGB")
                    buf = io.BytesIO(); img.save(buf, format="JPEG")
                    return buf.getvalue()
                except (ImportError, OSError): return None
        if isinstance(v, (bytes, bytearray)): return bytes(v)
        try:
            import PIL.Image
            if isinstance(v, PIL.Image.Image):
                buf = io.BytesIO(); v.convert("RGB").save(buf, format="JPEG")
                return buf.getvalue()
        except ImportError: pass
        if isinstance(v, (str, Path)) and Path(str(v)).is_file():
            return Path(str(v)).read_bytes()
    return None


def _extract_gt(row):
    raw = next((row[c] for c in _GT_JSON_COLS if c in row and row[c]), None)
    if raw is None:
        flat = {f: str(row.get(f, "") or "") for f in _FIELD_KEYS}
        return flat if all(flat[k] for k in _FIELD_KEYS) else None
    if isinstance(raw, str):
        try: obj = json.loads(raw)
        except json.JSONDecodeError:
            try: obj = ast.literal_eval(raw)
            except (ValueError, SyntaxError): return None
    elif isinstance(raw, dict): obj = raw
    else: return None
    if isinstance(obj, dict) and isinstance(obj.get("gt_parse"), dict):
        obj = obj["gt_parse"]
    if (isinstance(obj, dict) and isinstance(obj.get("gt_parses"), list)
            and obj["gt_parses"] and isinstance(obj["gt_parses"][0], dict)):
        obj = obj["gt_parses"][0]
    if not isinstance(obj, dict): return None
    obj_lower = {str(k).lower(): str(v) for k, v in obj.items()}
    out = {}
    for k in _FIELD_KEYS:
        if k in obj_lower and obj_lower[k]: out[k] = obj_lower[k]
        else: return None
    return out


def _read_parquet_splits(snap):
    import pyarrow.parquet as pq
    data_dir = snap / "data" if (snap / "data").is_dir() else snap
    grouped = {}
    for p in sorted(data_dir.rglob("*.parquet")):
        grouped.setdefault(p.stem.split("-", 1)[0].lower(), []).append(p)
    return {k: (pq.read_table(v[0]) if len(v) == 1
                else pq.concat_tables([pq.read_table(f) for f in v]))
            for k, v in grouped.items()}


def _try_huggingface(workdir):
    try: from huggingface_hub import snapshot_download
    except ImportError: return None
    work = workdir / "hf"
    img_dir = work / "img";      img_dir.mkdir(parents=True, exist_ok=True)
    ent_dir = work / "entities"; ent_dir.mkdir(parents=True, exist_ok=True)
    snap_dir = work / "_snap"
    try:
        snap = snapshot_download(repo_id=HF_REPO, revision=HF_REV,
                                 repo_type="dataset", local_dir=str(snap_dir))
    except Exception as exc:
        log.warning("HF download failed: %s", exc); return None
    tables = _read_parquet_splits(Path(snap))
    rows = None
    for split in ("test", "validation", "train"):
        t = tables.get(split)
        if t is not None and t.num_rows == TASK3_TEST_COUNT:
            rows = t.to_pylist(); break
    if rows is None: return None
    n = 0
    for idx, row in enumerate(rows):
        stem  = _extract_stem(row, idx)
        bytes_ = _extract_image_bytes(row)
        gt    = _extract_gt(row)
        if not bytes_ or gt is None: continue
        (img_dir / f"{stem}.jpg").write_bytes(bytes_)
        (ent_dir / f"{stem}.json").write_text(
            json.dumps(gt, ensure_ascii=False), encoding="utf-8")
        n += 1
    if n < TASK3_TEST_COUNT: return None
    return work


def ensure_canonical_test_set(data_path):
    img_dir = data_path / "test" / "img"
    ent_dir = data_path / "test" / "entities"
    if (img_dir.exists()
        and len(list(img_dir.glob("*.jpg"))) == TASK3_TEST_COUNT
        and ent_dir.exists()
        and len(list(ent_dir.iterdir())) == TASK3_TEST_COUNT):
        return ("cached", img_dir, ent_dir)
    workdir = data_path / "_canonical_dl"
    workdir.mkdir(parents=True, exist_ok=True)
    primary = _try_rrc(workdir)
    if primary is not None:
        n_img = _place_files(primary, img_dir, "*.jpg", "task3-test(347p)", is_entity=False)
        n_ent = _place_files(primary, ent_dir, "*.txt", "entities",         is_entity=True)
        mirror = "rrc"
    else:
        hf = _try_huggingface(workdir)
        if hf is None:
            raise RuntimeError("canonical-SROIE: both RRC and HF mirrors failed.")
        n_img = _place_files(hf, img_dir, "*.jpg",  "img",      is_entity=False)
        n_ent = _place_files(hf, ent_dir, "*.json", "entities", is_entity=True)
        mirror = "huggingface"
    if n_img != TASK3_TEST_COUNT or n_ent != TASK3_TEST_COUNT:
        raise RuntimeError(
            f"canonical-SROIE count mismatch ({mirror}): {n_img}/{n_ent}")
    return (mirror, img_dir, ent_dir)


def load_gold_total(stem, ent_dir):
    import re
    def parse_money(s):
        if s is None: return None
        s = str(s).replace(",", "").replace("RM", "").replace("$", "").strip()
        m = re.search(r"-?\d+(?:\.\d+)?", s)
        return float(m.group()) if m else None
    for ext in ("json", "txt"):
        path = ent_dir / f"{stem}.{ext}"
        if not path.exists(): continue
        text = path.read_text(errors="ignore").strip()
        if not text: continue
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                for key in ("total", "TOTAL", "Total"):
                    if key in data and data[key]:
                        return parse_money(data[key])
        except json.JSONDecodeError: pass
    return None


# ----------------------------------------------------------------------
# Task-1 OCR loader: pulls per-line text from darentang/sroie HF mirror
# and groups by y-coord into lines. Indexed by canonical stem.
# ----------------------------------------------------------------------

def _y_center(b):
    if isinstance(b, dict):
        return (b.get("y_min", b.get("y0", 0)) + b.get("y_max", b.get("y1", 0))) / 2
    if hasattr(b, "__len__"):
        if len(b) == 4: return (b[1] + b[3]) / 2
        if len(b) == 8: return (b[1] + b[3] + b[5] + b[7]) / 4
    return 0.0


def _words_to_lines(words, bboxes, y_tol_frac=0.02):
    if not words: return []
    if not bboxes or len(bboxes) != len(words):
        return list(words)
    pairs = sorted(zip(words, bboxes), key=lambda wb: _y_center(wb[1]))
    ys = [_y_center(b) for _, b in pairs]
    yrange = (max(ys) - min(ys)) if len(ys) > 1 else 1.0
    tol = max(8.0, y_tol_frac * yrange)
    lines, cur, last_y = [], [], None
    for (w, b), y in zip(pairs, ys):
        if last_y is None or abs(y - last_y) < tol:
            cur.append(w); last_y = y if last_y is None else 0.5 * (last_y + y)
        else:
            lines.append(" ".join(cur)); cur = [w]; last_y = y
    if cur: lines.append(" ".join(cur))
    return lines


def load_sroie_ocr_lines(stems_needed=None):
    """Pull SROIE Task-1 OCR from darentang/sroie 'test' split.

    Returns {stem: [text_lines]}. Groups per-word OCR into lines by y-coord.
    If stems_needed is None, returns all 347 receipts.
    """
    try:
        from datasets import load_dataset
    except ImportError:
        log.warning("datasets package not installed")
        return {}
    try:
        ds = load_dataset(DARENTANG, split="test", trust_remote_code=True)
    except Exception as e:
        log.warning("darentang/sroie load failed: %s", e)
        return {}
    out = {}
    for ex in ds:
        img_path = ex.get("image_path") or ""
        stem = Path(str(img_path)).stem if img_path else None
        if not stem:
            continue
        if stems_needed is not None and stem not in stems_needed:
            continue
        words = ex.get("words", [])
        bboxes = ex.get("bboxes", [])
        lines = _words_to_lines(words, bboxes)
        out[stem] = lines
    log.info("darentang/sroie loaded %d/%d receipts", len(out),
             len(stems_needed) if stems_needed else 347)
    return out
