"""Masked cross-entropy with reachability constraint T (AAD structural loss).

Adds an auxiliary loss term that penalizes the unconstrained next-token
distribution `p_t` for placing probability mass on tokens whose extension
is infeasible under T:

    L_struct(t) = -log(sum_{sigma in M_t} p_t(sigma))

When the model is "well-calibrated for AAD" (all mass on feasible tokens),
L_struct = 0. When the model leaks mass onto infeasible tokens, L_struct
> 0 and grows with the leakage. This makes lambda_struct in S7's grid an
actual loss coefficient rather than the previous label-smoothing
stand-in.

Total loss combined in the trainer as:
    L = L_CE + lambda_struct * mean_t(L_struct(t))

The mean is over positions inside the `<s_total>...</s_total>` span only;
the rest of the sequence (entity tags, other fields) is unconstrained.

Implementation notes:
  * Logits indexing follows HF convention: logits[:, t, :] predicts
    labels[:, t].
  * `total_span = (start, end)` are *inclusive* positions in labels:
    start = position of `<s_total>` + 1, the first digit prediction;
    end   = position of `</s_total>`, the closing tag prediction.
  * We rely on the gold-target tokenization being one-token-per-char for
    digit / decimal positions. Mixed-tokenization positions (e.g. if the
    BPE tokenizer collapsed "12" into a single subword) are detected and
    contribute 0 to L_struct with a warning.
  * `build_mask` is called once per position; the implementation in
    `core.aad_decoder` is pure-python at ~ms per call, which is
    acceptable when amortized over the (few) total-span positions.
"""
from __future__ import annotations
from typing import Dict, List, Optional, Sequence, Set, Tuple
import warnings

import torch
import torch.nn.functional as F

from ..core.aad_decoder import build_mask, EOS as AAD_EOS, DEFAULT_VOCAB
from ..core.subset_sum import reachable_targets


def aad_structural_loss(
    logits: torch.Tensor,
    labels: torch.Tensor,
    items_cents: Sequence[Sequence[int]],
    tau_cents: Sequence[int],
    total_spans: Sequence[Tuple[int, int]],
    digit_token_ids: Dict[str, int],
    close_total_token_id: Optional[int] = None,
) -> torch.Tensor:
    """Per-batch L_struct averaged over total-span positions.

    Args:
        logits:          [B, T, V] decoder logits
        labels:          [B, T]    target token ids (with -100 for padding)
        items_cents:     length-B list of per-receipt item-cent lists
        tau_cents:       length-B list of per-receipt tau cents
        total_spans:     length-B list of (start, end) inclusive positions
                         in labels marking the `<s_total>` digit span.
                         A span of (-1, -1) means "no total in this sample"
                         and contributes 0 to the loss.
        digit_token_ids: e.g. {"0": id, ..., "9": id, ".": id}
        close_total_token_id: optional id of `</s_total>` to treat as
                         AAD's EOS at the final position of the span.

    Returns: scalar tensor (mean over all contributing positions).
    """
    if logits.dim() != 3:
        raise ValueError(f"expected logits [B,T,V], got {tuple(logits.shape)}")
    B, T, _ = logits.shape
    log_probs = F.log_softmax(logits, dim=-1)

    # Inverse map: token_id -> char (for prefix reconstruction).
    id_to_char = {tid: ch for ch, tid in digit_token_ids.items()}

    contributions: List[torch.Tensor] = []

    for b in range(B):
        items = list(items_cents[b]) if items_cents[b] is not None else []
        tau = int(tau_cents[b]) if tau_cents[b] is not None else 0
        start, end = total_spans[b]
        if start < 0 or end < start or not items:
            continue
        T_reach: Set[int] = reachable_targets(items, tau, k_min=1 if tau != 0 else 2)
        if not T_reach:
            continue

        prefix_chars: List[str] = []
        for t in range(start, end + 1):
            if t >= T:
                break
            label_tid = int(labels[b, t].item()) if labels[b, t] >= 0 else -100

            # Decide which token IDs the AAD mask covers at this step.
            mask_chars = build_mask("".join(prefix_chars), T_reach)
            mask_ids: List[int] = []
            for ch in mask_chars:
                if ch == AAD_EOS:
                    if close_total_token_id is not None:
                        mask_ids.append(close_total_token_id)
                else:
                    tid = digit_token_ids.get(ch)
                    if tid is not None:
                        mask_ids.append(tid)
            mask_ids = sorted(set(mask_ids))
            if not mask_ids:
                # No feasible tokens — skip rather than contribute -inf.
                break

            mask_id_t = torch.tensor(mask_ids, device=logits.device, dtype=torch.long)
            log_mass = torch.logsumexp(log_probs[b, t, mask_id_t], dim=0)
            # L_struct(t) = -log_mass. Want loss to grow when mass small.
            contributions.append(-log_mass)

            # Update prefix using the GOLD label (teacher forcing).
            if label_tid in id_to_char and id_to_char[label_tid] != AAD_EOS:
                prefix_chars.append(id_to_char[label_tid])
            elif label_tid == close_total_token_id:
                break  # gold says end of total reached
            else:
                # Multi-token char (BPE collapsed) — bail out cleanly.
                warnings.warn(
                    f"aad_structural_loss: position {t} in batch element "
                    f"{b} has label token {label_tid} not in digit vocab; "
                    f"truncating L_struct accumulation for this sample.",
                    RuntimeWarning,
                )
                break

    if not contributions:
        return logits.new_tensor(0.0)
    return torch.stack(contributions).mean()


def build_digit_token_ids(tokenizer) -> Tuple[Dict[str, int], Optional[int]]:
    """Resolve a tokenizer's IDs for "0".."9", ".", and `</s_total>`.

    Returns (digit_token_ids, close_total_token_id). Raises ValueError
    if any of the digit characters tokenize to anything other than a
    single token (which would prevent per-character supervision).
    """
    digit_token_ids: Dict[str, int] = {}
    for ch in list("0123456789") + ["."]:
        ids = tokenizer(ch, add_special_tokens=False).input_ids
        if len(ids) != 1:
            raise ValueError(
                f"tokenizer maps {ch!r} to {len(ids)} tokens ({ids}); "
                f"aad_structural_loss requires one-token-per-char digits."
            )
        digit_token_ids[ch] = ids[0]
    close_id = tokenizer.convert_tokens_to_ids("</s_total>")
    if close_id == tokenizer.unk_token_id:
        close_id = None
    return digit_token_ids, close_id


def find_total_span(labels_row: torch.Tensor,
                    open_total_id: int,
                    close_total_id: int) -> Tuple[int, int]:
    """Locate the `<s_total>` digit span in a labels row.

    Returns (start, end) inclusive: start = position after `<s_total>`,
    end = position of `</s_total>` (so the mask is applied at every step
    that predicts a digit, dot, or the closing tag).

    Returns (-1, -1) if either tag is missing.
    """
    seq = labels_row.tolist() if hasattr(labels_row, "tolist") else list(labels_row)
    try:
        i = seq.index(open_total_id)
        j = seq.index(close_total_id, i + 1)
    except ValueError:
        return (-1, -1)
    return (i + 1, j)
