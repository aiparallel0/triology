"""Default DONUT trainer for SROIE total-field extraction.

A `train_fn` callable that fits the contract S7 expects:

    train_donut_sroie(adapter, config) -> dict   # train_metrics

`adapter` is a `DonutAdapter` instance; `config` is a `TrainConfig`
with `init`, `lambda_struct`, `seed`, `output_dir`, and `extra`.

Init mapping:
    "scratch"         : reset model weights to random (rare in practice)
    "warm_start"      : keep pretrained weights, fine-tune all params
    "freeze_partial"  : freeze the vision encoder, fine-tune decoder

Lambda mapping (real masked-CE-with-T, not the previous label-smoothing
stand-in):

    L_total = L_CE + lambda_struct * mean_t[-log P(M_t | y_<t, x)]

where M_t is the AAD reachability mask at decoder step t inside the
`<s_total>...</s_total>` span. See `training.aad_loss` for the math.
The `lambda_struct=0` case reduces to ordinary CE; large lambda pushes
the unconstrained decoder toward never placing mass on infeasible
tokens (so AAD's renormalization becomes a near-identity).

The function expects a SROIE root directory (passed as
`config.extra['sroie_root']`) with the canonical {img,box,entities}/
layout. Targets are formatted as DONUT prompt tags:

    "<s_cord-v2><s_total>16.43</s_total></s>"

This file's heavy imports (torch, transformers, PIL) are all done
inside the function so that importing the module is free.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


def _format_total(cents: int) -> str:
    return f"{cents // 100}.{cents % 100:02d}"


def train_donut_sroie(adapter, config) -> Dict[str, Any]:
    """Fine-tune adapter._model on SROIE with optional AAD structural loss.

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

    from ..data.sroie_loader import load_sroie
    from .aad_loss import (
        aad_structural_loss, build_digit_token_ids, find_total_span,
    )

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
    # Build (image, target, items_cents, tau_cents) tuples
    # ------------------------------------------------------------------
    receipts = load_sroie(str(sroie_path))
    samples: List[Dict[str, Any]] = []
    for r in receipts:
        img_path = r.meta.get("image")
        if not img_path or not os.path.exists(img_path):
            continue
        target = f"<s_cord-v2><s_total>{_format_total(r.gold_total_cents)}</s_total></s>"
        samples.append({
            "image": img_path,
            "target": target,
            "items_cents": r.items_cents(),
            "tau_cents": r.tau_cents(),
        })
    if not samples:
        raise RuntimeError(f"No usable receipts found under {sroie_path}")

    # ------------------------------------------------------------------
    # Model + processor + init mode
    # ------------------------------------------------------------------
    adapter._ensure_loaded(None)
    model = adapter._model
    processor = adapter._processor
    tokenizer = processor.tokenizer

    # Add the special tags if missing. DONUT's base tokenizer doesn't
    # necessarily know `<s_total>` / `</s_total>` etc. — extend.
    special_tags = ["<s_cord-v2>", "<s_total>", "</s_total>"]
    to_add = [t for t in special_tags
              if tokenizer.convert_tokens_to_ids(t) == tokenizer.unk_token_id]
    if to_add:
        tokenizer.add_tokens(to_add, special_tokens=True)
        model.decoder.resize_token_embeddings(len(tokenizer))

    open_total_id = tokenizer.convert_tokens_to_ids("<s_total>")
    close_total_id = tokenizer.convert_tokens_to_ids("</s_total>")
    digit_token_ids, _ = build_digit_token_ids(tokenizer)

    if config.init == "scratch":
        model.apply(lambda m: getattr(m, "reset_parameters", lambda: None)())
    elif config.init == "freeze_partial":
        for p in model.encoder.parameters():
            p.requires_grad = False

    lambda_struct = float(config.lambda_struct)

    # ------------------------------------------------------------------
    # Dataset: pre-tokenize labels + cache total_span + items/tau
    # ------------------------------------------------------------------
    class _SroieDataset(Dataset):
        def __init__(self, samples):
            self.samples = samples
            self._cache = {}

        def __len__(self):
            return len(self.samples)

        def _encode(self, i):
            if i in self._cache:
                return self._cache[i]
            ex = self.samples[i]
            label_ids = tokenizer(
                ex["target"], add_special_tokens=False,
                padding="max_length", truncation=True,
                max_length=adapter.max_length,
                return_tensors="pt",
            ).input_ids[0]
            labels = label_ids.clone()
            labels[labels == tokenizer.pad_token_id] = -100
            start, end = find_total_span(labels, open_total_id, close_total_id)
            self._cache[i] = (labels, start, end)
            return self._cache[i]

        def __getitem__(self, idx):
            ex = self.samples[idx]
            img = Image.open(ex["image"]).convert("RGB")
            pixel = processor(img, return_tensors="pt").pixel_values[0]
            labels, start, end = self._encode(idx)
            return {
                "pixel_values": pixel,
                "labels": labels,
                "items_cents": ex["items_cents"],
                "tau_cents": ex["tau_cents"],
                "total_span_start": start,
                "total_span_end": end,
            }

    ds = _SroieDataset(samples)
    n_train = max(1, int(0.9 * len(ds)))
    train_ds = torch.utils.data.Subset(ds, range(n_train))
    eval_ds = torch.utils.data.Subset(ds, range(n_train, len(ds))) if len(ds) > n_train else None

    def collate(batch):
        out = {
            "pixel_values": torch.stack([b["pixel_values"] for b in batch]),
            "labels": torch.stack([b["labels"] for b in batch]),
            # Non-tensor fields the model.forward() must not see; we pop
            # them out in compute_loss before forwarding.
            "items_cents": [b["items_cents"] for b in batch],
            "tau_cents": [b["tau_cents"] for b in batch],
            "total_spans": [
                (b["total_span_start"], b["total_span_end"]) for b in batch
            ],
        }
        return out

    # ------------------------------------------------------------------
    # Custom Trainer: L = L_CE + lambda * L_struct
    # ------------------------------------------------------------------
    class _AADStructuralTrainer(Seq2SeqTrainer):
        def compute_loss(self, model, inputs, return_outputs=False,
                         num_items_in_batch=None):
            items = inputs.pop("items_cents", None)
            taus = inputs.pop("tau_cents", None)
            spans = inputs.pop("total_spans", None)
            outputs = model(**inputs)
            loss_ce = outputs.loss
            if lambda_struct > 0 and items is not None:
                loss_struct = aad_structural_loss(
                    outputs.logits, inputs["labels"],
                    items, taus, spans,
                    digit_token_ids,
                    close_total_token_id=close_total_id,
                )
                loss = loss_ce + lambda_struct * loss_struct
            else:
                loss = loss_ce
            return (loss, outputs) if return_outputs else loss

    out_dir = os.path.join(config.output_dir, config.cell_name())
    os.makedirs(out_dir, exist_ok=True)

    args = Seq2SeqTrainingArguments(
        output_dir=out_dir,
        num_train_epochs=config.extra.get("epochs", 3),
        per_device_train_batch_size=config.extra.get("batch_size", 2),
        per_device_eval_batch_size=config.extra.get("batch_size", 2),
        learning_rate=config.extra.get("lr", 5e-5),
        weight_decay=0.01,
        logging_steps=20,
        save_strategy="epoch",
        eval_strategy="epoch" if eval_ds is not None else "no",
        seed=config.seed,
        predict_with_generate=False,
        report_to=[],
        dataloader_num_workers=0,
        remove_unused_columns=False,  # keep items_cents etc. on the batch
    )

    trainer = _AADStructuralTrainer(
        model=model,
        args=args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        tokenizer=tokenizer,
        data_collator=collate,
    )

    train_out = trainer.train()
    eval_out = trainer.evaluate() if eval_ds is not None else {}

    trainer.save_model(out_dir)
    processor.save_pretrained(out_dir)

    return {
        "n_train": n_train,
        "n_eval":  max(0, len(ds) - n_train),
        "train_loss": float(train_out.training_loss),
        "eval_loss":  float(eval_out.get("eval_loss", float("nan"))),
        "lambda_struct": lambda_struct,
        "loss_term": (
            "L_CE + lambda * L_struct(masked-CE-with-T)"
            if lambda_struct > 0 else "L_CE (lambda=0)"
        ),
        "init": config.init,
        "epochs": int(args.num_train_epochs),
    }
