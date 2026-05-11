"""Unit-tests for training.aad_loss.aad_structural_loss.

Run with:
    python -m <pkg>.tests.test_aad_loss

These are not part of the smoke test because torch is in
requirements.gpu.txt (heavy import); they only run if torch is
available.
"""
from __future__ import annotations
import math
import sys


def _require_torch():
    try:
        import torch  # noqa: F401
        return True
    except ImportError:
        return False


def test_oracle_logits_give_zero_loss():
    """When the decoder puts all mass on a single feasible gold sequence,
    L_struct should be ~0 at each step (log(1.0) = 0)."""
    import torch
    from ..training.aad_loss import aad_structural_loss

    # Vocab: digits 0-9 (ids 0..9), '.' (id 10), CLOSE_TOTAL (id 11),
    # pad (id 12). Vocab size 13.
    digit_token_ids = {str(i): i for i in range(10)}
    digit_token_ids["."] = 10
    close_id = 11
    V = 13

    # Receipt with items [350, 1200] cents, tau=93. Gold total = 1643 cents.
    # Decoder format: "DD.DD" -> "16.43". 5 tokens + close_total.
    items = [350, 1200]
    tau = 93
    gold_seq = ["1", "6", ".", "4", "3"]
    gold_ids = [digit_token_ids[c] for c in gold_seq]

    # B=1, T = len(gold) + 1 (for </s_total>) + 2 padding
    T_len = len(gold_ids) + 1 + 2
    labels = torch.full((1, T_len), -100, dtype=torch.long)
    for i, tid in enumerate(gold_ids):
        labels[0, i] = tid
    labels[0, len(gold_ids)] = close_id   # close tag
    # Total span: (0, len(gold_ids)) inclusive => indices 0..4
    total_spans = [(0, len(gold_ids))]

    # Build oracle logits: concentrate on the gold token at each position,
    # so softmax gives ~1.0 to the gold token. log_softmax(gold) = 0.
    logits = torch.full((1, T_len, V), -1e9)
    for i, tid in enumerate(gold_ids):
        logits[0, i, tid] = 0.0
    logits[0, len(gold_ids), close_id] = 0.0

    loss = aad_structural_loss(
        logits, labels, [items], [tau], total_spans, digit_token_ids,
        close_total_token_id=close_id,
    )
    assert loss.item() < 1e-4, f"oracle loss should be ~0, got {loss.item()}"
    print(f"  oracle loss = {loss.item():.6f}  (expected ~0)  OK")


def test_uniform_logits_match_log_vocab_minus_log_mask():
    """For uniform logits, p_t(sigma) = 1/V everywhere, so the mass on
    M_t is |M_t|/V and L_struct(t) = log(V) - log(|M_t|).

    With items [350, 1200] tau=93, T = {93, 443, 1293, 1643}, gold=1643.
    At step 0 (prefix=""), the mask includes all digits that can start
    a value in T (1, 4, 6 — also 9 because 93 starts with 9; also 1
    because 1643 starts with 1; etc.). We just sanity-check the upper
    bound: L_struct(t) <= log(V).
    """
    import torch
    from ..training.aad_loss import aad_structural_loss

    digit_token_ids = {str(i): i for i in range(10)}
    digit_token_ids["."] = 10
    close_id = 11
    V = 13

    items, tau = [350, 1200], 93
    gold_seq = ["1", "6", ".", "4", "3"]
    gold_ids = [digit_token_ids[c] for c in gold_seq]
    T_len = len(gold_ids) + 1 + 2
    labels = torch.full((1, T_len), -100, dtype=torch.long)
    for i, tid in enumerate(gold_ids):
        labels[0, i] = tid
    labels[0, len(gold_ids)] = close_id

    # Uniform logits: zeros everywhere -> softmax = 1/V at every token.
    logits = torch.zeros((1, T_len, V))
    total_spans = [(0, len(gold_ids))]
    loss = aad_structural_loss(
        logits, labels, [items], [tau], total_spans, digit_token_ids,
        close_total_token_id=close_id,
    )
    upper = math.log(V)
    assert 0.0 < loss.item() <= upper + 1e-4, (
        f"uniform loss should lie in (0, log(V)={upper:.3f}], "
        f"got {loss.item()}"
    )
    print(f"  uniform loss = {loss.item():.4f}  (in (0, {upper:.3f}])  OK")


def test_no_total_span_returns_zero():
    """Samples whose total_span is (-1,-1) contribute nothing."""
    import torch
    from ..training.aad_loss import aad_structural_loss

    digit_token_ids = {str(i): i for i in range(10)}
    digit_token_ids["."] = 10
    V = 13
    logits = torch.zeros((1, 4, V))
    labels = torch.full((1, 4), -100, dtype=torch.long)
    loss = aad_structural_loss(
        logits, labels, [[]], [0], [(-1, -1)], digit_token_ids,
        close_total_token_id=None,
    )
    assert loss.item() == 0.0, f"expected 0, got {loss.item()}"
    print(f"  no-span loss = 0.0  OK")


def test_concentrated_on_infeasible_gives_large_loss():
    """When all logit mass sits on an infeasible token, L_struct is large
    (in the limit, infinite). We just check it's bigger than uniform."""
    import torch
    from ..training.aad_loss import aad_structural_loss

    digit_token_ids = {str(i): i for i in range(10)}
    digit_token_ids["."] = 10
    close_id = 11
    V = 13

    items, tau = [350, 1200], 93
    gold_seq = ["1", "6", ".", "4", "3"]
    gold_ids = [digit_token_ids[c] for c in gold_seq]
    T_len = len(gold_ids) + 1 + 2
    labels = torch.full((1, T_len), -100, dtype=torch.long)
    for i, tid in enumerate(gold_ids):
        labels[0, i] = tid
    labels[0, len(gold_ids)] = close_id

    # Concentrate mass on token id '7' at every step — gold values 93,
    # 443, 1293, 1643 don't begin with 7 and don't have 7 in any continuation.
    logits = torch.full((1, T_len, V), -1e9)
    logits[0, :, 7] = 0.0
    total_spans = [(0, len(gold_ids))]
    loss = aad_structural_loss(
        logits, labels, [items], [tau], total_spans, digit_token_ids,
        close_total_token_id=close_id,
    )
    assert loss.item() > 100.0, (
        f"infeasible-mass loss should be very large, got {loss.item()}"
    )
    print(f"  infeasible-mass loss = {loss.item():.1f}  (large)  OK")


def main():
    if not _require_torch():
        print("torch not installed; skipping aad_loss tests.")
        return
    print("Running aad_loss tests:")
    test_no_total_span_returns_zero()
    test_oracle_logits_give_zero_loss()
    test_uniform_logits_match_log_vocab_minus_log_mask()
    test_concentrated_on_infeasible_gives_large_loss()
    print("All aad_loss tests passed.")


if __name__ == "__main__":
    main()
