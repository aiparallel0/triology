# Failure Catalog

Fifty-two catalogued failures from 221 commits across `aiparallel0/triology`
(Paper 1, σ-verifier, 67 commits) and `aiparallel0/arith-gating` (Paper 2,
beam-margin, 154 commits), 12 May – 25 May 2026, plus the `arith-gating`
predecessor era recorded in `RESEARCH_LOG.md`.

Every entry is real. The commit hash is the evidence. Where a fix commit exists
it is named, because **the fix commit is usually the only place the failure was
ever written down** — which is itself failure D8.

Eight families:

| | Family | Count | The shape |
|---|---|---|---|
| **A** | Benchmark and data diligence | 6 | The dataset is not what its paper says it is |
| **B** | Leakage and contamination | 4 | The eval split was in the training set |
| **C** | Statistical claim integrity | 9 | The number is real; the sentence about it is not |
| **D** | Number provenance and drift | 8 | The same quantity, two values, three artifacts |
| **E** | Citation integrity | 4 | A reference that cannot be resolved |
| **F** | Experiment pipeline reliability | 9 | The run completed and produced garbage |
| **G** | Framing, scope and churn | 7 | Rework caused by deciding late |
| **H** | Sibling and artifact symmetry | 5 | Two papers, one gets the attention |

---

## A. Benchmark and data diligence

These are the cheapest failures to prevent and the most expensive to discover.
All six were found *after* design work had been done against the assumed schema.

### A1 — The benchmark does not have the fields the method needs
**Symptom.** The arithmetic-identity verifier was designed around
`subtotal + tax = total`, `paid − change = total`, `subset-sum(items) = subtotal`.
**Root cause.** SROIE Task-3 labels exactly four fields: `{company, date,
address, total}`. No `subtotal`, no `tax`, no `paid`, no `change`, no `items`.
The method as specified could not be evaluated on the field's most obvious
benchmark.
**Detection.** Read the label schema — not the paper's description of it — before
committing to a benchmark.
**Fix.** Benchmark rejected on diligence. `RESEARCH_LOG.md §1`.

### A2 — The dataset name is a phantom
**Symptom.** Weeks of planning referenced "FATURA-2".
**Root cause.** There is no FATURA-2. The dataset is FATURA (Limam et al.,
arXiv:2311.11856). Third-party HuggingFace mirrors propagated a wrong name, and
the wrong name propagated into the plan.
**Detection.** Resolve every dataset to a primary source — the paper or the
authors' own release — before it enters a design document.
**Fix.** `scripts/fetch_fatura_zenodo.py`, now in `attic/`. `RESEARCH_LOG.md §1`.

### A3 — The paper's class count is not the shipped class count
**Symptom.** FATURA's paper documents 24 classes. The design assumed access to
`Subtotal_value`, `Tax_value`, `Discount`, `GST`.
**Root cause.** The authoritative Zenodo `layoutlm_HF_format` annotations
collapse 24 classes into 13, silently merging all of those into a single `OTHER`
class (ID 13). Only `total` and `items` survive as separable financial fields.
**Detection.** Load actual annotation files and count the distinct labels. A
paper's table describes intent; the shipped JSON describes the data.
**Fix.** Benchmark rejected. `RESEARCH_LOG.md §1, §6.3`.

### A4 — Parseable output mistaken for correct output
**Symptom.** The cross-dataset transfer experiment (H3) came back a wash: the
empirical ratio 1.55× collapsed to the arithmetic floor 1.43×.
**Root cause.** Donut-CORD was run zero-shot on WildReceipt. It emitted
**93% JSON-parseable** output and **69% per-field error**. Donut's decoder is
constrained to a fine-tuned JSON grammar, so the *shell* is nearly always valid;
the *values* inside it were mostly wrong. Both granularity conditions were
accepting mostly-wrong predictions, so the comparison measured nothing.
**Detection.** Report parse rate and accuracy as two separate numbers, always.
Never let one stand in for the other.
**Fix.** Result reframed; fine-tuning on the target distribution identified as
the precondition. `RESEARCH_LOG.md §1, §6.4`.

