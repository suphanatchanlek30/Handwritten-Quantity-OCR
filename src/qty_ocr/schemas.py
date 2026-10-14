"""Data structures shared across pipeline stages.

Bounding-box convention everywhere: ``[x_min, y_min, x_max, y_max]`` in integer
pixels, ``x_max``/``y_max`` exclusive (numpy slicing ``img[y_min:y_max, x_min:x_max]``).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

BBox = tuple[int, int, int, int]


class FieldStatus(str, Enum):
    OK = "ok"
    BLANK = "blank"
    NEEDS_REVIEW = "needs_review"
    INVALID_TEXT = "invalid_text"
    FIELD_NOT_FOUND = "field_not_found"
    RECOGNITION_ERROR = "recognition_error"
    ALIGNMENT_FAILED = "alignment_failed"


class BlankLabel(str, Enum):
    BLANK = "blank"
    NONBLANK = "nonblank"
    UNCERTAIN = "uncertain"


def validate_bbox(bbox: BBox, width: int, height: int) -> None:
    """Raise ``ValueError`` unless ``bbox`` is a non-empty box inside ``width x height``."""
    x0, y0, x1, y1 = bbox
    if not all(isinstance(v, int) for v in bbox):
        raise ValueError(f"bbox must contain ints: {bbox}")
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        raise ValueError(f"bbox {bbox} not inside image {width}x{height}")


def clip_bbox(bbox: BBox, width: int, height: int) -> BBox:
    x0, y0, x1, y1 = bbox
    return (max(0, x0), max(0, y0), min(width, x1), min(height, y1))


@dataclass
class OCRCandidate:
    """One recognition attempt on one preprocessing variant."""

    variant: str
    raw_text: str | None
    rec_score: float | None
    normalized_text: str | None
    is_valid_numeric: bool
    inference_time_ms: float
    model_name: str
    error: str | None = None
    # digit-constrained decoding of the same model output (normalized_text uses it when present)
    digit_text: str | None = None
    digit_score: float | None = None
    digit_char_scores: list[float] = field(default_factory=list)
    digit_substituted: int = 0
    n_images: int = 1             # >1 for digit_segments (one inference per segment)
    # best reading with one more digit, and how much less likely it is (mean log-prob per frame)
    longer_text: str | None = None
    longer_penalty: float | None = None


@dataclass
class BlankStats:
    label: BlankLabel
    ink_pixels: int
    ink_ratio: float
    n_components: int
    max_component_height: int
    ink_groups: int        # horizontally separated ink clusters (≈ digit count lower bound)
    ink_bbox: BBox | None  # relative to the crop

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["label"] = self.label.value
        return d


@dataclass
class FieldResult:
    row_id: int
    field_type: str
    bbox_aligned: BBox | None
    bbox_original: BBox | None
    is_blank: bool | None
    raw_text: str | None
    normalized_text: str | None
    value: str | None
    value_int: int | None
    confidence: float | None
    status: FieldStatus
    needs_review: bool
    review_reasons: list[str] = field(default_factory=list)
    preprocessing_variant: str | None = None
    crop_path: str | None = None
    blank_stats: BlankStats | None = None
    candidates: list[OCRCandidate] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "row_id": self.row_id,
            "field_type": self.field_type,
            "bbox_aligned": list(self.bbox_aligned) if self.bbox_aligned else None,
            "bbox_original": list(self.bbox_original) if self.bbox_original else None,
            "is_blank": self.is_blank,
            "raw_text": self.raw_text,
            "normalized_text": self.normalized_text,
            "value": self.value,
            "value_int": self.value_int,
            "confidence": self.confidence,
            "status": self.status.value,
            "needs_review": self.needs_review,
            "review_reasons": list(self.review_reasons),
            "preprocessing_variant": self.preprocessing_variant,
            "crop_path": self.crop_path,
            "blank_stats": self.blank_stats.to_dict() if self.blank_stats else None,
            "candidates": [asdict(c) for c in self.candidates],
        }


@dataclass
class DocumentResult:
    document_id: str
    template_id: str
    model: str | None
    status: str
    image_width: int
    image_height: int
    source_path: str
    fields: list[FieldResult] = field(default_factory=list)
    alignment: dict[str, Any] = field(default_factory=dict)
    timings_ms: dict[str, float] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "template_id": self.template_id,
            "model": self.model,
            "status": self.status,
            "image_width": self.image_width,
            "image_height": self.image_height,
            "source_path": self.source_path,
            "alignment": self.alignment,
            "timings_ms": {k: round(v, 2) for k, v in self.timings_ms.items()},
            "errors": list(self.errors),
            "fields": [f.to_dict() for f in self.fields],
        }
