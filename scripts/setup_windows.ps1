# Set up the CPU version on Windows x64 with Python 3.11.
# Run from the repository root:
#   powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
$env:PYTHONUTF8 = "1"

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

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python Launcher ('py') was not found. Install 64-bit Python 3.11 from https://www.python.org/downloads/windows/."
}

try {
    Invoke-Checked py -3.11 -c "import sys; assert sys.maxsize > 2**32; print(sys.version)"
} catch {
    throw "Python 3.11 (64-bit) is required. Install it, then run this script again."
}

if (-not (Test-Path ".venv")) {
    Invoke-Checked py -3.11 -m venv .venv
}

$python = ".\.venv\Scripts\python.exe"
try {
    Invoke-Checked $python -c "import sys; assert sys.version_info[:2] == (3, 11); assert sys.maxsize > 2**32"
} catch {
    throw "Existing .venv must use Python 3.11 (64-bit). Remove .venv and run this script again."
}
Invoke-Checked $python -m pip install --upgrade pip

# Windows CPU wheels are installed from PyPI. The pinned list prevents a second
# OpenCV distribution from replacing the supported opencv-contrib package.
Invoke-Checked $python -m pip install -r requirements.txt
Invoke-Checked $python -m pip uninstall -y opencv-python opencv-python-headless
Invoke-Checked $python -m pip install -e . --no-deps

Write-Host ""
Write-Host "Environment check (downloads the PP-OCR model on first run):"
Invoke-Checked $python scripts\check_environment.py --download
Write-Host ""
Write-Host "Ready. Example: & $python -m qty_ocr.cli run --input data\samples\order_form_01.jpg --output outputs\example --debug"
