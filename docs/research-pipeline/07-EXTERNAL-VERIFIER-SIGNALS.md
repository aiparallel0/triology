# Domain Patterns — External Verifiers as Selective-Prediction Signals

**Scope.** Generalised from one study: an arithmetic check used to decide
whether to trust a model's extracted total. The receipt is an instance. The
class is **any task whose output admits a structural constraint that can be
checked without consulting the model.** Balancing tables, schemas with
referential integrity, code with type checks, plans a solver can validate, units
that must cancel, totals that must sum. Everything below is written for that
class; the receipt appears only where it makes a mechanism concrete.

**Relationship to the rest of this playbook.** `02-EVIDENCE-AND-CLAIMS.md` gives
the claim-strength ladder generally. This file gives the rungs that this
particular *kind* of result keeps falling off.

---

## A. The construction

### A1 — The deterministic verifier as a confidence signal

**Class.** When a task's output must satisfy a checkable structural constraint,
a deterministic verifier of that constraint is a **selective-prediction signal**
whose errors are governed by the structure of the input rather than by the
model's internals.

**Why it is worth measuring.** The default signal in a neural pipeline is the
model's own confidence. It is a property of the generator, so the process that
produces a confident error is the same process asked to detect it. A verifier
that never reads the model does not inherit that failure mode.

**What it is not.** It is not a better calibrator, and framing it as one invites
the reviewer to ask why you did not simply recalibrate. The claim is about
**where the signal comes from**, not about how well it is scaled.

### A2 — Orthogonality is disjoint error, not dominance

**Class.** Two signals combine usefully when they **fail on different inputs**.
Neither has to beat the other on any aggregate.

**Consequence for how results are presented.** The strongest evidence for the
construction is often a stratum where the two signals are *exactly equal* in
standalone accuracy and still improve when intersected. That case looks
unremarkable in a table of aggregate scores and is the most persuasive cell you
have. Present it as such.

**Failure to avoid.** Arguing dominance when the data show orthogonality.
It overclaims, and it is refutable by a single stratum where the other signal
wins.

### A3 — The witness exists by construction, and what voids that

**Class.** For a well-formed input the structural constraint is satisfiable by
definition: the checked quantity *is* a function of the visible parts. This is
what makes the verifier sound rather than heuristic.

**The clause that matters.** "Well-formed" is doing all the work. Enumerate what
voids it — inputs where the parts are not recoverable, where the constraint
holds only approximately, where upstream extraction is lossy — because that
enumeration is the honest boundary of the method and a reviewer will look for
it.

### A4 — Guarding against the trivial witness

**Class.** Any constraint checker admits degenerate satisfactions: a single part
that equals the whole, an empty subset, an identity. Without a guard the
verifier accepts these and its precision is meaningless.

**The generalisable shape.** The guard's correct setting is **regime-dependent**
— in one regime the degenerate case is a coincidence and must be excluded; in
another it is the legitimate, intended match and excluding it destroys coverage.
Do not pick one setting globally. Determine the regime, and see C1 for how to
determine it without labels.

### A5 — Composition at a matched operating point

**Class.** Comparing a threshold-free signal against a thresholded one is
meaningless at arbitrary thresholds. **Match the operating point** — set the
comparison signal's threshold so both accept the same fraction — and compare
accuracy there.

**Why this is not a detail.** Without it, every reported gain is confounded with
a coverage change, and the entire result collapses into C-class "you accepted
fewer things and were righter about them". See B2.

---

## B. What the claim may be

### B1 — Novelty of the technique versus novelty of the measurement

**Class.** For a construction drawn from long-standing engineering practice,
these are two different claims at two different rungs:

| Claim | Rung | Defensibility |
|---|---|---|
| the technique is new | high | usually false for practice-derived methods, and one counterexample kills it |
| *the measurement of it as a signal of this kind* is not in the literature | lower | survives, because it is a statement about a specific evaluation |

