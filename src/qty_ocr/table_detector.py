"""Stage 3 — printed table grid localisation.

The grid is extracted from a *printed-ink* mask only (dark **and** low
saturation). Coloured handwriting — e.g. a thin red "1" that looks like a
vertical rule — is therefore never mistaken for a table line.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np

from .config import AlignmentConfig, TemplateConfig


@dataclass
class GridMasks:
    printed: np.ndarray      # dark & low-saturation pixels (uint8 0/255)
    horizontal: np.ndarray   # long horizontal strokes
    vertical: np.ndarray     # long vertical strokes


@dataclass
class TableGrid:
    """Grid lines on the aligned (template) coordinate system."""

    vertical_lines: list[int]
    horizontal_lines: list[int]
    detected_vertical: list[int]
    detected_horizontal: list[int]
    missing_vertical: list[int] = field(default_factory=list)
    missing_horizontal: list[int] = field(default_factory=list)
    match_ratio: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "vertical_lines": self.vertical_lines,
            "horizontal_lines": self.horizontal_lines,
            "detected_vertical": self.detected_vertical,
            "detected_horizontal": self.detected_horizontal,
            "missing_vertical": self.missing_vertical,
            "missing_horizontal": self.missing_horizontal,
            "match_ratio": round(self.match_ratio, 4),
        }


class TableNotFoundError(RuntimeError):
    """Raised when the table grid cannot be localised."""


def printed_ink_mask(bgr: np.ndarray, cfg: AlignmentConfig) -> np.ndarray:
    """Pixels that look like printed black/grey ink (not coloured handwriting)."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    sat = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)[:, :, 1]
    if cfg.grid_threshold == "adaptive":
        block = max(3, cfg.adaptive_block_px | 1)
        dark = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, block, cfg.adaptive_c
        ) > 0
    else:
        dark = gray <= cfg.grid_max_gray
    mask = dark & (sat <= cfg.grid_max_saturation)
    return mask.astype(np.uint8) * 255


def extract_grid_masks(bgr: np.ndarray, cfg: AlignmentConfig) -> GridMasks:
    """Morphologically isolate long horizontal and vertical printed strokes."""
    printed = printed_ink_mask(bgr, cfg)
    h, w = printed.shape
    h_len = max(15, int(w * cfg.horizontal_kernel_ratio))
    v_len = max(15, int(h * cfg.vertical_kernel_ratio))
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (h_len, 1))
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_len))
    t = max(1, cfg.line_thickening_px)
    # Close 1px gaps (anti-aliasing / JPEG) along the line, then thicken it
    # across its direction so a slightly slanted rule (residual perspective)
    # still contains the long opening kernel. Text has gaps along the line
    # direction, so thickening across it does not turn text into rules.
    closed_h = cv2.morphologyEx(printed, cv2.MORPH_CLOSE, np.ones((1, 3), np.uint8))
    closed_v = cv2.morphologyEx(printed, cv2.MORPH_CLOSE, np.ones((3, 1), np.uint8))
    closed_h = cv2.dilate(closed_h, np.ones((2 * t + 1, 1), np.uint8))
    closed_v = cv2.dilate(closed_v, np.ones((1, 2 * t + 1), np.uint8))
    horizontal = cv2.morphologyEx(closed_h, cv2.MORPH_OPEN, h_kernel)
    vertical = cv2.morphologyEx(closed_v, cv2.MORPH_OPEN, v_kernel)
    return GridMasks(printed=printed, horizontal=horizontal, vertical=vertical)


def line_positions(profile: np.ndarray, min_value: float) -> list[int]:
    """Centres of runs where a 1-D projection ``profile`` reaches ``min_value``."""
    above = profile >= min_value
    positions: list[int] = []
    start: int | None = None
    for i, flag in enumerate(above):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            positions.append(int(round((start + i - 1) / 2)))
            start = None
    if start is not None:
        positions.append(int(round((start + len(above) - 1) / 2)))
    return positions


def snap_lines(
    expected: list[int] | tuple[int, ...], detected: list[int], tolerance: int
) -> tuple[list[int], list[int]]:
    """Match each expected line to the nearest detected one within ``tolerance``.

    Returns ``(snapped, missing_expected)`` where unmatched lines keep their
    expected (template) position.
    """
    snapped: list[int] = []
    missing: list[int] = []
    for e in expected:
        if detected:
            nearest = min(detected, key=lambda d: abs(d - e))
            if abs(nearest - e) <= tolerance:
                snapped.append(nearest)
                continue
        snapped.append(int(e))
        missing.append(int(e))
    return snapped, missing


def detect_grid(
    aligned_bgr: np.ndarray,
    template: TemplateConfig,
    cfg: AlignmentConfig,
    masks: GridMasks | None = None,
) -> TableGrid:
    """Detect table lines on an image already aligned to ``template`` coordinates."""
    if masks is None:
        masks = extract_grid_masks(aligned_bgr, cfg)
    x0, y0, x1, y1 = template.table_box
    pad = cfg.line_snap_tolerance_px * 2
    h, w = masks.horizontal.shape
    ys, ye = max(0, y0 - pad), min(h, y1 + pad)
    xs, xe = max(0, x0 - pad), min(w, x1 + pad)

    # A table rule must span at least half of the table along its axis.
    h_profile = (masks.horizontal[ys:ye, x0:x1] > 0).sum(axis=1)
    v_profile = (masks.vertical[y0:y1, xs:xe] > 0).sum(axis=0)
    detected_h = [p + ys for p in line_positions(h_profile, 0.5 * (x1 - x0))]
    detected_v = [p + xs for p in line_positions(v_profile, 0.5 * (y1 - y0))]

    tol = cfg.line_snap_tolerance_px
    snapped_v, missing_v = snap_lines(template.vertical_lines, detected_v, tol)
    snapped_h, missing_h = snap_lines(template.horizontal_lines, detected_h, tol)
    total = len(template.vertical_lines) + len(template.horizontal_lines)
    matched = total - len(missing_v) - len(missing_h)
    return TableGrid(
        vertical_lines=snapped_v,
        horizontal_lines=snapped_h,
        detected_vertical=detected_v,
        detected_horizontal=detected_h,
        missing_vertical=missing_v,
        missing_horizontal=missing_h,
        match_ratio=matched / total,
    )


def find_table_quad(masks: GridMasks, min_area_ratio: float = 0.05) -> np.ndarray | None:
    """Return the outer table corners ``(tl, tr, br, bl)`` as float32 (4, 2), or None."""
    grid = cv2.bitwise_or(masks.horizontal, masks.vertical)
    grid = cv2.dilate(grid, np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(grid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    contour = max(contours, key=cv2.contourArea)
    img_area = grid.shape[0] * grid.shape[1]
    if cv2.contourArea(contour) < min_area_ratio * img_area:
        return None
    hull = cv2.convexHull(contour)
    peri = cv2.arcLength(hull, True)
    for eps in (0.01, 0.02, 0.03, 0.05):
        approx = cv2.approxPolyDP(hull, eps * peri, True)
        if len(approx) == 4:
            return order_corners(approx.reshape(4, 2).astype(np.float32))
    box = cv2.boxPoints(cv2.minAreaRect(hull))
    return order_corners(box.astype(np.float32))


def order_corners(pts: np.ndarray) -> np.ndarray:
    """Order 4 points as top-left, top-right, bottom-right, bottom-left."""
    pts = np.asarray(pts, dtype=np.float32).reshape(4, 2)
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).ravel()  # y - x
    return np.array(
        [pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]],
        dtype=np.float32,
    )
