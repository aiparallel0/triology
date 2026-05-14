# Paper 1 (ASYU seed) — Section Outline with Number Sources

Every numerical claim has a source JSON. Run `python scripts/smoke/paper_table.py` to refresh all numbers in one go.

## Section 1. Introduction (~1.0 page)

- Problem: KIE total predictions need precision-gated abstention for downstream deployment.
- Limitation of confidence-only abstention: domain-blind, doesn't exploit arithmetic redundancy.
- Proposed: $\sigma$ — subset-sum verifier with cardinality guard.
- Contribution claims (numbered):
  1. $\sigma$ Pareto-dominates softmax-thresholding on CORD.
  2. $\sigma$-only accept-set is perfectly correct on CORD (22/22, Wilson CI [0.85, 1.00]).
  3. $\sigma \cap$ softmax achieves 100% precision on the joint-accept set across all corpora.
  4. $\sigma$ is precision-robust to 40% synthetic label noise (≥0.93 precision).
  5. DP runs at p99 < 1 ms; sigma overhead < 1% of DONUT inference time.

## Section 2. Related Work (~0.5 page)

- Selective prediction / abstention methods (Geifman & El-Yaniv; Hendrycks).
- KIE confidence / OOD detection (relevant DONUT/LayoutLMv3 papers).
- Arithmetic verification (CV literature, financial OCR).
- Cost-sensitive evaluation.

## Section 3. Method (~1.5 pages)

### 3.1 Receipt arithmetic identity
- Definition: $\sum_i \text{item}_i + \tau = \pi$.
- $\tau$ = tax + service + ... (signed).
- I3 reformulation: $\exists S \subseteq \text{money\_lines}, \sum S + \tau = \pi$.

### 3.2 The $\sigma$ verifier
- DP for I3 (0/1 knapsack-style, sum-tracking).
- Cardinality guard $|S| \geq 2$ when $|\tau| \leq \epsilon$.
- $\epsilon$-tolerance for OCR rounding.
- Extractor: $\tau$ from tax/service/discount keyword lines; money_lines from per-line OCR.

### 3.3 Multi-candidate $\tau$ (briefly; defer details to journal)
- v13: collect plausible $\tau$ candidates; $\sigma$ accepts iff $\pi$ in union of $T(\text{money}, \tau_k)$.
- Pareto trade-off: increases coverage at cost of some precision.

## Section 4. Experimental setup (~0.5 page)

- 3 corpora: CORD-v2 (n=100, DONUT generative), SROIE Task-3 (n=347, DONUT generative), WildReceipt (n=472, LayoutLMv3 encoder-only).
- Source models: `philschmid/donut-base-sroie`, `naver-clova-ix/donut-base-finetuned-cord-v2`, `Theivaprakasham/layoutlmv3-finetuned-wildreceipt`.
- $\epsilon = 0.02$ (defended in Section 5 via V's tolerance sweep).
- Implementation: 0/1-knapsack DP in pure Python; no model retraining.

## Section 5. Results (~2.0 pages)

### 5.1 Headline Table 1 — per-corpus comparison
- Source: PAPER_TABLE.md T1
- Columns: corpus, n, $\sigma$ cov, $\sigma$ prec [95% CI], softmax prec [95% CI], $\sigma \cap$ softmax n / prec [95% CI], $\sigma$-only prec [95% CI]
- Key callout: CORD $\sigma$-only **22/22 = 1.0 [0.85, 1.00]** (perfectly orthogonal evidence).

### 5.2 Pareto frontier (Figure 1)
- Source: PAPER_TABLE.md T6 (S_pareto.json)
- CORD subplot: $\sigma$ alone on the front; $\sigma \cap$ softmax = 1.0 prec @ 13% cov; $\sigma \cup$ softmax = 0.97 prec @ 74% cov.
- SROIE subplot: softmax dominates at high prec; $\sigma \cup$ softmax expands high-coverage region.

### 5.3 Failure-mode taxonomy (Table 2)
- Source: PAPER_TABLE.md T4 (L_sroie + L_cord)
- SROIE: dominant categories are tau_too_negative + far_miss.
- CORD: dominant categories are pred_wrong (model error, not $\sigma$'s fault).
- Regime interpretation: CORD failures are tolerance/rounding-driven; SROIE failures are extractor/OCR-driven.

## Section 6. Ablation & robustness (~0.5 page)

### 6.1 Cardinality guard ablation (Table 3)
- Source: PAPER_TABLE.md T3 (G's kmin=1 vs kmin=2).
- kmin=2 trades coverage for precision; corpus-dependent value.

### 6.2 Tolerance sweep (Figure 2)
- Source: PAPER_TABLE.md T7 (V's $\epsilon$ curve on CORD).
- Defends $\epsilon = 0.02$ as a sweet spot.

### 6.3 Noise robustness (Figure 3 or Table 4)
- Source: PAPER_TABLE.md T5 (Q v2, 10 seeds).
- $\sigma$ precision stays ≥0.93 even at 40% noise; coverage degrades 4×.

## Section 7. Cost & latency (~0.4 page)

- DP latency: T2 (G) — p99 < 1 ms.
- $\sigma$ overhead vs DONUT: `time_budget.json` — $\sigma$ adds <1% to inference cost.
- Honest discussion: N's finding (accept-all wins on net-F1 at $\lambda = 0$); $\sigma$ is for cost-asymmetric regimes.

## Section 8. Discussion (~0.3 page)

- Regime taxonomy: labeled-amounts vs OCR-derived.
- When $\sigma$ helps: high-precision deployment, financial KIE, compliance, audit.
- Limitations: requires extracted money lines + $\tau$; performance bounded by extractor quality on OCR corpora.
- Future work (journal version): multi-field $\sigma$, $\sigma$-as-corrector, conformal calibration of $\sigma$ threshold, joint $\sigma$ + beam-margin gate.

## Section 9. Conclusion (~0.2 page)

- Recap headline: $\sigma$ as confidence-orthogonal verifier.
- Practical claim: <1% overhead, deployable today.
- Tease journal extensions.

## Figures (proposed)

1. Pareto frontier: CORD + SROIE in two subplots (from S_pareto.json).
2. $\sigma$ precision vs $\epsilon$ on CORD (from V_tolerance_sweep_cord.json).
3. $\sigma$ precision vs noise rate on CORD (from Q_money_noise_cord.json).
4. Failure-mode bar chart: SROIE vs CORD (from L + L_cord).

## Tables (proposed)

1. Headline per-corpus (Section 5.1).
2. Failure-mode taxonomy counts (Section 5.3).
3. Cardinality guard ablation (Section 6.1).
4. Wilson CIs for key rates (footnote or table caption).

## Reproducibility commitment

- Code: triology repo, branch claude/prepare-papers-repos-4LUdJ.
- Run: `bash scripts/smoke/run_paper1.sh` reproduces every number.
- Number aggregator: `python scripts/smoke/paper_table.py` regenerates Tables.
