"""Template-free table localisation (``layout.mode: auto``).

Photos arrive at any size, rotation, perspective and lighting, and forms may
add or move columns. Instead of matching fixed template coordinates this
module:

1. extracts printed rules with a **local (adaptive) threshold** so shadows and
   uneven lighting do not matter, and only from low-saturation pixels so
   coloured handwriting is never taken for a rule;
2. deskews, then collects quadrilateral candidates from the rule mask and
   rectifies each one to a canonical width; the candidate whose interior has
   the most full-length rules wins (so the page border or desk edge is not
   mistaken for the table);
3. flattens illumination on the rectified table;
4. reads columns / rows directly from the detected rules (any count);
5. finds the qty column from the header text via the already-loaded
   recogniser (``qty`` / ``จำนวน``), falling back to "n-th column from the
   right" when no recogniser is available or the header is unreadable.
"""

from __future__ import annotations

import logging
import re
from difflib import SequenceMatcher
from dataclasses import dataclass, field, replace
from typing import Any

import cv2
import numpy as np

from .alignment import AlignmentResult, _rotation_homography, estimate_skew_deg, transform_points
from .config import AlignmentConfig, LayoutConfig
from .table_detector import TableGrid, extract_grid_masks, line_positions, order_corners, printed_ink_mask

logger = logging.getLogger(__name__)


@dataclass
class QtyColumn:
    index: int
    method: str                      # "header_ocr" | "position_fallback"
    header_texts: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"index": self.index, "method": self.method, "header_texts": self.header_texts, "notes": self.notes}


def flatten_illumination(bgr: np.ndarray, kernel: int) -> np.ndarray:
    """Divide each channel by its local background (max filter) so paper becomes white everywhere."""
    k = max(3, kernel | 1)
    se = cv2.getStructuringElement(cv2.MORPH_RECT, (k, k))
    out = np.empty_like(bgr)
    for c in range(3):
        ch = bgr[:, :, c]
        bg = cv2.blur(cv2.dilate(ch, se), (k, k)).astype(np.float32)
        out[:, :, c] = np.clip(ch.astype(np.float32) / np.maximum(bg, 1.0) * 255.0, 0, 255).astype(np.uint8)
    return out


def _merge_close(positions: list[int], min_gap: int) -> list[int]:
    merged: list[int] = []
    for p in sorted(positions):
        if merged and p - merged[-1] < min_gap:
            merged[-1] = (merged[-1] + p) // 2
        else:
            merged.append(p)
    return merged


def detect_rules(aligned: np.ndarray, box: tuple[int, int, int, int], align_cfg: AlignmentConfig,
                 layout: LayoutConfig, coverage: float | None = None,
                 search_pad: int | None = None, masks: Any = None) -> tuple[list[int], list[int]]:
    """Vertical / horizontal rules spanning ``coverage`` of ``box`` = (x0, y0, x1, y1).

    Rules are searched up to ``search_pad`` px outside the box so a slightly
    wrong box can be corrected; rules on the image border (page edges) are ignored.
    """
    cov = layout.final_line_coverage if coverage is None else coverage
    pad = layout.margin_px if search_pad is None else search_pad
    if masks is None:
        masks = extract_grid_masks(aligned, align_cfg)
    H, W = masks.horizontal.shape
    x0, y0, x1, y1 = box
    ys, ye = max(0, y0 - pad), min(H, y1 + pad)
    xs, xe = max(0, x0 - pad), min(W, x1 + pad)
    h_prof = (masks.horizontal[ys:ye, x0:x1] > 0).sum(axis=1)
    v_prof = (masks.vertical[y0:y1, xs:xe] > 0).sum(axis=0)
    hs = [p + ys for p in line_positions(h_prof, cov * (x1 - x0))]
    vs = [p + xs for p in line_positions(v_prof, cov * (y1 - y0))]
    edge = 4
    hs = [y for y in hs if edge <= y < H - edge]
    vs = [x for x in vs if edge <= x < W - edge]
    return _merge_close(vs, layout.min_column_width_px), _merge_close(hs, layout.min_row_height_px)