### A5 — Weak supervision too sparse to train on
**Symptom.** LayoutLMv3 fine-tuned on CORD-derived BIO labels converged to
predicting `O` for every token. End-task arithmetic pass rate: **0/100**.
**Root cause.** BIO labels were derived by string-matching gold field values
against OCR tokens, which tagged one token per field and `O` for the rest. At
small data scale the majority class wins.
**Detection.** Inspect the label distribution before training. A 1:N positive
rate at N in the hundreds is not a training set.
**Fix.** Backbone switched to Donut, which produces structured output natively
and needs no BIO derivation. `RESEARCH_LOG.md §2, §6.5`.

### A6 — The canonical split is smaller than the claim needs
**Symptom.** CORD-v2's canonical test split is 100 receipts; bootstrap CIs on
AUROC spanned ~0.21.
**Root cause.** No power analysis was done before designing the hypothesis.
Resolving a 0.03 AUROC gap at 80% power needs roughly **1,200 receipts** —
outside any published KIE benchmark.
**Detection.** Compute the minimum detectable effect from the split size before
committing to the hypothesis, not during revision.
**Fix.** Pre-committed power analysis is now §0.4 of the successor plan
(`non-key-handoff/non_key_channel_research_plan.md`), with per-corpus cells
below their MDE flagged `[underpowered]` and barred from the headline.
`RESEARCH_LOG.md §1, §6.1`.

---

## B. Leakage and contamination

The most dangerous family, because leakage **improves** every number. Nothing
looks wrong. The paper gets better.

### B1 — Evaluating on the fine-tuning split
**Symptom.** Commit `e56e15e` re-ran CORD on train+validation+test, n=1000, and
every cell improved.
**Root cause.** CORD-v2 **train is the Donut fine-tuning split.** The model had
seen 800 of those 1000 receipts during training.
**Detection.** For every (checkpoint, corpus) pair, write down which split the
checkpoint was trained on. It is a property of the checkpoint, not of the
corpus, and it is invisible in the data loader.
**Fix.** `70af078` — canonical CORD reset to test+validation, n=200. Five
poisoned run JSONs and four macro files restored from the last leakage-free
state (`073cabc`). Note what this cost: **a good state had to be identified in
history and restored, because the contamination had already propagated into
generated artifacts.**

### B2 — Contamination survives in a downstream cache
**Symptom.** After B1's fix, the pooled row was still contaminated.
**Root cause.** `build_T8_pooled` read a stale cached pooled figure rather than
recomputing from the per-corpus cells.
**Detection.** Any derived aggregate must be recomputed from its inputs on every
run, never cached. A cache of a contaminated number outlives the fix.
**Fix.** `70af078` — pooled row now recomputed from the leakage-free per-corpus
cells (n=1019, intersection 182/184, Wilson LB 0.961).

### B3 — Contamination survives in figures and analyses
**Symptom.** Figures still showed the contaminated n.
**Root cause.** Decontaminating the source of truth does not regenerate what was
derived from it. Five analyses (`T_significance`, `U2`, `U3`, `U4`,
`U_intersection_control`) and two figures depended on the poisoned cells.
**Detection.** Maintain the dependency graph from run artifacts to every derived
figure, table and macro. Regenerate the closure, not the file you noticed.
**Fix.** `70af078`, and in the sibling `c7f5c6f` — *"Regenerate Fig3 on
leakage-free n=200; recompute significance battery."*

### B4 — Prose survives the decontamination
**Symptom.** After the numbers were fixed, the paper still argued from the old
ones.
**Root cause.** The AURC null result was stated in prose. Post-decontamination
the result changed; the sentence did not.
**Detection.** Grep the prose for every number that moved. The macro system
updates the *rendered* numbers automatically, which is exactly why the
*sentences about* them go stale silently.
**Fix.** `d3ea4d4` — *"Fix stale AURC null prose contradicting
post-decontamination result."* Sibling: `e79bcdb`.

