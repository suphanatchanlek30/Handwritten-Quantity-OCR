"""Debug images: grid lines, detected table, qty overlay and contact sheet.

Visualisation never mutates inputs; every function draws on a copy.
"""

from __future__ import annotations

import cv2
import numpy as np

from .schemas import FieldResult, FieldStatus

# BGR colours
GREEN = (0, 160, 0)
YELLOW = (0, 190, 255)
GRAY = (150, 150, 150)
RED = (0, 0, 230)
BLUE = (200, 90, 0)

STATUS_COLORS = {
    FieldStatus.OK: GREEN,
    FieldStatus.NEEDS_REVIEW: YELLOW,
    FieldStatus.INVALID_TEXT: YELLOW,
    FieldStatus.BLANK: GRAY,
    FieldStatus.FIELD_NOT_FOUND: RED,
    FieldStatus.RECOGNITION_ERROR: RED,
    FieldStatus.ALIGNMENT_FAILED: RED,
}

FONT = cv2.FONT_HERSHEY_SIMPLEX


def draw_table_lines(bgr: np.ndarray, horizontal: np.ndarray, vertical: np.ndarray) -> np.ndarray:
    out = (bgr.astype(np.float32) * 0.5 + 127).astype(np.uint8)
    out[horizontal > 0] = (0, 0, 255)
    out[vertical > 0] = (255, 0, 0)
    return out


def draw_detected_table(
    bgr: np.ndarray,
    quad: np.ndarray | None,
    vertical: list[int] | None = None,
    horizontal: list[int] | None = None,
) -> np.ndarray:
    """Draw the detected table quad (and, on aligned images, the snapped grid)."""
    out = bgr.copy()
    if quad is not None:
        cv2.polylines(out, [quad.astype(np.int32).reshape(-1, 1, 2)], True, BLUE, 3)
    if vertical and horizontal:
        for x in vertical:
            cv2.line(out, (x, horizontal[0]), (x, horizontal[-1]), GREEN, 1)
        for y in horizontal:
            cv2.line(out, (vertical[0], y), (vertical[-1], y), GREEN, 1)
    return out


def _label(img: np.ndarray, text: str, org: tuple[int, int], color: tuple[int, int, int], scale: float = 0.6) -> None:
    (tw, th), base = cv2.getTextSize(text, FONT, scale, 1)
    x, y = org
    cv2.rectangle(img, (x - 2, y - th - 4), (x + tw + 2, y + base), (255, 255, 255), -1)
    cv2.rectangle(img, (x - 2, y - th - 4), (x + tw + 2, y + base), color, 1)
    cv2.putText(img, text, (x, y), FONT, scale, color, 1, cv2.LINE_AA)


def draw_qty_overlay(original_bgr: np.ndarray, fields: list[FieldResult]) -> np.ndarray:
    """Field rectangles on the original document; labels sit left of the cell."""
    out = original_bgr.copy()
    for f in fields:
        if f.bbox_original is None:
            continue
        color = STATUS_COLORS.get(f.status, RED)
        x0, y0, x1, y1 = f.bbox_original
        cv2.rectangle(out, (x0, y0), (x1, y1), color, 2)
        if f.status == FieldStatus.BLANK:
            text = f"R{f.row_id} blank"
        elif f.value is not None:
            conf = f"{f.confidence:.2f}" if f.confidence is not None else "-"
            text = f"R{f.row_id} {f.value} ({conf})"
        else:
            text = f"R{f.row_id} {f.status.value}"
        (tw, _), _ = cv2.getTextSize(text, FONT, 0.6, 1)
        _label(out, text, (max(2, x0 - tw - 10), y0 + 22), color)
    return out


def _fit_height(img: np.ndarray, height: int) -> np.ndarray:
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    if img.size == 0:
        return np.full((height, height, 3), 220, np.uint8)
    scale = height / img.shape[0]
    return cv2.resize(img, (max(1, int(img.shape[1] * scale)), height), interpolation=cv2.INTER_AREA)


def _pad_width(img: np.ndarray, width: int) -> np.ndarray:
    if img.shape[1] >= width:
        return img[:, :width]
    pad = np.full((img.shape[0], width - img.shape[1], 3), 255, np.uint8)
    return np.hstack([img, pad])


def contact_sheet(
    fields: list[FieldResult],
    originals: dict[int, np.ndarray],
    chosen: dict[int, np.ndarray],
    row_height: int = 80,
) -> np.ndarray:
    """One row per field: id | original crop | chosen variant | prediction text."""
    crop_w, var_w, text_w, id_w = 240, 240, 420, 70
    rows = []
    header = np.full((30, id_w + crop_w + var_w + text_w, 3), 255, np.uint8)
    for x, t in ((5, "row"), (id_w + 5, "original crop"), (id_w + crop_w + 5, "chosen variant"),
                 (id_w + crop_w + var_w + 5, "prediction / conf / status")):
        cv2.putText(header, t, (x, 20), FONT, 0.55, (0, 0, 0), 1, cv2.LINE_AA)
    rows.append(header)
    for f in fields:
        color = STATUS_COLORS.get(f.status, RED)
        idp = np.full((row_height, id_w, 3), 255, np.uint8)
        cv2.putText(idp, f"{f.row_id:02d}", (12, row_height // 2 + 10), FONT, 0.9, (0, 0, 0), 2, cv2.LINE_AA)
        orig = _pad_width(_fit_height(originals.get(f.row_id, np.zeros((0, 0, 3), np.uint8)), row_height), crop_w)
        var = chosen.get(f.row_id)
        varp = _pad_width(_fit_height(var, row_height), var_w) if var is not None else np.full((row_height, var_w, 3), 255, np.uint8)
        txt = np.full((row_height, text_w, 3), 255, np.uint8)
        value = f.value if f.value is not None else ("null" if f.is_blank else (repr(f.raw_text) if f.raw_text is not None else "-"))
        conf = f"{f.confidence:.3f}" if f.confidence is not None else "-"
        cv2.putText(txt, f"{value}", (10, 30), FONT, 0.9, (0, 0, 0), 2, cv2.LINE_AA)
        cv2.putText(txt, f"conf {conf}  {f.status.value}", (10, 55), FONT, 0.5, color, 1, cv2.LINE_AA)
        if f.preprocessing_variant:
            cv2.putText(txt, f"variant {f.preprocessing_variant}", (10, 74), FONT, 0.45, (90, 90, 90), 1, cv2.LINE_AA)
        row = np.hstack([idp, orig, varp, txt])
        cv2.rectangle(row, (0, 0), (row.shape[1] - 1, row.shape[0] - 1), color, 2)
        rows.append(row)
    return np.vstack(rows)
