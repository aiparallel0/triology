"""Corpus loading dispatcher.

`load_corpus(name, path=None, n=500, seed=0, max_receipts=None, **extra)`
returns a list of `Receipt` objects regardless of the underlying corpus.

Supported names:
    "synthetic" — built-in fixture (no path, no network, no GPU).
    "sroie"     — SROIE Task-3; `path` is the dataset root.
    "cord"      — CORD-v2; `path` is the dataset root or HF save_to_disk dir.

Extra kwargs are forwarded to the loader and ignored if it doesn't use
them (e.g., `profile` and `confusion_rate` only matter for synthetic).
"""
from __future__ import annotations
from typing import List

from .types import Receipt, MoneyLine


def load_corpus(name: str, path=None, n: int = 500, seed: int = 0,
                max_receipts=None, **extra) -> List[Receipt]:
    name = (name or "").lower()
    if name in ("synthetic", "synth"):
        from .synthetic_loader import load_synthetic
        return load_synthetic(n=n, seed=seed, max_receipts=max_receipts, **extra)
    if name == "sroie":
        if path is None:
            raise ValueError("load_corpus('sroie', ...) requires --path")
        from .sroie_loader import load_sroie
        return load_sroie(path=path, max_receipts=max_receipts, seed=seed, **extra)
    if name == "cord":
        if path is None:
            raise ValueError("load_corpus('cord', ...) requires --path")
        from .cord_loader import load_cord
        return load_cord(path=path, max_receipts=max_receipts, **extra)
    raise ValueError(f"unknown corpus: {name!r}")


__all__ = ["Receipt", "MoneyLine", "load_corpus"]
