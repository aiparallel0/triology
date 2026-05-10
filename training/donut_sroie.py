"""Default DONUT trainer for SROIE total-field extraction.

A `train_fn` callable that fits the contract S7 expects:

    train_donut_sroie(adapter, config) -> dict   # train_metrics

`adapter` is a `DonutAdapter` instance; `config` is a `TrainConfig`
with `init`, `lambda_struct`, `seed`, `output_dir`, and `extra`.

Init mapping:
    "scratch"         : reset model weights to random (rare in practice)
    "warm_start"      : keep pretrained weights, fine-tune all params
    "freeze_partial"  : freeze the vision encoder, fine-tune decoder

Lambda mapping:
    Structural loss isn't a single line in HuggingFace's Seq2SeqTrainer,
    so until we ship a proper masked-CE-with-T term we route
    `lambda_struct` to label smoothing as a stand-in (higher lambda →
    more probability mass spread to non-gold tokens, encouraging the
    model not to over-commit). This is documented in S7's output.

The function expects a SROIE root directory (passed as
`config.extra['sroie_root']`) with the canonical {img,box,entities}/
layout. Targets are formatted as DONUT prompt tags:

    "<s_cord-v2><s_total>36.23</s_total></s>"

Returns a dict of training metrics; the adapter's `train()` writes a
manifest.json with these alongside the saved checkpoint.

This file's heavy imports (torch, transformers, PIL) are all done
inside the function so that importing the module is free.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


def train_donut_sroie(adapter, config) -> Dict[str, Any]:
    """Fine-tune adapter._model on SROIE total extraction.

    Side effects:
      * loads the model into adapter._model / ._processor (lazy)
      * writes a fine-tuned checkpoint into config.output_dir/<cell>/
    """
    import torch  # type: ignore
    from torch.utils.data import Dataset  # type: ignore
    from transformers import (  # type: ignore
        Seq2SeqTrainer, Seq2SeqTrainingArguments,
    )
    from PIL import Image  # type: ignore

    sroie_root = (config.extra or {}).get("sroie_root")
    if not sroie_root:
        raise ValueError(
            "train_donut_sroie requires config.extra['sroie_root'] "
            "pointing at a SROIE Task-3 root with img/box/entities/."
        )
    sroie_path = Path(sroie_root)
    img_dir = sroie_path / "img"
    ent_dir = sroie_path / "entities"
    if not img_dir.exists() or not ent_dir.exists():
        raise FileNotFoundError(
            f"SROIE layout missing under {sroie_path}: expected "
            f"{img_dir} and {ent_dir}."
        )

    # ------------------------------------------------------------------
    # Build (image, target) pairs
    # ------------------------------------------------------------------
    pairs: List[Dict[str, str]] = []
    for ent in sorted(ent_dir.glob("*.txt")):
        try:
            obj = json.loads(ent.read_text(encoding="utf-8", errors="replace"))
        except json.JSONDecodeError:
            continue
        total = obj.get("total")
        if not total:
            continue
        # Normalize to "DD.DD"
        total = total.strip().replace(",", "")
        img_path = img_dir / f"{ent.stem}.jpg"
        if not img_path.exists():
            img_path = img_dir / f"{ent.stem}.png"
        if not img_path.exists():
            continue
        target = f"<s_cord-v2><s_total>{total}</s_total></s>"
        pairs.append({"image": str(img_path), "target": target})
    if not pairs:
        raise RuntimeError(f"No usable receipts found under {sroie_path}")

    # ------------------------------------------------------------------
    # Model + processor (warm_start / scratch / freeze_partial)
    # ------------------------------------------------------------------
    adapter._ensure_loaded(None)
    model = adapter._model
    processor = adapter._processor

    if config.init == "scratch":
        # Reset weights — leaves architecture and tokenizer intact.
        model.apply(lambda m: getattr(m, "reset_parameters", lambda: None)())
    elif config.init == "freeze_partial":
        for p in model.encoder.parameters():
            p.requires_grad = False

    # ------------------------------------------------------------------
    # Dataset
    # ------------------------------------------------------------------
    class _SroieDataset(Dataset):
        def __init__(self, pairs):
            self.pairs = pairs

        def __len__(self):
            return len(self.pairs)

        def __getitem__(self, idx):
            ex = self.pairs[idx]
            img = Image.open(ex["image"]).convert("RGB")
            pixel = processor(img, return_tensors="pt").pixel_values[0]
            labels = processor.tokenizer(
                ex["target"], add_special_tokens=False, return_tensors="pt",
                padding="max_length", truncation=True, max_length=adapter.max_length,
            ).input_ids[0]
            labels[labels == processor.tokenizer.pad_token_id] = -100
            return {"pixel_values": pixel, "labels": labels}

    ds = _SroieDataset(pairs)
    n_train = int(0.9 * len(ds))
    train_ds = torch.utils.data.Subset(ds, range(n_train))
    eval_ds = torch.utils.data.Subset(ds, range(n_train, len(ds)))

    out_dir = os.path.join(config.output_dir, config.cell_name())
    os.makedirs(out_dir, exist_ok=True)
    smoothing = max(0.0, min(0.5, 0.1 * float(config.lambda_struct)))

    args = Seq2SeqTrainingArguments(
        output_dir=out_dir,
        num_train_epochs=config.extra.get("epochs", 3),
        per_device_train_batch_size=config.extra.get("batch_size", 2),
        per_device_eval_batch_size=config.extra.get("batch_size", 2),
        learning_rate=config.extra.get("lr", 5e-5),
        weight_decay=0.01,
        logging_steps=20,
        save_strategy="epoch",
        eval_strategy="epoch",
        seed=config.seed,
        label_smoothing_factor=smoothing,
        predict_with_generate=False,
        report_to=[],
        dataloader_num_workers=0,
    )

    trainer = Seq2SeqTrainer(
        model=model,
        args=args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        tokenizer=processor.tokenizer,
    )

    train_out = trainer.train()
    eval_out = trainer.evaluate()

    # Save model + processor for later loading via Checkpoint(path=out_dir)
    trainer.save_model(out_dir)
    processor.save_pretrained(out_dir)

    return {
        "n_train": n_train,
        "n_eval":  len(ds) - n_train,
        "train_loss": float(train_out.training_loss),
        "eval_loss":  float(eval_out.get("eval_loss", float("nan"))),
        "label_smoothing_factor": smoothing,
        "init": config.init,
        "lambda_struct": config.lambda_struct,
        "epochs": int(args.num_train_epochs),
    }
