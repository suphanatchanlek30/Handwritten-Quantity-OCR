from __future__ import annotations

import numpy as np
import pytest

from qty_ocr.digit_decoder import DigitAlphabet, decode_digits, decode_fixed_length, digit_distribution, extra_digit_penalty

# toy dictionary: blank, space, letters, ASCII digits, full-width 8
CHARS = ["blank", " ", "B", "Z", "I", "S"] + list("0123456789") + ["８"]
IDX = {c: i for i, c in enumerate(CHARS)}
ALPHA = DigitAlphabet.from_character_list(CHARS)


def frames(*specs):
    """Each spec: dict char->prob for one time step (rest of mass spread to blank)."""
    out = np.zeros((len(specs), len(CHARS)), np.float32)
    for t, spec in enumerate(specs):
        for c, p in spec.items():
            out[t, IDX[c]] = p
        out[t, 0] += max(0.0, 1.0 - out[t].sum())
    return out


def test_plain_digits_unchanged():
    d = decode_digits(frames({"3": 0.95}, {"blank": 1.0}, {"2": 0.9}), ALPHA)
    assert d.text == "32" and d.substituted == 0 and d.score > 0.9


def test_letters_mapped_to_most_likely_digit_with_low_score():
    # model says "B" then "Z", but 8 / 2 hold the most digit mass in those frames
    d = decode_digits(frames({"B": 0.8, "8": 0.1, "3": 0.05}, {"blank": 1.0}, {"Z": 0.7, "2": 0.2}), ALPHA)
    assert d.text == "82" and d.substituted == 2
    assert d.score < 0.5  # substitution is visible as low confidence


def test_fullwidth_mass_counts_for_digit():
    d = decode_digits(frames({"I": 0.5, "8": 0.2, "８": 0.25, "3": 0.3}), ALPHA)
    assert d.text == "8"  # 0.45 for 8 beats 0.3 for 3


def test_repeated_frames_collapse_and_blank_separates():
    d = decode_digits(frames({"1": 0.9}, {"1": 0.9}, {"blank": 1.0}, {"1": 0.9}), ALPHA)
    assert d.text == "11"


def test_space_acts_as_separator_not_digit():
    d = decode_digits(frames({"4": 0.9}, {" ": 0.9}, {"8": 0.9}), ALPHA)
    assert d.text == "48"


def test_all_blank_gives_empty():
    d = decode_digits(frames({"blank": 1.0}, {"blank": 1.0}), ALPHA)
    assert d.text == "" and d.score is None


def test_alphabet_requires_blank_first_and_digits():
    with pytest.raises(ValueError):
        DigitAlphabet.from_character_list(["a", "blank"] + list("0123456789"))
    with pytest.raises(ValueError):
        DigitAlphabet.from_character_list(["blank", "a", "b"])


def test_digit_distribution_rows_sum_to_one():
    q = digit_distribution(frames({"B": 0.6, "8": 0.2}, {" ": 0.9}, {"3": 0.9}), ALPHA)
    assert q.shape == (3, 11) and np.allclose(q.sum(axis=1), 1.0)
    assert q[1, 0] > 0.99  # whitespace counts as blank


def test_fixed_length_recovers_merged_digit():
    # "7" strong, then a weak "9" that loses to blank in greedy decoding
    p = frames({"7": 0.9}, {"7": 0.8}, {"9": 0.35}, {"9": 0.3}, {"blank": 1.0})
    greedy = decode_digits(p, ALPHA).text
    q = digit_distribution(p, ALPHA)
    text2, _ = decode_fixed_length(q, 2)
    longer, penalty = extra_digit_penalty(q, len(greedy))
    assert greedy == "7" and text2 == "79" and longer == "79" and penalty < 0.5


def test_fixed_length_penalty_large_for_true_single_digit():
    p = frames({"blank": 1.0}, {"7": 0.99}, {"7": 0.99}, {"blank": 1.0})
    _, penalty = extra_digit_penalty(digit_distribution(p, ALPHA), 1)
    assert penalty > 1.0


def test_fixed_length_impossible():
    assert decode_fixed_length(np.full((2, 11), 1 / 11), 3) == ("", float("-inf"))
