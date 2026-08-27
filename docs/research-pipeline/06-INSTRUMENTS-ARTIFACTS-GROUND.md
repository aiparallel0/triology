# Instruments, Artifacts, and Ground

**What this adds.** `01-FAILURE-CATALOG.md` is about the number and the sentence
about it. `paper/asyu/audit/` is about whether the rendered artifact conforms.
Neither covers the three things that failed most often once both of those were
in place:

- the **instrument** that does the checking, which can be wrong in ways that
  look exactly like passing;
- the **artifact**, which is not the source and fails differently from it;
- the **ground** — repository state, toolchain, remote, working tree — which
  is not stable and does not announce when it moves.

Every entry is a class. The instance that produced it is named only where it
makes the mechanism legible. Nothing here is hypothetical.

---

## A. The instrument can be wrong

A check is code. Code has defects. A defective check is worse than no check,
because it converts "unverified" into "verified" without passing through
"wrong", and nobody re-examines a green result.

### A1 — The check that encodes a workaround as a requirement

**Mechanism.** A constraint is satisfied by a hack. Someone writes a check that
asserts the hack is present. The hack is now permanent: removing it fails the
audit, so the audit defends the workaround against its own author.

**Tell.** A check whose assertion names an implementation rather than a
property. "`\linespread{0.95}` is present" is an implementation. "The body is at
the class default" is a property.

**Rule.** Assert the property, not the mechanism that currently delivers it.
When a check must reference an implementation, write in its comment which
requirement it stands for, so a later reader can tell whether the requirement or
the implementation is what changed.

### A2 — The check that cannot fail

**Mechanism.** A verification step whose failure mode is indistinguishable from
its success mode. A loader that substitutes a default when the file is missing.
A pattern that matches nothing and reports no match. A search that ran against
the wrong scope and found nothing.

**Tell.** Ask of every check: *what does it print when the thing it inspects is
absent?* If the answer is the same as when the thing is correct, it is not a
check.

**Rule.** Make absence loud and distinct from correctness. Three exit states,
not two: pass, fail, and **could-not-run**. A skipped check is an unverified
claim and must be recorded as one; it is never a pass.

### A3 — The check never tested against the defect it names

**Mechanism.** A check is written from a description of a defect rather than
from the defect. It compiles, runs, reports clean, and would have reported clean
on the broken input too.

**Cost when skipped.** Two instruments in this repo failed this way. One missed
its target defect twice in a row for two unrelated reasons before it worked. A
second needed three calibrations before it separated true collisions from
benign ones, and its first version produced eleven false alarms on
known-good input — enough that a reader would have learned to ignore it.

**Rule.** Before trusting a check, **inject the defect and confirm it fails.**
Then confirm it passes on the known-good input. A check that has only ever been
run on good input has been tested in one direction, which is the direction that
proves nothing. Keep the regression as a self-test the suite runs.

### A4 — The instrument's own false positives and false negatives

**Mechanism.** The measurement code carries assumptions about the medium that
are silently wrong: an anchor that matches only at line start when the content
wraps; a case-sensitive match against text the renderer up-cased; a font-name
substring that the actual font does not contain; a tokenizer that fuses two
regions the reader sees as separate.

**Tell.** A surprising *negative* result from your own tooling deserves the same
scrutiny as a surprising positive. "Not found" is a claim.

**Rule.** When an instrument reports something structurally implausible —
a section that should exist and does not, a count that jumps — suspect the
instrument first and confirm by a second, independent path before reporting.
Report the correction plainly and move on.

### A5 — The check discarded when the decision reverses

**Mechanism.** A requirement is reversed. The check that enforced it is now
failing, so it is deleted. The decision loses its enforcement in both
directions, and the reverted state can drift back with nothing to catch it.

**Rule.** **Invert the check, do not delete it.** Keep the original requirement
in a comment with who asked for it and when, so the next reader can see that the
reversal was a decision rather than an omission. A deleted check takes the
decision with it.

---

## B. The artifact is not the source

Source-level checking is cheap and finds a real class of defect. It cannot see
the failures that only exist once the source is rendered.

