# Code-vs-Paper Audit: the amount extractor τ

Audit of the implementation against "Sigma-Verifier: Reducing Silent Errors in
Receipt Total Extraction via Structural Arithmetic Verification". Read from the
code and the committed run artifacts only. Paths are relative to the repository
root. Line numbers are from the state audited.

---

## Answer to the primary question

**No.** The code does not implement the multi-candidate amount extractor the
paper describes, and no such extractor exists anywhere in the repository.

What the code implements is a **multi-candidate τ**, where τ is an **additive
scalar adjustment** (tax, service charge, discount) and the candidates are
alternative *values of that scalar*. There is exactly **one** amount multiset
`M` per receipt. The acceptance test is

```
sigma fires iff  exists tau_k in candidates,  exists S subset M
                 with |S| >= kmin(tau_k)  and  sum(S) + tau_k ~= pi
```

which is stated verbatim in the module docstring at
`scripts/smoke/A_donut_cord_on_sroie.py:5-13`. The paper's Section III equation
has no τ term at all: it defines `T(M) = {sum_{i in S} m_i}`. The implemented
reachable set is `{sum(S) + tau_k}`.

This is a mismatch of object (scalar vs multiset), of mechanism (additive offset
vs alternative parse), and of the governing equation.

---

## Claim table

| # | Claim | Paper says | Code does | Verdict | Evidence |
|---|---|---|---|---|---|
| 1 | τ is the only corpus-specific part; it builds M | τ is the extractor producing M | τ is an additive scalar adjustment added to every subset sum. M is built by a separate, unnamed scan. The three corpora use three unrelated M-builders | **MISMATCH** | `A_donut_cord_on_sroie.py:_scan_money_and_tax:139-169` (M), `:extract_money_lines_v13:172-191` (τ set), `I3_reachable_multi:212-231` (`s + tau_c`, line 230) |
| 2a | On SROIE τ keeps ambiguous line readings as candidate sets `M_k` | multiple multisets | one multiset `money`; candidates are scalars `{0.0} ∪ {per-category last-then-sum} ∪ {each individual signed amount}` | **MISMATCH** | `A:extract_money_lines_v13:174-191`; `cands` is a set of floats, line 175, 184, 186 |
| 2b | σ accepts if ANY candidate set contains a witness | union over multisets | union over τ scalars of one DP's reachable set | **PARTIAL** (union exists, over the wrong object) | `A:I3_reachable_multi:224-231` |
| 2c | 3.12 candidates per receipt | candidate readings | mean number of **τ scalars** per receipt = **3.1153** | **MISMATCH of definition, number reproduces** | `A:main:291,297,318`; artifact `runs/A_donut_cord_on_sroie.json` `summary.tau_candidates_per_receipt_mean = 3.115273775216138` |
| 3a | Multi-candidate τ is the default and produces Tables I, II, Figs 2, 3 | yes | true **for SROIE only**. CORD and WildReceipt have no multi-candidate path at all; both call a single-τ `I3_reachable` | **PARTIAL** | `B_donut_cord_on_cord.py:I3_reachable:50`; `F_layoutlmv3_on_wildreceipt.py:I3_reachable:79` |
| 3b | Table IV uses a fixed single-candidate extractor | yes | true: imports the v12 single-τ function and forces `kmin` in `(1,2)` | **MATCH** | `G_robustness.py:21,60,65-67` |
| 3c | Table V uses a fixed single-candidate extractor; that is why r=0 CORD coverage differs from the headline | extractor difference | CORD never had a multi-candidate extractor. The difference is (i) `price` only vs `price`-then-`unitprice` fallback, and (ii) τ from `total.tax_price` vs `sub_total` tax+service−discount | **MISMATCH** (stated cause is wrong) | headline `B:cord_money_lines:39-48` (line 43 fallback), `B:168-170` (τ); ablation `Q_money_noise_cord.py:extract_cord_items:80-97` (line 92 price only, line 96 τ) |
| 4 | V-E: "candidate readings per line" 3.30 vs 3.33 | per-line readings | mean **τ candidates per receipt**, split by correctness: **3.30** (10 wrongly accepted) vs **3.3333** (63 correctly accepted). Same quantity as the 3.12, not a per-line measure | **MISMATCH of definition, numbers reproduce** | recomputed from `runs/A_donut_cord_on_sroie.json` `results[*].n_tau_candidates` |
| 4b | V-E: 6.7 vs 4.3 extracted amounts | wrong vs correct accepts | **6.7** vs **4.3492** | **MATCH** | recomputed from `results[*].money_count` |
| 5 | CORD: M from the per-field JSON | ambiguous | from the **dataset's gold annotation JSON** (`gt_parse.menu[*].price/unitprice`). Donut supplies only π | **PARTIAL / under-disclosed** | `B:148` (`gt_parse`), `B:166`, `B:cord_money_lines:39-48` |
| 5b | Is the labelled total in M? | excluded | excluded: M is built from `menu` price/unitprice only; on SROIE, TOTAL_LIKE lines are skipped | **MATCH** | `B:cord_money_lines:39-48`; `A:_scan_money_and_tax:150-151` |
| 6 | WildReceipt: M from per-token `Prod_price_value` annotations | annotations | **gold** annotations (`item["anns"]`), not LayoutLMv3 predictions. Predictions supply only π. Prices are additionally **row-grouped and summed per row**, so elements of M are row sums, not token prices | **PARTIAL / under-disclosed** | `F:176` (`anns`), `F:169-172` (π from `word_pred`), `F:177-182` (row grouping) |
| 7a | k_min ∈ {1,2} chosen per corpus: 2 on CORD and WildReceipt, 1 on SROIE | fixed per corpus | computed **per receipt** as `kmin = 1 if abs(tau) > eps else 2`; on SROIE, **per τ candidate** | **MISMATCH** | `A:226`, `B:51`, `F:80`, `Q:41` |
| 7b | Chosen label-free by a fraction θ, values 0.07 / 0.05 / 0.41, insensitive over θ∈[0.1,0.4] | a θ rule | **no θ exists in the repository.** No code computes "extractor returns a single amount equal to π". The only textual hit is a LaTeX macro name in `make_docx.py:310` | **MISMATCH ,  unimplemented** | repository-wide search for `theta`, `0.41`, `single_amount`, `cardinality_guard` |
| 7c | Measured k_min per corpus | 2 on WildReceipt | **k_min=1 on 288/472 receipts (61.0%)**, k_min=2 on 184 (39.0%) | **MISMATCH** | recomputed from `runs/F_layoutlmv3_on_wildreceipt.json` `results[*].tau` |
| 7d | k_min uses only (π, M), no gold labels | label-free | k_min is derived from τ. On CORD, τ comes from the **gold** `sub_total`; on WildReceipt, from the **gold** `Tax_value` annotation. So k_min depends on gold labels on two of three corpora | **MISMATCH** | `B:168-170`, `F:184` |
| 8a | ε = 0.02 | yes | yes, default and at every call site | **MATCH** | `A:212,299`, `B:50`, `F:79`, `Q:41` |
| 8b | Integer-cent 0/1-knapsack DP | yes | yes: `int(round(v*100))`, dict DP tracking minimum cardinality per reachable sum | **MATCH** | `A:216-223`, `B:52-62`, `F:81-91` |
| 9 | SROIE OCR source | "OCR-derived" | the dataset's **shipped Task-1 transcriptions**, pulled from the `darentang/sroie` HF mirror, words grouped into lines by y-coordinate. **No OCR engine was run by us** | **PARTIAL / under-disclosed** | `sroie_canonical.py:22` (`DARENTANG = "darentang/sroie"`), `:load_sroie_ocr_lines:267-295`; `A:322` (`"ocr_source": "darentang/sroie Task-1"`) |

