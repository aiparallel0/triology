# non-key-attention (Idea A)

> Repository for Idea A of the umbrella plan: *non-key channel as a confidence signal for document KIE*. CPU-only, runs inside a Claude Code container.

## What this repo tests

When a KIE model decodes the total field, it also attends to dozens of other tokens on the receipt — store name, item lines, address, footer. These attention weights are computed at inference and discarded. This repo tests whether the **entropy** of those discarded weights, computed over the non-key partition, signals when the prediction is unsafe.

## Companion documents

- `non_key_channel_research_plan.md` (mega) — shared protocol, datasets, statistics, decision gates, CPU/parallelization budget, dataset-schema verification, prompts.
- `references/sigma_verifier.pdf`, `references/beam_margin.pdf` — style references for Step 8 (style only, no text reuse).

## Hypotheses (from mega §1)

- **H1.A** — at matched coverage, `G_A: H_N(x) < τ` strictly improves precision over the rule `G_full: H(α) < τ`. Δ-AUROC ≥ **+0.05** is the kill threshold (raised from +0.02).
- **H2.A** — McNemar (`G_A`, `G_softmax`) yields `b > 0`; combined rule `G_A ∧ G_softmax` strictly improves precision.

## The measure

```
H_N(x) := − Σ_{t ∈ N} ᾱ_t log ᾱ_t,    ᾱ_t := α_t / Σ_{s ∈ N} α_s
```

with `N = T \ K`, the non-key partition defined in mega §0.5 (predicted-bbox primary; gold-bbox sanity ablation per mega §0.5).

For the **cross-backbone pooled secondary table** only:

```
H_N_normalized(x) := H_N(x) / log(|N(x)|)  ∈ [0, 1]
```

reported with explicit caveat that underlying units differ across architectures (Donut: image patches; LayoutLMv3: text tokens). Per-backbone tables on raw `H_N` are the headline (ASK-7 resolution; see mega §1.1).

## Pipeline (this repo)

1. **Pre-flight**: `make schema` writes `dataset_schema_check.md` for each corpus (mega §0.8). `make budget` writes `CPU_BUDGET.md` (mega §0.7).
2. **Smoke**: `make smoke` runs `smoke_test.py` on 3 real CORD receipts; must print finite, non-NaN `H_N` within 5 min CPU.
3. **Cache**: `make cache` runs KIE inference for all corpora × checkpoints; writes `shared-cache/predictions_<corpus>.parquet` with manifest. Commits to repo (mega §0.6 container-survival rule).
4. **Signals**: `make signals` computes `H_N`, `H(α)` (full), `H_K`, `w_N`, `H_N_normalized` per receipt.
5. **Baselines**: `cseq` / MSP, sigma-verifier, beam-margin (read from cache).
6. **Stats**: `make stats` runs the per-corpus + pooled statistics per mega §0.4.
7. **Tables/figures**: `make figures` generates risk-coverage curves and `H_N` histograms.
8. **Paper**: `make paper` populates `paper/main.tex` placeholders from `results/*.json` via `paper/fill_tex.py`.
9. Steps 5–8 per mega §8.6 prompts (paper template, restyling).

`Makefile` is the entry point for every phase; targets are idempotent and skip if their outputs already exist.

## Files this repo writes

- `results/scores_attention_{cord,sroie,wildreceipt,...}.csv`
- `results/stats_attention_{cord,sroie,wildreceipt,...}.json`
- `results/risk_coverage_attention_{cord,sroie,wildreceipt,...}.csv`
- `results/runtime_attention_{cord,sroie,wildreceipt,...}.json` (wall-clock budget tracking)
- `figures/attention_{cord,...}_{rc,hist}.pdf`
- `shared-cache/predictions_{cord,sroie,wildreceipt,...}.parquet` + `manifest_*.json` (committed)
- `paper/main.tex` (with `\PH{}` placeholders, scaffolded at setup time), `paper/refs.bib`, `paper/fill_tex.py`, `paper/main_filled.tex` (generated)
- `RESEARCH_LOG.md` (incremental; dataset gotchas, framing pivots, dead ends)
- `runs/<timestamp>/MANIFEST.json` (kaggle2-style per-run artefact pinning)

## Kill criteria (from mega §1.6)

- AUROC(`H_N`) − AUROC(`H(α)`) < **+0.05** at the best radius across all corpora → partition is cosmetic; demote to ablation in Beam-Margin paper.
- McNemar `b ≈ 0` (`G_A` errors ⊆ `G_softmax` errors) → orthogonality fails; report as honest null.
- Gold-bbox-partition signal vanishes (sanity ablation per mega §0.5) → predicted-bbox result is partition-error noise; kill the claim.

## Repo-specific implementation notes

- **Donut.** Extract `decoder_attentions[-1]` from `generate(..., output_attentions=True)`. Identify the total-value span by parsing the generated JSON and mapping the value-string's character offsets back into the decoded token sequence via HuggingFace `decoder_output_offsets`. Average attention over those steps and over heads of the final cross-attention layer. Document the mapping in `DECISIONS.md` (Mode B advice from setup).
- **LayoutLMv3.** Extract `attentions[-1]` (final self-attention); for each token tagged `Total_value` take its row, average over heads, then average across the tagged positions. Search HF Hub for a CORD-fine-tuned LayoutLMv3 at scaffold time; if none exists, fall back to `Theivaprakasham/layoutlmv3-finetuned-wildreceipt` on WildReceipt only, with the cross-architecture limitation documented in `RESEARCH_LOG.md`.
- **Partition.** Predicted-bbox primary; `K`: tokens whose bounding-box centroid is within `r · diag(image)` of the predicted total bbox, `r = 0.05` default. Sensitivity: `r ∈ {0.02, 0.05, 0.10, 0.20}`. Gold-bbox sanity ablation per mega §0.5.
- **Robustness ablations.** Layer choice (last vs. mean of last 4); head aggregation (mean / max / entropy-of-head-mean).
- **Cross-backbone aggregation.** Per-backbone primary; `H_N_normalized` pooled secondary (per ASK-7 resolution and mega §1.1).
- **Diagnostic framing.** Per Jain & Wallace 2019 / Wiegreffe & Pinter 2019, `H_N` is a diagnostic signal, never a mechanistic explanation. Both papers cited in `paper/refs.bib`. (Mode B advice from setup.)

## CPU budget (this idea)

- Attention tensors are already inside the KIE forward pass.
- `H_N` is O(|N|); sub-millisecond per receipt.
- Donut forward per receipt: ~1–3 s CPU. ~1000 receipts × ~2 s ≈ 20–50 min serial; ~7–15 min on 4-core pool. Well within mega §0.7's 10-min-per-ablation cap when parallelized; falls back to 200-receipt subset if not.
- LayoutLMv3 forward per receipt: ~0.5–1.5 s CPU. Comparable.
