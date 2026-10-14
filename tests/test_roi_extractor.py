from __future__ import annotations

import cv2
import numpy as np
import pytest

from qty_ocr.alignment import align_document
from qty_ocr.blank_detector import detect_blank
from qty_ocr.roi_extractor import extract_qty_cells, qty_cell_boxes
from qty_ocr.schemas import BlankLabel, clip_bbox, validate_bbox

from .conftest import SAMPLE_PATH, render_form


def test_validate_bbox():
    validate_bbox((0, 0, 10, 10), 10, 10)
    for bad in [(5, 5, 5, 10), (-1, 0, 5, 5), (0, 0, 11, 5), (3, 3, 2, 8)]:
        with pytest.raises(ValueError):
            validate_bbox(bad, 10, 10)
    assert clip_bbox((-3, -3, 20, 20), 10, 10) == (0, 0, 10, 10)


def test_rows_top_to_bottom_and_inside_qty_column(cfg, synthetic_form):
    res = align_document(synthetic_form, cfg.template, cfg.alignment)
    cells = extract_qty_cells(res.aligned_bgr, res.grid, cfg.template.qty_column_index, cfg.template.header_rows, cfg.roi)
    assert [c.row_id for c in cells] == list(range(1, cfg.field.expected_rows + 1))
    ys = [c.crop_bbox[1] for c in cells]
    assert ys == sorted(ys)
    q = cfg.template.qty_column_index
    x_left, x_right = res.grid.vertical_lines[q], res.grid.vertical_lines[q + 1]
    for c in cells:
        assert c.valid
        assert x_left < c.crop_bbox[0] < c.crop_bbox[2] < x_right
        assert c.crop.shape[:2] == (c.crop_bbox[3] - c.crop_bbox[1], c.crop_bbox[2] - c.crop_bbox[0])


def test_header_row_excluded(cfg):
    grid_rows = qty_cell_boxes(
        type("G", (), {"vertical_lines": list(cfg.template.vertical_lines),
                       "horizontal_lines": list(cfg.template.horizontal_lines)})(),
        cfg.template.qty_column_index,
        cfg.template.header_rows,
    )
    assert grid_rows[0][1][1] == cfg.template.horizontal_lines[1]


def test_margin_numbers_never_in_crops(cfg):
    """Red numbers right of the table must not appear in any qty crop."""
    form = render_form(cfg, {r: "1" for r in range(1, 11)}, margin_numbers=True)
    res = align_document(form, cfg.template, cfg.alignment)
    cells = extract_qty_cells(res.aligned_bgr, res.grid, cfg.template.qty_column_index, cfg.template.header_rows, cfg.roi)
    table_right = cfg.template.vertical_lines[-1]
    assert all(c.crop_bbox[2] < table_right for c in cells)


def test_stroke_near_cell_edge_survives_crop(cfg):
    form = render_form(cfg, {})
    t = cfg.template
    x = t.vertical_lines[t.qty_column_index] + 100
    y_bottom = t.horizontal_lines[2]  # bottom border of row 1
    cv2.line(form, (x, y_bottom - 40), (x, y_bottom - 9), (0, 0, 200), 3)  # ends 9px above rule
    res = align_document(form, cfg.template, cfg.alignment)
    cell = extract_qty_cells(res.aligned_bgr, res.grid, cfg.template.qty_column_index, cfg.template.header_rows, cfg.roi)[0]
    stats, _ = detect_blank(cell.crop, cfg.blank_detection)
    assert stats.label == BlankLabel.NONBLANK
    assert stats.ink_bbox[3] >= cell.crop.shape[0] - 8  # stroke reaches bottom of crop


@pytest.mark.skipif(not SAMPLE_PATH.exists(), reason="real sample not present")
def test_real_sample_crops(cfg):
    from qty_ocr.image_loader import load_image

    img = load_image(SAMPLE_PATH)
    res = align_document(img.bgr, cfg.template, cfg.alignment)
    assert res.success
    cells = extract_qty_cells(res.aligned_bgr, res.grid, cfg.template.qty_column_index, cfg.template.header_rows, cfg.roi)
    assert len(cells) == 10 and all(c.valid for c in cells)
    q = cfg.template.qty_column_index
    for c in cells:  # crops stay inside the qty column (right-margin numbers excluded)
        assert cfg.template.vertical_lines[q] - 3 < c.crop_bbox[0]
        assert c.crop_bbox[2] < cfg.template.vertical_lines[q + 1] + 3
    labels = [detect_blank(c.crop, cfg.blank_detection)[0].label for c in cells]
    # sanity check from visual inspection, not a rule forced on the output
    assert labels.count(BlankLabel.NONBLANK) == 6 and labels.count(BlankLabel.BLANK) == 4
    assert np.all([c.crop.dtype == np.uint8 for c in cells])
