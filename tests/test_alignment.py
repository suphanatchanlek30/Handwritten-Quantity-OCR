from __future__ import annotations

from dataclasses import replace

import cv2
import numpy as np
import pytest

from qty_ocr.alignment import align_document, map_bbox, transform_points
from qty_ocr.table_detector import line_positions, order_corners, snap_lines

from .conftest import SAMPLE_PATH, warp


def test_transform_points_roundtrip():
    H = np.array([[1.02, 0.03, 5.0], [-0.02, 0.98, -7.0], [1e-5, 2e-5, 1.0]])
    pts = np.array([[0, 0], [100, 50], [1600, 1700]], dtype=np.float64)
    back = transform_points(transform_points(pts, H), np.linalg.inv(H))
    assert np.allclose(back, pts, atol=1e-6)


def test_map_bbox_identity_and_clip():
    assert map_bbox((10, 20, 30, 40), np.eye(3), 100, 100) == (10, 20, 30, 40)
    assert map_bbox((-5, -5, 150, 30), np.eye(3), 100, 100) == (0, 0, 100, 30)


def test_order_corners_any_input_order():
    pts = np.array([[100, 900], [1500, 100], [100, 100], [1500, 900]], dtype=np.float32)
    tl, tr, br, bl = order_corners(pts)
    assert tuple(tl) == (100, 100) and tuple(tr) == (1500, 100)
    assert tuple(br) == (1500, 900) and tuple(bl) == (100, 900)


def test_line_positions_and_snap():
    profile = np.zeros(50)
    profile[10:12] = 100
    profile[30] = 100
    assert line_positions(profile, 50) == [10, 30]  # (10+11)/2 rounds to even -> 10
    snapped, missing = snap_lines([11, 29, 45], [10, 30], tolerance=3)
    assert snapped == [10, 30, 45] and missing == [45]


def test_identity_alignment(cfg, synthetic_form):
    res = align_document(synthetic_form, cfg.template, cfg.alignment)
    assert res.success and res.method == "homography" and not res.used_fallback
    assert res.grid.match_ratio == 1.0


@pytest.mark.parametrize("angle", [-3.0, 2.0])
def test_rotated_document(cfg, synthetic_form, angle):
    h, w = synthetic_form.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    res = align_document(warp(synthetic_form, M, (w, h)), cfg.template, cfg.alignment)
    assert res.success and res.method == "homography"
    assert res.grid.match_ratio >= cfg.alignment.min_line_match_ratio
    # after refinement every aligned grid line sits on its template position
    assert np.allclose(res.grid.vertical_lines, cfg.template.vertical_lines, atol=2)
    assert np.allclose(res.grid.horizontal_lines, cfg.template.horizontal_lines, atol=2)


@pytest.mark.parametrize("scale", [0.6, 1.4])
def test_resized_document(cfg, synthetic_form, scale):
    resized = cv2.resize(synthetic_form, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    res = align_document(resized, cfg.template, cfg.alignment)
    assert res.success and res.grid.match_ratio >= cfg.alignment.min_line_match_ratio


def test_perspective_document(cfg, synthetic_form):
    h, w = synthetic_form.shape[:2]
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst = np.float32([[30, 15], [w - 10, 0], [w - 40, h - 5], [0, h - 30]])
    M = cv2.getPerspectiveTransform(src, dst)
    res = align_document(warp(synthetic_form, M, (w, h)), cfg.template, cfg.alignment)
    assert res.success and res.method == "homography"
    assert res.grid.match_ratio >= cfg.alignment.min_line_match_ratio


def test_blank_page_fails_explicitly(cfg):
    blank = np.full((cfg.template.height, cfg.template.width, 3), 255, np.uint8)
    res = align_document(blank, cfg.template, cfg.alignment)
    assert not res.success and res.method == "none" and res.reasons


def test_static_mode_flags_nothing_on_reference(cfg, synthetic_form):
    static_cfg = replace(cfg.alignment, mode="static")
    res = align_document(synthetic_form, cfg.template, static_cfg)
    assert res.success and res.method == "static_scale" and not res.used_fallback


@pytest.mark.skipif(not SAMPLE_PATH.exists(), reason="real sample not present")
@pytest.mark.parametrize(
    "kind", ["rotate4", "perspective", "scale1.5"],
)
def test_real_sample_distorted(cfg, kind):
    from qty_ocr.image_loader import load_image

    img = load_image(SAMPLE_PATH).bgr
    h, w = img.shape[:2]
    if kind == "rotate4":
        im = warp(img, cv2.getRotationMatrix2D((w / 2, h / 2), 4, 1.0), (w, h))
    elif kind == "perspective":
        src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
        dst = np.float32([[120, 40], [w - 30, 0], [w - 140, h - 20], [0, h - 90]])
        im = warp(img, cv2.getPerspectiveTransform(src, dst), (w, h))
    else:
        im = cv2.resize(img, None, fx=1.5, fy=1.5)
    res = align_document(im, cfg.template, cfg.alignment)
    assert res.success and res.method == "homography" and res.grid.match_ratio == 1.0
    assert np.allclose(res.grid.vertical_lines, cfg.template.vertical_lines, atol=2)
    assert np.allclose(res.grid.horizontal_lines, cfg.template.horizontal_lines, atol=2)
