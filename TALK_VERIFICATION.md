# Pre-talk verification

Verification of the implementation behind "Sigma-Verifier: Reducing Silent
Errors in Receipt Total Extraction via Structural Arithmetic Verification".
Evidence is source and committed run artifacts only. Paper text is never used
as evidence for what the code does. Line numbers are current as of this run.

Script aliases as given: A = `scripts/smoke/A_donut_cord_on_sroie.py`,
B = `scripts/smoke/B_donut_cord_on_cord.py`,
F = `scripts/smoke/F_layoutlmv3_on_wildreceipt.py`,
G = `scripts/smoke/G_robustness.py`,
Q = `scripts/smoke/Q_money_noise_cord.py`. All paths confirmed to exist.

---

## 1. Environment

| Item | State |
|---|---|
| Network to Hugging Face | Available (HTTP 200) |
| `datasets` | Installed during this session. **Version matters**, see below |
| `torch`, `transformers`, `Pillow` | Installed during this session (torch 2.13.0, transformers 5.16.1). Needed only so that G can `import` A; no model inference was run |
| GPU | **None.** `torch.cuda.is_available()` false |
| Donut / LayoutLMv3 checkpoints | **Not downloaded, not needed.** G and Q are CPU-only post-processing over committed predictions |
| CORD-v2 | Downloaded. test 100 + validation 100 |
| SROIE Task-3 canonical (347 images + entities) | Downloaded via the HF fallback mirror. The RRC primary failed: `<urlopen error Tunnel connection failed: 403 Forbidden>` |
| SROIE Task-1 OCR (`darentang/sroie`) | **Only loadable with `datasets < 4`.** See blocker below |

### Two environment blockers found, both worked around without touching code

**(a) A committed file shadows the standard library.** `types.py` at the
repository root is 655 bytes of **zlib-compressed data**, tracked in git
(introduced in commit `46d4fba`). Because Python puts the working directory on
`sys.path`, *every* Python process started from the repository root fails:

```
File "/usr/lib/python3.11/enum.py", line 3, in <module>
    from types import MappingProxyType, DynamicClassAttribute
SyntaxError: source code string cannot contain null bytes
```

The scripts use working-directory-relative paths (`runs/...`, `data/...`), so
the repository root is where they must run. Worked around with `python3 -P`
(safe path, omits cwd from `sys.path`). **No code was modified.** This file
should be deleted; it is not referenced anywhere.

**(b) `darentang/sroie` is a script-based dataset.** `datasets` 4+ removed
loading-script support:

```
WARNING:sroie_canonical:darentang/sroie load failed:
Dataset scripts are no longer supported, but found sroie.py
```

`load_sroie_ocr_lines` catches this and returns `{}`
(`scripts/smoke/sroie_canonical.py:281-282`). Under `datasets` 5.0.1, G
therefore ran to completion and **wrote a full, plausible-looking
`runs/G_robustness.json` in which every receipt had an empty `M`, coverage 0.0,
and all 347 receipts in the `money_count = "0"` bucket.** That artifact was
deleted, not committed. Downgrading to `datasets==2.19.0` restored all 347
receipts and G then produced real numbers. This is a silent-failure path worth
fixing: the loader should raise rather than return `{}`.

---

## 2. Task 1 verdict table

