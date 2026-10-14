"""Device selection and GPU guards — runnable without a GPU (availability is faked)."""

from __future__ import annotations

import sys
import types
from dataclasses import replace
from types import SimpleNamespace

import pytest

from qty_ocr import device as dev
from qty_ocr.config import ConfigError, validate_config
from qty_ocr.recognizer import PaddleV5Recognizer, RecognizerInitError


@pytest.mark.parametrize("spec,ok", [("cpu", True), ("auto", True), ("gpu", True), ("gpu:0", True),
                                     ("gpu:3", True), ("GPU:1", True), ("cpu:0", False), ("auto:1", False),
                                     ("cuda", False), ("gpu:x", False), ("", False)])
def test_is_valid_device(spec, ok):
    assert dev.is_valid_device(spec) is ok


def test_config_accepts_gpu_and_rejects_garbage(cfg):
    validate_config(replace(cfg, hardware=replace(cfg.hardware, device="gpu:0")))
    validate_config(replace(cfg, hardware=replace(cfg.hardware, device="auto")))
    with pytest.raises(ConfigError):
        validate_config(replace(cfg, hardware=replace(cfg.hardware, device="cuda")))


@pytest.fixture
def fake_gpu(monkeypatch):
    def set_available(ok: bool):
        monkeypatch.setattr(dev, "gpu_available", lambda engine: (ok, "faked for test"))
    return set_available


def test_resolve_cpu_never_probes(fake_gpu):
    fake_gpu(True)
    assert dev.resolve_device("cpu", "onnxruntime").device == "cpu"


def test_resolve_auto(fake_gpu):
    fake_gpu(False)
    assert dev.resolve_device("auto", "onnxruntime").device == "cpu"
    fake_gpu(True)
    choice = dev.resolve_device("auto", "onnxruntime")
    assert choice.device == "gpu:0" and choice.is_gpu


def test_resolve_explicit_gpu(fake_gpu):
    fake_gpu(True)
    assert dev.resolve_device("gpu", "onnxruntime").device == "gpu:0"
    assert dev.resolve_device("gpu:1", "paddle_static").device == "gpu:1"
    fake_gpu(False)
    with pytest.raises(dev.DeviceUnavailableError):
        dev.resolve_device("gpu", "onnxruntime")


def test_real_probe_on_this_machine_reports_reason():
    ok, why = dev.gpu_available("onnxruntime")
    assert isinstance(ok, bool) and why


def _install_fake_paddleocr(monkeypatch, providers):
    """Replace paddleocr.TextRecognition with a stub exposing the attributes the recogniser uses."""
    created = {}

    class FakeTextRecognition:
        def __init__(self, **kwargs):
            created.update(kwargs)
            session = SimpleNamespace(get_providers=lambda: list(providers))
            post_op = SimpleNamespace(character=["blank"] + list("0123456789"))
            self.paddlex_predictor = SimpleNamespace(runner=SimpleNamespace(session=session), post_op=post_op)

    fake = types.ModuleType("paddleocr")
    fake.TextRecognition = FakeTextRecognition
    monkeypatch.setitem(sys.modules, "paddleocr", fake)
    return created


def test_recognizer_refuses_silent_cpu_fallback(cfg, fake_gpu, monkeypatch):
    fake_gpu(True)
    _install_fake_paddleocr(monkeypatch, ["CPUExecutionProvider"])  # CUDA failed to load
    hw = replace(cfg.hardware, device="gpu")
    with pytest.raises(RecognizerInitError, match="GPU requested"):
        PaddleV5Recognizer(replace(cfg.ocr, engine="onnxruntime"), hw, None)


def test_recognizer_passes_gpu_device_to_paddleocr(cfg, fake_gpu, monkeypatch):
    fake_gpu(True)
    created = _install_fake_paddleocr(monkeypatch, ["CUDAExecutionProvider", "CPUExecutionProvider"])
    rec = PaddleV5Recognizer(replace(cfg.ocr, engine="onnxruntime"), replace(cfg.hardware, device="gpu:0"), None)
    assert created["device"] == "gpu:0" and created["model_name"] == "PP-OCRv5_server_rec"
    assert rec.device == "gpu:0" and rec.providers[0] == "CUDAExecutionProvider"


def test_recognizer_gpu_requested_without_cuda_is_clear_error(cfg, fake_gpu, monkeypatch):
    fake_gpu(False)
    _install_fake_paddleocr(monkeypatch, ["CPUExecutionProvider"])
    with pytest.raises(RecognizerInitError, match="no usable GPU"):
        PaddleV5Recognizer(cfg.ocr, replace(cfg.hardware, device="gpu"), None)
