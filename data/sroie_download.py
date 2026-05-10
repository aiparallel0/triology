"""SROIE Task-3 auto-download (no manual upload, no ICDAR registration).

Strategy (in order, with fallback):

  1. Public **tarball** of the git mirror — single HTTP(S) GET against
     `codeload.github.com`, much faster than `git clone` when egress to
     `github.com` is throttled (which vast.ai sometimes is).

  2. Public git mirror — `zzzDavid/ICDAR-2019-SROIE` (~50 MB, flat
     `data/{img, box, key}/` layout). Used if the tarball fetch fails.

  3. HuggingFace mirror — `Metric-AI/icdar_sroie` (Donut-style JSON
     ground-truth, no box files). Last resort: useful for verifier-
     level smoke tests, but reachability metrics that depend on box-
     derived OCR text won't produce meaningful numbers.

All paths normalize to the canonical `<dest>/test/{img, box, entities}/`
shape that `sroie_loader.load_sroie` expects. Idempotent: re-running
with an already-populated `<dest>/test/img/` returns immediately.
"""
from __future__ import annotations
import io
import json
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path
from typing import Optional


GIT_MIRROR_URL = "https://github.com/zzzDavid/ICDAR-2019-SROIE.git"
GIT_MIRROR_TARBALLS = (
    # codeload is GitHub's archive endpoint; HEAD on default branch.
    "https://codeload.github.com/zzzDavid/ICDAR-2019-SROIE/tar.gz/refs/heads/master",
    "https://codeload.github.com/zzzDavid/ICDAR-2019-SROIE/tar.gz/refs/heads/main",
)
HF_MIRROR_REPO = "Metric-AI/icdar_sroie"
HF_FIELD_KEYS = ("company", "date", "address", "total")


def _is_populated(dest_test: Path) -> bool:
    img = dest_test / "img"
    ent = dest_test / "entities"
    return (
        img.is_dir() and ent.is_dir()
        and any(img.glob("*.jpg")) and any(ent.iterdir())
    )


def _normalize_flat_layout(src_data: Path, test_dir: Path) -> None:
    """Copy flat {img, box, key} -> canonical {img, box, entities}."""
    if not src_data.exists():
        raise RuntimeError(
            f"unexpected mirror layout: missing {src_data}. The "
            f"mirror's directory structure may have changed."
        )
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
            out_name = (
                f.with_suffix(".txt").name
                if dst_name == "box" and f.suffix == ".csv"
                else f.name
            )
            shutil.copy(f, dst / out_name)


def _tarball_mirror(dest: Path) -> None:
    """Single-GET tarball of the mirror — usually 5-10x faster than git clone."""
    test_dir = dest / "test"
    if _is_populated(test_dir):
        print(f"[sroie] cached at {test_dir}, skipping tarball fetch",
              file=sys.stderr)
        return

    last_err: Optional[Exception] = None
    for url in GIT_MIRROR_TARBALLS:
        print(f"[sroie] GET {url}", file=sys.stderr)
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "paper3-sroie/1.0"},
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                buf = io.BytesIO(resp.read())
            with tarfile.open(fileobj=buf, mode="r:gz") as tf:
                tmp = dest / "_tar"
                if tmp.exists():
                    shutil.rmtree(tmp)
                tmp.mkdir(parents=True, exist_ok=True)
                tf.extractall(tmp)
            # Tarball top-level is e.g. "ICDAR-2019-SROIE-master/"
            top = next((p for p in tmp.iterdir() if p.is_dir()), None)
            if top is None:
                raise RuntimeError("tarball had no top-level directory")
            _normalize_flat_layout(top / "data", test_dir)
            shutil.rmtree(tmp, ignore_errors=True)
            return
        except Exception as e:
            last_err = e
            print(f"[sroie] tarball {url} failed: {e}", file=sys.stderr)
            continue
    raise RuntimeError(f"all tarball URLs failed; last error: {last_err!r}")


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
    _normalize_flat_layout(tmp / "data", test_dir)
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
                        prefer: str = "tar",
                        hf_repo: str = HF_MIRROR_REPO) -> Path:
    """Auto-download SROIE Task-3 to `<dest>/test/{img,box,entities}/`.

    `prefer`:
        "tar" — try tarball first, fall back to git, then HF (default)
        "git" — try git first, fall back to tarball, then HF
        "hf"  — try HuggingFace first

    Idempotent.
    """
    dest_path = Path(dest)
    dest_path.mkdir(parents=True, exist_ok=True)

    if _is_populated(dest_path / "test"):
        print(f"[sroie] already populated at {dest_path / 'test'}",
              file=sys.stderr)
        return dest_path

    if prefer == "tar":
        sources = [_tarball_mirror, _git_clone_mirror, _hf_fallback]
    elif prefer == "git":
        sources = [_git_clone_mirror, _tarball_mirror, _hf_fallback]
    elif prefer == "hf":
        sources = [_hf_fallback, _tarball_mirror, _git_clone_mirror]
    else:
        raise ValueError(f"unknown prefer={prefer!r}")

    last_err: Optional[Exception] = None
    for fn in sources:
        try:
            if fn is _hf_fallback:
                fn(dest_path, hf_repo)
            else:
                fn(dest_path)
            if _is_populated(dest_path / "test"):
                return dest_path
        except Exception as e:
            last_err = e
            print(f"[sroie] {fn.__name__} failed: {e}", file=sys.stderr)
            continue

    raise RuntimeError(
        "All SROIE auto-download paths failed. "
        f"Last error: {last_err!r}. You can also pass the canonical "
        "RRC zip via --src."
    )
