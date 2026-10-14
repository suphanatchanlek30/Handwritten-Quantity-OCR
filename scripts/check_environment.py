"""Environment check: Python, architecture, packages, Paddle backend and model readiness.

Usage:
    python scripts/check_environment.py            # checks only (no network)
    python scripts/check_environment.py --download # also download/initialise the model (IPv4)
"""

from __future__ import annotations

import argparse
import importlib
import os
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Must run before paddlex is imported: it reads PADDLE_PDX_* flags at import time,
# and this machine's IPv6 route hangs model downloads.
from qty_ocr.net import disable_model_source_check, force_ipv4  # noqa: E402

force_ipv4()
disable_model_source_check()

MODEL_NAME = "PP-OCRv5_server_rec"  # + "_onnx" when ocr.engine is onnxruntime


def status(ok: bool, label: str, detail: str = "") -> bool:
    print(f"  [{'OK' if ok else 'FAIL'}] {label}{(': ' + detail) if detail else ''}")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true", help="initialise the model (downloads if missing)")
    parser.add_argument("--config", default=str(ROOT / "configs" / "changhouse.yaml"))
    args = parser.parse_args()

    all_ok = True
    print("System")
    is_mac = platform.system() == "Darwin"
    if is_mac:
        all_ok &= status(platform.machine() == "arm64", "architecture (expect arm64, not Rosetta)", platform.machine())
    else:
        status(True, "architecture", f"{platform.system()} {platform.machine()}")
    all_ok &= status(sys.version_info[:2] == (3, 11), "python", sys.version.split()[0])
    mac = platform.mac_ver()[0]
    status(True, "macOS", mac or "n/a")

    print("Packages")
    versions = {}
    for mod in ["paddle", "paddleocr", "paddlex", "onnxruntime", "cv2", "numpy", "PIL", "yaml"]:
        try:
            m = importlib.import_module(mod)
            versions[mod] = getattr(m, "__version__", "?")
            status(True, mod, versions[mod])
        except Exception as exc:  # noqa: BLE001 - report every import problem
            all_ok &= status(False, mod, f"{type(exc).__name__}: {exc}")

    try:
        from importlib.metadata import distributions

        cv_dists = sorted(d.metadata["Name"] for d in distributions() if d.metadata["Name"].lower().startswith("opencv"))
        all_ok &= status(len(cv_dists) == 1, "single OpenCV distribution", ", ".join(cv_dists))
    except Exception as exc:  # noqa: BLE001
        status(False, "OpenCV distribution check", str(exc))

    print("Paddle backend")
    if "paddle" in versions:
        import paddle

        status(True, "compiled with CUDA", str(paddle.device.is_compiled_with_cuda()) + (" (expected False on Mac)" if platform.system() == "Darwin" else ""))
        status(True, "device", paddle.device.get_device())
        try:
            paddle.utils.run_check()
            status(True, "paddle.utils.run_check()")
        except Exception as exc:  # noqa: BLE001
            all_ok &= status(False, "paddle.utils.run_check()", str(exc))

    print("GPU (NVIDIA / CUDA)")
    from qty_ocr.config import load_config as _load_cfg
    from qty_ocr.device import onnxruntime_cuda_available, paddle_cuda_available, resolve_device

    cfg_now = _load_cfg(args.config)
    for name, probe in (("onnxruntime CUDA", onnxruntime_cuda_available), ("paddle CUDA", paddle_cuda_available)):
        ok, why = probe()
        print(f"  [{'OK' if ok else '--'}] {name}: {why}")
    try:
        choice = resolve_device(cfg_now.hardware.device, cfg_now.ocr.engine)
        status(True, "device for this config", f"{cfg_now.hardware.device!r} -> {choice.device} ({choice.reason})")
    except Exception as exc:  # noqa: BLE001 - report configuration problems
        all_ok &= status(False, "device for this config", str(exc))

    print("Model")
    from qty_ocr.config import load_config as _load

    engine = _load(args.config).ocr.engine
    folder = MODEL_NAME + ("_onnx" if engine == "onnxruntime" else "")
    cache = Path(os.environ.get("PADDLE_PDX_CACHE_HOME", Path.home() / ".paddlex")) / "official_models" / folder
    cached = (cache / ("inference.onnx" if engine == "onnxruntime" else "inference.pdiparams")).exists()
    if cached:
        status(True, f"{folder} cached (engine={engine})", str(cache))
    else:
        print(f"  [--] {folder} not cached yet: {cache}")
    if args.download or cached:
        try:
            from qty_ocr.config import load_config
            from qty_ocr.recognizer import PaddleV5Recognizer

            cfg = load_config(args.config)
            rec = PaddleV5Recognizer(cfg.ocr, cfg.hardware, cfg.network)
            status(True, "TextRecognition init",
                   f"{rec.init_time_ms:.0f} ms, engine={cfg.ocr.engine}, device={rec.device}, providers={rec.providers}")
        except Exception as exc:  # noqa: BLE001
            all_ok &= status(False, "TextRecognition init", f"{type(exc).__name__}: {exc}")
    elif not cached:
        all_ok = False
        print("    -> run with --download to fetch the model (~84 MB)")

    print("\nRESULT:", "READY" if all_ok else "NOT READY (see FAIL lines above)")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
