# Status — what arrived in this transfer

This branch was reconstructed from a flat dump of the original
`paper3` bundle (working tree + a copy of its `.git/objects/`,
all flattened into one directory by the chat downloader). The
bundle's last commit (`Initial commit: Paper 3 AAD experiment
harness`) was recovered intact and is the source of truth for the
file layout below.

## What's present (recovered from the bundle commit)

```
.gitignore
LICENSE
MIGRATION.md            (empty in the bundle — placeholder)
README.md
__init__.py             (empty package marker)
push-to-github.sh
requirements.txt
core/
  __init__.py
  aad_decoder.py
  identities.py
  keyword_tagger.py
  money_lines.py
  stats.py
  subset_sum.py
scripts/
  __init__.py
  s1_T_distribution.py
  s2_I_coverage.py
  s3_cord_confusion.py
  s4_perturbation_battery.py
  s5_aad_overhead.py
  s6_expectation.py
  s7_aad_train_grid.py
  s8_4system_eval.py
tests/
  __init__.py
  test_smoke.py
vast/
  onstart.sh            (added in this transfer commit)
  run.sh                (added in this transfer commit)
```

## What's missing — `data/` module

The README and every script under `scripts/` import from
`paper3.data` (e.g. `from ..data import load_corpus`,
`from ..data.kie_model_io import StubKIEModel`). **No `data/`
directory was present in the bundle's commit**, so the scripts
cannot run as-is. The README expects:

```
data/
  __init__.py            # exposes load_corpus(name, path, n, seed, ...)
  types.py               # Receipt, MoneyLine dataclasses
  sroie_loader.py        # SROIE Task-3 reader
  cord_loader.py         # CORD-v2 (HuggingFace) reader
  synthetic_loader.py    # smoke-test fixture (no network, no GPU)
  kie_model_io.py        # KIEModelInterface + register_kie_model_factory
```

These modules need to be implemented before the smoke test
(`python -m paper3.tests.test_smoke`) or any individual script
will succeed. Suggested order:

1. `data/types.py` — `Receipt` and `MoneyLine` dataclasses (the
   shape is implied by usage in `core/identities.py`,
   `core/money_lines.py`, and `scripts/s2_I_coverage.py`).
2. `data/synthetic_loader.py` — produces `Receipt` objects with
   subtotal / tax / total / change consistent with I1-I5; this is
   what unblocks the `--corpus synthetic` path that every script
   defaults to.
3. `data/__init__.py` — `load_corpus(name, path=None, n=500, seed=0)`
   dispatcher that routes `synthetic` to step 2 and (eventually)
   `sroie` / `cord` to their loaders.
4. `data/kie_model_io.py` — `KIEModelInterface` Protocol plus
   `register_kie_model_factory(...)`, `get_kie_model()`, and the
   `StubKIEModel` referenced in S5 / S7 / S8.
5. `data/sroie_loader.py` and `data/cord_loader.py` — only needed
   once you have real corpora to evaluate against.

## Running on vast.ai

```bash
# In the on-start script field of a vast.ai instance template,
# or after first SSH:
curl -fsSL https://raw.githubusercontent.com/aiparallel0/triology/claude/transfer-to-github-MHAZT/vast/onstart.sh | bash

# Then, once data/ is implemented:
bash /workspace/paper3/vast/run.sh
```

`onstart.sh` clones the repo into `/workspace/paper3`, installs
`requirements.txt`, and attempts the smoke test (which will fail
loudly until `data/` exists — that's expected). `run.sh` invokes
S1-S6 in sequence on synthetic data once the loader is in place.
