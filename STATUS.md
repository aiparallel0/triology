# Status

End-to-end synthetic experiments run, including the smoke test
(`python -m <pkg>.tests.test_smoke`, ≈1s, 6/6 pass).

## Layout

```
.gitignore
LICENSE
MIGRATION.md
README.md
STATUS.md
__init__.py
push-to-github.sh
requirements.txt          # numpy only (S1-S6 on synthetic)
requirements.gpu.txt      # torch / transformers / pillow / etc. (DONUT adapter)
core/
  aad_decoder.py
  identities.py
  keyword_tagger.py
  money_lines.py
  stats.py
  subset_sum.py
data/
  __init__.py             # load_corpus(name, path, n, seed, ...) dispatcher
  types.py                # Receipt, MoneyLine
  synthetic_loader.py     # smoke-test fixture
  sroie_loader.py         # SROIE Task-3 (img/, box/, entities/)
  cord_loader.py          # CORD-v2 (HF save_to_disk or *.json directory)
  kie_model_io.py         # KIEModelInterface, StubKIEModel, registry
adapters/
  README.md
  donut.py                # DONUT (naver-clova-ix/donut-base) adapter
scripts/
  s1_T_distribution.py
  s2_I_coverage.py
  s3_cord_confusion.py
  s4_perturbation_battery.py
  s5_aad_overhead.py
  s6_expectation.py
  s7_aad_train_grid.py
  s8_4system_eval.py
tests/
  test_smoke.py
vast/
  onstart.sh              # vast.ai on-start script
  run.sh                  # one-call run-S1-through-S6
```

## What runs out of the box (numpy only)

S1, S2, S3, S4, S5, S6 with `--corpus synthetic`. The smoke test
covers all six and finishes in about a second.

```bash
pip install -r requirements.txt
bash vast/run.sh --n 500
```

## What needs corpora

- `--corpus sroie --path /data/SROIE_Task3/test` (S1, S2, S4)
- `--corpus cord  --path /data/cord-v2/test`     (S1, S2, S3)

The CORD loader reads either a `datasets.save_to_disk` directory or a
flat `*.json` directory. SROIE expects the canonical
`{img,box,entities}/` triple.

## What needs a model adapter

S5 reports overhead in absolute milliseconds without an adapter. With
one registered, it also reports the **% of base decoder latency**.

S7 (training grid) and S8 (system comparison) require an adapter.

The bundled `paper3.adapters.donut` wraps DONUT. Activate it by
importing the module before invoking a script:

```bash
pip install -r requirements.gpu.txt
bash vast/run.sh --adapter donut --n 500
```

S7's actual training loop is left to the user (pass it via
`TrainConfig.extra["train_fn"]`) — the harness handles seed/init/λ
sweeping and checkpoint-manifest writing, but does not bundle a
DONUT trainer.
