from __future__ import annotations

import cv2
import numpy as np

from dataclasses import replace

from qty_ocr.blank_detector import count_ink_groups, detect_blank, ink_group_masks
from qty_ocr.preprocessing import build_variants, digit_segments
from qty_ocr.schemas import BlankLabel

from .conftest import draw_digit_strokes


def blank_crop(w: int = 222, h: int = 80) -> np.ndarray:
    return np.full((h, w, 3), 255, np.uint8)


def test_empty_cell_is_blank(cfg):
    stats, mask = detect_blank(blank_crop(), cfg.blank_detection)
    assert stats.label == BlankLabel.BLANK and stats.ink_pixels == 0 and mask.max() == 0


def test_thin_one_is_not_blank(cfg):
    crop = blank_crop()
    cv2.line(crop, (110, 18), (111, 58), (0, 0, 200), 1)  # hairline red "1"
    stats, _ = detect_blank(crop, cfg.blank_detection)
    assert stats.label == BlankLabel.NONBLANK


def test_handwritten_zero_is_not_blank(cfg):
    crop = blank_crop()
    draw_digit_strokes(crop, 100, 15, "0")
    stats, _ = detect_blank(crop, cfg.blank_detection)
    assert stats.label == BlankLabel.NONBLANK


def test_blue_and_black_ink_detected(cfg):
    for color in [(180, 80, 20), (30, 30, 30)]:
        crop = blank_crop()
        draw_digit_strokes(crop, 100, 15, "7", color=color, thickness=1)
        stats, _ = detect_blank(crop, cfg.blank_detection)
        assert stats.label == BlankLabel.NONBLANK, color


def test_tiny_speck_is_blank(cfg):
    crop = blank_crop()
    crop[40:42, 100:102] = (0, 0, 200)
    stats, _ = detect_blank(crop, cfg.blank_detection)
    assert stats.label == BlankLabel.BLANK


def test_residual_table_rule_ignored(cfg):
    crop = blank_crop()
    m = cfg.blank_detection.inspect_margin_px
    crop[m : m + 2, :] = (90, 90, 90)  # grey rule leaking in at the top edge
    stats, _ = detect_blank(crop, cfg.blank_detection)
    assert stats.label == BlankLabel.BLANK


def test_uncertain_band(cfg):
    crop = blank_crop()
    crop[38:42, 100:104] = (0, 0, 200)  # 16 px, short
    stats, _ = detect_blank(crop, cfg.blank_detection)
    assert stats.label == BlankLabel.UNCERTAIN


def test_ink_groups_count_separate_digits(cfg):
    crop = blank_crop()
    draw_digit_strokes(crop, 60, 15, "1")
    draw_digit_strokes(crop, 100, 15, "0")
    stats, _ = detect_blank(crop, cfg.blank_detection)
    assert stats.ink_groups == 2


def test_count_ink_groups_merges_x_overlap():
    # x, y, w, h, area — two strokes of one digit overlap in x
    comps = np.array([[10, 0, 20, 40, 100], [15, 10, 20, 30, 80], [60, 0, 15, 40, 90]])
    assert count_ink_groups(comps, min_area=15, min_height_ratio=0.3) == 2


def test_variants_are_bgr_uint8(cfg):
    crop = blank_crop()
    draw_digit_strokes(crop, 100, 15, "7")
    stats, _ = detect_blank(crop, cfg.blank_detection)
    all_on = replace(cfg.preprocessing, original=True, grayscale=True, red_mask=True, ink_isolation=True)
    variants = build_variants(crop, all_on, stats.ink_bbox)
    assert "original" in variants and "tight_crop" in variants and "red_mask" in variants
    for name, img in variants.items():
        assert img.ndim == 3 and img.shape[2] == 3 and img.dtype == np.uint8, name


def test_red_mask_skipped_for_black_ink(cfg):
    crop = blank_crop()
    draw_digit_strokes(crop, 100, 15, "7", color=(20, 20, 20))
    variants = build_variants(crop, replace(cfg.preprocessing, red_mask=True), None)
    assert "red_mask" not in variants and "tight_crop" not in variants


def test_digit_segments_split_left_to_right(cfg):
    crop = blank_crop()
    draw_digit_strokes(crop, 60, 15, "1")
    draw_digit_strokes(crop, 110, 15, "0")
    _, mask = detect_blank(crop, cfg.blank_detection)
    groups = ink_group_masks(mask, cfg.blank_detection.group_min_area, cfg.blank_detection.group_min_height_ratio)
    segs = digit_segments(crop, groups, 0.35)
    assert len(segs) == 2
    assert segs[0].shape[1] < segs[1].shape[1]  # narrow "1" first, wider "0" second
    for seg in segs:
        assert seg.dtype == np.uint8 and seg.shape[2] == 3
        assert (seg[0] == 255).all()  # white padding


def test_digit_segment_excludes_neighbour_pixels(cfg):
    crop = blank_crop()
    draw_digit_strokes(crop, 60, 15, "1")
    draw_digit_strokes(crop, 75, 15, "0")  # close neighbour, separate component
    _, mask = detect_blank(crop, cfg.blank_detection)
    groups = ink_group_masks(mask, cfg.blank_detection.group_min_area, cfg.blank_detection.group_min_height_ratio)
    segs = digit_segments(crop, groups, 0.35)
    assert len(segs) == 2
    cols = np.nonzero((segs[0].min(axis=2) < 150).any(axis=0))[0]
    assert 0 < cols.max() - cols.min() < 10  # only the narrow "1" stroke, no part of the "0"


def test_touching_digits_stay_one_segment(cfg):
    crop = blank_crop()
    draw_digit_strokes(crop, 60, 15, "0")
    draw_digit_strokes(crop, 80, 15, "0")  # ellipses overlap in x → one group
    _, mask = detect_blank(crop, cfg.blank_detection)
    groups = ink_group_masks(mask, cfg.blank_detection.group_min_area, cfg.blank_detection.group_min_height_ratio)
    assert len(groups) == 1


def test_relative_threshold_handles_dim_photo(cfg):
    crop = np.full((80, 222, 3), 150, np.uint8)  # grey paper in a dark photo
    cv2.line(crop, (110, 18), (112, 58), (110, 110, 135), 2)  # faint, low-contrast stroke
    stats, _ = detect_blank(crop, cfg.blank_detection)
    assert stats.label == BlankLabel.NONBLANK
    empty = np.full((80, 222, 3), 150, np.uint8)
    empty = np.clip(empty + np.random.default_rng(0).normal(0, 3, empty.shape), 0, 255).astype(np.uint8)
    assert detect_blank(empty, cfg.blank_detection)[0].label == BlankLabel.BLANK