> **The B-family lesson.** Leakage is not one fix. It is: identify → restore a
> clean state → recompute derived aggregates → regenerate figures → re-run
> dependent analyses → rewrite the prose. Six steps, and the last one is the one
> that gets skipped, because by then everything looks correct.

---

## C. Statistical claim integrity

The numbers in this project were, with the exceptions in family D, correct.
These are failures of the **sentence wrapped around** the number.

### C1 — A null result claimed without power
**Symptom.** "Signal choice doesn't matter" reported as a finding on n=100.
**Root cause.** 13 candidate aggregators sat within an AUROC band of 0.026 with
fully overlapping bootstrap CIs and DeLong p ∈ [0.49, 0.81]. That is consistent
with *no difference* and equally consistent with *a difference this study cannot
see*. Absence of evidence was reported as evidence of absence.
**Fix.** The null is now stated with its MDE attached. `RESEARCH_LOG.md §3, §6.1`.

### C2 — A ratio that is arithmetic, not signal
**Symptom.** Field-level abstention reported as 2.26× better than receipt-level.
**Root cause.** A receipt has ~12 fields and is wrong iff any field is wrong, so
receipt error is **mechanically** ~3.15× field error. About 99% of the "win" was
conjunction arithmetic. The comparison was between units, not between methods.
**Detection.** For any ratio between two granularities, compute what the ratio
would be under a null model with no signal at all. Report the excess.
**Fix.** `a5308e8` — base-rate baseline paragraph added. Reviewer round 1.

### C3 — The narrative contradicted by a second metric
**Symptom.** Round-2 review showed relative-risk reduction **favoured the
opposite conclusion** (35% vs 26% at c=0.80).
**Root cause.** The paper had chosen the metric that supported the story.
**Detection.** Compute both absolute and relative forms of every headline
comparison before writing the sentence. If they disagree, that disagreement is
the finding.
**Fix.** `c7cc3eb` — *"flip rhetorical centre to match the data (H1 null is the
finding)."* The correct response to a metric that contradicts the narrative is
to change the narrative.

### C4 — Significance mistaken for effect
**Symptom.** An orthogonal-shift result was called positive because its
bootstrap CI excluded zero.
**Root cause.** With enough resamples, a CI excludes zero for effects too small
to matter.
**Fix.** `5a1edfa` — *"require meaningful effect (≥0.02 AUROC), not just CI>0."*
The threshold was set **before** the verdict, and the honest verdict then
followed (`8a0fded`).

### C5 — p-values below floating-point underflow
**Symptom.** Levene/Bartlett/F/Fligner reported as p < 10⁻⁸⁶, 10⁻²⁸¹, 10⁻⁸⁹.
**Root cause.** Those are below double-precision underflow. They are artifacts of
the computation, not measurements, and read to a reviewer as naive
over-precision.
**Fix.** `65d48ba` — substantive test statistics kept verbatim (W=508, T=1285,
F=156), p reported at the paper's existing conservative bound of 10⁻⁴⁰. Note
the discipline: **address correctly, do not under-address.** The fix keeps the
strong true statement and drops only the indefensible digits.

### C6 — A superlative the data does not support
**Symptom.** The paper's title claimed a "difficulty-invariant" signal.
**Root cause.** A dedicated re-analysis (`BM_difficulty_invariance.py`) found
CORD and SROIE nearly disjoint in sequence length; only the short bin tests both.
There log₂C survives at 4.57 (~24×), so the law is not a pure length artefact —
**but** sequence length still out-separates the margin (AUROC 0.869 vs 0.769).
Length is a partial confound that was *not* eliminated.
**Fix.** `04ed7e2` — title changed to "Distribution-Shift", the
"length-confound ruled out" claim downgraded to "partially controlled" with the
stratified numbers stated. The commit message is the model: *"This is
data-driven correction of a real overclaim, not reflexive softening; the law
itself (reproducible 169× compression) stands."*

### C7 — A quantity misdescribed in the abstract
**Symptom.** The abstract said a shift statistic sat "well inside" the
in-distribution spread.
**Root cause.** 0.069 is ≈1.08 σ_in. That is *outside* one standard deviation,
not well inside.
**Fix.** `373d037`. Abstracts get written early, from an intuition about a number
that later changed.

