"""Corpus download helpers.

CORD-v2 is hosted on HuggingFace as `naver-clova-ix/cord-v2`; we use
`datasets.load_dataset(..., split=...)` and persist with `save_to_disk`
so the on-disk shape matches what `cord_loader.load_cord` expects.

SROIE Task-3 — auto-fetched from a public git mirror
(`zzzDavid/ICDAR-2019-SROIE`, ~50 MB, no auth) so the harness needs
no manual upload and no ICDAR registration. A HuggingFace mirror
(`Metric-AI/icdar_sroie`) acts as a fallback. The official RRC zip
remains supported via --src for users who do have credentials.

Usage:
    python -m <pkg>.data.download cord  --dest /workspace/datasets/cord-v2
    python -m <pkg>.data.download sroie --dest /workspace/datasets/SROIE_Task3
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


def download_sroie(dest: str, src: Optional[str] = None,
                   prefer: str = "git") -> None:
    """Make `<dest>/test/{img,box,entities}/` exist.

    Three paths, in priority order:
      1. If `--src` is passed, unzip the user-supplied RRC zip (the
         original gated-but-canonical archive).
      2. Otherwise auto-fetch from the public git mirror
         (zzzDavid/ICDAR-2019-SROIE, ~50 MB).
      3. Fall back to the HuggingFace mirror (Metric-AI/icdar_sroie,
         JSON entities only — no box files, so reachability metrics
         that need OCR text won't work).
    """
    dest_path = Path(dest)
    if src:
        src_path = Path(src)
        if not src_path.exists():
            raise FileNotFoundError(
                f"SROIE archive not found at {src_path}. Drop the --src "
                f"flag to auto-download from the public mirror."
            )
        dest_path.mkdir(parents=True, exist_ok=True)
        print(f"[download] unzipping {src_path} -> {dest_path}")
        with zipfile.ZipFile(src_path) as zf:
            zf.extractall(dest_path)
    else:
        from .sroie_download import download_sroie_auto
        download_sroie_auto(str(dest_path), prefer=prefer)

    # Sanity check via the loader.
    from .sroie_loader import load_sroie
    test_root = dest_path / "test" if (dest_path / "test").exists() else dest_path
    try:
        receipts = load_sroie(str(test_root), max_receipts=5)
    except FileNotFoundError as e:
        print(f"[download] note: layout sanity-check skipped — {e}",
              file=sys.stderr)
        return
    if not receipts:
        print("[download] note: 0 receipts loaded; check layout under "
              f"{test_root}", file=sys.stderr)
        return
    print(f"[download] SROIE sanity check: loaded {len(receipts)} receipts; "
          f"first gold = {receipts[0].gold_total_cents}")


def main():
    ap = argparse.ArgumentParser(description="corpus download helper")
    sub = ap.add_subparsers(dest="corpus", required=True)
    p_cord = sub.add_parser("cord", help="CORD-v2 from HuggingFace")
    p_cord.add_argument("--dest", required=True)
    p_cord.add_argument("--splits", default="train,validation,test")
    p_cord.add_argument("--hf_id", default="naver-clova-ix/cord-v2")
    p_sroie = sub.add_parser(
        "sroie",
        help="SROIE Task-3 — auto-fetches from a public mirror; "
             "pass --src to unpack a local RRC zip instead.",
    )
    p_sroie.add_argument("--dest", required=True)
    p_sroie.add_argument("--src", default=None,
                         help="path to a local RRC zip (optional)")
    p_sroie.add_argument("--prefer", choices=["tar", "git", "hf"], default="tar",
                         help="which mirror to try first (default: tar — "
                              "single-GET tarball, usually fastest)")
    args = ap.parse_args()
    if args.corpus == "cord":
        download_cord(args.dest, args.splits.split(","), args.hf_id)
    else:
        download_sroie(args.dest, src=args.src, prefer=args.prefer)


if __name__ == "__main__":
    main()
