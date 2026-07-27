# Unverified list

Items not confirmed against an independent authority. **Things that live only
in a chat transcript do not survive it**, so they live here instead.

Nothing on this list is a claim that something is wrong. Each is a claim that
has not been *checked*, which is a different and more dangerous state — a
skipped check whose "could not run" is indistinguishable from "nothing wrong"
is worse than no check at all.

---

## A. Blocking on the human

| # | Item | What is needed |
|---|---|---|
| A1 | **Author block.** Currently a bracketed placeholder. | Real names, department, institution, city/country, e-mail. The paper is not submittable until these are filled. A realistic-looking invented affiliation is worse than the obvious gap. |
| A2 | **Submission deadline.** Not recorded in the repo. | If one exists, put it in `GROUND_TRUTH.md §7`. |
| A3 | **ASYU author kit / template.** Absent from the repo. | Needed to close the table-rule-style question in `GROUND_TRUTH.md §4`. Until then `booktabs` stays, deliberately. |

## B. Not verifiable in the environment the changes were made in

There is **no TeX distribution and no outbound network** in that environment
(`pdflatex`, `latexmk`, `pdftotext`, `pdfinfo` all absent; CTAN and Debian
mirrors return 403 through the proxy). Every rendered-artifact check therefore
reports SKIP, and SKIP is not PASS.

| # | Item | The check that closes it |
|---|---|---|
| B1 | **The paper still compiles.** Only brace / environment / `\if…\fi` balance was checked statically. | `make main` |
| B2 | **Page count with the boxes off.** Changes 5 and 7 add roughly 14 lines of body text; captions lost about 12. Net effect on a 6-page limit is unknown. | `bash audit/tools/showchanges.sh off && make main && bash audit/tools/gate.sh . 6` |
| B3 | **Caption format on the rendered PDF.** The class file says `Fig. 1.` and small-caps `TABLE I`; source inspection cannot see an override. | `bash audit/tools/caption_format.sh main.pdf` |
| B4 | **Overfull boxes from `\exhyphenpenalty=10000`.** Forbidding breaks at explicit hyphens can push a long compound past the column. `microtype` and `\emergencystretch 3em` should absorb it. Should is not did. | `grep -c Overfull main.log` |
| B5 | **`framed` is installed.** The block-level red boxes need it. `main.tex` falls back to red rules via `\IfFileExists`, so a missing package degrades rather than fails — but the fallback has never been rendered either. | build once in each mode |
| B6 | **`\fcolorbox` in the author block and in `\subsection{}`.** Unbreakable boxes in a title area. `\chgi` is stripped from PDF bookmarks via `\pdfstringdefDisableCommands`; that path is untested. | build in review mode |
| B7 | **Shortened table captions in small caps.** They are short enough to read; whether they fit on one line at `\footnotesize\scshape` is a rendering question. | look at the page |
| B8 | **The `\PH` and `\assertfilled` errors actually fire.** Both are designed to fail the build. A gate you have never seen fail is not a gate. | `bash audit/tools/build_selftest.sh .` and temporarily rename `numbers_latency.tex` |

## C. Content claims not re-derived in this pass

This pass was venue conformance. It did not audit the science, and these were
noticed rather than checked:

| # | Item | Note |
|---|---|---|
| C1 | "to our knowledge the first peer-reviewed formalisation…" (Introduction, Contributions). | A first-ness claim is unverifiable by construction and is the shape that hardens across revisions into an assertion. It is currently hedged. Keep it hedged. |
| C2 | Fig. 1's caption asserts `1019` receipts as a literal; `\poolN` is the single source of truth for the same quantity elsewhere. | Two spellings of one number is how a decrypt timing became both `0.101 s` and `0.037 s` in the source project. Route the caption through `\poolN{}` when someone next edits it. |
| C3 | `\usepackage{algorithmic}` is loaded and never used. | Harmless today. Worth knowing that in the source project a ruled `algorithm` float with a bold run-in header drew the reviewer note *"Bu tablo mu?"* — *is this a table?* — pointed at something that was not a table. Do not add one. |
| C4 | Sibling artifacts `presentation.tex` and `caveats_explained.tex` were **not** modified. | See `CHANGES.md` §Phase 7. Sibling drift is invisible because each artifact looks fine on its own. |
