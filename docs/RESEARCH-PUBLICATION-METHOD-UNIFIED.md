# Research and Publication Method Handbook

Field-agnostic rules for building, verifying, positioning and publishing an
experimental or computational claim. Every rule comes from a concrete mistake or
win. Examples are given in field-neutral form.

In a hurry: start with the checklists in Section 14, or the ready-to-use prompts
in Sections 21 and 22.

This unified edition merges four sources: the comprehensive method handbook, the condensed lessons edition, a project whose lessons are Sections 24 to 26, and a venue-paper project whose lessons are Section 28. The handbook is the spine; the lessons edition's publication-strategy lessons (Sections 13.11 to 12.13) and its distinctive prompts (Section 21.17) are folded in, broken source tables are repaired, and the prompt-section numbering is corrected. A crosswalk from the condensed edition is in Section 23.

Sections 24 to 26 come from a project in which every serious defect was silent: three separate checks shipped a false pass, a build reported success on failure, a correction notice was over-read and broke a property it never mentioned, and a format conversion had to be proved lossless rather than inspected. They are appended rather than interleaved so that no existing section number moves (Sections 11.8 and 19.11 explain why that matters). Where they overlap an existing lesson they cross-refer to it instead of restating it, per Section 11.15.

Section 28 comes from taking a venue paper through review, revision and camera-ready. It is likewise appended rather than interleaved, and the sections it touches elsewhere are 9.11, 10.16, 11.8, 12.15, 13.7 and 13.8. It reaches Sections 24 and 26 from a different direction: those chapters ask what a check must do to be trusted, while Section 28 asks what the instrument, the rendered artifact and the repository ground each contribute to a claim. Where the two meet, in particular Sections 24.1 and 28.2, 23.4 and 27.3, and 25.3 and 27.3, both statements are kept because each carries its own evidence.

## Contents

```
 1. READING THE SOURCE AND REPRODUCING
 2. REPRODUCTION FIDELITY
 3. EXPERIMENTAL DESIGN
 4. PRE-REGISTRATION AND HONESTY STRUCTURES
 5. MEASUREMENT AND REPORTING
 6. EVIDENCE INTEGRITY: LEAKAGE, POWER AND SCOPE
 7. DEBUGGING
 8. DESIGNING A CRITERION OR CLASSIFIER
 9. LITERATURE AND CLAIM MANAGEMENT
10. SELF-CORRECTION AND FRAMING
11. TEXT AUDITING
12. TOOLING
13. ARTIFACTS AND PUBLICATION
14. CHECKLISTS
15. STYLING AND TYPOGRAPHY
16. BACKGROUND: THE REASONING BEHIND THE RULES
17. PREVENTION, SOURCE LEVELS AND BALANCE
18. DEEP PRINCIPLES
19. FINAL GLEANINGS
20. FIGURE GENERATION ARCHITECTURE
21. READY-TO-USE PROMPTS
22. HOUSE RULES AND SHORT PROMPTS
23. CROSSWALK (CONDENSED EDITION)
24. THE CHECK ITSELF
25. RECEIVING AN EXTERNAL REQUIREMENT
26. DELIVERING THE SAME WORK IN A SECOND FORMAT
27. TEMPLATE CONFORMANCE
28. THE INSTRUMENT, THE ARTIFACT AND THE GROUND
29. SUMMARY
```

---

## HOUSE RULES

Paste this block once at the top of a session. Every prompt in this document refers to it.

```
HOUSE RULES
- No em-dashes anywhere. Use a comma, a colon, parentheses, or two sentences.
- Table and figure captions: label plus a one-line explanation, on ONE line.
  Caption width must not exceed the width of the object it belongs to.
- Plain competent prose. No selling, no hype, no throat-clearing, no adjectives
  doing work that evidence should do. State the result and move on.
- Every number traceable to a script or a source. Mark invented values TODO,
  and check the marker does not render into the artifact.
- Never evaluate on a split the released model or resource was trained on.
  If everything improved at once, ask what started being included.
- Figures: vector only, body font, units on axes, never colour-only encoding
  (add hatch or texture).
- Say what you did not do, and why, rather than leaving it implicit.
- A check is trusted only after the defect it names has been injected and
  the check has been seen to fail on it.
- Verify the artifact, not only the source. Compiling clean is not evidence
  that the content survived.
- Fetch before claiming something does not exist. Exhaustive search of a
  stale copy is exhaustive only of the copy.
```

---

# 1. READING THE SOURCE AND REPRODUCING

## 1.1 A secondary description and a primary definition give different things

When reproducing a method, dataset or system, read its definition from the
**primary source and its formal statement**. Abstracts, introductions,
related-work sections in other papers and figure captions systematically
simplify and sometimes misreport.

**Example:** A method was described in a secondary source as "the parameter comes
only from configuration". The primary source's own definition derived the
parameter from the input data. The reproduction built on the secondary
description behaved entirely differently, and passed every internal consistency
test.

```
for every structural claim : primary source + section/equation/line number
if you cannot show one     : mark the result PROVISIONAL
```

## 1.2 Separate unspecified choices from the actual structure

If the source does not specify a detail (initial value, preprocessing step,
hyperparameter, cutoff), instantiate it reasonably and **say so explicitly**.

```
Unspecified X, Y, Z were instantiated as follows. They are not tied to the
structural components that drive the result; eight independent instantiations
gave the same outcome.
```

## 1.3 Count how many things a quantity depends on

Produce two lists for any central quantity: **influence set** and **free set**.
The free set is where your experimental design has room to move.

**Example:** Three intermediate values were thought to drive a computation. All
three were functions of a single sum, and that sum covered only a quarter of the
inputs. The rest were free. This predicted, in advance, that the work would be
easier than expected, and the prediction was confirmed by measurement (about a
7.5-fold difference).

## 1.4 A step that runs in reverse is evidence about structure

**Example:** A process was defined forward, but its inverse could only run
backward because each step read the next input. The inverse working was proof
that the forward dependency had been implemented correctly.

Use reversibility tests not as "does it work" but as "which structural property
does this confirm".

## 1.5 Simplify the composition

**Example:** A three-round process reduced to a single-round one because all its
layers were of the same mathematical type. The three rounds did not provide the
claimed additional complexity.

Write down the mathematical type of each layer. Composition of same-type layers
is usually the same type.

---

# 2. REPRODUCTION FIDELITY

## 2.1 Published summary statistics do not prove fidelity

**Measured example:** Correct and **incorrect** reproductions of a structure were
compared.

```
version                  summary stat A   summary stat B   discriminating measure
correct version           6.669            99.60%           33.9 units
partial version           6.665            99.72%           33.0 units
wrong version             6.661            99.50%            2.0 units
source reported           7.947            99.49%           -
```

The **wrong** version's statistic B is closest to what the source reported.
Statistic A is identical across all three. Only the third column separates them.

## 2.2 Design the discriminating measurement

The measurement must be a **direct consequence** of the structural property you
claim.

```
claim                                discriminating measurement
"component X operates in a chain"    outputs affected by one input change
"component X operates independently" same measure, expected value 1
"quantity depends on d inputs"       how many DISTINCT inputs change one output
"state Y is unreachable"             in N attempts, was it reached, how often
```

## 2.3 Derive the expected value first

**Example:** The expected value of an avalanche measurement was derived by a
simple probability argument as `2/9 ~ 0.222`; measurement gave `0.236`. The match
was a second independent confirmation.

If derivation and measurement disagree, one is wrong. Do not report until both
are clean.

## 2.4 Build a deliberately wrong control version

**Measured results:**
```
correct vs component removed          33.9 vs 1.0      SEPARATED
correct vs wrong analysis method      eps=0 vs eps=255 SEPARATED
correct vs different component weak   0.236 vs 0.229   DID NOT SEPARATE
```

The third line matters: **each structural property may need its own
discriminator.** One property was not separated by this measurement; a different
test separated it.

## 2.5 The fidelity test does not validate the structure

**Evidence:** In one reproduction the central quantity was modelled wrongly. The
fidelity test passed cleanly and nine independent runs gave exact results.
Reading the primary source later showed the model was wrong. The test was working
perfectly inside a wrong structure.

```
mandatory order, no step skipped:
  1. primary source definition   <- correctness of the structure
  2. internal consistency test   <- the implementation against itself
  3. discriminating measurement  <- fidelity inside the assumed structure
  4. only then a result
```

## 2.6 Two independent verification channels

One quantitative measurement and one structural necessity (reversibility,
conservation, invariance).

---

# 3. EXPERIMENTAL DESIGN

## 3.1 State the access and control model

Say explicitly what you can observe, what you can control, and what is given to
you. The same measurement means different things under different access.

**Evidence:** Two different numbers were reported for one system. Both were
correct but measured under different access models, and the model was never
stated. Readers could not tell which to believe.

## 3.2 Do not build the baseline from extreme values

If your control or baseline sits at saturation, there is no headroom in either
direction and the experiment fails **because of the baseline, not the structure**.

**Example:** A baseline built to satisfy a constraint pushed most values to the
extremes. No condition could be varied in both directions. Switching to mid-range
values made the measurement work perfectly.

## 3.3 Saturation and wraparound effects

If you compensate to hold a sum or mean constant, ensure the compensation point
has room. Saturation or modular wrap **silently** breaks the constraint and the
result looks like a structural finding.

```
choosing a compensation point:
  to increase : value < upper bound
  to decrease : value > lower bound
after compensating: recompute the constraint and verify it (do not let it pass
silently)
```

## 3.4 Compute compensation capacity

```
required_movement <= number_of_compensation_points * (range width)
```

If this does not hold, your design cannot preserve the constraint. If it cannot
be made to hold, that is a **real limit** and is reported as one.

## 3.5 Learn unwanted contributions in a separate phase

```
Phase 1: change only the unwanted components, learn their effect
Phase 2: perform the real intervention, SUBTRACT the phase-1 effect
```

Result: three cases where no component could previously be isolated reached full
decomposition.

## 3.6 Signature-vector matching

Resolve an unknown mapping between two sets using each element's
**which-observations-was-it-active** signature. `N` observations give `2^N`
discriminating power.

## 3.7 A reference element is mis-assigned in its own round

**Evidence:** In one ordering procedure, the element chosen as reference was
positioned wrongly because its own value was measured against a second reference.
64 elements, 60 correct, four wrong. Fix: never assign the references in their
own round.

## 3.8 Cap the brute force

```
residue large : shrink with an all-pairs measurement inside the residue
residue small : brute force plus validation against a known sample
always        : set a hard cap, or it is silently exceeded
```

6 elements is 720 orderings; 12 is 479 million.

## 3.9 Test at small scale first

Small scale sometimes exposes **new** bugs. Test at both ends.

---

# 4. PRE-REGISTRATION AND HONESTY STRUCTURES

## 4.1 Hypothesis and falsification rule before data

**Evidence:** A rule of the form "if H is falsified the large claim opens,
otherwise it does not" was written first. When results arrived the agreement rate
was high and drifting to a stronger statement was easy. The rule prevented it.

## 4.2 Ambiguous pre-registration is resolved conservatively

Take the **less exciting** reading and **report the ambiguity**.

**Evidence:** A hypothesis was written about one condition but intended to cover
two conditions jointly. On the literal reading it was falsified; on the intended
reading it was not. The conservative reading was taken and the ambiguity was
recorded.

**Preventive form:** Instead of "X will not happen", write the triple:
```
which measurement | which threshold | which verdict
```

## 4.3 Fix definitions before searching

**Evidence:** For one search, "counts as qualifying" was fixed in advance, with
an explicit clause that a reference implementation does not count. When the
search came back empty, the urge to loosen the definition appeared. The rule
prevented it.

## 4.4 Two populations: calibration and measurement

```
positive samples -> sensitivity (does it find what you are looking for)
negative samples -> specificity (does it claim what is not there)
```

**Evidence:** A procedure produced results on 16 unknown samples (sensitivity)
and zero false positives on 11 samples with independently known answers
(specificity). With only the first, "the procedure may be over-producing" would
have gone unanswered.

**Where to find the calibration population:** Established systems, standards and
products that use the same mechanism but use it **correctly**.

## 4.5 Two configurations of one system is the strongest data point

**Evidence:** One system, under one configuration flag, was unreachable in one
mode and reachable in 606 attempts in the other (control group 485). The vendor
documented both the risk and the defence.

## 4.6 Write the expected result first

Predict, with reasoning, then run. A prediction holding is independent evidence
of structural understanding.

---

# 5. MEASUREMENT AND REPORTING

## 5.1 Decompose the effect

```
parameter  size      measure A   measure B    B / size
8          256       221         0.5 s        1959
12         4096      221         8.5 s        2071
16         65536     221         112 s        1713
```

Measure A is **completely flat**; measure B scales cleanly. A single number would
have hidden the decomposition.

## 5.2 Separate measurement from extrapolation

If you fit a law from measured points and carry it further, state explicitly
which part is measured and which extrapolated.

## 5.3 "Not measurable" is a result

**Example:** In some cases a comparison could not be made because the required
second sample did not exist. Quantified: **zero** found in 40,000 and in 200,000
attempts. That is not "we failed to measure"; it is the outcome of the first step
of the procedure.

## 5.4 State the scope of the result
```
[ ] which subset was measured
[ ] any excluded cases and why
[ ] are validation samples disjoint from the setup set
[ ] is the result exact or statistical
```

If a subset is excluded, write "complete result (45 of 48)", not "complete
result".

## 5.5 Do not confuse worst case with average case

Guarantees usually bind on the **worst case**. The average is more optimistic and
makes the system look safer.

**Measured example:** On a real corpus the worst-case measure ran 7.3 to 9.5
while the average measure ran 11.5 to 15.7. A gap of 4 to 6 units.

**Honesty note:** The worst case is set by a single extreme element, usually an
unimportant one. Say so, or the number looks more devastating than it is.

## 5.6 Support synthetic measurement with real data

The second measurement closes "this only holds in your construction".

## 5.7 Every hand-written number is a risk

```
quantity    by hand   measured
A           0.0085    0.0073
B           0.0115    0.0106
C           0.0302    0.38     <- wrong direction, STRENGTHENED the claim
```

The last line matters: the hand-written value made the claim **weaker** than the
truth. Errors go both ways.

---

# 6. EVIDENCE INTEGRITY: LEAKAGE, POWER AND SCOPE

Section 5 covers how to report a measurement. This section covers whether the
measurement is contaminated, and whether the claim you attach to it matches the
population it was taken on. Both failures produce numbers that look better than
the truth, which is why neither announces itself.

## 6.1 An improvement is the only signal leakage ever gives you

Public checkpoints are fine-tuned on a named split of the same public corpus you
are about to evaluate on. Evaluate on that split and every cell improves.

There is no diagnostic here beyond suspicion, because contamination never makes
a result worse. A change that improves everything at once deserves the question
"what did I just start including?" before it deserves a paragraph in the results.

Before any run: find which split the released model was trained on, exclude it,
and state the exclusion and the resulting n in the setup. The same applies to
any resource with a train and test structure that someone else prepared: a
pretrained embedding, a cached feature set, an off-the-shelf tokenizer's
vocabulary.

## 6.2 Decontamination is not one step

Removing the contaminated data changes the number. It also changes every
artifact downstream of the number, and those move at different times:

```
[ ] the run itself, re-executed on the clean split
[ ] any cached or intermediate artifact built from the dirty run
[ ] every figure generated from those artifacts
[ ] every derived statistic in secondary analyses
[ ] THE PROSE ABOUT THE NUMBER
```

The last line is the one that escapes. A generated-value pipeline updates every
figure automatically and cannot update a sentence that characterises the value:
"substantially outperforms" survives a re-run that turned it into "matches".
After any decontamination, re-read every sentence that describes a result, not
just the results.

## 6.3 A null claimed without power is not a null

"No significant difference" from a design that could not have detected the
effect is not evidence of absence. It is absence of evidence, and the two are
opposite claims about the world.

Report the minimum effect the design could have detected. If you cannot, say the
result is uninformative about effects smaller than some size and stop there.
This is not pedantry: a null with power is a finding, and a null without power
is a missing experiment described as a finding.

## 6.4 Pooled significance is not per-stratum significance

A pooled test over a large combined n clears thresholds that no individual
stratum clears. That is power working correctly, not a trick. It is also not a
per-stratum claim, and stating it as one is a rung violation.

When the pool passes and the strata do not, say exactly that, and then say
**which** of the two reasons applies:

- the effect is absent in those strata, or
- the strata are underpowered and the result is consistent with the pooled
  effect.

These are different claims and the distinction is testable. Leaving it
unresolved lets a reader choose the flattering reading.

## 6.5 The pool inherits its largest stratum

With unevenly sized strata, a pooled figure is a weighted statement dominated by
the biggest one. It can be entirely honest and still mislead, because a reader
hears "across all data" and not "mostly the largest set".

Put the stratum sizes next to the pooled number and name which stratum carries
it. Where the strata disagree with each other, make the per-stratum table the
headline and the pool the supporting number, not the reverse.

## 6.6 Small cells license consistency statements only

