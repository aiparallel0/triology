# Research plan: non-key channel as a confidence signal for document KIE

**Scope.** Three signals for receipt key-information extraction (KIE), each computed from the *non-key* tokens of the input — the portion of a document a standard KIE pipeline discards after locating the key field. All work inference-only on CPU, inside a Claude Code container. This document specifies formulations, hypotheses, baselines, metrics, decision gates, CPU/parallelization budgets, and reproducibility deliverables.

This is the **regenerated** version of the plan, incorporating decisions from the kick-off Q&A and lessons from the `arith-gating`, `triology`, and `kaggle2` reference repos.

---

## 0. Common protocol

### 0.1 Datasets

Headline scope is **multi-corpus** with experimentally-compatible receipt KIE datasets — same task schema (OCR + bboxes + total field), not necessarily same language.

| Corpus | Split used | n (target) | Role |
|---|---|---|---|
| CORD-v2 | train + validation + test (all splits) | ~1000 | primary; full corpus is in scope. Idea D LM training uses 5-fold CV inside this corpus. |
| SROIE Task-3 | canonical | 347 | second corpus; per-corpus tables. |
| WildReceipt | test | 472 | encoder-only / token-classification evaluation. |
| (optional) MC-OCR, FATURA, or other compatible receipt KIE corpora | — | — | only added if Step 0 dataset-schema verification (§0.8) confirms field availability and bbox quality. |
| **Pooled** | — | **~1819+** | secondary; per-corpus tables remain the headline. |

**Rule from the kick-off**: every additional corpus must be **experimentally compatible** with the existing setup (receipt-style OCR + bboxes + total field). It does **not** need to be linguistically compatible with CORD — Idea D's per-corpus 5-fold KenLM scheme (§3.2) neutralizes the language-mismatch issue that single-LM designs would create.

### 0.2 Models (inference-only)

Primary checkpoints:

| Backbone | Checkpoint | Evaluated on |
|---|---|---|
| Donut | `naver-clova-ix/donut-base-finetuned-cord-v2` | CORD |
| Donut | `philschmid/donut-base-sroie` | SROIE |
| LayoutLMv3 | search HF Hub for a CORD-finetuned variant at scaffold time; fall back to `Theivaprakasham/layoutlmv3-finetuned-wildreceipt` on WildReceipt with a documented cross-architecture limitation (see §0.5 and ASK-7 resolution) | CORD if available, else WildReceipt |

**No fine-tuning, no training of the KIE model.** CPU single-thread inference per receipt; parallelism via process pool over receipts (see §0.7).

**Stop condition**: if any of the above checkpoints is gated, removed, or fails to download, halt and write the failure to `SETUP_REPORT.md`.

### 0.3 Target field

Single field: **total**. Multi-field generalization is out of scope (§9).

Correctness criterion: `|ŷ − y*| ≤ ε` with `ε = 0.02` (integer cents on float-normalized totals; raw-string equality after canonical-form normalization on string-typed corpora).

### 0.4 Statistical machinery

Apply to every measure below.

- Wilson 95% CI for per-cell precision
- Paired McNemar with continuity correction for orthogonality vs. softmax (and pairwise across A/C/D — see §4.2)
- Paired bootstrap, B = 5000, for AURC differences
- Permutation test, B = 10000, for AUROC differences
- Per-corpus tables reported separately from any pooled number
- Leave-one-corpus-out worst-case Wilson lower bound reported alongside pool

**Power analysis (pre-committed; lesson from arith-gating).** At pooled N≈1800 the minimum-detectable-effect at 80% power and α=0.05 is ≈ Δ-AUROC 0.03. At per-corpus N=200 (CORD test only) MDE is ≈ Δ-AUROC 0.075. The kill thresholds in §1.6/§2.6/§3.6 are set above the pooled MDE. Any per-corpus cell below its corpus-MDE is explicitly flagged in the results tables as `[underpowered]` — never reported as a positive headline.

### 0.5 Shared definitions

For a document `x` with input tokens `T = {1, …, n}`, define a **key-region partition**:

```
K(x) := { t ∈ T : dist(bbox(t), bbox(ŷ)) ≤ r · diag(image) }
N(x) := T \ K(x)
```

with default `r = 0.05` (5% of image diagonal). The partition is computed **after** model inference, from the **predicted** key bounding box. `r` is a single hyperparameter shared across all three ideas; sensitivity is tested per idea (`r ∈ {0.02, 0.05, 0.10, 0.20}`).

