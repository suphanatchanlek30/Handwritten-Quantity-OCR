"""Digit-constrained CTC decoding of PP-OCRv5 output probabilities.

The pretrained recogniser chooses among ~18k characters, so handwritten digits
are often emitted as look-alike letters (``32``→``BZ``, ``64``→``GA``,
``95``→``IS``). Here the model's own per-frame probabilities are re-decoded
with the output alphabet restricted to ``0-9``:

1. Standard CTC segmentation on the *unconstrained* argmax: consecutive frames
   with the same non-blank id form one character; blank and whitespace frames
   separate characters. This keeps the character count the model saw.
2. Each character segment is re-labelled with the digit whose probability mass
   (ASCII + full-width forms) summed over the segment's frames is highest.
3. Per-character confidence = mean over its frames of
   ``P(digit) / (1 - P(blank))`` — the share of the non-blank mass that the
   digit holds. A frame that was confidently "B" gives a *low* score for "8",
   so substituted characters are visible as low confidence, never hidden.

No new model, no extra inference: it reuses the probabilities already computed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

DIGITS = "0123456789"
FULLWIDTH = "０１２３４５６７８９"


@dataclass
class DigitDecoding:
    text: str
    score: float | None          # mean per-character digit share; None when text is empty
    char_scores: list[float] = field(default_factory=list)
    substituted: int = 0         # characters whose unconstrained argmax was not a digit


@dataclass(frozen=True)
class DigitAlphabet:
    blank_index: int
    separator_indices: tuple[int, ...]        # whitespace treated like blank
    digit_columns: tuple[tuple[int, ...], ...]  # per digit 0..9: dictionary indices

    @classmethod
    def from_character_list(cls, characters: list[str]) -> "DigitAlphabet":
        if not characters or characters[0] != "blank":
            raise ValueError("CTC character list must start with 'blank'")
        index = {c: i for i, c in enumerate(characters)}
        cols = []
        for d, fw in zip(DIGITS, FULLWIDTH):
            ids = tuple(index[c] for c in (d, fw) if c in index)
            if not ids:
                raise ValueError(f"digit {d!r} missing from recogniser dictionary")
            cols.append(ids)
        seps = tuple(i for i, c in enumerate(characters) if i > 0 and c.isspace())
        return cls(blank_index=0, separator_indices=seps, digit_columns=tuple(cols))

    @property
    def digit_index_set(self) -> frozenset[int]:
        return frozenset(i for ids in self.digit_columns for i in ids)


def decode_digits(probs: np.ndarray, alphabet: DigitAlphabet) -> DigitDecoding:
    """Decode one image's ``(T, C)`` softmax output to a digit string."""
    probs = np.asarray(probs, dtype=np.float32)
    if probs.ndim != 2:
        raise ValueError(f"expected (T, C) probabilities, got shape {probs.shape}")
    ids = probs.argmax(axis=1)
    skip = {alphabet.blank_index, *alphabet.separator_indices}

    segments: list[list[int]] = []
    prev = -1
    for t, i in enumerate(ids):
        i = int(i)
        if i in skip:
            prev = i
            continue
        if i == prev and segments:
            segments[-1].append(t)
        else:
            segments.append([t])
        prev = i

    digit_mass = np.stack([probs[:, list(c)].sum(axis=1) for c in alphabet.digit_columns], axis=1)
    nonblank = np.clip(1.0 - probs[:, alphabet.blank_index], 1e-6, None)
    digit_ids = alphabet.digit_index_set

    text, scores, substituted = [], [], 0
    for seg in segments:
        mass = digit_mass[seg]                 # (len, 10)
        d = int(mass.sum(axis=0).argmax())
        share = np.clip(mass[:, d] / nonblank[seg], 0.0, 1.0)
        text.append(DIGITS[d])
        scores.append(float(share.mean()))
        substituted += int(ids[seg[0]]) not in digit_ids
    return DigitDecoding(
        text="".join(text),
        score=float(np.mean(scores)) if scores else None,
        char_scores=[round(s, 4) for s in scores],
        substituted=substituted,
    )


