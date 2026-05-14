"""MF v3: sigma vs softmax baseline on WildReceipt (labeled-amounts, encoder-only).

v3 deferred: Theivaprakasham/wildreceipt provides only 'image_path' strings that
point to files in the original MMOCR distribution (not bundled with HF). Loading
those files requires downloading the WildReceipt image archive separately, which
is a deployment concern beyond Paper 1's scope.

Decision: gracefully skip MF, emit a clear 'image-archive-required' summary, and
let the Paper 1 story rely on:
  - CORD (DONUT generative + softmax baseline available)  → sigma vs softmax comparable
  - SROIE (DONUT generative + softmax baseline available) → sigma vs softmax comparable
  - WildReceipt (LayoutLMv3 encoder-only, sigma only from F)  → sigma alone reported

The regime-distinction story is still defensible: sigma wins on CORD (labeled-amounts,
generative), softmax wins on SROIE (OCR-derived, generative); WildReceipt provides a
cross-architecture replication of sigma's behavior without the softmax-baseline column.
Journal version can add the softmax baseline once the image archive is wired in.
"""
import json
from pathlib import Path

F_OUT = Path("runs/F_layoutlmv3_on_wildreceipt.json")
OUT = Path("runs/MF_wildreceipt_baseline.json")
OUT.parent.mkdir(parents=True, exist_ok=True)


def main():
    # Read F's results so we can report sigma alone
    f_summary = {}
    n_sigma_accept = 0
    n_correct_sigma = 0
    n_total = 0
    if F_OUT.exists():
        f = json.loads(F_OUT.read_text())
        f_summary = f.get("summary", {})
        for r in f.get("results", []):
            n_total += 1
            if r.get("in_T"):
                n_sigma_accept += 1
                if r.get("correct"):
                    n_correct_sigma += 1

    summary = {
        "corpus": "WildReceipt test (labeled-amounts, encoder-only)",
        "status": "deferred",
        "reason": (
            "Theivaprakasham/wildreceipt provides only image_path strings that reference "
            "the original MMOCR distribution archive, which is not bundled with the HF "
            "dataset. Inference-with-softmax requires downloading the WildReceipt image "
            "archive separately. Skipped from base run; deferred to journal version."
        ),
        "sigma_from_F": {
            "n": n_total,
            "coverage": (n_sigma_accept / max(1, n_total)),
            "precision": (n_correct_sigma / max(1, n_sigma_accept)) if n_sigma_accept else None,
            "n_accepted": n_sigma_accept,
            "n_correct": n_correct_sigma,
            "source": str(F_OUT),
        },
        "F_summary": f_summary,
        "verdict": (
            "Paper 1 baseline comparison is 2-corpus (CORD + SROIE) for sigma vs softmax. "
            "WildReceipt contributes a 3rd corpus for sigma alone (cross-architecture "
            "validation), and a softmax baseline for it goes to the journal version."
        ),
    }
    OUT.write_text(json.dumps({"summary": summary}, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
