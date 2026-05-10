"""KIE model adapter interface + factory registry.

Scripts S5, S7, S8 are model-aware. They speak to any model satisfying
the four-method `KIEModelInterface`:

    train(config)                        -> Checkpoint
    predict(image_path, ckpt)            -> Prediction
    decode_total_with_aad(image_path, ckpt, T) -> (text, per_step_logp)
    latency_profile(image_paths, ckpt)   -> {mean_ms, p95_ms, ...}

Adapters register themselves at import time:

    from paper3.data.kie_model_io import register_kie_model_factory
    register_kie_model_factory(lambda: MyAdapter())

Then `get_kie_model()` returns the registered instance. If no adapter
is registered, `StubKIEModel` is returned and the model-aware scripts
either skip the model-dependent rows (S5) or print a helpful message
and exit (S7, S8).

See `paper3.adapters.donut` for a working DONUT adapter.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol, Set, Tuple


# ---------------------------------------------------------------------------
# Data classes shared between adapters and scripts
# ---------------------------------------------------------------------------

@dataclass
class TrainConfig:
    init: str                  # "scratch" | "warm_start" | "freeze_partial"
    lambda_struct: float       # AAD structural-loss weight
    seed: int = 0
    output_dir: str = "results/checkpoints"
    extra: Dict[str, Any] = field(default_factory=dict)

    def cell_name(self) -> str:
        return f"init={self.init}_lambda={self.lambda_struct}"


@dataclass
class Checkpoint:
    path: str
    train_metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Prediction:
    fields: Dict[str, str]                    # e.g. {"total": "36.23", ...}
    raw_text: str = ""
    confidence: Optional[float] = None


# ---------------------------------------------------------------------------
# The protocol every adapter implements
# ---------------------------------------------------------------------------

class KIEModelInterface(Protocol):
    def train(self, config: TrainConfig) -> Checkpoint: ...
    def predict(self, image_path: str, ckpt: Optional[Checkpoint]) -> Prediction: ...
    def decode_total_with_aad(
        self, image_path: str, ckpt: Optional[Checkpoint], T: Set[int]
    ) -> Tuple[str, List[float]]: ...
    def latency_profile(
        self, image_paths: List[str], ckpt: Optional[Checkpoint]
    ) -> Dict[str, float]: ...


# ---------------------------------------------------------------------------
# Stub used when no adapter is registered
# ---------------------------------------------------------------------------

class StubKIEModel:
    """No-op model. Scripts detect this with `isinstance(m, StubKIEModel)`."""

    def train(self, config: TrainConfig) -> Checkpoint:
        raise NotImplementedError(
            "StubKIEModel.train: register a real adapter via "
            "register_kie_model_factory()"
        )

    def predict(self, image_path: str, ckpt: Optional[Checkpoint]) -> Prediction:
        raise NotImplementedError("StubKIEModel.predict")

    def decode_total_with_aad(
        self, image_path: str, ckpt: Optional[Checkpoint], T: Set[int]
    ) -> Tuple[str, List[float]]:
        raise NotImplementedError("StubKIEModel.decode_total_with_aad")

    def latency_profile(
        self, image_paths: List[str], ckpt: Optional[Checkpoint]
    ) -> Dict[str, float]:
        raise NotImplementedError("StubKIEModel.latency_profile")


# ---------------------------------------------------------------------------
# Module-level registry
# ---------------------------------------------------------------------------

_FACTORY: Optional[Callable[[], KIEModelInterface]] = None


def register_kie_model_factory(factory: Callable[[], KIEModelInterface]) -> None:
    """Install the factory that builds the adapter on first use."""
    global _FACTORY
    _FACTORY = factory


def get_kie_model() -> KIEModelInterface:
    """Return the registered adapter, or StubKIEModel if none."""
    if _FACTORY is None:
        return StubKIEModel()
    return _FACTORY()


def clear_kie_model_factory() -> None:
    """Test helper: forget any registered factory."""
    global _FACTORY
    _FACTORY = None
