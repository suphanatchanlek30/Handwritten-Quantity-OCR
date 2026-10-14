"""Stage 8 — preprocessing variants for recognition.

Every variant is returned as a 3-channel **BGR** ``uint8`` image, the format
PaddleX expects for ndarray input (verified: BGR ndarray == file-path result).
No variant resizes the crop; PP-OCRv5 performs its own model-specific resize.
"""

from __future__ import annotations

import cv2
import numpy as np

from .config import PreprocessingConfig
from .schemas import BBox


def to_grayscale(crop_bgr: np.ndarray, clahe: bool = False) -> np.ndarray:
    gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
    if clahe:
        gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4)).apply(gray)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def red_weight(crop_bgr: np.ndarray, cfg: PreprocessingConfig) -> np.ndarray:
    """Soft red-ink strength in [0, 1] (keeps faint anti-aliased stroke edges)."""
    hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)
    hue, sat, val = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    in_hue = np.zeros(hue.shape, dtype=bool)
    for lo, hi in cfg.red_hue_ranges:
        in_hue |= (hue >= lo) & (hue <= hi)
    valid = in_hue & (sat >= cfg.red_min_saturation) & (val >= cfg.red_min_value)
    return np.where(valid, sat.astype(np.float32) / 255.0, 0.0).astype(np.float32)


def _weight_to_bgr(weight: np.ndarray) -> np.ndarray | None:
    """Render ink strength (0..1) as dark strokes on white, normalised to the strongest ink."""
    peak = float(weight.max())
    if peak <= 0:
        return None
    out = (255.0 * (1.0 - np.clip(weight / peak, 0.0, 1.0))).astype(np.uint8)
    return cv2.cvtColor(out, cv2.COLOR_GRAY2BGR)


def red_ink_isolation(crop_bgr: np.ndarray, cfg: PreprocessingConfig) -> np.ndarray | None:
    """Red strokes only, dark on white. ``None`` when the crop has no red ink."""
    w = red_weight(crop_bgr, cfg)
    if int((w > 0).sum()) < 10:
        return None
    return _weight_to_bgr(w)


def ink_weight(crop_bgr: np.ndarray) -> np.ndarray:
    """Colour-agnostic ink strength: max of saturation and darkness, in [0, 1]."""
    hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
    sat = hsv[:, :, 1].astype(np.float32) / 255.0
    dark = (255.0 - gray.astype(np.float32)) / 255.0
    w = np.maximum(sat, dark)
    return np.where(w >= 0.08, w, 0.0).astype(np.float32)  # drop JPEG background noise


def ink_isolation(crop_bgr: np.ndarray) -> np.ndarray | None:
    """Any-colour handwriting (red, blue, black) as dark strokes on white."""
    return _weight_to_bgr(ink_weight(crop_bgr))


def adaptive_binarize(crop_bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)


def tight_crop(crop_bgr: np.ndarray, ink_bbox: BBox | None, padding_ratio: float) -> np.ndarray | None:
    """Crop around the detected ink with proportional white padding (no resizing)."""
    if ink_bbox is None:
        return None
    x0, y0, x1, y1 = ink_bbox
    pad = max(8, int(round(padding_ratio * (y1 - y0))))
    region = crop_bgr[y0:y1, x0:x1]
    return cv2.copyMakeBorder(region, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=(255, 255, 255))


def build_variants(
    crop_bgr: np.ndarray, cfg: PreprocessingConfig, ink_bbox: BBox | None = None
) -> dict[str, np.ndarray]:
    """Return enabled variants in evaluation order (``original`` first)."""
    variants: dict[str, np.ndarray] = {}
    for name in cfg.enabled_variants():
        if name == "original":
            variants[name] = crop_bgr
        elif name == "grayscale":
            variants[name] = to_grayscale(crop_bgr, cfg.clahe)
        elif name == "red_mask":
            img = red_ink_isolation(crop_bgr, cfg)
            if img is not None:
                variants[name] = img
        elif name == "ink_isolation":
            img = ink_isolation(crop_bgr)
            if img is not None:
                variants[name] = img
        elif name == "adaptive_threshold":
            variants[name] = adaptive_binarize(crop_bgr)
        elif name == "tight_crop":
            img = tight_crop(crop_bgr, ink_bbox, cfg.tight_crop_padding_ratio)
            if img is not None:
                variants[name] = img
    return variants


def digit_segments(
    crop_bgr: np.ndarray, group_masks: list[np.ndarray], padding_ratio: float
) -> list[np.ndarray]:
    """One white-background image per ink group (left to right).

    Pixels outside the group's (slightly dilated) mask are painted white so a
    neighbouring digit never leaks into the segment. No resizing.
    """
    out: list[np.ndarray] = []
    kernel = np.ones((5, 5), np.uint8)
    for gm in group_masks:
        ys, xs = np.nonzero(gm)
        if len(xs) == 0:
            continue
        keep = cv2.dilate(gm, kernel) > 0
        x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
        region = np.where(keep[..., None], crop_bgr, 255).astype(np.uint8)[y0:y1, x0:x1]
        pad = max(8, int(round(padding_ratio * (y1 - y0))))
        out.append(cv2.copyMakeBorder(region, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=(255, 255, 255)))
    return out