**Partition circularity — accepted limitation.** Because the partition is defined by the predicted bbox, an incorrect prediction yields an incorrect partition. This is the operational regime: at inference time the system has no gold bbox. The non-key channel signals are tested under this realistic condition. As a **sanity ablation**, every per-idea results table includes a `gold-bbox-partition` row computed on the subset of receipts where the corpus provides a usable gold total bbox (CORD: all; SROIE Task-3: total-line bbox derivable; WildReceipt: per token-class annotation). If the signal vanishes under the gold-bbox partition, the predicted-bbox result is mechanistically the partition-error noise, not the non-key channel — kill the claim.

### 0.6 Caching

All intermediate signals (attention maps, OCR tokens, embeddings, perplexities, fold-ids) are cached to disk after first inference pass under `shared-cache/predictions_<corpus>.parquet`. Every downstream statistic is computed from the cache. The expensive step (KIE inference) runs once per receipt per checkpoint.

**Container-survival rule.** The Claude Code session container is ephemeral. Caches **must be committed to the repository** (parquet is small enough; if it grows past 100 MB use `git lfs`). Re-runs in a fresh container read from the committed cache; the KIE forward pass does not re-execute unless the cache is invalidated by a manifest hash mismatch.

**Manifest.** Each cache file ships with `shared-cache/manifest_<corpus>.json` recording: checkpoint SHA, transformers version, image preprocessing hash, OCR token-list hash, `seed = 42`, fold-id mapping (Idea D). Lesson from `kaggle2/run_5seed_sweep.sh`.

### 0.7 CPU / parallelization budget

Each ablation must complete in **≤ 10 minutes wall-clock** on the available Claude Code CPU cores (assume 2–4 cores). Budget enforcement:

- Detect available cores with `os.cpu_count()`; use `multiprocessing.Pool` over receipts for all per-receipt computations.
- Each per-idea pipeline writes `runtime_<idea>_<corpus>.json` recording wall-clock seconds per stage.
- **Hard fallback**: if the estimated wall-clock for a configuration exceeds 10 minutes (estimate by timing 20 receipts and extrapolating), the run drops to a **200-receipt random subset** of the corpus, with the random selection fixed by `seed = 42`. The fallback is logged in `DECISIONS.md` and labeled `[subset]` in all derived tables.

A `CPU_BUDGET.md` at each session root records the pre-run estimate for every configuration (1019+ receipts × N backbones × 3 measures × ablation cells). Any configuration estimated above 8 CPU-hours total triggers automatic subset fallback before the first inference call.

**Stop condition**: if the total budget exceeds 24 CPU-hours after applying subset fallbacks, halt and write to `SETUP_REPORT.md`.

### 0.8 Dataset-schema verification (pre-flight)

Before any inference, write `dataset_schema_check.md` per corpus by inspecting 5–10 raw annotation files. Confirm: (1) "total" field exists and is named what we expect; (2) bbox coordinates are in pixel or normalized form and we know which; (3) currency / decimal-separator convention; (4) OCR tokens are pre-segmented or need re-segmentation. **Direct lesson from arith-gating's RESEARCH_LOG** (FATURA collapsed from 24 to 13 classes silently; SROIE Task-3 lacks subtotal/tax). Skipping this check has caused weeks of wasted runs in prior projects.

### 0.9 Seed and reproducibility

`seed = 42` everywhere: PyTorch (`torch.manual_seed`), NumPy (`np.random.seed`), Python (`random.seed`), HuggingFace `generation_config.do_sample = False`, KenLM training shuffle (`kenlm` training script `-S` argument), all subset selections, all bootstrap RNGs.

Every HuggingFace model SHA and dataset SHA is pinned in each repo's `environment.md`. Every Python library version pinned in `requirements.txt`. Inline notes call out anything we deliberately leave unpinned (lesson from arith-gating's torch/torchvision: vast.ai images ship matched pairs so over-pinning breaks).

---

## 1. Idea A — Non-key attention entropy

### 1.0 Problem

When a KIE model decodes the total field, it also attends to dozens of other tokens on the receipt — store name, item lines, address, footer. These attention weights are computed at inference and discarded. The question: does the *spread* of those discarded weights, restricted to the non-key partition, tell us when the prediction is unsafe?

### 1.1 Formulation

**Definition A.1.** Let `α ∈ Δ^n` be the decoder's cross-attention distribution over input tokens during generation of the predicted key field (averaged across the predicted-key decoding steps and across heads of the final cross-attention layer). The **non-key attention entropy** is

```
H_N(x) := − Σ_{t ∈ N} ᾱ_t log ᾱ_t,    ᾱ_t := α_t / Σ_{s ∈ N} α_s.
```

