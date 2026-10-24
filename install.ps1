# Example: ./install.ps1 --target codex --scope user
$ErrorActionPreference = 'Stop'
if (Get-Command python -ErrorAction SilentlyContinue) {
    & python (Join-Path $PSScriptRoot 'scripts/install.py') @args
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 (Join-Path $PSScriptRoot 'scripts/install.py') @args
} else {
    throw 'Python 3.10+ is needed for this installer. Manual copy instructions are in docs/setup.md.'
}
exit $LASTEXITCODE