### C8 — Small-n cells presented as results
**Symptom.** SROIE's combined-rule cell reports 15/15 correct, a perfect 100%.
**Root cause.** n=15 supports a Wilson lower bound of 0.796. It is consistent
with the overall finding and proves nothing on its own.
**Fix.** Every mention is now marked "n=15, consistency only", and the caveats
deck devotes a section to it: *"Even a perfect 15/15 only guarantees about 0.80
or better."*

### C9 — A pooled headline carried by one corpus
**Symptom.** Pooled n=1019 reads as three-corpus evidence.
**Root cause.** 114 of the 184 combined-rule accepts are WildReceipt. The pool is
unevenly weighted at 200/347/472 and the effect is carried by one corpus.
**Fix.** The per-corpus table, not the pool, is the stated headline; the pooled
figure is explicitly labelled secondary; leave-one-corpus-out worst-case Wilson
lower bound is reported alongside the pool.

---

## D. Number provenance and drift

Family C is about sentences. This family is about the numbers themselves being
in more than one place.

### D1 — A number with no measurement behind it
**Symptom.** The paper stated σ's latency.
**Root cause.** Nothing had measured it. The figure came from an estimate.
**Fix.** `2b4f929` *"Replace unbacked sigma latency numbers with real CPU
measurement"*, then `006db2d` *"Commit sigma-latency measurement artifact
(backs the paper's latency numbers)"*. Two commits, and the second is the one
that matters: **the artifact that backs the number is committed beside it.**

### D2 — The same quantity disagreeing across artifacts
**Symptom.** Paper, presentation deck and caveats deck stated different values
for the same quantities.
**Root cause.** Three artifacts, three hand-copied sets of numbers.
**Fix.** `b8e2b57` *"Reconcile reviewer-flagged number contradictions across
paper + decks."* Reviewer-flagged: an external reader found it.

### D3 — A rounded quantity recomputed inconsistently
**Symptom.** Coverage stated as 38.1%.
**Root cause.** 386/1019 = 37.9%. Someone rounded from a different intermediate.
**Fix.** `b9edc78`.

### D4 — An aggregate that does not equal the sum of its parts
**Symptom.** Table III's pooled McNemar row printed b=183, c=186.
**Root cause.** The per-corpus rows sum to 185 and 188 (44+50+91, 41+56+91). The
pooled row was typed, not computed.
**Detection.** Assert every total against the sum of its components, in code.
**Fix.** `b9edc78`, including the backing macro file `numbers_pooled.tex`.

### D5 — Two derived numbers in the same paragraph disagreeing
**Symptom.** A cost-benefit sentence used c=0.381 and p=0.954 while the table
two lines above said 0.379 and 0.953.
**Fix.** `e93f487`.

### D6 — Impossible values rendered without complaint
**Symptom.** Figures printed `n=-217` and `n=None`.
**Root cause.** An upstream computation produced nonsense and the plotting code
formatted it faithfully.
**Detection.** Assert domain constraints at the plotting boundary: counts are
non-negative integers, probabilities are in [0,1], n is not None.
**Fix.** `d125ba5`.

### D7 — A macro default that ships as a plausible value
**Symptom.** Results macros carry safe defaults (`NA`, `PENDING`, a placeholder
number) so the paper compiles before the pipeline has run.
**Root cause.** When the generated file fails to load, the default renders
perfectly. `NA` typesets. A default numeric value typesets *and looks like a
result.*
**Detection.** Assert at `\begin{document}` that every default was overridden.
**Fix.** `f936412` *"fix silent-default + fatal macro bugs"*, `bfe8f3b` *"add
missing newcommand defaults"*, and in this repo's conformance pass the
`\assertfilled` guard.

### D8 — The finding recorded only in the fix
**Symptom.** Most entries in this catalog were reconstructed from commit
messages, because that is the only place they exist.
**Root cause.** A defect found, fixed and described in a commit message is
invisible to anyone reading the paper, the log, or the next session's context.
**Fix.** A tracked defect register. `RESEARCH_LOG.md` was written once
(`1a6136f`) and is excellent; it was never updated after.

---

## E. Citation integrity

### E1 — A citation that cannot be located
**Symptom.** `rombach2026conformal` was cited as prior work in document-KIE
conformal prediction — a load-bearing novelty claim.
**Root cause.** The reference could not be resolved to a primary source.
**Fix.** `ee880e5` *"Delete unlocatable rombach2026conformal citation."*
Deleting a citation you cannot verify is the correct action even when it
weakens a related-work paragraph.

### E2 — A `\cite` to a bib entry that does not exist
**Symptom.** `\cite{ioffe2015batchnorm}` with no matching entry.
**Detection.** `grep -c undefined main.log`. Zero-cost, and it was not run.
**Fix.** `0069e1b`.

### E3 — Statistical machinery used without attribution
**Symptom.** Wilson intervals, McNemar, AURC and calibration used throughout
with no citation at first use.
**Fix.** `ffa1249`.

### E4 — Over-sanitising destroyed real information
**Symptom.** A pass that rewrote code-like tokens into plain prose removed real
dataset and annotation names.
**Root cause.** A formatting rule applied without asking whether each instance
carried information.
**Fix.** Three commits to undo: `2d82e43` *"restore real dataset name (Invoices
and Receipts OCR v1) in all four references"*, `422924c` *"restore the canonical
dataset annotation names (Total_value, Prod_price_value) in plain serif text —
preserves real info without code font"*, `d53a2a3`.
**The lesson.** A cleanup rule needs an exception test: *does this token name a
real object a reader must be able to look up?*

