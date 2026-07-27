# Audit kit — ASYU sigma-verifier paper

Runnable checks, plus the ground truth they check against.

```bash
cd paper/asyu
bash audit/run_audit.sh
```

Each check states what it catches and how to read it in its own header. Checks
needing a rendered PDF or a TeX distribution report **SKIP**, never a quiet
pass — a check whose "could not run" state is indistinguishable from "nothing
wrong" is worse than no check.

| File | What it is |
|---|---|
| `GROUND_TRUTH.md` | Phase 0: page limit, class, caption spec derived from `IEEEtran.cls`, and the one axis still open |
| `CHANGES.md` | the twelve changes, why each, and what was deliberately not changed |
| `UNVERIFIED.md` | what has *not* been confirmed, and what closes each item |
| `run_audit.sh` | runs everything below |

| Check | Catches |
|---|---|
| `tools/float_refs.py` | floats that are cited but never **discussed** — the flagship |
| `tools/selftest_float_refs.sh` | that the classifier still reproduces the defect |
| `tools/placeholder_leak.sh` | unfilled `\PH{}` and unoverridden `NA`/`PENDING` defaults |
| `tools/numbers_keydiff.py` | a result silently dropped while restructuring |
| `tools/caption_format.sh` | a package overriding the publisher class — **on the PDF** |
| `tools/gate.sh` | page count, overfull boxes, undefined refs |
| `tools/build_selftest.sh` | a build that reports success on a broken source |
| `tools/selfcontained.sh` | a deliverable that only builds in your working tree |
| `tools/headings_titlecase.py` | sentence-case headings, `\section` included |
| `tools/numbers_consistency.sh` | one quantity stated two ways |
| `tools/disclosure_check.sh` | claims about real-world actions asserted as fact |
| `tools/tex_structure.py` | brace / environment / `\if…\fi` balance, for when you cannot compile |
| `tools/showchanges.sh` | flips the red change boxes on and off |

## The three rules this kit exists to enforce

**Run every rendered-artifact check against the PDF, never the source.** Source
inspection cannot see what a package override did. The source of the caption
bug in the project this kit is distilled from said `font=footnotesize` for 91
commits and looked entirely reasonable.

**A clean build is not evidence.** In that project the build never failed, the
page count was always right, and the PDF always looked finished — while a
package override was destroying the publisher's caption format, two unfilled
placeholders were deleting a figure and a table, a build script was returning
failure on success and shipping stale artifacts, and a disclosure sentence was
escalating from intent to asserted fact across three commits each described as
"reconciling". Confidence has to come from comparing the rendered artifact
against an independent authority.

**A checker that has never failed is not measuring anything.**
`selftest_float_refs.sh` exists because `float_refs.py` had three bugs during
development, each producing a false pass or false failure, and each of them is
the generic failure mode of any LaTeX-text heuristic:

1. **Clause openers are not just `. ; :`.** A reference after `\end{table}` or
   display math sees `pre == "} "`. Peel trailing LaTeX before testing. This
   one was live in this repository: the first run scored 5/9 and reported four
   false failures, all of them references sitting right after `\end{table}`.
2. **`\subsection{Reproduction}` is a clause opener.** Peeling a single
   trailing `}` leaves `\subsection{Reproduction`, which ends in a letter and
   reads as mid-sentence. Strip whole `\command{...}` groups iteratively.
3. **An empty or wrong input file scored a perfect pass.** Zero floats means
   zero missing floats means exit 0. Hence
   `if not labels: sys.exit(2)`. `tex_structure.py` and `numbers_keydiff.py`
   carry the same guard for the same reason.

## Order of work

```
Phase 0  Ground truth      class file, template, page limit, deadline   <- GROUND_TRUTH.md
Phase 1  Trustworthy build make it fail loudly; prove it by breaking it <- build_selftest.sh
Phase 2  Content           argument and numbers settle, formatting untouched
Phase 3  Integrity audit   numbers, citations, claim strength, disclosures
Phase 4  Conformance       template applied whole-document              <- CHANGES.md
Phase 5  Fit               cut to limit, prove no result lost           <- numbers_keydiff.py
Phase 6  Deliverable       self-contained package, clean-room compiled  <- selfcontained.sh
Phase 7  Sibling sweep     repeat 3-6 on every other artifact           <- CHANGES.md
```

Phase 0 before everything: the page limit and the caption specification are
*inputs*. Discovered late they invalidate finished work. Phase 5 after Phase 4:
conformance changes length, so cutting first means cutting twice.

## Two habits that cost the source project three correction rounds

**The narrow fix.** A reviewer marks one instance; only that instance is fixed;
the same note comes back pointing at a different object. The identical margin
note — *"Bu tablo mu?"*, *is this a table?* — arrived twice about two different
objects because only the first was fixed. Apply every rule to the whole
document, and report the places nobody annotated.

**The deferred verification.** A gap is correctly found, correctly reported in
chat, and never written back into the artifact. That is the pattern behind the
disclosure drift, the AI declaration and the unverified citation.
`UNVERIFIED.md` is the countermeasure: items that live only in a conversation
do not survive it.