A cell with a handful of observations can produce a perfect score with an
interval that excludes nothing interesting. Such a cell supports "consistent
with the overall finding" and nothing stronger.

Never let a small perfect cell appear in a summary, an abstract or a heading
without its n attached, and never let it be the sentence a reader remembers. The
reader will not go back to the table.

## 6.7 Absence of asymmetry is not evidence of independence

A paired test showing that neither of two methods is systematically better than
the other is a null on asymmetry. It is routinely presented as positive evidence
that the two are independent, which it is not.

If the independence claim is load-bearing, measure it directly: correlation of
errors within a fixed accepted set, tested against a control that holds the
accepted fraction constant so the result cannot be explained by having accepted
fewer cases. Then state which test supports which claim, and keep the asymmetry
null as what it is.

## 6.8 Compare at a matched operating point

Comparing a threshold-free method against a thresholded one at an arbitrary
threshold measures the threshold, not the method. Set the comparison method's
threshold so both select the same fraction, and compare accuracy there.

Without this, any reported gain is confounded with a selectivity change, and the
result reduces to "we kept fewer cases and were righter about them", which is
true of almost any filter. The same applies to any pair of methods whose
operating points can be moved: match first, then compare.

## 6.9 Checklist: before believing your own number

```
[ ] Which split was the released model or resource trained on, and is it excluded
[ ] Did anything improve across the board, and if so what started being included
[ ] After decontamination, was the PROSE about the number re-read
[ ] For any null: what is the minimum detectable effect
[ ] For any pooled claim: do the strata support it, and if not, absent or
    underpowered
[ ] Stratum sizes reported beside the pooled figure
[ ] Every small cell carries its n wherever it appears
[ ] Independence claims backed by a direct correlation test, not by a null
[ ] Methods compared at a matched operating point
```

---

# 7. DEBUGGING

## 7.1 The core distinction

When an experiment does not give the expected result, the default reading must
**not** be "the phenomenon is real".

```
1. ISOLATE the core assumption and measure it alone
2. Test arithmetic, boundary and saturation cases SEPARATELY
3. Only if both are clean, say "the phenomenon is real"
```

**Evidence, no phenomenon:** A procedure failed four times and was read as a
structural obstruction each time. The real causes were saturation and a
degenerate baseline.

**Evidence, real phenomenon:** The same distinction found a genuine limit
elsewhere and quantified it (0 of 256 attempts valid).

## 7.2 Verify components separately

**Evidence:** Two components verified separately (one 16/16, one zero errors)
localised the fault to a single unknown.

## 7.3 Partial success misleads

**Evidence (8/9):** A fix took 0/9 to 8/9. The remaining case was a different
kind of ambiguity and needed a second fix.

**Evidence (8/20):** A validation score of 8/20 was not "partly right": a wrong
candidate happened to give the right answer on some inputs. **The partial rate
carries information about the type of error.**

## 7.4 Remaining candidates: equivalent or merely unseparated

**Equivalent case:** Two candidates were algebraically convertible into each
other and gave the same result on every input. Which one you pick is irrelevant.

**Unseparated case:** In another condition of the same problem, four candidates
appeared. The second pair was **not** equivalent; it simply did not separate
under the eight measurements chosen. Widening to sixteen and validating against a
known sample resolved it.

```
1. DERIVE BY HAND whether equivalence holds
2. if not, widen the measurement set
3. in all cases VALIDATE against a known sample; never take the first candidate
```

## 7.5 Do not mistake a display bug for a finding

**Evidence:** A measurement printed as "1" when "2" was expected. Cause: integer
truncation; the real value was 1.97.

Keep rounding, truncation and formatting separate from measurement. Print the raw
value too.

## 7.6 Iteration count is a diagnostic

More than two iterations on the same target means you should question the
**assumption**, not the method.

**Evidence:** Four attempts failed on one target, all making the same error. The
fifth succeeded because the primary source was read first. Three versions of the
same work sitting in the code archive are the visible evidence of this
diagnostic.

---

# 8. DESIGNING A CRITERION OR CLASSIFIER

## 8.1 Measure, do not infer

**Evidence:** "There is a strong component inside, therefore this property does
not hold" was wrong. The same component carried the property in one usage
(measured 1.00) and not in another (measured 0.695). The question was not "which
component" but **"which usage"**.

## 8.2 A coarse measure misses a fine distinction

**Evidence:** A test did not distinguish a structure depending on one input from
one depending on two; both produced the same coarse value. The separating
quantity was different and invisible unless measured. The coarse test's
classification was wrong.

**Rule:** If your test outputs a number, list **every** structure that can
produce it. More than one means you need a second test.

## 8.3 Measure which step is doing the work

**Evidence:** Across 36 samples, the second step changed the outcome in exactly
**one** case. Everything else was decided by the first step. The second step's
real function was determining cost, not outcome. This changed how the procedure
was presented.

---

# 9. LITERATURE AND CLAIM MANAGEMENT

## 9.1 Broadening narrows, and that is normal

Showing how far a method reaches also shows its limits. As reach grows,
originality narrows.

```
move                      | what narrowed          | what broadened
--------------------------|------------------------|-------------------------
validation next door      | parameter originality  | reach, calibration
reading the primary source| one claim withdrawn    | anchor + new structural finding
literature scan           | priority claim         | independent corroboration
```

The left column is certain and conspicuous; the right requires measurement.
Weigh both.

## 9.2 Does your parameter have a name next door

Search for the **function**, not the name.

**Evidence:** A parameter coincided numerically with a condition defined a decade
earlier in an adjacent field (measured ratios 0.78 to 1.01). Had a reviewer found
it, it would have been a missing citation. Found first, it became a bridge that
enlarged the paper's reach.

## 9.3 Distinguish full from partial overlap

Same quantity, different **consequence**.

**Evidence:** In one field, beating the concept reaches the target directly; in
the other it only opens an intermediate step. Without stating this, the
connection overclaims.

## 9.4 Your class may already have a name

**Evidence:** The class being defined already had an established name, subtypes,
and even a narrative of how it arose.

## 9.5 The field moves fast

Run a targeted six-month scan before submission and post a preprint without
waiting.

## 9.6 An overlapping paper is both a mine and a treasure

It narrows your claim and **strengthens your evidence**. Write both:

```
X et al. independently reached the same conclusion, which is evidence that the
finding is not specific to our construction.
```

## 9.7 One search is not a literature review

---

# 10. SELF-CORRECTION AND FRAMING

## 10.1 Make retractions visible

State, in order: what was claimed, what was found, what survives. The reviewer
will find it anyway; finding it yourself builds trust.

## 10.2 Track the direction of corrections

```
change of rationale -> healthy, the process is working
change of direction -> stop, look at the foundation
```

**Evidence:** Three consecutive corrections arrived: a citation withdrawn, a
hypothesis rationale collapsed, a framing found wrong. All three changed the
rationale; none changed the direction. The decision to continue rested on that.

## 10.3 A collapsed rationale does not collapse the result

**Evidence:** A rationale collapsed under measurement. The result was right but
the reason was different. The new rationale **strengthened** the main thesis.

## 10.4 External feedback questions the framing; internal audit checks consistency

**Observation:** Consistency auditing (numbers, contradictions, missing
citations) can be done systematically. Framing errors (wrong model assumption,
wrong rationale, wrong positioning) almost always surface through an **outside
question**.

**Evidence:** In one project three serious framing errors were all found by
open-ended questions. None would have been caught by a checklist.

**Application:** Have someone make you explain the project periodically.

## 10.5 Put your evidence on axes

**Evidence:** Most of the evidence turned out to sit at the zero point of both
axes. This turned an intuitive objection into a quantitative one (7 of 11) and
showed which cells needed filling.

## 10.6 An empty cell is a finding only after you have searched

Before searching it is an observation. Also state which regions you could not
search.

## 10.7 Distinguish headline from evidence

Countable results are the most easily preempted. Put the headline on the
**method or framing**.

**Test:** If a reviewer can place your results side by side with another paper's
in one table, your headline is in the wrong place.

## 10.8 Turning an empirical result into a theorem is the highest-return move

If your field has a paper saying "X was observed empirically", proving X is
**necessary** is the strongest contribution, and it gives a natural pitch for
that paper's venue.

## 10.9 Caveats that take up space read as defensive

Write each caveat once, where it belongs. Collect them in Limitations rather than
scattering them through the body.

## 10.10 The same phenomenon with two different outcomes is a strong narrative

**Evidence:** The relevant components of two populations were measured and came
out **equally weak**. The separating factor was shown to be a different component
entirely. This became the directly measured form of the main thesis, and was
stronger than a single-population narrative.

---

## 10.11 A review is written against a build, and framing can be conceded narrowly

Two habits belong with self-correction. First, a review, critique or task list
is written against a specific build; verify each reported defect against the
current artifact before acting, and report which were already resolved. Acting
blind on a stale list re-introduces work and can undo the fix that resolved the
complaint. Section 28.17 gives the procedure.

Second, when a reviewer rejects the paper's framing rather than its results, the
instinct is to defend the framing. That is usually wrong, because the framing
was chosen before the evidence was in. Re-read what the reviewer says the work
*is*, and where that fits the evidence better than your description, adopt it in
their vocabulary. Separate the claim you must give up from the claim you can
still make, and keep the narrower one intact rather than losing both. The
results do not change; only the sentence describing them does.

A repeated defence is a diagnostic. When the same disclaimer appears three or
four times, each instance was added against a separate challenge and the
underlying claim was never resolved. Do not merely delete the copies: decide
whether the evidence supports the claim, resolve it, and state the resolution
once in the section that owns it.

# 11. TEXT AUDITING

## 11.1 Number consistency across all surfaces
```
- abstract says "ten results", body says "second result", elsewhere "the count
  stays at one"
- section heading says "eight X", the table shows fourteen attempts
- figure caption says 66.5%, the text says 23.6% (same quantity)
- sample count appears as 18, 21, 24 and 25 in four different places
```

## 11.2 Headings do arithmetic too

"Eight X" plus two previously reported made ten, but the reader had to do the sum
themselves. The correct phrasing was "eight **further** X".

## 11.3 Figures go stale when results change

A contradiction between text and figure is the first thing a reviewer catches.

## 11.4 Find unreferenced figures

**Evidence:** In one audit, ten of fifteen figures were unreferenced; five were
safely removed and a full page was recovered.

## 11.5 Account for escape characters when searching

**Evidence:** Names containing underscores were written escaped in the source. A
plain search returned **zero** and led to the conclusion "no citations exist". In
reality there were ten. A false gap report was nearly written.

If a critical search returns zero, retry with the escaped variant and confirm one
instance by eye in the raw file.

## 11.6 Never use greedy regex on markup

**Evidence:** A regex written to remove five blocks deleted everything between
two of them. The document went from 30 pages to 7 with 50 broken references.

```
1. find the START and END LINE numbers of the target
2. delete the line range (bottom up)
3. run a structural integrity check after every deletion
```

## 11.7 Restore from a known-good copy

Do not try to repair a destructive edit. Restore and redo with the correct
method.

## 11.8 Not whether a reference is valid but whether it points to the right place

If you have renumbered a document, internal references being **numerically
valid** is not enough. The number can exist and still point at the wrong section.

**Measured example:** In a document renumbered three times, an automated check
reported "no invalid references", because every reference number matched an
existing section. A semantic check found three errors: the introduction said
"prompts are in Section 13" but Section 13 was now something else and the prompts
had moved to 15.

```
numeric check  : does the reference number exist       -> insufficient
semantic check : does the reference point at the right -> required
                 target
```

**Application:** For every internal reference, print the target heading and
compare it with the sentence containing the reference. This is a small enough
list to check by eye.

> **Prompt:** For every internal reference in this document, print the target
> heading and compare it with the sentence containing the reference. List the
> ones that are numerically valid but semantically wrong.

## 11.9 Structural integrity check
```
[ ] broken references (citation exists, target does not)
[ ] environment or tag balance
[ ] duplicated paragraph
[ ] missing macro or broken encoding
[ ] build error and warning counts
```

## 11.10 Clean run from the delivered package

Building in your working directory is not enough. Unpack the **delivered
archive** and run from scratch. Missing dependencies only show up there.

## 11.11 Take the revision diary out of the body

"In an earlier draft", "this took three attempts", "this cost us a run" read as
defensive. Write results in the present tense; put the history in the cover
letter.

**Exception:** A withdrawn claim stays visible. The difference: a retraction is a
**result**, not a process narrative.

## 11.12 Remove intent-attributing language

"Silently omits", "hides", "avoids" become the observation: "does not report".

## 11.13 Count your repeated formulations

A phrase appearing three times is unnecessary in two of them.

---

## 11.14 A table of contents is navigation protection

In a long document a table of contents is not only convenience, it is
**protection against number drift**. Generated automatically from the file, it
updates itself when a section is added, and the problem of a hand-maintained list
going stale disappears.

```python
heads = re.findall(r'^# (\d+)\. (.+)$', s, re.M)
toc = '```\n' + '\n'.join(f'{n:>2}. {t}' for n, t in heads) + '\n```'
```

Same principle: a hand-written table of contents violates the single source
principle.

> **Prompt:** Does this document have a table of contents, is it generated from
> the file or maintained by hand? If by hand, does it match the section headings?

## 11.15 Hunting conceptual duplication

The same lesson may be written twice in two different sections, and because the
headings differ a heading-level audit will not catch it.

**Measured example:** In one document "consistency is cheaper than correctness"
and "what passes internal consistency can still be wrong" stood in two separate
sections. The second one even admitted "it appears in this handbook under several
names", which is not a solution.

**The fix is not deletion but sharpening the distinction:** let one say **why**
this happens and the other say **what to do**, and have the second cross-refer to
the first.

```
concept-level scan: extract each lesson's key phrase,
                    flag two headings falling on the same concept
```

> **Prompt:** Is the same lesson taught in two different sections of this
> document? Scan at concept level, not heading level. If you find one, do not
> delete; separate them into "why" and "what to do" and add a cross-reference.

## 11.16 Audit the rendered artifact, not only the source

Every rule in this section operates on the source. A further class of defect
exists only after rendering: overlapping text, a block outside its region, a
sentence split across a column, an element silently dropped, a marker that was
meant for the authors printing inside a reference because the bibliography style
renders the field it was hidden in.

Extract the rendered text and geometry programmatically and check it. Two
specific traps. An unescaped metacharacter can discard the rest of a region
while the build reports success, so verify that the *last* sentence of each
region reached the page, not the first. And a fit measurement taken while layout
defects are present is not a measurement of the fixed document: repair first,
then measure. Section 28.6 to 27.9 covers the family.

# 12. TOOLING

## 12.1 Verify the environment first

Check that a library or tool exists, and its version, before designing around it.

## 12.2 Do not trust shell expansion

**Evidence:** A multi-directory creation command produced a single literal
directory and every subsequent copy went silently into empty folders. It was only
noticed when a file count came back zero.

**Rule:** Always print a file count after copying.

## 12.3 Output encoding

Content extracted from source documents can contain invalid bytes. Put a cleaning
step in the pipeline, and validate encoding after any edit.

## 12.4 Chunk long-running jobs

**Evidence:** A matrix experiment timed out. Running a single cell first,
verifying, then running the whole matrix worked.

## 12.5 Write intermediate results to disk

Write every experiment result to a structured file. When writing the text, read
from the file, not from memory.

---

## 12.6 Extracting structure from a source: the operation

If the primary source is a PDF, reading the structure is a search task and it has
an order.

```
1. convert to text, PRESERVING LAYOUT
     pdftotext -layout source.pdf s.txt
   without layout, tables and equations scramble and indices shift
2. find the section carrying the structure first, do not read the whole text
     grep -n 'Step 1\|Algorithm\|Equation' s.txt
3. extract equation numbers and their surroundings
     awk 'NR>=START && NR<=END' s.txt
4. search for how the critical quantity is computed
     grep -niE 'sum of|seed|initial|derived from' s.txt
```

**Two traps:** Extracted text contains invalid bytes, so put a cleaning step such
as `tr -cd '\11\12\15\40-\176'` in the pipeline. And if a search comes back
empty, try the escaped variant or one split by a line break.

**Measured example:** In one source, the definition of the quantity driving the
permutation was not in the section the prose description pointed to but three
sections later, in the shuffling step. `grep -n 'sum of'` found it in one line;
reading cover to cover would have taken half a day.

> **Prompt:** Convert this source to text preserving layout, search for the
> section carrying the structure, and find which equation defines the central
> quantity. Do not read the whole text, search it.

## 12.7 A session can close: the handoff document

Long work outlasts one session. Without a handoff document the next session
starts from zero and repeats the same mistakes.

```
[ ] where to start (which file to read first)
[ ] which folder produced which result
[ ] the dependency note (which module imports what, what goes on the path)
[ ] three or four commands that reproduce the headline results
[ ] next tasks, with the mandatory ones marked
[ ] caveats that do NOT close, stated as such
[ ] the corrections made in this session (so the same error is not repeated)
```

The last two are the most often skipped and the most expensive. If unclosed
caveats are not written down the next session assumes they closed; if the
corrections are not written down the same wrong model gets rebuilt.