| # | Verdict | Evidence | Quoted source |
|---|---|---|---|
| 1 | **CONFIRMED** | A:10-11 (docstring), A:212-231, A:230 | `sigma fires iff exists tau_k in candidates, exists S subset money_lines` / `with |S| >= kmin(tau_k) and sum(S) + tau_k approx= pi.`  —  `def I3_reachable_multi(money_lines, tau_candidates, eps=0.02):` / `"""v13: union of T sets across all tau candidates."""` / `T.add((s + tau_c) / 100.0)` |
| 2 | **CONFIRMED** | A:44, A:172-191 | `MAX_TAU_CANDIDATES = 8` ; `TAU_CAP = 10000.0` (A:45) ; `cands = {0.0}` (175) ; `sign, amt = items[-1]` / `tau_v12 += sign * amt` (182-183) ; `cands.add(round(sign * amt, 4))` (186) ; `cands = [t for t in cands if abs(t) <= TAU_CAP]` (187) ; `cands_sorted = sorted(cands, key=lambda t: -abs(t))` / `cands = list(set([0.0] + cands_sorted[:MAX_TAU_CANDIDATES - 1]))` (189-190) |
| 3 | **CONFIRMED** | A:150-151, B:39-48, F:176-182 | `if TOTAL_LIKE_RE.search(ln) and not (TAX_KW_RE.search(ln) or SERV_KW_RE.search(ln) or DISC_KW_RE.search(ln)):` / `continue` ; `for k in ("price", "unitprice"):` (B:43) ; `prices_ann = [a for a in anns if a.get("label") == PRC_ID]` (F:176) |
| 4 | **CONFIRMED** | A:216-223, B:52-62, F:81-91 | `cents = [int(round(v * 100)) for v in money_lines]` / `D = {0: 0}` / `if ns not in new or new[ns] > k + 1: new[ns] = k + 1` |
| 5 | **CONFIRMED** | A:226, B:51, F:80, Q:41 | `kmin = 1 if abs(tau) > eps else 2` (identical text at all four sites; A:226 is inside `for tau in tau_candidates:` at A:225, so on SROIE it is per candidate) |
| 6 | **CONFIRMED** | A:212, A:299, B:50, F:79, Q:41 | `def I3_reachable_multi(money_lines, tau_candidates, eps=0.02):` ; `in_T = pred is not None and any(abs(pred - t) <= 0.02 for t in T)` |
| 7 | **CONFIRMED** | B:148, B:166, B:43, B:168-170 | `gt = json.loads(ex["ground_truth"]).get("gt_parse", {})` ; `money = cord_money_lines(gt.get("menu"))` ; `for k in ("price", "unitprice"):` ; `tau = ((parse_money(sub.get("tax_price")) or 0.0)` / `+ (parse_money(sub.get("service_price")) or 0.0)` / `- (parse_money(sub.get("discount_price")) or 0.0))` |
| 8 | **CONFIRMED** | F:169-172, F:176-182, F:184 | `pred_total_words = [words[wid] for wid, pid in word_pred.items()` / `if pid == pred_total_class and wid < len(words)]` ; `prices_ann = [a for a in anns if a.get("label") == PRC_ID]` / `rows = row_group(prices_ann)` / `if vs: per_line_prices.append(sum(vs))` ; `taxes = [parse_money(a["text"]) for a in anns if a.get("label") == TAX_ID]` |
| 9 | **CONFIRMED** | `sroie_canonical.py:22`, `:268`, A:322 | `DARENTANG  = "darentang/sroie"  # Task-1 OCR source` ; `"""Pull SROIE Task-1 OCR from darentang/sroie 'test' split.` ; `"ocr_source": "darentang/sroie Task-1",`. No OCR engine (pytesseract / easyocr / paddle) appears anywhere in the repository |
| 10 | **CONFIRMED** | repo-wide search | Only hit for `theta` is `paper/asyu/audit/tools/make_docx.py:310`, a LaTeX macro allow-list entry: `'sigma', 'tau', 'theta', 'varepsilon', 'toprule', 'midrule',`. No code computes a single-amount-equal-to-π fraction. `0.07` / `0.41` appear nowhere as such a statistic |
| 11 | **CONFIRMED** | B:50, F:79, A:212 | `def I3_reachable(money_lines, tau, eps=0.02):` (B and F, scalar `tau`) vs `def I3_reachable_multi(money_lines, tau_candidates, eps=0.02):` (A only) |
| 12 | **CONFIRMED** | G:21, G:60, G:65-67 | `from A_donut_cord_on_sroie import extract_money_lines, TAU_CAP  # noqa` ; `money, tau, capped = extract_money_lines(ocr_lines)` ; `for kmin in (1, 2):` / `T = I3_reachable(money, tau, kmin) if money else set()` |
| 13 | **CONFIRMED** | Q:92, Q:96 | `p = parse_money(m.get("price"))` (no `unitprice` fallback) ; `tax = parse_money(total_info.get("tax_price")) if isinstance(total_info, dict) else None` where `total_info = gt.get("total")` (Q:95). B instead reads `sub_total` and adds service, subtracts discount |
| 14 | **PARTIAL** | see below | Softmax extraction and matched-coverage composition located; per-corpus threshold is implicit in a top-k selection, not an explicit stored threshold |

