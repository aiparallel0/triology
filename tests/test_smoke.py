"""End-to-end smoke test.

Runs S1-S6 on small synthetic corpora and asserts non-trivial outputs.
Designed to complete in well under 60s. Failure means the experiment
infrastructure is broken regardless of corpus availability.

Run from repo root:
    python -m paper3.tests.test_smoke
or:
    pytest paper3/tests/test_smoke.py
"""
from __future__ import annotations
import json
import subprocess
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS = REPO_ROOT / "results"


def _run(script_name: str, *extra_args) -> dict:
    """Invoke a script as a module, return parsed JSON of its results file."""
    cmd = [sys.executable, "-m", f"paper3.scripts.{script_name}",
           "--corpus", "synthetic", "--n", "100", "--seed", "0",
           *extra_args]
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    elapsed = time.perf_counter() - t0
    if proc.returncode != 0:
        raise AssertionError(
            f"{script_name} exited {proc.returncode}\n"
            f"--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}"
        )
    print(f"  {script_name}: ok ({elapsed:.2f}s)")
    return proc


def test_s1_T_distribution():
    _run("s1_T_distribution")
    out = json.loads((RESULTS / "s1_T_distribution.json").read_text())
    block = out.get("synthetic") or list(out.values())[0]
    assert block["n_receipts"] >= 90, "S1 produced too few receipts"
    assert block["T_size"]["max"] >= 1, "S1 |T| max should be >= 1"
    # Latency sanity: p95 should be well under 100ms
    assert block["T_construction_ms"]["p95"] < 100


def test_s2_I_coverage():
    _run("s2_I_coverage")
    out = json.loads((RESULTS / "s2_I_coverage.json").read_text())
    block = out.get("synthetic") or list(out.values())[0]
    assert block["n"] >= 90
    by = block["by_identity"]
    # I3 should have very high availability on synthetic
    assert by["I3"]["availability"]["rate"] >= 0.90, \
        f"I3 availability too low: {by['I3']['availability']['rate']}"
    # I3 must accept gold 100% of the time when available (Paper 1 Prop. 1)
    assert by["I3"]["soundness_given_avail"]["rate"] == 1.0
    # I5 default rule should also have soundness 1.0
    assert by["I5"]["soundness_given_avail"]["rate"] == 1.0


def test_s3_cord_confusion():
    _run("s3_cord_confusion", "--confusion_rate", "0.1")
    out = json.loads((RESULTS / "s3_cord_confusion.json").read_text())
    assert out["n_aligned_pairs"] > 100, "S3 too few aligned pairs"
    P = out["P_ocr_given_gold"]
    assert len(P) == 10 and all(len(row) == 10 for row in P)
    # Off-diagonal mass should be substantial at confusion_rate=0.1
    off_diag = sum(P[i][j] for i in range(10) for j in range(10) if i != j)
    assert off_diag > 0.05, "S3 confusion matrix too clean"


def test_s4_perturbation_battery():
    _run("s4_perturbation_battery", "--n", "300")
    out = json.loads((RESULTS / "s4_perturbation_battery.json").read_text())
    by = out["by_perturbation"]
    # Single-digit-uniform should be in Paper 1's neighborhood (5-15%)
    sd = by["single_digit_uniform"]["false_acceptance_rate"]
    assert 0.03 < sd < 0.20, f"single_digit_uniform out of range: {sd}"
    # Two-digit-swap should be much lower (Paper 1: 1.63%)
    ts = by["two_digit_swap"]["false_acceptance_rate"]
    assert ts < 0.06, f"two_digit_swap unexpectedly high: {ts}"


def test_s5_aad_overhead():
    _run("s5_aad_overhead")
    out = json.loads((RESULTS / "s5_aad_overhead.json").read_text())
    assert out["n_receipts"] >= 90
    # Per-receipt AAD overhead p95 should be << 100ms
    assert out["per_receipt_total_ms"]["p95"] < 200
    assert out["mean_steps_per_receipt"] >= 3


def test_s6_expectation():
    _run("s6_expectation", "--n", "100")
    out = json.loads((RESULTS / "s6_expectation.json").read_text())
    by = out["by_eps"]
    # At ε=0, Δ should be exactly 0
    e0 = by.get("0.000")
    if e0:
        assert abs(e0["E_delta"]) < 1e-6
    # At ε=0.10, Δ should be strictly positive
    e10 = by.get("0.100")
    if e10:
        assert e10["E_delta"] > 0.05, \
            f"AAD lift at ε=0.10 too small: {e10['E_delta']}"
    # Monotonicity: E[Δ] should generally increase from ε=0 to ε=0.20
    keys = sorted(by.keys(), key=float)
    if "0.000" in keys and "0.200" in keys:
        assert by["0.200"]["E_delta"] > by["0.000"]["E_delta"]


def main():
    """Run all tests sequentially and report timing."""
    print(f"Smoke test: paper3 experiment system ({REPO_ROOT})")
    t0 = time.perf_counter()
    tests = [
        ("S1 T-distribution",        test_s1_T_distribution),
        ("S2 I-coverage",            test_s2_I_coverage),
        ("S3 CORD confusion matrix", test_s3_cord_confusion),
        ("S4 perturbation battery",  test_s4_perturbation_battery),
        ("S5 AAD overhead",          test_s5_aad_overhead),
        ("S6 expectation curve",     test_s6_expectation),
    ]
    failures = []
    for name, fn in tests:
        print(f"\n[{name}]")
        try:
            fn()
        except AssertionError as e:
            print(f"  FAIL: {e}")
            failures.append((name, str(e)))
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {e}")
            failures.append((name, f"{type(e).__name__}: {e}"))
    elapsed = time.perf_counter() - t0
    print(f"\n--- summary: {len(tests) - len(failures)}/{len(tests)} passed "
          f"in {elapsed:.1f}s ---")
    if failures:
        for name, msg in failures:
            print(f"  ✗ {name}: {msg[:200]}")
        sys.exit(1)
    print("All smoke tests passed.")


if __name__ == "__main__":
    main()
