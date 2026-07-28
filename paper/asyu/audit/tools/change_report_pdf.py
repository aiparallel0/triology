#!/usr/bin/env python3
"""Render the change set as a PDF, straight from git diff.

This is NOT the typeset paper. No TeX distribution is available in the
environment this runs in, so the paper itself cannot be compiled here. What it
can do is show, faithfully and without retyping anything, exactly what changed
against the original -- every removed line, every added line, added lines
inside a red box.

The content comes from `git diff <base> -- main.tex`. Nothing is summarised
from memory, so the PDF cannot drift from the source it describes.

    python3 audit/tools/change_report_pdf.py [<base-ref>] [<out.pdf>]
"""
import os
import re
import subprocess
import sys

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether,
                                PageTemplate, Paragraph, Spacer, Table,
                                TableStyle)

CHG = colors.HexColor('#CC0000')
INK = colors.HexColor('#1C1917')
MUT = colors.HexColor('#6E675E')
DEL = colors.HexColor('#8A8178')
BG = colors.HexColor('#FBF7F2')

S = ParagraphStyle('body', fontName='Times-Roman', fontSize=8.6, leading=11.2,
                   textColor=INK, alignment=TA_LEFT)
S_DEL = ParagraphStyle('del', parent=S, fontName='Times-Italic', textColor=DEL)
S_ADD = ParagraphStyle('add', parent=S, textColor=INK)
S_H = ParagraphStyle('h', fontName='Helvetica-Bold', fontSize=10.5, leading=13,
                     textColor=INK, spaceBefore=9, spaceAfter=2)
S_SUB = ParagraphStyle('sub', fontName='Helvetica', fontSize=7.6, leading=9.6,
                       textColor=MUT, spaceAfter=3)
S_LBL = ParagraphStyle('lbl', fontName='Helvetica-Bold', fontSize=6.4,
                       leading=8, textColor=MUT)
S_TITLE = ParagraphStyle('t', fontName='Times-Bold', fontSize=19, leading=22,
                         textColor=INK)
S_NOTE = ParagraphStyle('note', parent=S, fontSize=8.8, leading=11.8)

# Which commit-comment marker introduced a hunk -> a human-readable origin.
ORIGIN = [
    (r'CHANGE 1\b|CHANGE 1 ', 'Committee item 1 - author information'),
    (r'CHANGE 2\b', 'Reviewer rule 1 - abstract in bold'),
    (r'CHANGE 3\b', 'Reviewer rule 2 - keywords in italic'),
    (r'CHANGE 4\b', 'Reviewer rule 6 - Title Case'),
    (r'CHANGE 5\b', 'Committee item 3 - floats must be discussed, not only cited'),
    (r'CHANGE 6\b', 'Reviewer rule 4 - table captions, small-caps constraint'),
    (r'CHANGE 7\b', 'Displaced caption detail re-sited (no result lost)'),
    (r'CHANGE 1[01]\b', 'Build gate - unfilled slots must fail the build'),
    (r'CHANGE 12\b', 'Hyphenation of compounds'),
    (r'CHANGE 13\b', 'Number provenance - typed literal where a macro exists'),
    (r'CHANGE 14\b', 'Claim strength - overclaim vs the paper\'s own Fig. 2'),
    (r'CHANGE 15\b', 'ASYU editor item 1 - line spacing'),
    (r'CHANGE 16\b', 'ASYU editor item 2 - 10 nk abstract/keywords'),
    (r'CHANGE 17\b', 'ASYU editor item 3 - 6 nk after each paragraph'),
    (r'CHANGE 18\b', 'ASYU editor item 4 - TABLE I. with a period'),
    (r'CHANGE 21\b', 'Reviewer 1 - show coverage beside precision'),
    (r'CHANGE 22\b', 'Reviewer 1 - Fig. 1 implied we invented the method'),
    (r'CHANGE 23\b', 'Reviewer 1 - organise results around research questions'),
    (r'CHANGE 24\b', 'Reviewer 2 - operational cost of 18% coverage'),
    (r'CHANGE 25\b', 'Reviewer 2 - selective-prediction baselines'),
    (r'CHANGE 26\b', 'Reviewer 2 - SROIE OCR hypothesis, now tested'),
    (r'CHANGE 27\b', 'Reviewer 3 - which extractor each experiment uses'),
]


