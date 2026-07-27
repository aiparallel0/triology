# Setup prompt — non-key channel research program (regenerated)

> Drop this into a fresh Claude Code session alongside `non_key_channel_research_plan.md`, `non-key-attention.md`, `non-key-coupling.md`, `non-key-perplexity.md`.

You are Claude Code. Your job is to set up three GitHub repositories for a multi-paper research program on confidence signals for document KIE, and to apply the design decisions already locked in the mega plan's §10 Change log. The original ASK / ADVISE matrix has been resolved during the kick-off; this setup runs almost entirely in Mode B. Remaining ASKs are listed in §3 below — halt at the first one.

## Context

CPU-only, inside the Claude Code container. Three papers test whether a document's non-key tokens carry independent selective-prediction signal:
- **A** — attention entropy on non-key tokens
- **C** — cosine coupling between non-key context and predicted key (three parallel key-encoding variants)
- **D** — per-corpus 5-fold CV KenLM perplexity on the non-key token sequence

All decisions: see the mega plan's §10.

## Files in this session

- `non_key_channel_research_plan.md` — single source of truth.
- `non-key-attention.md`, `non-key-coupling.md`, `non-key-perplexity.md` — per-repo cookbooks.

## Repositories to create

| Repo | Idea |
|---|---|
| `non-key-attention` | A |
| `non-key-coupling`  | C |
| `non-key-perplexity` | D |

For each repo, scaffold (per mega §7 reproducibility deliverables):

