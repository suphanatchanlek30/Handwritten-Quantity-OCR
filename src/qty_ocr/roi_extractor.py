"""Stage 4-6 — qty column, row segmentation and cell cropping."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import ROIConfig
from .schemas import BBox, validate_bbox
from .table_detector import TableGrid


@dataclass
class QtyCell:
    row_id: int                 # 1-based, top to bottom
    cell_bbox: BBox             # full cell between the grid lines (aligned coords)
    crop_bbox: BBox             # cell minus border margin (aligned coords)
    crop: np.ndarray            # BGR copy of the aligned image inside crop_bbox
    valid: bool
    problems: list[str]


def qty_cell_boxes(grid: TableGrid, qty_column_index: int, header_rows: int) -> list[tuple[int, BBox]]:
    """Return ``(row_id, cell_bbox)`` for each data row of the qty column, top to bottom."""
    q = qty_column_index
    x0, x1 = grid.vertical_lines[q], grid.vertical_lines[q + 1]
    rows = grid.horizontal_lines[header_rows:]
    return [(i + 1, (x0, rows[i], x1, rows[i + 1])) for i in range(len(rows) - 1)]


def shrink_bbox(bbox: BBox, margin: int) -> BBox:
    x0, y0, x1, y1 = bbox
    return (x0 + margin, y0 + margin, x1 - margin, y1 - margin)


def extract_qty_cells(
    aligned_bgr: np.ndarray,
    grid: TableGrid,
    qty_column_index: int,
    header_rows: int,
    cfg: ROIConfig,
) -> list[QtyCell]:
    """Crop every qty cell from the aligned document."""
    h, w = aligned_bgr.shape[:2]
    cells: list[QtyCell] = []
    for row_id, cell_bbox in qty_cell_boxes(grid, qty_column_index, header_rows):
        problems: list[str] = []
        crop_bbox = shrink_bbox(cell_bbox, cfg.crop_margin_px)
        try:
            validate_bbox(crop_bbox, w, h)
        except ValueError as exc:
            problems.append(f"bbox_invalid: {exc}")
        cw, ch = crop_bbox[2] - crop_bbox[0], crop_bbox[3] - crop_bbox[1]
        if cw < cfg.min_crop_width or ch < cfg.min_crop_height:
            problems.append(f"crop_too_small({cw}x{ch})")
        if problems:
            crop = np.zeros((0, 0, 3), dtype=np.uint8)
        else:
            x0, y0, x1, y1 = crop_bbox
            crop = aligned_bgr[y0:y1, x0:x1].copy()
        cells.append(
            QtyCell(
                row_id=row_id,
                cell_bbox=cell_bbox,
                crop_bbox=crop_bbox,
                crop=crop,
                valid=not problems,
                problems=problems,
            )
        )
    return cells
