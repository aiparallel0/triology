# Adapters — KIE-model integration

S5/S7/S8 are model-aware. They route through `KIEModelInterface`
(defined in `paper3/data/kie_model_io.py`) so that the same scripts
work with any KIE backbone.

## Available adapters

### DONUT (`paper3.adapters.donut`)

Wraps `naver-clova-ix/donut-base` (or any DONUT-compatible
`VisionEncoderDecoderModel`). Importing the module auto-registers
the factory:

```python
import paper3.adapters.donut    # registers DonutAdapter
```

Heavy dependencies (torch, transformers, pillow, sentencepiece) are
imported lazily — installing them is only required when the adapter
actually runs (`predict`, `decode_total_with_aad`, `latency_profile`,
`train`).

To install:

```bash
pip install -r requirements.gpu.txt
```

Environment variables:

- `DONUT_MODEL_ID`   default `naver-clova-ix/donut-base`
- `DONUT_DEVICE`     default `auto` (uses CUDA if available)
- `DONUT_MAX_LENGTH` default `64`

### Adding a new adapter

Implement the four `KIEModelInterface` methods (`train`, `predict`,
`decode_total_with_aad`, `latency_profile`), then call

```python
from paper3.data.kie_model_io import register_kie_model_factory
register_kie_model_factory(lambda: YourAdapter())
```

at module import time. Drop it under `paper3/adapters/<name>.py`.

## Wiring it up for S5/S7/S8

The model-aware scripts call `get_kie_model()` once at startup. There
is no flag — whichever adapter was registered most recently wins. To
pick an adapter, import it before invoking the script:

```bash
python -c "import paper3.adapters.donut" -m paper3.scripts.s5_aad_overhead --corpus synthetic --n 200
```

or, more practically, add a small `run_with_donut.py` driver:

```python
# run_with_donut.py
import paper3.adapters.donut       # registers
import runpy
runpy.run_module("paper3.scripts.s5_aad_overhead", run_name="__main__")
```
