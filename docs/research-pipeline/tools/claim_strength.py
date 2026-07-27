#!/usr/bin/env python3
"""Claim-strength audit -- the flagship check.

The numbers in an empirical paper are usually right. What fails is the SENTENCE
wrapped around them, stated one rung higher than the evidence supports:

  - a null reported without its minimum detectable effect
  - a ratio that is conjunction arithmetic reported as signal
  - a superlative the stratified data does not support
  - a small cell reported as a result rather than a consistency statement

This does not judge whether a claim is true. It finds sentences that make a
strong claim without the companion that would license it, so a human decides.
That judgement cannot be automated. The enumeration can.

  strong-without-support   rung 5/6 language with no nearby CI, p-value or n
  null-without-power       a null claim with no MDE / power statement anywhere
  small-n-unqualified      an n below THRESHOLD not marked as consistency-only
  superlatives             first / only / always / guarantees / invariant
  hedge-inventory          the hedges present, for eyeball comparison

Exit 0 when nothing needs a decision, 1 when something does, 2 if the input
yielded no claims at all -- a file with no claims is not a file with no
problems.

Usage: claim_strength.py <file.tex> [<file.tex> ...] [--small-n 30]
"""
import re
import sys

# Rung 5/6: an assertion of established fact or superiority.
STRONG = re.compile(r"""
    \b(?:demonstrat\w+|establish\w+|prove[nsd]?|confirms?|shows?\s+that|
        outperform\w*|beats?|dominat\w+|significantly\s+\w+|
        substantial\w*|clearly\s+\w+|strictly\s+better|
        yields?\s+up\s+to)\b
""", re.I | re.X)

# Rung 1/2: correctly hedged.
HEDGE = re.compile(r"""
    \b(?:we\s+hypothesi[sz]e|remains?\s+a\s+hypothesis|consistent\s+with|
        suggests?|may\b|appears?\s+to|is\s+not\s+evidence|
        absence\s+of\s+evidence|underpowered|future\s+work|
        we\s+do\s+not\s+claim|explicitly\s+not|only\s+implies|
        cannot\s+conclude|not\s+establish\w*|scoped|
        consistency\s+only|nominally|too\s+small\s+a\s+sample)\b
""", re.I | re.X)

# Claims that are unfalsifiable by construction and drift upward over revisions.
SUPERLATIVE = re.compile(r"""
    \b(?:to\s+our\s+knowledge\s+the\s+first|the\s+first\b|
        state[-\s]of[-\s]the[-\s]art|guarantee[sd]?\b|
        always\b|never\s+fails|invariant\b|
        eliminat\w+|rules?\s+out|no\s+confound)\b
""", re.I | re.X)

# Evidence tokens that license a strong claim.
EVIDENCE = re.compile(r"""
    (?: \$?p\s*[<={]                     # p-value
      | CI\b | confidence\s+interval
      | \[\s*0?\.\d+\s*,                 # an interval literal
      | Wilson | bootstrap | permutation | McNemar | TOST
      | lower\s+bound
      | \bn\s*[{=]                       # a stated n
      | \\[a-zA-Z]*(?:Lo|Hi|CI|P|Wil|CPlo|Jeff)\b   # interval macros
    )
""", re.I | re.X)

POWER = re.compile(r"""
    \b(?:minimum\s+detectable|MDE\b|power\s+analys\w+|
        at\s+\d+\%\s+power|underpowered|
        too\s+small\s+a\s+sample|receipts?\s+needed|
        required\s+n\b|\\rgReqn)\b
""", re.I | re.X)

NULL_CLAIM = re.compile(r"""
    \b(?:no\s+(?:significant\s+)?(?:difference|effect|asymmetry)|
        indistinguishable | does\s+not\s+(?:differ|hold|pass|clear) |
        null\s+(?:result|finding) | non[-\s]rejection |
        not\s+statistically\s+significant)\b
""", re.I | re.X)


def sentences(src):
    src = re.sub(r'(?<!\\)%.*', '', src)
    src = re.sub(r'\\begin\{(?:tabular|tikzpicture|equation|align)\*?\}.*?'
                 r'\\end\{(?:tabular|tikzpicture|equation|align)\*?\}',
                 ' ', src, flags=re.S)
    src = re.sub(r'\\(?:label|cite|ref|includegraphics)\{[^}]*\}', ' ', src)
    src = re.sub(r'\s+', ' ', src)
    out, buf = [], ''
    for tok in re.split(r'(?<=[.!?])\s+', src):
        buf = tok.strip()
        if len(buf) > 25:
            out.append(buf)
    return out


def main(argv):
    args = [a for a in argv[1:] if not a.startswith('--')]
    small_n = 30
    if '--small-n' in argv:
        small_n = int(argv[argv.index('--small-n') + 1])
    if not args:
        print(__doc__)
        return 2

    rc = 0
    for path in args:
        src = open(path, encoding='utf8').read()
        sents = sentences(src)
        if not sents:
            print(f"{path}: NO PROSE FOUND -- wrong file? check did not run")
            return 2

        strong_bare, supers, nulls, smalls = [], [], [], []
        n_hedged = 0
        for s in sents:
            has_ev = bool(EVIDENCE.search(s))
            if HEDGE.search(s):
                n_hedged += 1
            if STRONG.search(s) and not has_ev and not HEDGE.search(s):
                strong_bare.append(s)
            if SUPERLATIVE.search(s):
                supers.append(s)
            if NULL_CLAIM.search(s) and not POWER.search(s):
                nulls.append(s)
            for m in re.finditer(r'n\s*[{=]?[=\s]*\{?(\d+)\}?', s):
                if int(m.group(1)) <= small_n and not HEDGE.search(s):
                    smalls.append((m.group(1), s))
                    break

        has_power_anywhere = bool(POWER.search(src))

        print(f"{path}")
        print(f"  sentences: {len(sents)}   hedged: {n_hedged}   "
              f"power/MDE stated anywhere: {'yes' if has_power_anywhere else 'NO'}")

        def report(title, items, note, fail=True):
            nonlocal rc
            if not items:
                print(f"  {title}: NONE")
                return
            print(f"  {title} ({len(items)}) -- {note}")
            for it in items[:8]:
                s = it if isinstance(it, str) else f"[n={it[0]}] {it[1]}"
                print(f"    - {s[:150]}")
            if len(items) > 8:
                print(f"    ... and {len(items) - 8} more")
            if fail:
                rc = 1

        report("STRONG CLAIMS WITHOUT NEARBY EVIDENCE", strong_bare,
               "state the CI, p or n in the same sentence, or drop a rung")
        report("NULL CLAIMS WITHOUT POWER", nulls,
               "absence of evidence is not evidence of absence: attach the MDE")
        report("SUPERLATIVES", supers,
               "unfalsifiable by construction; these drift upward over revisions",
               fail=False)
        report(f"SMALL CELLS (n<={small_n}) NOT MARKED CONSISTENCY-ONLY", smalls,
               "say 'consistency only' every time")

    return rc


if __name__ == '__main__':
    sys.exit(main(sys.argv))
