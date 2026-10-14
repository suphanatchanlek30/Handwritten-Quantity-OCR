#!/usr/bin/env bash
# Set up the project on a Linux x86_64 machine with an NVIDIA GPU (e.g. RTX 3050).
# PREPARED BUT NOT YET TESTED ON A GPU — check every step's output.
# Usage: bash scripts/setup_gpu.sh   (run from the project root)
set -euo pipefail
cd "$(dirname "$0")/.."

PY="$(command -v python3.11 || true)"
if [[ -z "$PY" ]]; then
  echo "ERROR: python3.11 not found (paddleocr 3.7 / onnxruntime-gpu 1.31 wheels here are tested with 3.11)" >&2
  exit 1
fi
if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "ERROR: nvidia-smi not found — install the NVIDIA driver first" >&2
  exit 1
fi
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv

[[ -d .venv ]] || "$PY" -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-gpu.txt
python -m pip uninstall -y onnxruntime opencv-python opencv-python-headless >/dev/null 2>&1 || true
python -m pip install -e . --no-deps

echo
echo "Environment check (GPU):"
python - <<'PY'
import onnxruntime as ort
print("onnxruntime", ort.__version__, "providers:", ort.get_available_providers())
assert "CUDAExecutionProvider" in ort.get_available_providers(), "CUDAExecutionProvider missing"
PY
python scripts/check_environment.py --download
echo
echo "Next: python -m qty_ocr.cli run --input data/samples/order_form_01.jpg --output outputs/gpu_run --device gpu"