### Claim 14 detail

Softmax scores are **not recomputed** in the composition step; they are read from
per-corpus baseline artifacts as a stored field `softmax_score`
(`runs/M_baseline_softmax.json`, `runs/MB_cord_baseline.json`,
`runs/MF2_wildreceipt_softmax.json`, key `softmax_score` on every result row).

Matched coverage and the intersection are computed in
`scripts/smoke/MF2_wildreceipt_softmax.py`. The composition is a **top-k
selection**, where k is σ's accept count, not a stored per-corpus threshold:

```
    sigma_correct_ids = {rid for rid in sigma_accepts if f_results[rid]["correct"]}
    smax_correct_ids = {rid for rid in softmax_accepts if f_results[rid]["correct"]}
    wr["b_mcnemar"] = len(sigma_correct_ids - smax_correct_ids)
    wr["c_mcnemar"] = len(smax_correct_ids - sigma_correct_ids)
```
(MF2:276-279)

**CANNOT DETERMINE** for the Donut / LayoutLMv3 softmax derivation itself: the
scripts that *produced* `softmax_score` (geometric mean over the predicted
total-value span) are not identifiable from the committed artifacts, and the
baseline scripts that write those files were not located under `scripts/`.
The value is consumed, not derived, everywhere the composition is computed.

---

## 3. Task 2 — Tables IV and V

Both scripts are **CPU-only post-processing over committed predictions** and
needed no checkpoint: G reads `runs/A_donut_cord_on_sroie.json` (`G:24`,
`G:63 pred = a_results.get(stem, {}).get("pred", gold)`), Q reads
`runs/B_donut_cord_on_cord.json` (`Q:116`).

Arguments used: **defaults, no arguments**, invoked as
`python3 -P scripts/smoke/G_robustness.py` and
`python3 -P scripts/smoke/Q_money_noise_cord.py` from the repository root.
`-P` is required only because of the `types.py` shadowing described above.
`datasets==2.19.0` is required for G.

### Table IV — cardinality guard on SROIE, n = 347

| Setting | Metric | Paper | Recomputed | Match |
|---|---|---|---|---|
| kmin = 1 (no guard) | Coverage | 0.161 | **0.15561959654178675** | **NO** |
| kmin = 1 (no guard) | Precision | 0.929 | **0.9259259259259259** | **NO** |
| kmin = 2 (guard on) | Coverage | 0.029 | **0.02881844380403458** | YES |
| kmin = 2 (guard on) | Precision | 0.900 | **0.9** | YES |

Artifact written: `runs/G_robustness.json`. n = 347 confirmed, `tau_cap_fires` 0.

### Table V — injected money-line noise on CORD, 10 seeds

`NOISE_RATES = [0.0, 0.05, 0.10, 0.20, 0.40]` (Q:27), `SEEDS = list(range(10))`
(Q:28). **n = 85 receipts**, from CORD `split="test"` (100) minus those without
items or a total (Q:118). The paper's Table V does not state this n, and it is
not the 200 of the headline CORD row.

| r | Coverage paper | Coverage recomputed | Match | Precision paper | Precision recomputed | Match | Precision 95% CI recomputed |
|---|---|---|---|---|---|---|---|
| 0.00 | 0.267 | **0.2705882352941176** | **NO** | 0.957 | **0.9565217391304348** | YES | [0.9565, 0.9565] |
| 0.05 | not printed | 0.2400000000000000 | – | not printed | 0.9552536231884058 | – | [0.9475, 0.9665] |
| 0.10 | 0.208 | **0.2082352941176471** | YES | 0.949 | **0.9489096573208722** | YES | [0.9417, 0.9613] |
| 0.20 | 0.160 | **0.1635294117647059** | **NO** | 0.964 | **0.9629746835443038** | **NO** | [0.9391, 0.9856] |
| 0.40 | 0.091 | **0.0882352941176470** | **NO** | 0.980 | **0.975** | **NO** | [0.925, 1.0] |

