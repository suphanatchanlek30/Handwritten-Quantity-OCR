"""Stage 2 — template-aware document alignment.

Primary path (``automatic``): find the outer table rectangle from the printed
grid, compute a homography that maps its corners onto the template table
corners, warp, then *verify* by re-detecting the inner grid lines. Alignment
is only accepted when enough template lines are found at the expected place.

Fallback (``static``): scale the whole page to the template size. It is used
only in ``automatic_with_fallback`` mode, is verified the same way, and is
reported as a fallback so every field is flagged for review.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np

from .config import AlignmentConfig, TemplateConfig
from .schemas import BBox, clip_bbox
from .table_detector import (
    GridMasks,
    TableGrid,
    detect_grid,
    extract_grid_masks,
    find_table_quad,
    printed_ink_mask,
)

logger = logging.getLogger(__name__)


@dataclass
class AlignmentResult:
    success: bool
    method: str                      # "homography" | "static_scale" | "none"
    aligned_bgr: np.ndarray | None
    H: np.ndarray | None             # original -> aligned (template)
    H_inv: np.ndarray | None         # aligned -> original
    grid: TableGrid | None
    detected_quad: np.ndarray | None  # table corners on the original image
    used_fallback: bool = False
    reasons: list[str] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    source_masks: GridMasks | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "method": self.method,
            "used_fallback": self.used_fallback,
            "reasons": self.reasons,
            "H": self.H.round(6).tolist() if self.H is not None else None,
            "H_inv": self.H_inv.round(6).tolist() if self.H_inv is not None else None,
            "detected_quad": self.detected_quad.round(1).tolist()
            if self.detected_quad is not None
            else None,
            "grid": self.grid.to_dict() if self.grid else None,
            **self.diagnostics,
        }


def template_quad(template: TemplateConfig) -> np.ndarray:
    x0, y0, x1, y1 = template.table_box
    return np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], dtype=np.float32)


def transform_points(points: np.ndarray, H: np.ndarray) -> np.ndarray:
    """Apply a 3x3 homography to an (N, 2) array of points."""
    pts = np.asarray(points, dtype=np.float64).reshape(-1, 1, 2)
    return cv2.perspectiveTransform(pts, H).reshape(-1, 2)


def map_bbox(bbox: BBox, H: np.ndarray, width: int, height: int) -> BBox:
    """Map an axis-aligned box through ``H``; return its integer bounding box, clipped."""
    x0, y0, x1, y1 = bbox
    corners = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], dtype=np.float64)
    mapped = transform_points(corners, H)
    box = (
        int(np.floor(mapped[:, 0].min())),
        int(np.floor(mapped[:, 1].min())),
        int(np.ceil(mapped[:, 0].max())),
        int(np.ceil(mapped[:, 1].max())),
    )
    return clip_bbox(box, width, height)


def _quad_sanity(quad: np.ndarray, template: TemplateConfig) -> list[str]:
    """Geometric plausibility checks on a detected table quad."""
    problems: list[str] = []
    tl, tr, br, bl = quad
    top, bottom = np.linalg.norm(tr - tl), np.linalg.norm(br - bl)
    left, right = np.linalg.norm(bl - tl), np.linalg.norm(br - tr)
    if min(top, bottom, left, right) < 50:
        problems.append("table_quad_too_small")
        return problems
    tx0, ty0, tx1, ty1 = template.table_box
    expected_aspect = (tx1 - tx0) / (ty1 - ty0)
    aspect = ((top + bottom) / 2) / ((left + right) / 2)
    if not 0.75 * expected_aspect <= aspect <= 1.33 * expected_aspect:
        problems.append(f"table_aspect_mismatch({aspect:.3f} vs {expected_aspect:.3f})")
    if max(top, bottom) / min(top, bottom) > 1.5 or max(left, right) / min(left, right) > 1.5:
        problems.append("table_perspective_too_strong")
    return problems


def _warp_and_verify(
    bgr: np.ndarray, H: np.ndarray, template: TemplateConfig, cfg: AlignmentConfig
) -> tuple[np.ndarray, TableGrid]:
    aligned = cv2.warpPerspective(
        bgr,
        H,
        (template.width, template.height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )
    return aligned, detect_grid(aligned, template, cfg)


def _refine_with_intersections(
    bgr: np.ndarray,
    H: np.ndarray,
    grid: TableGrid,
    template: TemplateConfig,
    cfg: AlignmentConfig,
) -> tuple[np.ndarray, np.ndarray, TableGrid, float | None]:
    """Fit a correction homography from detected grid intersections to template ones.

    The outer quad comes from thickened line masks, so it is a few pixels too
    large; matching every detected (vertical x horizontal) intersection to its
    template position removes that bias. Only lines actually detected (not
    template fallbacks) are used. Returns the original transform unchanged when
    the refinement is not better.
    """
    mv, mh = set(grid.missing_vertical), set(grid.missing_horizontal)
    src, dst = [], []
    for xi, (xd, xt) in enumerate(zip(grid.vertical_lines, template.vertical_lines)):
        if xt in mv:
            continue
        for yi, (yd, yt) in enumerate(zip(grid.horizontal_lines, template.horizontal_lines)):
            if yt in mh:
                continue
            src.append((xd, yd))
            dst.append((xt, yt))
    if len(src) < 8:
        return H, *_warp_and_verify(bgr, H, template, cfg), None
    src_a, dst_a = np.float64(src), np.float64(dst)
    before = float(np.abs(src_a - dst_a).max())
    H_fix, _ = cv2.findHomography(src_a, dst_a, 0)
    if H_fix is None:
        return H, *_warp_and_verify(bgr, H, template, cfg), round(before, 2)
    H_new = H_fix @ H
    aligned, new_grid = _warp_and_verify(bgr, H_new, template, cfg)
    resid = [
        abs(d - t)
        for d, t in zip(new_grid.vertical_lines + new_grid.horizontal_lines,
                        list(template.vertical_lines) + list(template.horizontal_lines))
    ]
    after = float(max(resid))
    if new_grid.match_ratio < grid.match_ratio or after > before:
        aligned, grid = _warp_and_verify(bgr, H, template, cfg)
        return H, aligned, grid, round(before, 2)
    return H_new, aligned, new_grid, round(after, 2)


def _static_homography(width: int, height: int, template: TemplateConfig) -> np.ndarray:
    sx, sy = template.width / width, template.height / height
    return np.array([[sx, 0, 0], [0, sy, 0], [0, 0, 1]], dtype=np.float64)


def estimate_skew_deg(bgr: np.ndarray, cfg: AlignmentConfig, max_side: int = 1400) -> float | None:
    """Dominant near-horizontal line angle (degrees, image coords) or None if no long lines.

    Angles do not depend on scale, so large photos are downscaled first (Hough is the slow part).
    """
    scale = min(1.0, max_side / max(bgr.shape[:2]))
    if scale < 1.0:
        bgr = cv2.resize(bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    printed = printed_ink_mask(bgr, cfg)
    h, w = printed.shape
    lines = cv2.HoughLinesP(
        printed, 1, np.pi / 1800, threshold=150, minLineLength=int(0.2 * w), maxLineGap=10
    )
    if lines is None:
        return None
    angles, weights = [], []
    for x0, y0, x1, y1 in lines[:, 0]:
        ang = float(np.degrees(np.arctan2(y1 - y0, x1 - x0)))
        if ang > 90:
            ang -= 180
        elif ang < -90:
            ang += 180
        if abs(ang) <= cfg.max_skew_deg:
            angles.append(ang)
            weights.append(float(np.hypot(x1 - x0, y1 - y0)))
    if not angles:
        return None
    order = np.argsort(angles)
    cum = np.cumsum(np.asarray(weights)[order])
    return float(np.asarray(angles)[order][np.searchsorted(cum, cum[-1] / 2)])  # weighted median


def _rotation_homography(angle_deg: float, w: int, h: int) -> np.ndarray:
    R = cv2.getRotationMatrix2D((w / 2, h / 2), angle_deg, 1.0)
    return np.vstack([R, [0, 0, 1]]).astype(np.float64)


def align_document(
    bgr: np.ndarray, template: TemplateConfig, cfg: AlignmentConfig
) -> AlignmentResult:
    """Align ``bgr`` to the template. Never raises for poor alignment; inspect ``success``."""
    h, w = bgr.shape[:2]
    masks = extract_grid_masks(bgr, cfg)
    reasons: list[str] = []
    diagnostics: dict[str, Any] = {"input_size": [w, h]}
    quad: np.ndarray | None = None

    if cfg.mode in ("automatic", "automatic_with_fallback"):
        # Deskew first: long morphology kernels only catch rules within ~1 degree.
        R = np.eye(3)
        work, work_masks = bgr, masks
        skew = estimate_skew_deg(bgr, cfg) if cfg.deskew else None
        diagnostics["skew_deg"] = None if skew is None else round(skew, 3)
        if skew is not None and abs(skew) > 0.05:
            R = _rotation_homography(skew, w, h)
            work = cv2.warpAffine(bgr, R[:2], (w, h), flags=cv2.INTER_LINEAR,
                                  borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
            work_masks = extract_grid_masks(work, cfg)
        work_quad = find_table_quad(work_masks)
        if work_quad is not None:
            # report the quad in original-image coordinates
            quad = transform_points(work_quad, np.linalg.inv(R)).astype(np.float32)
        if work_quad is None:
            reasons.append("table_quad_not_found")
        else:
            problems = _quad_sanity(work_quad, template)
            if problems:
                reasons.extend(problems)
            else:
                H_quad = cv2.getPerspectiveTransform(work_quad, template_quad(template)).astype(np.float64)
                H = H_quad @ R
                aligned, grid = _warp_and_verify(bgr, H, template, cfg)
                if grid.match_ratio >= cfg.min_line_match_ratio:
                    H, aligned, grid, residual = _refine_with_intersections(bgr, H, grid, template, cfg)
                    diagnostics["refine_residual_px"] = residual
                diagnostics["homography_match_ratio"] = round(grid.match_ratio, 4)
                if grid.match_ratio >= cfg.min_line_match_ratio:
                    return AlignmentResult(
                        success=True,
                        method="homography",
                        aligned_bgr=aligned,
                        H=H,
                        H_inv=np.linalg.inv(H),
                        grid=grid,
                        detected_quad=quad,
                        reasons=reasons,
                        diagnostics=diagnostics,
                        source_masks=masks,
                    )
                reasons.append(
                    f"homography_line_match_low({grid.match_ratio:.2f}<{cfg.min_line_match_ratio})"
                )

    if cfg.mode in ("static", "automatic_with_fallback"):
        H = _static_homography(w, h, template)
        aligned, grid = _warp_and_verify(bgr, H, template, cfg)
        diagnostics["static_match_ratio"] = round(grid.match_ratio, 4)
        used_fallback = cfg.mode != "static"
        if grid.match_ratio >= cfg.min_line_match_ratio:
            if used_fallback:
                logger.warning("Automatic alignment failed (%s); using static fallback", reasons)
            return AlignmentResult(
                success=True,
                method="static_scale",
                aligned_bgr=aligned,
                H=H,
                H_inv=np.linalg.inv(H),
                grid=grid,
                detected_quad=quad,
                used_fallback=used_fallback,
                reasons=reasons,
                diagnostics=diagnostics,
                source_masks=masks,
            )
        reasons.append(
            f"static_line_match_low({grid.match_ratio:.2f}<{cfg.min_line_match_ratio})"
        )

    logger.error("Alignment failed: %s", reasons)
    return AlignmentResult(
        success=False,
        method="none",
        aligned_bgr=None,
        H=None,
        H_inv=None,
        grid=None,
        detected_quad=quad,
        reasons=reasons,
        diagnostics=diagnostics,
        source_masks=masks,
    )
