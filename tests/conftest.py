"""Shared fixtures: a synthetic CHANGHOUSE-like form renderer.

Synthetic images exercise geometry / blank-detection logic only. They are not
evidence of OCR accuracy on real handwriting.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from qty_ocr.config import AppConfig, load_config

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs" / "changhouse.yaml"
SAMPLE_PATH = ROOT / "data" / "samples" / "order_form_01.jpg"
RED = (0, 0, 200)  # BGR


@pytest.fixture(scope="session")
def cfg() -> AppConfig:
    return load_config(CONFIG_PATH)


def draw_digit_strokes(img: np.ndarray, x: int, y: int, kind: str, color=RED, thickness: int = 3) -> None:
    """Very simple handwriting-like strokes: '1' (vertical bar), '0' (ellipse), '7'."""
    if kind == "1":
        cv2.line(img, (x, y), (x + 2, y + 40), color, thickness)
    elif kind == "0":
        cv2.ellipse(img, (x + 12, y + 20), (11, 19), 0, 0, 360, color, thickness)
    elif kind == "7":
        cv2.line(img, (x, y), (x + 22, y), color, thickness)
        cv2.line(img, (x + 22, y), (x + 8, y + 40), color, thickness)


def render_form(
    cfg: AppConfig,
    filled: dict[int, str] | None = None,
    margin_numbers: bool = True,
    extra_first_column: bool = False,
) -> np.ndarray:
    """Render the template grid with optional red strokes in qty cells (row -> digits).

    ``extra_first_column`` inserts a narrow "No." column (like the V2 form) so the
    qty column moves right — the auto layout must still find it.
    """
    t = cfg.template
    img = np.full((t.height, t.width, 3), 255, np.uint8)
    xs, ys = list(t.vertical_lines), t.horizontal_lines
    q = t.qty_column_index
    if extra_first_column:
        xs = [xs[0], xs[0] + 70] + [x + 0 for x in xs[1:]]
        q += 1
    for x in xs:
        cv2.line(img, (x, ys[0]), (x, ys[-1]), (90, 90, 90), 2)
    for y in ys:
        cv2.line(img, (xs[0], y), (xs[-1], y), (90, 90, 90), 2)
    cv2.putText(img, "CHANGHOUSE", (xs[0], 160), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (30, 30, 30), 2)
    for y in (287, 341):  # dotted fill-in lines above the table (must not be taken as table rules)
        for x in range(xs[0] + 170, xs[-1], 9):
            cv2.line(img, (x, y), (x + 4, y), (150, 150, 150), 1)
    for r, (y0, y1) in enumerate(zip(ys[1:-1], ys[2:]), start=1):
        cv2.putText(img, f"88501701{r:05d}", (xs[0] + 40, y0 + 55), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (20, 20, 20), 2)
        digits = (filled or {}).get(r)
        if digits:
            x = xs[q] + 80
            for d in digits:
                draw_digit_strokes(img, x, y0 + 22, d)
                x += 34
            if margin_numbers:  # red annotation outside the table must never be read
                draw_digit_strokes(img, xs[-1] + 30, y0 + 22, digits[0])
    return img


@pytest.fixture
def synthetic_form(cfg: AppConfig) -> np.ndarray:
    return render_form(cfg, {1: "17", 2: "0", 3: "1", 5: "70"})


def warp(img: np.ndarray, M: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    if M.shape == (2, 3):
        return cv2.warpAffine(img, M, size, borderValue=(255, 255, 255))
    return cv2.warpPerspective(img, M, size, borderValue=(255, 255, 255))