**Item 4 of the task, the r = 0.00 CI.** It is degenerate in the recomputation
too: `[0.9565217391304348, 0.9565217391304348]`. At rate 0 no noise is injected,
so all ten seeds are identical and the bootstrap over ten identical values is a
point. The paper's `[0.957, 0.957]` is therefore reproduced in kind.

**Version control on this result.** The deviations are not a library artifact.
Q was run under `datasets` 5.0.1 and again under 2.19.0 and produced **identical
numbers** both times. Artifact written: `runs/Q_money_noise_cord.json`.

Neither artifact has been committed; both are new files in `runs/`.

---

## 4. Task 3 — headline numbers from committed artifacts

Definitions used throughout. **Coverage** = accepted / n. **Precision** =
(accepted and `correct`) / accepted. **σ accept** = the stored boolean
`sigma_accept`. **Softmax matched** = the top-|σ accepts| rows of the same
corpus ranked by the stored `softmax_score`, descending. **Intersection** =
accepted by both. **σ-only** = σ accepts not in the softmax matched set.
Fields used: `id`, `correct`, `sigma_accept`, `softmax_score` from
`runs/MB_cord_baseline.json` (CORD, 200), `runs/M_baseline_softmax.json`
(SROIE, 347), `runs/MF2_wildreceipt_softmax.json` → `WildReceipt_results`
(WildReceipt, 472). Wilson interval at z = 1.959963984540054.

### 3a — Table I, pooled n = 1019

| Rule | n_acc paper / recomputed | Coverage paper / recomputed | n_corr paper / recomputed | Precision paper / recomputed | Wilson paper / recomputed | Match |
|---|---|---|---|---|---|---|
| σ | 386 / **386** | 0.379 / **0.378803** | 365 / **365** | 0.946 / **0.945596** | [0.918,0.964] / **[0.9183,0.9641]** | YES |
| softmax (matched) | 386 / **386** | 0.379 / **0.378803** | 368 / **368** | 0.953 / **0.953368** | [0.927,0.970] / **[0.9275,0.9703]** | YES |
| σ ⊓ softmax | 184 / **184** | 0.181 / **0.180569** | 182 / **182** | 0.989 / **0.989130** | [0.961,0.997] / **[0.9612,0.9970]** | YES |
| σ-only | 202 / **202** | 0.198 / **0.198234** | 183 / **183** | 0.906 / **0.905941** | [0.858,0.939] / **[0.8578,0.9390]** | YES |
| softmax-only | 202 / **202** | 0.198 / **0.198234** | 186 / **186** | 0.921 / **0.920792** | [0.875,0.951] / **[0.8752,0.9507]** | YES |

**Table I reproduces in full, every cell including the intervals.**

### 3b — Per-corpus, Fig. 2 and Table II

| Corpus | Quantity | Paper | Recomputed | Match |
|---|---|---|---|---|
| CORD | σ | 0.990 (99) | **98/99 = 0.98990** | YES |
| CORD | softmax matched | 0.960 (99) | **95/99 = 0.95960** | YES |
| CORD | σ⊓softmax | 54/55 = 0.982, [0.904,0.997] | **54/55 = 0.98182, [0.9039,0.9968]** | YES |
| CORD | σ-only | 1.000 (44) | **44/44 = 1.00000** | YES |
| SROIE | σ | 0.863 (73) | **63/73 = 0.86301** | YES |
| SROIE | softmax matched | 0.945 (73) | **69/73 = 0.94521** | YES |
| SROIE | σ⊓softmax | 15/15, [0.796,1.000] | **15/15 = 1.00000, [0.7961,1.0000]** | YES |
| SROIE | σ-only | 0.828 (58) | **48/58 = 0.82759** | YES |
| WildReceipt | σ | 0.953 (214) | **204/214 = 0.95327** | YES |
| WildReceipt | softmax matched | 0.953 (214) | **204/214 = 0.95327** | YES |
| WildReceipt | σ⊓softmax | 113/114 = 0.991, [0.952,0.998] | **113/114 = 0.99123, [0.9520,0.9984]** | YES |
| WildReceipt | σ-only | 0.910 (100) | **91/100 = 0.91000** | YES |