### B1 — Clean at source, broken in the artifact

**Mechanism.** Every source-level check passes. The rendered output has
overlapping text, a block outside its region, an element split across a
boundary, or a component silently dropped. None of this exists in the source;
it is produced by the renderer's layout decisions.

**Rule.** For any pipeline that renders, **build the artifact and inspect the
artifact.** Extract its geometry and text programmatically, not only by eye.
Reserve eyes for what geometry cannot express.

### B2 — The defect whose size is not its cost

**Mechanism.** A quantity you measure to judge fit does not scale with the
severity of the problem. A block that overflows its region by a hair and one
that overflows by a page can consume identical space in the measurement, because
the renderer accounts for the block, not the overflow.

**Consequence.** A fit measurement taken while such defects are present is
**not a measurement of the fixed document.** It will read as fitting and then
change when the defect is repaired.

**Rule.** Fix structural defects **before** taking any measurement that depends
on layout, and re-measure after. Never report a fit number taken over a
document with known layout errors.

### B3 — Silent truncation that compiles

**Mechanism.** A metacharacter appears unescaped in content. The processor
interprets it as syntax and discards the remainder of the region. The build
succeeds, emits no warning, and produces a shorter, coherent-looking artifact.

**Why it survives review.** The damage is indistinguishable from the author
having written less. There is no ragged edge to notice.

**Rule.** Treat "compiles clean and looks plausible" as **no evidence at all**
about content completeness. Verify that content survives to the artifact by
checking the artifact for content you know should be there — the last sentence
of each region, not the first.

### B4 — The hardcoded twin of a generated value

**Mechanism.** A value flows from a generator into the document through a macro
everywhere except one place, where it was typed. The two agree today. The
generator re-runs; one updates.

**Tell.** Any literal number in a document that has a provenance system is a
defect until proven to be outside that system's scope.

**Rule.** Every value with a generated source reads from that source. Where a
literal is genuinely correct — a threshold the design fixes, not a measurement —
say so at the site.

### B5 — Provenance lost to a prose rewrite

**Mechanism.** A generated token is replaced by prose that states the same thing
more readably. The statement is now hardcoded. If the analysis re-runs and the
result changes, every number updates and the sentence does not.

**Rule.** This is a legitimate trade, not a defect — readable prose beats a
leaked status flag. But it **must be recorded**, because the document has
silently lost a live link. Name it when you make it. Prefer keeping the
generated value somewhere on the page even when the prose carries the meaning.

---

## C. The ground moves

The repository, the toolchain, and the remote are inputs. They change without
telling you, and every one of them changed inside a single working session.

### C1 — The working tree is not the branch you think

**Mechanism.** A branch pointer is reset, a merge lands from elsewhere, a
container is re-provisioned from a different revision. The branch *name* is
unchanged. The files are not.

**Cost when missed.** Edits land on the wrong content and are then committed as
if they were incremental.

**Rule.** Before the first edit of a work session, and after any interruption,
**verify tree identity**: current commit, divergence from the remote, and
whether the file you are about to edit matches what you last wrote. Prefer a
positive check ("this file equals my last commit") over the absence of a
complaint.

### C2 — The toolchain is not permanent

**Mechanism.** Anything installed during a session — compilers, converters,
libraries — is part of the environment, not the repository. A recycle removes
it. The next command fails in a way that reads like a defect in the work.

**Rule.** A `command not found` after a gap is an environment event, not a
finding. Re-provision and continue. Never let it be reported as a change in the
project's state.

### C3 — The remote moved while you worked

**Mechanism.** Others commit to the same branch. Your local view is a snapshot
from whenever you last fetched.

**Cost when missed.** This produced the single worst error in the session: a
confident, evidence-backed statement that a defect **did not exist anywhere in
the repository**, made after searching local history exhaustively. The defect
existed, on the remote, in commits not yet fetched. Exhaustive search of a stale
copy is exhaustive only of the copy.

**Rule.** Before any claim of the form *"X does not exist in this repository"*,
**fetch**. Scope every negative claim to what was actually searched: "not in the
local tree at `<commit>`" is defensible; "not anywhere" needs the fetch.

