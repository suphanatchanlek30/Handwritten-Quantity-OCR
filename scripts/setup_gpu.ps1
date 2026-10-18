# Set up the project on Windows x64 with an NVIDIA GPU (e.g. RTX 3050).
# PREPARED BUT NOT YET TESTED ON A GPU — check every step's output.
# Usage (PowerShell, from the project root):  powershell -ExecutionPolicy Bypass -File scripts\setup_gpu.ps1
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed ($LASTEXITCODE): $FilePath $($Arguments -join ' ')"
    }
}

$env:PYTHONUTF8 = "1"   # avoid console encoding errors with non-ASCII output
if (-not (Get-Command nvidia-smi -ErrorAction SilentlyContinue)) { throw "nvidia-smi not found - install the NVIDIA driver first" }
Invoke-Checked nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv

if (-not (Test-Path .venv)) { Invoke-Checked py -3.11 -m venv .venv }
$python = ".\.venv\Scripts\python.exe"
try {
    Invoke-Checked $python -c "import sys; assert sys.version_info[:2] == (3, 11); assert sys.maxsize > 2**32"
} catch {
    throw "Existing .venv must use Python 3.11 (64-bit). Remove .venv and run this script again."
}
Invoke-Checked $python -m pip install --upgrade pip
Invoke-Checked $python -m pip install -r requirements-gpu.txt
Invoke-Checked $python -m pip uninstall -y onnxruntime opencv-python opencv-python-headless
Invoke-Checked $python -m pip install -e . --no-deps
Invoke-Checked $python -c "import onnxruntime as o; p=o.get_available_providers(); print(p); assert 'CUDAExecutionProvider' in p"
Invoke-Checked $python scripts\check_environment.py --download
Write-Host "Next: $python -m qty_ocr.cli run --input data\samples\order_form_01.jpg --output outputs\gpu_run --device gpu"
