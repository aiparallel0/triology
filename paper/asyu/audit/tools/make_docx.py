#!/usr/bin/env python3
"""Build a .docx review copy of the paper from main.tex.

Why this exists: reviewers and language tools read Word, not LaTeX, and the
naive route (hand the .tex to pandoc) loses or corrupts four things that
matter for a review pass:

  1. Generated numbers. Every result in the paper is a macro filled in from
     runs/ by numbers_*.tex. Pandoc does not expand them, so the export
     reads "median \\latMedian" where the paper says "median 4.07". A
     reviewer cannot check a number that is not there.
  2. TikZ figures. Three of the four figures are drawn in TikZ. Pandoc
     cannot render them and silently drops them. Here each one is compiled
     standalone and embedded as a real image.
  3. Citations. Pandoc leaves \\cite{kim2022donut} as literal text. IEEEtran
     numbers references by order of first citation, so that order is
     recomputed here and the reference list is emitted to match.
  4. The custom `steps` list, which pandoc does not know and would drop
     along with the worked example inside it.

The output is a review artifact, not a submission format. The submission is
the LaTeX; this is for people and tools that need to read the prose.

Usage: make_docx.py [<main.tex>] [-o <out.docx>]
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, '..', '..'))


def run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def strip_comments(src):
    """Blank comments, keeping % that is escaped as a percent sign."""
    out = []
    for line in src.split('\n'):
        i, n = 0, len(line)
        cut = None
        while i < n:
            if line[i] == '\\':
                i += 2
                continue
            if line[i] == '%':
                cut = i
                break
            i += 1
        out.append(line if cut is None else line[:cut])
    return '\n'.join(out)


def macro_values(tex, src_dir):
    """Preamble defaults, then every generated file overrides them.

    Same precedence as the document: \\newcommand default first, then
    \\input{numbers_*.tex} replaces it. Reading them in this order is what
    makes the export show the real result rather than the ?? placeholder.
    """
    vals = {}
    head = tex[:tex.find('\\begin{document}')]
    for m in re.finditer(r'\\newcommand\{\\([a-zA-Z]+)\}\{([^{}]*)\}', head):
        vals[m.group(1)] = m.group(2)
    for name in re.findall(r'\\input\{([^}]+)\}', head):
        path = os.path.join(src_dir, name)
        if not os.path.exists(path):
            continue
        body = open(path, encoding='utf8').read()
        for m in re.finditer(r'\\(?:re)?newcommand\{\\([a-zA-Z]+)\}\{([^{}]*)\}', body):
            vals[m.group(1)] = m.group(2)
    return vals


def expand(text, vals):
    """Substitute result macros until fixpoint (some expand into others)."""
    for _ in range(5):
        before = text

        def sub(m):
            return vals.get(m.group(1), m.group(0))
        text = re.sub(r'\\([a-zA-Z]+)\{\}', lambda m: vals.get(m.group(1), m.group(0)), text)
        text = re.sub(r'\\([a-zA-Z]+)(?![a-zA-Z])', sub, text)
        if text == before:
            break
    return text


def build_figures(tex, src_dir, out_dir):
    """Compile each tikzpicture standalone and rasterise it.

    Returns {figure-label: png-path}. A figure that fails to compile is
    reported and skipped rather than silently omitted, because a missing
    figure in a review copy reads as a paper that has no figure there.
    """
    try:
        import fitz
    except ImportError:
        print("  pymupdf missing: cannot rasterise figures", file=sys.stderr)
        return {}

    head = tex[:tex.find('\\begin{document}')]
    preamble = '\n'.join(l for l in head.split('\n') if l.startswith((
        '\\usepackage{tikz', '\\usetikzlibrary', '\\definecolor',
        '\\usepackage{amsmath', '\\usepackage{xcolor')))

    out = {}
    body = tex[tex.find('\\begin{document}'):]
    floats = re.findall(r'\\begin\{(figure\*?)\}(.*?)\\end\{\1\}', body, re.S)
    for env, blk in floats:
        lm = re.search(r'\\label\{([^}]+)\}', blk)
        if not lm:
            continue
        label = lm.group(1)

        gm = re.search(r'\\includegraphics\[[^\]]*\]\{([^}]+)\}', blk)
        if gm:                                    # already a PDF on disk
            pdf = os.path.join(src_dir, gm.group(1))
            if os.path.exists(pdf):
                png = os.path.join(out_dir, label.replace(':', '_') + '.png')
                fitz.open(pdf)[0].get_pixmap(dpi=200).save(png)
                out[label] = png
            continue

        tm = re.search(r'\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}', blk, re.S)
        if not tm:
            continue
        work = tempfile.mkdtemp()
        doc = ('\\documentclass[border=3pt]{standalone}\n' + preamble +
               '\n\\begin{document}\n' + tm.group(0) + '\n\\end{document}\n')
        open(os.path.join(work, 'f.tex'), 'w', encoding='utf8').write(doc)
        r = run(['pdflatex', '-interaction=nonstopmode', 'f.tex'], cwd=work)
        pdf = os.path.join(work, 'f.pdf')
        if os.path.exists(pdf):
            png = os.path.join(out_dir, label.replace(':', '_') + '.png')
            fitz.open(pdf)[0].get_pixmap(dpi=200).save(png)
            out[label] = png
        else:
            tail = [l for l in r.stdout.split('\n') if l.startswith('!')][:2]
            print(f"  figure {label}: standalone compile failed {tail}",
                  file=sys.stderr)
        shutil.rmtree(work, ignore_errors=True)
    return out


def number_citations(body, src_dir):
    """Recompute IEEEtran numbering: order of first citation.

    The edits reordered Related Work, so the numbering from any previous
    export is stale. Returns (body-with-[n], ordered list of raw bib entries).
    """
    order = []
    for m in re.finditer(r'\\cite\{([^}]+)\}', body):
        for k in m.group(1).split(','):
            k = k.strip()
            if k and k not in order:
                order.append(k)

    bib = ''
    path = os.path.join(src_dir, 'references.bib')
    if os.path.exists(path):
        bib = open(path, encoding='utf8').read()
    entries = {}
    for m in re.finditer(r'@\w+\s*\{\s*([^,]+),(.*?)\n\}', bib, re.S):
        entries[m.group(1).strip()] = m.group(2)

    def field(blk, name):
        m = re.search(name + r'\s*=\s*[{"](.*?)[}"]\s*,?\s*\n', blk, re.S)
        if not m:
            m = re.search(name + r'\s*=\s*\{(.*?)\}\s*,', blk, re.S)
        return ' '.join(m.group(1).split()).strip('{}') if m else ''

    refs = []
    for i, key in enumerate(order, 1):
        blk = entries.get(key)
        if blk is None:
            refs.append(f'[{i}] {key} (not found in references.bib)')
            continue
        au = field(blk, 'author').replace(' and ', ', ')
        ti = field(blk, 'title')
        ve = (field(blk, 'booktitle') or field(blk, 'journal') or
              field(blk, 'publisher') or '')
        yr = field(blk, 'year')
        bits = [b for b in (au, f'"{ti},"' if ti else '', ve, yr) if b]
        refs.append(f'[{i}] ' + ' '.join(bits) + '.')

    def rep(m):
        nums = [str(order.index(k.strip()) + 1) for k in m.group(1).split(',')
                if k.strip() in order]
        return '[' + ', '.join(nums) + ']'
    return re.sub(r'\\cite\{([^}]+)\}', rep, body), refs


def main(argv):
    tex_path = os.path.join(SRC, 'main.tex')
    out_path = os.path.join(SRC, 'dist', 'sigma-verifier-asyu-review.docx')
    args = [a for a in argv[1:] if not a.startswith('-')]
    if args:
        tex_path = os.path.abspath(args[0])
    if '-o' in argv:
        out_path = os.path.abspath(argv[argv.index('-o') + 1])
    src_dir = os.path.dirname(tex_path)

    if not shutil.which('pandoc'):
        print("pandoc not installed", file=sys.stderr)
        return 2

    raw = open(tex_path, encoding='utf8').read()
    tex = strip_comments(raw)
    vals = macro_values(tex, src_dir)
    work = tempfile.mkdtemp()
    figs = build_figures(tex, src_dir, work)

    body = tex[tex.find('\\begin{document}'):tex.find('\\end{document}')]

    # Abstract and keywords -> the run-in form the venue prints, so the
    # export reads the way the PDF does.
    body = re.sub(r'\\begin\{abstract\}(.*?)\\end\{abstract\}',
                  lambda m: '\n\n\\textbf{Abstract---}' + m.group(1) + '\n\n',
                  body, flags=re.S)
    body = re.sub(r'\\begin\{IEEEkeywords\}(.*?)\\end\{IEEEkeywords\}',
                  lambda m: '\n\n\\textbf{Index Terms---}' + m.group(1) + '\n\n',
                  body, flags=re.S)

    # Floats -> image + caption paragraph, or table + caption paragraph.
    def float_sub(m):
        env, blk = m.group(1), m.group(2)
        cm = re.search(r'\\caption\{(.*?)\}\s*\n?\s*\\label', blk, re.S)
        cap = cm.group(1) if cm else ''
        lm = re.search(r'\\label\{([^}]+)\}', blk)
        label = lm.group(1) if lm else ''
        if env.startswith('figure'):
            n = fignum.setdefault(label, len(fignum) + 1)
            img = figs.get(label)
            inc = f'\n\n\\includegraphics{{{img}}}\n\n' if img else '\n\n'
            return inc + f'\\textbf{{Fig. {n}.}} ' + cap + '\n\n'
        n = tabnum.setdefault(label, len(tabnum) + 1)
        tb = re.search(r'\\begin\{tabular\}.*?\\end\{tabular\}', blk, re.S)
        tbl = tb.group(0) if tb else ''
        return (f'\n\n\\textbf{{TABLE {roman(n)}.}} ' + cap + '\n\n' +
                tbl + '\n\n')

    fignum, tabnum = {}, {}

    def roman(n):
        vals_ = [(10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')]
        s = ''
        for v, r in vals_:
            while n >= v:
                s += r
                n -= v
        return s

    # Order matters: figure*/table* before figure/table.
    for env in ('figure\\*', 'table\\*', 'figure', 'table'):
        body = re.sub(r'\\begin\{(' + env + r')\}(?:\[[^\]]*\])?(.*?)\\end\{\1\}',
                      float_sub, body, flags=re.S)

    body, refs = number_citations(body, src_dir)

    # Custom list -> a list pandoc understands, keeping the worked example.
    body = body.replace('\\begin{steps}', '\\begin{enumerate}')
    body = body.replace('\\end{steps}', '\\end{enumerate}')

    body = expand(body, vals)

    # Leftovers that only make sense in the typeset paper.
    for pat in (r'\\resizebox\{[^}]*\}\{[^}]*\}\{%?', r'\\maketitle',
                r'\\thispagestyle\{[^}]*\}', r'\\pagestyle\{[^}]*\}',
                r'\\linespread\{[^}]*\}', r'\\selectfont', r'\\boldmath',
                r'\\vspace\{[^}]*\}', r'\\smallskip', r'\\noindent',
                r'\\setlength\{[^}]*\}\{[^}]*\}', r'\\centering',
                r'\\begin\{document\}', r'\\label\{[^}]*\}'):
        body = re.sub(pat, '', body)
    body = body.replace('_', r'\_')          # Prod_price_value, total_value
    body = re.sub(r'\\ref\{[^}]*\}', '', body)

    title = re.search(r'\\title\{(.*?)\n?\}', tex, re.S)
    title = re.sub(r'\\\\|\s+', ' ', title.group(1)).strip() if title else 'Paper'

    doc = ('\\documentclass{article}\n\\usepackage{graphicx}\n'
           '\\usepackage{amsmath,amssymb,booktabs}\n\\begin{document}\n'
           f'\\section*{{{title}}}\n' + body +
           '\n\n\\section*{References}\n\n' +
           '\n\n'.join(r.replace('_', r'\_') for r in refs) +
           '\n\\end{document}\n')
    stage = os.path.join(work, 'export.tex')
    open(stage, 'w', encoding='utf8').write(doc)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    r = run(['pandoc', stage, '-f', 'latex', '-o', out_path,
             '--resource-path', work + ':' + src_dir], cwd=work)
    if r.returncode != 0:
        print(r.stderr[:1500], file=sys.stderr)
        return 1

    print(f"wrote {out_path}")
    print(f"  figures embedded: {len(figs)}/{len(fignum)}")
    print(f"  references: {len(refs)}")
    unexpanded = sorted(set(re.findall(r'\\([a-zA-Z]{3,})(?![a-zA-Z])', body)))
    known = {'textbf', 'emph', 'includegraphics', 'begin', 'end', 'item',
             'section', 'subsection', 'textit', 'times', 'approx', 'sum',
             'subseteq', 'sqcap', 'inf', 'leq', 'geq', 'gtrsim', 'mid',
             'dots', 'text', 'mathbb', 'chi', 'phi', 'rho', 'kappa', 'pi',
             'sigma', 'tau', 'theta', 'varepsilon', 'toprule', 'midrule',
             'bottomrule', 'tabular', 'enumerate', 'equation', 'Big',
             'textstyle', 'ensuremath', 'mu', 'Pr', 'quad', 'nobreakspace'}
    leftover = [u for u in unexpanded if u not in known]
    if leftover:
        print(f"  note: unexpanded control sequences: {leftover[:12]}")
    shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
