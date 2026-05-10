# Status

End-to-end synthetic experiments run, including the smoke test
(`python -m <pkg>.tests.test_smoke`, ≈3s, 6/6 pass). S7 and S8 are
runnable; with `--adapter donut` they execute against
`naver-clova-ix/donut-base` via the bundled adapter.

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
requirements.gpu.txt      # torch / transformers / pillow / etc. (DONUT, training, downloads)
core/                     # math + verifiers (subset_sum, identities, AAD, stats)
data/                     # corpus loaders + KIE-model interface
  __init__.py             # load_corpus(name, path, n, seed, ...) dispatcher
  download.py             # CORD-v2 from HuggingFace; SROIE unzip helper
  types.py                # Receipt, MoneyLine
  synthetic_loader.py     # smoke-test fixture
  sroie_loader.py         # SROIE Task-3
  cord_loader.py          # CORD-v2 (HF save_to_disk OR *.json)
  kie_model_io.py         # KIEModelInterface, StubKIEModel, registry
adapters/
  donut.py                # DONUT adapter (auto-registers on import)
  README.md
training/
  __init__.py
  donut_sroie.py          # default S7 train_fn (HF Seq2SeqTrainer on SROIE)
scripts/                  # S1-S8 (all runnable; S5/S7/S8 model-aware)
tests/test_smoke.py
vast/
  onstart.sh              # vast.ai on-start script (INSTALL_GPU=1 for full deps)
  run.sh                  # one-call S1-S6, optional --adapter donut
```

## What runs out of the box (numpy only)

S1, S2, S3, S4, S5, S6 with `--corpus synthetic`. The smoke test
covers all six and finishes in about three seconds.

```bash
pip install -r requirements.txt
bash vast/run.sh --n 500
```

## Real-corpus runs

Get the data first (CORD-v2 is automatic; SROIE Task-3 is gated by
registration on the ICDAR challenge site):

```bash
pip install -r requirements.gpu.txt        # for `datasets`
python -m <pkg>.data.download cord  --dest /workspace/datasets/cord-v2
python -m <pkg>.data.download sroie --src ~/Downloads/SROIE.zip \
                                    --dest /workspace/datasets/SROIE_Task3
```

Then:

```bash
python -m <pkg>.scripts.s1_T_distribution \
   --corpus all \
   --sroie /workspace/datasets/SROIE_Task3/test \
   --cord  /workspace/datasets/cord-v2

python -m <pkg>.scripts.s2_I_coverage --corpus all --sroie ... --cord ...
python -m <pkg>.scripts.s3_cord_confusion --corpus cord --path /workspace/datasets/cord-v2
python -m <pkg>.scripts.s4_perturbation_battery --corpus sroie --path /workspace/datasets/SROIE_Task3/test
```

## Model-aware runs (S5 % overhead, S7 training grid, S8 system bars)

Install the GPU stack:

```bash
pip install -r requirements.gpu.txt
```

Run with the DONUT adapter registered:

```bash
# S5 with % of base latency
bash vast/run.sh --adapter donut --n 200

# S7 — 9-cell (init x lambda) grid on SROIE
python -c "import <pkg>.adapters.donut, runpy, sys; \
  sys.argv=['s7','--sroie','/workspace/datasets/SROIE_Task3/test','--epochs','3']; \
  runpy.run_module('<pkg>.scripts.s7_aad_train_grid', run_name='__main__')"

# S8 — system comparison
python -c "import <pkg>.adapters.donut, runpy, sys; \
  sys.argv=['s8','--systems','donut:unconstrained,donut:sigma,donut:aad', \
            '--corpus','sroie','--path','/workspace/datasets/SROIE_Task3/test']; \
  runpy.run_module('<pkg>.scripts.s8_4system_eval', run_name='__main__')"
```

`<pkg>` is `paper3` (recommended) or whatever directory name the repo
was cloned into; the harness derives the package name from the
directory.

## Caveats

- S7's `lambda_struct` currently routes to label-smoothing factor
  (`label_smoothing_factor = 0.1 * lambda_struct`) as a stand-in until
  a proper masked-CE-with-T loss is wired into the trainer. The
  manifest.json next to each checkpoint records this clearly so the
  table in the paper can footnote it.
- S8's `--perturb` flag is a placeholder; image-domain perturbation
  needs either an image corruption pipeline or a text-input adapter.
  The clean-test column of the §VI bars is the only one currently
  reported.
- The training/ module loads heavy deps lazily; `pip install -r
  requirements.gpu.txt` is required before invoking `train_donut_sroie`.