**Rule.** State the disclaimer once, precisely, and do not repeat it. A paper
that keeps insisting it claims no novelty is signalling anxiety about a claim it
has already conceded, and reviewers read the repetition as the tell it is.

**Where the repetition comes from.** Every time a reviewer challenges the
novelty, the temptation is to add another disclaimer in another section. The
result is the same sentence four times. Fix it at the source: one statement, in
the section where the literature is discussed.

### B2 — The two quantities that sound like one

**Class.** These constructions produce at least two distinct statistics that
plain English conflates:

- the **effect** — how much accuracy improves when both signals must agree;
- the **mechanism** — how decorrelated the two signals' errors are.

They can have different scopes. The effect may reach significance only in the
pool while the mechanism holds within every stratum. Both statements are true,
and placed near each other without naming their subjects they read as the
paragraph contradicting itself.

**Rule.** **Name the quantity in the sentence, every time**, especially in the
sentences that state scope limits. "It does not hold per stratum" is unreadable;
"the *precision lift* does not reach significance per stratum, while the *error
decorrelation* does" is a result.

### B3 — Pooled significance is not per-stratum significance

**Class.** A pooled test with a large combined n will clear a threshold that no
individual stratum clears. This is not a trick; it is power. It is also not a
per-stratum claim, and stating it as one is a rung violation.

**Rule.** If the pooled result passes and the strata do not, say exactly that,
and say whether the strata fail because the effect is absent or because they are
underpowered — those are different and the distinction is testable.

### B4 — The pool inherits its largest stratum

**Class.** When strata are unevenly sized, a pooled number is a weighted
statement dominated by the biggest one. It can be reported honestly and still
mislead, because readers hear "across all data" and not "mostly the largest
set".

**Rule.** Report the stratum sizes next to the pooled figure and say which one
carries it. Where they disagree, make the **per-stratum table the headline** and
the pool the supporting number.

### B5 — Small cells license consistency statements only

**Class.** A cell with a handful of accepted items can produce a perfect score
and a confidence interval so wide it excludes nothing interesting.

**Rule.** Such a cell supports "consistent with the overall finding" and nothing
stronger. Never let a small perfect cell appear in a summary without its n
attached, and never let it be the sentence a reader remembers.

### B6 — Absence of asymmetry is not evidence of independence

**Class.** A paired test showing neither signal is systematically better than
the other is a **null on asymmetry**. It is routinely misread as positive
evidence that the signals are independent.

**Rule.** If you want the independence claim, run the test that measures it
directly — correlation of errors within the accepted set, against a control that
holds coverage fixed. Then say which test supports which claim. Keep the
asymmetry null as what it is: an absence of evidence, not evidence of absence.

---

## C. Design choices reviewers attack

### C1 — Any hyperparameter chosen with labels

**Class.** A setting tuned on labelled data cannot be set that way at deployment
time, and a reviewer will say so.

**The pattern that survives.** Choose it from a **computable property of the
unlabelled input stream**, show the strata separate cleanly on that property,
and show the choice is insensitive across a range. Then it is a deployment rule
rather than a fitted parameter, and you can say so in one sentence.

**Corollary.** When you also report a sweep over that setting, label it
explicitly as an ablation of the rule, or it reads as the tuning you just denied.

### C2 — Attributing a loss to an upstream stage

**Class.** The verifier underperforms in one regime. The convenient explanation
is that an upstream component is at fault. This is the most self-serving claim
available and needs evidence, not plausibility.

**The shape of adequate evidence.** A measurable property that differs between
the wrongly-accepted and correctly-accepted cases in the direction your
explanation predicts, with a test — plus a second property that your explanation
predicts should *not* differ, shown not to. The second half is what separates an
account from a story.

**Rule.** State the strength honestly. With a small number of failures this
"supports the account rather than settling it", and naming the study that would
settle it is worth more than an extra adjective.

