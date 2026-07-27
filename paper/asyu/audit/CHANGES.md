# Changes applied to `main.tex`

Venue-conformance pass over the ASYU sigma-verifier paper, following the paper
pipeline playbook. Twelve changes. Every one of them is either **inside a red
box in the rendered review PDF** or **listed on the review-only change index
page** appended after the bibliography.

Turn the marking off with one line:

```bash
bash audit/tools/showchanges.sh off     # \showchangestrue -> \showchangesfalse
```

Nothing else moves. The boxes are apparatus, not content.

---

## How the marking works

| Macro | Renders as | Used for |
|---|---|---|
| `\chgi{...}` | thin red frame, inline | a word, a heading, an author field — short spans only |
| `chgblock` env | red frame that **breaks** across lines, columns and pages (`framed`) | added or rewritten paragraphs |
| `\chgcap{...}` | boxed red `CHANGED` tag + red caption text | captions |

A caption cannot contain a breakable box and an `\fbox` around a whole caption
would overfull the column, so captions get a boxed tag plus red text rather
than a frame. That is the one place where "red box around the change" is
approximated rather than literal, and it is deliberate.

If `framed.sty` is missing, `chgblock` degrades to a pair of red rules via
`\IfFileExists` — a missing package must not fail the build.

---

## The changes

### Visible in the body, inside red boxes

**1 — Author block.** *Committee item 1: missing author information must be
added per the template.*
`\IEEEauthorblockN{Authors Anonymized}` → an explicitly bracketed fillable
block. **Blocking on the human.** The author block cannot be inferred, and a
plausible invented affiliation is worse than an obvious gap: it is the kind of
thing that ships.

**2 — `\boldmath` in the abstract.** *Reviewer rule 1: the whole abstract in
bold; at present only some words are bold.*
Followed literally this rule is already satisfied — IEEEtran bolds abstract
*text* on its own. What actually looked inconsistent is that **inline math
stays upright inside a bold paragraph**. `\boldmath` is the fix for the real
defect; bolding words by hand would have been the fix for the symptom.

**3 — `\itshape` in the keywords.** *Reviewer rule 2.* IEEEtran italicises
only the `Keywords—` lead-in.

**4 — One heading to Title Case.** *Reviewer rule 6.*
`The Performance Gain is Genuine` → `... Gain Is Genuine`. The other twelve
headings were already Title Case; `\section` was checked as well as
`\subsection`, because in the source project every subsection was fixed while
three section titles stayed sentence case. Verified by
`audit/tools/headings_titlecase.py`.

**5 — Fig. 1 given a clause of its own.** *Committee item 3, and the one that
agents get wrong.*

Every float in this paper already carried a `\ref{}`. A naive audit returns
"all referenced — nothing to do." The operative complaint is the second
clause: *ilgili paragraflarda açıklanması*, **explained in the relevant
paragraphs**. A float mentioned only as `(Fig. 1)` is cited but not discussed.

The workable test is grammatical position:

- ❌ parenthetical — `…as that independent signal (Fig.~\ref{fig:scope}).`
- ✅ subject — `Fig.~\ref{fig:scope} shows the whole argument in one picture. …`

Fig. 1 is the full-width teaser on page 1 — the single most prominent object
in the paper — and it was the one float never explained in a paragraph. A new
paragraph now introduces it and walks through what it shows, and the trailing
parenthetical was removed.

Measured with `audit/tools/float_refs.py`:

| | floats | subject-position | verdict |
|---|---|---|---|
| before | 9 | 8 | `fig:scope` cited but never discussed, exit 1 |
| after | 9 | 9 | `NONE` missing, exit 0 |

**6 — Five table captions shortened.** *Reviewer rule 4 / committee item 2,
capitalisation axis.*

Authority: the `\@makecaption` table branch in the `IEEEtran.cls` vendored in
this directory —
`{\normalfont\footnotesize #1}\\{\normalfont\footnotesize\scshape #2}`.
`TABLE I` sits on its own line above a **centred small-caps** title. A
three-line sentence is unreadable in small caps.

