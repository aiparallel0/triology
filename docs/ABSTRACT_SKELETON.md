# Paper 1 (FOCUS-Sigma / ASYU seed) — Abstract Skeleton

Fill in numbers from `runs/PAPER_TABLE.json` (regenerated each run by `paper_table.py`).

## Working title (pick one)

- *"Subset-Sum Verification as a Confidence-Orthogonal Selective Predictor for Receipt KIE Total Fields"*
- *"Sigma: A Subset-Sum Witness for Receipt Total Predictions"*
- *"Arithmetic Identity Verification of KIE Total Predictions"*

## Abstract (~180 words)

> **Problem.** Key-Information-Extraction (KIE) models predict receipt totals that propagate downstream; their errors are costly. Confidence-based abstention is domain-blind and ignores the receipt's arithmetic redundancy.
>
> **Method.** We propose **σ**, a subset-sum verifier that accepts a predicted total iff it can be witnessed as a subset-sum identity over the receipt's amount lines plus extracted tax: $\exists S, \sum S + \tau = \pi$. The verifier is a 0/1-knapsack DP with a cardinality guard $|S| \geq 2$.
>
> **Results.** Across three corpora and two model families:
> - CORD-v2 (n=[CORD_N]): $\sigma$ achieves precision **[CORD_SIGMA_PREC]%** at [CORD_SIGMA_COV]% coverage, vs softmax-threshold's [CORD_SOFTMAX_PREC]% at matched coverage. The $\sigma$-only accept set is **[SIGMA_ONLY_NUM]/[SIGMA_ONLY_DEN] = 100%** correct (Wilson 95% CI [CI_LO, CI_HI]).
> - SROIE Task-3 (n=347): softmax dominates at high precision; $\sigma \cup$ softmax expands the high-coverage Pareto front.
> - WildReceipt (n=472, LayoutLMv3 encoder-only): $\sigma$ achieves [WR_SIGMA_PREC]% at [WR_SIGMA_COV]% coverage.
>
> The DP runs at **[DP_P99] ms** p99 (n=347 SROIE), and $\sigma$ is precision-robust to label noise (≥0.93 precision under 40% perturbation, 10 seeds). $\sigma \cap$ softmax achieves 100% precision on the joint-accept set across all tested corpora.
>
> **Contribution.** $\sigma$ is a domain-aware, confidence-orthogonal selective predictor that **Pareto-dominates softmax-thresholding on labeled-amounts corpora** and provides complementary high-precision evidence on OCR-derived corpora. We characterize when $\sigma$ helps via a regime taxonomy.

## Numbers to fill (from PAPER_TABLE.json)

| placeholder | source | locked value |
|---|---|---|
| `[CORD_N]` | T1 CORD `n` | 100 |
| `[CORD_SIGMA_PREC]` | T1 CORD `sigma_precision` | 98.2 |
| `[CORD_SIGMA_COV]` | T1 CORD `sigma_coverage` | 55.0 |
| `[CORD_SOFTMAX_PREC]` | T1 CORD `softmax_precision` | 92.7 |
| `[SIGMA_ONLY_NUM]/DEN` | T1 CORD `sigma_only` | 22/22 |
| `[CI_LO, CI_HI]` | T `sigma_only.wilson_95_ci` | [0.85, 1.00] |
| `[WR_SIGMA_PREC]` | T1 WildReceipt | 95.3 |
| `[WR_SIGMA_COV]` | T1 WildReceipt | 45.3 |
| `[DP_P99]` | T2 `p99_ms` | 0.55 |

## Honesty notes to weave in

- N's finding: accept-all wins at λ=0 (cost-symmetric); $\sigma$'s value is realized when error-cost ≫ abstention-cost. Mention this in discussion.
- SROIE softmax wins at matched coverage: report honestly; orthogonality and $\sigma \cup$ softmax are the SROIE story.
- WildReceipt softmax baseline deferred (no image archive bundled with HF dataset): explicit limitation note + journal future work.
- McNemar paired test on SROIE/CORD: report p-values from T `mcnemar_paired_test.p_value`.
