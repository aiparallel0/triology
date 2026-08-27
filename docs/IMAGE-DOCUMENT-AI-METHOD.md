# Image and Document AI Method Handbook

Domain companion to the *Research and Publication Method Handbook*. That
document is field-agnostic. This one holds the rules that only bite when the
input is a document image and the output is a set of extracted fields: corpora
whose labelling regime decides what your method can see, backbones that emit
structurally different objects, an OCR stage whose errors arrive disguised as
your errors, and a class of failure that is silent by construction.

Every rule comes from a concrete mistake or win on a receipt key-information
extraction study taken through review to camera-ready. Examples are given in
domain-neutral form wherever the specific corpus does not matter.

In a hurry: Section 9.

## Contents

```
 1. CORPORA AND LABELLING REGIMES
 2. BACKBONES AND WHAT THEY EMIT
 3. THE UPSTREAM STAGE YOU DID NOT BUILD
 4. CONFIDENCE AND SELECTIVE PREDICTION
 5. EXTERNAL VERIFICATION AS A SIGNAL
 6. EVALUATION ACROSS REGIMES
 7. CLAIMS THIS DOMAIN GETS WRONG
 8. FIGURES AND TABLES FOR THIS DOMAIN
 9. CHECKLISTS
10. THREE-SENTENCE SUMMARY
```

---

## HOUSE RULES (domain additions)

Paste alongside the general house rules.

```
DOMAIN HOUSE RULES
- Name the labelling regime of every corpus in the setup, not just its name.
- Never evaluate on a split the backbone was fine-tuned on. Check which split
  the public checkpoint used.
- A confidence score from a generative decoder and from a token classifier are
  architecture-appropriate analogues, not the same number. Say so.
- Attribute a loss to the OCR stage only with a differential test, never by
  plausibility.
- Report per-corpus first, pooled second, with corpus sizes attached.
- Figures: never colour-only. Hatch the bar that carries the finding.
```

---

# 1. CORPORA AND LABELLING REGIMES

## 1.1 The labelling regime decides what your method can see

Document corpora differ less in content than in **how the ground truth was
recorded**, and that difference determines which methods are even applicable.
Three regimes recur:

| Regime | What you get | What a method can use |
|---|---|---|
| field-labelled | per-field values in structured form | exact values, directly |
| OCR-derived | text lines from an OCR pass, weakly typed | values only after parsing, with OCR noise |
| per-token annotated | tokens tagged with field classes | values by grouping tagged tokens |

A method that reads values from the page behaves differently in each. Report the
regime for every corpus in the experimental setup. A reader who knows only the
corpus names cannot predict your results; a reader who knows the regimes can.

## 1.2 Span the regimes deliberately, not the corpora

Three corpora in the same regime tell you less than two in different regimes.
Choose the corpus set so that the regimes differ, and say that is why they were
chosen. This converts "we used three datasets" from a robustness gesture into a
design decision that supports a generality claim.

## 1.3 The fine-tuning split is inside the benchmark

Public checkpoints are fine-tuned on a named split of the same public corpus you
are about to evaluate on. Evaluating on that split inflates every cell, and an
improvement is the only signal leakage ever gives you.

Before any run: find which split the checkpoint used, exclude it, and state the
exclusion in the setup with the resulting n. Decontamination is not one step.
The number moves, the cached artifacts move, the figures move, and the prose
about the number is the step that most often survives uncorrected.

## 1.4 The canonical split is smaller than the headline number

Corpus papers quote totals. Task splits are smaller, and the "canonical" subset
used by prior work may be smaller again. Quote the n you actually evaluated and
where it came from, and do not let the corpus paper's number stand in for it.

## 1.5 Corpora do not persist what you need

A corpus may not record the per-item property your secondary measurement
requires: an item count, a bounding box, a per-line type. This forces a
measurement subset, which is legitimate and must be declared.

State the subset positively, in the caption where the measurement appears: what
the subset **has**, not what the remainder lacks. A bare smaller n next to a
larger headline n reads as missing data, and a reader will assume the worst
explanation available.

---

# 2. BACKBONES AND WHAT THEY EMIT

## 2.1 Two structurally opposite designs, not two similar ones

The generality claim you can make is a function of how different your backbones
are. The two poles in this domain:

- **generative, OCR-free**: a vision encoder-decoder reads pixels and emits a
  structured document one token at a time;
- **encoder-only**: OCR text with layout coordinates and the page image go in,
  and each token is classified into a field.

Testing across that gap licenses "the result does not depend on the model".
Testing two generative models of similar design does not. Choose the second
system for maximal architectural distance and say why the distance matters.

## 2.2 The output object differs, and so does everything downstream

