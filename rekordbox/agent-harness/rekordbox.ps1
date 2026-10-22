# Local launcher for this fork. Added 2026-10-22; does not install CLI Hub.
$ErrorActionPreference = 'Stop'
$taskPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) {
    throw 'Create .venv here with Python 3.11+ and run: .\.venv\Scripts\python.exe -m pip install -e .'
}
& $taskPython -m cli_anything.rekordbox @args
exit $LASTEXITCODE
