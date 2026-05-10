"""DONUT (Document Understanding Transformer) adapter.

Wraps `naver-clova-ix/donut-base` (or any DONUT-style
VisionEncoderDecoderModel) behind `KIEModelInterface`. The adapter is
deliberately lightweight: training is a thin call into HuggingFace's
`Seq2SeqTrainer`, and `decode_total_with_aad` runs the model's normal
generation loop with a custom logits processor that zeros logits for
tokens whose prefix completion does not lie in the reachability set T.

This module is opt-in. Importing it registers a factory that will
build the adapter on first use of `get_kie_model()`. To use:

    import paper3.adapters.donut    # registers the factory

The heavy imports (`torch`, `transformers`) happen lazily inside the
factory so that just importing this module does not require GPUs or
Hugging Face installations.

Environment:
    DONUT_MODEL_ID    HuggingFace model id, default 'naver-clova-ix/donut-base'
    DONUT_DEVICE      'cuda', 'cpu', or 'auto' (default 'auto')
    DONUT_MAX_LENGTH  decoder max length (default 64)

`train` defers the actual fine-tuning to a user-provided callable
configured via `extra["train_fn"]` in `TrainConfig`, so that we don't
ship a full training loop. The S7 grid driver invokes this once per
cell of the (init × λ_struct) ablation.
"""
from __future__ import annotations
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from ..core.aad_decoder import build_mask, EOS, DEFAULT_VOCAB
from ..data.kie_model_io import (
    KIEModelInterface, TrainConfig, Checkpoint, Prediction,
    register_kie_model_factory,
)


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