### C3 — Regime dependence is a finding

**Class.** The signal wins in one input regime and loses in another. The
temptation is to bury this or to average it away.

**Rule.** Report the regimes and the mechanism that explains them. "Each signal
owns a regime" is a stronger and more useful result than a uniform average, and
it tells a practitioner which one to deploy. Averaging destroys exactly the
information a reader needs.

### C4 — The baseline class that does not exist

**Class.** The obvious comparison baselines all share the property your method
exists to avoid — every one of them reads the model's internals. Comparing
against more of them adds no information about the thing you claim.

**Rule.** Say this explicitly as a limitation: you compare against one
representative internal signal; the alternatives are the same *kind* of signal;
and the baseline you would want — a second **external** verifier — you know of
none published. That is a scope statement a reviewer can accept. Silence on it
reads as an omission.

### C5 — Two architectures is a claim about generality

**Class.** Testing on structurally opposite designs is what licenses "the result
does not depend on the model". Testing on two similar ones does not.

**Rule.** Choose the second system for *maximal architectural distance*, and say
why the distance matters. Also state where the two are not comparable — a
confidence score from a generative decoder and from a token classifier are
architecture-appropriate analogues, not the same number, and treating them as
interchangeable is a defect a careful reviewer will find.

---

## D. Operational framing

### D1 — Coverage is the price; state the exchange rate

**Class.** These constructions buy accuracy with abstention. A result that
reports only the accuracy gain is incomplete and reads as marketing.

**Rule.** Report the coverage cost in the same breath, in the abstract as well
as the results. Then give the **condition** under which the trade pays — the
ratio of the cost of an undetected error to the cost of a human review — and
state that it is a condition, not a universal claim. Naming the regime where it
does *not* pay makes the rest credible.

### D2 — The verifier's cost against the decision's cost

**Class.** A deterministic check is usually orders of magnitude cheaper than the
inference it guards. That makes latency a non-issue, and saying so in three
sentences is two too many.

**Rule.** State the measurement, state the comparison once, and state what you
did **not** measure — end-to-end ratio on the deployment hardware is usually
absent, and claiming deployability without it is a rung violation.

### D3 — Measurement populations are not evaluation populations

**Class.** Secondary measurements — timing, resource use, ablations — are often
taken over a different subset than the headline evaluation, because they need
inputs the main pipeline does not persist.

**Failure mode.** The paper reports one n everywhere and a different n in one
figure, with no explanation. A reader reads the smaller number as missing data.

**Rule.** Where a measurement covers a subset, **say which subset and why, in
the caption**, positively: what the subset has, not what the remainder lacks.
And derive the count from the generating artifact rather than typing it (see
`06`, B4).

### D4 — Robustness that degrades the right way

**Class.** For a verifier, the valuable robustness result is not that accuracy
is unchanged under corruption, but that the failure mode is **conservative**:
coverage falls while accuracy holds. The check becomes more selective, and
selectivity is the safe direction.

**Rule.** Design the stress test to expose the direction of degradation, and
report it as direction, not just magnitude. A method that gets quieter under
noise is deployable; one that stays confident is not.

---

## E. Transfer conditions

Before reaching for this construction on a new task, all four must hold:

1. **A checkable invariant exists** over the output and something visible in the
   input, computable without the model.
2. **The invariant is closed** — satisfiable by construction on well-formed
   input, not merely usually true. Otherwise the verifier's rejections are
   confounded with its own incompleteness.
3. **The target is a parsed value**, not raw generated text. Format variation
   must be normalised upstream, and that normaliser is part of the system whether
   or not you benchmark it.
4. **Errors are plausibly decorrelated** from the model's confidence — the
   invariant depends on input structure rather than on the same features the
   model scores.

Where all four hold, the pattern transfers and the evaluation design in this
file transfers with it. Where the second fails, you have a heuristic filter, and
it must be evaluated and described as one.
