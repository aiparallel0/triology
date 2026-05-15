# Build the ASYU paper and presentation.
# Defaults: parallel, latexmk-driven (only re-runs the passes that are needed),
# regenerates the matplotlib figures when their data or scripts change.
#
#   make            -> main.pdf and presentation.pdf in parallel
#   make main       -> main.pdf only
#   make pres       -> presentation.pdf only
#   make figures    -> just the matplotlib figure PDFs
#   make watch      -> rebuild on every edit (latexmk -pvc)
#   make clean      -> remove build artifacts
#   make distclean  -> also remove cached figure PDFs

LATEXMK   ?= latexmk
LATEXMKFLAGS ?= -pdf -interaction=nonstopmode -halt-on-error -silent
PYTHON    ?= python3

# Repo root, two levels up.
ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../..)

# Figures generated from python + the runs/ JSON files.
FIG_PDFS := figures/fig_overview.pdf figures/fig_accept_venn.pdf
RUNS     := $(ROOT)/runs/PAPER_TABLE.json

# Default: build everything, in parallel jobs.
.PHONY: all main pres figures watch clean distclean
all:
	@$(MAKE) --no-print-directory -j2 main pres

main: main.pdf
pres: presentation.pdf

# Each PDF depends on its own .tex, the bib, and the figures it embeds.
main.pdf: main.tex references.bib $(FIG_PDFS)
	$(LATEXMK) $(LATEXMKFLAGS) main.tex

presentation.pdf: presentation.tex $(FIG_PDFS)
	$(LATEXMK) $(LATEXMKFLAGS) presentation.tex

# Figure regeneration.
figures: $(FIG_PDFS)

figures/fig_overview.pdf: figures/fig_overview.py $(RUNS)
	cd figures && $(PYTHON) fig_overview.py

figures/fig_accept_venn.pdf: figures/fig_accept_venn.py $(RUNS)
	cd figures && $(PYTHON) fig_accept_venn.py

# Continuous rebuild while editing.
watch:
	$(LATEXMK) -pdf -pvc -interaction=nonstopmode main.tex

clean:
	$(LATEXMK) -C main.tex presentation.tex
	rm -f *.aux *.bbl *.blg *.log *.out *.toc *.nav *.snm *.fls *.fdb_latexmk

distclean: clean
	rm -f $(FIG_PDFS)