**All twelve reproduce.**

### 3c — Table III, paired McNemar

| Set | b paper | c paper | χ² paper | p paper | Source in code | Match |
|---|---|---|---|---|---|---|
| Pooled | 185 | 188 | 0.011 | 0.917 | `runs/MF2_wildreceipt_softmax.json` → `Pooled_McNemar` = `{"b":185,"c":188,"chi2":0.0107,"p_value":0.9175}` | YES, as a stored value |
| CORD | 44 | 41 | 0.047 | 0.828 | **hardcoded constant** MF2:46 `"b_mcnemar": 44, "c_mcnemar": 41,` | YES, as a constant |
| SROIE | 50 | 56 | 0.236 | 0.627 | **hardcoded constant** MF2:55 `"b_mcnemar": 50, "c_mcnemar": 56,` | YES, as a constant |
| WildReceipt | 91 | 91 | 0.005 | 0.941 | computed, MF2:276-279 | YES |

**This is the one place the numbers reproduce but the provenance does not hold.
See Discrepancy D1.** Only the WildReceipt row is computed from data. CORD and
SROIE are literals in the source. An independent recomputation of b and c from
the per-receipt artifacts under the definition "σ accepted and correct, minus
softmax accepted and correct" does **not** reproduce 44/41 or 50/56, because
matched coverage makes the discordant accept sets equal in size.

### 3d — Section V-E, SROIE

| Quantity | Paper | Recomputed | Match | Field |
|---|---|---|---|---|
| mean amounts, wrongly accepted | 6.7 (10) | **6.700000** (n=10) | YES | `results[*].money_count` where `in_T and not correct` |
| mean amounts, correctly accepted | 4.3 (63) | **4.349206** (n=63) | YES | same, `in_T and correct` |
| one-sided permutation p | 0.004 | **0.004250** (B=20000, seed 0) | YES | on `money_count` |
| mean τ candidates, wrongly accepted | 3.30 | **3.300000** | YES | `results[*].n_tau_candidates` |
| mean τ candidates, correctly accepted | 3.33 | **3.333333** | YES | same |
| overall mean τ candidates | 3.12 | **3.115274** | YES | all 347 |

**Confirmed: 3.12 and 3.30 / 3.33 are the same quantity** (`n_tau_candidates`,
per receipt) at different groupings — all receipts versus the accepted split.
Neither is a per-line measure, and neither counts readings.

### 3e — Worked examples, printed from `runs/A_donut_cord_on_sroie.json`

```
{'id': 'X51005675103', 'ocr_lines': 33, 'money_count': 7, 'n_tau_candidates': 5,
 'tau_candidates': [0.0, 100.17, 40.28, -5.67, 94.5], 'T_size': 119,
 'pred': 5.67, 'gold': 100.17, 'in_T': True, 'correct': False}

{'id': 'X00016469671', 'ocr_lines': 27, 'money_count': 4, 'n_tau_candidates': 2,
 'tau_candidates': [0.0, -1.0], 'T_size': 7,
 'pred': 170.0, 'gold': 170.0, 'in_T': True, 'correct': True}
```

Both match the expected records exactly. Note in the first: 7 money lines
generate `T_size` 119 once unioned over 5 τ offsets, π = 5.67 is accepted while
gold is 100.17, and −5.67 is itself one of the τ candidates.

### 3f — k_min distributions

