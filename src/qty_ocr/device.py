"""Inference device selection (CPU / NVIDIA GPU) for the recogniser.

``hardware.device`` accepts:

* ``cpu``            — always CPU (default; the only option on Apple Silicon)
* ``gpu`` / ``gpu:N`` — NVIDIA GPU N (default 0); **fails** if CUDA is unavailable
* ``auto``           — ``gpu:0`` when the configured engine can use CUDA, otherwise ``cpu``

A GPU is never assumed: availability is probed for the configured engine
(``onnxruntime`` → ``CUDAExecutionProvider``; ``paddle_static`` → Paddle built
with CUDA and a visible device). After the model is loaded the recogniser also
checks which provider ONNX Runtime *actually* uses, because ONNX Runtime can
quietly fall back to CPU when CUDA/cuDNN libraries fail to load.

Only the CPU path has been run on this project's development machine (Apple
Silicon, no NVIDIA GPU). The GPU path is prepared but unverified.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_DEVICE_RE = re.compile(r"^(cpu|auto|gpu)(?::(\d+))?$")


class DeviceUnavailableError(RuntimeError):
    """A GPU was requested but the installed runtime cannot use one."""


@dataclass(frozen=True)
class DeviceChoice:
    device: str          # value passed to PaddleOCR: "cpu" or "gpu:N"
    requested: str
    reason: str

    @property
    def is_gpu(self) -> bool:
        return self.device.startswith("gpu")


def is_valid_device(spec: str) -> bool:
    m = _DEVICE_RE.match(spec.strip().lower())
    return bool(m) and not (m.group(1) in ("cpu", "auto") and m.group(2) is not None)


def onnxruntime_cuda_available() -> tuple[bool, str]:
    try:
        import onnxruntime as ort
    except ImportError:
        return False, "onnxruntime is not installed"
    providers = ort.get_available_providers()
    if "CUDAExecutionProvider" in providers:
        return True, f"onnxruntime providers {providers}"
    return False, (f"onnxruntime has no CUDAExecutionProvider (available: {providers}); "
                   "install onnxruntime-gpu instead of onnxruntime")


def paddle_cuda_available() -> tuple[bool, str]:
    try:
        import paddle
    except ImportError:
        return False, "paddlepaddle is not installed"
    if not paddle.device.is_compiled_with_cuda():
        return False, "paddlepaddle is a CPU build; install paddlepaddle-gpu"
    count = paddle.device.cuda.device_count()
    if count < 1:
        return False, "paddlepaddle-gpu is installed but no CUDA device is visible"
    return True, f"paddle CUDA devices: {count}"


def gpu_available(engine: str) -> tuple[bool, str]:
    if engine == "onnxruntime":
        return onnxruntime_cuda_available()
    if engine == "paddle_static":
        return paddle_cuda_available()
    return False, f"unknown engine {engine!r}"


def resolve_device(requested: str, engine: str) -> DeviceChoice:
    """Turn ``hardware.device`` into a concrete device, probing GPU support for ``engine``."""
    spec = requested.strip().lower()
    m = _DEVICE_RE.match(spec)
    if not m or not is_valid_device(spec):
        raise ValueError(f"hardware.device must be cpu, auto, gpu or gpu:N — got {requested!r}")
    kind, index = m.group(1), m.group(2)
    if kind == "cpu":
        return DeviceChoice("cpu", requested, "configured")
    ok, why = gpu_available(engine)
    if kind == "auto":
        if ok:
            return DeviceChoice("gpu:0", requested, f"auto: {why}")
        logger.info("device auto → cpu (%s)", why)
        return DeviceChoice("cpu", requested, f"auto: {why}")
    if not ok:
        raise DeviceUnavailableError(
            f"hardware.device={requested!r} but no usable GPU for engine {engine!r}: {why}. "
            "Use hardware.device: cpu (or auto), or see README section 'รันบน GPU'."
        )
    return DeviceChoice(f"gpu:{index or 0}", requested, why)


def actual_onnxruntime_providers(model: object) -> list[str] | None:
    """Providers the loaded ONNX Runtime session really uses (``None`` if not inspectable)."""
    runner = getattr(getattr(model, "paddlex_predictor", None), "runner", None)
    session = getattr(runner, "session", None)
    get = getattr(session, "get_providers", None)
    return list(get()) if callable(get) else None
