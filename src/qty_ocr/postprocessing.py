"""Stages 10-11 — numeric validation, candidate selection and review flags.

Rules:

* Quantities stay strings (leading zeros kept); ``value_int`` is derived separately.
* No look-alike substitution (``O``→``0``, ``I``→``1`` ...). Such output is invalid.
* Only Unicode NFKC normalisation and whitespace removal are applied; removing
  inner whitespace (``"4 8"``) adds a review reason instead of passing silently.

Decision policy (evidence: docs/BENCHMARK.md, 20 forms / 120 handwritten fields):

* Text used for decisions is the **digit-constrained** decoding of the model
  output (``digit_decoder``); the unconstrained ``raw_text`` is kept for audit.
* ``primary_variant`` (``tight_crop``) supplies the value when valid.
* ``digit_segments`` (each ink group recognised separately and concatenated)
  is an independent second reading:
  - agree → strong evidence (109/110 agreeing fields were correct in-sample);
  - disagree → always ``needs_review``; suggested value: if lengths differ, the
    reading whose length equals the number of ink groups; if lengths match,
    per-position digit with the higher character score.
* Other enabled variants are cross-checks: a different valid reading with
  score ≥ ``contradiction_min_score`` → ``variant_disagreement``.
* ``letters_mapped_to_digits`` when the model actually emitted non-digits that
  were mapped (e.g. ``BZ``→``32``) — a guess, so always reviewed.
* ``low_confidence`` when the chosen score < review threshold;
  ``ink_groups_exceed_digits`` when more separate ink clusters than digits.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from .schemas import BlankLabel, FieldStatus, OCRCandidate

_WS = re.compile(r"\s+")


def normalize_text(raw: str | None) -> tuple[str | None, list[str]]:
    """Return ``(normalized_text, notes)``. Never drops non-whitespace characters."""
    if raw is None:
        return None, []
    notes: list[str] = []
    text = unicodedata.normalize("NFKC", raw).strip()
    if _WS.search(text):
        text = _WS.sub("", text)
        notes.append("inner_whitespace_removed")
    return text, notes


def is_valid_quantity(text: str | None, min_digits: int, max_digits: int) -> bool:
    if not text:
        return False
    return bool(re.fullmatch(rf"[0-9]{{{min_digits},{max_digits}}}", text))


def invalid_reason(text: str | None, min_digits: int, max_digits: int) -> str | None:
    """Why ``text`` is not a valid quantity (``None`` when valid)."""
    if text is None or text == "":
        return "empty_prediction"
    if not re.fullmatch(r"[0-9]+", text):
        return "non_numeric_characters"
    if len(text) > max_digits:
        return "too_many_digits"
    if len(text) < min_digits:
        return "too_few_digits"
    return None


@dataclass
class Decision:
    status: FieldStatus
    raw_text: str | None
    normalized_text: str | None
    value: str | None
    value_int: int | None
    confidence: float | None
    variant: str | None
    review_reasons: list[str] = field(default_factory=list)

    @property
    def needs_review(self) -> bool:
        return self.status not in (FieldStatus.OK, FieldStatus.BLANK)


def decide(
    candidates: list[OCRCandidate],
    *,
    min_digits: int,
    max_digits: int,
    review_threshold: float,
    primary_variant: str = "tight_crop",
    segment_variant: str = "digit_segments",
    contradiction_min_score: float = 0.85,
    missing_digit_max_penalty: float = 0.03,
    missing_digit_max_penalty_with_ink_groups: float = 0.06,
    blank_label: BlankLabel = BlankLabel.NONBLANK,
    ink_groups: int | None = None,
    extra_reasons: list[str] | None = None,
) -> Decision:
    """Choose the field value from recognition candidates using the documented policy."""
    reasons: list[str] = list(extra_reasons or [])
    if blank_label == BlankLabel.UNCERTAIN:
        reasons.append("blank_detection_uncertain")

    ok = [c for c in candidates if c.error is None]
    if not ok:
        errors = sorted({c.error or "no_candidates" for c in candidates}) or ["no_candidates"]
        return Decision(
            FieldStatus.RECOGNITION_ERROR, None, None, None, None, None, None,
            reasons + [f"recognition_error: {e}" for e in errors],
        )

    primary = next((c for c in ok if c.variant == primary_variant), None)
    segments = next((c for c in ok if c.variant == segment_variant), None)
    valid = [c for c in ok if c.is_valid_numeric]
    score = candidate_score

    value: str | None = None
    chosen: OCRCandidate | None = None
    if primary is not None and primary.is_valid_numeric:
        chosen, value = primary, primary.normalized_text
    elif valid:
        chosen = max(valid, key=lambda c: score(c) or 0.0)
        value = chosen.normalized_text
        shown = repr(primary.normalized_text) if primary is not None else "missing"
        reasons.append(f"primary_variant_invalid({primary_variant}={shown})")
    else:
        ref = primary or ok[0]
        if all(not c.normalized_text for c in ok):
            why = ["empty_prediction_on_nonblank"]
        else:
            why = sorted({invalid_reason(c.normalized_text, min_digits, max_digits) or "invalid" for c in ok})
        return Decision(
            FieldStatus.INVALID_TEXT, ref.raw_text, ref.normalized_text, None, None,
            score(ref), ref.variant, reasons + why,
        )

    # Touching digits merged by CTC (e.g. "79" read as "7"): adopt the n+1-digit
    # re-decoding when it is almost as likely as the n-digit one.
    recovered = False
    if chosen.longer_text and chosen.longer_penalty is not None:
        limit = missing_digit_max_penalty
        if ink_groups is not None and ink_groups > len(value or ""):
            limit = max(limit, missing_digit_max_penalty_with_ink_groups)
        if chosen.longer_penalty <= limit and is_valid_quantity(chosen.longer_text, min_digits, max_digits):
            reasons.append(
                f"possible_merged_digits({value}->{chosen.longer_text}, penalty={chosen.longer_penalty:.3f})"
            )
            value, recovered = chosen.longer_text, True

    # Second, independent reading: per-digit segments.
    if (
        segments is not None
        and segments is not chosen
        and segments.is_valid_numeric
        and segments.normalized_text != value
    ):
        reasons.append(f"tight_vs_segments_disagree({value} vs {segments.normalized_text})")
        lc, ls = len(value or ""), len(segments.normalized_text or "")
        if not recovered and lc != ls and ink_groups is not None and ls == ink_groups and lc != ink_groups:
            chosen, value = segments, segments.normalized_text

    contradictions = sorted(
        {
            f"{c.variant}={c.normalized_text}@{(score(c) or 0):.2f}"
            for c in valid
            if c is not chosen
            and c.variant != segment_variant
            and c.normalized_text != value
            and (score(c) or 0.0) >= contradiction_min_score
        }
    )
    if contradictions:
        reasons.append(f"variant_disagreement({', '.join(contradictions)})")
    if chosen.digit_substituted:
        reasons.append(f"letters_mapped_to_digits({chosen.raw_text!r}->{chosen.normalized_text})")
    conf = score(chosen)
    if conf is None or conf < review_threshold:
        reasons.append(f"low_confidence({(conf or 0):.3f}<{review_threshold})")
    value = value or ""
    if not is_valid_quantity(value, min_digits, max_digits):
        return Decision(
            FieldStatus.INVALID_TEXT, chosen.raw_text, value, None, None, conf, chosen.variant,
            reasons + [invalid_reason(value, min_digits, max_digits) or "invalid"],
        )
    if ink_groups is not None and ink_groups > len(value):
        reasons.append(f"ink_groups_exceed_digits({ink_groups}>{len(value)})")
    if chosen.digit_text is None:
        reasons.extend(n for n in _notes_for(chosen.raw_text) if n not in reasons)

    return Decision(
        FieldStatus.NEEDS_REVIEW if reasons else FieldStatus.OK,
        chosen.raw_text,
        value,
        value,
        int(value),
        conf,
        chosen.variant,
        reasons,
    )


def _notes_for(raw: str | None) -> list[str]:
    return normalize_text(raw)[1]


def make_candidate(
    variant: str,
    raw_text: str | None,
    rec_score: float | None,
    inference_time_ms: float,
    model_name: str,
    *,
    min_digits: int,
    max_digits: int,
    error: str | None = None,
    digit_text: str | None = None,
    digit_score: float | None = None,
    digit_char_scores: list[float] | None = None,
    digit_substituted: int = 0,
    n_images: int = 1,
) -> OCRCandidate:
    """Build a candidate. With digit decoding, ``normalized_text`` is the digit-constrained text
    (the one used for decisions) while ``raw_text``/``rec_score`` keep the unconstrained output."""
    if digit_text is not None:
        normalized = digit_text
    else:
        normalized, _ = normalize_text(raw_text)
    return OCRCandidate(
        variant=variant,
        raw_text=raw_text,
        rec_score=None if rec_score is None else round(float(rec_score), 6),
        normalized_text=normalized,
        is_valid_numeric=error is None and is_valid_quantity(normalized, min_digits, max_digits),
        inference_time_ms=round(inference_time_ms, 2),
        model_name=model_name,
        error=error,
        digit_text=digit_text,
        digit_score=None if digit_score is None else round(float(digit_score), 6),
        digit_char_scores=list(digit_char_scores or []),
        digit_substituted=digit_substituted,
        n_images=n_images,
    )


def candidate_score(c: OCRCandidate) -> float | None:
    """Score that belongs to ``normalized_text`` (digit score when digit decoding was used)."""
    return c.digit_score if c.digit_text is not None else c.rec_score
