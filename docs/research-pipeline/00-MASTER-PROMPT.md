# Master Prompt — Empirical Paper Pipeline

**Hand this file to an agent as its standing instruction** when the task is:
*run experiments and turn the results into a paper.*

It is the operating instruction for the half of the work that happens **before**
formatting: choosing a benchmark, running a pipeline, deciding what the numbers
mean, and writing sentences that survive a reviewer. For captions, page limits,
templates and float references, use the venue-conformance playbook instead —
see *Scope* below.

Every rule here exists because something in `aiparallel0/triology` or
`aiparallel0/arith-gating` actually went wrong. The evidence is
[01-FAILURE-CATALOG.md](01-FAILURE-CATALOG.md), 52 failures across 221 commits,
each with its commit hash. Nothing is hypothetical.

---

## Scope, and what this does not cover

| This playbook | The venue-conformance playbook |
|---|---|
| benchmarks, leakage, power, claims, provenance, pipeline reliability, scope churn | templates, captions, float references, page limits, headings, packages |
| "is the number real, and is the sentence about it true?" | "does the rendered artifact conform?" |
| Phases 0–4 below | Phases 5–8 below |

They compose. Run this one first: **formatting is a function of content, and
content is a function of results.** Reformatting after every result change was
the single largest source of rework in the source project.

---

## The nine prime directives

**D1 — The artifact is the evidence, never the description of it.**
Read the label schema, not the paper's table describing it. Load the annotation
file and count the classes. FATURA's paper documents 24; the shipped annotations
have 13, with `Subtotal_value` and `Tax_value` silently merged into `OTHER`
(A3). SROIE Task-3 has four fields and the method needed six (A1). Both were
discovered after design work.
*Applies equally to your own prior output: re-derive, don't re-trust.*

**D2 — Leakage is checked per checkpoint, not per corpus.**
Which split was this checkpoint fine-tuned on? It is a property of the
checkpoint, invisible in the data loader, and it makes every number better.
CORD-v2 *train* is the Donut fine-tuning split; a run over train+validation+test
was training-contaminated and every cell improved (B1). Write the
(checkpoint → trained-on split) table in Phase 0 and keep it in the repo.

**D3 — A claim is a sentence, and the sentence is what fails.**
The numbers in the source project were, with the exceptions in family D,
correct. What failed was the sentence wrapped around them: a null reported
without its minimum detectable effect (C1), a ratio that was conjunction
arithmetic reported as signal (C2), a superlative the stratified data did not
support (C6). Before writing a claim, state what would have to be true for it to
be false, and check that.

**D4 — Compute both forms of every headline comparison before writing it.**
Absolute and relative. Pooled and per-corpus. If they disagree, that
disagreement *is* the finding. In the source project the relative-risk form
reversed the conclusion (35% vs 26%) and a reviewer found it, not the authors
(C3). The correct response was to flip the narrative, not the metric
(`c7cc3eb`).

**D5 — One source of truth per number, and an artifact that backs it.**
Every number in a paper resolves to exactly one generated file, which resolves
to exactly one run artifact. A latency figure with nothing measuring it is not a
number (D1); the fix was two commits, and the second — committing the
measurement artifact beside the paper — is the one that mattered. Corollary:
every total is asserted against the sum of its parts, in code. Table III's
pooled McNemar row printed 183/186 where the per-corpus rows summed to 185/188
(D4).

**D6 — Fix the closure, not the file you noticed.**
Decontaminating a result does not regenerate what was derived from it. In the
source project one leakage fix required: restore the clean run JSONs → recompute
the pooled aggregate (it was cached, B2) → regenerate two figures → re-run five
dependent analyses (B3) → **rewrite the prose that argued from the old numbers**
(B4). Six steps. The last is the one that gets skipped, because by then
everything looks correct.

**D7 — Assert the shape of the data at every boundary.**
Not the values — the shape. n after each filter (SROIE silently collapsed 347→7
because Donut emits `<s></s>` on schema mismatch, F5). Counts non-negative and
not `None` (figures printed `n=-217` and `n=None`, D6). Parse rate and accuracy
reported as two numbers, never one standing in for the other (93% parseable,
69% wrong, A4). Macro defaults overridden (D7). Output paths (F7). Device counts
(F2).

**D8 — Write findings into the artifact, not the commit message.**
Most of the failure catalog had to be reconstructed from commit messages,
because that is the only place those findings exist (D8). A defect found, fixed
and described in a commit message is invisible to the paper, to the next
session, and to you in a week. Keep a tracked defect register and an
`UNVERIFIED.md`. Items that live only in a conversation do not survive it.

