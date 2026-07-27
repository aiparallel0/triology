# Phase 0 — Ground truth for the ASYU sigma-verifier paper

The page limit and the caption specification are **inputs**, not discoveries.
Discovered late they invalidate finished work; the whole caption saga in the
source project would have been a ten-minute Phase 0 task. This file is that
task, done.

Rule for everything below: **the class file and the style definitions are the
evidence. A template's rendered PDF, a checklist, a reviewer's paraphrase, and
your own earlier output are all hypotheses.**

---

## 1. Page limit — RESOLVED

**6 pages, IEEE format.** Source: `docs/ASYU_SEED_SCOPE.md:7` ("ASYU conference
paper: ~6 pages, IEEE format") and the page allocation table at line 35.

Wired into `audit/tools/gate.sh` as a hard gate (`PAGE_LIMIT`, default 6) so it
cannot be re-discovered late.

> The gate is only meaningful with the red change boxes **off**. They add
> height. `gate.sh` warns when `main.tex` is still in review mode.

## 2. Document class — RESOLVED

`\documentclass[conference]{IEEEtran}`, and `IEEEtran.cls` is vendored in this
directory (`paper/asyu/IEEEtran.cls`). That makes Authority A readable without
a network.

## 3. Caption format — RESOLVED, and already correct

**Authority A, the class file.** `grep -n "makecaption" IEEEtran.cls` → the
traditional non-compsoc branch at line 2774:

```
% figure branch
\setbox\@tempboxa\hbox{\normalfont\footnotesize {#1.}\nobreakspace\nobreakspace #2}
% table branch
\footnotesize\bgroup\par\centering\@IEEEtabletopskipstrut
  {\normalfont\footnotesize #1}\\{\normalfont\footnotesize\scshape #2}\par
```

and at lines 2607–2608: `\def\figurename{Fig.}`, `\def\tablename{TABLE}`, with
`\thetable` Roman (line 2830).

So the class specifies:

| Float | Label | Separator | Title |
|---|---|---|---|
| figure | `Fig. N` | **period**, then two non-breaking spaces | roman, footnotesize |
| table | `TABLE N` (Roman) | **newline** | **centred small caps**, footnotesize |

**This paper does not load the `caption` package.** That is the whole reason
its captions are already correct. In the source project the venue's own
template contained

```latex
\usepackage[font=footnotesize]{caption}
```

`caption` has no IEEEtran support: it discards the class's `\@makecaption` and
imposes its own default separator, a **colon**. It is also why that project's
table titles silently lost `\scshape` — `font=` sets the caption font *from
scratch*, so an option that merely looks like it restates the size was a total
override. **If anyone ever adds `\usepackage{caption}` to this file, both
defects arrive at once and neither is visible in the source.**

**Consequence that had to be acted on:** because the class renders table
titles in `\scshape`, a three-line sentence caption is unreadable. The five
table captions were shortened and the displaced detail moved into body
paragraphs — see `CHANGES.md`, change 6 and 7.

Figure captions are *not* small caps (the figure branch has no `\scshape`), so
the long explanatory figure captions in this paper are fine as they are and
were left alone.

**Still to verify on the rendered PDF** — source inspection cannot see an
override:

```bash
bash audit/tools/caption_format.sh main.pdf
# want:  Fig. 1.   TABLE I      reject any colon
```

`pdftotext` renders small caps as `R ECONSTRUCTION`. That is an extraction
artifact, not a defect. Confirm visually:

```bash
pdftoppm -r 110 -png -f 3 -l 3 main.pdf /tmp/page
```

## 4. Table rule style — **OPEN**

Reviewer rule 4 in the source project named three axes: capitalisation,
punctuation, **alignment**. Capitalisation and punctuation are settled above by
Authority A. Rule style is not.

This paper uses `booktabs` (`\toprule`/`\midrule`/`\bottomrule`) in all five
tables. The source project's venue prescribed a ruled **grid**
(`{|l|c|c|c|}` with `\hline` between rows and bold header cells), and
converting was mandatory *there*.

**It was not applied here, deliberately.** The authority for a grid style
would be the ASYU template, and there is no ASYU template, `.docx`, or style
guide anywhere in this repository — `find . -iname '*asyu*' -o -iname '*.docx'`
returns only `docs/ASYU_SEED_SCOPE.md`. `IEEEtran.cls` prescribes nothing about
table rules. Applying another venue's rule on the strength of its plausibility
is precisely the failure documented in `02-VENUE-CONFORMANCE §D`: a polished
external checklist, ~20 confident corrections, most of them wrong, which would
have introduced errors into a paper that was already correct.

**To close this item**, obtain the ASYU author kit and run Authority B:

```bash
unzip -o ASYUtemplate.docx -d docx/
python3 - <<'EOF'
import re
s = open('docx/word/styles.xml', encoding='utf8').read()
for m in re.finditer(r'<w:style [^>]*w:styleId="([^"]*)"[^>]*>(.*?)</w:style>', s, re.S):
    sid, body = m.groups()
    if re.search(r'table|figure|caption', sid, re.I):
        caps = 'SMALLCAPS' if '<w:smallCaps' in body else ('ALLCAPS' if '<w:caps' in body else '')
        print(f"{sid:24s} {caps}")
EOF
```

Two independent authorities agreeing is what makes a deviation from a
template's *rendered output* defensible to a committee. One is not enough, and
zero is what we have for this axis.

If the template turns out to prescribe a grid, converting adds width: vertical
rules plus bold headers overflowed two tables in the source project. Tighten
with `\setlength{\tabcolsep}{3pt}` rather than shrinking the font.

## 5. Float spacing — RESOLVED

`\floatsep` is `5pt plus 2pt minus 2pt` here (main.tex), with
`\textfloatsep`/`\intextsep` at `6pt`/`5pt`. The source project's template
prescribed `\floatsep 0pt`, which makes two floats stacked in one column
collide visually; `6pt` was the documented deviation. This paper is already
inside that spacing family and was left alone.

## 6. Author block — **OPEN, BLOCKING**

`\author{}` was `\IEEEauthorblockN{Authors Anonymized}`. It is now an
explicitly bracketed fillable block. It cannot be inferred and must never be a
realistic fake. **This is a blocking question for the human, not a task.**

## 7. Submission deadline — **UNKNOWN**

Not recorded anywhere in this repository. If there is one, put it here: a
24-hour committee correction window is what turns every item above from
planning into triage.
