# non-key-coupling (Idea C)

> Repository for Idea C of the umbrella plan: *non-key channel as a confidence signal for document KIE*. CPU-only, runs inside a Claude Code container.

## What this repo tests

A coffee-shop receipt's surrounding text — vendor name, item descriptions, address — implicitly constrains what the total can be. A predicted total of `$58,400` on a single-coffee receipt is not just unlikely under softmax; it is informationally decoupled from the rest of the page. This repo tests whether the **cosine coupling** between a non-key context embedding and the predicted key embedding is a per-receipt confidence signal.

## Companion documents

- `non_key_channel_research_plan.md` (mega)
- `references/sigma_verifier.pdf`, `references/beam_margin.pdf` — style references for Step 8 (style only, no text reuse).

## Hypotheses (from mega §2)

- **H1.C** — AUROC(`M`; correctness) > **0.65** on every corpus (raised from 0.55).
- **H2.C** — McNemar (`G_C`, `G_softmax`) yields `b > 0`; combined rule strictly improves precision.

## The measure

```
M(x) := ⟨z, e⟩ / (‖z‖ · ‖e‖)
```

with `z := φ(x_N)` (context encoder over non-key OCR with K-region tokens replaced by `[MASK]`) and `e := ψ(ŷ)` (key encoder over predicted total).

**Three parallel key-encoding variants** (ASK-11 resolution from setup):

| Variant | Key text passed to `ψ` | Why |
|---|---|---|
| (a) key-alone | `"58.40"` | original plan; documented short-numeric-string warning |
| (b) key + ±w OCR tokens | `"TOTAL $58.40 paid by cash"`, sweep `w ∈ {3, 5, 10}` | adds linguistic anchoring around the numeric |
| (c) learned MLP scorer | (a) embedding → 2-layer MLP trained on cached `(z, e)` pairs against correctness, 5-fold CV | data-driven scoring rule |

The strongest variant is the headline result. Diagnostic: `Spearman(M_a, numeric_edit_distance(ŷ, gold))` per corpus — if `|ρ| > 0.7`, variant (a) is dominated by tokenization artifacts.

## Pipeline (this repo)

1. **Pre-flight**: `make schema`, `make budget`.
2. **Smoke**: `make smoke` runs `smoke_test.py` on 3 real CORD receipts; prints variant-(a) cosine.
3. **Cache**: read `shared-cache/predictions_<corpus>.parquet` (this repo's own copy; mega §8.2).
4. **Signals**: `make signals` computes `M_a`, `M_b` for each `w`, `M_c` (MLP); plus DINOv2 vision-path variant if under CPU cap.
5. **Baselines**: softmax, sigma-verifier, beam-margin, uniform random, deletion-vs-`[MASK]` ablation.
6. **Stats**: per mega §0.4; diagnostic Spearmans per variant.
7. **Tables/figures**: `make figures` generates risk-coverage + `M` histograms per variant.
8. **Paper**: `make paper` populates placeholders.
9. Steps 5–8 per mega §8.6 prompts.

## Files this repo writes

- `results/scores_coupling_{corpus}_{variant}.csv` (variant ∈ {a, b_w3, b_w5, b_w10, c, dinov2})
- `results/stats_coupling_{corpus}_{variant}.json`
- `results/risk_coverage_coupling_{corpus}_{variant}.csv`
- `results/runtime_coupling_{corpus}_{variant}.json`
- `figures/coupling_{corpus}_{variant}_{rc,hist}.pdf`
- `models/mlp_scorer_fold{0..4}.pt` (variant c)
- `shared-cache/predictions_{corpus}.parquet` + `manifest_*.json` (committed)
- `paper/main.tex`, `paper/refs.bib`, `paper/fill_tex.py`, `paper/main_filled.tex`
- `RESEARCH_LOG.md`
- `runs/<timestamp>/MANIFEST.json`

## Kill criteria (from mega §2.6)

- AUROC(`M`) < **0.65** on all corpora across all three variants → drop the idea.
- |Spearman(`M`, `cseq`)| > 0.7 across all corpora → redundant with softmax; fold into ablation.
- Cosine vs. InfoNCE Spearman < 0.5 → estimator instability dominates; report methodological warning, proceed with cosine.
- Diagnostic |Spearman(M_a, numeric-edit-distance)| > 0.7 → variant (a) is artifact-dominated; promote (b) or (c) to headline.
- Gold-bbox-partition signal vanishes (sanity ablation per mega §0.5) → kill.

## Repo-specific implementation notes

- **Primary context encoder**: `sentence-transformers/all-MiniLM-L6-v2` (22 M params, ~10–30 ms per 50–200 token sequence on CPU).
- **Masking strategy**: K-region tokens are **replaced by a single `[MASK]` token**, not deleted. Deletion breaks syntactic locality ("TOTAL" left dangling). Comparison reported as an ablation. (Mode B advice from setup.)
- **Three key-encoding variants** per §2.1 above; (b) sweeps `w ∈ {3, 5, 10}`.
- **Second encoder ablation**: re-run primary path with Google USE or fastText-mean encoder; report side-by-side. MiniLM was trained on natural-language web text, not OCR. (Mode B from setup.)
- **DINOv2 vision-path ablation** (optional, CPU-capped): `dinov2-base` frozen, document image with predicted-total bbox zeroed; key encoder = MiniLM projected via fixed PCA into DINOv2 space. Hard 10-min wall-clock cap; 200-receipt subset fallback (mega §0.7). Drop entirely if even the subset exceeds the cap. (Mode B from setup.)
- **Methodological comparison (optional)**: 2-layer MLP critic trained on cached `(z, e)` pairs from CORD-train; estimate InfoNCE lower bound; report Spearman vs. cosine.

## CPU budget (this idea)

- MiniLM forward on a 50–200 token sequence: ~10–30 ms CPU.
- 1000 receipts × 3 primary variants × 30 ms ≈ 1–2 min on 4-core pool.
- DINOv2-base on a 224×224 image: ~200–500 ms CPU. 1000 receipts × 350 ms ≈ 6 min on 4-core pool; under the 10-min cap; subset fallback if not.
- MLP scorer (variant c) training: seconds per fold on CPU.
- Embeddings cached to `shared-cache/embeddings_<corpus>.parquet` after first pass; downstream stats are read-only.