> **Prompt:** Write a handoff document for this project: where to start, the
> dependency note, four commands, next tasks, caveats that do not close, and the
> corrections made in this session.

## 12.8 The checker is code, and the ground is not stable

Two additions to environment discipline, both expanded in Section 28.

The instrument can be wrong in ways that look exactly like passing. Before
trusting a check, inject the defect it names and confirm it fails, then confirm
it passes on known-good input; a check only ever run on good input has been
tested in the direction that proves nothing. Give every check three exit states,
never two, so could-not-run is distinguishable from pass.

The repository and toolchain move without announcing it. Verify tree identity
before the first edit of a session and after any interruption, since a branch
pointer can be reset while the branch name stays the same. Fetch before
asserting that something does not exist anywhere, because exhaustive search of a
stale clone is exhaustive only of the clone. Explore on disposable copies, and
when exploration has already mutated the source, reset and reapply once rather
than patching forward.

# 13. ARTIFACTS AND PUBLICATION

## 13.1 Artifact rules
```
- one random seed, identical in every script
- the result-producing path must not depend on special hardware
- every number produced by a script
- for every claim, name the script that produced it
- ship a dependency note
- clean-run test from the delivered archive
```

## 13.2 Package layout
```
FINDINGS.md          one main document
code-<step>/         each experiment in its own folder with its result file
reports/             interim reports, retractions, pre-registration
README.md            which folder produced which result, quick commands
```

## 13.3 Do not split a paper whose halves validate each other

```
"the experiments calibrate the method, the method frames the experiments" -> do not split
"two independent contributions, no shared dataset"                        -> can split
```

**Extra problem:** In simultaneous submission mutual citation **does not work**.
Citing an unpublished manuscript is weak, and if one is rejected the other is
unsupported.

## 13.4 Correct splitting is sequential

First paper published, second cites it, and the second needs **new work** (new
data, new domain, generalisation). Otherwise it is salami.

## 13.5 Venue is chosen by target audience

**Question:** who needs to read this? A paper criticising a practice should go
where the community practising it reads. A higher-impact but differently-audienced
venue reaches people who already know.

## 13.6 Length is solved by cutting, not splitting
```
- empirical demonstration of a proved result (should be short)
- many sub-experiments from one family (three in the body, rest in an appendix)
- theoretical frameworks used in no result
- intent-attributing language and the revision diary
- unreferenced figures
```

## 13.7 Preprint for priority, not splitting

A preprint is free, fixes the date, and most journals allow it.

## 13.8 The open-access decision starts with your institution

Publishers now personalise the fee by country, institution and membership.

```
1. check your institution's agreement (this usually decides it)
2. if not covered, do not pay
3. but post the preprint regardless
```

## 13.9 Declare conflicts in the cover letter

If your venue published one of the works you criticise, say so politely. It is
not an obstacle, but the editor should know in advance.

## 13.10 Check the mechanics of advice you are given

**Evidence:** One piece of advice held that two papers would strengthen each
other by mutual citation. In simultaneous submission neither would be published
yet, so the mechanism did not work and the advice's main benefit vanished. The
advice was reasonable in content and broken in mechanism.

## 13.11 Major revision is a conditional yes

| decision | meaning | action |
|---|---|---|
| reject | not suitable for this venue | submit elsewhere |
| major revision | serious corrections needed | fix, resubmit |
| minor revision | small corrections | fix, editor checks |
| accept | rare, usually after minor |  |

Typical requests in a major revision: run or strengthen an experiment; clarify
the difference from concurrent work; shorten; read a source more carefully.

> Prompt: If a major revision decision arrives, check whether the typical requests
> (strengthen experiment, clarify concurrent difference, shorten, read source) can
> be met in advance.

## 13.12 Wait for the reviewer data

Postpone irreversible decisions (splitting, changing venue) until reviewer
feedback arrives. The reviewer gives you free information. If it says too long,
you split with a mandate; if it accepts, you go to the second venue with a
published citation; if it says run on the authors' code, you do that in revision.

> Prompt: Check whether irreversible decisions (splitting, changing venue) are
> postponed until reviewer data arrives. The reviewer gives free information.

## 13.13 Journal metrics

| metric | what it says |
|---|---|
| CiteScore / IF | impact (4+ good, 8+ very good, 13+ top) |
| first decision time | desk reject or accept (3 days = fast) |
| decision after review | review time (60 to 90 days = normal) |
| submission to acceptance | including revision (150 to 180 days = normal) |

If first decision is three days, it either goes straight to review or is a desk
reject. For an original research paper a direct accept in three days effectively
does not happen.

> Prompt: Interpret the target journal's metrics (IF, first-decision time,
> acceptance time). A three-day first decision means desk reject or fast review;
> is the strategy set accordingly?

---

## 13.14 Shift the weight instead of rewriting

Venue selection (12.5) says pick the audience. This is the move after that:
instead of rewriting the same paper for a different venue, SHIFT its weight.

```
Venue A: "here is our finding, with a framework behind it"  (finding headline)
Venue B: "here is our framework, calibrated by these findings" (framework headline)
```

The second framing is immune to concurrent finding work: others produce
findings, you provide the tool. The same evidence base serves both; only the
headline moves. This is why the split decision (12.3, 12.4) can be deferred: you
do not need two papers to reach two audiences, you need two framings of one.

> **Prompt:** If this paper could go to two venue types, can its weight be shifted
> rather than the paper rewritten: finding as headline for one, framework as
> headline for the other? Is the framework framing immune to concurrent work?

## 13.15 A fixed size makes every addition a trade

A page limit converts every improvement into an exchange. Reviewers ask for
additions, each reasonable, together unaffordable, and the reflex is to cut
something the reviewers liked.

Check first whether the requested content already exists unmarked. Much of what
reviewers ask for is present and merely invisible, sitting inside a sentence
that does not announce it; folding the answer into that sentence recovers most
of the length at no cost to content. A request is frequently a visibility defect
rather than a content defect, and the two have entirely different prices.

When budget binds, enumerate candidate fixes and measure each rather than taking
the first that works: two remedies for one defect can differ by a whole page,
and the expensive one is often the obvious one. Treat layout as a search with
the renderer as oracle, not as a deduction from its rules. Sections 28.13 to
27.15.

# 14. CHECKLISTS

## 14.1 Before reproducing
```
[ ] primary source in hand (not a secondary description)
[ ] which formal statement defines the central quantity
[ ] which inputs it depends on (influence set and free set counted)
[ ] unspecified choices listed
[ ] which direction reversibility runs
```

## 14.2 Before the main experiment
```
[ ] internal consistency test passes
[ ] expected value of the discriminating measure DERIVED analytically
[ ] a deliberately wrong control version built, and the measure separated them
[ ] baseline condition not at saturation
[ ] compensation capacity computed
[ ] constraint verified after every intervention
[ ] access and control model written down
[ ] pre-registration written (hypothesis, threshold, falsification rule)
```

## 14.3 When the experiment gives an unexpected result
```
[ ] core assumption isolated and measured
[ ] saturation and boundary cases checked
[ ] baseline not degenerate
[ ] components compared against ground truth separately
[ ] tested at small scale
[ ] partial success not read as "almost there"
[ ] equivalence of remaining candidates derived by hand
[ ] display artefacts (rounding, truncation) ruled out
[ ] more than two iterations means the assumption is questioned
```

## 14.4 Before reporting
```
[ ] fidelity measurement done and its value is in the report
[ ] effect decomposed into components
[ ] access model stated
[ ] scope of the result stated, including exclusions
[ ] primary-source anchor exists, otherwise result is PROVISIONAL
[ ] no hand-written numbers remain
[ ] measurement separated from extrapolation
[ ] worst case versus average case stated
```

## 14.5 Text audit
```
[ ] all occurrences of every number counted and consistent
[ ] numbers in headings consistent with the totals
[ ] figures show current results
[ ] unreferenced figures identified
[ ] escape characters accounted for in searches
[ ] block deletion done by line range
[ ] structural integrity check after every edit
[ ] clean run from the delivered package
[ ] revision diary removed from the body
[ ] intent-attributing language removed
```

## 14.6 Before submission
```
[ ] central concept searched for by name in adjacent fields
[ ] six-month scan done, overlapping work cited
[ ] existing name of the class searched
[ ] retractions in a visible section
[ ] caveats that do not close in a separate list
[ ] headline on the method, countable results as evidence
[ ] preprint posted
[ ] artifact package ready with dependency note
[ ] conflict of interest declared in the cover letter
```

---

## 14.7 Before trusting a check

```
[ ] Does it assert a property, or the workaround that currently satisfies it?
[ ] What does it print when the thing it inspects is absent?
[ ] Has the defect been injected and the check confirmed to FAIL on it?
[ ] Does it pass on known-good input, with no false alarms a reader would learn
    to ignore?
[ ] Three exit states: pass, fail, could-not-run. Is a skip recorded as
    unverified rather than counted as a pass?
[ ] If a decision reversed, was the check inverted rather than deleted?
```

## 14.8 Before believing the artifact is correct

```
[ ] Built from the delivered package, in a clean directory, not the working tree
[ ] Rendered text and geometry extracted and checked, not only the source
[ ] Last sentence of each region confirmed present on the page
[ ] Every literal number traced to its generator; no hardcoded twins
[ ] No author-facing marker (TODO, VERIFY, placeholder) reaches the output
[ ] Fit measured only AFTER structural defects were repaired
[ ] Tree identity verified: right branch, right commit, no unfetched remote work
```

# 15. STYLING AND TYPOGRAPHY

## 15.1 Dashes

Do not use em-dashes. Use a comma, a colon, parentheses, or split into two
sentences. An em-dash usually hides a weak sentence structure; removing it either
fixes the sentence or reveals it should have been two.

```
en-dash : ranges only        7-10 units, pp. 20-30
hyphen  : compounds only     pre-registration, worst-case
```

## 15.2 Caption width equals object width

A caption must not exceed the width of the object it belongs to. A caption
spanning the page above a narrow table looks asymmetric and destroys the reader's
sense of where the object ends.

```latex
\usepackage{caption}
\newsavebox\tblbox

\begin{table}[t]
  \centering
  \sbox\tblbox{%
    \begin{tabular}{lrr}
      \toprule
      condition & count & measure \\
      \midrule
      A & 221 & 0.236 \\
      B & 131 & 0.014 \\
      \bottomrule
    \end{tabular}}
  \captionsetup{width=\wd\tblbox}
  \caption{Recovery cost.}
  \usebox\tblbox
\end{table}
```

For figures:
```latex
\begin{figure}[t]
  \centering
  \includegraphics[width=0.62\linewidth]{figure.pdf}
  \captionsetup{width=0.62\linewidth}
  \caption{The plane defined by the two axes.}
\end{figure}
```

## 15.3 Captions must be one line

A caption is an **index entry**, not an explanation.

```
measurement conditions (seed, size, cores) -> table note
interpretation                             -> body text
abbreviation expansions                    -> table note
column definitions                         -> column header or table note
```

```
bad  : Table 3: Results for three conditions using the two-phase design; counts
       are for n=48 with seed 20260815 on a single core, and the measure was
       taken over all positions.
good : Table 3: Results for the two-phase design.
       [table note] n=48, seed 20260815, single core. Measure over all positions.
```

## 15.4 Use table notes

```latex
\usepackage{threeparttable}

\begin{table}[t]
\centering
\begin{threeparttable}
\caption{Results for the two-phase design.}
\begin{tabular}{lrr}
  \toprule
  condition & count & measure\tnote{a} \\
  \midrule
  A & 221 & 0.236 \\
  B & 131 & 0.014 \\
  \bottomrule
\end{tabular}
\begin{tablenotes}[flushleft]\footnotesize
  \item[a] Over all positions. $n=48$, seed 20260815, single core.
\end{tablenotes}
\end{threeparttable}
\end{table}
```

## 15.5 Number formatting
```
[ ] fixed number of decimals within a column
[ ] numbers aligned on the decimal point
[ ] consistent thousands separator
[ ] no more digits than the measurement supports
[ ] do not mix percentages and fractions in one table
[ ] leading zero kept: 0.236
```

```latex
\usepackage{siunitx}
\begin{tabular}{l S[table-format=4.0] S[table-format=1.3]}
  \toprule
  condition & {count} & {measure} \\
  \midrule
  A & 1786 & 0.236 \\
  B &  221 & 0.014 \\
  \bottomrule
\end{tabular}
```

Writing `0.2361` for a mean over forty trials claims a precision you did not
measure.

## 15.6 Table rules
```
[ ] use booktabs: toprule, midrule, bottomrule
[ ] NO vertical rules
[ ] no double horizontal rules
[ ] no rule on every row
[ ] if a column is constant across all rows, DELETE it and say so in the caption
```

## 15.7 Figures
```
[ ] same font family as body text, similar size
[ ] units on axis labels
[ ] NO colour-only encoding (add pattern, marker or position)
[ ] vector format, not raster
[ ] do not repeat the caption inside the figure
[ ] no gratuitous grid, frame or shadow
[ ] legend does not cover the figure
```

## 15.8 Cross-references
```
[ ] every table and figure referenced AT LEAST ONCE
[ ] the reference comes BEFORE the object
[ ] "Table 1" and "Figure 2" style consistent
[ ] unreferenced object: add a reference or delete the object
```

## 15.9 Symbols and notation
```
[ ] every symbol defined at first use
[ ] symbol table if more than ten symbols
[ ] no symbol with two meanings
[ ] the same quantity always gets the same symbol
[ ] symbols in text set in math mode
```

## 15.10 Emphasis and lists
```
[ ] do not bold a whole sentence
[ ] emphasis sparingly, at most one phrase per sentence
[ ] bulleted lists only for actual lists
[ ] a list shorter than three items becomes a sentence
```

## 15.11 Section headings
```
[ ] if a heading contains a number, the arithmetic must hold
[ ] headings are noun phrases, not sentences
[ ] headings at the same level share a grammatical pattern
```

## 15.12 Spacing and placement
```
[ ] table or figure appears at or after its first reference
[ ] do not force float placement
[ ] check for widows and orphans
[ ] consistent space before and after equations
```

---

# 16. BACKGROUND: THE REASONING BEHIND THE RULES

Earlier sections say what to do. This one says **why**. A rationale travels
better than a rule: a rule may not fit a new situation, but the rationale tells
you what to do in it.

These were extracted from choices **enacted but never written down**: what was
asked for, what was corrected, what was emphasised repeatedly.

## 16.1 The reader's scarce resource is working memory

| rule | rationale |
|---|---|
| caption width equals object width | the caption is **bound** to the object; a wider one claims territory it does not own and the eye loses the object's edge |
| caption one line | a caption is an **index entry**; a second line means the author is explaining in the wrong place |
| decimal alignment | readers compare magnitudes by scanning **vertically**; misalignment forces digit-by-digit reading |
| symbol defined at first use | an undefined symbol forces a jump back, and the return point must also be held |
| sparing emphasis | every emphasis is a priority claim; if everything is emphasised nothing is |
| no vertical rules | a vertical rule encodes a grouping that **column order** should already encode; needing one means the ordering is wrong |

If you forget a formatting rule, ask what it costs the reader's memory. The
answer usually regenerates the rule.

## 16.2 A table shows variation, not facts

A column constant across all rows carries no variation; it is a fact, and facts
belong in prose. A one-row table is a sentence.

**Applied to figures:** A figure shows a relation text cannot. Test: delete it
and write two sentences; if something is lost, keep it.

## 16.3 Evidence comes after the claim

Readers build their model **linearly**. Evidence before the claim forces
re-reading.

**At paper scale:** method before results, calibration before measurement.
Presenting results validated by an instrument without first showing the
instrument was validated is the same error.

## 16.4 A precision claim is a claim

`0.2361` asserts a four-digit measurement. From forty trials that is false.

**Extended:** "we showed", "we proved", "for the first time" are precision claims
and must be audited like numbers.

## 16.5 A description is a lossy compression in the describer's direction

A secondary description keeps what interested the describer and discards the
rest. The discarded part may be exactly what you need. This is the real reason
for the primary-source rule: compression is **directed**, not careless.

## 16.6 Consistency is cheaper than correctness, and your test finds consistency

A wrong model can be internally consistent and pass every internal test.
Correctness needs an external anchor; consistency does not.

**Measured consequence:** One reproduction modelled the central quantity wrongly.
The fidelity test passed and nine runs gave exact results. The model was wrong.

## 16.7 From the inside, the temptation is invisible

The urge to widen the frame after results arrive feels like **a reasonable
reading**. You do not feel biased. That is why the decision must move to a time
when the bias cannot form.

## 16.8 Closure is provisional

A finding in one area can invalidate the **rationale** of a conclusion in
another.

**Measured example:** A structural finding cast doubt on a hypothesis closed much
earlier in a different section. On re-examination the rationale was indeed wrong,
and the correct rationale strengthened the main thesis.

## 16.9 A claim is its artifact

Prose is a pointer to a number. If the number is not producible there is no
claim, only a sentence.

**Why so strict:** In one measured case the hand-written value made the claim
**weaker** than the truth. Errors go both ways.

## 16.10 Epistemic verbs are load-bearing

