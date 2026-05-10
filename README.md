# `paper3/` — experiment harness for the IJDAR Arithmetic-Aligned Decoding paper

This package fills the `\PENDING{}` placeholders in the Paper 3 draft
and underwrites Sections IV through VIII with reproducible numbers.
It is the **data and evaluation layer** that sits on top of:

- the SROIE Task-3 and CORD-v2 receipt corpora (real receipts), and
- any off-the-shelf KIE model exposed through a small adapter
  (DONUT, LayoutLMv3, or similar — see *Plugging in a KIE model* below).

Scripts default to a synthetic-data smoke-test fixture so the entire
harness runs end-to-end without a network or a GPU. Real-corpus runs
swap in `--corpus sroie --path …` or `--corpus cord --path …` once
the data is available locally.

## First-time push to GitHub

If you just unzipped this bundle and want to publish it:

```bash
# Easiest path (requires `gh` CLI, https://cli.github.com):
chmod +x push-to-github.sh
./push-to-github.sh paper3-aad-harness --private

# Or follow MIGRATION.md for the manual `git push` / web-UI paths.
```

The bundle ships with a prepared single-commit git history; you don't
need to `git init` or stage anything yourself.

## Layout

```
paper3/
├── data/
│   ├── types.py             Receipt + MoneyLine dataclasses
│   ├── sroie_loader.py      SROIE Task-3 (img/ + box/ + entities/)
│   ├── cord_loader.py       CORD-v2 (HuggingFace gt_parse / valid_line)
│   ├── synthetic_loader.py  smoke-test fixture (extends Paper 1)
│   ├── kie_model_io.py      KIEModelInterface + adapter registration
│   └── __init__.py          load_corpus(name, path, ...) dispatcher
│
├── core/
│   ├── subset_sum.py        T(r) reachability set (Paper 1's verifier)
│   ├── keyword_tagger.py    cash/change/subtotal/tax/discount lexicons
│   ├── money_lines.py       regex extractor; D.DD value-from-OCR-line
│   ├── identities.py        I1, I2, I3, I4 (rate=0.06), I5 (D3 stub)
│   ├── aad_decoder.py       T-aware mask, masked softmax, abstain
│   └── stats.py             Wilson 95% CIs, paired bootstrap
│
├── scripts/
│   ├── s1_T_distribution.py            §I/§II/§III  |T| p95
│   ├── s2_I_coverage.py                §IV table (I1-I5 cross-corpus)
│   ├── s3_cord_confusion.py            CORD-v2 digit confusion heatmap
│   ├── s4_perturbation_battery.py      §VI tab:t_shift
│   ├── s5_aad_overhead.py              §VI overhead row (absolute ms)
│   ├── s6_expectation.py               §VII Δ-vs-leakage curve
│   ├── s7_aad_train_grid.py            §VI 3×3 (init × λ_struct) grid
│   └── s8_4system_eval.py              §VI system-comparison bars
│
├── tests/test_smoke.py                 end-to-end synthetic, <60s
├── results/                            JSON + SVG outputs land here
└── README.md
```

## Mapping: scripts → Paper 3 placeholders

| Placeholder                                | Script | Status |
|--------------------------------------------|--------|--------|
| §I/§II/§III  `\PENDING{T-p95}` (3×)        | S1     | smoke-tested; awaits real corpora |
| §IV  cross-corpus availability table       | S2     | smoke-tested; awaits real corpora |
| §II `fig:cord_confusion` heatmap           | S3     | smoke-tested; awaits CORD-v2 |
| §VI `tab:t_shift` (synthetic vs empirical) | S4     | smoke-tested; uses S3 output |
| §VI AAD overhead absolute ms               | S5     | smoke-tested; "% of base" needs adapter |
| §VII Δ over expectations                   | S6     | smoke-tested |
| §VI 3×3 (init × λ_struct) cell grid        | S7     | runnable as dry-run; full run needs adapter |
| §VI system-comparison bars                 | S8     | runnable as skeleton; full run needs adapter |
| §VIII cover-letter venue                   | clerical | one-line edit when venue chosen |

## Running

Smoke-test everything (≈6 s):

```bash
python -m paper3.tests.test_smoke
```

Each script in isolation:

```bash
# Synthetic smoke runs (no real data, no model required)
python -m paper3.scripts.s1_T_distribution --corpus synthetic --n 500
python -m paper3.scripts.s2_I_coverage    --corpus synthetic --n 500
python -m paper3.scripts.s3_cord_confusion --corpus synthetic --n 500 --confusion_rate 0.08
python -m paper3.scripts.s4_perturbation_battery --corpus synthetic --n 2000
python -m paper3.scripts.s5_aad_overhead   --corpus synthetic --n 500
python -m paper3.scripts.s6_expectation    --corpus synthetic --n 200

# Dry-run S7 (no adapter needed):
python -m paper3.scripts.s7_aad_train_grid --sroie /data/SROIE_Task3 --dry_run

# Real-corpus runs (replace paths)
python -m paper3.scripts.s1_T_distribution --corpus all \
    --sroie /data/SROIE_Task3/test --cord /data/cord-v2/test
python -m paper3.scripts.s2_I_coverage    --corpus all \
    --sroie /data/SROIE_Task3/test --cord /data/cord-v2/test
python -m paper3.scripts.s3_cord_confusion --corpus cord --path /data/cord-v2/test
python -m paper3.scripts.s4_perturbation_battery --corpus sroie --path /data/SROIE_Task3/test
```

