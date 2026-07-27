# Evidence and Claims

How a number becomes a sentence, and what goes wrong in between. Plus the
dossier of every human revision these two papers received.

---

## A. The claim-strength ladder

The failures in family C are all the same failure: a claim stated one rung
higher than its evidence supports. Fix the rung, not the wording.

| Rung | Wording | What must be true | Example from these papers |
|---|---|---|---|
| 6 · **Proven** | "X is Y" | Deductive, or an exact computation | "the total *is* a sum of visible amounts" — true by construction on well-formed receipts |
| 5 · **Established** | "X beats Y (p, CI, effect ≥ θ)" | Pre-committed threshold cleared, per-corpus and pooled, confound named | the 169× variance compression: reproducible, mechanism-confirmed |
| 4 · **Resolved but modest** | "a small, statistically resolved gain" | CI excludes zero, effect small, said so | σ's orthogonality lift: *"small, pooled, statistically-significant, and explicitly not per-corpus or large"* |
| 3 · **Consistent with** | "consistent with the overall finding" | Underpowered cell, direction agrees | SROIE 15/15, Wilson LB 0.796 — "n=15, consistency only" |
| 2 · **Hypothesis** | "we hypothesise; this remains a hypothesis" | Plausible mechanism, no controlled test | the SROIE loss attributed to upstream OCR: *"the controlled hand-OCR-corrected subsample test remains future work"* |
| 1 · **Not established** | say nothing, or say the null with its MDE | Absence of evidence | the 13-aggregator null: **must** carry "~1,200 receipts needed to resolve" |

**Two directions of failure, and they are not symmetric.**

*Upward drift* is the dangerous one: rung 2 becomes rung 5 across three commits
each described as tidying. Nothing looks like a fabrication at any single step.

*Downward over-correction* is also a defect. When p-values below floating-point
underflow were reported, the fix was **not** to soften the finding. It kept the
substantive statistics verbatim (W=508, T=1285, F=156) and bounded only the
indefensible digits (`65d48ba`). The commit message for the title overclaim
states the principle exactly:

> *"This is data-driven correction of a real overclaim, not reflexive softening;
> the law itself (reproducible 169× compression) stands."* — `04ed7e2`

**Weakening a true strong claim into a vague one is not honesty. It is a
different error with better manners.**

### The test before you write

For each claim, in writing:

1. Which generated file holds the number?
2. What is the effect size, and what threshold was pre-committed?
3. Absolute *and* relative — do they agree? (C3)
4. Per-corpus *and* pooled — which corpus carries it? (C9)
5. What would a null model with no signal give? (C2)
6. What confound remains, and how big is it? (C6)
7. What is the smallest n in any cell that supports this? (C8)

If a question has no answer, the claim is one rung lower than you wrote it.

---

## B. Provenance: one number, one home

The rule: **every number in every artifact resolves to exactly one generated
file, which resolves to exactly one run artifact.**

The implementation in these repos, which works:

```
scripts/smoke/U5_percorpus_rigor.py     ->  numbers_percorpus_rigor.tex
                                             \renewcommand{\rgCordWil}{0.9039}
main.tex:  \newcommand{\rgCordWil}{0.9039}    % safe default
           \InputIfFileExists{numbers_percorpus_rigor.tex}{}{}
```

Three properties this buys, and the failure each prevents:

- The paper compiles before the pipeline has run (drafts stay reviewable).
- A number cannot disagree between the paper and its table (D2, D3, D5).
- Changing a result changes every mention at once.

And the **failure mode it introduces**, which must be tested for separately:
when the generated file does not load, the safe default renders perfectly. `NA`
typesets. A placeholder *number* typesets and looks like a result (D7).

```latex
% the test that makes the bridge worth having
\AtBeginDocument{%
  \assertfilled{\latMedian}{NA}%
  \assertfilled{\rcEarned}{PENDING}%
}
```

> The bridge without the test is a net loss. It swaps a *visible* inconsistency
> for a *silent* one.

### Assertions the generator owes you

Not the paper's job — the generating script's:

- **Totals equal the sum of their parts.** Table III's pooled McNemar row printed
  183/186 where the per-corpus rows summed to 185/188 (D4). One `assert` in
  `build_T8_pooled` would have caught it.
- **Derived aggregates are recomputed, never cached.** A cached pooled figure
  survived a leakage decontamination and stayed contaminated (B2).
- **Domain constraints hold at the plotting boundary.** Counts non-negative
  integers, probabilities in [0,1], n not `None` (D6).
- **Rounding happens once, at the end.** 386/1019 = 37.9%, printed as 38.1%
  because someone rounded an intermediate (D3).

---

## C. The human-revision dossier

Four named human revisions landed on these two papers, plus two rounds of
scientific critique on the predecessor. They are the ground truth for what
reviewers of this venue class actually ask for.

### C.1 — Two rounds of scientific critique (predecessor, `arith-gating` era)

**Round 1 — the base-rate confound.** The 2.26× advantage claimed for field-level
abstention is mostly conjunction arithmetic: a receipt has ~12 fields and is
wrong iff any is wrong, so receipt error is mechanically ~3.15× field error.
About 99% of the "win" was structural.
*Response:* explicit acknowledgment in the abstract, plus a "base-rate baseline"
paragraph (`a5308e8`). **Adding the honest comparison, not removing the claim.**

**Round 2 — the metric that reverses the conclusion.** Relative-risk reduction
*favours receipt-level* abstention (35% vs 26% at c=0.80), directly contradicting
the paper's narrative.
*Response:* flip the rhetorical centre. The H1 null became the contribution;
H2's absolute-risk win was demoted to mostly-inherited-from-arithmetic
(`c7cc3eb`).