**Measured example:** A parameter was described as "discovered twice". The truth:
discovered once, **rebuilt without noticing** once. You do not discover what you
did not notice.

```
discover : named it, wrote the condition, proved it
rebuild  : produced the structure but did not see the condition
bridge   : showed the two fields have the same quantity
```

## 16.11 The learning sequence is part of the result

Readers want to know **how you learned it**. Silent restatement invites "what
else was quietly corrected".

**Keep the distinction:** a retraction is a **result**; process narration is not.

## 16.12 Process narration shifts the frame

When a text narrates its own production, the reader's question shifts from "is
this true" to "how hard did they work". The second invites the wrong scrutiny.

## 16.13 Ambition is constrained by rule, not lowered

**Measured example:** The widest claim was set as a target and the opening
condition written before data. The condition was not met, the claim was not made,
but setting the target directed the search and produced a narrower earned claim.

## 16.14 Open items are a search space, not a debt

**Measured example:** Three unclosed items were scanned with "is there anything
here" in mind. One produced a literature collision, one independent
corroboration, one confirmed originality. All three had been filed as debt.

## 16.15 Small operational failures recur

Conceptual errors are project-specific. Operational errors (encoding, escape
characters, shell expansion, display truncation) recur in **every** project,
because the tools are the same. Recording them has a higher return.

## 16.16 Consolidation comes before extension

**Measured example:** The corrections produced late were worth more than the
countable results produced early, because the countable results partly overlapped
an independent paper.

## 16.17 A rule applied to one artifact applies to all

Applying a rule to only one document implies it does not hold in the second.
Readers read the implication as inconsistency.

## 16.18 A rule applies retroactively as well

When you introduce a new formatting rule, artifacts written **before** the rule
are in scope too. Applying it only to new content implies the rule does not hold
in the old content, and readers read that implication as inconsistency.

**Measured example:** A project adopted "no em-dashes anywhere" and new documents
followed it. An audit found 439 em-dashes across twenty-four reports written
before the rule. All were cleaned in one pass.

```
when a rule is introduced:
  [ ] new content complies
  [ ] EXISTING content scanned
  [ ] any exception has its reason written down
```

> **Prompt:** Have the formatting rules adopted later in this project been
> applied to all existing artifacts, or only to new content? Scan the files
> written before the rule.

## 16.19 How to extract implicit rules

```
implicit rules show up in three places:
  1. what was specifically asked for  -> what counted as important
  2. what was asked to be corrected   -> which error was not tolerated
  3. what was emphasised repeatedly   -> which principle is load-bearing

method:
  1. list every correction request
  2. for each, ask which general principle it is a special case of
  3. group requests mapping to the same principle
  4. write the RATIONALE per group, not the rule
  5. list the derived rules underneath
```

Write rationales because a rule may not fit an unencountered situation while a
rationale tells you what to do there.

---

## 16.20 Summary: eighteen reasons, one line each

The TR handbook closes this section with a one line summary of every reason. The
EN handbook lacks it. Same table, in English.

```
reader's memory is scarce        -> most formatting rules come from here
a table shows variation          -> drop constant columns and needless figures
evidence comes after the claim   -> placement and section order
a precision claim is a claim     -> significant digits and qualifier audit
description is directional        -> the primary source anchor
consistency is cheaper           -> the fidelity test alone is not enough
from inside the temptation hides  -> pre-registration and the conservative fix
closure is provisional           -> rescan after a new finding
a claim is its artifact          -> every number from a script
epistemic verbs are load-bearing -> discover/reconstruct/bridge distinction
learning order is part of result -> a visible retraction
process narration shifts frame   -> the revision log goes outside
ambition is bounded by rule      -> keep the target high, write the condition first
open items are a search space    -> scan with an "is there anything here" eye
small failures recur             -> record the operational error too
consolidation before extension   -> track the marginal return
a rule applies to all            -> if there is an exception, write its reason
implicit rules can be extracted  -> scan requests, corrections, and repetition
```

# 17. PREVENTION, SOURCE LEVELS AND BALANCE

Earlier sections describe how to **catch** errors. This one describes how to
**stop most of them forming**. Each lesson carries a prompt you can use directly.

## 17.1 Make every repeated number a variable

Prevent rather than audit. If a number appears in the abstract, introduction,
a table and the conclusion, all four must feed from one source.

```latex
\newcommand{\nResult}{sixteen}
\newcommand{\nResultN}{16}
```

Change the number in one place. A number kept in sync by hand eventually drifts,
and it usually drifts in the most visible place.

> **Prompt:** Is every repeated number in this paper a macro? Is the same number
> hardcoded in several places, or fed from a single source?

## 17.2 Assert your arithmetic relations

If your numbers stand in a relation (A + B + C = D), check it **automatically**
after every change.

```python
assert int(a) + int(b) + int(c) == int(d), "counts disagree"
```

This catches the whole family of "sixteen recoveries, three failures, fourteen
attempts" contradictions.

> **Prompt:** Check the arithmetic relations between numbers in this paper
> (A+B+C=D). Is it automatically verifiable after each change, and is it
> currently consistent?

## 17.3 Residue scanning with normalised search

After a major change, search for stale expressions. Line breaks defeat a naive
search, so use a **whitespace-insensitive** one.

```python
s = ' '.join(tex.split())            # normalise
assert s.count("not recovered") == expected
assert s.count("out of class") == expected
```

> **Prompt:** Have stale expressions (changed verdicts, "not recovered") been
> cleaned from this paper? Scan for residues with a normalised search.

## 17.4 Table edits break in a chain

Adding a row or column breaks more than it appears to.

```
[ ] column count in the header row
[ ] multicolumn widths
[ ] column count in footnote rows
[ ] special characters (\&) colliding with the real column separator
[ ] cross references in other tables
[ ] macro counts
```

**Less fragile alternative:** add the information as a footnote instead of a
column.

> **Prompt:** Audit the chain effect of table changes in this paper: column
> count, multicolumn widths, footnote consistency, special character collision,
> cross references.

## 17.5 The level scale of a source citation

The **level** of what you took from the source sets the strength of your claim.
This is graded, not binary.

| level | example | reliability |
|---|---|---|
| equation or formula | "Eq. 14: f(x) = ..." | highest |
| algorithm step | "Step 5: d_i selects ..." | high |
| section reference | "Section 2.5 uses ..." | medium |
| description | "the paper says it uses ..." | lowest |

A description-level reading makes the verdict **provisional**. An equation makes
it definite. Keep claim strength proportional to source level.

> **Prompt:** Check the level of source citations in this paper (equation, step,
> section, description). Are description-level readings marked provisional, and
> is claim strength proportional to source level?

## 17.6 Reading errors are unidirectional

When you misread a complex system, the error almost always runs from
**structured to unstructured**. The reverse, reading an unstructured thing as
structured, is rare.

This is systematic: the default assumption is "simple and unstructured", and
seeing the structure requires reading the source.

**Practical consequence:** If your source readings change verdicts and all move
the same way, that is a bias and must be reported.

> **Prompt:** Check the direction of source-reading errors in this paper. Do
> they all move structured to unstructured, or the reverse? If unidirectional,
> is it reported as a bias?

## 17.7 Preserve the triple

Your paper should contain three things at once.

```
1. positive result  : something found, measured, shown
2. negative result  : something did not work, was refused
3. out of scope     : the criterion declines to apply
```

With only (1) it looks like "it fits everything". With (2) and (3) it looks like
"it discriminates". The value of a criterion is in what it excludes.

> **Prompt:** Does this paper preserve the triple (positive result, negative
> result, out of scope)? With only positive results it looks like it fits
> everything; is there balance?

## 17.8 Cut format before content

The cutting order is fixed and must not be reversed.

```
1. unreferenced figures and decoration
2. empirical demonstration of an already proved result
3. many sub-experiments from one family (three in the body, rest in an appendix)
4. revision diary and intent attribution
5. only now: content
```

Cutting content is irreversible; cutting format always is.

> **Prompt:** Solve this paper's length problem with format cuts only. How many
> pages can be recovered without touching content? List them in order.

## 17.9 A length pass opens an experiment question

While shortening a section you discover which sentence is **load-bearing**. If
there is no measurement behind the load-bearing sentence, there is a missing
experiment there.

A cutting pass is therefore an audit, not only a writing task.

> **Prompt:** Halve this section. For every sentence you could not cut, show me
> the measurement behind it. Where there is none, list it as a missing
> experiment.

## 17.10 Name your ceiling

Every project has one caveat it cannot lift. **Name it** and state how it would
be lifted. An unnamed limit gets named by the reviewer instead.

**Form:** "This work was done on [X]. Until that caveat is lifted the
contribution remains [conceptual, partial, provisional]. The way to lift it is
[a concrete experiment]."

> **Prompt:** Name the largest caveat this paper cannot lift. Is it stated
> explicitly, and is the way to lift it given as a concrete experiment?

---

# 18. DEEP PRINCIPLES

These came from individual experiment sessions, and most arose from a
contradiction or a failure. Each carries a prompt.

## 18.1 "Not found" sometimes becomes "cannot be found because it cannot exist"

When you search and do not find, there are two possibilities:

```
1. the sample was insufficient (the search was limited)
2. what you seek CANNOT exist in principle (a structural constraint)
```

The second is a far stronger result. A **gap** (we did not find it) can become a
**theorem** (it cannot be found), and that transformation may be the most
valuable part of the work.

**But:** without formalisation no credit is given. Keep the observation and
theorem distinction strict. The difference between "not found so far" and
"cannot exist" is a proof sketch.

> **Prompt:** Can the "not found" results in this paper be turned into "cannot be
> found because it cannot exist"? Is the structural constraint formalised, or
> does it stay at observation level?

## 18.2 When two costs are the same quantity there is no "make it better" option

Sometimes strengthening a system (increasing parameter X) makes the legitimate
user's job harder **in the same proportion**. That is the sign that the attack
cost and the use cost are the **same quantity**.

In that case "increase security" and "preserve usability" conflict and there is
no trade-off between them. The correct move is not to increase the parameter but
to **change the design**.

> **Prompt:** Does a security or quality parameter in this paper hit a usability
> limit? If the two costs are the same quantity, is it stated that there is no
> trade-off?

## 18.3 Apply your thesis to your own method

Your critique of a tool or approach also applies to **your use** of that tool.

Concretely: if you argue "the standard measurement does not distinguish two
different structures", then your own reproductions, checked with that same
measurement, are also indistinguishable. Your work sits inside the same blindness
and needs an independent verification.

> **Prompt:** Is this paper's thesis applied to its own method? If the thesis
> binds you too, has an independent verification been added?

## 18.4 A verification test also verifies the structure

When a round trip or consistency test passes, it may mean not just "my code
works" but **"I understood the structure correctly"**, especially in complex or
counterintuitive mechanisms.

Where a mechanism makes you wonder "how could this ever be inverted", the inverse
working is independent evidence that the mechanism was built correctly.

> **Prompt:** Does this paper highlight cases where a verification test proves
> structural understanding rather than only implementation?

## 18.5 A constant unknown is absorbed, not recovered

If you must recover an unknown, first ask: **is it constant?** If it is, it can
be **absorbed** into the structure you build on top (table, equation, model).

If a transformation has a constant shift, index the table by the shifted argument
instead of finding the shift. A "parameter to be recovered" is sometimes "a
constant that can be hidden inside the table". In one measured case this reduced
cost by about three hundred fold.

> **Prompt:** Can a constant unknown in this work be absorbed into the structure
> instead of recovered separately? If a cost reduction is possible, propose it.

## 18.6 Size does not prevent controllability

A parameter being **large** does not mean the other side cannot **adjust** it. If
they control the input, they control any parameter that is a function of the
input, however wide it is.

**Lesson:** Write your criterion as **"can the other side adjust it"**, not "is
the parameter large". A criterion measuring size measures the wrong quantity.

> **Prompt:** Are wide but controllable parameters evaluated correctly in this
> paper? Is the criterion written as "can it be adjusted"?

## 18.7 Two kinds of fidelity: structural and surface

```
structural : is the mechanism your analysis relies on correct
surface    : does the observed output (statistics, appearance) match
```

For your purpose usually only structural fidelity is required. But you must
**justify this explicitly**: "the simplified step does not affect the structure
the analysis relies on." Without that justification partial fidelity is suspect.

> **Prompt:** Is partial fidelity (structural full, surface partial) justified in
> this work? Is it shown at mechanism level that the omitted step does not affect
> the result?

## 18.8 Check the ancestor before merging

When a "better" version or contribution arrives, check **which base it descends
from**. It may contain a good idea and still descend from an old or wrong base
that lost the intermediate corrections.

**Decision form:** do not take the package. Take the **good idea** and apply it
to the current base.

> **Prompt:** Which base does each version or contribution added to this work
> descend from? Could a good idea have come from an old branch and lost
> intermediate corrections?

## 18.9 What passes internal consistency can still be wrong

This is the operational form of the principle in Section 16.6. It is kept
separate because that one says **why** this happens and this one says **what to
do about it**.

Passing a round trip, a consistency test or an internal verification does not
make a model **correct**; these tests use the model's own assumptions.

**What to do:** Add at least one external anchor independent of the assumption.
```
counts as an anchor : an equation from the primary source
                      an independent measurement channel (invertibility,
                      conservation)
                      a deliberately wrong control version
does not count      : another test of the same model
                      more internal consistency checking
```

> **Prompt:** Beyond internal consistency tests, does this work have a
> verification independent of its assumptions? If not, which external anchor
> could be added?

## 18.10 The weakest component rule

If a quantity is composed of more than one part, the effective value is the
**minimum** of the parts, not their sum. The other side always targets the
weakest component.

```
"256 units strong component + 8 units weak component"  =  8 units,  not 264
```

List components **separately**; do not give one aggregate number.

> **Prompt:** Is the effective value of multi-component quantities in this work
> computed as the minimum rather than the sum? Is each component listed
> separately?

## 18.11 Do not impose the model on yourself, derive it from reality

When choosing an analysis framework or set of assumptions, avoid **imposing** it.
The framework must descend from the **reality** of the system you study.

Assuming the worst case is as misleading as assuming the best case. The correct
approach uses the conditions the system **genuinely** offers.

> **Prompt:** Is the analysis framework in this work imposed by the authors? Is
> it derived from the system's reality or chosen arbitrarily?

## 18.12 Acceptance criterion discipline: no marking without evidence

To mark a task "done" the **acceptance criterion** must be met.

```
counts as evidence : a script that was run with its output recorded
                     a measured number
                     a cited location from the source (equation, section, line)
does not count     : "it looks reasonable"
                     "it probably works"
                     "I wrote the code but did not run it"
                     "something similar worked before"
```

> **Prompt:** For every item marked "done" in this project, is the acceptance
> criterion met? List the markings that have no evidence.

## 18.13 An error becomes a finding

When you find an error, do not only fix it: ask **why it arose**. The answer is
usually a general principle, and that principle is your finding.

```
error      : I synchronised a number by hand and it drifted
fix        : I updated the number
FINDING    : a hand-synchronised number drifts; use a macro
```

The fix is project-specific, the finding is portable. Most of this handbook was
produced this way.

> **Prompt:** Turn every error found in this project into a portable finding.
> List them in three columns: error, fix, and the general principle behind it.

---

# 19. FINAL GLEANINGS

Items that did not fit the other sections but keep proving useful.

## 19.1 Report the failure points

What did not work is a result too. Hiding failed attempts costs twice: the reader
cannot see the boundary, and someone repeats the same attempt.

**Form:** approach tried, result, **why it failed**. Without the third column the
list is useless.

> **Prompt:** Are the approaches that were tried and failed reported in this
> work? Does each have a "why it failed" column?

## 19.2 The experiment and text loop

Writing opens experiments and experiments change the writing. **Close the loop:**

```
a gap appears while writing   -> add it to the experiment list
the experiment returns        -> update the text
updating opens a new gap      -> repeat
```

Submitting before the loop closes leaves sentences with no measurement behind
them.

> **Prompt:** Are the experiment questions opened while writing recorded in this
> work? Are there sentences left with no measurement behind them?

## 19.3 The single source principle

If the same information lives in two places, one of them eventually goes wrong.
Every quantity, definition and verdict lives in **one place**; everything else
feeds from it.

```
numbers      -> macro
verdicts     -> one table, the text cites it
definitions  -> first occurrence, then citation
code output  -> json, the text reads from it
```

> **Prompt:** Is the same information held independently in more than one place
> in this work? List the violations of the single source principle.

## 19.4 The derived file is current, the source document is stale

If you have derived other documents from one source, it is easy in later rounds
to update **only the derived ones**. The source goes quietly stale, and one day
someone reads it.

**Measured example:** Two handbooks were derived from one source document. Over
the next five rounds only the handbooks were updated. An audit showed the source
citing a section that no longer existed: numbering had changed in the derived
files and not in the source.

**Two legitimate options, there is no third:**
```
1. update the source every round too  -> the single source principle holds
2. mark the source as an ARCHIVE      -> "this document is dated R0, the current
                                         versions are the derived ones"
3. leaving it silently                -> not an option
```