| Corpus | Method | k_min = 1 | k_min = 2 | Note |
|---|---|---|---|---|
| WildReceipt | `abs(tau) > 0.02` over `results[*].tau` | **288** (61.0%) | **184** (39.0%) | matches the expected 288 / 184 |
| SROIE | over `results[*].tau_candidates` | **322 of 347** receipts carry at least one non-zero τ, so a k_min = 1 path exists | **all 347** also carry `0.0`, so a k_min = 2 path always exists | both guards are active on the same receipt |
| CORD | **recomputed without re-running the model**, replicating B:168-170 on the gold `sub_total` of CORD-v2 test + validation, n = 200 | **80** (40.0%) | **120** (60.0%) | see note |

CORD note: `runs/B_donut_cord_on_cord.json` does not persist `tau` (result keys
are `T_size, correct, gold, id, in_T, pred`). Rather than patch B, the τ
expression at B:168-170 was replicated verbatim against the same gold field on
the same 200 receipts. This required no code change, so **no patch was made and
no before/after identity check was needed** (see section 7).

### 3g — Sections V-C and V-D

Scripts: the artifacts are `runs/U2_orthogonality.json` and
`runs/U3_risk_coverage.json`. The paper consumes them through the generated
macros in `paper/asyu/numbers_orth.tex` and `numbers_riskcov.tex`.

| Quantity | Paper | Recomputed from artifact | Match |
|---|---|---|---|
| lift vs random control | +0.050 | **0.05039539249032077** | YES |
| its CI | [0.013, 0.094] | **[0.013271344040574728, 0.09420289855072461]** | YES |
| its p | 0.003 | **0.003** | YES |
| lift vs softmax+noise | +0.050 | **0.04954204913675736** | YES |
| its CI | [0.020, 0.081] | **[0.020252779046748826, 0.0810122791254867]** | YES |
| its p | 0.0005 | **0.0005** | YES |
| φ | 0.183 | **0.18275733071187777** | YES |
| φ permutation p | 0.0002 | **0.00024993751562109475** | YES |
| AURC softmax | 0.054 | **0.054424216226276335** | YES |
| AURC σ | 0.027 | **0.02701688472208868** | YES |
| paired-bootstrap ΔAURC | 0.027 | **0.027407331504187657** | YES |
| its CI | [0.002, 0.059] | **[0.0016045899770525222, 0.05886472785831679]** | YES |
| its p | 0.018 | **0.018** | YES |

**All thirteen reproduce.**

### 3h — Fig. 4 latency

Artifact `runs/time_budget_cpu.json`, produced by
`scripts/fresh_run/time_budget_cpu.py`.

| Quantity | Paper | Recomputed | Match |
|---|---|---|---|
| median | 4.07 µs | **4.07** | YES |
| p99 | 312 µs | **311.646** | YES |
| max | 715 µs | **715.059** | YES |
| n | 819 | **819** | YES |

---

## 5. Discrepancies found

**D1. Table III's CORD and SROIE rows are hardcoded constants, and the SROIE
constant contradicts the SROIE artifact.** MF2:47-56 contains:

```
    "SROIE": {
        "n": 347,
        "sigma_acc": 75,  "sigma_corr": 65,
        "smax_acc":  75,  "smax_corr":  71,
        "int_acc":   15,  "int_corr":   15,
        "sigonly_acc": 60, "sigonly_corr": 50,
        "smonly_acc":  60, "smonly_corr": 56,
        "b_mcnemar": 50, "c_mcnemar": 56,
    },
```

The committed SROIE artifact gives **73 accepted, 63 correct, 58 σ-only**, not
75 / 65 / 60. Consequently `MF2.Pooled.sigma_acc = 388` while the sum of the
three per-corpus artifacts is **99 + 73 + 214 = 386**.

**Effect on printed numbers: Table I and Table III are computed over pooled sets
that differ by two SROIE receipts.** Table I (via `runs/PAPER_TABLE.json`
`T1_headline`, which carries `sigma_acc: 73, sigma_corr: 63, sigma_only_n: 58`)
uses 386. Table III's pooled b = 185, c = 188 comes from the 388 version. Both
sets of printed numbers reproduce from their own source; the two sources
disagree with each other.

**D2. Table IV does not fully reproduce.** kmin = 1 coverage is 0.1556 against a
printed 0.161, and precision 0.9259 against a printed 0.929. The kmin = 2 row
reproduces. Recomputed from a fresh run of the committed G.