---

## What a "candidate" actually is

Not an alternative multiset for the receipt, and not an alternative reading of
one line as the paper implies. It is one of at most eight **scalar** values
(`MAX_TAU_CANDIDATES = 8`, `A:44`), assembled at `A:175-190`:

1. `0.0`, always present (line 175);
2. the v12 aggregate: for each of tax / service / discount, the **last**
   occurrence, signed and summed (lines 179-184);
3. **each individual** signed tax / service / discount amount (lines 185-186).

Capped at `|τ| ≤ 10000` (`TAU_CAP`, line 187) and truncated to the 7 largest by
absolute value plus `0.0` if more than eight (lines 188-190).

There is no Cartesian product and no union of multisets, because there is only
one multiset. The union at `A:224-231` is over τ values.

---

## One SROIE receipt, end to end

The artifact persists counts and τ values but **not** the OCR line strings or the
money multiset itself, so the amounts cannot be shown without re-running against
the HF dataset and the Donut checkpoint. At the level the artifact permits:

**`X51005675103` ,  wrongly accepted**

| field | value |
|---|---|
| `ocr_lines` | 33 |
| `money_count` (\|M\|) | 7 |
| `n_tau_candidates` | 5 |
| `tau_candidates` | `[0.0, 100.17, 40.28, -5.67, 94.5]` |
| `T_size` | 119 |
| `pred` (π) | 5.67 |
| `gold` | 100.17 |
| `in_T` | True |
| `correct` | **False** |