**D9 — Do the sibling in the same commit.**
Two papers, three artifacts each. In the source project nearly every commit has
a hand-applied twin days later — hyperref settings, em-dash removal, overflow
guards, gitignore, and the leakage decontamination itself (H1). Divergence is
invisible because each artifact looks fine alone. If a change is right for one,
apply it to all in one commit, or write down why not.

---

## Eight standing constraints

1. **No headline before its enabling result exists.** The source project's own
   scoping document says it in capitals: *"Do NOT commit to a headline claim
   before MB + MF are run."* That discipline held, and it is why Paper 1's
   framing survived where the predecessor's shifted three times (G1).

2. **Pre-commit the effect-size threshold, before you see the verdict.**
   `5a1edfa` required ≥0.02 AUROC rather than merely CI>0, and the honest
   negative verdict followed. A threshold chosen after the result is not a
   threshold.

3. **Report the pessimistic bound.** Wilson lower bound, not the point estimate.
   Leave-one-corpus-out worst case alongside any pool. A pooled n=1019 carried
   114/184 by a single corpus is a one-corpus result wearing three corpora (C9).

4. **Small cells are consistency statements, not results.** n=15 at 15/15
   supports a Wilson lower bound of 0.796. Say "consistency only" every time
   (C8).

5. **Report no digit you cannot defend.** p < 10⁻²⁸¹ is below double-precision
   underflow — an artifact, not a measurement. Keep the substantive statistic
   (W=508, T=1285) and bound p conservatively (C5). *Address correctly; do not
   under-address.* Weakening a true strong claim to a vague one is also a defect.

6. **A cleanup rule needs an exception test.** A pass that rewrote code-like
   tokens into plain prose deleted real dataset and annotation names, and took
   three commits to undo (E4). Before applying any rule document-wide, ask: does
   this instance name a real object a reader must be able to look up?

7. **Delete what you cannot verify.** An unresolvable citation was removed even
   though it weakened a related-work paragraph (E1). A `\cite` with no bib entry
   is caught by `grep -ci undefined` on the log, which costs nothing and was not
   run (E2).

8. **Fix the title last.** Nine titles across two papers (G3), at least two of
   them pure taste. A title is the cheapest thing to change and the easiest to
   defer.

---

## The eight-phase procedure

Each phase has an **exit condition**. Do not start the next phase until it
holds. The order is not stylistic — see [03-LIFECYCLE.md](03-LIFECYCLE.md) for
what each out-of-order transition cost.

### Phase 0 — Feasibility and ground truth
Before any experiment.

- Resolve every dataset to a **primary source**. "FATURA-2" does not exist (A2).
- Load actual annotation files. Count distinct labels. Confirm every field the
  method needs is separately labelled (A1, A3).
- Write the **(checkpoint → fine-tuned-on split)** table. This is D2, and it is
  the single highest-value hour in the project (B1).
- Compute the **minimum detectable effect** from the split sizes you will
  actually have. If the claim you intend needs 1,200 receipts and the benchmark
  has 100, you have learned that now rather than in revision (A6, C1).
- Cross-check the idea against **your own prior work** before the literature
  (G2).
- Record the venue's page limit and deadline.

> **Exit:** a `GROUND_TRUTH.md` containing the schema check, the leakage table,
> the MDE per corpus, and the page limit. Every later "we can't, because…" is
> traceable here.

### Phase 1 — A pipeline that fails loudly
Before spending compute.

- Assertions at every boundary (D7): n floors after each filter, dtype, output
  path, device count, non-null counts.
- Missing-script and worker-crash guards, so a failure crashes rather than
  hangs (F3).
- A smoke run: the full pipeline end to end on ~10 examples, in minutes.
- **Prove it fails.** Break a script deliberately and confirm the orchestrator
  reports failure and ships nothing stale.
- A force-fresh path that deletes committed run artifacts (F1).

> **Exit:** you have watched the pipeline fail on a deliberate break, and no
> stale artifact survived it.

### Phase 2 — Experiments
Formatting untouched. Prose untouched.

- Run. Fix the run-wasting bugs (F4–F9). Re-run.
- Every result lands as a **generated file** — never typed into the paper (D5).
- Commit the artifact that backs each number beside it (D1).

> **Exit:** every number the paper will state exists in a generated file that a
> single command reproduces.

### Phase 3 — Interpretation
The phase this playbook exists for. No writing yet.

For each intended claim:

1. Compute **both** absolute and relative forms (D4).
2. Compute the **null-model value** — what would this ratio be with no signal at
   all? (C2)
3. Compare the effect to the **pre-committed threshold** (constraint 2).
4. Check per-corpus as well as pooled, and identify which corpus carries it (C9).
5. Name the **confound you have not eliminated**, and quantify it. In the source
   project sequence length still out-separated the proposed signal, 0.869 vs
   0.769, and saying so cost a word in the title and nothing else (C6).
6. Write down the claim's **strength** from the ladder in
   [02-EVIDENCE-AND-CLAIMS.md](02-EVIDENCE-AND-CLAIMS.md), and never let it
   drift upward later.

> **Exit:** a claims table — claim, supporting number, strength, unresolved
> confound. This becomes the paper's Limitations section and its caveats deck.

### Phase 4 — Writing
Only now.

- Every claim traced to a row of the Phase 3 table.
- Every number rendered from a macro, never typed (D5).
- Abstract written **last** — abstracts get written early from an intuition
  about a number that later changed (C7).
- Statistical machinery cited at first use (E3).

> **Exit:** the audit kit's claim-strength and provenance checks pass —
> [05-AUDIT-KIT.md](05-AUDIT-KIT.md).

### Phase 5 — Conformance
Hand over to the venue-conformance playbook: template, captions, float
references, headings. Apply every rule to the whole document, not the flagged
instances.

### Phase 6 — Fit
Cut to the page limit, and prove no result was lost. Conformance changes length,
so cutting before conforming means cutting twice.

### Phase 7 — Deliverable
A self-contained package, clean-room compiled, generated by a committed script.
Never hand-assembled and never edited in place — an edited package is a second
source of truth, and the tracked copy becomes the one nobody compiles.

### Phase 8 — Sibling sweep
Repeat 3–7 on every other artifact: the second paper, each presentation deck,
each explainer. Non-negotiable (D9, H1–H3).

---

## What to front-load, ranked by rework prevented

1. **The leakage table.** One hour. Prevented an entire restore-and-regenerate
   cascade across five analyses, two figures, four macro files and the prose
   (B1–B4).
2. **The schema check.** One hour per benchmark. Two benchmarks were rejected on
   it after design work had already been done against the assumed schema
   (A1, A3).
3. **The power analysis.** Prevents publishing a null the study cannot support
   (A6, C1), and it is the one thing that cannot be fixed in revision.
4. **A pipeline that crashes instead of hanging** (F3), with n-floor assertions
   (F5).
5. **The single-source-of-truth bridge** — *plus a test that an unfilled slot
   fails the build.* The bridge without the test is a net loss: it swaps a
   visible inconsistency for a silent one (D7).
6. **The author block, as a blocking question.** It cannot be inferred. Ask in
   the first exchange; a bracketed placeholder until then, never a realistic
   fake.
7. **A tracked `UNVERIFIED.md`** (D8).

---

## The recurring shapes

**The narrow fix.** A reviewer marks one instance; only that instance is fixed;
the same note returns pointed at a different object.

**The deferred verification.** A gap is correctly found, correctly reported in
chat, and never written back into the artifact (D8). This is the generative
pattern behind most of family D.

**The helpful mechanism with a new failure mode.** The macro bridge fixed number
drift and introduced silent defaults (D7). Committing run artifacts made results
reproducible and made stale results invisible (F1). Budget for testing every fix
as a change in its own right.

**The sibling drift.** Two artifacts, one gets the attention. Divergence is
invisible because each looks fine on its own (H1).

**The confident wrong input.** A polished external checklist, mostly incorrect.
Fluency correlates with neither accuracy nor authority — including in your own
earlier output.

**The fix cascade.** v4.1 → v4.8 in one day, each version fixing errors the last
introduced (G5). When you are editing the rendered artifact faster than you can
check it, stop and build a check.

---

## Read next

| File | For |
|---|---|
| [01-FAILURE-CATALOG.md](01-FAILURE-CATALOG.md) | the 52 failures, with commits |
| [02-EVIDENCE-AND-CLAIMS.md](02-EVIDENCE-AND-CLAIMS.md) | the claim-strength ladder, the human-revision dossier, the six reviewer rules |
| [03-LIFECYCLE.md](03-LIFECYCLE.md) | what each out-of-order transition cost |
| [04-WORKED-EXAMPLES.md](04-WORKED-EXAMPLES.md) | three defects traced end to end, with the fork points |
| [05-AUDIT-KIT.md](05-AUDIT-KIT.md) | runnable checks |
