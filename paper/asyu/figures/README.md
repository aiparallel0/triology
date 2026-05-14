# Paper 1 (ASYU) Figures

Each script is self-contained: reads from `../../../runs/*.json` and writes
`fig_*.pdf` into this directory.

```bash
cd paper/asyu/figures
python fig_overview.py
python fig_pareto.py
python fig_accept_venn.py
python fig_reliability.py
```

Requirements: `matplotlib`, `numpy`. No external Venn library — primitives only.

## Figures

### `fig_overview.pdf` — Pipeline overview (currently the only figure embedded in `main.tex`)

Two-panel bar chart of accept-precision per corpus (CORD, SROIE) across the
four gates: `sigma`, `softmax-matched`, `sigma ∩ softmax`, `sigma-only`. Bar
heights are Wilson-CI lower bounds; point estimates are annotated inset along
with the accept-set size `n`. The figure double-codes the F1 finding (intersection
precision = 1.0 on SROIE; `sigma-only` precision = 1.0 on CORD).

Data source: `runs/PAPER_TABLE.json` (`T1_headline`).

### `fig_pareto.pdf` — Coverage–precision Pareto frontier per corpus (journal-grade, available now)

Two-panel scatter of (coverage, precision) operating points with the Pareto
frontier annotated. CORD frontier dominated by `sigma` and `sigma ⊓ softmax`;
SROIE frontier dominated by softmax at low coverage and `sigma ⊔ softmax` at
higher coverage. Annotates the specific operating points the paper cites.

Data source: `runs/PAPER_TABLE.json` (`T6_pareto_front`).

### `fig_accept_venn.pdf` — Accept-set Venn diagram per corpus (journal-grade, available now)

Two-panel Venn diagram with `|sigma|`, `|softmax|`, `|sigma ⊓ softmax|`
annotated and each region precision-coloured. Visualises the F2 orthogonality
claim: the two disagreement lobes are large and the intersection is small,
which is why intersection precision rises to 1.0.

Data source: `runs/PAPER_TABLE.json` (`T1_headline`).

### `fig_reliability.pdf` — σ precision by reachable-set size (journal-grade, available now)

Bar chart of σ accept precision on CORD binned by `|T(M)|`. The single CORD
miss localises to the `|T| ∈ [5,9]` bin (5/6); `|T|=1` and `|T|≥10` are
perfect. Supports the F3 reliability subsection.

Data source: `runs/sigma_reliability_cord.json`.

## Embedding into `main.tex`

Currently `main.tex` references only `fig_overview.pdf`. To embed the others,
add `\includegraphics[width=\linewidth]{figures/fig_<name>.pdf}` inside a
`\begin{figure}[t]…\end{figure}` block in the relevant results subsection.

ASYU has a tight page budget (6 pp.); the conservative choice is to keep
`fig_overview` inline and reserve `fig_pareto / fig_accept_venn / fig_reliability`
for the journal version. All four scripts are ready either way.