class DonutAdapter:
    """Minimal DONUT wrapper. Heavy deps imported lazily."""

    def __init__(
        self,
        model_id: Optional[str] = None,
        device: Optional[str] = None,
        max_length: Optional[int] = None,
    ):
        self.model_id = model_id or _env("DONUT_MODEL_ID",
                                         "naver-clova-ix/donut-base")
        self.device = device or _env("DONUT_DEVICE", "auto")
        self.max_length = int(max_length or _env("DONUT_MAX_LENGTH", "64"))
        self._processor = None
        self._model = None

    # ------------------------------------------------------------------
    # Lazy model loading
    # ------------------------------------------------------------------

    def _ensure_loaded(self, ckpt: Optional[Checkpoint]) -> None:
        if self._model is not None and self._processor is not None:
            return
        try:
            from transformers import (  # type: ignore
                DonutProcessor, VisionEncoderDecoderModel,
            )
            import torch  # type: ignore
            from PIL import Image  # type: ignore  # noqa: F401
        except ImportError as e:
            raise ImportError(
                "DONUT adapter requires `transformers`, `torch`, "
                "`pillow`, and `sentencepiece`. Install with: "
                "pip install transformers torch pillow sentencepiece"
            ) from e
        source = ckpt.path if (ckpt and ckpt.path and os.path.exists(ckpt.path)) else self.model_id
        self._processor = DonutProcessor.from_pretrained(source)
        self._model = VisionEncoderDecoderModel.from_pretrained(source)
        if self.device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model.to(self.device)
        self._model.eval()
        self._torch = torch

    # ------------------------------------------------------------------
    # KIEModelInterface
    # ------------------------------------------------------------------

    def train(self, config: TrainConfig) -> Checkpoint:
        """Defer training to a user-supplied callable.

        S7 expects to run 9 cells of the (init × λ_struct) grid. Each
        cell's training loop differs by initialization strategy and
        loss weighting; we don't hard-code one. Pass a callable as
        `config.extra["train_fn"]` with signature

            train_fn(adapter, config) -> dict   # train_metrics

        and a `train_fn_output_path` key controlling where to save.
        Returns a Checkpoint pointing at the saved directory.
        """
        train_fn: Optional[Callable[..., Dict[str, Any]]] = (
            config.extra.get("train_fn") if config.extra else None
        )
        if train_fn is None:
            raise NotImplementedError(
                "DonutAdapter.train: pass a callable as "
                "config.extra['train_fn'] to drive the actual training "
                "loop. The adapter intentionally does not bundle one."
            )
        out_dir = os.path.join(config.output_dir, config.cell_name())
        os.makedirs(out_dir, exist_ok=True)
        metrics = train_fn(self, config) or {}
        # Persist a manifest so S8 can pick this checkpoint up later.
        manifest = {
            "cell": config.cell_name(),
            "init": config.init,
            "lambda_struct": config.lambda_struct,
            "seed": config.seed,
            "metrics": metrics,
        }
        with open(os.path.join(out_dir, "manifest.json"), "w") as fh:
            json.dump(manifest, fh, indent=2)
        return Checkpoint(path=out_dir, train_metrics=metrics)

    def predict(self, image_path: str, ckpt: Optional[Checkpoint]) -> Prediction:
        self._ensure_loaded(ckpt)
        from PIL import Image  # type: ignore
        img = Image.open(image_path).convert("RGB")
        inputs = self._processor(img, return_tensors="pt").pixel_values.to(self.device)
        prompt = "<s_cord-v2>"
        decoder_input_ids = self._processor.tokenizer(
            prompt, add_special_tokens=False, return_tensors="pt"
        ).input_ids.to(self.device)
        with self._torch.no_grad():
            out = self._model.generate(
                inputs, decoder_input_ids=decoder_input_ids,
                max_length=self.max_length,
                pad_token_id=self._processor.tokenizer.pad_token_id,
                eos_token_id=self._processor.tokenizer.eos_token_id,
                use_cache=True,
            )
        text = self._processor.batch_decode(out, skip_special_tokens=True)[0]
        fields = self._parse_donut_output(text)
        return Prediction(fields=fields, raw_text=text)

    def decode_total_with_aad(
        self, image_path: str, ckpt: Optional[Checkpoint], T: Set[int]
    ) -> Tuple[str, List[float]]:
        """Decode the `total` field constrained to T using AAD masking.

        Generates one token at a time, applying `build_mask(prefix, T)`
        at the digit/decimal vocabulary and renormalizing logits.
        """
        self._ensure_loaded(ckpt)
        from PIL import Image  # type: ignore
        img = Image.open(image_path).convert("RGB")
        pixel_values = self._processor(img, return_tensors="pt").pixel_values.to(self.device)
        torch = self._torch
        tok = self._processor.tokenizer
        # Token ids for digits, '.', and EOS in the DONUT vocabulary.
        token_ids = {sym: tok.convert_tokens_to_ids(sym) for sym in DEFAULT_VOCAB if sym != EOS}
        eos_id = tok.eos_token_id
        token_ids[EOS] = eos_id
        valid_ids = [v for v in token_ids.values() if v is not None and v >= 0]

        # Encoder once
        with torch.no_grad():
            enc_out = self._model.get_encoder()(pixel_values=pixel_values)
        prefix_ids = tok(
            "<s_cord-v2><s_total>", add_special_tokens=False, return_tensors="pt"
        ).input_ids.to(self.device)

        prefix_str = ""
        log_probs: List[float] = []
        for _ in range(self.max_length):
            with torch.no_grad():
                step_out = self._model(
                    encoder_outputs=enc_out, decoder_input_ids=prefix_ids,
                )
            logits = step_out.logits[0, -1, :]  # [vocab]
            mask_syms = build_mask(prefix_str, T)
            mask = torch.full_like(logits, float("-inf"))
            for sym in mask_syms:
                tid = token_ids.get(sym)
                if tid is None or tid < 0:
                    continue
                mask[tid] = 0.0
            # Restrict logits to feasible-and-known tokens
            for tid in valid_ids:
                if mask[tid].item() == float("-inf") and tid not in [token_ids[s] for s in mask_syms if token_ids.get(s) is not None]:
                    pass  # already -inf
            adj = logits + mask
            if torch.all(torch.isinf(adj)):
                # Mask empty: abstain to unconstrained
                adj = logits
            probs = torch.softmax(adj, dim=-1)
            top = torch.argmax(probs).item()
            log_probs.append(float(torch.log(probs[top]).item()))
            tok_str = tok.decode([top]).strip()
            if top == eos_id or tok_str == "":
                break
            prefix_str += tok_str
            prefix_ids = torch.cat([prefix_ids, torch.tensor([[top]], device=self.device)], dim=1)
        return prefix_str, log_probs

    def latency_profile(
        self, image_paths: List[str], ckpt: Optional[Checkpoint]
    ) -> Dict[str, float]:
        """Measure base-decoder latency on a sample of images.

        If image_paths is empty, runs on a single dummy white image so
        callers can still get a number for the % overhead column.
        """
        self._ensure_loaded(ckpt)
        from PIL import Image  # type: ignore
        torch = self._torch
        if not image_paths:
            samples = [Image.new("RGB", (1280, 960), "white")]
        else:
            samples = [Image.open(p).convert("RGB") for p in image_paths[:50]]
        latencies_ms: List[float] = []
        prompt = "<s_cord-v2>"
        decoder_input_ids = self._processor.tokenizer(
            prompt, add_special_tokens=False, return_tensors="pt"
        ).input_ids.to(self.device)
        for img in samples:
            pix = self._processor(img, return_tensors="pt").pixel_values.to(self.device)
            t0 = time.perf_counter()
            with torch.no_grad():
                _ = self._model.generate(
                    pix, decoder_input_ids=decoder_input_ids,
                    max_length=self.max_length,
                    pad_token_id=self._processor.tokenizer.pad_token_id,
                    eos_token_id=self._processor.tokenizer.eos_token_id,
                    use_cache=True,
                )
            latencies_ms.append((time.perf_counter() - t0) * 1000.0)
        latencies_ms.sort()
        n = len(latencies_ms)
        return {
            "n":      float(n),
            "mean_ms": sum(latencies_ms) / n,
            "p50_ms": latencies_ms[n // 2],
            "p95_ms": latencies_ms[min(n - 1, int(n * 0.95))],
            "max_ms": latencies_ms[-1],
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_donut_output(text: str) -> Dict[str, str]:
        """Extract <s_field>value</s_field> spans from DONUT's output."""
        import re
        out: Dict[str, str] = {}
        for m in re.finditer(r"<s_([a-z_]+)>(.*?)</s_\1>", text, re.S):
            out[m.group(1)] = m.group(2).strip()
        return out


def register() -> None:
    """Install the DONUT factory. Called automatically on import."""
    register_kie_model_factory(lambda: DonutAdapter())


# Auto-register on import. Call clear_kie_model_factory() to undo.
register()