> **Prompt:** Does this project have documents derived from a source? Is the
> source current, or marked as an archive? Is anything going quietly stale?

## 19.5 A table is a data structure, not a view

Design a table as a **data structure**, not as "let me show this": rows are
records, columns are fields, every cell the same type.

This view solves three things automatically: constant columns get removed, mixed
types get separated, and the script that produces the table becomes the table.

> **Prompt:** Are the tables in this paper designed as data structures? Are rows
> records, columns fields, and every cell the same type?

## 19.6 The accountability chain

For every claim the chain must be unbroken:

```
claim -> which number -> which script -> which input -> which source
```

If any link is broken the claim is unsupported. Before submission, walk this
chain end to end for **three randomly chosen claims**.

> **Prompt:** Pick three claims at random from this paper and walk the
> accountability chain end to end: claim, number, script, input, source. Any
> broken links?

## 19.7 Nothing unmeasured is claimed

Every quantitative expression needs a measurement behind it. Words like
"approximately", "usually" and "most" are quantitative too.

```
bad  : the method works in most cases
good : the method worked in 11 of 14 attempts
bad  : the cost is quite low
good : the cost is 221 queries and does not change with class width
```

> **Prompt:** Match every quantitative expression in this paper (including
> approximately, most, usually) with the measurement behind it. List the ones
> with none.

## 19.8 Publication tactics

**Major revision is a conditional yes.** It is not a rejection. Answer the
reviewer point by point in the form "what changed, and where".

**Wait for the reviewer data.** Do not make large structural decisions (splitting,
reframing) before reviewer feedback arrives. A reviewer mandate is a stronger
justification than your own guess.

**Do not choose a venue on metrics alone.** Target audience, cycle time and scope
fit usually matter more than impact factor.

> **Prompt:** Which decisions for this submission should wait for reviewer data,
> and which must be made now? List both.

## 19.9 Remaining formatting items

**Citation style:** one style per document. Do not mix author-year with numeric.
If a citation can be the subject of a sentence, author-year fits; if not, numeric
does.

**Bibtex hygiene:**
```
[ ] DOI or a permanent URL in every entry
[ ] journal names all full or all abbreviated, not mixed
[ ] special characters escaped, capitals protected with braces
[ ] no duplicate entries
[ ] unpublished work marked unpublished or preprint
```

**Algorithms and pseudocode:**
```
[ ] every line numbered
[ ] inputs and outputs stated explicitly
[ ] variable names identical to those in the text
[ ] cost stated by loop structure, not line count
[ ] pseudocode clear enough to be turned into working code
```

> **Prompt:** Audit this paper's citation style, bibtex hygiene and algorithm
> formatting. Any mixed styles, missing DOIs, or unnumbered algorithm lines?

---

## 19.10 Write the patch so it can be applied mechanically

If you update a document through patches applied in another environment, the
patch's **location anchor** must occur exactly once in the document and must
**already exist**.

**The mistake made this round:** In a first draft, four patches anchored to a
heading that an **earlier patch in the same file would add**. That creates a
dependency on apply order and breaks when patches from another source are
reconciled.

```
[ ] every locate string occurs EXACTLY ONCE in the target file
[ ] no locate is text produced by another patch in this file
[ ] each patch is one idea, one location
[ ] uniqueness verified automatically before sending
```

The verification is one line and must not be skipped:
```python
assert open(target).read().count(locate) == 1, f"anchor not unique: {locate}"
```

> **Prompt:** Does every `locate` string in this patch file occur exactly once in
> its target? Does any patch anchor to text another patch will add? Verify
> automatically.

## 19.11 Verify a patch landed by content, not by label

Searching for **the heading number you supplied** produces false negatives: the
apply step may have shifted your number to avoid clashing with other additions.

**Measured example:** Two of sixteen patches appeared "not applied". A content
search found both in place; the apply step had turned what was sent as `10.13`
into `10.14` and `10.15` because of intervening insertions.

```
search by label   : "## 10.13 X"          -> produces false negatives
search by content : a distinctive sentence -> reliable
```

> **Prompt:** Verify whether my patches were applied using a distinctive sentence
> from each patch, not the heading number.

## 19.12 Two independent workers on one document: do not coordinate

When two people or two sessions contribute independently to one document, trying
to divide the work costs twice: the coordination time, and the risk that the
division itself is wrong.

**The right structure:** everyone reports **everything they know**, and
reconciliation happens in a separate step. Overlapping contributions are not
waste, they are **independent corroboration**: if two people found the same gap,
the gap is real.

```
coordinate       : coordination cost + risk of a wrong split
work independently: overlap happens, but overlap carries information
```

> **Prompt:** If more than one source contributes to this document, was the work
> divided or did everyone report everything they knew? Are overlapping
> contributions treated as waste or as corroboration?

## 19.13 A convergence criterion: when do you say done

When an iterative process stops must be defined **in advance**, otherwise fatigue
becomes the stopping criterion.

**A usable criterion:** stop when all independent contributors say "nothing
missing" **in the same round**. One contributor saying done is not enough,
because it cannot see its own blind spot.

**And saying done has a precondition:** state at what level you looked this
round. If you looked at heading level and not at content level, you may not say
done.

```
valid done   : "I read at content level and found no gap"
invalid done : "the headings match, done"
```

> **Prompt:** Does this iterative process have a stopping criterion defined in
> advance? Do contributors state at what level they looked when they say done?

# 20. FIGURE GENERATION ARCHITECTURE

Figures are not drawn one at a time, they are produced by a **system**. Without
one, each figure invents its own colours, box style and font, and the paper looks
assembled rather than designed.

## 20.1 Colour is semantic, not decorative

A single palette file (`palette.py`) is the colour source for every figure. **No
figure defines its own colour.**

Principle: one concept, one colour. And critically: carry the difference **not
only by colour but also by hatch**.

```
BROKEN         -> dense forward hatch  (////)
RESISTS        -> crosshatch           (xxxx)
REFUSE         -> dots                 (....)
key material   -> mid grey, no texture
plaintext path -> light grey
measured data  -> dark grey
reference line -> grey, dashed
```

This keeps figures readable under colour blindness (deuteranopia, protanopia) and
in greyscale print.

> **Prompt:** Is colour in this paper's figures semantic or decorative? Is there
> a single palette source, is each concept bound to one colour, is the verdict
> difference distinguishable under colour blindness and greyscale (hatch
> supported)?

## 20.2 Verify accessibility automatically

Three checks are **asserted** in the palette file and their result written out:

```
1. verdict pair differs in CIELAB L* by >= 25 AND carries a hatch difference
   (for colour blindness and greyscale print)
2. the three verdict fills map to three visibly different greys
3. each fill meets >= 4.5:1 WCAG contrast against its own label ink
```

Vienot 1999 matrices can be used for the colour-blindness simulation. The result
is recorded in a file such as `COLOUR_CHECK.md`, so the check is an artifact too.

> **Prompt:** Verify this paper's figure colour system for accessibility: verdict
> pair CIELAB L* >= 25 with a hatch difference, three verdicts mapping to three
> greys, each fill meeting 4.5:1 WCAG contrast. Run a colour-blindness
> simulation.

## 20.3 Shared drawing primitives

Every diagram uses the **same** box style, line weight, arrow head and font. A
`figtools.py` file defines the shared primitives: box (rounded corner, centred
label), label, arrow (consistent connection style), colour chip (for legends),
axis clearing.

Constants in one place:
```
STROKE      = 1.1   standard edge
STROKE_THIN = 0.8
ROUND       = 0.10  corner rounding
```

**The separation matters:** `figtools` defines no colour; colour comes only from
`palette`. The two files have disjoint responsibilities.

> **Prompt:** Do this paper's diagrams use shared drawing primitives? Are box
> style, line weight, arrow head and font consistent, and are the constants
> (STROKE, ROUND) single sourced?

## 20.4 Technical requirements

Two settings are **mandatory** for publication:

```python
matplotlib.rcParams['pdf.fonttype'] = 42     # TrueType, NOT Type 3
```
Some journals reject PDFs with Type 3 fonts.

**Data is not hardcoded into the figure.** The generation script reads it from a
JSON file, so the figure obeys the single source principle too: when a number
changes the figure updates itself.

**A point estimate alone misleads.** Show a confidence interval (bootstrap or
analytic) and, where one exists, a dashed chance-level line.

> **Prompt:** Do this paper's figures use PDF font type 42, read data from a file
> rather than hardcoded, and show confidence intervals and a chance-level line?

## 20.5 A failing check must stop the palette

Accessibility checks exist not to report but to **stop production**. The figure
script calls the palette and does not draw if the check fails.

```python
ok, _ = palette.check(verbose=False)
assert ok, "palette failed the accessibility check, no figure produced"
```

**Measured example:** A palette that looked reasonable failed two of three
checks: WCAG 4.35:1 (threshold 4.5) and a CIELAB L* difference of 2.1 between two
verdicts (threshold 25). Two manual fixes also failed; each cleared one threshold
and broke another.

**Solve instead of guessing.** Place the three verdicts at even spacing on the L*
axis (for example 25, 55, 85) and find the colour that lands on each L* by binary
search.

```
target L*    : 25, 55, 85
per hue      : scale the base colour, binary search until L* hits the target
ink          : white if L* < 55, else black; if WCAG fails, take the other end
```

Result: all three pairs between 29.6 and 60.0 in L* difference, every WCAG value
above 5.10:1, three distinct greyscale values.

**Lesson:** Satisfying a constraint set by hand stops working once there are more
than three constraints. Turn the constraint into a target and solve it.

> **Prompt:** Does the palette in this project pass its accessibility checks? If
> not, do not try manual fixes; choose target L* values and solve for the colours
> that land on them.

## 20.6 Verify font embedding with a tool

Setting `pdf.fonttype = 42` is not enough, **verify** the output. A raw byte
search inside the PDF misleads: the string `/TrueType` may not appear at all in a
file that uses CID subsetting.

```
pdffonts figure.pdf
  name              type           emb sub uni
  BMQQDV+DejaVuSans CID TrueType   yes yes yes     <- correct
```

What you are checking is the **absence** of `Type 3` and `emb` reading `yes`.

> **Prompt:** Verify this project's figure PDFs with `pdffonts`. Any Type 3, are
> the fonts embedded, are they subset?

## 20.7 The prompt that builds the architecture

```
Set up a figure generation architecture for this paper:

1. palette.py
   - single colour source, one concept one colour
   - verdicts also separated by hatch (colour blindness + greyscale)
   - assert CIELAB L* difference >= 25 and WCAG >= 4.5:1
   - write the result to COLOUR_CHECK.md

2. figtools.py
   - shared primitives: box, arrow, label, chip, axis clearing
   - fixed line weights (STROKE, STROKE_THIN, ROUND)
   - defines NO colour

3. every figure imports both and defines no colour or style of its own
   - data read from JSON, not hardcoded
   - pdf.fonttype = 42
   - confidence intervals and a chance-level line

Output vector PDF. No em dashes. Caption one line, matched to object width.
```

> **Prompt:** Build the architecture above for this project and give me all three
> files: `palette.py`, `figtools.py`, and one example figure script.

---

# 21. READY-TO-USE PROMPTS

Paste these directly. Each is self-contained. Replace the bracketed parts.

## 21.1 Extract method structure from a primary source

```
I am going to give you the primary source for [METHOD/SYSTEM]. Extract its
structure for reproduction. Do not summarise. For each item cite the exact
section, equation or line number, and mark anything you cannot anchor as
UNANCHORED.

Produce:
1. The central quantity: which formal statement defines it, and exactly which
   inputs it depends on. Give me two lists: influence set and free set.
2. Every derived quantity, and for each: does it SELECT behaviour, or is it
   merely recorded?
3. The mathematical type of every stage, and what the composition reduces to.
4. Which direction any inverse operation must run, and why.
5. Every constant or choice the source leaves unspecified.

Finish with: "UNANCHORED ITEMS: ..." If that list is non-empty, say that any
result is PROVISIONAL.
```

## 21.2 Design a discriminating reproduction check

```
I have reproduced [METHOD] and I claim it has the structural property
[PROPERTY].

Design a measurement that separates my reproduction from one where that property
is absent. Requirements:

- the measurement must be a direct consequence of [PROPERTY], not a general
  summary statistic
- give me the expected value ANALYTICALLY before I measure, with derivation
- tell me what a deliberately wrong reproduction would give
- if the property cannot be separated by this measurement, say so and propose a
  second one

Then give me code for: the correct version, a deliberately wrong control
version, and the measurement over both.
```

## 21.3 Debug an unexpected experimental result

```
My experiment on [SYSTEM] gives [UNEXPECTED RESULT].

Do NOT assume the phenomenon is real. Work through this order and report each
step:

1. Isolate the core assumption and measure it alone. Report the number.
2. Check arithmetic and boundary cases separately:
   - saturation or modular wrap in any compensation
   - degenerate baseline (are most values at the extremes?)
   - compensation capacity: required <= points * range?
3. Verify each component against ground truth separately. Report which are
   correct.
4. If partial success (e.g. 8/9 or 8/20), do not call it "almost there". Tell me
   what type of error that rate implies.
5. If multiple candidates remain, derive BY HAND whether they are equivalent or
   merely unseparated by my measurement set.
6. Rule out display artefacts: rounding, integer truncation, formatting.

Only if steps 1 and 2 are clean may you conclude the phenomenon is real, and
then quantify it.
```

## 21.4 Write a pre-registration

```
I am about to run [EXPERIMENT] to test whether [CLAIM].

Write a pre-registration I will freeze before collecting data. It must contain:

1. Hypotheses, each in this exact form:
   "WHICH MEASUREMENT | WHICH THRESHOLD | WHICH VERDICT"
   Do not write vague statements like "X will not happen".
2. The falsification rule: which result opens which claim, and which does not.
3. Definitions of any inclusion criterion, fixed BEFORE any search, including
   what does NOT count.
4. A list of forbidden claims: sentences I may not write unless a specific
   condition is met.
5. An ambiguity clause: if the wording admits two readings, I take the
   conservative one and report the ambiguity.

Flag any hypothesis whose wording could be read two ways, and rewrite it.
```

## 21.5 Audit a manuscript for number consistency

```
Audit this manuscript for numerical and internal consistency. Report every
instance with location.

1. Every quantity: list ALL occurrences across abstract, body, tables, figures
   and conclusion. Flag disagreements.
2. Section headings containing numbers: does the arithmetic hold?
3. Figures: do they show current results or are they stale?
4. Every table and figure: referenced at least once, and does the reference come
   before the object?
5. Counts of samples, experiments, positive and negative results: consistent
   everywhere?
6. Any number that looks hand-estimated rather than script-produced.

When searching markup source, account for escape characters. If a search returns
zero, retry with the escaped variant before concluding absence.
```

## 21.6 Scan for a concept's name in adjacent literature

```
My paper defines: [DEFINITION AND FUNCTION].

Search whether this already exists under another name in adjacent fields. Search
for its FUNCTION, not its name. Try phrasings like: [FUNCTIONAL DESCRIPTION 1],
[FUNCTIONAL DESCRIPTION 2].

For anything found, report:
1. Is it the same quantity, or only analogous?
2. Is the CONSEQUENCE the same in both settings?
3. Which citations become mandatory.
4. How my originality claim should be narrowed, in one sentence.

Also search whether my CLASS already has an established name. If it does, my
name is a renaming and must be presented as one.

Finish with: "This was N searches. It is not a full literature review."
```

## 21.7 Style and typography audit

```
Audit this manuscript against these rules and report every violation with
location.

1. No em-dashes. Report each and propose the rewrite.
2. Every caption must fit the width of its object. Report any that span wider.
3. Every caption must be ONE line. For each that wraps, rewrite it short and say
   where the removed detail goes (table note or body).
4. Number formatting: fixed decimals per column, decimal alignment, consistent
   separators, no more digits than the measurement supports.
5. Tables: booktabs only, no vertical rules, flag any column constant across all
   rows.
6. Figures: units on axes, no colour-only encoding, vector format.
7. Every symbol defined at first use; no symbol with two meanings.
8. Flag any fully bolded sentence.
9. Flag intent-attributing language ("silently omits", "hides", "avoids") and
   propose the neutral observation.
10. Flag revision-diary language ("in an earlier draft", "this took three
    attempts") for removal to the cover letter.
```

## 21.8 Write a visible retraction

```
I claimed [OLD CLAIM]. I have found [NEW EVIDENCE] showing it is wrong or too
strong.

Write a retraction note in a matter-of-fact voice stating, in order:
1. what was claimed
2. what was found, with the source anchor
3. what survives
4. when and how I learned it

Do not be theatrical and do not over-apologise. Do not silently restate the
contribution. Under 150 words. Then tell me where in the paper it goes.
```

## 21.9 Hostile reviewer simulation

```
Read this manuscript as a hostile but competent reviewer for [VENUE]. You are
looking for reasons to reject.

Produce, in order:
1. The three strongest objections, each with the text that triggers it.
2. For each, whether it is fatal, major, or cosmetic.
3. Every place a claim exceeds its evidence.
4. Every limitation I have not stated that you can infer.
5. Any two statements in the paper that contradict each other.
6. The first paragraph at which you would stop reading, and why.
7. Anything you suspect has been done before that I have not cited.

Do not praise anything. If you cannot find three objections, say so explicitly.
```

