# Research Pipeline Playbook

A standing instruction for AI agents doing **empirical paper work**: choosing a
benchmark, running a pipeline, deciding what the numbers mean, and writing
sentences that survive a reviewer.

**Start here → [00-MASTER-PROMPT.md](00-MASTER-PROMPT.md)** — hand that file to
an agent as its operating instruction. The rest are references it links to.

---

## What this is

Distilled from two real papers taken to ASYU 2026 through **221 commits** across
`aiparallel0/triology` (Paper 1, σ-verifier) and `aiparallel0/arith-gating`
(Paper 2, beam-margin), 12–25 May 2026 — plus the predecessor era recorded in
`RESEARCH_LOG.md`, four named human editorial revisions, two rounds of
scientific critique, a set of six reviewer formatting rules, and a training-set
leak found after the paper had already been reviewed and hedged.

Every rule exists because something actually went wrong. Every entry carries its
commit hash. Nothing is hypothetical.

## Contents

| File | What it is |
|---|---|
| [00-MASTER-PROMPT.md](00-MASTER-PROMPT.md) | The operating instruction: 9 prime directives, 8 standing constraints, 8-phase procedure with exit conditions |
| [01-FAILURE-CATALOG.md](01-FAILURE-CATALOG.md) | 52 catalogued failures in 8 families, each with symptom, root cause, detection, fix and commit |
| [02-EVIDENCE-AND-CLAIMS.md](02-EVIDENCE-AND-CLAIMS.md) | The claim-strength ladder, number provenance, and the dossier of every human revision these papers received |
| [03-LIFECYCLE.md](03-LIFECYCLE.md) | The 20 stages the work actually went through, what each out-of-order transition cost, and the order to use instead |
| [04-WORKED-EXAMPLES.md](04-WORKED-EXAMPLES.md) | Three defects traced end to end, with the fork points where a careless agent goes wrong |
| [05-AUDIT-KIT.md](05-AUDIT-KIT.md) | Runnable checks, and an honest account of what cannot be automated |
| [06-INSTRUMENTS-ARTIFACTS-GROUND.md](06-INSTRUMENTS-ARTIFACTS-GROUND.md) | The checker, the rendered artifact, the repository state, the instruction and the budget: 25 classes of failure in the things you verify *with* rather than the things you verify, compressed to 24 rules, plus a record of the decisions that reversed |
| [07-EXTERNAL-VERIFIER-SIGNALS.md](07-EXTERNAL-VERIFIER-SIGNALS.md) | Domain patterns for external verifiers as selective-prediction signals, generalised from the receipt-arithmetic study to any checkable structural invariant: 22 classes, including how to respond when a reviewer rejects your framing |
| [tools/](tools/) | `claim_strength.py`, `number_provenance.py`, `run_research_audit.py` |

## The one-paragraph version

**The numbers were right; the sentences about them were not.** Across these two
papers the recurring failure is a claim stated one rung above its evidence: a
null reported without its minimum detectable effect, a 2.26× advantage that was
conjunction arithmetic rather than signal, a title claiming a confound had been
*eliminated* when the stratified analysis showed sequence length still
out-separated the signal 0.869 to 0.769. Beneath that sits a worse family:
CORD-v2 *train* is the Donut fine-tuning split, so a well-motivated run over
train+validation+test improved **every cell** — and an improvement is the only
signal leakage ever gives you. Fixing it took six steps, and the one that nearly
escaped was the prose, because a macro bridge updates every number and cannot
update a sentence about a number. Confidence has to come from provenance: one
number, one generated file, one committed artifact.

## Relationship to the venue-conformance playbook

Two playbooks, one boundary, no overlap:

| This one | `paper/asyu/audit/` |
|---|---|
| benchmarks, leakage, power, claims, provenance, pipeline reliability, scope | templates, captions, float references, page limits, headings |
| *is the number real, and is the sentence about it true?* | *does the rendered artifact conform?* |
| Phases 0–4 | Phases 5–8 |

Files 06 and 07 were added after both of the above were in place, and cover
what neither did. 06 asks a third question — *is the instrument that checks
this trustworthy, and is the ground it runs on the ground I think it is?* —
because a defective check converts "unverified" into "verified" without passing
through "wrong". 07 is the only topic-scoped file in the set: it generalises the
σ-verifier study into the class of external structural verifiers, for reuse on a
different task.

Run this one **first**. Formatting is a function of content, and content is a
function of results; reformatting after every result change was the single
largest source of rework in these repos.

Neither answers the other's question. A paper needs both answered.

## Using the checks

```bash
# both checks, one or more papers
python3 docs/research-pipeline/tools/run_research_audit.py paper/asyu/main.tex

# the flagship: any sentence a rung above its evidence?
python3 docs/research-pipeline/tools/claim_strength.py paper/asyu/main.tex

# was it measured, and does it exist twice?
python3 docs/research-pipeline/tools/number_provenance.py paper/asyu/main.tex
```

Applied to Paper 1 on 27 July 2026, these found two live defects that four
editorial revisions and two numeric audits had not:

- **Nine table cells typed as literals** while `numbers_pooled.tex` already
  produced exactly those values. The same table had drifted before — Table III's
  pooled row once printed b=183, c=186 where the per-corpus rows sum to 185, 188.
  The earlier fix corrected the literal and left it a literal.
- **An overclaim contradicting the paper's own figure caption** — *"the
  combination consistently outperforms either gate alone"*, where Fig. 2 says
  σ-alone is nominally higher on CORD.

Both are fixed. Details in `paper/asyu/audit/CHANGES.md`, changes 13 and 14.

## What the tools cannot do

Families A (data diligence), B (leakage) and G (scope churn) caused most of the
rework in these repos, and **no script detects any of them**. They are decided in
the first day and prevented only by sequence. Their artifact is a written
`GROUND_TRUTH.md` containing the schema check, the checkpoint→split leakage
table, and the minimum detectable effect per corpus — not a green check.

The operational rule for leakage is behavioural: **treat an unexplained
improvement as a defect until explained.** That is the only signal it gives you.

## Where this lives

One copy, in `triology`. `arith-gating` is the sibling paper and is governed by
the same playbook; it does not get its own copy, because two copies of a
document is the failure this playbook spends a whole family on (D, and directive
D5). Cross-repo checks run by path:

```bash
python3 docs/research-pipeline/tools/run_research_audit.py \
    paper/asyu/main.tex ../arith-gating/paper/asyu/main.tex
```
