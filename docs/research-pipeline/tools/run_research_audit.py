#!/usr/bin/env python3
"""Run the research-pipeline audit over one or more papers.

    python3 run_research_audit.py paper/asyu/main.tex [more.tex ...]

Checks that need a rendered PDF, a TeX distribution or a GPU are NOT here --
they are in the venue-conformance kit (see 05-AUDIT-KIT.md §7) or they are not
automatable at all (leakage, §3). This runner covers what can be decided from
the source and the generated number files.

Exit 0 when nothing needs a decision, 1 when something does.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKS = [
    ("claim strength -- is any sentence a rung above its evidence?",
     "claim_strength.py"),
    ("number provenance -- was it measured, and does it exist twice?",
     "number_provenance.py"),
]

BAR = "─" * 72


def main(argv):
    papers = argv[1:]
    if not papers:
        print(__doc__)
        return 2

    worst = 0
    for paper in papers:
        if not os.path.exists(paper):
            print(f"MISSING: {paper}")
            worst = 1
            continue
        print()
        print("=" * 72)
        print(f"  {paper}")
        print("=" * 72)
        for title, script in CHECKS:
            print()
            print(BAR)
            print(f"▶ {title}")
            print(BAR)
            r = subprocess.run([sys.executable, os.path.join(HERE, script),
                                paper])
            if r.returncode == 2:
                print("  → DID NOT RUN (no input found) -- this is not a pass")
                worst = 1
            elif r.returncode:
                print("  → NEEDS A DECISION")
                worst = 1
            else:
                print("  → nothing outstanding")

    print()
    print("=" * 72)
    print("  Not covered here, and not optional:")
    print("    leakage table          -- by hand, GROUND_TRUTH.md (05 §3)")
    print("    total-equals-parts     -- assertions in the generating script (§4)")
    print("    hedge drift            -- git log, read it yourself (§5)")
    print("    rendered-artifact conformance -- the venue kit (§7)")
    print("=" * 72)
    return worst


if __name__ == "__main__":
    sys.exit(main(sys.argv))