Seven money lines generate a reachable set of 119 values once unioned across five
τ offsets. The predicted total 5.67 is accepted while the true total is 100.17,
and `-5.67` is itself one of the τ candidates. This is the mechanism behind the
SROIE false accepts: the τ union inflates `T` and the discount value re-enters
the acceptance test as an offset.

**`X00016469671` ,  correctly accepted**: 27 OCR lines, |M|=4,
`tau_candidates=[0.0, -1.0]`, `T_size`=7, π = gold = 170.0.

---

## Reproduction of the paper's numbers

| Paper value | Recomputed | Source |
|---|---|---|
| 3.12 candidates/receipt | **3.1153** | mean `n_tau_candidates` over 347 |
| 3.30 (wrongly accepted) | **3.30** | mean `n_tau_candidates` over the 10 |
| 3.33 (correctly accepted) | **3.3333** | mean `n_tau_candidates` over the 63 |
| 6.7 vs 4.3 amounts | **6.7 vs 4.3492** | mean `money_count`, same split |
| SROIE σ: 73 accepted, 0.863 | **73, 0.8630** | `in_T` / `correct` |
| CORD σ coverage | **0.4950** (99/200) | `runs/B_donut_cord_on_cord.json` |

Every number reproduces. The 3.12 and the 3.30/3.33 are **the same quantity at
different groupings**, not two different measurements.

---

## Cannot determine

- **Tables IV and V cannot be verified.** `runs/G_robustness.json` and
  `runs/Q_money_noise_cord.json` are **not in the repository**. The scripts
  exist; their outputs do not. Whether the published Table IV and Table V values
  came from these scripts cannot be determined from the repository.
- **CORD's k_min distribution cannot be recomputed**: `B` does not persist `tau`
  in `results` (`B` result keys are `T_size, correct, gold, id, in_T, pred`).
- The provenance of θ = 0.07 / 0.05 / 0.41 cannot be determined; no code
  produces these values.

---

## Corrections the paper needs before the talk

1. **Section III, "Amount extraction".** The described mechanism does not exist.
   Replace with: a single multiset M per receipt, plus a set of candidate
   **additive adjustments** τ_k (tax, service, discount) tried in union. State
   that ambiguous *lines* are not re-parsed into alternative multisets.

2. **Section III, Eq. for T(M).** The equation omits τ. The implemented set is
   `T(M) = {sum_{i in S} m_i + tau_k}`. Add the τ term or the equation does not
   describe the system.

3. **Section III, cardinality guard, and Section IV, Settings.** k_min is not
   fixed per corpus. It is `1 if |τ| > ε else 2`, evaluated per receipt and, on
   SROIE, per τ candidate. On WildReceipt this yields k_min=1 on **61%** of
   receipts, contradicting "k_min=2 on CORD and WildReceipt".

4. **Section III, the θ rule.** Delete or reimplement. There is no θ in the code
   and no computation of the "single amount equal to π" fraction. The values
   0.07 / 0.05 / 0.41 and the insensitivity claim over θ∈[0.1,0.4] are
   unsupported by the repository.

5. **Section III/IV, k_min is not label-free.** k_min depends on τ, and τ is read
   from gold annotations on CORD (`sub_total`) and WildReceipt (`Tax_value`).
   The "deployment-time decision rule, not a hyperparameter tuned on labels"
   sentence is false as implemented.

6. **Section IV, Datasets / Section III.** State plainly that on CORD and
   WildReceipt, **M and τ are read from ground-truth annotations**, and only π
   comes from the model. σ is fed gold amounts on two of three corpora. This
   materially qualifies every deployment and audit-trail claim.

7. **Section IV.** WildReceipt M elements are **row sums** of `Prod_price_value`
   tokens, not individual token prices. Undisclosed.

8. **Section IV, extractor settings paragraph.** The stated reason for the r=0
   CORD coverage difference is wrong. CORD has no multi-candidate extractor. The
   real causes are the missing `unitprice` fallback and a different τ source in
   the noise script.

9. **Section V-E.** "Candidate readings per line (3.30 against 3.33)" is neither
   per line nor readings. It is mean τ candidates per receipt. Either relabel it
   or drop it, and note it is the same quantity as the 3.12 in Section III.

10. **Section IV, Datasets.** Say that SROIE text is the dataset's shipped
    Task-1 transcription (`darentang/sroie` mirror, grouped into lines by
    y-coordinate), not output of an OCR engine run for this work. "OCR-derived"
    currently implies the latter.

11. **Tables IV and V.** Regenerate and commit `G_robustness.json` and
    `Q_money_noise_cord.json`, or mark both tables as unreproducible from the
    released artifacts.