## 21.10 Split decision

```
My manuscript is [N] pages covering [PART A] and [PART B]. I am considering
splitting it for [VENUE 1] and [VENUE 2].

Apply this test and answer directly:
1. Remove PART A. Does PART B still stand on its own evidence?
2. Remove PART B. Does PART A still stand?
3. If either half is the CALIBRATION or the FRAME of the other, splitting
   weakens both.
4. If I submit both simultaneously, does mutual citation actually work?

If the answer is do not split, tell me which cuts solve the length problem,
ranked by how much they cost the argument.
```

## 21.11 Package the artifact

```
Package this project for submission. Produce:

1. A directory layout: one main findings document, one folder per experiment
   with its result file, a reports folder, and a README.
2. A README stating: where to start, which folder produced which result, the
   dependency note, and four quick commands reproducing the headline results.
3. Verification steps before shipping:
   - open the archive in a clean directory and run from there
   - check every text file is valid UTF-8
   - confirm no hand-written numbers remain
   - confirm the result-producing path does not need special hardware
4. A list of caveats that do NOT close, stated as such.

Random seed: [SEED]. Everything reproducible from it on a single core.
```

## 21.12 Extract implicit rules from a project

```
Here is a record of a project: [TRANSCRIPT, CORRECTION REQUESTS, REVIEW NOTES].

Extract the rules that were ENACTED but never written down. Look in three
places:
  1. what was specifically asked for      -> what counted as important
  2. what was asked to be corrected       -> which error was not tolerated
  3. what was emphasised repeatedly       -> which principle is load-bearing

Method:
  1. list every correction request
  2. for each, ask which general principle it is a special case of
  3. group requests mapping to the same principle
  4. write the RATIONALE per group, not the rule
  5. list the derived rules underneath

Write rationales, not rules, because a rule may not fit an unencountered
situation while a rationale tells me what to do there.
```

## 21.13 Decide whether a finding is real or an artefact

```
I measured [SURPRISING RESULT]. Before I report it, stress-test it.

1. Could this be a display artefact? Check rounding, truncation, formatting.
   Show me the raw value.
2. Could this be a boundary artefact? Check saturation, wrap, off-by-one.
3. Could this be a degenerate-input artefact? What does the input distribution
   look like at the extremes?
4. Is the effect present at more than one size or setting? If only one, treat it
   as suspect.
5. What would this look like if my implementation were wrong in the most likely
   way? Is that distinguishable?
6. Derive the expected value analytically under the null assumption. Does the
   measurement exceed the noise?

Verdict: REAL, ARTEFACT, or UNDECIDED with the measurement that would decide it.
```

## 21.14 Reframe the headline

```
My paper's current headline is: [CURRENT CLAIM].

A concurrent paper [CITATION] covers part of the same ground. Reframe so my
contribution is not directly comparable.

1. Which of my results are countable? Those are most preemptable; they should be
   EVIDENCE, not headline.
2. Which are instruments, criteria, proofs or corrections? Those are the
   headline.
3. Rewrite the abstract's final sentence and the introduction's claim sentence.
4. Test: could a reviewer place my results side by side with theirs in one
   table? If yes, the headline is still wrong.
5. Write one sentence positioning the concurrent work as independent
   corroboration rather than competition.
```

## 21.15 Design the calibration population

```
I have a procedure that classifies [OBJECTS] and I have tested it on [N]
positive cases. A reviewer will say it may be over-producing.

Design a calibration population:
1. Find established systems, standards or products that use the SAME mechanism
   but use it CORRECTLY, where the answer is independently known.
2. For each, state the four fields my procedure needs, and the expected verdict
   BEFORE I run it.
3. Tell me what would count as a false positive, and what I should report if I
   get one.
4. Look for one system with two configurations that should get two different
   verdicts. That is the strongest single data point.
5. Tell me what my agreement rate does and does not prove (specificity is not
   sensitivity).
```

## 21.16 Decide whether to consolidate or extend

```
Current state: [SUMMARY OF RESULTS AND OPEN ITEMS].

Help me decide whether to produce more results or consolidate what I have.

1. Which of my results are countable and therefore preemptable?
2. Which are distinguishing (instrument, criterion, correction)?
3. Has any recent work overlapped the countable ones? Search.
4. What is the marginal return of one more countable result versus making the
   existing ones defensible?
5. List the consolidation tasks in priority order, marking which are mandatory
   for submission.
6. Track the direction of my recent corrections: did they change the RATIONALE
   or the DIRECTION of my claims? If direction, tell me to stop and re-examine
   the foundation.
```

## 21.17 Prompts from the condensed edition

These three are carried over from the condensed lessons edition; they complement
the prompts above rather than repeat them.

### Style pass (Midwest register)
> Prompt: Improve the style of this paper. Midwest register: competence that does
> not need to sell itself, understated confidence, free of unnecessary adjectives,
> stating the result without overstating it. Rules: no em dash; every table or
> figure caption one line at the element width; no defensive repetition; one idea
> per paragraph; hedging only when genuinely uncertain. Do not change content, only
> clarify expression.

### Structural consistency audit
> Prompt: Audit the structural consistency of this paper: (1) is every number
> single sourced as a macro?; (2) do the arithmetic relations hold?; (3) is every
> claim's accountability chain (result to verification to model to source)
> complete?; (4) are revised results current at all citation points?; (5) are the
> three aspects (positive, negative, out of scope) preserved? List the gaps.

### Pre-submission final check
> Prompt: Audit this paper before submission: macros single sourced, zero undefined
> references, zero compile errors, residue expressions clean, defensive repetition
> minimal, concurrent citation and narrowing note present, tables column
> consistent, no em dash, preprint ready. Mark every missing item and fix it.

---

# 22. HOUSE RULES AND SHORT PROMPTS

Everything below is short on purpose. Each block fits in a prompt window with
room to spare. Paste one, not the whole section.

## 22.0 HOUSE RULES

Most prompts below say "Apply HOUSE RULES". Paste this block once at the top of
a session, or inline it when you need it.

```
HOUSE RULES
- No em-dashes anywhere. Use a comma, a colon, parentheses, or two sentences.
- Table and figure captions: label plus a one-line explanation, on ONE line.
  Caption width must not exceed the width of the object it belongs to.
- Plain competent prose. No selling, no hype, no throat-clearing, no adjectives
  doing work that evidence should do. State the result and move on.
- Every number traceable to a script or a source. Mark invented values TODO.
- Figures: vector only, body font, units on axes, never colour-only encoding.
- Say what you did not do, and why, rather than leaving it implicit.
- A check is trusted only after the defect it names has been injected and
  the check has been seen to fail on it.
- Verify the artifact, not only the source. Compiling clean is not evidence
  that the content survived.
- Fetch before claiming something does not exist. Exhaustive search of a
  stale copy is exhaustive only of the copy.
```

---

## 22.1 Micro-prompts by lesson

Three shapes per lesson: APPLY changes something, AUDIT only reports, FIX
repairs one named class of problem. Keep them separate; an audit that also
edits hides what it changed.

### Modelling and source reading
```
APPLY : Extract the structure of [TARGET] from the primary source. Cite an
        equation or section for every claim. Mark unanchored items.
AUDIT : List every structural claim in my notes that has no source anchor.
        Do not fix anything.
FIX   : For each unanchored claim, either find the anchor in [SOURCE] or mark
        the verdict PROVISIONAL. Nothing else.
```

### Fidelity and reproduction
```
APPLY : Design a measurement that separates my implementation from one missing
        [PROPERTY]. Derive the expected value first, then give code.
AUDIT : Does my fidelity check actually discriminate? Tell me what a wrong
        implementation would score on it.
FIX   : Build the deliberately wrong control version and run the measurement on
        both. Report the two numbers only.
```

### Attack or experiment design
```
APPLY : Design the probe set for [TARGET]. State the access model and the
        compensation capacity.
AUDIT : Check my design for a degenerate baseline, saturation, and insufficient
        compensation. Report only.
FIX   : Rebuild the baseline from mid-range values and re-verify the constraint
        after every intervention.
```

### Debugging
```
APPLY : My run gives [SYMPTOM]. Isolate the core assumption and measure it
        alone. Report the number before concluding anything.
AUDIT : List every non-structural cause that could produce [SYMPTOM]: overflow,
        wrap, degenerate base, display truncation.
FIX   : Verify each component against ground truth separately and tell me which
        one is wrong.
```

### Measurement and reporting
```
APPLY : Decompose this cost into online and offline components and show how each
        scales.
AUDIT : Find every number in this report that is stated without its scope,
        precision, or access model.
FIX   : Rewrite the results section so measurement and extrapolation are
        clearly separated.
```

### Criterion or classifier design
```
APPLY : List every structure that could produce the same value my test outputs.
        If more than one, propose a second test.
AUDIT : For each step of my procedure, count how many verdicts it actually
        changes. Report the imbalance.
FIX   : Add the missing sub-test to the step that is currently under-determined.
```

### Literature and claims
```
APPLY : Search whether [CONCEPT] exists under another name next door. Search its
        function, not its name.
AUDIT : Which of my claims would a reviewer find already published? List them
        with the likely citation.
FIX   : Narrow the originality claim to one sentence that survives [FINDING].
```

### Self-correction
```
APPLY : Write a visible retraction for [CLAIM]. Under 150 words, matter of fact.
AUDIT : Across my recent corrections, did each change the RATIONALE or the
        DIRECTION of a claim? Flag any direction change.
FIX   : Move all process narration out of the body and into a cover-letter
        paragraph.
```

### Style
```
APPLY : Improve this file's style. Apply HOUSE RULES. Show a diff, not a rewrite.
AUDIT : List every style violation with line numbers. Change nothing.
FIX   : Fix only the em-dashes. Nothing else.
```

### Figures and tables
```
APPLY : Improve the figures and tables in this file. Apply HOUSE RULES.
AUDIT : For each table and figure: is it referenced, is the caption one line, is
        any column constant, is anything encoded by colour alone?
FIX   : Rewrite every caption as label plus a one-line explanation. Move
        conditions to table notes.
```

### General error check
```
CHECK : Is there an error in this file? Look for contradictions between
        sections, numbers that disagree, claims exceeding evidence, and broken
        references. Report with locations, fix nothing.
```

### Artifacts
```
APPLY : Package this project: layout, README, dependency note, four commands
        that reproduce the headline results.
AUDIT : Would this archive run in a clean directory? List what is missing.
FIX   : Add the dependency note and the clean-run instructions only.
```

---

## 22.2 Builder prompts

### Build a full paper from scratch, Overleaf ready
```
Build a complete LaTeX paper from these results.

Inputs: [RESULTS FILE], [NUMBERS OR JSON], [VENUE], [PAGE LIMIT].

Deliver a zip that compiles on Overleaf with no edits:
  main.tex, refs.bib, figures/ (TikZ or vector pdf), README with build command.

Requirements:
- Headline is the method or finding, not the count of results.
- Every number comes from the inputs. Anything you invent is marked TODO.
- Figures in TikZ or pgfplots, body font, units on axes, no colour-only encoding.
- Captions: label plus one-line explanation, on one line, width matched to the
  object using a savebox.
- Apply HOUSE RULES.

Give me the file tree first, then each file in full.
```

### Revise an existing draft
```
Revise this draft. Do not rewrite it wholesale.

Inputs: [DRAFT], [REVIEW COMMENTS OR GOALS], [PAGE LIMIT].

Deliver, in order:
1. A change list: what changes, where, and why.
2. The edited passages only, as replacement blocks with enough context to locate
   them.
3. What you did NOT change, and why.

Rules:
- Preserve the author's voice and any deliberate repetition.
- Do not alter numbers. Flag suspect ones instead.
- Apply HOUSE RULES.
```

### One premium figure
```
Make one figure for this result: [RESULT OR DATA].

Deliver standalone TikZ or pgfplots that compiles alone and drops into a paper.

Requirements:
- Vector only. Body font at matched size. Units on every axis.
- Never encode by colour alone; add marker, pattern or position.
- No gratuitous grid, frame, shadow or 3D.
- Legend outside unless it covers nothing.
- Caption: label plus one-line explanation, on one line, width matched.
- Apply HOUSE RULES.

Open with one sentence saying what the reader should see first.
```

### Tables from results
```
Turn these results into publication tables: [RESULTS].

Rules:
- booktabs only, no vertical rules, no rule on every row.
- Delete any column constant across all rows and state it in the caption.
- Fixed decimals per column, aligned on the decimal point, siunitx.
- No more digits than the measurement supports.
- Caption: label plus one-line explanation, on one line, width matched with a
  savebox.
- Conditions go in a table note, never the caption.
- Apply HOUSE RULES.
```

### Overleaf package check
```
Check this LaTeX project compiles clean and ships correctly.

Report, with the fix for each:
1. Missing packages, files or figures.
2. Undefined references and citations.
3. Any figure not in vector format.
4. Any caption longer than one line or wider than its object.
5. Any number not traceable to a source.
6. Build errors and warnings.

Then give me the corrected file tree and the build command.
```

### Abstract and opening claim
```
Rewrite the abstract and the introduction's claim sentence.

Inputs: [CURRENT ABSTRACT], [MAIN RESULT], [WHAT IS ALREADY KNOWN].

Rules:
- The headline is the instrument, criterion or proof, not the count of results.
- Countable results appear as evidence, in one clause.
- No sentence may promise what the paper does not deliver.
- Apply HOUSE RULES.

Give three versions at different levels of ambition, and say which is earned by
the evidence.
```

### Cover letter
```
Write a cover letter for [VENUE].

Inputs: [PAPER SUMMARY], [WHAT IS NEW], [ANY CONFLICT OF INTEREST].

Rules:
- Three short paragraphs. What the paper does, why this venue, what is new.
- Declare any conflict plainly, including if this venue published work we
  criticise.
- Put revision history here, not in the paper.
- No selling. Apply HOUSE RULES.
```

### Response to reviewers
```
Draft a response to these reviewer comments: [COMMENTS].

For each comment produce:
  the comment, one line
  what we changed, with the section number
  or why we did not change it, in one sentence

Rules:
- Concede quickly where the reviewer is right. Do not argue tone.
- Where you disagree, give the measurement, not the opinion.
- Never claim a change you did not make.
- Apply HOUSE RULES.
```

---

# 23. CROSSWALK (CONDENSED EDITION)

This document is the union of the comprehensive handbook and the condensed
lessons edition. If you learned the condensed edition, the table maps its parts
to the sections here.

| Condensed edition (lessons) | This document |
|---|---|
| HOUSE RULES | HOUSE RULES (top), Section 22 |
| Part 1 Experiment design | Sections 2, 3, 4, 5, 7 |
| Part 2 Source reading and verification | Sections 1, 9, 16 |
| Part 3 Macro system and consistency | Sections 11, 16 |
| Part 4 Revision management | Sections 11, 16 |
| Part 5 Literature positioning | Section 9 |
| Part 6 Publication strategy | Section 13 (incl. 12.11 to 12.13) |
| Part 7 Feedback loops | Sections 5, 9, 18 |
| Part 8 Checklist before submission | Section 14 |
| Part 9 Style and formatting | Sections 15, 19 |
| Part 10 Background principles | Section 16 |
| Part 11 Deep principles | Sections 17, 17 |
| Part 12 Article building and editing prompts | Sections 21, 21 (incl. 20.17) |

The third source, a later project, maps as follows.

| Third source (silent-failure project) | This document |
|---|---|
| Verification code as an object requiring verification | Section 24 |
| Build gates, exit status, staleness, warning classes | Section 24.9 |
| Fallbacks that publish the wrong thing | Section 24.10 |
| Reading a correction notice without over-reading it | Sections 25.1, 24.2 |
| Conflicting authorities, stored definition versus rendering | Sections 25.3, 24.4 |
| Rules leaking between venues; requirements that reverse | Sections 25.5, 24.6 |
| Acting on a review you received | Section 25.7 |
| Anonymity and other "must not contain" constraints | Section 25.8 |
| Parameter interaction and compensated constants | Section 25.9 |
| Delivering the same work in a second format | Section 26 |
| Meeting someone else's template | Section 27 |

The same project's domain lessons, which are about cryptanalysis and the
evaluation of detectors rather than about method, are in
`CRYPTANALYSIS-AND-EVALUATION.md`.

---

# 24. THE CHECK ITSELF

Section 2 designs a measurement that discriminates. Section 18.9 says internal
consistency is not correctness. This section is about the **verification code as
an object requiring verification**. It exists because in one project three
separate checks shipped a false pass, and each was found only by pointing it at
an artifact a human had already rejected.

An absent check leaves you uncertain. A **vacuous** check leaves you confident
and wrong, and consumes the attention that would have found the defect.

## 24.1 A check that has only ever passed has not been tested

It has been **run**. The failing path is the one path never exercised, because
checks are written while looking at correct input.

```
when writing a check, in the same sitting:
  [ ] one input it must PASS
  [ ] one input it must FAIL
  [ ] both recorded, both re-run when the check changes
```

