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
#
#   make audit      -> run the conformance audit (see audit/README.md)
#   make package    -> dist/*.zip, self-contained, ready to upload to Overleaf
#   make review     -> red change boxes ON, then build   (do not submit this)
#   make submit     -> red change boxes OFF, build, then gate on the page limit

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

# Conformance audit. Rendered-PDF checks report SKIP without a TeX
# distribution rather than passing quietly -- SKIP is not PASS.
PAGE_LIMIT ?= 6
.PHONY: audit review submit package
audit:
	@PAGE_LIMIT=$(PAGE_LIMIT) bash audit/run_audit.sh

# Self-contained Overleaf packages, both modes. Derived from this tree every
# time -- the zip is never edited in place, or it becomes a second source of
# truth and the tracked copy becomes the one nobody compiles.
package:
	@bash audit/tools/make_package.sh review
	@bash audit/tools/make_package.sh submit

# Review copy: every change from the conformance pass inside a red box, plus
# the change index page after the bibliography.
review:
	@bash audit/tools/showchanges.sh on
	@$(MAKE) --no-print-directory main

# Submission copy: boxes off, then gate. The page limit is only meaningful in
# this mode -- the red boxes add height.
submit:
	@bash audit/tools/showchanges.sh off
	@$(MAKE) --no-print-directory main
	@bash audit/tools/gate.sh . $(PAGE_LIMIT) main

# Continuous rebuild while editing.
watch:
	$(LATEXMK) -pdf -pvc -interaction=nonstopmode main.tex

clean:
	$(LATEXMK) -C main.tex presentation.tex
	rm -f *.aux *.bbl *.blg *.log *.out *.toc *.nav *.snm *.fls *.fdb_latexmk

distclean: clean
	rm -f $(FIG_PDFS)
