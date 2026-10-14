# Set up the project on Windows x64 with an NVIDIA GPU (e.g. RTX 3050).
# PREPARED BUT NOT YET TESTED ON A GPU — check every step's output.
# Usage (PowerShell, from the project root):  powershell -ExecutionPolicy Bypass -File scripts\setup_gpu.ps1
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$env:PYTHONUTF8 = "1"   # avoid console encoding errors with non-ASCII output
if (-not (Get-Command nvidia-smi -ErrorAction SilentlyContinue)) { throw "nvidia-smi not found - install the NVIDIA driver first" }
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv

if (-not (Test-Path .venv)) { py -3.11 -m venv .venv }
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-gpu.txt
.\.venv\Scripts\python.exe -m pip uninstall -y onnxruntime opencv-python opencv-python-headless 2>$null
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
.\.venv\Scripts\python.exe -c "import onnxruntime as o; p=o.get_available_providers(); print(p); assert 'CUDAExecutionProvider' in p"
.\.venv\Scripts\python.exe scripts\check_environment.py --download
Write-Host "Next: .\.venv\Scripts\python.exe -m qty_ocr.cli run --input data\samples\order_form_01.jpg --output outputs\gpu_run --device gpu"