- `README.md` — points to `<repo>.md`
- `<repo>.md` — copy from this session
- `non_key_channel_research_plan.md` — copy of the mega
- `references/` — placeholder for `sigma_verifier.pdf`, `beam_margin.pdf` (user adds later)
- `environment.md` — Python version, OS, HuggingFace checkpoint SHAs (pinned), library versions (pinned per `requirements.txt`), `seed = 42`
- `requirements.txt` — pinned per mega §8.3, with inline rationale for any deliberate non-pins (lesson from arith-gating's torch handling)
- `Makefile` — phase targets: `make schema`, `make budget`, `make smoke`, `make cache`, `make signals`, `make stats`, `make figures`, `make paper`, `make check`
- `smoke_test.py` — runs on **3 real CORD receipts** (not a hand-crafted dummy — lesson from arith-gating); prints finite, non-NaN scores; must complete in ≤ 5 min CPU
- `paper/main.tex` — IEEE template with `\PH{key}` placeholders for every numerical claim (arith-gating style)
- `paper/fill_tex.py` — reads `results/*.json` and emits `paper/main_filled.tex`
- `paper/refs.bib` — preloaded with Jain & Wallace 2019, Wiegreffe & Pinter 2019, Fomicheva et al. 2020, Ren et al. 2019
- `DECISIONS.md` — empty initially; log every Mode B decision
- `RESEARCH_LOG.md` — empty initially; incrementally documents dataset gotchas, framing pivots, dead ends (lesson from arith-gating)
- `shared-cache/` — directory for `predictions_<corpus>.parquet` + `manifest_<corpus>.json` (committed per mega §0.6 container-survival rule)
- `runs/` — directory for per-run `MANIFEST.json` (kaggle2 style)
- `SETUP_REPORT.md` — written at end of setup

## Modes

- **Mode A — ASK**: stop, ask user, wait for reply.
- **Mode B — ADVISE**: apply expert judgment, log to repo's `DECISIONS.md` (issue, chosen path, rejected alternatives, rationale), proceed.

Default to Mode B.

## 1. Locked-in decisions (apply silently; no need to ask)

These were resolved during the kick-off. Log each in the relevant repo's `DECISIONS.md` for the audit trail.

**Cross-cutting**:
1. Partition is defined by predicted bbox; accepted limitation; gold-bbox-partition sanity ablation added per mega §0.5.
2. Kill thresholds: AUROC > **0.65** (Idea C); Δ-AUROC ≥ **+0.05** (Ideas A, D).
3. Step 8 restyling is match-style-not-text; explicit anti-plagiarism written into the per-repo Step 8 prompt per mega §8.6.
4. Cross-idea McNemar tests (A,C), (A,D), (C,D) promoted into the umbrella §4.2 headline analysis.
5. CPU-budget pre-flight: write `CPU_BUDGET.md` at session root before any inference (mega §0.7). Hard 10-min wall-clock cap per ablation; 200-receipt subset fallback if exceeded.
6. Pin every HF model SHA + dataset SHA in `environment.md`; pin every library version in `requirements.txt`; `seed = 42` everywhere (mega §0.9).
7. Dataset-schema verification pre-flight: write `dataset_schema_check.md` per corpus by inspecting 5–10 raw annotation files (mega §0.8; lesson from arith-gating's FATURA/SROIE-Task-3 schema surprises).
8. Adopt arith-gating's paper template: `\PH{}` placeholders + `fill_tex.py`. Paper scaffolding exists before experiments run.
9. Each repo carries its own `shared-cache/`, committed to git. Re-runs in fresh containers do not re-execute KIE inference.

**Idea A**:
10. Donut total-span identification via parsed JSON + HuggingFace `decoder_output_offsets` mapping.
11. Cite Jain & Wallace 2019 and Wiegreffe & Pinter 2019; frame `H_N` as diagnostic, not explanation.
12. Run radius sweep `r ∈ {0.02, 0.05, 0.10, 0.20}` before any AUROC claim.
13. Cross-architecture: per-backbone primary tables; `H_N_normalized = H_N / log|N|` pooled secondary.

**Idea C**:
14. Three parallel key-encoding variants: (a) key-alone, (b) key + ±w OCR tokens for `w ∈ {3, 5, 10}`, (c) MLP scorer trained on cached `(z, e)` pairs.
15. K-region tokens replaced by `[MASK]`, not deleted.
16. Add Google USE or fastText-mean as a second-encoder ablation alongside MiniLM.
17. DINOv2 vision-path strictly optional; 10-min CPU cap; subset fallback per mega §0.7.

**Idea D**:
18. Per-corpus 5-fold CV KenLM (no single shared LM); drift-detector reframing as fallback if wall-clock budget exceeded.
19. Numeric-normalization ablation (digits→`<num>` vs raw).
20. N-gram order ablation `n ∈ {3, 4, 5}`.
21. Pre-committed KS-test leakage diagnostic; refuse to publish per-corpus AUROC if KS p > 0.05 between train-fold and held-out-fold `S` distributions.

## 2. Datasets in scope

Multi-corpus, **experimentally compatible** (same task schema, OCR + bboxes + total field):

- **CORD-v2** (all splits, train+val+test, ~1000 receipts) — anchor.
- **SROIE Task-3** (canonical, ~347).
- **WildReceipt** (test, ~472).
- **Optional**: any additional receipt KIE corpus that passes the §0.8 dataset-schema verification (candidates: MC-OCR, FATURA receipts subset). Skip if pre-flight finds schema mismatches.

Language need not match across corpora — Idea D's per-corpus 5-fold CV KenLM design neutralizes the language-mismatch issue. Idea A and C are not language-sensitive.

## 3. Remaining ASKs (halt at the first)

Most ASKs were resolved during kick-off. Only these remain — they can only be answered by inspecting the runtime container or HF Hub at scaffold time, so they're deferred.

**[ASK-A1]** Search HF Hub for a LayoutLMv3 checkpoint fine-tuned on CORD-v2. If a defensible one exists, use it; if none exists, ask the user whether to (a) restrict LayoutLMv3 to WildReceipt only and document the cross-architecture limitation, or (b) drop LayoutLMv3 entirely and run single-backbone (Donut only).

**[ASK-A2]** Detect `os.cpu_count()` in the Claude Code container. If < 2 cores are available, ask the user whether to (a) accept serial execution with the 200-receipt subset fallback as default, or (b) defer to an environment with ≥ 4 cores.

**[ASK-A3]** Confirm the user has `sigma_verifier.pdf` and `beam_margin.pdf` to drop into each repo's `references/` folder before Step 8. If not, ask which papers to substitute as the style targets.

**Stop conditions** (per mega):
- Any required HuggingFace checkpoint gated/removed/fails to download → halt.
- `kenlm` (Idea D) cannot be installed → halt.
- Any smoke test fails to produce a finite, non-NaN score → halt.
- CPU budget estimate exceeds 24 CPU-hours total after applying subset fallbacks → halt.

## 4. Proceed

1. Create the three repos with the scaffolding above.
2. Drop the mega + the appropriate `<repo>.md` into each.
3. Write `environment.md`, `requirements.txt`, `Makefile`, `paper/` scaffolding, empty `DECISIONS.md`, empty `RESEARCH_LOG.md`, `shared-cache/`, `runs/` in each.
4. Apply the locked-in decisions silently; log each to the relevant repo's `DECISIONS.md`.
5. Run pre-flight: `dataset_schema_check.md`, `CPU_BUDGET.md`, smoke test on 3 real CORD receipts in each repo.
6. **Halt at the first ASK above.** Do not start the next ASK until the previous one is answered.
7. Do not begin Step 4 (the actual experiment from mega §8.6) until all ASKs are resolved.
8. Write `SETUP_REPORT.md` at session root listing:
   - Repos created
   - Files dropped per repo
   - Locked-in decisions logged (one line each: `[repo] [issue#] [chosen path]`)
   - ASK-A1, ASK-A2, ASK-A3 answers
   - Pre-flight outputs (schema checks, CPU budget, smoke test passes/fails)
   - Any stop-condition triggered