Selective rule: `G_A(x; τ) := 𝟙[H_N(x) < τ]` — accept low-entropy (anchored) predictions.

**Cross-architecture aggregation.** Donut tokenizes images into Swin patches; LayoutLMv3 tokenizes OCR text into BPE tokens. The "non-key partition" objects are different (image patches vs. text tokens). Per the ASK-7 resolution:
- **Primary tables**: per-backbone (raw `H_N`).
- **Secondary pooled table**: `H_N_normalized := H_N / log(|N|)`, which lives in [0, 1] for any non-empty partition. Pooled rank-statistics (AUROC, Spearman) computed on `H_N_normalized` are reported with the explicit caveat that the underlying unit differs across architectures.

**Proposition A.1** (decomposition). Full-attention entropy decomposes as

```
H(α) = H_b(w_K, w_N) + w_K · H_K + w_N · H_N,
```

with `w_K = Σ_{t ∈ K} α_t`, `w_N = 1 − w_K`, and `H_b` the binary mass-split entropy. Hence `H_N` is a distinct sub-statistic of `α`, not a function of `H(α)` alone.

**Hypothesis A.1.** At matched coverage, `G_A` strictly improves precision over `G_full` thresholded on `H(α)`.

**Hypothesis A.2.** McNemar test on `(G_A, G_softmax)` yields `b > 0`. Combined rule `G_A ∧ G_softmax` strictly improves precision at matched coverage.

### 1.2 Implementation

**Donut.**
- Set `output_attentions=True` in `generate(...)`.
- Identify total-field token indices via the parsed JSON span. Map the value-span's character offsets back into the decoded token sequence using HuggingFace `decoder_output_offsets` (Mode B advice, documented per repo).
- Extract cross-attention `decoder_attentions[-1]` (final layer); average across the total-span decoding steps and across heads.
- Map encoder positions to image patches via the encoder's patch grid; partition into K/N by patch-centroid distance to predicted total bbox.

**LayoutLMv3.**
- For each token tagged `Total_value`, take its row from `attentions[-1]`, average across heads, then average across the tagged positions.
- Partition by OCR-bbox distance to the predicted-total bbox.

### 1.3 Baselines

| ID | Baseline | Source |
|---|---|---|
| A-B1 | `H(α)` full-attention entropy | Fomicheva et al. 2020 TACL |
| A-B2 | `H_K` key-attention entropy | symmetric ablation |
| A-B3 | `w_N` non-key mass (scalar) | degenerate scalar |
| A-B4 | softmax confidence: `cseq` (Donut), MSP (LayoutLMv3) | standard |
| A-B5 | sigma-verifier (Paper 1) | structural baseline |
| A-B6 | beam-margin (Paper 2) | second-moment baseline |

### 1.4 Metrics

- AUROC(`H_N`; correctness) per backbone × per corpus; plus pooled on `H_N_normalized`.
- AURC vs. A-B1 and A-B4 with paired bootstrap, 95% CI.
- Risk-coverage curve overlaid against A-B1, A-B4.
- Combined-rule precision at matched coverage vs. A-B4 alone; Wilson CI + McNemar.
- McNemar(`G_A`, `G_softmax`) — report `b`, `c`, χ², p-value.

### 1.5 Ablations

- Radius sweep: `r ∈ {0.02, 0.05, 0.10, 0.20}` — required before any AUROC claim.
- Layer choice: final cross-attn vs. mean over last 4 layers.
- Head aggregation: mean / max / entropy-of-head-mean.
- Gold-bbox partition (sanity per §0.5).

### 1.6 Kill criteria

- AUROC(`H_N`) − AUROC(`H(α)`) < **+0.05** at the best radius across all corpora → partition is cosmetic; demote to ablation in the Beam-Margin paper.
- McNemar `b ≈ 0` → orthogonality fails; report as honest null per Beam-Margin precedent.
- Gold-bbox-partition signal vanishes → predicted-bbox result is partition-noise; kill.

### 1.7 Diagnostic disclaimer

Per Jain & Wallace (NAACL 2019) and Wiegreffe & Pinter (EMNLP 2019), attention weights are not faithful explanations of model reasoning. Frame `H_N` as a **diagnostic signal**, never as a mechanistic explanation. Cite both in the paper draft. (Mode B advice; documented per repo.)

### 1.8 CPU feasibility

Attention tensors are inside the KIE forward pass. `H_N` is O(|N|) per receipt — sub-millisecond. Donut forward on a single receipt: ~1–3 s CPU; ~1000 receipts ≈ 20–50 min serial; ~7–15 min on 4-core pool. Within the §0.7 budget.

---

## 2. Idea C — Context-key coupling

