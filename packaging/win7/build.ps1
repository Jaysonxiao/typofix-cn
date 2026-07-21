$ErrorActionPreference = "Stop"

$profilePython = Join-Path $PSScriptRoot ".venv-win7\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $profilePython)) {
    throw "Missing Win7 profile interpreter: $profilePython"
}

& $profilePython -m pip install -r (Join-Path $PSScriptRoot "requirements.txt")
Set-Location (Resolve-Path (Join-Path $PSScriptRoot "..\.."))
& $profilePython (Join-Path $PSScriptRoot "test_profile.py")
& $profilePython -m PyInstaller (Join-Path $PSScriptRoot "typofix_win7.spec") --noconfirm --clean