**D3. Table V does not fully reproduce.** Three of four printed rows differ:
r = 0.00 coverage 0.2706 vs 0.267; r = 0.20 coverage 0.1635 vs 0.160 and
precision 0.9630 vs 0.964; r = 0.40 coverage 0.0882 vs 0.091 and precision 0.975
vs 0.980. Deviations are small but reproducible and are not a library-version
artifact: identical under `datasets` 5.0.1 and 2.19.0.

**D4. Table V's n is 85, not 200.** Q uses CORD `split="test"` only, minus
receipts lacking items or a total. The headline CORD row uses test + validation,
n = 200. This is a second, larger reason the r = 0 row differs from the headline
coverage, independent of the extractor field differences in claim 13.

**D5. The paper's per-corpus k_min statement does not hold in the code.** With
`kmin = 1 if abs(tau) > eps else 2` evaluated per receipt: WildReceipt runs
k_min = 1 on 288 of 472 (61.0%) and CORD on 80 of 200 (40.0%). On SROIE both
guards are active on every receipt, because `0.0` is always a τ candidate and
322 of 347 receipts also carry a non-zero one.

**D6. `U2_orthogonality` uses a different pooled intersection.**
`U2.pooled.n_intersection = 168` and `p_softmax_matched = 0.9378`, against
Table I's intersection of 184 at softmax precision 0.9534. The V-C lifts all
reproduce, but they are computed on a different matched-coverage selection than
Table I's.

**D7. A silent-failure path in the OCR loader.** `load_sroie_ocr_lines` returns
`{}` on any exception (`sroie_canonical.py:281-282`), and G then writes a
complete artifact of zeros rather than failing. Observed directly in this
session under `datasets` 5.0.1.

**D8. `types.py` at the repository root is committed zlib data** and prevents
any Python process from starting in the repository root.

**Consistency with the earlier audit:** every Task 1 claim is CONFIRMED, so the
audit's description of the code is accurate. Claim 14 is the only PARTIAL, and
that is an incompleteness in the audit rather than an error: the audit did not
state where `softmax_score` originates, and it still cannot be determined.

---

## 6. Cannot determine

| Item | Blocker |
|---|---|
| The derivation of `softmax_score` for Donut and LayoutLMv3 | The scripts that write `M_baseline_softmax.json` and `MB_cord_baseline.json` were not found under `scripts/`. The value is consumed as a stored field everywhere it is used. No script in the repository computes a geometric mean over a predicted total-value span |
| The origin of θ = 0.07 / 0.05 / 0.41 | No code computes it. Repo-wide search found only a LaTeX macro name |
| Whether the printed Table IV and Table V values were ever produced by the committed G and Q | Their artifacts were absent before this session. The recomputation differs in 2 of 4 and 5 of 8 cells respectively, so either the code or the inputs have changed since the paper's numbers were generated. Which of the two cannot be determined |
| Re-running A, B or F end to end | Requires the Donut and LayoutLMv3 checkpoints and GPU-scale inference over 1019 receipts. Not attempted; not required for any item above |

---

## 7. Patches made

**None.** No source file was modified. The two obstacles were handled without
editing code:

- `types.py` shadowing: worked around with the interpreter flag `python3 -P`.
- CORD `tau` not persisted in B: rather than patch B to store it, the τ
  expression at B:168-170 was replicated verbatim in a separate read-only
  script against the same gold `sub_total` field and the same 200 receipts.

Because no code changed, the before/after identity check on `in_T` and `correct`
is **not applicable**: `runs/B_donut_cord_on_cord.json`,
`runs/A_donut_cord_on_sroie.json` and `runs/F_layoutlmv3_on_wildreceipt.json`
are byte-identical to their committed state and were only read.

Two artifacts were **created** by running committed scripts with default
arguments: `runs/G_robustness.json` and `runs/Q_money_noise_cord.json`. Neither
is committed. One artifact was **deleted before commit**: the zeroed
`runs/G_robustness.json` produced under `datasets` 5.0.1, which was invalid for
the reason in D7.
