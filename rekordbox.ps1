# Standalone launcher. Modified 2026-10-23; preserves the original checkout's runtime.
$ErrorActionPreference = 'Stop'
$taskPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) {
    $taskPython = Join-Path $PSScriptRoot 'rekordbox\agent-harness\.venv\Scripts\python.exe'
}
if (-not (Test-Path -LiteralPath $taskPython)) {
    throw 'Create .venv here with Python 3.11+ and run: .\.venv\Scripts\python.exe -m pip install -e .'
}
& $taskPython -m cli_anything.rekordbox @args
exit $LASTEXITCODE
