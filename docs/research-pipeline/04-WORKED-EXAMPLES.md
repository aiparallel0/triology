# Worked Examples

Three defects traced end to end, with the fork points marked. At each fork the
careless move is shown beside the correct one. **The careless move is always the
faster one, and always produces an artifact that looks better.**

---

# Example 1 — The result that improved

The most dangerous class, because every signal says success.

## The input

Commit `e56e15e`, *"Paper1 per-corpus power (CORD train+val+test, B fixed)."*
A reasonable, well-motivated change: the CORD test split is 100 receipts,
bootstrap CIs span ~0.21, and the paper is underpowered per-corpus (A6, C1). So
run on all three splits and get n=1000.

Every cell improved. The per-corpus power problem was solved.

## Fork 1 — What does an improvement mean?

**❌ Careless:** accept it. More data, better numbers, tighter intervals. This is
exactly what more data is supposed to do, and the change was made *specifically*
to fix an acknowledged weakness. Nothing in the output distinguishes this from
success.

**Why it fails:** CORD-v2 **train is the Donut fine-tuning split.** The
checkpoint is `naver-clova-ix/donut-base-finetuned-cord-v2`. 800 of those 1000
receipts were in its training set. The improvement is memorisation.

**✅ Correct:** treat an unexplained improvement as a defect until explained. The
question is not "are these numbers better?" but "which split was this checkpoint
trained on?"

```
checkpoint                                       fine-tuned on
naver-clova-ix/donut-base-finetuned-cord-v2      CORD-v2 train
philschmid/donut-base-sroie                      SROIE
Theivaprakasham/layoutlmv3-finetuned-wildreceipt WildReceipt train
```

> **Fork lesson:** leakage is a property of the **checkpoint**, not of the
> corpus, and it is invisible at the data loader. It never announces itself,
> because its only symptom is that your paper got better.

## Fork 2 — What is the unit of the fix?

**❌ Careless:** change the split back and re-run. One line, one command.

**Why it fails:** by the time the leakage was found, the contaminated numbers had
propagated into five run JSONs, four macro files, a cached pooled aggregate, two
figures, five downstream analyses, and the prose. Re-running the loader fixes
the first of those.

**✅ Correct:** fix the closure. `70af078` did six things:

```
1. restore   5 poisoned run JSONs + 4 macro files from the last
             leakage-free state (073cabc)
2. recompute the pooled row from the leakage-free per-corpus cells
             -- build_T8_pooled had CACHED it (B2)
3. correct   the contaminated LOCKED CORD cells hard-coded inside
             MF2_wildreceipt_softmax.py
4. regenerate fig_overview + fig_accept_venn
             ("CORD now n=200 / 55, no negative or None counts")
5. re-run    T_significance, U2, U3, U4, U_intersection_control
6. -----------------------------------------------------------------
```

Step 6 is missing from that commit. It arrived separately.

## Fork 3 — The step that nearly escaped

**❌ Careless:** the macros are regenerated, so the paper renders the new numbers.
Done.

**Why it fails:** the macro bridge updates every *number*. It cannot update a
*sentence about* a number. The paper contained a prose argument that the AURC
comparison was null — a claim which was true of the contaminated numbers and
false of the clean ones. The paper now rendered correct numbers underneath an
argument that contradicted them.

**✅ Correct:** `d3ea4d4` — *"Fix stale AURC null prose contradicting
post-decontamination result."* Sibling: `e79bcdb` — *"Fix stale variant-count
contradiction in limitations (i)."*

> **Fork lesson:** the single-source-of-truth bridge creates a blind spot exactly
> the size of its own benefit. Numbers update automatically, so **prose about
> numbers is the only thing that can silently go stale** — and it is the last
> place anyone looks, because everything renders correctly.

## Fork 4 — What do you do with the contaminated run?

**❌ Careless:** delete it. It was wrong.

**✅ Correct:** keep it, reframed as a control. The sibling paper's `b27e95b`:

> *"F5 reframed as an honest robustness check: including the CORD-train
> fine-tuning split (n=400) gives 7.29, **lower**, so training leakage does not
> inflate the effect."*

A contaminated run, correctly labelled, is evidence about the direction of the
contamination. That is worth more than a deletion.

## Outcome

One Phase 0 table — checkpoint against fine-tuned-on split — would have cost an
hour and prevented: a contaminated headline, a six-step restore, a re-run of
five analyses, two figure regenerations, two prose corrections across two
papers, and a repeat of the entire honest-verdict pass (stages 11 → 13 in
[03-LIFECYCLE.md](03-LIFECYCLE.md)).

The careless path at any fork yields a paper with better numbers, a clean build,
and a result that does not exist.

---

# Example 2 — The claim that was true, at the wrong rung

## The input

A real, reproducible, mechanism-confirmed finding: beam-margin variance
compresses by **169×** between in-distribution and shifted data. The effect is
large, it replicates, and the mechanism is understood.

The paper's title claimed the signal was **difficulty-invariant**.

## Fork 1 — Is a strong true result licence for a strong claim?

**❌ Careless:** yes. The compression is 169×. The mechanism is confirmed. The
claim follows.

**Why it fails:** "difficulty-invariant" is not a claim about effect size. It is
a claim that a *specific confound* — example difficulty, of which sequence
length is the main observable — has been **eliminated**. Nothing in the 169×
result speaks to that.

