param(
    [string]$MainOutput = "data/desi_main",
    [string]$CorrectionOutput = "data/desi_corrections"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$LocalPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Python = if (Test-Path $LocalPython) { $LocalPython } else { "python" }

& $Python -m desi_rv_audit.cli download-main `
    --main-output $MainOutput `
    --correction-output $CorrectionOutput

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