A generative backbone can hallucinate a well-formed value that never appeared on
the page. A token classifier cannot: it can only mislabel tokens that exist.
These are different failure modes and they need different guards. Do not write a
method section that assumes one and evaluate on both.

## 2.3 Parsed value, not raw text

Anything that consumes a model's output as a value assumes a parsing step that
turns emitted text into a typed quantity. Format variation, currency symbols,
thousands separators, and hallucinated formatting all live in that step.

The normaliser is part of your system whether or not you benchmark it. Say
explicitly that it exists, and say whether you evaluated it. A method that
assumes a clean parsed scalar and never mentions the parser has an unmeasured
dependency in its critical path.

---

# 3. THE UPSTREAM STAGE YOU DID NOT BUILD

## 3.1 OCR errors arrive disguised as your errors

Where the pipeline includes OCR, its failures reach your method as ordinary
input: a digit confusion, a merged line, a phantom value that no human sees on
the page. Your method then fails on that input and the failure is recorded
against your method.

## 3.2 Ambiguity is resolved by carrying candidates, not by guessing

A single OCR line can support more than one reading, and picking one early
throws away the correct interpretation on some fraction of items. Carrying
multiple candidate readings and accepting if **any** candidate succeeds is
usually better, and the average candidate count per item is a statistic worth
reporting: it tells a reader how much ambiguity the corpus actually contains.

Report which extractor configuration produced which result. When an ablation
holds the extractor fixed while the headline uses the multi-candidate version,
their accept sets differ, and a reader comparing the two tables will otherwise
read it as a contradiction.

## 3.3 Attributing a loss to OCR requires a differential test

"Our method underperforms here because the OCR is poor" is the most
self-serving explanation available in this domain. Plausibility is not evidence.

Adequate evidence has two halves. A measurable property that differs between the
failure cases and the success cases **in the direction your explanation
predicts**, with a test. And a second property that your explanation predicts
should **not** differ, shown not to. The second half is what separates an
account from a story, and its absence is visible to any reviewer who looks.

State the strength honestly. With a small number of failures this supports the
account rather than settling it, and naming the study that would settle it is
worth more than an extra adjective.

---

# 4. CONFIDENCE AND SELECTIVE PREDICTION

## 4.1 Silent errors are the expensive mode

In document extraction, the costly failure is not a visible crash or an empty
field. It is a **plausible wrong value** that passes downstream unchallenged.
Frame the problem around that, because it is what motivates abstention over
accuracy, and it is the part a practitioner recognises immediately.

## 4.2 The default signal is a property of the generator

The confidence signal available by default is derived from the model's own
output distribution. That makes the process that produces a confident error the
same process asked to detect it. This is a structural limitation, not a
calibration problem, and saying "structural" rather than "miscalibrated" is what
stops a reviewer asking why you did not simply recalibrate.

## 4.3 Confidence is a different object on each architecture

For a generative decoder it is an aggregate over the probabilities of the
emitted value tokens. For a token classifier it is an aggregate over the
predicted-class probability on the tokens tagged with the field. Both are the
model's self-assessed probability of the thing it emitted, so they are
**architecture-appropriate analogues**.

They are not numerically interchangeable, and pooling them into one distribution
without saying so is a defect a careful reviewer will find. Define both, name
the analogy, and refuse the interchange explicitly.

## 4.4 Coverage is the currency

Any abstention mechanism trades coverage for accuracy. A result that reports the
accuracy gain without the coverage cost is incomplete and reads as marketing.
Report both in the same breath, in the abstract as well as the results, and give
the condition under which the trade pays: the ratio of the cost of an undetected
error to the cost of a human review. Name the regime where it does **not** pay.
That is what makes the rest credible.

---

# 5. EXTERNAL VERIFICATION AS A SIGNAL

## 5.1 The construction

When an extracted field must satisfy a structural constraint computable from
other visible content, a deterministic checker of that constraint is a
selective-prediction signal whose errors are governed by document structure
rather than by the model. Totals that must equal a sum of parts, dates that must
be ordered, quantities that must multiply to a line value, fields that must
match a checksum: all admit the same construction.

The claim is about **where the signal comes from**, not about how well it is
scaled.

## 5.2 Orthogonality is disjoint error, not dominance

Two signals combine usefully when they fail on different documents. Neither has
to beat the other on any aggregate. The strongest evidence is often a corpus
where both signals have *identical* standalone accuracy and the intersection is
still better: that cell looks unremarkable in a table of aggregate scores and is
the most persuasive result you have.

Do not argue dominance when the data show orthogonality. It overclaims, and one
corpus where the other signal wins refutes it.

## 5.3 The witness exists by construction, and "well-formed" carries the clause

