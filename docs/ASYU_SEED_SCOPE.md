# Paper 1 — ASYU Seed Scope

**Status:** scoping draft. Locks the conference-paper scope; banks the rest for the journal version.

## Decision

**ASYU conference paper:** ~6 pages, IEEE format. Single fixed operating point (v12). Headline is sigma + orthogonality-with-softmax across multiple corpora.

**Journal version (future):** full method/empirical surface including the v13 multi-candidate-tau curve, multi-field sigma, sigma-as-corrector, conformal calibration, DocILE, cross-architecture analysis, and (cross-paper) sigma + beam-margin joint gate.

## Open empirical question (must resolve before locking)

**Does softmax-threshold dominate sigma on labeled-amounts corpora (CORD, WildReceipt) the same way it does on SROIE?**

M (SROIE) showed: softmax @ 21.6% coverage gives 0.947 precision vs sigma's 0.867. MB and MF will tell us whether the same holds on CORD/WildReceipt.

Decision rule once MB + MF land:

- **softmax wins on all 3** => paper's headline is purely orthogonality (sigma intersect softmax). Regime distinction is dropped.
- **sigma wins on CORD/WildReceipt, softmax wins on SROIE** => regime distinction is real. Paper's headline includes both claims.
- **mixed / within-noise** => report what holds, frame conservatively.

Do NOT commit to a headline claim before MB + MF are run.

## Headline numbers (placeholders — fill after MB/MF)

| Corpus | n | sigma_coverage | sigma_precision | softmax_matched_coverage_precision | intersect_n / precision |
|---|---|---|---|---|---|
| CORD-v2 test | 100 | 0.55 | 0.98 | **TBD (MB)** | **TBD** |
| WildReceipt test | 472 | 0.45 | 0.95 | **TBD (MF)** | **TBD** |
| SROIE Task-3 | 347 | 0.12 (v12) | 0.95 | 0.98 @ 14.4% | 15 / 1.000 |

Footer row (latency): DP p99 < 1ms across all corpora.

## Page allocation (6 pages, IEEE)

| Section | Pages |
|---|---|
| 1. Intro + problem statement | 1.0 |
| 2. Related work | 0.5 |
| 3. Method (I3 + cardinality guard + single-tau extractor) | 1.5 |
| 4. Experiments (3-corpus sigma table) | 1.0 |
| 5. Baseline + orthogonality | 1.0 |
| 6. Ablation + latency | 0.5 |
| 7. Conclusion (with journal teasers) | 0.5 |
| **Total** | **6.0** |

## What is IN the ASYU paper

1. I3 subset-sum verifier definition + DP
2. Cardinality guard |S| >= 2
3. Single-tau extractor (v12 final form: TOTAL_LIKE dominance + single tau per category + bare-int reject + reg-pattern reject)
4. 3-corpus sigma table at fixed precision target (0.95)
5. Baseline: softmax-threshold sweep + matched-coverage comparison
6. Orthogonality: sigma vs softmax accept-set overlap, intersect_precision
7. One ablation: cardinality guard kmin=1 vs kmin=2 (G script)
8. DP latency one-liner: p50 ~ 0.005 ms, p99 < 1 ms
9. Brief failure-mode discussion (L script, aggregated)

## What is OUT of ASYU (banked for journal)

1. **Multi-candidate tau (v13)** — method extension. Mentioned as "future work" only.
2. **Precision-coverage curve** via varying tau-candidate cardinality. Journal figure.
3. **DocILE 4th corpus** — unless K v4 lands a clean number (>=0.85 identity-hold at relaxed epsilon=2 units, n>=300). Otherwise journal only.
4. **Multi-field sigma** (joint total + subtotal + tax verification) — journal extension.
5. **Sigma-as-corrector** (replace pi with closest subset+tau when sigma rejects) — journal.
6. **Conformal calibration of sigma threshold** — journal theoretical scaffolding.
7. **Cross-architecture deep dive** — ASYU shows 2 arches (DONUT + LayoutLMv3); journal expands.
8. **Joint sigma + beam-margin** (cross-paper, depends on Paper 2 landing) — journal only.
9. **Full failure-mode taxonomy** with quantitative recoverability ceiling — journal.
10. **Money-count bucket precision analysis** — journal.

## Risk register

| Risk | Severity | Mitigation |
|---|---|---|
| Softmax dominates sigma on all 3 corpora | High | Reframe headline as pure orthogonality story; intersect_precision = 1.0 on SROIE is the anchor result |
| Multi-candidate tau (v13) trades too much precision | Medium | Use v12 (single-tau) for ASYU; journal version frames v13 as the curve |
| DocILE identity-hold rate stays mediocre | Low | Demote DocILE to journal only |
| Failure-mode taxonomy too noisy for headline | Low | Cite L counts in 1 paragraph; full taxonomy goes to journal |
| Reviewer asks for cross-corpus model transfer | Medium | Cite future work; ASYU is in-distribution only |

## Key figures (ASYU paper, ~4 figures)

1. **Figure 1** (intro): receipt with sigma working, schematic of I3 verifier.
2. **Figure 2** (method): cardinality guard ablation — precision vs coverage, kmin=1 vs kmin=2.
3. **Figure 3** (experiments): 3-corpus sigma vs softmax comparison at matched coverage, plus intersect_precision callout.
4. **Figure 4** (analysis): money-count bucket breakdown (G script) — shows where sigma succeeds and where it cannot fire.

## Tentative titles (decide after MB/MF)

- *"Subset-Sum Verification as a Confidence-Orthogonal Selective Predictor for Receipt KIE"*
- *"sigma: A Subset-Sum Witness for KIE Total Predictions"*
- *"Arithmetic Identity Verification for Receipt Total Field Extraction"*

## Fundamental problem statement (working draft)

> *KIE total-field predictions need a precision-gated abstention mechanism for downstream deployment. Existing softmax-confidence thresholds are domain-blind and operate purely on the model's internal probability distribution. We propose sigma, a domain-aware verifier that accepts a predicted total iff it can be witnessed as a subset-sum identity over the receipt's OCR'd amounts plus extracted tax. Across three corpora and two model families, sigma achieves precision >= 0.95 at meaningful coverage and provides confidence-orthogonal evidence: the conjunction sigma intersect softmax yields a perfect-precision joint gate. The DP verifier runs in p99 < 1 ms.*

## Acceptance probability estimate

At ASYU's typical acceptance rate (~50-60% for honest empirical AI papers with clear novelty), this paper at 75-80% completeness should hit 55-65% acceptance probability. The orthogonality finding is the linchpin; if it generalizes across corpora, this is a comfortable accept.

## Critical path to ASYU submission

1. Run MB + MF (this commit). ~5 minutes.
2. Lock the headline based on MB/MF outcome.
3. Draft sections 1-7 in LaTeX over ~3 days.
4. Internal review pass.
5. Submit.