### C4 — Cumulative edits corrupt

**Mechanism.** A pattern-based edit is applied repeatedly during exploration.
Each pass matches slightly differently. Guards duplicate, offsets go stale, a
replacement lands inside a previous replacement. The file degrades in ways that
still parse.

**Tell.** A parameter sweep in which every configuration produces the same
result, or a result that is impossible. Both mean the knob is not connected.

**Rule.** When exploring, **never mutate the source.** Write each candidate to a
disposable copy. When an exploratory pass has already mutated the source, do not
patch forward: **reset to the last commit and reapply the intended changes
once**, deliberately.

### C5 — The unverified assumption inside a sweep

**Mechanism.** A sweep varies two parameters, but one edit silently fails to
apply, so the second parameter never changes. Every row looks like evidence and
is actually one configuration measured five times.

**Rule.** Have the sweep **report the state it actually produced**, not the
state it intended. A configuration count printed from the file beats a
configuration count printed from the loop variable.

---

## D. The instruction is not always coherent

### D1 — Two authorities, one artifact

**Mechanism.** A template, a venue editor, a house style guide, and a
collaborator each specify something incompatible. Following the newest
instruction silently breaks an older commitment that someone made in writing.

**Rule.** When a new instruction contradicts a standing one, **do not silently
pick**. Surface the conflict with the evidence for both, say which you did not
do and why, and let the person who owns both decide. When they decide, apply it
fully and update whatever enforced the old state (see A5).

### D2 — The premise that is already stale

**Mechanism.** A review, a critique, or a task list is written against an older
revision. Some items are already fixed; acting on them re-introduces work or
undoes improvements.

**Rule.** **Verify each reported defect against the current artifact before
acting.** Report which items were already resolved. This is not pedantry: it is
the difference between an editor's list and a list of things that are true.

### D3 — The choice that evidence has already resolved

**Mechanism.** A request offers two options and asks for both, on the assumption
that the answer is unknown. Investigation resolves it.

**Rule.** When evidence settles a question the requester thought open,
**say so and give the resolved answer**, with the evidence. Presenting a
disproved option as a live alternative is a false choice, and it transfers a
decision back to someone who now has less information than you.

### D4 — Scope is part of the instruction

**Mechanism.** A task specifies exactly which places may be changed to make room
for a fix. Exceeding that scope quietly rewrites material that was already
settled and reviewed.

**Rule.** When the sanctioned change set is insufficient, **finish everything
possible within it and report the shortfall**, rather than widening it. Scaling
scope is the requester's decision.

### D5 — The correction you owe

**Mechanism.** You state something confidently and it turns out to be wrong, and
the error changed what the other person concluded.

**Rule.** Correct it plainly, once, at the point where it matters, with what the
truth is. Do not bury it, do not over-apologise, do not re-litigate. A wrong
statement that changed someone's belief is the one kind of error that must be
named explicitly rather than quietly fixed.

---

## E. The rules, compressed

1. Assert the property, never the workaround that currently satisfies it.
2. Every check has three outcomes; could-not-run is not a pass.
3. Inject the defect and watch the check fail before you trust it.
4. Suspect your instrument when its result is structurally implausible.
5. Invert a check when a decision reverses; deleting it loses the decision.
6. Build the artifact and measure the artifact.
7. Repair layout defects before measuring anything layout-dependent.
8. "Compiles clean" is not evidence about content completeness.
9. Every generated value reads from its generator, in every location.
10. Record it when readable prose replaces a live link.
11. Verify tree identity before the first edit and after any interruption.
12. Fetch before asserting that something does not exist.
13. Explore on copies; if the source got mutated, reset and reapply once.
14. Make sweeps report the state they produced, not the state they intended.
15. Surface conflicting instructions instead of silently choosing.
16. Check reported defects against the current artifact before acting.
17. Resolve a false choice with evidence rather than answering both halves.
18. Report a shortfall inside scope rather than widening scope.
19. Correct a belief-changing error explicitly, once.
