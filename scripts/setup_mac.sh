#!/usr/bin/env bash
# Set up the project on macOS Apple Silicon (arm64) with Python 3.11.
# Usage: bash scripts/setup_mac.sh   (run from the project root)
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ "$(uname -m)" != "arm64" ]]; then
  echo "WARNING: expected arm64, got $(uname -m). Are you running under Rosetta?" >&2
fi

# Never fall back to plain `python3` — on this machine it is 3.15, which has no PaddlePaddle wheel.
PY=""
for cand in /opt/homebrew/bin/python3.11 "$(command -v python3.11 || true)"; do
  if [[ -n "$cand" && -x "$cand" ]]; then PY="$cand"; break; fi
done
if [[ -z "$PY" ]]; then
  echo "ERROR: python3.11 not found. Install it with:  brew install python@3.11" >&2
  exit 1
fi
echo "Using $PY ($("$PY" -c 'import platform,sys;print(sys.version.split()[0], platform.machine())'))"

if [[ ! -d .venv ]]; then
  "$PY" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip

# PaddlePaddle CPU wheel from the official index (macOS arm64)
python -m pip install "paddlepaddle==3.3.0" -i https://www.paddlepaddle.org.cn/packages/stable/cpu/

# Remaining pinned dependencies (verified versions)
python -m pip install -r requirements.txt

# paddlex pulls opencv-contrib-python; a second OpenCV wheel would clash on `cv2`.
python -m pip uninstall -y opencv-python opencv-python-headless >/dev/null 2>&1 || true

python -m pip install -e . --no-deps

echo
echo "Environment check:"
python scripts/check_environment.py --download