---

## F. Experiment pipeline reliability

Nine ways a run completed successfully and produced nothing usable.

### F1 — A stale committed artifact silently reused
**Fix.** `edbf6b2` — *"force-fresh (rm stale committed runs JSON)."* Committing
run artifacts makes results reproducible **and** makes stale results invisible.
Both are true; the second needs a force-fresh path.

### F2 — Requesting more devices than exist
**Fix.** `edbf6b2` — clamp GPUS to the real device count.

### F3 — A crashed worker wedges the pipeline
**Symptom.** The orchestrator hung instead of failing.
**Fix.** `013fcae` — *"clean worker exit + missing-script guards (stop pipeline
wedging)."* A hang costs more than a crash: a crash tells you.

### F4 — The scores you need are not populated by default
**Symptom.** `sequences_scores` was empty, so the beam-margin signal was
undefined.
**Root cause.** HuggingFace `generate()` needs `output_scores=True` and
`return_dict_in_generate=True`.
**Fix.** `08612d2`, with a per-step fallback path.

### F5 — Schema mismatch produces empty output and a tiny n
**Symptom.** SROIE returned n=7.
**Root cause.** Donut-CORD emits `<s></s>` on schema mismatch — an empty but
*valid* generation. Seven receipts survived filtering.
**Detection.** Assert a floor on n after every filtering step. A silent collapse
from 347 to 7 should stop the run.
**Fix.** `3ef3527` — force `min_new_tokens`.

### F6 — dtype crash deep in a run
**Fix.** `d6a1b1d` — fp16 dtype crash in the Mahalanobis path.

### F7 — Output written to the wrong path
**Fix.** `a4ae881`. The run "succeeded" and the analysis read the previous file.

### F8 — Bugs that waste an entire GPU run
**Fix.** `e0fc924` — *"Fix run-wasting + methodology bugs in new Paper 2
analyses."* The named category is the useful part: some bugs cost only a
re-run; these cost the run.

### F9 — Plotting code that fails only on the real data
**Symptom.** `wild_only` KeyError, and an f-string scoping bug.
**Fix.** `d9692f4`. Figure scripts are code and need the same smoke test as the
pipeline; they run last, when the compute has already been spent.

> Related: matplotlib's mathtext does not support `\le` (`e6e6803`). Figure
> text is a third typesetting system with its own grammar, beside LaTeX and the
> terminal.

---

## G. Framing, scope and churn

