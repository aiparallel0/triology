#!/usr/bin/env python3
"""Float-reference classifier -- committee item 3.

A float that carries a \\ref{} is *cited*.  A float whose name opens a clause
and is followed by a reporting verb is *discussed*.  The organising-committee
complaint that agents get wrong ("tum tablo ve sekillerin ... ilgili
paragraflarda aciklanmasi") is about the second, not the first: a naive audit
that only counts \\ref{} returns "all referenced -- nothing to do".

Counts a reference only when the float name opens a clause AND is followed by a
reporting verb.  Sentence-initial adverbials ("Finally, Fig. 6 shows ...") and
conjoined clauses ("and Fig. 5 plots ...") are legitimate subject position and
are accepted.

Exit codes
  0  every float has >=1 subject-position reference          (the only pass)
  1  at least one float is cited but never discussed
  2  the input yielded no floats at all -- the check found nothing, which is
     NOT the same as finding nothing wrong (see AUDIT.md, bug 3)

Usage: float_refs.py <file.tex> [<file.tex> ...]
"""
import re
import sys

# Reporting verbs.  A float name in subject position is only a *discussion* if
# the float is said to do something.  Third-person singular and passive forms.
VERBS = r"""(?:shows?|reports?|gives?|lists?|plots?|presents?|summari[sz]es?|
            compares?|breaks?|isolates?|tests?|addresses?|makes?|records?|
            confirms?|demonstrates?|illustrates?|depicts?|displays?|
            details?|describes?|contains?|holds?|traces?|quantifies?|
            visuali[sz]es?|separates?|collects?|charts?|maps?|singles?|
            highlights?|reveals?|indicates?|answers?|establishes?|
            measures?|evaluates?|examines?|states?|counts?|sets?|marks?|
            is|are|was|were|shown|reported|given|listed|plotted|presented|
            summari[sz]ed|compared|collected|used|drawn)"""

# Float-name openers as they appear in prose, immediately before a \ref.
NAME = r"(?:Fig\.|Figure|Table|Tables|Algorithm|Alg\.|Sec\.)"

CLAUSE_END = ".;:!?"          # real clause terminators
OPENERS = "([{"               # a reference opening a bracketed aside is NOT subject


def strip_comments(text: str) -> str:
    """Drop LaTeX line comments without eating \\%."""
    return re.sub(r"(?<!\\)%.*", "", text)


# A reference sitting immediately after one of these is at the head of new
# material, not mid-sentence.  Bug 1: clause openers are not just '. ; :'.
STRUCTURAL = re.compile(
    r"(?:\\end\{[^}]*\}"          # \end{table}, \end{enumerate}, ...
    r"|\\begin\{[^}]*\}"
    r"|\\\\"                      # explicit line break
    r"|\\item"
    r"|\\par"
    r"|\\\]|\\\)|\$\$"            # display math closers
    r"|\\(?:noindent|smallskip|medskip|bigskip|newline|centering|hline))\s*$")

# \command{...} / \command[..]{...} groups, nested one level deep.
GROUP = re.compile(r"\\[A-Za-z@]+\*?(?:\[[^\]]*\])?"
                   r"\{(?:[^{}]|\{[^{}]*\})*\}\s*$")

# A bare control sequence: \bottomrule, \sigma, \footnotesize ...
BARE = re.compile(r"\\[A-Za-z@]+\*?\s*$")


def opens_clause(pre: str) -> bool:
    """True when the text before a float name puts that name in subject position.

    Peels trailing LaTeX before testing, and stops at a structural boundary.

    Bug 2: \\subsection{Reproduction} IS a clause opener, but naively peeling a
    single trailing '}' leaves '\\subsection{Reproduction', which ends in a
    letter and would be judged mid-sentence.  Whole \\command{...} groups are
    stripped iteratively, never single characters.
    """
    pre = pre.rstrip()
    while True:
        if STRUCTURAL.search(pre):
            return True                           # head of new material
        for pat in (GROUP, BARE):
            new = pat.sub("", pre).rstrip()
            if new != pre:
                pre = new
                break
        else:
            # a lone closing brace left by a group we could not match whole
            new = re.sub(r"(?<![\\A-Za-z])\}\s*$", "", pre).rstrip()
            if new == pre:
                break
            pre = new

    if not pre:                                   # start of file / of a group
        return True
    last = pre[-1]
    if last in CLAUSE_END:
        return True
    if last in OPENERS:                           # "(Fig. 3)" -- parenthetical
        return False
    if last == ",":
        # sentence-initial adverbial ("Finally, Fig. 6 shows ...") or a
        # conjoined clause; accept only when the comma closes a short lead-in
        # that itself opens a clause.
        head = pre[:-1]
        lead = re.split(r"[.;:!?]", head)[-1].strip()
        return 0 < len(lead.split()) <= 4
    if re.search(r"\b(?:and|but|while|whereas|where|which|so|then|because)$",
                 pre, re.I):
        return True                               # conjoined clause
    return False


def analyse(path):
    src = strip_comments(open(path, encoding="utf8").read())

    labels = re.findall(r"\\label\{((?:fig|tab|alg):[^}]+)\}", src)
    subject, parenthetical, uncited = {}, {}, []

    for lab in labels:
        subject[lab] = 0
        parenthetical[lab] = 0

    pat = re.compile(r"\\(?:ref|autoref|cref|Cref)\{([^}]+)\}")
    for m in pat.finditer(src):
        lab = m.group(1)
        if lab not in subject:
            continue
        # text immediately before the \ref, including the float name itself
        pre_full = src[:m.start()]
        name_m = re.search(NAME + r"[~ ]*$", pre_full)
        if not name_m:
            parenthetical[lab] += 1
            continue
        before_name = pre_full[:name_m.start()]
        post = src[m.end():m.end() + 220]
        # strip a trailing '(a)', '{}' etc. then look for the reporting verb
        post = re.sub(r"^\s*(?:\([a-z]\)|\{\}|\\,)\s*", " ", post)
        verb = re.match(r"\s*(?:\\[A-Za-z]+\s*)?(?:[a-z]+\s+){0,2}" + VERBS
                        + r"\b", post, re.X)
        if opens_clause(before_name) and verb:
            subject[lab] += 1
        else:
            parenthetical[lab] += 1

    for lab in labels:
        if subject[lab] == 0 and parenthetical[lab] == 0:
            uncited.append(lab)

    return labels, subject, parenthetical, uncited


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    rc = 0
    for path in argv[1:]:
        labels, subject, parenthetical, uncited = analyse(path)
        if not labels:
            # Bug 3: an empty or wrong input file used to score a perfect pass.
            # Zero floats means zero missing floats means exit 0.  Any check
            # whose "nothing found" state is indistinguishable from "nothing
            # wrong" must assert it found something.
            print(f"{path}: NO FLOATS FOUND -- wrong file? check did not run")
            sys.exit(2)
        n_sub = sum(subject.values())
        n_par = sum(parenthetical.values())
        print(f"{path}")
        print(f"  floats: {len(labels)}  subject-position: {n_sub}  "
              f"parenthetical: {n_par}")
        missing = [l for l in labels if subject[l] == 0]
        if uncited:
            print("  UNREFERENCED (no \\ref at all):")
            for l in uncited:
                print(f"    {l}")
        if missing:
            print("  CITED BUT NEVER DISCUSSED (no subject-position reference):")
            for l in missing:
                print(f"    {l}  (parenthetical x{parenthetical[l]})")
            rc = 1
        else:
            print("  missing subject-position references: NONE")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