On a well-formed document the constraint is satisfiable by definition, which is
what makes the check sound rather than heuristic. Everything depends on
"well-formed". Enumerate what voids it: documents where the parts are not
recoverable, where the constraint holds only approximately, where the upstream
extraction is lossy. That enumeration is the honest boundary of the method.

## 5.4 Guard the degenerate satisfaction, per regime

Every constraint checker admits trivial satisfactions: one part equal to the
whole, an empty subset, an identity. Without a guard the checker accepts them
and its precision is meaningless.

The correct guard setting is **regime-dependent**. Where the field appears as its
own labelled line, the trivial match is a coincidence and must be excluded.
Where an OCR pass surfaces that line as ordinary text, the same match is the
legitimate intended one and excluding it destroys coverage. Do not pick one
setting globally.

## 5.5 Choose the guard without labels

A guard tuned on labelled data cannot be set that way at deployment, and a
reviewer will say so. Choose it from a computable property of the unlabelled
input stream, show the corpora separate cleanly on that property, and show the
choice is insensitive across a range. Then it is a deployment rule rather than a
fitted parameter, and one sentence establishes that.

When you also sweep the setting, label the sweep explicitly as an ablation of
the rule, or it reads as the tuning you just denied.

## 5.6 Compose at a matched operating point

Comparing a threshold-free checker against a thresholded confidence score at an
arbitrary threshold is meaningless. Set the confidence threshold so both accept
the same fraction, and compare accuracy there. Without this, every reported gain
is confounded with a coverage change and the result collapses into "you accepted
fewer documents and were righter about them".

## 5.7 The cost of the check against the cost of the decision

A deterministic check over parsed values is typically orders of magnitude
cheaper than the inference that produced them, which makes latency a non-issue.
State the measurement once, state the comparison once, and state what you did
**not** measure. End-to-end ratio on deployment hardware is usually absent, and
claiming deployability without it overreaches.

## 5.8 Robustness means degrading in the safe direction

For a verifier, the valuable robustness result is not that accuracy is unchanged
under corruption. It is that the failure mode is **conservative**: coverage falls
while accuracy holds, so the check becomes more selective under noise. Design
the stress test to expose the direction of degradation and report the direction,
not just the magnitude. A method that gets quieter under noise is deployable;
one that stays confident is not.

---

# 6. EVALUATION ACROSS REGIMES

## 6.1 Regime dependence is a finding, not an embarrassment

The same signal will win on one regime and lose on another. The temptation is to
average it away. Report the regimes and the mechanism instead: "each signal owns
a regime" is stronger and more useful than a uniform mean, and it tells a
practitioner which to deploy. Averaging destroys exactly the information the
reader needs.

## 6.2 Per-corpus first, pooled second

When corpora are unevenly sized, a pooled figure is dominated by the largest.
It can be honest and still mislead, because readers hear "across all data" and
not "mostly the largest corpus". Put the corpus sizes next to the pooled number,
say which corpus carries it, and make the per-corpus table the headline.

## 6.3 Pooled significance is not per-corpus significance

A pooled test with large combined n clears thresholds no individual corpus
clears. That is power, not a trick, but it is not a per-corpus claim. If the
pool passes and the corpora do not, say exactly that, and say whether the
corpora fail because the effect is absent or because they are underpowered.
Those are different and the distinction is testable.

## 6.4 Small cells license consistency statements only

A corpus where the method accepts a handful of documents can produce a perfect
score with an interval that excludes nothing. Such a cell supports "consistent
with the overall finding" and nothing stronger. Never let it appear in a summary
without its n, and never let it be the sentence a reader remembers.

## 6.5 Two statistics that sound like one

These evaluations produce at least two quantities that plain English conflates:
the **effect** (how much accuracy improves when signals must agree) and the
**mechanism** (how decorrelated their errors are). They can have different
scopes: the effect may reach significance only pooled while the mechanism holds
within every corpus.

Name the quantity in every sentence that states a scope limit. "It does not hold
per corpus" is unreadable and reads as self-contradiction two paragraphs later.

## 6.6 Absence of asymmetry is not evidence of independence

A paired test showing neither signal is systematically better is a null on
asymmetry, routinely misread as positive evidence of independence. If you want
the independence claim, measure error correlation directly within the accepted
set, against a control that holds coverage fixed. Then say which test supports
which claim.

## 6.7 The baseline class that does not exist

The obvious alternatives all read the model's internals, so they share the
property your method exists to avoid, and adding more of them adds no
information about your claim. Say this as a limitation: you compare against one
representative internal signal, the alternatives are the same kind of signal,
and the baseline you would want, a second document-external checker, you know of
none published. Silence on it reads as an omission.

---

# 7. CLAIMS THIS DOMAIN GETS WRONG

