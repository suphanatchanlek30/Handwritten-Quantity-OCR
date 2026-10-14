"""Optimised code paths must give exactly the same results as the straightforward ones."""

from __future__ import annotations

import importlib.util
import socket
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageOps

from qty_ocr.digit_decoder import decode_fixed_length, decode_fixed_lengths
from qty_ocr.image_loader import load_image

from .conftest import ROOT, SAMPLE_PATH

ORT_MODEL = Path.home() / ".paddlex" / "official_models" / "PP-OCRv5_server_rec_onnx"
HAS_ORT = importlib.util.find_spec("onnxruntime") is not None and ORT_MODEL.exists()


def _pillow_bgr(path: Path) -> np.ndarray:
    with Image.open(path) as im:
        return np.ascontiguousarray(np.asarray(ImageOps.exif_transpose(im).convert("RGB"))[:, :, ::-1])


@pytest.mark.skipif(not SAMPLE_PATH.exists(), reason="real sample not present")
def test_fast_jpeg_decode_matches_pillow():
    assert np.array_equal(load_image(SAMPLE_PATH).bgr, _pillow_bgr(SAMPLE_PATH))


def test_png_and_rotated_jpeg_use_pillow_path(tmp_path):
    rgb = (np.random.default_rng(0).integers(0, 255, (80, 120, 3))).astype(np.uint8)
    png = tmp_path / "a.png"
    Image.fromarray(rgb).save(png)
    assert np.array_equal(load_image(png).bgr, rgb[:, :, ::-1])
    jpg = tmp_path / "rot.jpg"
    exif = Image.Exif()
    exif[0x0112] = 6  # rotate 90 CW on display
    Image.fromarray(rgb).save(jpg, exif=exif, quality=95)
    loaded = load_image(jpg)
    assert loaded.bgr.shape[:2] == (120, 80) and loaded.metadata["exif_rotated"]
    assert np.array_equal(loaded.bgr, _pillow_bgr(jpg))


def test_single_pass_viterbi_equals_separate_runs():
    rng = np.random.default_rng(3)
    for _ in range(200):
        T = int(rng.integers(1, 50))
        q = rng.dirichlet(np.ones(11) * rng.uniform(0.05, 1.0), size=T)
        allk = decode_fixed_lengths(q, 4)
        for k in range(1, 5):
            assert allk[k] == decode_fixed_length(q, k)


@pytest.mark.ocr
@pytest.mark.skipif(not (HAS_ORT and SAMPLE_PATH.exists()), reason="onnxruntime model or sample missing")
def test_runs_fully_offline(cfg, tmp_path, monkeypatch):
    """With models cached, initialisation and inference must not open any network connection."""
    attempts: list[object] = []

    def blocked(self, addr, *a, **k):  # type: ignore[no-untyped-def]
        attempts.append(addr)
        raise OSError("network blocked by test")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    from qty_ocr.pipeline import process_document
    from qty_ocr.recognizer import PaddleV5Recognizer

    rec = PaddleV5Recognizer(cfg.ocr, cfg.hardware, cfg.network)
    doc = process_document(SAMPLE_PATH, cfg, tmp_path / "out", recognizer=rec, debug=False)
    assert doc.status == "completed" and attempts == []


@pytest.mark.ocr
@pytest.mark.skipif(not (HAS_ORT and SAMPLE_PATH.exists()), reason="onnxruntime model or sample missing")
def test_batch_paths_match_single_document(cfg, tmp_path):
    from qty_ocr.pipeline import process_document, process_many
    from qty_ocr.recognizer import PaddleV5Recognizer

    rec = PaddleV5Recognizer(cfg.ocr, cfg.hardware, cfg.network)
    paths = [SAMPLE_PATH, ROOT.parent / "Data Test" / "arm-14.jpg"]
    paths = [p for p in paths if p.exists()]
    single = [process_document(p, cfg, tmp_path / "s" / p.stem, recognizer=rec, debug=False) for p in paths]
    for prefetch in (False, True):
        many = [d for _, d in process_many(paths, cfg, tmp_path / f"m{prefetch}", recognizer=rec, prefetch=prefetch)]
        for a, b in zip(single, many):
            assert [(f.value, f.status, f.review_reasons) for f in a.fields] == \
                   [(f.value, f.status, f.review_reasons) for f in b.fields]