**Evidence:** A conformance check was validated three ways and only the third
mattered: it passed the current artifact, failed the artifact that had been
rejected earlier, and returned "no data" rather than a pass on an empty file.
The middle case is the regression test; without it the check is decoration.

> **Prompt:** For every check in this project, show me the known-bad input it
> fails on. List the checks that have only ever passed.

## 24.2 Unresolved must not compare equal to unresolved

If two values both fail to resolve and your comparison reports "equal", you have
built a check that certifies the exact condition it exists to detect.

**Evidence:** A check compared two font identifiers. A lookup bug made both
resolve to the placeholder `?`, and `? == ?` certified a wrong typeface as
matching the correct one. The check reported a clean pass on the artifact that
had already been returned by the reviewer.

```
three outcomes, never two:
  MATCH        the values resolved and agree
  MISMATCH     the values resolved and differ
  UNRESOLVED   at least one did not resolve  -> FAIL, never a pass
```

> **Prompt:** In every comparison this project makes, what happens when one side
> fails to resolve? Show me that "could not determine" is a failure and not a
> value that can match another.

## 24.3 A matcher's silence is evidence only if it has been shown to fire

A pattern written from the **name** of the thing rather than its actual encoding
matches nothing and reports everything as clean.

**Evidence:** A search for monospaced fonts used the pattern `Mono`. The font
actually present was named `NimbusMonL`, with no trailing letter, so the search
returned empty and the document was declared clean. Separately, every font name
in that file was prefixed with a six-character subset tag, hiding the base name
from a naive match.

This is the same class as Section 11.5 (escape characters defeating a search) and
Section 12.6 (a search returning empty because the term is split across a line).
The general form: **a zero result is a claim about your search, not about the
world**, until the search has been shown to find a known instance.

> **Prompt:** Every pattern in this project's checks: show me the string it must
> match and the string it must not. Which patterns have never matched anything?

## 24.4 Empty or wrong input must not score a pass

"No violations found" and "nothing was examined" must be different exit states.

```
count what you actually measured
if the count is zero -> exit with a distinct status, never success
```

**Evidence:** A reference classifier gave a perfect score on an empty file. Every
per-item check passed because there were no items.

## 24.5 Know which end of a cascade wins, and test where the two ends disagree

Where properties compose base-first and override-last, reading the wrong end
reports the **inherited** value instead of the **effective** one. It is right in
every case where nothing was overridden, which is most cases, so it survives
testing.

**Evidence:** A property check read the first occurrence of a toggle in a
concatenated property chain. The chain carried the inherited value first and the
explicit override last. The check reported an element as carrying a property it
had explicitly switched off, and did so only for elements that had been
deliberately corrected.

```
[ ] name which end of the cascade wins
[ ] construct the case where inherited and effective DIFFER
[ ] test there, not on the common case
```

## 24.6 A matcher over a variable-length token needs an explicit boundary

Without one it finds its own quarry **inside** valid input.

**Evidence:** A pattern looking for a label without its terminator matched a
shorter label inside a longer, correct one, and reported a violation in a file
that had none.

## 24.7 The instrument must cover the region the answer lives in

A measurement that **confirms** your suspicion is the cheapest false positive
available, because you stop looking when you find what you expected.

**Evidence:** A rendered crop was taken to check whether a character had been
dropped. The crop ended just below the baseline, which is exactly where that
character sits, and appeared to prove the defect. A taller crop showed it present
all along. The instrument had manufactured the fault it was pointed at.

```
before believing a CONFIRMING measurement:
  [ ] does the instrument's field of view include where the evidence must be
  [ ] does the same instrument show a known-present instance
```

This is the operational partner of Section 7.5 (a display bug is not a finding).
That one says a rendering artefact can look like a result; this one says a
**truncated view** can look like a confirmation.

> **Prompt:** For each measurement in this project that confirmed an expected
> defect, show me the instrument covered the region the evidence lives in.

## 24.8 Compare in both directions, and choose the comparison shape deliberately

"Everything in A appears in B" catches **loss**. "Everything in B appears in A"
catches **invention**. Running one and believing you have covered both is common.

The shape of the comparison must match how the two sides legitimately differ:

```
positional (window, diff, sequence)
  catches : reordering, garbling, local corruption
  drowns  : wherever the target generates its own counters, moves an aside,
            or splits a token differently

membership (multiset, count per item)
  catches : loss, invention, duplication
  blind   : to pure reordering
```

**Evidence:** A first design compared two representations with a sliding window
and produced dozens of findings, none of them defects: the target format
generated its own numbering, moved notes to the foot of a column, and split words
at different points. A multiset comparison reported zero and still caught a
deleted sentence, an altered value and a removed object.

**Rule:** enumerate the ways the two sides may legitimately differ **before**
choosing the comparison. If your check is noisy, the shape is usually wrong, not
the tolerance.

> **Prompt:** List the ways these two artifacts may legitimately differ without
> either being wrong. Then choose the comparison shape, and justify it against
> that list.

## 24.9 A gate must refuse, and the refusal must be tested

Three failures of the same class, all found late:

```
exit status  : a build returned FAILURE on a passing run and SUCCESS on a
               failing one. Nothing downstream noticed, because nothing
               downstream had ever seen it fail.
freshness    : success was proved by the output EXISTING. A stale output from an
               earlier run satisfied that, which is precisely the situation where
               the current run failed.
warning class: the toolchain reported a dropped character as a warning. The
               artifact built, nothing overflowed, and an identifier silently
               lost a character.
```

```
[ ] exit status tested in BOTH directions
[ ] outputs deleted before production, so existence afterwards proves this run
[ ] every warning class that can change what ships is promoted to a failure
[ ] the gate leaves the previous good artifact untouched when it refuses
```

**How to enumerate the third:** read the toolchain's log vocabulary once,
deliberately, and ask of each class **can this change what ships**. Gate on the
ones that can. This is a one-hour task that pays for itself the first time.

> **Prompt:** Does this project's build gate fail on: a wrong exit status, a
> stale artifact, and every warning class that can silently change output? Show
> me the deliberate breakage that proves each.

## 24.10 Distinguish a build that must not stop from one that must not lie

Tolerating a missing input is right for a draft and wrong for a deliverable. The
same configuration cannot serve both.

**Evidence:** A document defined default values for every quantity and then loaded
override files with a mechanism designed never to fail if a file is absent.
Thirty of eighty-five defaults **disagreed** with the real values. With every file
present the correct numbers shipped. With one file missing, a different set of
numbers would have shipped, silently, and the build would have succeeded.

```
draft mode      : missing input tolerated, fallback used
deliverable mode: missing input is FATAL
and in both     : a fallback is VISIBLY wrong (??), never plausibly wrong
```

A plausible default ships as fact. This is Section 19.3 (single source) meeting
Section 5.7 (every hand-written number is a risk): the fallback is a second
source for the same quantity, and it is the one nobody audits.

> **Prompt:** List every value in this project that has both a default and an
> override. Where they disagree, what ships if the override is missing, and does
> the build say so?

## 24.11 A converter must abort, not skip

Any process that transforms a deliverable, and which silently skips what it
cannot handle, produces an artifact that **looks finished and is not**.

**Evidence:** While building a format converter, four defects each produced a
plausible-looking output: a block was dropped whenever an optional element came
first; a style in the target format silently substituted a symbol font, rendering
one alphabet as another; paragraphs merged because the walker never split on
blank lines; and a numbered environment lost its number while the body still
cited it.

Aborting on an unrecognised construct is the kinder failure. It converts an
invisible content defect into a visible build failure.

> **Prompt:** Does every transformation step in this project abort on input it
> does not recognise, or does it skip? Show me what it does with one construct it
> has never seen.

## 24.12 Record which cases fail, never the ratio

A regression control is a statement about **which** conditions an artifact
violates. Written down as a count, it decays twice: the denominator moves as the
check grows, and the artifact itself goes missing.

**Evidence:** A note recorded that a check "fails the earlier artifact on 6 of 8
checks". The check later grew to fourteen, making the ratio meaningless, and by
then the artifact had been cleaned up and could not be re-run to restore it. The
item names and their measured values would still have been true.

```
[ ] the control is a COMMIT REFERENCE and a rebuild recipe, not a stored file
[ ] what is recorded is which items fail and their measured values
[ ] never a ratio; the numerator is stable, the denominator is not
```

This is Section 19.3 again: the count is a second source for something the check
already knows, and it is the copy nobody updates.

> **Prompt:** For every regression control in this project, is it stored as a
> file or as a rebuild recipe? Does the record name the failing items and their
> values, or only a count?

---

# 25. RECEIVING AN EXTERNAL REQUIREMENT

Section 9 handles the literature, Section 13 handles the venue, Section 21.9
simulates a hostile reviewer. This section is about the different task of being
**given a list of corrections by an authority** and acting on it without
introducing new defects.

The failure modes here are almost all **over-reading** and **under-scoping**, and
they are expensive because a defect introduced inside a fix is hard to attribute
later.

## 25.1 A requirement constrains what it names, and nothing else

Reading a requirement more broadly than written creates defects in the act of
removing them.

**Evidence:** A correction said a set of terms must be "9 point and italic". It
was read as "italic **and not bold**", and the weight was stripped. The
requirement never mentioned weight. The original complaint had been that the
terms were upright while the label was not. A property that was correct became
wrong, inside a change described as a fix.

```
before widening a requirement:
  1. recover the artifact AS IT WAS when the complaint was made
  2. compute the delta between that state and the requirement
  3. that delta is the entire ask
  4. anything outside it needs its own justification
```

The second step is the one people skip, and it is the one that carries the
information: the complaint tells you which property was wrong, and the
requirement tells you what it should be. Neither alone is enough.

> **Prompt:** For each item in this correction notice, show me the artifact as it
> was when the notice was written, and the smallest change that satisfies the
> item. Flag anything I am about to change that is outside that delta.

## 25.2 Fix the class, not the flagged instance

When someone marks one thing they have shown you a rule you are violating, and
they will not enumerate the rest.

**Evidence:** A reviewer annotated one object with "is this a table? if so it
must be in the proper format". The same note reappeared later on a different
object, because only the named instance had been fixed. The reviewer's own text
said the rule applied to all such objects, not only the one marked.

This is Section 16.17 seen from the other side: that one says a rule **you**
adopt applies to all your artifacts; this one says a rule **imposed on you**
applies to all instances in the artifact.

## 25.3 Two authorities will disagree, including one authority with itself

A specification and its own worked example routinely contradict each other.
Neither is automatically right.

**Evidence:** A body issued a numbered list of requirements and, in the same
message, attached the example document those requirements were said to describe.
Measured against the list, the example violated four of the numbered items. On
one further point the body's own two reference artifacts disagreed with each
other.

```
resolution rule:
  prefer the LATER and MORE SPECIFIC instruction
  record the disagreement in the artifact's own commentary
  TELL the other party which you followed and why
```

The third line is the one that protects you. Silent choice is the defect, not the
choice itself.

> **Prompt:** Where do this venue's written requirements and its own template
> disagree? List each conflict, which I followed, and whether I said so.

## 25.4 Ground truth is the stored definition, not the rendering

A reference artifact's **appearance** is evidence of what that artifact does, not
a specification of what is required. Where a requirement is expressed in a
producer's own units, the stored declaration is the only fixed reference: the
same conforming file measures differently under different engines, because each
resolves the underlying unit its own way.

**Evidence:** A requirement of "0.95 line spacing" is stored as a ratio against
single spacing. Single spacing for the same font is not the same distance in
three different engines, so one conforming file reports three different measured
values. Checking the rendering measures the renderer.

```
requirement names a stored property  -> check the declaration
requirement names a visual outcome   -> check the rendering
in doubt                             -> check both and reconcile
```

**And the converse:** where a layer between source and output can silently
override the source (Section 24.11), only the rendering can reveal it. The two
rules are not in conflict; they apply to different classes of requirement.

> **Prompt:** For each requirement here, is it a statement about a stored
> property or about a visual outcome? Am I checking it at the right level?

## 25.5 Rules carry their scope with them

A rule acquired from one authority, for one artifact, is not portable. Carried
into a context governed by a different authority it is simply wrong, and it
arrives with the false credibility of having been demanded by somebody.

**Evidence:** In a review of a third artifact prepared for a different venue, a
formatting rule from an earlier venue's correction notice had been carried over
and applied. The receiving venue's own template prescribed the opposite. The
source comment still cited the first venue's item number, which is how it was
found.

```
[ ] every acquired rule is annotated with the authority and artifact it came from
[ ] before applying it elsewhere, re-derive it from THAT context's specification
```

> **Prompt:** Which formatting or structural rules in this artifact were acquired
> from a different context? For each, does the governing specification here
> require the same thing?

## 25.6 Requirements reverse, including after you have implemented and verified them

Doing the work well does not protect it. Treat reversal as a normal event.

**Evidence:** A correction was issued, implemented, measured and verified. A later
message from the same authority corrected the earlier instruction and reversed
part of it, with an apology for the wording. The work was not wasted, but the
values had been written as constants in several dependent places.

```
build so that reversal is cheap:
  [ ] the required value is a parameter, named once
  [ ] anything derived from it is an EXPRESSION of it, not a computed constant
  [ ] the check points at the requirement, not at the number it currently implies
```

See Section 25.9 for why the second line matters more than it looks.

## 25.7 Verify each finding of a review before acting on it

A review is a set of **hypotheses**. Acting on all of it introduces changes for
non-problems and can break correct work.

**Evidence:** An external read of two artifacts produced four findings. Two were
real and were fixed. One was accurate as an observation but not a defect: the
condition it described was bracketed by the surrounding cases. One was a
misreading of an extraction artefact, which the reviewer had themselves hedged;
acting on it would have changed a correct artifact.

```
for each finding: REPRODUCE it, then classify
  real defect        -> fix
  accurate, not a defect -> say why, change nothing
  mistaken           -> say why, change nothing
and report all three classes, not just the first
```

The checking is often where the real finding is. In the case above, chasing the
fourth, mistaken finding is what exposed a genuine hole in the build gate.

> **Prompt:** For each item in this review, reproduce it against the artifact and
> classify it as real, accurate-but-not-a-defect, or mistaken. Show the evidence
> for each classification before changing anything.

## 25.8 For a "must not contain X" constraint, enumerate the channels

The visible channel is the **least** likely to be the leak.

**Evidence:** An anonymity requirement was satisfied in the visible text of a
submission while the same submission carried author-identifying placeholders in
the front matter and would have carried real identities in document metadata had
the fields been filled. Metadata, embedded producer fields, file names,
acknowledgements and incidental artifacts all carry content the eye never audits.

```
[ ] list every channel of the artifact that can carry X
[ ] check each, starting with the ones a reader never sees
[ ] the visible text is checked LAST, because it is the one you already read
```

> **Prompt:** This artifact must not contain [X]. List every channel that could
> carry it, including metadata and file names, and check each.

## 25.9 Write compensations as expressions, never as pre-computed constants

A constant that is correct only because of a value defined elsewhere is silently
wrong the moment that value moves, and reads as arbitrary to the next person.

**Evidence:** A global spacing parameter was introduced to satisfy one
requirement. It **accumulated** with the spacing above every heading, so two
other requirements, already verified, silently went out of specification. The fix
was to reduce the heading values by the amount of the new parameter. Written as
plain numbers the heading values then looked wrong to any reader and would have
broken again on the next change to the global parameter. Written as
`target - parameter` they stayed correct and self-explaining.

```
if a comment is needed to explain why a number is what it is,
the number should have been the expression in the comment
```

**The general rule:** after changing any shared parameter, re-measure **every**
requirement that could depend on it, not only the one you were changing. The
interaction you did not measure is the one that broke.

> **Prompt:** Which quantities in this project are derived from a shared
> parameter? Are they written as expressions of it? After the last parameter
> change, which dependent requirements were re-measured?

---

# 26. DELIVERING THE SAME WORK IN A SECOND FORMAT

Venues, collaborators and archives ask for the same content in a form you did not
author it in. The naive approach, converting and eyeballing, fails silently and
in the direction that matters: content is **lost**, not corrupted, so the result
reads as finished.

## 26.1 Generate into the target's own definitions, not an imitation of them

If the target format has a notion of named styles, structure or numbering,
produce the artifact **in terms of those**, so the formatting comes from the
target's own definitions rather than from anything you assert.

**Evidence:** A document was generated into the recipient's own template package,
with every element carrying one of the template's style identifiers and every
number generated by the target application from the template's own counters. The
result could not drift from the template, because nothing about the formatting
was restated in the generated file.

The alternative, reproducing the look by hand, is a second source for every
formatting decision, and Section 19.3 says how that ends.

## 26.2 Verify the conversion in both directions, with an independent parser

Write the checker so that it shares **no code** with the converter. A check built
on the converter's own parser cannot detect the converter's own bugs.

```
direction 1 : every content word of the OUTPUT occurs in the source or the
              reference rendering        -> catches invention and garbling
direction 2 : every content word of the SOURCE occurs in the output
              -> catches loss
numbers     : compared separately and EXACTLY, with multiplicity
counts      : objects, notes, references compared as integers
```

