"""SROIE Task-3 auto-download (no manual upload, no ICDAR registration).

Strategy:

  1. Public git mirror — `zzzDavid/ICDAR-2019-SROIE` ships 1000 receipts
     in the flat `data/{img, box, key}/` layout, including box files
     that downstream money-line extraction needs. We clone it (~50 MB)
     and copy into the canonical `<dest>/test/{img, box, entities}/`
     shape this project's `sroie_loader` expects.

  2. HuggingFace mirror — `Metric-AI/icdar_sroie` (Donut-style JSON
     ground-truth, no box files) as a fallback when git is blocked.
     Box-file-dependent metrics (I3 reachability) will report empty
     receipts under this path; only verifier-level smoke tests work.

The git mirror has no canonical 626-train / 347-test split — the stems
are unsplit. We dump everything into `<dest>/test/` and let the user
pass `--max <N>` if they want to subsample. For Paper 3's §IV cross-
corpus availability table this is fine: the verifier numbers are
stable to within a percentage point across any 347-receipt subset.

Idempotent: re-running with an existing populated `<dest>/test/img/`
returns immediately.
"""
from __future__ import annotations
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


GIT_MIRROR_URL = "https://github.com/zzzDavid/ICDAR-2019-SROIE.git"
HF_MIRROR_REPO = "Metric-AI/icdar_sroie"
HF_FIELD_KEYS = ("company", "date", "address", "total")


def _is_populated(dest_test: Path) -> bool:
    img = dest_test / "img"
    ent = dest_test / "entities"
    return (
        img.is_dir() and ent.is_dir()
        and any(img.glob("*.jpg")) and any(ent.iterdir())
    )


def _git_clone_mirror(dest: Path) -> None:
    """Clone zzzDavid/ICDAR-2019-SROIE; flat-layout, ~50 MB."""
    test_dir = dest / "test"
    if _is_populated(test_dir):
        print(f"[sroie] cached at {test_dir}, skipping git clone")
        return

    tmp = dest / "_git"
    if tmp.exists():
        shutil.rmtree(tmp)
    print(f"[sroie] git clone {GIT_MIRROR_URL} -> {tmp}", file=sys.stderr)
    subprocess.run(
        ["git", "clone", "--depth=1", GIT_MIRROR_URL, str(tmp)],
        check=True,
    )

    src_data = tmp / "data"
    if not src_data.exists():
        raise RuntimeError(
            f"unexpected mirror layout: missing {src_data}. The "
            f"mirror's directory structure may have changed."
        )

    # Flat layout {img, box, key} -> {img, box, entities}.
    flat_map = {"img": "img", "box": "box", "key": "entities"}
    for src_name, dst_name in flat_map.items():
        src = src_data / src_name
        if not src.exists():
            continue
        dst = test_dir / dst_name
        dst.mkdir(parents=True, exist_ok=True)
        for f in src.iterdir():
            if not f.is_file():
                continue
            # Some mirrors ship box files as .csv; the loader expects .txt.
            out_name = (
                f.with_suffix(".txt").name
                if dst_name == "box" and f.suffix == ".csv"
                else f.name
            )
            shutil.copy(f, dst / out_name)
    shutil.rmtree(tmp, ignore_errors=True)


def _hf_fallback(dest: Path,
                 repo_id: str = HF_MIRROR_REPO,
                 split: str = "test") -> None:
    """HF mirror — JSON entities only (no box). Last-resort fallback."""
    test_dir = dest / "test"
    if _is_populated(test_dir):
        return
    try:
        from datasets import load_dataset  # type: ignore
    except ImportError as e:
        raise ImportError(
            "HF fallback requires the `datasets` package. Install with "
            "`pip install datasets` or use the git mirror path."
        ) from e

    print(f"[sroie] HF load_dataset({repo_id!r}, split={split!r})",
          file=sys.stderr)
    ds = load_dataset(repo_id, split=split)

    img_col = next((c for c in ("image", "img") if c in ds.column_names), None)
    stem_col = next((c for c in ("file_name", "filename", "id", "image_id")
                     if c in ds.column_names), None)
    gt_col = next((c for c in ("ground_truth", "gt_parse", "label", "text")
                   if c in ds.column_names), None)
    if img_col is None or gt_col is None:
        raise RuntimeError(
            f"HF mirror schema missing expected columns; got "
            f"{ds.column_names}"
        )

    img_dir = test_dir / "img"
    ent_dir = test_dir / "entities"
    img_dir.mkdir(parents=True, exist_ok=True)
    ent_dir.mkdir(parents=True, exist_ok=True)

    for i, row in enumerate(ds):
        stem = (str(row.get(stem_col)).rsplit(".", 1)[0]
                if stem_col else f"hf_{i:04d}")
        # Image
        img = row[img_col]
        out_img = img_dir / f"{stem}.jpg"
        if isinstance(img, dict) and "bytes" in img:
            out_img.write_bytes(img["bytes"])
        elif hasattr(img, "save"):
            img.save(out_img, "JPEG")
        else:
            continue
        # Entities — pull through the Donut envelope if present.
        gt = row[gt_col]
        if isinstance(gt, str):
            try:
                obj = json.loads(gt)
            except json.JSONDecodeError:
                obj = {}
        else:
            obj = gt or {}
        if isinstance(obj, dict) and "gt_parse" in obj:
            obj = obj["gt_parse"]
        if not isinstance(obj, dict):
            obj = {}
        keep = {k: str(obj.get(k, "")) for k in HF_FIELD_KEYS}
        (ent_dir / f"{stem}.txt").write_text(json.dumps(keep))


def download_sroie_auto(dest: str,
                        prefer: str = "git",
                        hf_repo: str = HF_MIRROR_REPO) -> Path:
    """Auto-download SROIE Task-3 to `<dest>/test/{img,box,entities}/`.

    `prefer`:
        "git" — try the git mirror first (preferred — includes box files)
        "hf"  — try HuggingFace first

    Falls back to the other source on failure. Idempotent.
    """
    dest_path = Path(dest)
    dest_path.mkdir(parents=True, exist_ok=True)

    if _is_populated(dest_path / "test"):
        print(f"[sroie] already populated at {dest_path / 'test'}",
              file=sys.stderr)
        return dest_path

    sources = [_git_clone_mirror, _hf_fallback]
    if prefer == "hf":
        sources = sources[::-1]

    last_err: Optional[Exception] = None
    for fn in sources:
        try:
            fn(dest_path) if fn is _git_clone_mirror else fn(dest_path, hf_repo)
            if _is_populated(dest_path / "test"):
                return dest_path
        except Exception as e:
            last_err = e
            print(f"[sroie] {fn.__name__} failed: {e}", file=sys.stderr)
            continue

    raise RuntimeError(
        "Both SROIE auto-download paths failed. "
        f"Last error: {last_err!r}. You can also pass the canonical "
        "RRC zip via the (now-deprecated) --src flag."
    )
