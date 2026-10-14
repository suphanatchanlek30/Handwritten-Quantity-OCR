"""Stage 9 — PP-OCRv5 Server Recognition adapter.

Verified against paddleocr 3.7.0 / paddlex 3.7.2 / paddlepaddle 3.3.0:

* ``TextRecognition(model_name=..., device="cpu", engine="paddle_static", cpu_threads=N)``
* ``predict(input=<path | BGR ndarray | list>, batch_size=N)`` returns a list of
  ``TextRecResult``; fields are read from the documented ``.json["res"]``
  serialisation (``rec_text``, ``rec_score``).
* ndarray inputs must be **BGR** (identical score to file-path input).

Digit-constrained decoding (``ocr.digit_constrained_decoding``) wraps the
predictor's ``post_op`` (a ``CTCLabelDecode`` in paddlex 3.7.2) to capture the
softmax matrix it already receives, then re-decodes it with
:mod:`qty_ocr.digit_decoder`. This touches a non-public paddlex attribute, so
the hook is verified at start-up and raises :class:`RecognizerInitError` if the
installed version does not match — it never degrades silently.

The model is created once per :class:`PaddleV5Recognizer` instance and reused.
``rec_score`` is the model's own confidence, not a calibrated probability.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np

from .config import HardwareConfig, NetworkConfig, OCRConfig
from .device import DeviceUnavailableError, actual_onnxruntime_providers, resolve_device
from .digit_decoder import DigitAlphabet, decode_digits, digit_distribution
from .net import disable_model_source_check, force_ipv4

logger = logging.getLogger(__name__)


class RecognizerInitError(RuntimeError):
    """The OCR engine or model could not be initialised (missing package, download failure ...)."""


class UnexpectedResultError(RuntimeError):
    """The installed PaddleOCR returned a result shape this adapter does not understand."""


@dataclass
class RawRecognition:
    raw_text: str | None
    rec_score: float | None
    inference_time_ms: float
    model_name: str
    error: str | None = None
    digit_text: str | None = None      # digit-constrained decoding of the same output
    digit_score: float | None = None
    digit_char_scores: list[float] = field(default_factory=list)
    digit_substituted: int = 0
    digit_q: np.ndarray | None = None  # (T, 11) per-frame [blank, 0..9] distribution for re-decoding


class _ProbabilityCapture:
    """Callable stand-in for paddlex ``post_op`` that records the probabilities it is given."""

    def __init__(self, original: Any) -> None:
        self._original = original
        self.captured: list[np.ndarray] = []

    def __call__(self, pred: Any, *args: Any, **kwargs: Any) -> Any:
        batch = np.asarray(pred[0])
        self.captured.extend(batch[i] for i in range(batch.shape[0]))
        return self._original(pred, *args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._original, name)


def extract_text_and_score(result: Any) -> tuple[str, float]:
    """Read ``rec_text``/``rec_score`` via the documented JSON serialisation."""
    payload = getattr(result, "json", None)
    if isinstance(payload, dict) and isinstance(payload.get("res"), dict):
        res = payload["res"]
    elif isinstance(result, dict):
        res = result
    else:
        raise UnexpectedResultError(f"Unsupported result type: {type(result).__name__}")
    if "rec_text" not in res or "rec_score" not in res:
        raise UnexpectedResultError(f"Result lacks rec_text/rec_score: keys={sorted(res)}")
    return str(res["rec_text"]), float(res["rec_score"])


class PaddleV5Recognizer:
    """Thin, reusable wrapper around ``paddleocr.TextRecognition``."""

    def __init__(
        self,
        ocr: OCRConfig,
        hardware: HardwareConfig,
        network: NetworkConfig | None = None,
    ) -> None:
        self.cfg = ocr
        self.model_name = ocr.model_name
        if network is not None:
            if network.force_ipv4:
                force_ipv4()
            if network.disable_model_source_check:
                disable_model_source_check()
        try:
            from paddleocr import TextRecognition
        except ImportError as exc:
            raise RecognizerInitError(
                "paddleocr is not installed in this environment. Run scripts/setup_mac.sh"
            ) from exc

        try:
            self.device_choice = resolve_device(hardware.device, ocr.engine)
        except DeviceUnavailableError as exc:
            raise RecognizerInitError(str(exc)) from exc
        self.device = self.device_choice.device
        kwargs: dict[str, Any] = {
            "model_name": ocr.model_name,  # always explicit: library default is PP-OCRv6
            "device": self.device,
            "engine": ocr.engine,
            "cpu_threads": hardware.cpu_threads,
        }
        if ocr.model_dir:
            kwargs["model_dir"] = ocr.model_dir
        if ocr.enable_mkldnn is not None:
            kwargs["enable_mkldnn"] = ocr.enable_mkldnn
        if ocr.engine == "onnxruntime":
            # Same PP-OCRv5_server_rec weights exported to ONNX (official *_onnx model).
            # ONNX Runtime ignores the Paddle-specific options; threads go via engine_config.
            kwargs.pop("enable_mkldnn", None)
            kwargs.pop("cpu_threads", None)
            if ocr.onnx_intra_op_threads:
                kwargs["engine_config"] = {"intra_op_num_threads": ocr.onnx_intra_op_threads}

        t0 = time.perf_counter()
        try:
            self._model = TextRecognition(**kwargs)
        except Exception as exc:  # noqa: BLE001 - re-raised with context, never swallowed
            raise RecognizerInitError(
                f"Failed to initialise {ocr.model_name} ({type(exc).__name__}: {exc}). "
                "See docs/TROUBLESHOOTING.md (model download / IPv6 / Paddle install)."
            ) from exc
        self.init_time_ms = (time.perf_counter() - t0) * 1000
        self.providers = actual_onnxruntime_providers(self._model) if ocr.engine == "onnxruntime" else None
        if self.device_choice.is_gpu and ocr.engine == "onnxruntime":
            # ONNX Runtime silently falls back to CPU when CUDA/cuDNN fail to load: refuse that.
            if not self.providers or self.providers[0] != "CUDAExecutionProvider":
                raise RecognizerInitError(
                    f"GPU requested but the ONNX Runtime session runs on {self.providers}. "
                    "Check CUDA/cuDNN versions for onnxruntime-gpu (see docs/TROUBLESHOOTING.md)."
                )
        logger.info("Loaded %s in %.0f ms on %s (%s) providers=%s kwargs=%s", ocr.model_name,
                    self.init_time_ms, self.device, self.device_choice.reason, self.providers, kwargs)

        self._capture: _ProbabilityCapture | None = None
        self._alphabet: DigitAlphabet | None = None
        if ocr.digit_constrained_decoding:
            self._install_digit_hook()

    def _install_digit_hook(self) -> None:
        predictor = getattr(self._model, "paddlex_predictor", None)
        post_op = getattr(predictor, "post_op", None)
        characters = getattr(post_op, "character", None)
        if predictor is None or post_op is None or not isinstance(characters, list):
            raise RecognizerInitError(
                "digit_constrained_decoding needs paddlex TextRecRunnerPredictor.post_op.character "
                "(verified on paddlex 3.7.2). Set ocr.digit_constrained_decoding: false for this version."
            )
        try:
            self._alphabet = DigitAlphabet.from_character_list(characters)
        except ValueError as exc:
            raise RecognizerInitError(f"Cannot build digit alphabet: {exc}") from exc
        self._capture = _ProbabilityCapture(post_op)
        predictor.post_op = self._capture
        logger.info("Digit-constrained decoding enabled (%d classes)", len(characters))

    def recognize(self, image_bgr: np.ndarray) -> RawRecognition:
        return self.recognize_batch([image_bgr])[0]

    def recognize_batch(self, images_bgr: Sequence[np.ndarray]) -> list[RawRecognition]:
        """Recognise BGR crops; one output per input, in order.

        All images go to a single ``predict()`` call (PaddleX still runs them in
        internal batches of ``ocr.batch_size``), which avoids per-call overhead.
        If that call fails, the images are retried chunk by chunk so an error is
        attributed only to the chunk that caused it.
        """
        if not images_bgr:
            return []
        images = [self._check_image(img) for img in images_bgr]
        # With batch_size > 1 PaddleX pads every image in a batch to the widest one;
        # grouping similar aspect ratios keeps that padding (wasted compute) small.
        order = list(range(len(images)))
        if self.cfg.batch_size > 1:
            order.sort(key=lambda i: images[i].shape[1] / images[i].shape[0])
        t0 = time.perf_counter()
        if self._capture is not None:
            self._capture.captured.clear()
        try:
            results = self._model.predict(input=[images[i] for i in order], batch_size=self.cfg.batch_size)
            if len(results) != len(images):
                raise UnexpectedResultError(f"Expected {len(images)} results, got {len(results)}")
            parsed_sorted = [extract_text_and_score(r) for r in results]
            parsed: list[tuple[str, float]] = [("", 0.0)] * len(images)
            for pos, i in enumerate(order):
                parsed[i] = parsed_sorted[pos]
            if self._capture is not None:
                captured = list(self._capture.captured)
                if len(captured) != len(images):
                    raise UnexpectedResultError(f"Captured {len(captured)} probability maps for {len(images)} images")
                restored = [captured[0]] * len(images)
                for pos, i in enumerate(order):
                    restored[i] = captured[pos]
                self._capture.captured[:] = restored
        except MemoryError as exc:
            raise RuntimeError(
                "Out of memory during OCR; reduce ocr.batch_size or hardware.cpu_threads"
            ) from exc
        except Exception:  # noqa: BLE001 - fall back to per-chunk calls to isolate the failure
            logger.warning("Whole-list recognition failed; retrying chunk by chunk", exc_info=True)
            return self._recognize_chunked(images)
        elapsed = (time.perf_counter() - t0) * 1000 / len(images)
        return self._build_outputs(parsed, elapsed)

    def _build_outputs(self, parsed: list[tuple[str, float]], elapsed: float) -> list[RawRecognition]:
        digits = self._decode_captured(len(parsed))
        probs = list(self._capture.captured) if self._capture is not None else [None] * len(parsed)
        outputs: list[RawRecognition] = []
        for (text, score), dig, prob in zip(parsed, digits, probs):
            rr = RawRecognition(text, score, elapsed, self.model_name)
            if prob is not None and self._alphabet is not None:
                rr.digit_q = digit_distribution(prob, self._alphabet).astype(np.float32)
            if dig is not None:
                rr.digit_text, rr.digit_score = dig.text, dig.score
                rr.digit_char_scores, rr.digit_substituted = dig.char_scores, dig.substituted
            outputs.append(rr)
        return outputs

    def _recognize_chunked(self, images_bgr: Sequence[np.ndarray]) -> list[RawRecognition]:
        """Chunk-by-chunk recognition; a failing chunk becomes ``recognition_error`` entries."""
        outputs: list[RawRecognition] = []
        bs = self.cfg.batch_size
        for start in range(0, len(images_bgr), bs):
            chunk = list(images_bgr[start : start + bs])
            t0 = time.perf_counter()
            if self._capture is not None:
                self._capture.captured.clear()
            try:
                results = self._model.predict(input=chunk, batch_size=bs)
                if len(results) != len(chunk):
                    raise UnexpectedResultError(
                        f"Expected {len(chunk)} results, got {len(results)}"
                    )
                parsed = [extract_text_and_score(r) for r in results]
            except MemoryError as exc:
                raise RuntimeError(
                    "Out of memory during OCR; reduce ocr.batch_size or hardware.cpu_threads"
                ) from exc
            except Exception as exc:  # noqa: BLE001 - recorded per field as recognition_error
                elapsed = (time.perf_counter() - t0) * 1000 / len(chunk)
                logger.exception("Recognition failed for batch starting at %d", start)
                outputs.extend(
                    RawRecognition(None, None, elapsed, self.model_name, f"{type(exc).__name__}: {exc}")
                    for _ in chunk
                )
                continue
            elapsed = (time.perf_counter() - t0) * 1000 / len(chunk)
            outputs.extend(self._build_outputs(parsed, elapsed))
        return outputs

    def _decode_captured(self, n: int) -> list[Any]:
        if self._capture is None or self._alphabet is None:
            return [None] * n
        probs = self._capture.captured
        if len(probs) != n:
            raise UnexpectedResultError(f"Captured {len(probs)} probability maps for {n} images")
        return [decode_digits(p, self._alphabet) for p in probs]

    @staticmethod
    def _check_image(img: np.ndarray) -> np.ndarray:
        if not isinstance(img, np.ndarray) or img.ndim != 3 or img.shape[2] != 3:
            raise ValueError("Recognizer expects HxWx3 BGR uint8 arrays")
        if img.dtype != np.uint8:
            raise ValueError(f"Recognizer expects uint8, got {img.dtype}")
        return np.ascontiguousarray(img)