| Table | Was | Now |
|---|---|---|
| I | `Pooled precision across all gate configurations ($n{=}1{,}019$). Wilson 95% confidence intervals reported for each result.` | `Pooled precision, all decision rules ($n{=}1{,}019$)` |
| II | `Accuracy of the combined decision rule reported separately for each dataset and AI model. Wilson 95% CIs reported for each result.` | `Combined decision rule, per corpus and backbone` |
| III | `Testing whether σ and softmax fail on the same receipts or different ones. b counts … c counts … Results reported separately for each dataset.` | `Paired McNemar test of $\sigma$ against softmax` |
| IV | `Effect of removing the minimum line item rule on SROIE ($n{=}347$), showing coverage and precision under each setting.` | `Cardinality-guard ablation on SROIE ($n{=}347$)` |
| V | `Precision and coverage of σ on CORD under increasing levels of artificially injected noise (10 seeds, bootstrap 95% CIs …). This experiment uses the fixed single-candidate extractor …` | `Injected money-line noise on CORD (10 seeds)` |

Figure captions were **not** shortened. The figure branch of `\@makecaption`
has no `\scshape`, so the long explanatory figure captions are fine as they
are. Same rule, different branch, different answer — which is the reason to
read the class file rather than apply "IEEE style" from memory.

**7 — Displaced caption detail re-sited.** *Shortening captions is where
results get silently lost.*

Every clause removed in change 6 was accounted for before it was removed:

| Clause removed | Where it already lived | Action |
|---|---|---|
| "Wilson 95% CIs reported for each result" (I, II) | column header `95% CI` / `Wilson 95%`, and Experimental Setup: *"Per-cell precision is reported with Wilson 95% confidence intervals"* | dropped, redundant |
| `b`/`c` definitions (III) | stated verbatim in the paragraph below the table | dropped, redundant |
| "showing coverage and precision under each setting" (IV) | the column headers | dropped, redundant |
| "removing the minimum line item rule" (IV) | body paragraph explains the guard at length | dropped, redundant |
| **"bootstrap 95% CIs" (V)** | **nowhere** | **moved to the body** |
| **single-candidate-extractor caveat + its refs to Table IV and Fig. 2 (V)** | **nowhere** | **moved to the body** |

The last two rows are the ones that matter. Both are real information stated
in no other place in the paper, and the caveat is what reconciles two CORD
coverage numbers that otherwise look like a contradiction. They are now a
marked paragraph in §Robustness.

Result key-set diff across the whole pass:

```
REMOVED entirely: NONE
ADDED: chgcap, chgtag, chgi, assertfilled, PH, latN
```

`REMOVED entirely: NONE` is the mandatory line. The additions are the marking
macros and the new build assertions; the occurrence-count increases on
`latMedian`, `latPNineNine`, `latMax`, `latN`, `rcEarned` and `poolN` are the
`\assertfilled` calls plus one new `\poolN{}` use in change 5. The check does
not clear you — it tells you what to justify.

### Preamble-level, no visible mark — hence the change index page

**8–9 — The marking apparatus.** `\showchanges` switch, `\chgi`, `\chgcap`,
`chgblock`, the `framed` fallback, `\pdfstringdefDisableCommands` entries so
the boxes never reach the PDF bookmarks, and the review-only change index
after the bibliography.

**10 — `\PH{}` now fails the build.**

It used to render `\textcolor{red}{\texttt{[key]}}` — a marker you can see
*if the output still typesets*, which is exactly what the failure prevents.
`\PH{cam_npcr1px}` puts an underscore into text mode. LaTeX raises
`! Missing $ inserted.`; under `-interaction=nonstopmode` it "recovers" by
consuming tokens, and the recovery swallows the following floats. In the
source project two unfilled placeholders on one line deleted a figure, a
table, a χ² result and an entire paragraph, and left two sections both
numbered V — from a PDF that compiled, was exactly 6 pages, had no visible
gaps, and was sent to a committee.

> A templating mechanism whose failure mode is a *language error* rather than
> a *visible gap* is a content-deletion bomb. Make unfilled slots fail the
> build.

`\PH` is currently used nowhere in this paper, which is what makes this a free
change today and a load-bearing one the first time someone uses it.

**11 — Results-macro assertion.** Every `\newcommand{\latMedian}{NA}`-style
safe default is there so the paper compiles before the pipeline has run. The
same defaults are a placeholder leak wearing a plausible face if they reach a
shipped PDF: `NA` and `PENDING` typeset perfectly. `\assertfilled` now checks
at `\begin{document}` that `numbers_*.tex` actually loaded, and errors if not.

