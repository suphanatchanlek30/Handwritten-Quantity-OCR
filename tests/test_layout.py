from __future__ import annotations

import importlib.util

import cv2
import numpy as np
import pytest

from qty_ocr.blank_detector import detect_blank
from qty_ocr.layout import header_matches, locate_table, locate_table_auto
from qty_ocr.roi_extractor import extract_qty_cells
from qty_ocr.schemas import BlankLabel

from .conftest import ROOT, SAMPLE_PATH, render_form, warp

spec = importlib.util.spec_from_file_location("simulate_photos", ROOT / "scripts" / "simulate_photos.py")
simulate_photos = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simulate_photos)


def labels_for(cfg, img):
    loc = locate_table(img, cfg, recognizer=None)
    assert loc.align.success, loc.align.reasons
    cells = extract_qty_cells(loc.align.aligned_bgr, loc.align.grid, loc.qty.index, loc.header_rows, cfg.roi)
    return loc, [detect_blank(c.crop, cfg.blank_detection)[0].label for c in cells]


def test_auto_finds_grid_without_template(cfg):
    form = render_form(cfg, {1: "17", 3: "1"})
    loc, labels = labels_for(cfg, form)
    assert loc.align.method == "auto_rectify"
    assert loc.align.diagnostics["columns"] == 4 and loc.align.diagnostics["rows_incl_header"] == 11
    assert loc.qty.index == 2 and loc.qty.method == "position_fallback"  # no recogniser in this test
    assert labels[0] == BlankLabel.NONBLANK and labels[2] == BlankLabel.NONBLANK
    assert labels[1] == BlankLabel.BLANK and labels[9] == BlankLabel.BLANK


def test_auto_handles_extra_column(cfg):
    form = render_form(cfg, {2: "70"}, extra_first_column=True)
    loc, labels = labels_for(cfg, form)
    assert loc.align.diagnostics["columns"] == 5
    assert loc.qty.index == 3  # moved right by the extra "No." column
    assert labels[1] == BlankLabel.NONBLANK and labels[0] == BlankLabel.BLANK


def test_auto_ignores_dotted_lines_and_margin_numbers(cfg):
    form = render_form(cfg, {r: "1" for r in range(1, 11)}, margin_numbers=True)
    loc, _ = labels_for(cfg, form)
    hs = loc.align.grid.horizontal_lines
    assert len(hs) == 12  # header + 10 rows, dotted fill-in lines excluded


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_auto_on_simulated_phone_photos(cfg, seed):
    form = render_form(cfg, {1: "17", 4: "0"}, extra_first_column=seed == 2)
    photo = simulate_photos.simulate(form.astype(np.float32), np.random.default_rng(seed), strength=0.8)
    loc, labels = labels_for(cfg, photo)
    assert loc.align.diagnostics["rows_incl_header"] == 11
    assert labels[0] == BlankLabel.NONBLANK and labels[3] == BlankLabel.NONBLANK
    assert labels[1] == BlankLabel.BLANK and labels[9] == BlankLabel.BLANK


def test_auto_fails_cleanly_on_blank_page(cfg):
    res = locate_table_auto(np.full((900, 700, 3), 255, np.uint8), cfg.layout, cfg.alignment)
    assert not res.success and "no_table_with_grid_found" in res.reasons


@pytest.mark.skipif(not SAMPLE_PATH.exists(), reason="real sample not present")
def test_auto_on_real_sample_rotated(cfg):
    from qty_ocr.image_loader import load_image

    img = load_image(SAMPLE_PATH).bgr
    h, w = img.shape[:2]
    rotated = warp(img, cv2.getRotationMatrix2D((w / 2, h / 2), 5, 1.0), (w, h))
    loc, labels = labels_for(cfg, rotated)
    assert labels.count(BlankLabel.NONBLANK) == 6 and labels.count(BlankLabel.BLANK) == 4


@pytest.mark.parametrize("text,ok", [("qty", True), ("QTY", True), ("qry", True), ("จำนวน", True),
                                     ("unit", False), ("title", False), ("No.", False), ("", False)])
def test_header_matches(text, ok):
    assert header_matches(text, ["qty", "จำนวน"]) is ok