> The author's own diagnosis after round 2 is the most useful line in the whole
> project record: **"the right fix is more experiments, not more
> wordsmithing."** A 2×2 of {Donut, Pix2Struct} × {CORD, WildReceipt} across
> seeds would convert "underpowered null on n=100" into "consistent null across
> 8 cells", at which point the result speaks without rhetorical hedging.

### C.2 — Four editorial revisions (`docx` / RedInk / Keskinoz / Sigma-Verifier)

Delivered as revised documents to be applied. What every one of them asked for,
across both papers:

| Demand | Commits |
|---|---|
| **Descriptive subsection titles** — "Results A–F" → titles that state the finding | `8e0fe35`, `11b0602`, `0c36dde` |
| **Plain-language captions and body** — captions replaced verbatim, body explanations added into Results | `8e0fe35`, `11b0602` |
| **A defined vocabulary** — "gate" defined once at first use; "gate"→"decision rule", "intersection"→"combination" paper-wide | `ce7e049`, `8e0fe35` |
| **House style** — no em-dashes; plain symbols typeset as math; `[ref]` → `\cite` | `e7b216d`, `ee880e5`, `11b0602` |
| **Structural merge** — Discussion and Limitations merged | `11b0602` |
| **Every caveat preserved through the 6-page hold** | all four |

Two things generalise from how these were applied.

**The revision file is the specification; your paper is the artifact.** Captions
and titles were replaced **verbatim** rather than paraphrased. Paraphrase is
where a revision silently becomes a negotiation.

**"6-page hold" was a stated exit condition on every one.** Each commit message
ends with the same evidence: *"6 pages, 0 Overfull, 0 undefined refs/cites, 0
em-dashes, guard PASS."* A revision that pushes you over the limit is not
applied yet.

### C.3 — The six formatting rules

A reviewer on a sibling venue delivered six formatting rules with a covering
instruction that matters as much as the rules:

> *"Apply these 6 rules to the **whole paper**, not only the first instances
> noted. If you find further places covered by the same rule that were not
> annotated, report those too."*

That is directive D2-of-conformance stated by the reviewer themselves. The six:

1. **Abstract fully bold.** The real defect is that inline math stays upright
   inside a bold paragraph — `\boldmath`, not bolding words by hand.
2. **Keywords fully italic.** IEEEtran italicises only the `Keywords—` lead-in
   (verified at `IEEEtran.cls:5288`).
3. **Figure captions use a period, not a colon.** Root cause is nearly always
   `\usepackage{caption}`, which has no IEEEtran support and replaces the
   class's `\@makecaption` wholesale.
4. **Table captions per the template** — on three axes: capitalisation,
   punctuation, alignment. Capitalisation is the one most agents miss: IEEEtran
   sets table titles in `\scshape`, which forces short captions and pushes
   displaced detail into the body.
5. **Tables must actually be tables** — real tabular structure, template rule
   style. This note recurred pointed at an `algorithm` float, because a ruled
   float with a bold run-in header reads as an unlabelled table.
6. **Subsection titles in Title Case** — and check `\section` too.

**Where they were applied here:** all six, in the conformance pass recorded at
`paper/asyu/audit/CHANGES.md`. Rules 1, 2, 4 and 6 were real defects and were
fixed. Rule 3 was already satisfied — this paper never loaded the `caption`
package, which is *why* its captions are correct, and that is worth knowing
before someone adds it. Rule 5's rule-style axis was **deliberately not
applied**: the only authority for a grid style would be the venue template,
which is not in the repository, and `IEEEtran.cls` prescribes nothing about
table rules. See constraint 6 in the master prompt — a cleanup rule needs an
exception test, and applying a plausible rule without its authority is how a
correct paper acquires defects.

---

## D. The caveats deck as a device

Both papers ship a `caveats_explained.tex` — a standalone deck that walks every
limitation from first principles, with the real numbers. It is the single most
transferable artifact in these repos.

Structure, per caveat: *plain-language statement → the actual numbers → what it
does and does not license → what would resolve it.*

The five caveats it carries for Paper 1:

1. Per-corpus underpowered — pooled 0.989 is carried by WildReceipt (114 of 184)
2. σ alone trails softmax in the OCR regime (0.863 vs 0.945) — stated plainly
3. The effect is small, not large — orthogonality established, magnitude not
4. Latency provenance — CPU-only, no end-to-end ratio measured
5. Scope and novelty — arithmetic cross-checks are long-standing practice; the
   contribution is the formalisation and the paired statistics

Three reasons this pays for itself:

- **It is the Phase 3 claims table, rendered.** Writing it forces the interpretation
  work before the prose, which is the whole point of Phase 3.
- **It pre-empts the reviewer.** Every caveat a reviewer could raise is already
  stated, with numbers, at the right rung of the ladder.
- **It resists upward drift.** A claim cannot quietly harden in the paper while a
  deck states its limit in plain language.

Its own closing line is the standard to hold:

> *"A true sentence that limits your claim is not a defect. A false sentence
> that inflates it is."*

---

## E. The unverified list

Everything not confirmed against an independent authority, tracked in the repo
rather than in a conversation (D8). Three sections:

**Blocking on a human** — the author block, the deadline, the venue template.
Cannot be inferred; a plausible invented affiliation is worse than an obvious
gap.

**Not verifiable in this environment** — every rendered-artifact check when
there is no TeX distribution; every GPU result when there is no GPU. These
report **SKIP**, never a quiet pass. *A check whose "could not run" state is
indistinguishable from "nothing wrong" is worse than no check.*

**Noticed but not re-derived** — first-ness claims, unused packages, a number
spelled two ways in two places. Not defects today. The register is what stops
them from becoming defects in a month.