### 2.0 Problem

A coffee-shop receipt's surrounding text — vendor name, item descriptions, address — implicitly constrains what the total can be. A predicted total of `$58,400` on a single-coffee receipt is not just unlikely under softmax; it is informationally decoupled from the rest of the page. Can we measure that decoupling directly?

### 2.1 Formulation

**Definition C.1.** Fix a frozen context encoder `φ : x_N ↦ ℝ^{d_φ}` and a frozen key encoder `ψ : y ↦ ℝ^{d_ψ}`. Set `z := φ(x_N)`, `e := ψ(ŷ)`. The **context-key coupling score** is

```
M(x) := ⟨z, e⟩ / (‖z‖ · ‖e‖).
```

Selective rule: `G_C(x; τ) := 𝟙[M(x) > τ]`.

**Three parallel key-encoding variants (ASK-11 resolution).** Each variant produces its own `M(x)`; the strongest is the headline.
- **(a) Key-alone**: `e := ψ("58.40")`. Documented warning: short numeric strings embed near-identically in MiniLM.
- **(b) Key + surrounding ±5 OCR tokens**: `e := ψ("TOTAL $58.40 paid by cash")`. Window size is a hyperparameter (sweep `w ∈ {3, 5, 10}`).
- **(c) Learned MLP scorer**: train a 2-layer MLP on cached `(z, e)` pairs from CORD-train against correctness; 5-fold CV; report AUROC on held-out folds. Light training (CPU, minutes).

**Diagnostic**: Spearman(M_a, numeric-edit-distance(ŷ, gold)) per corpus. If |Spearman| > 0.7, variant (a) is dominated by tokenization artifacts — drop in favor of (b)/(c).

**Proposition C.1** (decoupling lower bound). For any predictor `f` with `ŷ = f(x)`, `I(z ; ψ(ŷ)) ≤ I(z ; m)`. If `ŷ` is generated from the internal state independently of `x_N`, `I(z ; ψ(ŷ)) = 0`.

**Hypothesis C.1.** AUROC(`M`; correctness) > **0.65** on every corpus (raised from 0.55 per ASK-2 resolution).

**Hypothesis C.2.** McNemar(`G_C`, `G_softmax`) yields `b > 0`.

### 2.2 Implementation

**Primary (no training).**
- Context encoder: `sentence-transformers/all-MiniLM-L6-v2` (22 M params).
- Input to `φ`: OCR text concatenated, with K-region tokens **replaced by a single `[MASK]` token** (not deleted — preserves the syntactic frame "TOTAL [MASK] paid by cash"). Lesson from arith-gating: deletion breaks syntactic locality. (Mode B; documented.)
- Three key-encoding variants per §2.1 above.

**Second encoder ablation** (Mode B): re-run with Google Universal Sentence Encoder or a fastText-mean encoder; report side-by-side. MiniLM was trained on natural-language web text, not OCR.

**Secondary vision-path ablation (optional, CPU-capped).**
- DINOv2-base, document image with predicted-total bbox zeroed.
- Hard budget: 10 minutes wall-clock. Falls back to 200-receipt subset per §0.7.

### 2.3 Baselines

| ID | Baseline |
|---|---|
| C-B1 | softmax confidence |
| C-B2 | sigma-verifier |
| C-B3 | beam-margin |
| C-B4 | uniform random (sanity) |
| C-B5 | text-only cosine without OCR mask (deletion variant) |
| C-B6 | MINE / InfoNCE critic (methodology comparison) |

### 2.4 Metrics

- AUROC(`M`; correctness) per corpus and pooled, per variant (a/b/c).
- AURC vs. C-B1 with paired bootstrap.
- Combined rule (`M` AND C-B1) at matched coverage; Wilson + McNemar.
- Spearman(`M`, `cseq`) — redundancy check.
- Spearman(`M_cosine`, `M_MINE`) — estimator consistency.
- Diagnostic Spearman per §2.1.

### 2.5 Ablations

- Encoder choice: MiniLM / USE / fastText-mean / DINOv2 (vision path).
- Masking strategy: `[MASK]` replace (primary) / bbox-zero / OCR-text-delete.
- Variant: (a), (b) with `w ∈ {3, 5, 10}`, (c).
- Radius `r` (shared with §1).
- Gold-bbox partition (sanity per §0.5).

### 2.6 Kill criteria

- AUROC(`M`) < **0.65** on all corpora across all three variants → drop.
- |Spearman(`M`, `cseq`)| > 0.7 across all corpora → redundant; fold into ablation table.
- Cosine vs. InfoNCE Spearman < 0.5 → report as methodological warning, proceed with cosine.
- Diagnostic |Spearman(M_a, numeric-edit-distance)| > 0.7 → variant (a) is artifact-dominated; report (b) or (c) as headline.