**Why numbers separately:** a lost object leaves the prose around it intact.
Word-level comparison will not notice, and the numeric comparison will.

**Evidence:** The two-direction check reported clean while a value had been
altered; only the exact numeric comparison caught it. Conversely a deleted
paragraph was caught by the word comparison and by the numeric one, which is the
kind of redundancy you want.

## 26.3 Validate the verifier by damaging a good file

This is Section 24.1 applied to conversion, and it is quick.

**Evidence:** A passing output was damaged four ways and the checker re-run:
```
paragraph deleted   -> caught by word comparison AND numeric comparison
number altered      -> caught by numeric comparison only
object removed      -> caught by object count only
word substituted    -> caught by the invention direction only
```
Each damage class was caught by exactly one or two checks. Removing any single
check would have left a class undetected, and the table is what shows that.

> **Prompt:** Damage a passing output four ways (delete a paragraph, alter a
> number, remove an object, substitute a word) and show me which check catches
> each. List any damage class no check catches.

## 26.4 Establish where each reference is faithful before using it to judge

Every reference has a region where it reports reality and a region where it
degrades. Using it outside that region does not produce uncertainty, it produces
**confident, specific error**.

**Evidence:** Text extracted from a typeset document is faithful for prose and
lossy for mathematics: one extraction dropped a character from a formula and
reordered its parts, while the converted artifact rendered the same formula
correctly. Used as ground truth, the extraction flagged the correct artifact as
wrong. The fix was to accept a token explained by **either** reference, and to
say so in the check's own commentary.

> **Prompt:** For each reference this check compares against, name the region
> where it is faithful and the region where it degrades. Show me one input where
> you already know the answer and the reference reproduces it.

## 26.5 A second format is a second artifact, and every requirement applies to it

A requirement satisfied in the original is not thereby satisfied in the
conversion.

**Evidence:** Of fifteen numbered requirements, three were met in the original and
**not** in the converted artifact, because the target's own style definitions did
not carry them. They had to be applied explicitly in the generated file. Nobody
would have looked, because the original passed.

```
[ ] run the full requirement checklist against the SECOND artifact
[ ] where the target's defaults conflict with a requirement, override explicitly
[ ] where the two artifacts must differ, write down why
```

> **Prompt:** Run the full requirement list against the converted artifact, not
> only the original. Which items does the target format fail to carry by default?

## 26.6 Ship the source package and prove it builds away from your machine

Section 11.10 says run from the delivered archive. Two additions from a
conversion round:

```
[ ] the package contains only the inputs it actually references
[ ] it is built in a THROWAWAY directory before it is sealed
[ ] the artifact the package produces is put through the same checks as the
    artifact you built locally
```

The third is the one that is skipped. A package that builds is not the same claim
as a package that builds **the same thing**.

---

# 27. TEMPLATE CONFORMANCE

Sections 15 and 20 give style rules that hold everywhere. This one is about the
different job of meeting **someone else's** template: a stated set of numbered
requirements, a reference file, and a reviewer who will check.

It is written from one venue's correction cycle, and the concrete values are kept
so the method is legible. Substitute your own.

## 27.1 The reference file is a container; read the stored definitions

A template's **appearance** is evidence of what that file does. Its **stored
definitions** are the specification, and a set of numbered requirements will
usually map one to one onto them. That mapping is the single most useful artifact
you can build, and it takes an hour.

```
unzip the template, then read the style definitions, not the sample page
  style store     <- the specification
  numbering store <- where generated labels and counters come from
  sample document <- useful, not authoritative
```

**Convert the units before believing any number.** In one common format:

```
spacing before/after   twips         pt = twips / 20
font size              half-points   pt = size / 2
line spacing, "auto"   240ths        ratio = value / 240
line spacing, "exact"  twips         pt = value / 20   (does NOT scale)
first-line indent      twips         cm = twips / 566.9
rule weight            eighths-pt    pt = value / 8
```

The auto/exact distinction is load-bearing. An **auto** rule is a ratio against
single spacing and moves when the font does; an **exact** rule is an absolute
distance and ignores any global spread you set. A requirement of "0.95 line
spacing" is the first kind, and a requirement of "9 point leading in the
references" is the second, so a global scale applied to both breaks one of them.

## 27.2 Build the item-to-property table before editing anything

One row per numbered requirement: the stored property it names, the target in
real units, the change that satisfies it, and the value you measured afterwards.

```
item  requirement                     target       measured
----  ------------------------------  -----------  --------
 1    keyword line size and style     9pt          9pt
 2    space before/after main heading 8pt / 4pt    7.93pt
 3    space before/after sub heading  6pt / 3pt    6.02pt
 5    body line spacing               0.95         11.40pt
 6    first-line indent               0.51cm       14.40pt
14    reference leading               exact 9pt    8.97pt
15    space after each reference      2.5pt        2.49pt
```

The last column is the point of the table. An item with no measured value is an
item you have not done, however confident the edit felt.

## 27.3 Some requirements are not properties, and are checked differently

```
requirement names a STORED property  -> check the declaration
requirement names a VISUAL outcome   -> check the rendering
```

Checking a stored property by rendering measures the renderer: the same
conforming file reports different values under different engines, because each
resolves the underlying unit its own way. Checking a visual outcome by reading
the source misses anything a later layer overrode. Section 25.4 has the general
form; the practical consequence is that a conformance suite needs both kinds of
check and must know which item is which.

## 27.4 The template will not carry every requirement

**Evidence:** Of fifteen numbered items, three were satisfied in the primary
artifact and **not** in a second-format deliverable built on the venue's own
template, because the template's own styles did not carry them: two front-matter
paragraphs had no line rule and the wrong indent, and one caption style was
justified where the item required centring. Each had to be overridden explicitly.

Nobody would have looked, because the primary artifact passed. This is Section
25.5.

## 27.5 Generated labels beat typed ones

If the target format generates counters from the template's own definitions,
produce the artifact in terms of those. The numbering then **cannot** drift from
the template, and a typed label is a second source for something the template
already owns (Section 19.3).

## 27.6 Detail displaced from a caption must arrive somewhere

A requirement to shorten captions is a requirement to **move** their content, not
to delete it.

```
before cutting a caption:
  [ ] list every fact it carries
  [ ] locate each in the body, or ADD it there first
  [ ] re-run the reference check: shortening must not cost an object its
      subject-position discussion
  [ ] diff the set of generated values before and after; none may disappear
```

**Evidence:** Shortening eleven captions displaced seed counts, interval
half-widths, panel keys and a rendering disclosure. Three facts existed **only**
in a caption and were written into the body before the caption was cut. A
key-set diff confirmed nothing was lost outright, and six occurrence counts fell
only where the value still appeared elsewhere.

## 27.7 A conformance check needs the artifact it must reject

Section 24.1 in general; for templates specifically, three controls are cheap and
worth keeping:

```
the pre-fix build     rebuilt from a commit, not stored as a file (23.12)
the bare template     a good suite fails the venue's OWN sample on the items
                      where the sample and the written list disagree
an empty document     must report nothing-measured, never a pass
```

The middle one is the surprise. **Evidence:** measured against a committee's own
fifteen items, the sample document distributed with the template failed four of
them. A suite that passes the sample is measuring the sample, not the list.

> **Prompt:** Build the item-to-property table for this template: one row per
> numbered requirement, the stored property it names, the target in real units,
> and a column for the value I measure afterwards. Mark which items are stored
> properties and which are visual outcomes, and say which check applies to each.

> **Prompt:** Run my conformance suite against the venue's own sample document.
> Which items does the sample fail? Those are the points where the written
> requirements and the reference file disagree, and I need to decide and record
> which I follow.

---

# 28. THE INSTRUMENT, THE ARTIFACT AND THE GROUND

Sections 11 and 12 cover what to check and how to run things. This section
covers three failures that sit underneath both: the checker itself can be
wrong, the rendered artifact fails differently from its source, and the
repository and toolchain move without announcing it. A defective check is worse
than no check, because it converts "unverified" into "verified" without passing
through "wrong", and nobody re-examines a green result.

## 28.1 Assert the property, not the workaround

A constraint gets satisfied by a hack. Someone writes a check asserting the hack
is present. The hack is now permanent: removing it fails the audit, so the audit
defends the workaround against its own author.

The tell is a check whose assertion names an implementation rather than a
property. "This spacing override is present" is an implementation. "The body is
at the class default" is a property. Assert the second. Where a check must name
an implementation, record in its comment which requirement it stands for, so a
later reader can tell whether the requirement or the implementation changed.

## 28.2 A check that cannot fail is not a check

Ask of every check: what does it print when the thing it inspects is absent? If
that is the same as when the thing is correct, it is decoration. Loaders that
substitute a default for a missing file, patterns that match nothing and report
nothing, searches that ran against the wrong scope: all report success.

Three exit states, never two: pass, fail, and could-not-run. A skipped check is
an unverified claim and belongs on the unverified list. It is never a pass.

## 28.3 Inject the defect before trusting the check

A check written from a description of a defect rather than from the defect will
run clean on broken input. Two instruments here did exactly that. One missed its
target twice for two unrelated reasons; another needed three calibrations before
it separated real collisions from benign ones, and its first version raised
eleven false alarms on known-good input, enough that a reader would have learned
to ignore it.

Before trusting a check, inject the defect and confirm it fails, then confirm it
passes on good input. A check only ever run on good input has been tested in the
one direction that proves nothing. Keep the injection as a self-test.

## 28.4 Suspect your own instrument first

Measurement code carries silent assumptions about the medium: an anchor that
matches only at line start when content wraps, a case-sensitive match against
text the renderer upper-cased, a font-name substring the actual font does not
contain, a tokenizer that fuses two regions a reader sees as separate.

A surprising negative from your own tooling deserves the scrutiny of a
surprising positive. "Not found" is a claim. When an instrument reports
something structurally implausible, confirm by a second independent path before
reporting it.

## 28.5 Invert a check when a decision reverses, do not delete it

A requirement is reversed, the check that enforced it now fails, so it is
deleted. The decision loses enforcement in both directions and can drift back
with nothing to catch it. Invert it instead, and keep the original requirement
in a comment with who asked and when. A deleted check takes the decision with
it.

## 28.6 Build the artifact and measure the artifact

Source-level checks cannot see overlapping text, a block outside its region, an
element split across a boundary, or a component silently dropped. These are
produced by the renderer, exist only in the output, and pass every source check.
Extract the artifact's geometry and text programmatically. Reserve eyes for what
geometry cannot express.

## 28.7 A defect's size is not its cost

A quantity you measure to judge fit may not scale with severity. A block
overflowing its region by a hair and one overflowing by a page can consume
identical space in the measurement, because the renderer accounts for the block
and not the overflow.

A fit measurement taken while such defects are present is not a measurement of
the fixed document. Repair structural defects first, then measure, and never
report a fit number taken over a document with known layout errors.

## 28.8 Compiles clean is no evidence about content

An unescaped metacharacter makes the processor discard the rest of a region. The
build succeeds, emits no warning, and produces a shorter, coherent-looking
artifact. The damage is indistinguishable from the author having written less,
so there is no ragged edge to notice.

Verify content survives into the artifact by checking for text you know should
be there: the last sentence of each region, not the first.

## 28.9 Every value reads from its generator, in every location

A value flows from a generator through a macro everywhere except one place where
it was typed. The two agree today; the generator re-runs and one updates. Any
literal number in a document that has a provenance system is a defect until
shown to be outside that system.

The mirror case: replacing a generated token with prose that reads better
silently removes a live link. That is a legitimate trade, not a defect, but it
must be recorded, because a re-run will now update every number and not the
sentence.

## 28.10 Verify tree identity before the first edit

Branch pointers get reset, merges land from elsewhere, containers are
re-provisioned from a different revision. The branch name does not change; the
files do. Before the first edit of a session and after any interruption, check
the current commit, the divergence from the remote, and whether the file you are
about to edit matches what you last wrote. Prefer a positive check over the
absence of a complaint.

Anything installed during a session is environment, not repository. A
command-not-found after a gap is an environment event, not a finding.

## 28.11 Fetch before asserting that something does not exist

Others commit to the same branch; your view is a snapshot from the last fetch.
This produced the worst error of the work recorded here: a confident,
evidence-backed statement that a defect did not exist anywhere in the
repository, made after exhaustive local search. It existed, on the remote, in
commits not yet fetched.

Exhaustive search of a stale copy is exhaustive only of the copy. Scope every
negative claim to what was actually searched, or fetch first.

## 28.12 Explore on copies; reset rather than patch forward

Pattern-based edits applied repeatedly during exploration degrade a file in ways
that still parse: guards duplicate, offsets go stale, a replacement lands inside
a previous one. The tell is a parameter sweep where every configuration gives
the same answer, which means the knob is not connected.

Write each candidate to a disposable copy. When exploration has already mutated
the source, reset to the last commit and reapply the intended change once. Have
the sweep report the configuration it actually produced, not the one it
intended.

## 28.13 A fixed size makes every addition a trade

A page limit, a latency ceiling, a payload cap: each converts improvement into
exchange. Reviewers ask for additions, each reasonable, together unaffordable,
and the reflex is to cut something the reviewers liked.

Most of what reviewers ask for is often already present and merely invisible:
the answer sits inside a sentence that does not announce it. Folding the answer
into the sentence that already carried the point recovers most of the length at
no cost to content. Before cutting anything, check whether the requested content
already exists unmarked. A request is frequently a visibility defect rather than
a content defect, and the two have entirely different prices.

## 28.14 Enumerate fixes before choosing one

A defect usually has more than one remedy, and their costs can differ by a whole
unit of budget. Here one defect had two fixes: forcing a block to stay together
cost a full page, while changing where an adjacent float was allowed to sit cost
nothing. The expensive fix was the obvious one and was found first.

When budget binds, enumerate candidates and measure each. The intuitive remedy
often pays the renderer's price instead of working with it.

## 28.15 Layout is a search, not a deduction

Predicting placement from a renderer's documented rules is slow and unreliable,
because placement depends on global state you do not hold. When a renderer is
available, treat it as an oracle: generate candidates, render each, measure.
Reason only about which candidates are worth trying.

## 28.16 A reversal is three edits

Over a long engagement the same decision is revisited as reviewers, editors and
collaborators weigh in. A parameter is set, unset and set again; each individual
instruction is legitimate. What goes wrong is that the artifact and its
enforcement drift apart, because a reversal updates the artifact and forgets the
check, the comment, or the sibling document.

Treat every reversal as three edits: the artifact, the thing that enforces it,
and the record of why. Keep a running list of decisions that have flipped, with
who asked and when, because the next person to raise it will not know it has
been settled twice. In the work recorded here, eight decisions reversed and two
of them reversed twice.

## 28.17 Identify which build a review was written against

Reviews are written against a specific build, and by the time they arrive that
build is history. Items already fixed sit beside items still live with nothing
distinguishing them. Where the reviewer supplies the artifact, diff it against
current; otherwise check each reported defect against the current build. Report
which items were already resolved. Acting blind on a stale list re-introduces
work and can undo the fix that resolved the complaint.

## 28.18 Surface conflicting instructions instead of choosing silently

A template, a venue editor, a house style guide and a collaborator can each
specify something incompatible. Following the newest instruction silently breaks
an older commitment someone made in writing. When a new instruction contradicts
a standing one, surface the conflict with the evidence for both, say which you
did not do and why, and let whoever owns both decide. When they decide, apply it
fully and update whatever enforced the old state.

Two related habits. When evidence settles a question the requester thought open,
give the resolved answer rather than presenting a disproved option as a live
alternative. When the sanctioned change set is insufficient, finish everything
possible within it and report the shortfall rather than widening it.

## 28.19 Correct a belief-changing error explicitly, once

When you state something confidently and it turns out wrong, and the error
changed what someone concluded, name it plainly at the point where it matters
and say what the truth is. Do not bury it, do not over-apologise, do not
re-litigate. A wrong statement that changed someone's belief is the one kind of
error that must be named rather than quietly fixed.

---

# 29. SUMMARY

The weak point of an experimental paper is usually not the result: it is how you
know the result measures the right thing, and whether the claim already exists in
an adjacent literature.

The first is solved by a primary-source anchor, a deliberately wrong control
condition, and a measurement that is a direct consequence of the property
claimed; the second by searching for the concept's **function**.

Both come before reporting, and when both are skipped it is entirely possible to
produce a consistent but wrong result.

---

Two further threads were added later, from a project whose failures were all
**silent**: nothing announced itself, the build never failed, and every artifact
looked finished while being wrong.

Confidence therefore has to come from comparing the delivered artifact against an
independent authority, which makes the verification code itself an object
requiring verification (Section 24); and an external correction is a hypothesis
about your artifact, to be scoped to exactly what it names and re-derived before
it is carried anywhere else (Section 25).

A third thread, Section 28, comes at the same problem from the production side.
A claim rests on three things that are easy to confuse: the instrument that
checks it, the artifact a reader actually receives, and the repository state the
work was done against. Each can be sound while the other two are stale or wrong,
so each has to be established separately rather than inferred from the others.