def digit_distribution(probs: np.ndarray, alphabet: DigitAlphabet) -> np.ndarray:
    """Per-frame ``(T, 11)`` distribution over ``[blank, 0..9]``.

    Non-blank mass (including mass the model put on letters) is shared among
    the ten digits in proportion to their own probabilities.
    """
    probs = np.asarray(probs, dtype=np.float64)
    blank = probs[:, alphabet.blank_index]
    for i in alphabet.separator_indices:  # whitespace behaves like blank
        blank = blank + probs[:, i]
    blank = np.clip(blank, 0.0, 1.0)
    d = np.stack([probs[:, list(c)].sum(axis=1) for c in alphabet.digit_columns], axis=1)
    share = d / np.clip(d.sum(axis=1, keepdims=True), 1e-12, None)
    return np.concatenate([blank[:, None], (1.0 - blank)[:, None] * share], axis=1)


def decode_fixed_lengths(q: np.ndarray, k_max: int) -> dict[int, tuple[str, float]]:
    """Best CTC path over ``[blank, 0..9]`` for every exact length ``1..k_max`` in one pass.

    Returns ``{k: (text, mean log-probability per frame)}``. Viterbi over states
    ``(digits emitted, last token)``; a state with ``n`` digits only depends on
    states with ``<= n`` digits, so row ``n`` of a ``k_max`` table is exactly
    what a separate run with ``k = n`` computes. O(T·k·11) numpy work.
    """
    T = q.shape[0]
    out: dict[int, tuple[str, float]] = {k: ("", float("-inf")) for k in range(1, max(1, k_max) + 1)}
    if k_max < 1 or T < 1:
        return out
    k = k_max
    L = np.log(np.clip(q, 1e-12, None))
    NEG = -1e18
    dp = np.full((k + 1, 11), NEG)
    dp[0, 0] = 0.0
    back_n = np.zeros((T, k + 1, 11), dtype=np.int8)
    back_l = np.zeros((T, k + 1, 11), dtype=np.int8)
    digits = np.arange(1, 11)
    rows = np.arange(k + 1)
    for t in range(T):
        nd = np.full((k + 1, 11), NEG)
        bn = np.zeros((k + 1, 11), dtype=np.int8)
        bl = np.zeros((k + 1, 11), dtype=np.int8)
        # to blank: keep n, from any last token
        best_last = dp.argmax(axis=1)
        nd[:, 0] = dp[rows, best_last] + L[t, 0]
        bn[:, 0] = rows
        bl[:, 0] = best_last
        # to digit j, staying on the same label (no new digit)
        nd[:, digits] = dp[:, digits] + L[t, digits]
        bn[:, digits] = rows[:, None]
        bl[:, digits] = digits[None, :]
        # to digit j as a new label: from row n-1, any last token != j
        for n in range(1, k + 1):
            prev = dp[n - 1]
            order = np.argsort(prev)[::-1]
            top1, top2 = order[0], order[1]
            src = np.where(digits == top1, top2, top1)
            cand = prev[src] + L[t, digits]
            better = cand > nd[n, digits]
            nd[n, digits] = np.where(better, cand, nd[n, digits])
            bn[n, digits] = np.where(better, n - 1, bn[n, digits])
            bl[n, digits] = np.where(better, src, bl[n, digits])
        dp = nd
        back_n[t], back_l[t] = bn, bl
    for kk in range(1, k + 1):
        if T < kk:
            continue
        last = int(dp[kk].argmax())
        total = float(dp[kk, last])
        if total <= NEG / 2:
            continue
        n, seq = kk, []
        for t in range(T - 1, -1, -1):
            seq.append(last)
            n, last = int(back_n[t, n, last]), int(back_l[t, n, last])
        seq.reverse()
        text, prev_tok = [], 0
        for tok in seq:
            if tok != 0 and tok != prev_tok:
                text.append(DIGITS[tok - 1])
            prev_tok = tok
        out[kk] = ("".join(text), total / T)
    return out


def decode_fixed_length(q: np.ndarray, k: int) -> tuple[str, float]:
    """Best CTC path that collapses to exactly ``k`` digits: ``(text, mean log-prob per frame)``."""
    if k < 1 or q.shape[0] < k:
        return "", float("-inf")
    return decode_fixed_lengths(q, k)[k]


def extra_digit_penalty(q: np.ndarray, n: int) -> tuple[str, float]:
    """How much worse (mean log-prob per frame) the best ``n+1``-digit reading is than the best ``n``-digit one.

    Small values mean the model "almost" saw another digit — typical for
    touching digits that CTC merged (e.g. ``79`` read as ``7``).
    """
    n = max(1, n)
    res = decode_fixed_lengths(q, n + 1)  # one Viterbi pass gives both lengths
    _, s_n = res[n]
    text, s_n1 = res[n + 1]
    return text, float(s_n - s_n1)