### 2.7 CPU feasibility

- MiniLM forward on a 50–200 token sequence: ~10–30 ms CPU; 1000 receipts × 3 variants ≈ 1–2 min on 4-core pool.
- DINOv2-base on a 224×224 image: ~200–500 ms CPU; 1000 receipts ≈ 4–8 min on 4-core pool (within the 10-min cap; subset fallback otherwise).
- No training in the primary path; variant (c) MLP training is seconds on CPU.

---

## 3. Idea D — Non-key perplexity

### 3.0 Problem

Two receipts can have similar predicted totals but very different surrounding text — one a clean restaurant receipt, one a blurry crumpled gas receipt with weird OCR. The wrapping text carries a "this is the kind of document we know" signal that the key-field softmax does not see.

### 3.1 Formulation

**Definition D.1.** Let `p_ref` be a reference language model. For a document `x` with non-key OCR token sequence `w = (w_1, …, w_m)`:

```
S(x) := − (1 / m) · Σ_{i=1}^{m} log p_ref( w_i | w_{<i} ).
```

Selective rule: `G_D(x; τ) := 𝟙[ S(x) < τ ]`.

**Hypothesis D.1.** AUROC(`S`; correctness) − AUROC(`S_full`; correctness) > **+0.05** within each corpus (raised from +0.02 per ASK-2 resolution).

**Hypothesis D.2.** McNemar(`G_D`, `G_softmax`) yields `b > 0`.

### 3.2 Implementation

**Per-corpus 5-fold CV KenLM (primary).** ASK-15 resolution.

For each evaluation corpus independently:
1. Partition the corpus into 5 folds (random, seed=42).
2. For each fold `k`: train KenLM 4-gram with modified Kneser-Ney on the non-key tokens of folds `≠ k`. Score the receipts in fold `k`. Cache (receipt_id, fold_id, S(x)).
3. Final per-corpus `S` values are leakage-free; pool across folds for the corpus's per-receipt table.

This design eliminates the cross-language KenLM problem entirely — each corpus is scored under a model trained on its own distribution. There is no claim of cross-corpus transfer.

**Fallback (drift-detector reframing).** If per-corpus CV exceeds the §0.7 wall-clock budget after subset fallback, the paper reframes Idea D as a *drift detector*: a single KenLM trained on CORD-train scores all receipts across all corpora; AUROC measures cross-corpus separation rather than within-corpus correctness. Different paper claim; documented in `DECISIONS.md` if invoked.

**Token preparation.**
- Lower-case.
- Numeric normalization: digits → `<num>` (ablation: on / off — see §3.5).
- BOS / EOS at OCR line breaks.

**Secondary LM (ablation, CPU-capped).**
- `distilgpt2` frozen; PPL over the non-key token sequence; subset of 200 receipts if 10-min wall-clock cap is exceeded on the full corpus.

### 3.3 Baselines

| ID | Baseline |
|---|---|
| D-B1 | `S_full` — same KenLM scoring all OCR tokens |
| D-B2 | `S_key` — KenLM restricted to key region |
| D-B3 | softmax confidence |
| D-B4 | sigma-verifier |
| D-B5 | beam-margin |
| D-B6 | `S` under `distilgpt2` |

### 3.4 Metrics

- AUROC(`S`; correctness) per corpus.
- AURC vs. D-B1 and D-B3 with paired bootstrap.
- Combined rule (`S` AND softmax) at matched coverage; Wilson + McNemar.
- Spearman(`S_KenLM`, `S_distilgpt2`) — LM-choice robustness.
- **Leakage KS test** (lesson from §3.6): two-sample Kolmogorov–Smirnov on the `S` distribution between training folds and held-out folds. Refuse to publish the per-corpus AUROC if KS p > 0.05 — the test distribution is statistically indistinguishable from training.

### 3.5 Ablations

- N-gram order: `n ∈ {3, 4, 5}`.
- LM family: KenLM vs. distilgpt2.
- Radius `r` (shared with §1, §2).
- Numeric-token normalization on / off.
- Gold-bbox partition (sanity per §0.5).

### 3.6 Kill criteria

- AUROC(`S`) − AUROC(`S_full`) ≤ **+0.05** within every corpus → restriction is cosmetic; fold into ablation table.
- KS p > 0.05 between train-fold and held-out-fold `S` distributions → indistinguishable; refuse to claim a within-corpus AUROC.

### 3.7 CPU feasibility

