"""Corpus download helpers.

CORD-v2 is hosted on HuggingFace as `naver-clova-ix/cord-v2`; we use
`datasets.load_dataset(..., split=...)` and persist with `save_to_disk`
so the on-disk shape matches what `cord_loader.load_cord` expects.

SROIE Task-3 has no clean public auto-download — the official ICDAR
2019 Robust Reading challenge gates it behind a registration. The
`download_sroie` function expects an already-downloaded zip and just
does the unzip + sanity-check. The README documents where to get it.

Usage:
    python -m <pkg>.data.download cord  --dest /workspace/datasets/cord-v2
    python -m <pkg>.data.download sroie --src /downloads/SROIE.zip --dest /workspace/datasets/SROIE_Task3
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import zipfile
from pathlib import Path
from typing import List, Optional


def download_cord(dest: str, splits: Optional[List[str]] = None,
                  hf_id: str = "naver-clova-ix/cord-v2") -> None:
    """Pull CORD-v2 from HuggingFace and save_to_disk under `dest/<split>/`."""
    try:
        from datasets import load_dataset  # type: ignore
    except ImportError as e:
        raise ImportError(
            "CORD download requires the `datasets` package. "
            "Install with: pip install datasets"
        ) from e
    splits = splits or ["train", "validation", "test"]
    dest_root = Path(dest)
    dest_root.mkdir(parents=True, exist_ok=True)
    for split in splits:
        out_dir = dest_root / split
        if (out_dir / "dataset_info.json").exists():
            print(f"[download] {hf_id}:{split} already at {out_dir}, skipping")
            continue
        print(f"[download] fetching {hf_id}:{split} -> {out_dir}")
        ds = load_dataset(hf_id, split=split)
        ds.save_to_disk(str(out_dir))
    # Quick sanity-check: try the loader.
    from .cord_loader import load_cord
    receipts = load_cord(str(dest_root), max_receipts=5, split="test")
    print(f"[download] CORD sanity check: loaded {len(receipts)} receipts; "
          f"first gold = {receipts[0].gold_total_cents if receipts else 'n/a'}")


def download_sroie(src: str, dest: str) -> None:
    """Unzip an already-downloaded SROIE Task-3 archive into `dest/`.

    The official archive bundles `0325updated.task1train(626p).zip` etc.
    rather than the train/test split layout the loader expects. After
    unzipping we look for {img,box,entities}/ directly; if missing we
    print where the layout differs so the user can rearrange manually.
    """
    src_path = Path(src)
    dest_path = Path(dest)
    if not src_path.exists():
        raise FileNotFoundError(
            f"SROIE archive not found at {src_path}. SROIE Task-3 is "
            f"gated by registration at "
            f"https://rrc.cvc.uab.es/?ch=13&com=downloads — once you've "
            f"downloaded the archive, pass --src to this command."
        )
    dest_path.mkdir(parents=True, exist_ok=True)
    print(f"[download] unzipping {src_path} -> {dest_path}")
    with zipfile.ZipFile(src_path) as zf:
        zf.extractall(dest_path)
    needed = {"img", "box", "entities"}
    have = {p.name for p in dest_path.iterdir() if p.is_dir()}
    if not needed.issubset(have):
        print(
            f"[download] note: extracted dirs {sorted(have)} do not match "
            f"{sorted(needed)}. SROIE archives sometimes ship as nested zips "
            f"(`0325updated.task1train(626p).zip`, etc.); unzip those into "
            f"a single root with img/box/entities/ subdirs and re-run.",
            file=sys.stderr,
        )
        return
    from .sroie_loader import load_sroie
    receipts = load_sroie(str(dest_path), max_receipts=5)
    print(f"[download] SROIE sanity check: loaded {len(receipts)} receipts; "
          f"first gold = {receipts[0].gold_total_cents if receipts else 'n/a'}")


def main():
    ap = argparse.ArgumentParser(description="corpus download helper")
    sub = ap.add_subparsers(dest="corpus", required=True)
    p_cord = sub.add_parser("cord", help="CORD-v2 from HuggingFace")
    p_cord.add_argument("--dest", required=True)
    p_cord.add_argument("--splits", default="train,validation,test")
    p_cord.add_argument("--hf_id", default="naver-clova-ix/cord-v2")
    p_sroie = sub.add_parser("sroie", help="SROIE Task-3 (provide local zip)")
    p_sroie.add_argument("--src", required=True, help="path to the SROIE zip")
    p_sroie.add_argument("--dest", required=True)
    args = ap.parse_args()
    if args.corpus == "cord":
        download_cord(args.dest, args.splits.split(","), args.hf_id)
    else:
        download_sroie(args.src, args.dest)


if __name__ == "__main__":
    main()
