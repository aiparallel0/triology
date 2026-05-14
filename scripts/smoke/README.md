# Focus Sigma (ASYU Paper 1) smoke tests

Fresh-run smoke tests targeting a single RTX 4090 vast.ai instance.
Each test self-contained, ≤3 min wall-clock.

## Quick start

```bash
bash scripts/smoke/run_paper1.sh
```

## Scripts

| # | Script | GPU | Wall-clock | Validates |
|---|---|---|---|---|
| A | `A_donut_cord_on_sroie.py` | yes | ~2.5 min | Cross-corpus end-task F1 with/without I3 |
| B | `B_donut_cord_on_cord.py` | yes | ~45 s | In-distribution end-task F1 with/without I3 |
| E | `E_wildreceipt_preflight.py` | no | ~1 min | WildReceipt third-corpus viability |

## Outputs

All results land in `runs/<script>.json`.

## Success criteria

- **A**: `F1_sigma_strict_on_accepted - F1_bare ≥ +0.02` (cross-corpus regime is harsh)
- **B**: same on CORD in-distribution, threshold ≥ +0.03
- **E**: `items_2plus_rate ≥ 0.75` AND `total_parseable_rate ≥ 0.90` → include WildReceipt as third corpus

## Data sources (all auto-downloaded on first run)

- DONUT-CORD: `naver-clova-ix/donut-base-finetuned-cord-v2` (HF, ~1 GB)
- CORD-v2: `naver-clova-ix/cord-v2` (HF, CC BY 4.0)
- SROIE: `darentang/sroie` (HF mirror; override via `SROIE_HF` env var)
- WildReceipt: `download.openmmlab.com/mmocr/data/wildreceipt.tar` (Apache-2.0 via MMOCR)

## Adaptation notes

- SROIE HF mirror schemas vary. If `A_donut_cord_on_sroie.py` fails parsing gold/text fields,
  inspect a sample with `ds = load_dataset('darentang/sroie', split='test'); print(ds[0].keys())`
  and adjust the loader block at the top of the script.
- WildReceipt class IDs are read from `class_list.txt` at runtime (no hardcoded integers).