- KenLM training on ~800 non-key receipts (per fold): ~5–10 s.
- KenLM scoring: microseconds per receipt.
- 5-fold CV per corpus: ~1 min total CPU.
- DistilGPT2 forward on a 100-token sequence: ~50–150 ms; 1000 × ~100 ms ≈ 2 min serial, ~30 s on 4-core pool. Under the 10-min cap.

---

## 4. Umbrella experiment — if any two of {A, C, D} pass

### 4.1 Trigger

Each of A, C, D has a per-corpus AUROC pass criterion (§1.6, §2.6, §3.6). If ≥ 2 ideas pass on ≥ 2 corpora, proceed to umbrella analysis.

### 4.2 Joint statistical analysis

- **Pairwise McNemar on `(G_A, G_C)`, `(G_A, G_D)`, `(G_C, G_D)`** — establishes the orthogonal-channels claim. (Promoted from ADVISE-4 in the prior plan into the headline.)
- Multi-signal logistic ensemble: train logistic regression on cached `(H_N, M, S, cseq)` features against correctness, 5-fold CV pooled across corpora.
- Compare ensemble AURC to single best signal with paired bootstrap.

### 4.3 Combined selective rule

- `G_umbrella := G_A ∧ G_C ∧ G_D ∧ G_softmax`.
- Per-corpus Wilson CI; McNemar against softmax-only.

### 4.4 Headline framing

The unifying claim: the non-key channel of a document carries an independent, exploitable signal for KIE selective prediction beyond what the key-field softmax provides. A, C, D are three modal instantiations (attention, semantic embedding, lexical likelihood).

---

## 5. Sequencing and CPU pre-flight

### 5.1 Pre-flight (before any inference)

| Task | Output | Blocks |
|---|---|---|
| `dataset_schema_check.md` per corpus (§0.8) | one per corpus | everything |
| `CPU_BUDGET.md` at session root (§0.7) | estimate per configuration | everything |
| Confirm checkpoint downloads & SHAs | `environment.md` per repo | everything |
| Smoke test on 3 real CORD receipts | `smoke_test.py` exits 0 with finite scores | everything |

### 5.2 Week 1 — cheap signals first

| Task | Output | Blocks |
|---|---|---|
| Cache KIE inference outputs for all corpora × checkpoints | `shared-cache/predictions_<corpus>.parquet` | A, C, D |
| Compute `H_N` and all A baselines | A metrics table | — |
| Compute `H_full`, `H_K`, `w_N` ablations | A ablation tables | — |

### 5.3 Weeks 2–3

| Task | Output |
|---|---|
| MiniLM embeddings, cosine `M` (variants a/b/c) | C metrics tables |
| Per-corpus 5-fold KenLM training & scoring | D metrics tables |
| Optional: DINOv2, distilGPT2, fastText/USE ablations under CPU caps | ablation tables |

### 5.4 Week 4 — decision gate

- Per-idea kill criteria (§1.6, §2.6, §3.6).
- Umbrella trigger (§4.1) if ≥ 2 pass on ≥ 2 corpora.

### 5.5 Parallelization

- All three ideas share cached KIE outputs from Week 1; downstream computations are independent.
- A, C, D run in parallel processes once the cache is populated.
- Inside each idea, per-receipt computations parallelize via process pool over `os.cpu_count()` cores.

---

## 6. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Predicted-bbox partition is brittle | Sensitivity sweep over `r`; gold-bbox-partition sanity ablation (§0.5); report stability across radii in every per-idea table. |
| Attention is noisy / not faithful (Jain & Wallace) | A-B1 (Fomicheva full-attention) explicit baseline; A only claims a *partition* gain, framed as diagnostic per §1.7. |
| MI estimator instability for C | Cosine primary; MINE/InfoNCE methodology comparison only. |
| KenLM leakage from training folds | 5-fold CV (§3.2); KS-test diagnostic (§3.4); refuse to publish AUROC where KS p > 0.05. |
| Cross-corpus language mismatch | Per-corpus KenLM (§3.2) — no shared LM across corpora. |
| CPU runtime overruns | 10-min wall-clock cap per ablation with 200-receipt subset fallback (§0.7). |
| Under-powered claims (lesson from arith-gating) | Pre-committed power analysis in §0.4; per-cell `[underpowered]` flagging. |
| Dataset schema surprises (lesson from arith-gating) | Pre-flight `dataset_schema_check.md` per corpus (§0.8). |
| Container reset destroys caches | Caches committed to repo with manifest (§0.6). |

---

## 7. Reproducibility deliverables (per repo)