### G1 — The central claim changed three times
v1 arithmetic-identity gating → v2 entropy localization → v3
granularity-not-signal. Each shift was **data-driven and correct**; the cost
was that all downstream writing was invalidated each time.
`RESEARCH_LOG.md §3`.

### G2 — The idea duplicated a sibling paper
**Symptom.** v1's mechanism was found, on cross-comparison, to be Paper 1 of the
author's own trilogy.
**Detection.** Cross-check against your own prior work before the literature.
**Fix.** Pivot to a different mechanism on the same plumbing.

### G3 — Nine titles
`bc5e894` → `cbf878d` → `ca3bbdc` → `0788a97` on Paper 1;
`cdb9cf6` → `3039a2d` → `a0ac293` → `8858709` → `94db16d` → `c80c562` on Paper 2.
Two of these ("vision-forward", "importance-forward") are pure taste. A title is
cheap to change and cheap to defer: **fix the title last.**

### G4 — Fitting the page limit, repeatedly
`91b66b6` 7→6 pages, then `0daafe3` more aggressive trim, then `6e2950d` restore
tables and hard-cut prose instead, then `6262eb9` a full condensation. Four
passes, because content was still moving.

### G5 — An eight-version fix cascade in one day
v4.1 → v4.8 on 13 May, with messages of the form *"fix 5 v4.5 errors"*,
*"fix 6 visible v4.6 misalignments"*, *"harsh-review fixes"*. Each version fixed
errors the previous one introduced. Symptom of editing the rendered artifact
faster than it could be checked.

### G6 — Shipped duplicates
`063629c` — *"remove duplicate H2 coverage table and risk-coverage figure."*
Both were in the PDF.

### G7 — A merged PR reverted wholesale
`7bb0851` merged, `ec12350` reverted, `4776fcd` merged the revert. Whole-paper
PRs are atomic in the wrong direction.

---

## H. Sibling and artifact symmetry

Two papers and, per paper, a main document, a presentation deck and a caveats
deck. Six artifacts, each of which can drift.

### H1 — Every fix applied twice, manually
hyperref hidelinks (`3eb1542` / `5653a04`), em-dash removal, overflow prevention
(`794de59` / `e8f08c2`), gitignore for build artifacts (`ad73310` / `8d5d80c`),
caveats deck (`372ceb5` / `3e74860`), decontamination (`70af078` / `b27e95b`).
Nearly every commit in one repo has a twin in the other, applied by hand, days
apart.

### H2 — The decks drift from the paper
`8bbfbec` — *"develop/finalize presentation + caveats decks consistent with
final paper incl. corrected CPU latency + reconciled numbers."* Reconciliation
was a distinct, late task.

### H3 — A deck scoped to the wrong paper
`c72f57e` — *"refocus caveats deck to standalone beam-margin paper."*

### H4 — Figure-level defects found only by looking
`630756c` — a caption-redundant overlay causing node overlap, and `0.991`
rendering outside its circle. `a67d179` — latency-axis decades too narrow, so
p99/100/1000 labels collided. No check catches these. Render every figure at
final size and look at it.

### H5 — Layout defects that only appear at the boundary
`0a0031f` — *"drop redundant keyword so abstract block no longer orphans 'test'
into column 2."* `7516883` — a glue spec printed as body text because
`\setlength` was used where `\renewcommand` was needed.

---

## The distribution

| Family | Prevented by | Cost if not |
|---|---|---|
| A — data diligence | one hour reading schemas | the method is unevaluable |
| B — leakage | a checkpoint/split table | every number, silently better |
| C — claim integrity | computing both metrics first | the reviewer finds it |
| D — provenance | one source of truth + assertions | contradictions across artifacts |
| E — citations | resolving each to a primary source | a deleted claim, late |
| F — pipeline | asserting on n, dtype, path, floor | a wasted GPU run |
| G — framing | deciding scope before writing | everything downstream |
| H — symmetry | doing both artifacts in one commit | invisible divergence |

**Families A, B and G are decided in the first day.** They caused most of the
rework. The audit kit cannot detect them; only sequence prevents them, which is
what `03-LIFECYCLE.md` is for.