This is the test that makes the single-source-of-truth bridge worth having.
The bridge without it is a net loss — it swaps a *visible* inconsistency for
*silent* content deletion.

**12 — `\exhyphenpenalty=10000`.** Stops line-breaking at explicit compound
hyphens, so `softmax-orthogonal` cannot extract as `softmaxorthogonal`. The
source project drew a reviewer complaint about exactly this
(`perimage`, `differentialattack`, `cellularautomata`). Applied document-wide
rather than to flagged instances, so future compounds are covered
automatically. Watch for new overfull boxes — see `UNVERIFIED.md` B4.

---

## Deliberately not changed

**`booktabs` was left in place.** Converting to the ruled-grid style
(`{|l|c|c|}`, `\hline` between rows, bold header cells) was mandatory at the
source project's venue. Here the only authority for it would be the ASYU
template, and there is none in this repository; `IEEEtran.cls` prescribes
nothing about table rules.

The source project also received a well-formatted external "IEEE Compliance
Prompt": about twenty confident, professionally worded corrections. Checked
item by item against the class file and the venue template, **most were
wrong** — half were `pdftotext` extraction artifacts, half contradicted the
venue's actual template. Applying it wholesale would have introduced errors
into a paper that was already correct.

Advice is a hypothesis. The class file is evidence. This paper's tables are
real tables in a real tabular environment, which is what reviewer rule 5
actually demanded; the rule style is an open Phase 0 item with the exact
command to close it in `GROUND_TRUTH.md §4`.

---

## Phase 7 — sibling sweep

Non-negotiable in principle, and reported rather than acted on here because
the request was scoped to the sigma-verifier paper.

| Artifact | State |
|---|---|
| `paper/asyu/presentation.tex` | beamer talk, not a venue submission. Structure balanced. Six sentence-case headings — Title Case is a paper rule, not a slide rule, so this is a non-finding. No `caption` package. No floats. **Untouched.** |
| `paper/asyu/caveats_explained.tex` | beamer, internal explainer. Structure balanced. No `caption` package. No floats. **Untouched.** |
| `aiparallel0/arith-gating` — the beam-margin paper | **Not audited.** It is the sibling that has not had the attention, which is exactly the shape that produced the source project's stage 12: *"Paper 2 finally audited — full repeat of stages 8–10."* Two artifacts, one gets the attention, and divergence is invisible because each looks fine on its own. Run `audit/` against it before submitting either. |

---

## Changes 13–14 — from the research-pipeline audit

Added after `docs/research-pipeline/` was distilled from both repos' history and
its two checks were run against this paper. Both findings survived four
editorial revisions and two numeric audit passes.

**13 — Nine table cells routed through their generated macros.**
*Found by `docs/research-pipeline/tools/number_provenance.py`.*

Tables I, II and III typed values that `numbers_pooled.tex` already produces,
leaving `\poolSigA`, `\poolSigC`, `\poolIntA`, `\poolIntC`, `\poolMcB`,
`\poolMcC`, `\poolMcChi`, `\poolMcP`, `\wrN`, `\wrIntA` and `\wrIntC` unused
beside the literals that duplicated them.

This is not hypothetical drift. **Table III's pooled row once printed b=183,
c=186 where the per-corpus rows sum to 185 and 188** — corrected at `b9edc78`
by fixing the literal, which left it a literal and the mechanism untouched. Nine
cells now render from the generated file.

**No red box:** the rendered output is byte-identical. There is nothing to see
on the page, which is exactly why it is on the change-index page instead.

**14 — An overclaim contradicting this paper's own figure caption.**
*Found by `docs/research-pipeline/tools/claim_strength.py`.*

Section V-A read:

> *"Across all three datasets and both architectures, the combination
> consistently outperforms either gate alone."*

Fig. 2's caption says otherwise: *"on CORD it exceeds the matched-coverage
softmax rule while σ-alone at full coverage is nominally higher on a different
(larger) accept set."* The body claim was one rung above its evidence, and the
correction was already sitting in the paper's own float.

Rewritten to the comparison that is true — at matched coverage, with CORD named
as the exception and characterised as a comparison between different accept sets
rather than a reversal. Marked with a red `chgblock`.

Both are the shapes catalogued at `docs/research-pipeline/01-FAILURE-CATALOG.md`
D4 and C6.