Direct adoption of patterns from `arith-gating`, `kaggle2`, `triology`:

- **Seed-fixed inference script**, single-thread baseline + process-pool variant.
- **`shared-cache/predictions_<corpus>.parquet`** committed to repo with `manifest_<corpus>.json`.
- **One CSV per metric × per corpus** in `results/`.
- **Bootstrap and permutation null distributions** stored as `.npy`.
- **Paper template** `paper/main.tex` with `\PH{key}` placeholders + `paper/fill_tex.py` that reads `results/*.json` and emits `paper/main_filled.tex`. (Direct port of arith-gating's pattern.)
- **`RESEARCH_LOG.md`** documenting dataset gotchas, framing pivots, dead-end experiments, power-analysis discoveries — updated incrementally as the project runs. Modeled on arith-gating's RESEARCH_LOG.
- **`Makefile`** with phase-targets (`make smoke`, `make cache`, `make signals`, `make stats`, `make paper`, `make check`). Each phase reads JSON/parquet from the prior phase. Modeled on arith-gating + kaggle2.
- **`MANIFEST.json` per run** under `runs/<timestamp>/` capturing config snapshot + artifact SHA-256s. Modeled on kaggle2.
- **`environment.md`** with Python version, OS, model SHAs, library pins, seed.
- **`requirements.txt`** with inline rationale for any deliberately unpinned dep.

---

## 8. Cloud-code execution plan

### 8.1 Repository layout

| Repo | Idea | Auxiliary file |
|---|---|---|
| `non-key-attention` | A | `non-key-attention.md` |
| `non-key-coupling` | C | `non-key-coupling.md` |
| `non-key-perplexity` | D | `non-key-perplexity.md` |

Each repo contains its idea-specific auxiliary file, this mega plan, a `references/` folder for the two example papers (Sigma-Verifier, Beam-Margin) for Step 8, scaffolding from §7, and a `DECISIONS.md` log.

### 8.2 Shared cache (per repo)

Each repo carries its own `shared-cache/predictions_<corpus>.parquet` rather than depending on a fourth utility repo. The KIE inference is the only "shared" step; running it three times (once per repo) is cheap relative to the rest. This trades a small re-inference cost for full repo self-containment, which simplifies the Step 1 scaffold session.

If session-bootstrap time becomes a bottleneck, a fourth `non-key-cache` repo can be introduced — recorded as a future Mode B option in DECISIONS.

### 8.3 Environment (per repo)

- `requirements.txt` — pinned Python libraries.
- `environment.md` — Python version, OS, model checkpoint SHAs.
- `smoke_test.py` — fast end-to-end check on 3 real CORD receipts; must print finite, non-NaN scores within 5 min CPU.

Libraries per idea:

- all: `transformers`, `pandas`, `numpy`, `scipy`, `matplotlib`, `pillow`, `pyarrow`, `datasets`
- A: nothing extra
- C: `sentence-transformers`; optional `torch` for DINOv2; optional `fasttext` for the second-encoder ablation
- D: `kenlm`; optional `transformers` for the distilGPT2 path

### 8.4 Output schemas (per repo)

For each idea × corpus pair:

- `results/scores_<idea>_<corpus>.csv` — per receipt: `receipt_id, fold_id, ground_truth, prediction, correct, idea_score, baseline_1, baseline_2, …`
- `results/stats_<idea>_<corpus>.json` — aggregate: `{auroc, aurc, wilson_lo, wilson_hi, mcnemar_b, mcnemar_c, mcnemar_p, bootstrap_ci, underpowered_flag}`
- `results/risk_coverage_<idea>_<corpus>.csv` — `coverage, precision_idea, precision_baseline_1, …`
- `figures/<idea>_<corpus>_<fig>.pdf`
- `paper/main.tex` (with `\PH{}` placeholders), `paper/refs.bib`, `paper/fill_tex.py`, `paper/main_filled.tex` (generated)

### 8.5 Shared-cache schema (`predictions_<corpus>.parquet`)

| Column | Type | Description |
|---|---|---|
| `receipt_id` | str | unique identifier |
| `fold_id` | int | 0–4, assigned at scaffold time, seed=42 |
| `gold_total` | str/float | ground truth (raw + normalized) |
| `pred_total` | str/float | predicted total |
| `pred_total_bbox` | list[float] | `[x0, y0, x1, y1]` normalized |
| `gold_total_bbox` | list[float] | for §0.5 sanity ablation; null if unavailable |
| `ocr_tokens` | list[str] | OCR text tokens |
| `ocr_bboxes` | list[list[float]] | one bbox per token |
| `cseq` | float | softmax confidence (Donut) |
| `msp` | float | max softmax (LayoutLMv3) |
| `attention_to_inputs` | list[float] | length `n`, averaged over heads and total-span decoding steps |
| `corpus` | str | `cord` / `sroie` / `wildreceipt` / … |
| `backbone` | str | `donut-cord` / `donut-sroie` / `layoutlmv3-*` |

### 8.6 Claude Code prompts (per step)

The user drops the mega + the relevant `<repo>.md` into a fresh Claude Code session and issues these prompts in order.

**Step 4 — Run the experiment.**

```
Read non_key_channel_research_plan.md (mega) and <repo>.md (auxiliary).
Run pre-flight: dataset_schema_check.md per corpus, CPU_BUDGET.md at session root.
Set up the environment per §8.3.
Run inference on all corpora and cache outputs per §8.5.
Compute the idea-specific score and all baselines per §1 / §2 / §3.
Run statistical tests per §0.4.
Write results per §8.4.
Do not write a paper yet.
```

**Step 5 — Render the LaTeX paper.**

```
Read paper/main.tex (template with \PH{} placeholders) and results/.
Run paper/fill_tex.py to populate placeholders from results/*.json.
Generate figures/<idea>_<corpus>_<fig>.pdf via matplotlib.
Confirm paper/main_filled.tex compiles with pdflatex.
```

(Per-idea repo ships `paper/main.tex` already written with placeholders — the prose is in place before experiments run, lesson from arith-gating.)

**Step 6 — Auto-fill placeholders.** Subsumed into Step 5 by the template-first pattern; retained as a separate step only for manual interventions.

**Step 7 — Re-analyze with user prompt.**

```
The user has read the draft and provides this comment: <user input>.
Re-analyze the results in light of the comment.
Revise the Discussion section.
Do not silently change numbers — only the interpretive prose.
```

**Step 8 — Restyle against example papers (style only, no text reuse).**

```
Read references/sigma_verifier.pdf and references/beam_margin.pdf.
Compare to current paper/main_filled.tex.
Restyle prose to match: tight sentences, explicit kill-criterion phrasing, honest
negative results, section ordering. NO PROSE SENTENCES MAY BE COPIED VERBATIM
from the example papers. Restyling means matching sentence tightness and rhetorical
moves, never sentence-level reuse. Preserve every numerical claim verbatim.
```

### 8.7 Decision gate

After Step 4 in each repo, kill criteria in §1.6 / §2.6 / §3.6 determine whether to proceed to Steps 5–8. A failed kill criterion does not block the repo; the failure becomes a documented null result in the paper draft, per the Beam-Margin precedent.

---

## 9. Out of scope

- Multi-field generalization (totals only).
- Multilingual generalization across corpora (each corpus's KenLM is per-corpus).
- Any model fine-tuning of the KIE backbone.
- GPU experiments.
- Paper drafting prior to results (templates are scaffolded but not authored).
- Results interpretation outside Step 7.

---

## 10. Change log vs. prior plan

Decisions locked in the kick-off Q&A:

- **Multi-corpus, experimentally compatible.** CORD all-splits is the anchor; add any compatible receipt KIE dataset. Language need not match — Idea D handles this per-corpus.
- **Kill thresholds raised**: AUROC > 0.65 (C); Δ ≥ +0.05 (A, D).
- **Partition circularity**: accepted; gold-bbox-partition ablation added as sanity.
- **Donut/LayoutLMv3 cross-architecture**: per-backbone primary tables; normalized `H_N/log|N|` pooled secondary.
- **Idea C key-encoding**: three parallel variants (key-alone / key+phrase / MLP).
- **Idea D LM**: per-corpus 5-fold CV KenLM; drift-detector reframing as fallback.
- **DINOv2 / DistilGPT2**: kept as ablations with 10-min CPU cap and subset fallback.
- **Paper template**: arith-gating-style `\PH{}` placeholders + `fill_tex.py`.
- **Step 8 restyling**: match style, no text reuse — written into the per-repo prompt.
- **Cross-idea McNemar tests**: promoted from advise into headline umbrella analysis (§4.2).
- **CPU/parallelization budget**: explicit §0.7; 10-min wall-clock cap; 200-receipt subset fallback; `CPU_BUDGET.md` deliverable.
- **Dataset-schema verification**: explicit pre-flight §0.8 (lesson from arith-gating).
- **Reproducibility deliverables**: per-repo `RESEARCH_LOG.md`, `Makefile`, `MANIFEST.json`, committed `shared-cache/` (lessons from arith-gating + kaggle2).
- **Seed and pinning**: explicit §0.9.
