from __future__ import annotations

import csv
import importlib.util
import json
from dataclasses import replace
from pathlib import Path

import cv2
import numpy as np
import pytest

from qty_ocr.config import ConfigError, load_config, validate_config
from qty_ocr.image_loader import ImageLoadError, load_image
from qty_ocr.pipeline import process_document

from .conftest import CONFIG_PATH, SAMPLE_PATH

MODEL_DIR = Path.home() / ".paddlex" / "official_models" / "PP-OCRv5_server_rec"
HAS_OCR = importlib.util.find_spec("paddleocr") is not None and MODEL_DIR.exists()


def test_config_validation(cfg):
    validate_config(cfg)
    with pytest.raises(ConfigError):
        validate_config(replace(cfg, ocr=replace(cfg.ocr, batch_size=3)))
    template_mode = replace(cfg, layout=replace(cfg.layout, mode="template"))
    with pytest.raises(ConfigError):  # template must agree with expected_rows
        validate_config(replace(template_mode, field=replace(cfg.field, expected_rows=9)))
    validate_config(replace(cfg, field=replace(cfg.field, expected_rows=9)))  # auto: only a note
    with pytest.raises(ConfigError):
        validate_config(replace(cfg, layout=replace(cfg.layout, mode="magic")))


def test_config_rejects_unknown_key(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text(
        CONFIG_PATH.read_text(encoding="utf-8") + "\nocr_typo:\n  x: 1\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError):
        load_config(p)


def test_image_loader_errors(tmp_path):
    with pytest.raises(ImageLoadError):
        load_image(tmp_path / "missing.jpg")
    bad = tmp_path / "corrupt.jpg"
    bad.write_bytes(b"not an image")
    with pytest.raises(ImageLoadError):
        load_image(bad)
    gif = tmp_path / "x.gif"
    gif.write_bytes(b"GIF89a")
    with pytest.raises(ImageLoadError):
        load_image(gif)


def test_image_loader_returns_bgr(tmp_path):
    img = np.zeros((60, 60, 3), np.uint8)
    img[:, :] = (255, 0, 0)  # pure blue in BGR
    p = tmp_path / "blue.png"
    cv2.imwrite(str(p), img)
    loaded = load_image(p)
    assert tuple(loaded.bgr[0, 0]) == (255, 0, 0)


def test_crop_mode_on_synthetic(cfg, synthetic_form, tmp_path):
    src = tmp_path / "synthetic.png"
    cv2.imwrite(str(src), synthetic_form)
    doc = process_document(src, cfg, tmp_path / "out", recognizer=None, debug=True)
    assert doc.status == "crops_only"
    blanks = [f.row_id for f in doc.fields if f.is_blank]
    assert blanks == [4, 6, 7, 8, 9, 10]
    assert all(f.value is None for f in doc.fields)  # never fabricate values without OCR
    for name in ["results.json", "results.csv", "summary.md", "diagnostics.json",
                 "qty_overlay.png", "contact_sheet.png", "aligned.png", "table_lines.png"]:
        assert (tmp_path / "out" / name).exists(), name


def test_alignment_failure_produces_artifacts(cfg, tmp_path):
    src = tmp_path / "white.png"
    cv2.imwrite(str(src), np.full((800, 600, 3), 255, np.uint8))
    doc = process_document(src, cfg, tmp_path / "out", recognizer=None, debug=True)
    assert doc.status == "alignment_failed"
    assert all(f.status.value == "alignment_failed" for f in doc.fields)
    assert (tmp_path / "out" / "original.png").exists()
    assert (tmp_path / "out" / "results.json").exists()


@pytest.mark.ocr
@pytest.mark.skipif(not (HAS_OCR and SAMPLE_PATH.exists()), reason="paddleocr/model or sample unavailable")
def test_full_pipeline_real_sample(cfg, tmp_path):
    from qty_ocr.recognizer import PaddleV5Recognizer

    rec = PaddleV5Recognizer(cfg.ocr, cfg.hardware, cfg.network)
    doc = process_document(SAMPLE_PATH, cfg, tmp_path / "run", recognizer=rec, debug=True)
    assert doc.status == "completed" and doc.model == "PP-OCRv5_server_rec"
    payload = json.loads((tmp_path / "run" / "results.json").read_text(encoding="utf-8"))
    assert len(payload["fields"]) == 10
    for f in payload["fields"]:
        if f["is_blank"]:
            assert f["value"] is None and f["status"] == "blank"
        else:
            assert f["candidates"], "OCR must actually run on nonblank crops"
            assert all(c["model_name"] == "PP-OCRv5_server_rec" for c in f["candidates"])
            if f["value"] is not None:
                assert f["value"].isdigit() and 1 <= len(f["value"]) <= 3
            if f["status"] == "ok":
                assert f["confidence"] >= cfg.ocr.confidence_review_threshold
    with (tmp_path / "run" / "results.csv").open(encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 10 and {"document_id", "row_id", "qty", "confidence", "status",
                                "needs_review", "review_reasons", "crop_path"} <= set(rows[0])