**✅ Correct:** write a dedicated analysis for the confound.
`BM_difficulty_invariance.py`, a CPU re-analysis of existing data — no new
compute.

## Fork 2 — What does the confound analysis say?

It came back **mixed**, which is the hardest case:

```
CORD and SROIE are nearly seq_len-disjoint  -> only the short bin tests both
in the short bin: log2C survives at 4.57 (~24x)
   => the law is NOT a pure length artefact
but seq_len still out-separates margin: AUROC 0.869 vs 0.769
   => length is a PARTIAL confound, NOT eliminated
```

**❌ Careless A — keep the claim.** The law survived the stratified test. That is
the headline. The AUROC comparison is a detail.

**❌ Careless B — retract the finding.** Length out-separates the signal, so the
result is confounded and the paper should hedge everything.

**Both are wrong, and B is the one careful agents choose.** Over-correction reads
as rigour and is a different error with better manners.

**✅ Correct:** `04ed7e2` split the claim at the joint:

| Component | Evidence | Action |
|---|---|---|
| 169× compression is real and reproducible | direct measurement, replicated | **kept, unchanged** |
| the law is not a pure length artefact | short-bin log₂C = 4.57 | **kept, with the number** |
| difficulty is *eliminated* | contradicted: AUROC 0.869 vs 0.769 | **removed from title and body** |

Title: "Difficulty-Invariant" → "Distribution-Shift". Mechanism section:
"length-confound ruled out" → "partially controlled", with the stratified
numbers stated inline.

The commit message states the discipline exactly:

> *"This is data-driven correction of a real overclaim, not reflexive softening;
> the law itself (reproducible 169× compression) stands."*

> **Fork lesson:** a claim is not one thing. Decompose it into components, attach
> the evidence to each, and correct only the components that fail. The cost here
> was one word in a title.

## Fork 3 — The same shape, one commit later

`65d48ba`: Levene/Bartlett/F/Fligner p-values reported as p < 10⁻⁸⁶, 10⁻²⁸¹,
10⁻⁸⁹ — below double-precision underflow. Artifacts of the computation, and to a
reviewer they read as naive over-precision.

**❌ Careless A:** leave them; the tests really are overwhelming.
**❌ Careless B:** replace with "highly significant" and drop the statistics.

**✅ Correct:** keep the substantive test statistics verbatim (W=508, T=1285,
F=156) and report p at the paper's own existing conservative bound of 10⁻⁴⁰.
The commit says it in four words: **"address correctly, not under-address."**

## Outcome

Two overclaims corrected without losing a single true finding, because in both
cases the claim was decomposed before it was edited. Compare with the
predecessor's round-2 review (C3), where the same shape was handled by rewriting
the narrative twice before the data was allowed to choose it.

---

# Example 3 — The number that was never measured

Shortest, and the easiest to repeat.

## The input

The paper states σ's per-receipt latency. It is a supporting claim — the
verifier is cheap, therefore deployable — and nobody questions it, because a
dynamic program over a few dozen integers obviously *is* fast.

## What was wrong

Nothing had measured it. The figure came from an estimate that entered the paper
as a number and was then rendered, cited and carried into two decks.

## Fork — how would you ever catch it?

**❌ Careless:** read the paper and check the number is plausible. It is. A
subset-sum DP over ~20 amounts in integer cents at sub-millisecond is exactly
what you would expect.

**Why it fails:** plausibility is what an unmeasured number is optimised for. It
was generated by an intuition about the right order of magnitude, so it agrees
with your intuition about the right order of magnitude.

**✅ Correct:** check the *provenance*, not the value. For every number in the
paper, ask: **which generated file does this come from, and which run artifact
does that file come from?**

```bash
# every number must resolve to a generated file
grep -o '\\[a-zA-Z]*' main.tex | sort -u > used
grep -ho '\\renewcommand{\\[a-zA-Z]*}' numbers_*.tex | sort -u > generated
# anything numeric in `used` that is not in `generated` is typed, not measured
```

The fix was two commits, and the second is the one that matters:

- `2b4f929` — *"Replace unbacked sigma latency numbers with real CPU
  measurement"*
- `006db2d` — *"Commit sigma-latency measurement artifact (backs the paper's
  latency numbers)"*

## What the measurement then produced

Not just a number: a *provenance statement*. The caveats deck now carries latency
as one of five named caveats, and what it says is more useful than the value:

> median 4.07 µs, p99 312 µs, max 715 µs, n=819, on x86-64, Python 3.11
> (CPython), single thread — *"a faithful compute reconstruction at the real
> input sizes"*, and the paper states plainly that **the end-to-end ratio was not
> measured on this CPU-only host.**

The claim went from an unbacked number at rung 6 to a measured number at rung 5
with its scope stated. It also got *stronger*: microseconds is a better
argument than the estimate was, and now it can be defended.

## The generalisation

> An unmeasured number is indistinguishable from a measured one at the point of
> reading, and **more** plausible on average, because it was generated by the
> same intuition that judges it. The only defence is provenance: one number, one
> generated file, one committed artifact.

The same shape, three more times in these repos:
`b8e2b57` (three artifacts disagreeing about the same quantity),
`b9edc78` (a pooled row typed rather than computed: 183/186 where the parts sum
to 185/188), and
`d125ba5` (figures printing `n=-217` and `n=None`, because nothing asserted that
a count is a non-negative integer).
