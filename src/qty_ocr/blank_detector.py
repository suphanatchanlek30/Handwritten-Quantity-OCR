"""Stage 7 — handwriting presence (blank / nonblank / uncertain).

Ink is the union of two masks so the detector is not tied to red pens:

* **colour ink** — saturated pixels (red, blue, green pens ...)
* **dark ink**   — dark pixels (black/pencil) after removing long, edge-touching
  rule fragments that could leak in from the table border.

A blank cell returns ``blank`` (later ``value = null``) — never ``"0"``.
Thin strokes such as a hairline ``1`` are kept by the stroke-height rule even
when their pixel count is small.
"""

from __future__ import annotations

import cv2
import numpy as np

from .config import BlankDetectionConfig
from .schemas import BlankLabel, BlankStats


def ink_mask(crop_bgr: np.ndarray, cfg: BlankDetectionConfig) -> np.ndarray:
    """Binary (0/255) mask of handwriting candidates in ``crop_bgr``."""
    hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
    sat = hsv[:, :, 1]
    if cfg.ink_threshold == "relative":
        # Compare with this cell's own paper (median) so blur, faded ink, colour casts
        # and exposure differences between photos do not need re-tuning.
        paper_gray = float(np.median(gray))
        paper_sat = float(np.median(sat))
        color = (sat >= paper_sat + cfg.color_min_contrast) & (hsv[:, :, 2] >= cfg.color_min_value)
        dark = (gray <= paper_gray - cfg.dark_min_contrast).astype(np.uint8) * 255
    else:
        color = (sat >= cfg.color_min_saturation) & (hsv[:, :, 2] >= cfg.color_min_value)
        dark = (gray <= cfg.dark_max_gray).astype(np.uint8) * 255
    dark = _remove_border_rules(dark)
    mask = (color | (dark > 0)).astype(np.uint8) * 255
    return _remove_small_components(mask, cfg.min_component_area)


def _remove_border_rules(mask: np.ndarray) -> np.ndarray:
    """Drop thin components that touch the crop edge and span most of it (table rules)."""
    h, w = mask.shape
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    out = mask.copy()
    for i in range(1, n):
        x, y, cw, ch, _area = stats[i]
        touches = x == 0 or y == 0 or x + cw == w or y + ch == h
        long_h = cw >= 0.8 * w and ch <= 6
        long_v = ch >= 0.8 * h and cw <= 6
        if touches and (long_h or long_v):
            out[labels == i] = 0
    return out


def _remove_small_components(mask: np.ndarray, min_area: int) -> np.ndarray:
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    keep = np.zeros(n, dtype=bool)
    keep[1:] = stats[1:, cv2.CC_STAT_AREA] >= min_area
    return (keep[labels]).astype(np.uint8) * 255


def detect_blank(
    crop_bgr: np.ndarray, cfg: BlankDetectionConfig
) -> tuple[BlankStats, np.ndarray]:
    """Classify a qty crop. Returns ``(stats, full_size_mask)``.

    ``stats.ink_bbox`` is relative to ``crop_bgr``.
    """
    h, w = crop_bgr.shape[:2]
    m = cfg.inspect_margin_px
    full_mask = np.zeros((h, w), dtype=np.uint8)
    if h <= 2 * m or w <= 2 * m:
        raise ValueError(f"Crop {w}x{h} too small for inspect margin {m}")
    inner = crop_bgr[m : h - m, m : w - m]
    mask = ink_mask(inner, cfg)
    full_mask[m : h - m, m : w - m] = mask

    ink_pixels = int((mask > 0).sum())
    n, _labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    n_components = n - 1
    max_h = int(stats[1:, cv2.CC_STAT_HEIGHT].max()) if n_components else 0
    ink_bbox = None
    if ink_pixels:
        ys, xs = np.nonzero(full_mask)
        ink_bbox = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)

    if ink_pixels >= cfg.nonblank_min_pixels or (
        ink_pixels >= cfg.uncertain_min_pixels and max_h >= cfg.min_stroke_height_px
    ):
        label = BlankLabel.NONBLANK
    elif ink_pixels >= cfg.uncertain_min_pixels:
        label = BlankLabel.UNCERTAIN
    else:
        label = BlankLabel.BLANK

    groups = count_ink_groups(stats[1:], cfg.group_min_area, cfg.group_min_height_ratio)
    stats_out = BlankStats(
        label=label,
        ink_pixels=ink_pixels,
        ink_ratio=round(ink_pixels / float(mask.size), 6),
        n_components=n_components,
        max_component_height=max_h,
        ink_groups=groups,
        ink_bbox=ink_bbox,
    )
    return stats_out, full_mask


def count_ink_groups(component_stats: np.ndarray, min_area: int, min_height_ratio: float) -> int:
    """Count clusters of significant components whose x-ranges do not overlap.

    Separate digits ("4" and "3") form separate groups; strokes of one digit
    (the two strokes of an open "4") overlap in x and form one group. Touching
    digits form one group, so this is a *lower bound* on the digit count.
    """
    if len(component_stats) == 0:
        return 0
    max_h = int(component_stats[:, cv2.CC_STAT_HEIGHT].max())
    spans = sorted(
        (int(x), int(x + w))
        for x, _y, w, h, area in component_stats
        if area >= min_area and h >= min_height_ratio * max_h
    )
    groups = 0
    current_end = -1
    for x0, x1 in spans:
        if x0 > current_end + 1:
            groups += 1
            current_end = x1
        else:
            current_end = max(current_end, x1)
    return groups


def ink_group_masks(mask: np.ndarray, min_area: int, min_height_ratio: float) -> list[np.ndarray]:
    """Split an ink mask into per-digit masks, left to right.

    Significant components (same rule as :func:`count_ink_groups`) whose
    x-ranges overlap are merged into one group; small fragments (dots, broken
    stroke pieces) join the group whose x-span contains their centre, otherwise
    the nearest group. Touching digits stay together in one group.
    """
    n, labels, stats, _ = cv2.connectedComponentsWithStats((mask > 0).astype(np.uint8), connectivity=8)
    if n <= 1:
        return []
    comp = stats[1:]
    max_h = int(comp[:, cv2.CC_STAT_HEIGHT].max())
    big = [
        i for i in range(len(comp))
        if comp[i, cv2.CC_STAT_AREA] >= min_area and comp[i, cv2.CC_STAT_HEIGHT] >= min_height_ratio * max_h
    ]
    if not big:
        return []
    big.sort(key=lambda i: comp[i, cv2.CC_STAT_LEFT])
    groups: list[list[int]] = []
    spans: list[list[int]] = []
    for i in big:
        x0 = int(comp[i, cv2.CC_STAT_LEFT])
        x1 = x0 + int(comp[i, cv2.CC_STAT_WIDTH])
        if spans and x0 <= spans[-1][1] + 1:
            groups[-1].append(i)
            spans[-1][1] = max(spans[-1][1], x1)
        else:
            groups.append([i])
            spans.append([x0, x1])
    for i in range(len(comp)):
        if i in big:
            continue
        cx = comp[i, cv2.CC_STAT_LEFT] + comp[i, cv2.CC_STAT_WIDTH] / 2
        g = min(range(len(spans)), key=lambda k: 0 if spans[k][0] <= cx <= spans[k][1]
                else min(abs(cx - spans[k][0]), abs(cx - spans[k][1])))
        groups[g].append(i)
    return [np.isin(labels, [i + 1 for i in g]).astype(np.uint8) * 255 for g in groups]
