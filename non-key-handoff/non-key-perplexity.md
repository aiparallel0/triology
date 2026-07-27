# non-key-perplexity (Idea D)

> Repository for Idea D of the umbrella plan: *non-key channel as a confidence signal for document KIE*. CPU-only, runs inside a Claude Code container.

## What this repo tests

Two receipts can have similar predicted totals but very different surrounding text — one a clean restaurant receipt, one a blurry crumpled gas receipt with weird OCR. The wrapping text carries a "this is the kind of document we know" signal that the key-field softmax does not see. This repo tests whether **perplexity restricted to the non-key channel**, under a per-corpus 5-fold KenLM, beats full-text perplexity at flagging unsafe predictions.

## Companion documents

- `non_key_channel_research_plan.md` (mega)
- `references/sigma_verifier.pdf`, `references/beam_margin.pdf` — style references for Step 8 (style only, no text reuse).

## Hypotheses (from mega §3)

- **H1.D** — AUROC(`S`; correctness) − AUROC(`S_full`; correctness) > **+0.05** *within each corpus* (raised from +0.02; per-corpus, not cross-corpus).
- **H2.D** — McNemar (`G_D`, `G_softmax`) yields `b > 0`.

## The measure

```
S(x) := − (1 / m) · Σ_{i=1}^{m} log p_ref(w_i | w_{<i})
```

with `p_ref` a 4-gram KenLM trained on the non-key OCR tokens of the **same corpus's other folds** (5-fold CV, mega §3.2). No single global LM; the per-corpus design eliminates the cross-language confound that an Indonesian-trained KenLM scoring English receipts would produce.

## Pipeline (this repo)

1. **Pre-flight**: `make schema`, `make budget`.
2. **Smoke**: `make smoke` runs `smoke_test.py` on 3 real CORD receipts; trains a toy 4-gram on the other 997, scores the 3; prints finite, non-NaN `S`.
3. **Cache**: read `shared-cache/predictions_<corpus>.parquet` (this repo's own copy; mega §8.2).
4. **5-fold KenLM per corpus**: for each corpus independently, partition into 5 folds (seed=42); for each held-out fold, train KenLM 4-gram + modified Kneser-Ney on the other folds' non-key tokens; score the held-out fold; cache `(receipt_id, fold_id, S(x))`.
5. **Baselines**: `S_full` (same KenLM on all OCR tokens), `S_key` (KenLM on K-region only), softmax, sigma-verifier, beam-margin, distilGPT2-`S` if under CPU cap.
6. **Stats**: per mega §0.4; **KS-test leakage diagnostic** between training-fold and held-out `S` distributions per mega §3.4. Refuse to publish per-corpus AUROC if KS p > 0.05.
7. **Tables/figures**: risk-coverage + `S` histogram split by correct/incorrect, per corpus.
8. **Paper**: `make paper` populates placeholders.
9. Steps 5–8 per mega §8.6 prompts.

**Fallback**: if per-corpus 5-fold CV plus all scoring exceeds the §0.7 wall-clock budget after subset fallback, the paper reframes Idea D as a *drift detector*: single KenLM trained on CORD-train scores all corpora; AUROC reports cross-corpus separation. Documented in `DECISIONS.md` if invoked. (User-approved fallback from setup ASK-15.)

## Files this repo writes

- `results/scores_perplexity_{corpus}.csv` (with `fold_id` column)
- `results/stats_perplexity_{corpus}.json` (includes `ks_train_vs_test_p` per mega §3.4)
- `results/risk_coverage_perplexity_{corpus}.csv`
- `results/runtime_perplexity_{corpus}.json`
- `figures/perplexity_{corpus}_{rc,hist}.pdf`
- `models/kenlm_4gram_{corpus}_fold{0..4}.arpa` and `.binary`
- `shared-cache/predictions_{corpus}.parquet` + `manifest_*.json` (committed)
- `paper/main.tex`, `paper/refs.bib`, `paper/fill_tex.py`, `paper/main_filled.tex`
- `RESEARCH_LOG.md`
- `runs/<timestamp>/MANIFEST.json`

## Kill criteria (from mega §3.6)

- AUROC(`S`) − AUROC(`S_full`) ≤ **+0.05** within every corpus → restriction is cosmetic; fold into ablation, rename the contribution.
- KS-test p > 0.05 between train-fold and held-out-fold `S` distributions → distributions indistinguishable; refuse to claim a within-corpus AUROC (lesson from arith-gating: pre-commit to leakage gates).
- If the drift-detector fallback is invoked, the kill criteria switch to: AUROC for cross-corpus separation < 0.90 → drift-signal too weak; drop.

## Repo-specific implementation notes

- **LM choice.** KenLM 4-gram with modified Kneser-Ney is primary (pure CPU, deterministic, fast). DistilGPT2 PPL on non-key tokens is the ablation comparison (LM-choice robustness via Spearman). DistilGPT2 is CPU-capped at 10 min wall-clock; subset fallback (mega §0.7).
- **Per-corpus 5-fold CV** (ASK-15 resolution). Each corpus has its own KenLM; no shared model; no cross-corpus transfer claim. Fold assignment cached in `shared-cache/predictions_<corpus>.parquet` (column `fold_id`) and pinned to `seed = 42`.
- **N-gram order ablation**: `n ∈ {3, 4, 5}` (Mode B from setup; required before any AUROC claim).
- **Tokenization**: lower-case; digits → `<num>`; BOS/EOS at OCR line breaks.
- **Numeric-normalization ablation**: digits → `<num>` vs raw digits. Required before any AUROC claim — most non-key text is items + prices, so normalization may erase the signal. (Mode B from setup.)
- **Leakage diagnostic**: KS test per mega §3.4 — non-optional; pre-committed gate.

## CPU budget (this idea)

- KenLM training on ~800 non-key receipts (per fold, per corpus): seconds.
- 5-fold CV per corpus × 3 corpora: ~1 min total CPU.
- KenLM scoring: microseconds per receipt; full set in seconds.
- DistilGPT2 forward on a 100-token non-key sequence: ~50–150 ms; 1000 × ~100 ms ≈ 2 min serial, ~30 s on 4-core pool. Under the 10-min cap.
- This is the cheapest of the three ideas; the bottleneck is the KIE inference in step 3, which is shared with A and C and cached.