def _quad_candidates(masks_h: np.ndarray, masks_v: np.ndarray, min_area_ratio: float,
                     dilate_px: int = 3) -> list[np.ndarray]:
    k = max(3, dilate_px | 1)  # joins rule fragments broken by blur / perspective
    grid = cv2.dilate(cv2.bitwise_or(masks_h, masks_v), np.ones((k, k), np.uint8))
    contours, _ = cv2.findContours(grid, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    area_min = min_area_ratio * grid.shape[0] * grid.shape[1]
    quads: list[np.ndarray] = []
    for c in sorted(contours, key=cv2.contourArea, reverse=True)[:12]:
        if cv2.contourArea(c) < area_min:
            break
        hull = cv2.convexHull(c)
        peri = cv2.arcLength(hull, True)
        quad = None
        for eps in (0.01, 0.02, 0.03, 0.05):
            approx = cv2.approxPolyDP(hull, eps * peri, True)
            if len(approx) == 4:
                quad = approx.reshape(4, 2).astype(np.float32)
                break
        if quad is None:
            quad = cv2.boxPoints(cv2.minAreaRect(hull)).astype(np.float32)
        quad = order_corners(quad)
        if not any(np.abs(quad - q).max() < 15 for q in quads):
            quads.append(quad)
    return quads


def _target_size(quad: np.ndarray, width: int) -> tuple[int, int]:
    tl, tr, br, bl = quad
    w = (np.linalg.norm(tr - tl) + np.linalg.norm(br - bl)) / 2
    h = (np.linalg.norm(bl - tl) + np.linalg.norm(br - tr)) / 2
    return width, max(10, int(round(width * h / max(w, 1.0))))


def _connected_rules(vs: list[int], hs: list[int], masks: Any, reach: int = 8) -> tuple[list[int], list[int]]:
    """Keep only rules that meet at least two rules of the other direction.

    Dotted fill-in lines above/below the table, page edges and text baselines
    are long but do not intersect the table's vertical rules, so they are dropped.
    """
    Hh, Ww = masks.horizontal.shape

    def h_ok(y: int) -> bool:
        y0, y1 = max(0, y - reach), min(Hh, y + reach + 1)
        return sum(bool(masks.vertical[y0:y1, max(0, x - 3): x + 4].any()) for x in vs) >= 2

    def v_ok(x: int) -> bool:
        x0, x1 = max(0, x - reach), min(Ww, x + reach + 1)
        return sum(bool(masks.horizontal[max(0, y - 3): y + 4, x0:x1].any()) for y in hs) >= 2

    hs2 = [y for y in hs if h_ok(y)]
    vs2 = [x for x in vs if v_ok(x)]
    return vs2, hs2


def _fit_border_quad(big: np.ndarray, align_cfg: AlignmentConfig, layout: LayoutConfig) -> np.ndarray | None:
    """Outer table corners on ``big`` from Hough-fitted rules (tilted lines allowed).

    Only rules that intersect at least two rules of the other direction count,
    so dotted fill-in lines and page edges are ignored. Returns (tl, tr, br, bl) or None.
    """
    f = layout.border_fit_scale  # Hough on a reduced image; corners are re-measured on the final warp anyway
    small = cv2.resize(big, None, fx=f, fy=f, interpolation=cv2.INTER_AREA) if f < 1.0 else big
    pm = printed_ink_mask(small, align_cfg)
    H, W = pm.shape
    segs = cv2.HoughLinesP(pm, 1, np.pi / 720, threshold=int(120 * f),
                           minLineLength=int(0.15 * min(W, H)), maxLineGap=max(4, int(12 * f)))
    if segs is None:
        return None
    hor: list[tuple[float, float, float, float]] = []  # (x0, y0, x1, y1)
    ver: list[tuple[float, float, float, float]] = []
    for x0, y0, x1, y1 in segs[:, 0].astype(float):
        ang = abs(np.degrees(np.arctan2(y1 - y0, x1 - x0)))
        if ang <= 15 or ang >= 165:
            hor.append((x0, y0, x1, y1))
        elif 75 <= ang <= 105:
            ver.append((x0, y0, x1, y1))

    def cluster(lines: list[tuple[float, float, float, float]], horizontal: bool, gap: float) -> list[dict[str, Any]]:
        """Group collinear segments; fit y=a*x+b (horizontal) or x=a*y+b (vertical)."""
        items = []
        for x0, y0, x1, y1 in lines:
            u0, v0, u1, v1 = (x0, y0, x1, y1) if horizontal else (y0, x0, y1, x1)
            mid = (W if horizontal else H) / 2
            a = (v1 - v0) / (u1 - u0) if u1 != u0 else 0.0
            items.append((v0 + a * (mid - u0), u0, v0, u1, v1))
        items.sort()
        groups: list[list[tuple[float, ...]]] = []
        for it in items:
            if groups and it[0] - groups[-1][-1][0] <= gap:
                groups[-1].append(it)
            else:
                groups.append([it])
        out = []
        for g in groups:
            us = np.array([p for it in g for p in (it[1], it[3])])
            vs = np.array([p for it in g for p in (it[2], it[4])])
            a, b = np.polyfit(us, vs, 1) if np.ptp(us) > 1 else (0.0, float(vs.mean()))
            out.append({"a": a, "b": b, "lo": us.min(), "hi": us.max()})
        return out

    hl = cluster(hor, True, gap=8)
    vl = cluster(ver, False, gap=8)

    def meets(h: dict[str, Any], v: dict[str, Any], tol: float = 12) -> bool:
        # intersection of y = ah*x + bh and x = av*y + bv
        y = (h["a"] * v["b"] + h["b"]) / (1 - h["a"] * v["a"])
        x = v["a"] * y + v["b"]
        return h["lo"] - tol <= x <= h["hi"] + tol and v["lo"] - tol <= y <= v["hi"] + tol

    hl = [h for h in hl if sum(meets(h, v) for v in vl) >= 2]
    vl = [v for v in vl if sum(meets(h, v) for h in hl) >= 2]
    if len(hl) < 2 or len(vl) < 2:
        return None
    top = min(hl, key=lambda h: h["a"] * W / 2 + h["b"])
    bottom = max(hl, key=lambda h: h["a"] * W / 2 + h["b"])
    left = min(vl, key=lambda v: v["a"] * H / 2 + v["b"])
    right = max(vl, key=lambda v: v["a"] * H / 2 + v["b"])

    def cross(h: dict[str, Any], v: dict[str, Any]) -> tuple[float, float]:
        y = (h["a"] * v["b"] + h["b"]) / (1 - h["a"] * v["a"])
        return v["a"] * y + v["b"], y

    quad = np.float64([cross(top, left), cross(top, right), cross(bottom, right), cross(bottom, left)])
    if not np.all(np.isfinite(quad)):
        return None
    return quad / f


def _evaluate_candidate(
    bgr: np.ndarray, quad: np.ndarray, R: np.ndarray, layout: LayoutConfig, align_cfg: AlignmentConfig
) -> tuple[int, np.ndarray, np.ndarray, list[int], list[int], tuple[int, int]] | None:
    """Rectify a candidate with a wide margin, snap its box to the outermost rules, re-rectify, verify.

    Returns ``(score, H, quad_in_original, vertical_rules, horizontal_rules, (w, h))`` or None.
    A valid table has rules spanning ``final_line_coverage`` of its box and rules on all four borders.
    """
    W = layout.normalized_table_width
    M = max(layout.margin_px, int(round(layout.search_margin_ratio * W)))
    quad2 = transform_points(quad, np.linalg.inv(R)).astype(np.float32)  # original-image coords
    for _ in range(max(1, layout.refine_iterations)):
        tw, th = _target_size(quad2, W)
        dst = np.float32([[M, M], [M + tw, M], [M + tw, M + th], [M, M + th]])
        H1 = cv2.getPerspectiveTransform(quad2, dst).astype(np.float64)
        size = (tw + 2 * M, th + 2 * M)
        big = cv2.warpPerspective(bgr, H1, size, flags=cv2.INTER_LINEAR,
                                  borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
        # A rough quad leaves residual perspective (rows tilted by different angles), which
        # axis-aligned projections cannot follow. Fit the four outer rules as free lines.
        fitted = _fit_border_quad(big, align_cfg, layout) if layout.fit_border_lines else None
        if fitted is not None:
            quad2 = transform_points(fitted, np.linalg.inv(H1)).astype(np.float32)
            continue
        big_masks = extract_grid_masks(big, align_cfg)
        vs, hs = detect_rules(big, (M, M, M + tw, M + th), align_cfg, layout,
                              coverage=layout.min_line_coverage, search_pad=M, masks=big_masks)
        vs, hs = _connected_rules(vs, hs, big_masks)
        if len(vs) < 2 or len(hs) < 2:
            return None
        box = np.float64([[vs[0], hs[0]], [vs[-1], hs[0]], [vs[-1], hs[-1]], [vs[0], hs[-1]]])
        quad2 = transform_points(box, np.linalg.inv(H1)).astype(np.float32)

    m = layout.margin_px
    tw2, th2 = _target_size(quad2, W)
    dst2 = np.float32([[m, m], [m + tw2, m], [m + tw2, m + th2], [m, m + th2]])
    H2 = cv2.getPerspectiveTransform(quad2, dst2).astype(np.float64)
    aligned = cv2.warpPerspective(bgr, H2, (tw2 + 2 * m, th2 + 2 * m), flags=cv2.INTER_LINEAR,
                                  borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
    vs2, hs2 = detect_rules(aligned, (m, m, m + tw2, m + th2), align_cfg, layout)
    if len(vs2) < layout.min_columns + 1 or len(hs2) < 3:
        return None
    tol = layout.border_tolerance_px
    on_border = (abs(vs2[0] - m) <= tol and abs(vs2[-1] - (m + tw2)) <= tol
                 and abs(hs2[0] - m) <= tol and abs(hs2[-1] - (m + th2)) <= tol)
    if not on_border:
        return None
    score = (len(vs2) - 1) * (len(hs2) - 1)
    return score, H2, quad2, vs2, hs2, (tw2, th2)


def locate_table_auto(bgr: np.ndarray, layout: LayoutConfig, align_cfg: AlignmentConfig) -> AlignmentResult:
    """Find, rectify and grid the table without a template. Never raises for a bad image."""
    h, w = bgr.shape[:2]
    diagnostics: dict[str, Any] = {"input_size": [w, h], "layout_mode": "auto"}
    reasons: list[str] = []

    R = np.eye(3)
    work = bgr
    skew = estimate_skew_deg(bgr, align_cfg) if align_cfg.deskew else None
    diagnostics["skew_deg"] = None if skew is None else round(skew, 3)
    if skew is not None and abs(skew) > 0.05:
        R = _rotation_homography(skew, w, h)
        work = cv2.warpAffine(bgr, R[:2], (w, h), flags=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
    # Shorter kernels for the coarse search: under strong perspective each rule is slanted
    # differently, and long kernels only catch fragments. Precision comes later, on rectified images.
    coarse_cfg = replace(
        align_cfg,
        horizontal_kernel_ratio=align_cfg.horizontal_kernel_ratio * layout.coarse_kernel_scale,
        vertical_kernel_ratio=align_cfg.vertical_kernel_ratio * layout.coarse_kernel_scale,
    )
    masks = extract_grid_masks(work, coarse_cfg)
    candidates = _quad_candidates(masks.horizontal, masks.vertical, layout.min_table_area_ratio)
    diagnostics["quad_candidates"] = len(candidates)

    m = layout.margin_px
    best: tuple[int, np.ndarray, np.ndarray, list[int], list[int], tuple[int, int]] | None = None
    # Candidates are ordered by area; the first one that verifies as a full table wins
    # (larger non-table candidates such as the page outline fail verification quickly).
    for quad in candidates:
        best = _evaluate_candidate(bgr, quad, R, layout, align_cfg)
        if best is not None:
            break
    if best is None and layout.candidate_dilate_ratio > 0:
        # Fallback only: join rule fragments broken by blur / strong perspective.
        joined = _quad_candidates(masks.horizontal, masks.vertical, layout.min_table_area_ratio,
                                  int(layout.candidate_dilate_ratio * max(w, h)))
        extra = [q for q in joined if not any(np.abs(q - c).max() < 15 for c in candidates)]
        diagnostics["quad_candidates_fallback"] = len(extra)
        for quad in extra:
            best = _evaluate_candidate(bgr, quad, R, layout, align_cfg)
            if best is not None:
                break

    if best is None:
        reasons.append("no_table_with_grid_found")
        logger.error("Auto layout failed: %s (candidates=%d)", reasons, len(candidates))
        return AlignmentResult(False, "none", None, None, None, None, None, reasons=reasons,
                               diagnostics=diagnostics, source_masks=masks)

    _, H, quad_orig, vs, hs, (tw, th) = best
    aligned = cv2.warpPerspective(bgr, H, (tw + 2 * m, th + 2 * m), flags=cv2.INTER_LINEAR,
                                  borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
    if layout.flatten_illumination:
        aligned = flatten_illumination(aligned, layout.flatten_kernel_px)
    grid = TableGrid(vertical_lines=vs, horizontal_lines=hs, detected_vertical=vs,
                     detected_horizontal=hs, match_ratio=1.0)
    diagnostics.update({"columns": len(vs) - 1, "rows_incl_header": len(hs) - 1,
                        "rectified_size": [tw + 2 * m, th + 2 * m]})
    return AlignmentResult(True, "auto_rectify", aligned, H, np.linalg.inv(H), grid, quad_orig,
                           reasons=reasons, diagnostics=diagnostics, source_masks=masks)


def header_cells(grid: TableGrid, inset: int = 5) -> list[tuple[int, int, int, int]]:
    """Header cell boxes (inside the rules), left to right."""
    y0, y1 = grid.horizontal_lines[0], grid.horizontal_lines[1]
    xs = grid.vertical_lines
    return [(xs[i] + inset, y0 + inset, xs[i + 1] - inset, y1 - inset) for i in range(len(xs) - 1)]


def first_text_line(cell_bgr: np.ndarray, pad: int = 6) -> np.ndarray | None:
    """Crop the top-most printed text line of a header cell (e.g. ``qty`` above ``จำนวน``)."""
    gray = cv2.cvtColor(cell_bgr, cv2.COLOR_BGR2GRAY)
    dark = gray < 160
    rows = dark.sum(axis=1)
    on = rows > max(1, 0.01 * dark.shape[1])
    bands: list[tuple[int, int]] = []
    start = None
    for i, v in enumerate(on):
        if v and start is None:
            start = i
        elif not v and start is not None:
            bands.append((start, i))
            start = None
    if start is not None:
        bands.append((start, len(on)))
    bands = [bd for bd in bands if bd[1] - bd[0] >= 4]
    if not bands:
        return None
    y0, y1 = bands[0]
    cols = np.nonzero(dark[y0:y1].any(axis=0))[0]
    x0, x1 = int(cols.min()), int(cols.max()) + 1
    line = cell_bgr[max(0, y0 - pad): y1 + pad, max(0, x0 - pad): x1 + pad]
    return np.ascontiguousarray(line)


def header_matches(text: str, keywords: list[str], min_ratio: float = 0.66) -> bool:
    """Substring match, or one-character-off match for short Latin keywords (``qry`` ~ ``qty``)."""
    t = text.lower()
    if any(k in t for k in keywords):
        return True
    tokens = re.findall(r"[a-z0-9]+", t)
    return any(
        SequenceMatcher(None, tok, k).ratio() >= min_ratio
        for tok in tokens for k in keywords if k.isascii() and len(tok) >= len(k) - 1
    )


def locate_qty_column(aligned: np.ndarray, grid: TableGrid, layout: LayoutConfig, recognizer: Any = None) -> QtyColumn:
    """Verify the expected column's header text first (1 inference); scan others only if needed."""
    n_cols = len(grid.vertical_lines) - 1
    fallback = n_cols - layout.qty_column_from_right
    notes: list[str] = []
    if not 0 <= fallback < n_cols:
        notes.append(f"qty_column_from_right={layout.qty_column_from_right} invalid for {n_cols} columns")
        fallback = max(0, n_cols - 1)
    if recognizer is None:
        return QtyColumn(fallback, "position_fallback", notes=notes + ["no_recognizer"])

    keys = [k.lower() for k in layout.qty_header_keywords]
    lines = [first_text_line(aligned[y0:y1, x0:x1]) for x0, y0, x1, y1 in header_cells(grid)]
    texts: list[str] = [""] * n_cols

    def read(indices: list[int]) -> None:
        todo = [i for i in indices if lines[i] is not None]
        for i, r in zip(todo, recognizer.recognize_batch([lines[i] for i in todo])):
            texts[i] = (r.raw_text or "").strip()

    def is_qty(i: int) -> bool:
        return header_matches(texts[i], keys)

    read([fallback])
    if is_qty(fallback):
        return QtyColumn(fallback, "header_ocr", texts, notes)
    read([i for i in range(n_cols) if i != fallback])
    hits = [i for i in range(n_cols) if is_qty(i)]
    if len(hits) == 1:
        notes.append(f"header_ocr_differs_from_position({hits[0]} vs {fallback})")
        return QtyColumn(hits[0], "header_ocr", texts, notes)
    notes.append(f"header_ocr_matches={hits}")
    return QtyColumn(fallback, "position_fallback", texts, notes)


@dataclass
class TableLocation:
    align: AlignmentResult
    qty: QtyColumn | None
    header_rows: int


def locate_geometry(bgr: np.ndarray, cfg: Any) -> AlignmentResult:
    """Table geometry only (no OCR): safe to run in a worker thread while OCR runs elsewhere."""
    from .alignment import align_document

    if cfg.layout.mode == "template":
        return align_document(bgr, cfg.template, cfg.alignment)
    return locate_table_auto(bgr, cfg.layout, cfg.alignment)


def resolve_qty_column(align: AlignmentResult, cfg: Any, recognizer: Any = None) -> TableLocation:
    """Pick the qty column for an aligned table (header OCR in auto mode)."""
    if cfg.layout.mode == "template":
        qty = QtyColumn(cfg.template.qty_column_index, "template") if align.success else None
        return TableLocation(align, qty, cfg.template.header_rows)
    qty = None
    if align.success and align.aligned_bgr is not None and align.grid is not None:
        qty = locate_qty_column(align.aligned_bgr, align.grid, cfg.layout, recognizer)
        align.diagnostics["qty_column"] = qty.to_dict()
    return TableLocation(align, qty, cfg.layout.header_rows)


def locate_table(bgr: np.ndarray, cfg: Any, recognizer: Any = None) -> TableLocation:
    """Dispatch on ``layout.mode``; returns alignment + qty column for either mode."""
    return resolve_qty_column(locate_geometry(bgr, cfg), cfg, recognizer)