def esc(t):
    return (t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def clean(line):
    """Make a TeX line readable without pretending it is typeset."""
    t = line
    t = re.sub(r'\\(chgi|chgcap|chgblock|textbf|emph|texttt|noindent)\b', '', t)
    t = re.sub(r'\\(begin|end)\{[a-zA-Z*]+\}', '', t)
    t = re.sub(r'~\\ref\{[^}]*\}', ' X', t)
    t = re.sub(r'\\ref\{[^}]*\}', 'X', t)
    t = re.sub(r'\\cite\{[^}]*\}', '[ref]', t)
    t = re.sub(r'\\label\{[^}]*\}', '', t)
    t = t.replace('\\%', '%').replace('\\&', '&').replace('\\,', ' ')
    t = t.replace('``', '"').replace("''", '"').replace('---', '-')
    t = re.sub(r'\$([^$]*)\$', r'\1', t)
    t = t.replace('\\sigma', 'sigma').replace('\\tau', 'tau')
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def hunks(base, path, repo):
    raw = subprocess.run(
        ['git', '-C', repo, 'diff', '-U2', base, '--', path],
        capture_output=True, text=True).stdout.split('\n')
    out, cur = [], None
    for ln in raw:
        if ln.startswith('@@'):
            if cur:
                out.append(cur)
            cur = []
        elif cur is not None and (ln[:1] in '+- ' or ln == ''):
            cur.append(ln)
    if cur:
        out.append(cur)
    return out


def origin_of(block):
    txt = '\n'.join(block)
    for pat, name in ORIGIN:
        if re.search(r'\+\s*%.*' + pat, txt):
            return name
    return None


def build(base, out_pdf, repo, path):
    story = []
    story.append(Paragraph('Sigma-Verifier &mdash; what changed', S_TITLE))
    story.append(Spacer(1, 3))
    story.append(Paragraph(
        f'Every difference between the submitted paper ({base}) and the '
        f'current source, taken directly from <font face="Courier">git diff'
        f'</font>. Added text sits in a <font color="#CC0000"><b>red box</b>'
        f'</font>; removed text is greyed above it.', S_NOTE))
    story.append(Spacer(1, 5))
    story.append(Paragraph(
        '<b>This is not the typeset paper.</b> No TeX distribution is '
        'available where this was produced, so the six-page IEEE artifact '
        'could not be compiled here. This report shows the changes; it says '
        'nothing about page count, captions or spacing as rendered. Compiling '
        'is the check.', S_NOTE))
    story.append(Spacer(1, 10))

    n_shown = 0
    for block in hunks(base, path, repo):
        rem = [l[1:] for l in block if l.startswith('-')]
        add = [l[1:] for l in block if l.startswith('+')]
        # comment-only additions carry the reason; keep them as the origin line
        add_txt = [clean(l) for l in add if not l.lstrip().startswith('%')]
        rem_txt = [clean(l) for l in rem if not l.lstrip().startswith('%')]
        add_txt = [t for t in add_txt if t]
        rem_txt = [t for t in rem_txt if t]
        if not add_txt and not rem_txt:
            continue
        origin = origin_of(block)
        n_shown += 1

        items = []
        if origin:
            items.append(Paragraph(esc(origin), S_H))
        if rem_txt:
            items.append(Paragraph('WAS', S_LBL))
            items.append(Paragraph(esc(' '.join(rem_txt))[:2600], S_DEL))
            items.append(Spacer(1, 2.5))
        if add_txt:
            items.append(Paragraph('NOW', S_LBL))
            body = Paragraph(esc(' '.join(add_txt))[:2600], S_ADD)
            box = Table([[body]], colWidths=[168 * mm])
            box.setStyle(TableStyle([
                ('BOX', (0, 0), (-1, -1), 0.9, CHG),
                ('BACKGROUND', (0, 0), (-1, -1), BG),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            items.append(box)
        items.append(Spacer(1, 7))
        story.append(KeepTogether(items) if len(items) < 6 else items[0])
        if len(items) >= 6:
            story.extend(items[1:])

    doc = BaseDocTemplate(out_pdf, pagesize=A4,
                          leftMargin=20 * mm, rightMargin=20 * mm,
                          topMargin=16 * mm, bottomMargin=16 * mm,
                          title='Sigma-Verifier - change report')
    frame = Frame(20 * mm, 16 * mm, 170 * mm, A4[1] - 32 * mm, id='f')

    def deco(canvas, _doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(MUT)
        canvas.drawString(20 * mm, 9 * mm,
                          'Sigma-Verifier - change report - not the typeset paper')
        canvas.drawRightString(190 * mm, 9 * mm, str(canvas.getPageNumber()))
        canvas.restoreState()

    doc.addPageTemplates([PageTemplate(id='p', frames=[frame], onPage=deco)])
    doc.build(story)
    print(f"wrote {out_pdf}  ({n_shown} changed passages, base {base})")
    return 0


if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.abspath(os.path.join(here, '..', '..', '..', '..'))
    base = sys.argv[1] if len(sys.argv) > 1 else 'main'
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        here, '..', '..', 'dist', 'sigma-verifier-changes.pdf')
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    sys.exit(build(base, os.path.abspath(out), repo, 'paper/asyu/main.tex'))