## 7.1 Novelty of the technique against novelty of the measurement

Arithmetic and consistency checks over extracted fields are decades-old
engineering practice. Claiming the technique is new is usually false and one
counterexample kills it. Claiming that its **measurement as a signal of a
specific kind** is not in the literature is a lower and defensible rung, because
it is a statement about a specific evaluation.

State the disclaimer once, precisely, in the section where the literature is
discussed. Do not repeat it.

## 7.2 A repeated defence is a symptom

When the same disclaimer appears three or four times, each instance was added
against a separate challenge and the underlying claim was never resolved. Do not
merely delete the copies. Decide whether the evidence supports the claim,
resolve it, and state the resolution once. Deleting duplicates without resolving
the claim leaves the paper undefended in the one place the sentence was needed.

## 7.3 When a reviewer rejects the framing, adopt the framing the evidence supports

A reviewer who rejects the positioning rather than the results is usually right,
because the positioning was chosen before the evidence was in. Re-read what they
say the work *is*. A paper repositioned as an evaluation of a known technique
can be strong; the same paper insisting on methodological novelty it cannot
support is weak exactly where the reviewer is looking.

Separate the claim you must give up from the claim you can still make, and keep
the narrower one intact rather than losing both.

---

# 8. FIGURES AND TABLES FOR THIS DOMAIN

## 8.1 The comparison figure is per-corpus and multi-panel

The natural figure is one panel per corpus, with a bar per signal condition, so
regime dependence is visible at a glance. Put the n on every bar. A reader
cannot judge a precision without it, and the small cells are exactly the ones a
reader will otherwise over-read.

## 8.2 Never colour-only; hatch the bar that carries the finding

The intersection bar is the result. Encode it with hatching and a heavier edge
in addition to colour, so it survives greyscale printing and colour-blind
readers. Bold the annotation on that bar only.

## 8.3 Multi-panel layouts break tick labels before they break anything else

A label that fits at one panel width overlaps at three. Check the rendered
figure at final size, not the plotting window. Reduce the tick font and add pad
before you consider rotating labels or shortening the labels themselves.

## 8.4 Regenerate the figure from the results file

Figures go stale silently when results change. Generate from the same JSON the
tables read, so a re-run updates both. A figure with hardcoded values is a claim
with no provenance, and it will disagree with the table it sits next to.

## 8.5 Check the figure against the table it accompanies

Every value visible in a figure should be traceable to a table cell or the text.
This is the cheapest inconsistency check in the paper and it catches stale
regenerations immediately.

---

# 9. CHECKLISTS

## 9.1 Before the first run

```
[ ] Labelling regime named for every corpus
[ ] Which split the public checkpoint was fine-tuned on, and it is excluded
[ ] n quoted is the n you evaluate, not the corpus paper's total
[ ] Backbones chosen for architectural distance, and that is stated
[ ] The parsing/normalisation step named, and its evaluation status stated
```

## 9.2 Before believing a comparison

```
[ ] Signals compared at matched coverage, not at arbitrary thresholds
[ ] Guard against degenerate satisfaction set per regime, chosen without labels
[ ] Any sweep over that guard labelled explicitly as an ablation
[ ] Extractor configuration recorded per result; differing accept sets explained
[ ] Confidence definitions given per architecture, with interchange refused
```

## 9.3 Before reporting

```
[ ] Per-corpus table is the headline; pooled figure carries its corpus sizes
[ ] Pooled-only significance stated as pooled-only
[ ] Small cells carry their n and claim consistency only
[ ] Effect and mechanism named separately wherever scope is limited
[ ] Coverage cost reported wherever an accuracy gain is reported
[ ] Loss attributed to an upstream stage has a two-sided differential test
[ ] Measurement subsets declared positively, in the caption, with the reason
[ ] The missing baseline class stated as a limitation
```

## 9.4 Before submission

```
[ ] Every figure value traceable to a table cell or the text
[ ] Figures regenerated from the results file, not hand-edited
[ ] No colour-only encoding; the finding bar is hatched
[ ] Tick labels checked at final rendered size
[ ] The novelty disclaimer appears exactly once
```

---

# 10. THREE-SENTENCE SUMMARY

The labelling regime of a document corpus, not its name, decides what a method
can see and which guard settings are correct, so span regimes deliberately and
name them in the setup. The expensive failure in this domain is a plausible
wrong value that passes unchallenged, and the default confidence signal cannot
catch it because the process that produced the error is the process being asked
to detect it, which is why a checker computed from the document rather than the
model is worth measuring. Report per-corpus before pooled, name the effect and
the mechanism separately whenever you limit scope, and state the coverage cost
in the same breath as the accuracy gain.