S1–S6 produce paper-grade numbers as soon as real corpora are
available. S7 and S8 additionally require a registered KIE-model
adapter (see next section).

## Plugging in a KIE model

S5 (the latency-overhead percentage), S7 (training-grid runs), and S8
(system comparison) are model-aware. They consume any KIE model that
satisfies a four-method interface:

```python
# paper3/data/kie_model_io.py
class KIEModelInterface(Protocol):
    def train(self, config: TrainConfig) -> Checkpoint: ...
    def predict(self, image_path: str, ckpt: Checkpoint) -> Prediction: ...
    def decode_total_with_aad(self, image_path: str, ckpt: Checkpoint,
                              T: Set[int]) -> Tuple[str, List[float]]: ...
    def latency_profile(self, image_paths: List[str],
                        ckpt: Checkpoint) -> Dict[str, float]: ...
```

To use a model with the harness:

```python
# in your_adapter.py
from paper3.data.kie_model_io import register_kie_model_factory

class DonutAdapter:
    def train(self, config): ...
    def predict(self, image_path, ckpt): ...
    def decode_total_with_aad(self, image_path, ckpt, T): ...
    def latency_profile(self, image_paths, ckpt): ...

register_kie_model_factory(lambda: DonutAdapter())
```

Off-the-shelf models that fit naturally:

- **DONUT** (`naver-clova-ix/donut-base`) — vision-encoder-decoder
  emitting JSON-with-tags; the total field comes out as a sequence of
  digit/decimal-point tokens that AAD masks directly.
- **LayoutLMv3** (`microsoft/layoutlmv3-base`) — encoder-only with a
  sequence-labeling head; AAD applies to its generative head when
  exposed (or the BIO tag head can be wrapped for a comparable check).
- **Pix2Struct** (`google/pix2struct-base`) — also sequence-to-text on
  document images.

S7 and S8 are intentionally model-agnostic: the same scripts work with
any of the above (or any new model) once an adapter is registered.

## Design notes

**Soundness preserved.** All identities (I1-I5) accept the gold total
100% of the time when available, on every smoke-test run. This is
Paper 1's Proposition 1 extended to the new identities and is checked
by `tests/test_smoke.test_s2_I_coverage`.

**I4 (tax-rate consistency at r=0.06).** Per dashboard D2, I4 is
*available* iff both subtotal and tax keywords are present AND the tax
line equals subtotal × 0.06 (within 2-cent tolerance). Receipts whose
tax rate is not 6% simply do not have I4 fire — they fall back to
I1, I2, I3, I5.

**I5 (digit-validity, D3 still open).** The default rule is the loose
"every digit in the candidate appears in the union of money-line
digit pools". A stricter "position-aligned" rule is provided as
`i5_rule_position_aligned` and selectable via
`--i5_rule position_aligned` on S2. Both are interchangeable
implementations of `I5Rule = Callable[[Receipt, int], bool]`. Once
D3 is locked, the default rule is replaceable without other changes.

**Money in cents, integer-only.** Every value is integer cents end-to-
end. Float comparisons happen only inside the AAD-decoder simulation
(S6) and only for log-probability arithmetic.

**EPS_CENTS = 2.** Same tolerance as Paper 1. Critical for the
"99.99 ≈ 100.00" edge case in the AAD mask.

## Smoke-test reproduction targets

These numbers should remain stable across runs (synthetic, n=500, seed=0):

| Quantity                      | Target          | Source             |
|-------------------------------|-----------------|--------------------|
| I1 availability (sroie_like)  | ~38-44%         | Paper 1 Table II (38.3%) |
| I2 availability (sroie_like)  | ~58-65%         | Paper 1 Table II (62.7%) |
| I3 availability (sroie_like)  | 100%            | Paper 1 Table II (100%)  |
| I3 soundness                  | 100%            | Paper 1 Prop. 1     |
| Single-digit-OCR FAR          | ~9-10%          | Paper 1 Table I (9.44±0.10%) |
| Two-digit-swap FAR            | ~1-2%           | Paper 1 Table I (1.63±0.29%) |
| T-construction p95            | <10 ms          | Paper 1 Table I (3.26 ms) |
| AAD lift at ε=0.10            | ~1.5-1.8×       | Theorem 1           |

If any of these drift outside their range during a smoke run, the
`tests/test_smoke.py` assertions catch it.
